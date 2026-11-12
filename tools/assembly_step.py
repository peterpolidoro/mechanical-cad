"""Build one STEP file, and one FreeCAD document, of a whole assembly of a project.

    FreeCADCmd tools/assembly_step.py --pass PROJECT [KEY] [-- --out DIR] [-- --frame own] [-- --force]

FreeCADCmd reads dashed options itself, even after --pass; put a bare `--`
before this script's own options.

A project stores an assembly as its parts' STEP files and the placements in
assembly.json, never as a STEP file of its own. This derives that file for
looking at the assembly, in FreeCAD or any other CAD system: KEY (default: the
only assembly no other assembly places) is flattened, each part file is read
once, without the items it marks invisible, and every visible occurrence is a
link to it inside one container per sub-assembly instance. The tree, and the
product structure of the STEP file, are the assembly's hierarchy with its
occurrence names. `python3 -m mechanical_cad assemblies PROJECT` lists the
keys and says which are built.

Written to DIR, by default PROJECT/.cache/assemblies/ (derived, so the project
ignores it and it is never committed):

    KEY.step    the whole assembly; geometry shared between the instances of a part; normalised header
    KEY.FCStd   the same as a FreeCAD document, which opens faster than the STEP file imports
    KEY.json    what was built from what, and the check below; no timestamp

--frame z-up (the default) turns an assembly whose frame is +Y up so that it
stands upright in FreeCAD; --frame own leaves it in the assembly's own frame.

Before anything is kept the STEP file is read back and every solid in it is
matched, by volume and centre of mass, against where the flattened scene puts
it (mechanical_cad/solids.py). If the report describes the same scene, frame
and tool and the files are the ones it names, nothing is built and no file
changes; --force builds again.

What the files are not: they carry positions, not constraints or joints, and
shapes, not features. FreeCADCmd has no view, so they carry no colour either.
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

import kernel  # noqa: E402
from mechanical_cad import assemblies, flatten, jsonio, layout, solids, stepfile  # noqa: E402
from mechanical_cad import transforms as T  # noqa: E402

REPORT_SCHEMA = 1
_SOLID = re.compile(rb"=\s*(?:MANIFOLD_SOLID_BREP|BREP_WITH_VOIDS)\s*\(")


def placement(rows):
    return App.Placement(App.Matrix(*[float(v) for row in rows for v in row]))


def leaf(path):
    return path.rsplit("/", 1)[-1]


def build(scene, assets, frame):
    """Return (document, object to export, {part id: its solids}, {part id: invisible items left out})."""
    doc = App.newDocument("assembly")
    definitions = doc.addObject("App::DocumentObjectGroup", "definitions")
    definitions.Label = "Part files (the assembly links to these)"
    names = {p["id"]: p["name"] for p in scene["parts"]}
    features, part_solids, hidden = {}, {}, {}
    for i, (key, path) in enumerate(assets):
        shape, left_out = kernel.read_step_visible(path)
        feature = doc.addObject("Part::Feature", "part_%03d" % i)
        feature.Label = names[key]
        feature.Shape = shape
        feature.Visibility = False
        definitions.addObject(feature)
        features[key] = feature
        part_solids[key] = kernel.solids(shape)
        if left_out:
            hidden[key] = left_out
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
    containers = {}
    for a in scene["assemblies"]:          # in the order of the walk: a parent comes before its children
        if a["id"] not in needed:
            continue
        c = doc.addObject("App::Part", "asm_%03d" % len(containers))
        if a["parent_id"] is None:
            c.Label = f"{a['document']} (turned to Z up)" if turned else scene["title"]
            c.Placement = placement(to_frame)
        else:
            c.Label = leaf(a["id"])
            c.Placement = placement(a["transform"])
            containers[a["parent_id"]].addObject(c)
        containers[a["id"]] = c
    top = containers["root"]
    if turned:
        # The exporter leaves out the placement of the object it is given, so the root, which carries the
        # turn, goes inside one more container and that one is exported.
        top = doc.addObject("App::Part", "whole")
        top.Label = scene["title"]
        top.addObject(containers["root"])

    for i, o in enumerate(occurrences):
        link = doc.addObject("App::Link", "occ_%04d" % i)
        link.LinkedObject = features[o["part_id"]]
        link.Label = leaf(o["id"])
        link.Placement = placement(o["transform"])
        containers[o["parent_id"]].addObject(link)
    doc.recompute()
    return doc, top, part_solids, hidden, len(containers)


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

    if not opts["force"] and report_path.exists() and step_path.exists() and doc_path.exists():
        old = jsonio.load(report_path)
        if (all(old.get(k) == v for k, v in inputs.items()) and old.get("check", {}).get("same")
                and old.get("step", {}).get("sha256") == stepfile.sha256_file(step_path)):
            print(f"[assembly_step] {key}: already current ({step_path})")
            print(f"[assembly_step] the same as a FreeCAD document: {doc_path}")
            return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    doc, export, part_solids, hidden, containers = build(scene, assets, opts["frame"])
    placed = solids.placed(scene)
    with tempfile.TemporaryDirectory(dir=out_dir, prefix=".building-") as tmp:
        tmp_step, tmp_doc = Path(tmp) / f"{key}.step", Path(tmp) / f"{key}.FCStd"
        Import.export([export], str(tmp_step))
        data = stepfile.normalise_header(tmp_step.read_bytes(), name=f"{key}.step")
        tmp_step.write_bytes(data)
        check = solids.match(solids.expected(scene, part_solids, opts["frame"]), kernel.solids(kernel.read_step(tmp_step)))
        doc.saveAs(str(tmp_doc))
        App.closeDocument(doc.Name)
        step_changed = not step_path.exists() or step_path.read_bytes() != data
        if step_changed:
            os.replace(tmp_step, step_path)
        if step_changed or not doc_path.exists():
            os.replace(tmp_doc, doc_path)

    visible = {o["id"] for o in placed}
    report = dict(inputs)
    report.update({
        "parts": len(assets), "assembly_nodes": containers, "occurrences": len(placed),
        "occurrences_not_visible_left_out": [o["id"] for o in scene["occurrences"] if o["id"] not in visible],
        "suppressed_left_out": suppressed, "invisible_items_left_out": hidden,
        "step": {"file": step_path.name, "sha256": stepfile.sha256_bytes(data), "bytes": len(data),
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
