"""Build one STEP file, and one FreeCAD document, of a whole assembly of a project.

    FreeCADCmd tools/assembly_step.py --pass PROJECT [KEY] [-- --out DIR] [-- --frame own] [-- --force]

FreeCADCmd reads dashed options itself, even after --pass; put a bare `--`
before this script's own options.

A project stores an assembly as its parts' STEP files and the placements in
assembly.json, never as a STEP file of its own. This derives that file for
looking at the assembly, in FreeCAD or any other CAD system: KEY (default: the
only assembly no other assembly places) is flattened, each part file is read
once, without the items it marks invisible, and every visible occurrence is a
link to it inside the container of its sub-assembly. In the STEP file,
instances of a sub-assembly that hold the same parts in the same places are
usages of one product, named after the assembly's file, as the mirrored CAD
system has one document for them; an instance that differs has a product of
its own. In the FreeCAD document every instance is a container of its own, so
that one can be hidden or looked into without the others. The tree, and the
product structure of the STEP file, are the assembly's hierarchy with its
occurrence names. In the STEP file every usage carries that name as its id as
well, because Inventor shows the id, and a name FreeCAD numbered anew, as it
does when another object of the document has it, is the occurrence's own
again (mechanical_cad/stepfile.py, name_usages). `python3 -m mechanical_cad
assemblies PROJECT` lists the keys and says which are built.

Written to DIR, by default PROJECT/.cache/assemblies/ (derived, so the project
ignores it and it is never committed):

    KEY.step    the whole assembly; geometry shared between the instances of a part, structure between the
                instances of a sub-assembly; normalised header
    KEY.FCStd   the same assembly as a FreeCAD document, which opens faster than the STEP file imports
    KEY.json    what was built from what, and the check below; no timestamp

--frame z-up (the default) turns an assembly whose frame is +Y up so that it
stands upright in FreeCAD; --frame own leaves it in the assembly's own frame.

Before anything is kept the STEP file is read back and every solid in it is
matched, by volume and centre of mass, against where the flattened scene puts
it (mechanical_cad/solids.py). If the report describes the same scene, frame
and tool and the files are the ones it names, nothing is built and no file
changes; --force builds again.

The FreeCAD document opens with the assembly shown and the part files it links
to hidden, in a group of their own (mechanical_cad/fcstd.py writes that into
it; FreeCADCmd has no window and would leave everything hidden).

What the files are not: they carry positions, not constraints or joints, and
shapes, not features. They carry no colour either.
The part files and the manifests stay the source; these are for reading.

FreeCADCmd prints an uncaught exception and still exits 0, so this script
prints its own status line; trust that and the files, not the exit code.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
import os
import re
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import FreeCAD as App  # noqa: E402
import Import  # noqa: E402
import Part  # noqa: E402

import kernel  # noqa: E402
from mechanical_cad import assemblies, fcstd, flatten, jsonio, layout, solids, stepfile  # noqa: E402
from mechanical_cad import transforms as T  # noqa: E402

REPORT_SCHEMA = assemblies.BUILD_SCHEMA
_SOLID = re.compile(rb"=\s*(?:MANIFOLD_SOLID_BREP|BREP_WITH_VOIDS)\s*\(")
_USAGE = re.compile(rb"=\s*NEXT_ASSEMBLY_USAGE_OCCURRENCE\s*\(")
_PRODUCT = re.compile(rb"=\s*PRODUCT\s*\(")


def placement(rows):
    return App.Placement(App.Matrix(*[float(v) for row in rows for v in row]))


def leaf(path):
    return path.rsplit("/", 1)[-1]


def stem(document):
    """The name of an assembly's file without its extension: what its product is called."""
    return document.rsplit(".", 1)[0] if "." in document.strip(".") else document


def contents(scene, occurrences, needed):
    """{assembly id: what that instance holds}: its document, and the visible occurrences and the
    sub-assemblies below it with the placements they have in it. Two instances with equal contents are the
    same assembly; one whose flexible parent places something differently is not."""
    parts, subs, out = {}, {}, {}
    for o in occurrences:
        parts.setdefault(o["parent_id"], []).append(o)
    for a in scene["assemblies"]:
        if a["parent_id"] is not None and a["id"] in needed:
            subs.setdefault(a["parent_id"], []).append(a)

    def cells(rows):
        return tuple(float(v) for row in rows for v in row)

    def content(a):
        if a["id"] not in out:
            out[a["id"]] = (
                a["document"],
                tuple(sorted((leaf(o["id"]), o["part_id"], cells(o["transform"])) for o in parts.get(a["id"], ()))),
                tuple(sorted((leaf(c["id"]), content(c), cells(c["transform"])) for c in subs.get(a["id"], ()))))
        return out[a["id"]]

    for a in scene["assemblies"]:
        if a["id"] in needed:
            content(a)
    return out


def read_parts(assets):
    """Every part file read once, without the items it marks invisible:
    ({part id: shape}, {part id: its solids}, {part id: invisible items left out})."""
    shapes, part_solids, hidden = {}, {}, {}
    for key, path in assets:
        shapes[key], left_out = kernel.read_step_visible(path)
        part_solids[key] = kernel.solids(shapes[key])
        if left_out:
            hidden[key] = left_out
    return shapes, part_solids, hidden


def build(scene, assets, shapes, frame, share):
    """One FreeCAD document of the scene. Return (document, its top object, counts, view, renamed, products).

    share: whether instances of a sub-assembly that hold the same are one container and links to it. The STEP
    file is written from a document built that way, so that it has one product for them. The document that
    is kept is built with a container for every instance: in FreeCAD what is hidden inside a container is
    hidden in every link to it, and one instance could not be hidden or looked into without the others.

    counts is (assembly instances, containers); view is ({object name: shown in the window?}, names of the
    open tree nodes, a camera that has the assembly in view); renamed is {the label FreeCAD gave an occurrence
    or a sub-assembly instance: the name it was to have} where the two differ; products is {the label of a
    sub-assembly's container: the name its product is to have}."""
    doc = App.newDocument("assembly_step" if share else "assembly")
    definitions = doc.addObject("App::DocumentObjectGroup", "definitions")
    definitions.Label = "Part files (the assembly links to these)"
    names = {p["id"]: p["name"] for p in scene["parts"]}
    features = {}
    for i, (key, _) in enumerate(assets):
        feature = doc.addObject("Part::Feature", "part_%03d" % i)
        feature.Label = names[key]
        feature.Shape = shapes[key]
        feature.Visibility = False
        definitions.addObject(feature)
        features[key] = feature
    definitions.Visibility = False

    occurrences = solids.placed(scene)
    parents = {a["id"]: a["parent_id"] for a in scene["assemblies"]}
    needed = set()
    for o in occurrences:
        node = o["parent_id"]
        while node is not None and node not in needed:
            needed.add(node)
            node = parents[node]
    needed.add("root")

    to_frame = solids.frame_matrix(scene, frame)
    turned = to_frame != T.identity()
    containers, renamed, products = {}, {}, {}
    holds = contents(scene, occurrences, needed)
    first, shown_by_a_link, instance_links = {}, set(), []
    product_names = set(names.values()) | {scene["title"]}

    def label(obj, name):
        # FreeCAD keeps the labels of a document distinct: it numbers a label anew when another object has it.
        obj.Label = name
        if obj.Label != name:
            renamed[obj.Label] = name
    for a in scene["assemblies"]:          # in the order of the walk: a parent comes before its children
        if a["id"] not in needed:
            continue
        if a["parent_id"] in shown_by_a_link:       # inside an instance that is a link: the container it
            shown_by_a_link.add(a["id"])            # links to holds this one already
            continue
        if share and a["parent_id"] is not None and holds[a["id"]] in first:
            link = doc.addObject("App::Link", "asm_link_%03d" % len(instance_links))
            link.LinkedObject = first[holds[a["id"]]]
            label(link, leaf(a["id"]))
            link.Placement = placement(a["transform"])
            containers[a["parent_id"]].addObject(link)
            instance_links.append(link)
            shown_by_a_link.add(a["id"])
            continue
        c = doc.addObject("App::Part", "asm_%03d" % len(containers))
        if a["parent_id"] is None:
            c.Label = f"{a['document']} (turned to Z up)" if turned else scene["title"]
            c.Placement = placement(to_frame)
        else:
            label(c, leaf(a["id"]))
            c.Placement = placement(a["transform"])
            containers[a["parent_id"]].addObject(c)
            if share:
                first[holds[a["id"]]] = c
            # its product is named after the assembly's file; a second, different instance of that file,
            # or a part of that name, gets a number
            wanted, n = stem(a["document"]), 1
            while wanted in product_names:
                n += 1
                wanted = f"{stem(a['document'])} ({n})"
            product_names.add(wanted)
            products[c.Label] = wanted
        containers[a["id"]] = c
    top = containers["root"]
    if turned:
        # The exporter leaves out the placement of the object it is given, so the root, which carries the
        # turn, goes inside one more container and that one is exported.
        top = doc.addObject("App::Part", "whole")
        top.Label = scene["title"]
        top.addObject(containers["root"])

    shown = {}
    for i, o in enumerate(occurrences):
        if o["parent_id"] in shown_by_a_link:
            continue
        link = doc.addObject("App::Link", "occ_%04d" % i)
        link.LinkedObject = features[o["part_id"]]
        label(link, leaf(o["id"]))
        link.Placement = placement(o["transform"])
        containers[o["parent_id"]].addObject(link)
        shown[link.Name] = True
    doc.recompute()
    # In the window: the part files hidden, the assembly shown, its first level open in the tree.
    shown[definitions.Name] = False
    shown.update({f.Name: False for f in features.values()})
    shown.update({c.Name: True for c in containers.values()})
    shown.update({link.Name: True for link in instance_links})
    shown[top.Name] = True
    box = Part.getShape(top).BoundBox
    camera = fcstd.isometric_camera((box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax))
    return (doc, top, (len(needed), len(containers)), (shown, {top.Name, containers["root"].Name}, camera),
            renamed, products)


def options(argv):
    argv = [a for a in argv if a != "--"]
    opts = {"out": None, "frame": "z-up", "force": False}
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--force":
            opts["force"] = True
        elif a in ("--out", "--frame") and i + 1 < len(argv):
            opts[a[2:]] = argv[i + 1]
            i += 1
        elif a.startswith("--"):
            raise SystemExit(__doc__)
        else:
            positional.append(a)
        i += 1
    if not 1 <= len(positional) <= 2 or opts["frame"] not in solids.FRAMES:
        raise SystemExit(__doc__)
    return Path(positional[0]), (positional[1] if len(positional) == 2 else None), opts


def main(argv):
    project_dir, key, opts = options(argv)
    project = layout.load(project_dir)
    try:
        top = flatten.find_root(project, key)
        scene, assets, suppressed = flatten.flatten(project, top.key)
    except flatten.FlattenError as exc:
        for line in project.errors:
            print("ERROR  ", line)
        print(f"[assembly_step] {exc}")
        return 2
    key = top.key
    out_dir = Path(opts["out"]) if opts["out"] else assemblies.default_dir(project_dir)
    step_path, doc_path, report_path = (out_dir / f"{key}{ext}" for ext in (".step", ".FCStd", ".json"))
    inputs = {"schema_version": REPORT_SCHEMA, "key": key, "root": top.path,
              "scene_sha256": assemblies.scene_sha256(scene),
              "frame": opts["frame"], "tool": kernel.tool()}

    old = {}
    if report_path.exists():
        try:
            old = jsonio.load(report_path)
        except jsonio.JsonError:
            pass
        if not isinstance(old, dict):
            old = {}
    if not opts["force"] and old and step_path.exists() and doc_path.exists():
        if (all(old.get(k) == v for k, v in inputs.items()) and old.get("check", {}).get("same")
                and old.get("step", {}).get("sha256") == stepfile.sha256_file(step_path)):
            print(f"[assembly_step] {key}: already current ({step_path})")
            print(f"[assembly_step] the same as a FreeCAD document: {doc_path}")
            return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    shapes, part_solids, hidden = read_parts(assets)
    placed = solids.placed(scene)
    with tempfile.TemporaryDirectory(dir=out_dir, prefix=".building-") as tmp:
        tmp_step, tmp_doc = Path(tmp) / f"{key}.step", Path(tmp) / f"{key}.FCStd"
        doc, export, counts, _, renamed, products = build(scene, assets, shapes, opts["frame"], share=True)
        Import.export([export], str(tmp_step))
        App.closeDocument(doc.Name)
        data = stepfile.normalise_header(tmp_step.read_bytes(), name=f"{key}.step")
        data, named, restored = stepfile.name_usages(data, renamed)
        data, renamed_products = stepfile.name_products(data, products)
        tmp_step.write_bytes(data)
        check = solids.match(solids.expected(scene, part_solids, opts["frame"]), kernel.solids(kernel.read_step(tmp_step)))
        doc, _, _, view, _, _ = build(scene, assets, shapes, opts["frame"], share=False)
        doc.saveAs(str(tmp_doc))
        App.closeDocument(doc.Name)
        fcstd.write_view(tmp_doc, *view)       # saved without a window, the document would open with nothing shown
        step_changed = not step_path.exists() or step_path.read_bytes() != data
        if step_changed:
            os.replace(tmp_step, step_path)
        # The document is a zip archive with the time of its writing in it: it is replaced only when it has to be.
        if step_changed or not doc_path.exists() or old.get("schema_version") != REPORT_SCHEMA:
            os.replace(tmp_doc, doc_path)

    visible = {o["id"] for o in placed}
    report = dict(inputs)
    report.update({
        "parts": len(assets), "assembly_nodes": counts[0], "assembly_containers": counts[1],
        "occurrences": len(placed),
        "occurrences_not_visible_left_out": [o["id"] for o in scene["occurrences"] if o["id"] not in visible],
        "suppressed_left_out": suppressed, "invisible_items_left_out": hidden,
        "step": {"file": step_path.name, "sha256": stepfile.sha256_bytes(data), "bytes": len(data),
                 "usages": len(_USAGE.findall(data)), "usages_with_their_name_as_id": named,
                 "names_put_back": restored,
                 "products": len(_PRODUCT.findall(data)), "assembly_products_named_after_their_file": renamed_products,
                 "solid_definitions": len(_SOLID.findall(data)),
                 "solids_in_the_part_files": sum(len(v) for v in part_solids.values())},
        "document": doc_path.name,
        "check": check,
    })
    if not report_path.exists() or jsonio.load(report_path) != report:
        jsonio.write(report_path, report)
    print(f"[assembly_step] {key}: {len(assets)} part(s), {len(placed)} occurrence(s), {check['solids_found']} solid(s); "
          f"{step_path} {'written' if step_changed else 'unchanged'}")
    if not check["same"]:
        print(f"[assembly_step] FAILED: {len(check['unmatched'])} solid(s) are not where the scene puts them and "
              f"{len(check['found_but_not_expected'])} are not expected; see {report_path}")
        return 1
    print(f"[assembly_step] read back: every solid is where the scene puts it, within "
          f"{check['worst_position_deviation_mm']:.2g} mm")
    print(f"[assembly_step] the same as a FreeCAD document: {doc_path}")
    return 0


def _is_entry():
    here = Path(__file__).resolve()
    return any(a and Path(a).resolve() == here for a in sys.argv[:2])


if _is_entry():
    if "--pass" in sys.argv:
        args = sys.argv[sys.argv.index("--pass") + 1:]
    else:
        args = [a for a in sys.argv[1:] if Path(a).resolve() != Path(__file__).resolve()]
    try:
        rc = main(args)
    except SystemExit as exc:
        print(exc)
        rc = 2
    except BaseException:
        import traceback
        traceback.print_exc()
        rc = 1
    print(f"[assembly_step] exit status {rc}", flush=True)
    sys.exit(rc)
