"""Take one STEP file of an assembly apart into a project in the layout.

    python3 tools/take_apart.py FILE.step PROJECT --retrieved YYYY-MM-DD --publishable yes|no|unknown
        (--supplier S --part-number N [--url U] | --repository URL --commit HASH --path PATH | --description TEXT [--url U])
        [--licence L] [--note TEXT] [--name NAME] [--up +Y|+Z]

Run it where the OCP bindings are (.guix/manifest-build123d.scm).

FILE.step is a whole assembly as a CAD system exported it: products that hold
geometry, products that are made of other products, and the usages that place
one in another. PROJECT is a directory that does not exist yet, or one an
earlier run on the same file wrote. Written there (mechanical_cad/takeapart.py
has the rules for keys and names):

    designs/parts/<key>/part.step, origin.json     a supplied part for every product with geometry of its own:
                                                   its shape as the kernel read it, written out in millimetres
    designs/assemblies/<key>/assembly.json         an assembly for every product made of others: its direct
                                                   children under their usages' names, where the file has them
    .cache/take-apart/<root key>.json              what was read and what the rules changed; no timestamp

A product used several times is one part, placed several times. The options
after PROJECT say where the file came from, as for `add-supplied`; every part
records it, with the product it is and the hash of the file it was taken from.
--name gives the root assembly another name than its product's; --up states
which axis of the file points up, when that is known.

What is read: the product structure with its names and placements, and each
product's shape, through the kernel's reader for STEP files with structure. A
file that holds each product in its own length unit is read in millimetres.
What is not kept: colours, layers and materials, and the order of anything.
The result is checked afterwards with the layout's own tools:

    python3 -m mechanical_cad validate PROJECT
    FreeCADCmd tools/step_facts.py --pass PROJECT                  measure every part
    FreeCADCmd tools/assembly_step.py --pass PROJECT ROOT -- --frame own
    FreeCADCmd tools/compare_assembly_step.py --pass PROJECT ROOT FILE.step NEW.json     every solid, where the file has it

Running it again on the same file writes the same bytes and changes no file.
Prints what it did and a status line; the exit status is 0 when the project
was written, 1 when the file was refused, 2 when the command cannot be run.
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile

sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mechanical_cad import jsonio, stepfile, supplied, takeapart  # noqa: E402

REPORT_SCHEMA = 1
REPORT_DIR = (".cache", "take-apart")
_COLOUR = re.compile(rb"=\s*COLOUR_RGB\s*\(")
_PRODUCT = re.compile(rb"=\s*PRODUCT\s*\(")
_USAGE = re.compile(rb"=\s*NEXT_ASSEMBLY_USAGE_OCCURRENCE\s*\(")


def quiet():
    """Keep the kernel's reader and writer from printing their statistics for every product."""
    from OCP.Message import Message, Message_Gravity

    for printer in Message.DefaultMessenger_s().Printers():
        printer.SetTraceLevel(Message_Gravity.Message_Fail)


def read_tree(path):
    """The product structure of a STEP file and the shape of every product: (tree, {product id: shape}).

    The tree is the one mechanical_cad/takeapart.py plans from. A product id is
    the entry of its label in the document the kernel reads the file into.
    """
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TCollection import TCollection_AsciiString, TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDF import TDF_Label, TDF_LabelSequence, TDF_Tool
    from OCP.TDocStd import TDocStd_Document
    from OCP.TopAbs import TopAbs_FACE, TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ShapeTool

    document = TDocStd_Document(TCollection_ExtendedString("take-apart"))
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.SetColorMode(False)
    reader.SetLayerMode(False)
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise takeapart.TakeApartError(f"the kernel cannot read {path} as a STEP file")
    if not reader.Transfer(document):
        raise takeapart.TakeApartError(f"the kernel read {path} and could not take its structure over")
    tool = XCAFDoc_DocumentTool.ShapeTool_s(document.Main())

    def entry(label):
        text = TCollection_AsciiString()
        TDF_Tool.Entry_s(label, text)
        return text.ToCString()

    def name(label):
        attribute = TDataStd_Name()
        if label.FindAttribute(TDataStd_Name.GetID_s(), attribute):
            return attribute.Get().ToExtString()
        return ""

    def count(shape, what):
        n, explorer = 0, TopExp_Explorer(shape, what)
        while explorer.More():
            n += 1
            explorer.Next()
        return n

    def rows(location):
        t = location.Transformation()
        return [[t.Value(r, c) for c in (1, 2, 3, 4)] for r in (1, 2, 3)] + [[0.0, 0.0, 0.0, 1.0]]

    products, shapes = {}, {}

    def product(label):
        pid = entry(label)
        if pid in products:
            return pid
        record = products[pid] = {"name": name(label), "children": []}
        if XCAFDoc_ShapeTool.IsAssembly_s(label):
            components = TDF_LabelSequence()
            XCAFDoc_ShapeTool.GetComponents_s(label, components, False)
            for i in range(1, components.Length() + 1):
                component = components.Value(i)
                referred = TDF_Label()
                if not XCAFDoc_ShapeTool.GetReferredShape_s(component, referred):
                    continue
                record["children"].append({"name": name(component), "product": product(referred),
                                           "transform": rows(XCAFDoc_ShapeTool.GetLocation_s(component))})
            if record["children"]:
                return pid
        shape = XCAFDoc_ShapeTool.GetShape_s(label)
        record["solids"] = 0 if shape.IsNull() else count(shape, TopAbs_SOLID)
        record["geometry"] = not shape.IsNull() and count(shape, TopAbs_FACE) > 0
        shapes[pid] = shape
        return pid

    free = TDF_LabelSequence()
    tool.GetFreeShapes(free)
    return {"roots": [product(free.Value(i)) for i in range(1, free.Length() + 1)], "products": products}, shapes


def write_step(shape, name, path):
    """One product's shape as a STEP file of its own: AP214, millimetres, one product of that name."""
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.Interface import Interface_Static
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer

    writer = STEPControl_Writer()
    Interface_Static.SetCVal_s("write.step.schema", "AP214IS")
    Interface_Static.SetCVal_s("write.step.unit", "MM")
    Interface_Static.SetIVal_s("write.step.assembly", 0)
    Interface_Static.SetCVal_s("write.step.product.name", name)
    if writer.Transfer(shape, STEPControl_AsIs) != IFSelect_RetDone or writer.Write(str(path)) != IFSelect_RetDone:
        raise takeapart.TakeApartError(f"the kernel could not write the product {name!r} as a STEP file")


def describe(data):
    """What the text of the file says of itself: protocol, length units, how many products, usages and colours."""
    out = {"products": len(_PRODUCT.findall(data)), "usages": len(_USAGE.findall(data)),
           "colours": len(_COLOUR.findall(data))}
    try:
        out["protocol"] = stepfile.header(data)["protocol"]
    except Exception as exc:                       # an odd header does not stop the kernel from reading the file
        out["protocol"], out["header"] = None, str(exc)
    try:
        out["length_unit"] = stepfile.length_unit(data)
    except stepfile.StepFileError as exc:          # an assembly export may keep each document's own unit
        out["length_unit"], out["length_units"] = None, str(exc)
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("project")
    ap.add_argument("--retrieved", required=True)
    ap.add_argument("--publishable", required=True, choices=("yes", "no", "unknown"))
    for option in ("supplier", "part-number", "url", "repository", "commit", "path", "description", "licence", "note",
                   "name", "up"):
        ap.add_argument("--" + option)
    args = ap.parse_args(argv)
    file, project_dir = Path(args.file), Path(args.project)
    kind = "supplier" if args.supplier else "repository" if args.repository else "other"
    try:
        origin = supplied.origin_record(
            kind, args.retrieved, {"yes": True, "no": False, "unknown": None}[args.publishable],
            licence=args.licence, note=args.note,
            **({"supplier": args.supplier, "part_number": args.part_number, "url": args.url} if kind == "supplier" else
               {"repository": args.repository, "commit": args.commit, "path": args.path} if kind == "repository" else
               {"description": args.description, "url": args.url}))
        received = file.read_bytes()
    except (supplied.SuppliedError, OSError) as exc:
        print(f"[take_apart] {exc}")
        return 2
    said = describe(received)
    try:
        quiet()
        tree, shapes = read_tree(file)
        planned = takeapart.plan(tree, file.name, root_name=args.name)
        files = {}
        with tempfile.TemporaryDirectory() as tmp:
            for part in planned["parts"]:
                out = Path(tmp) / "part.step"
                write_step(shapes[part["product"]], part["name"], out)
                files[part["key"]] = out.read_bytes()
        done = takeapart.write(project_dir, planned, files, origin, file.name, stepfile.sha256_bytes(received),
                               up_axis=args.up)
    except takeapart.TakeApartError as exc:
        print(f"[take_apart] REFUSED: {exc}")
        return 1
    from OCP import __version__ as bindings
    notes = planned["notes"]
    report = {
        "schema_version": REPORT_SCHEMA, "root": planned["root"],
        "file": {"name": file.name, "sha256": stepfile.sha256_bytes(received), "bytes": len(received), **said},
        "tool": {"name": "OCP", "version": bindings},
        "products_read": len(tree["products"]), "parts": len(planned["parts"]), "assemblies": len(planned["assemblies"]),
        "occurrences": planned["occurrences"], "solids": planned["solids"],
        "parts_without_a_solid": sorted(p["key"] for p in planned["parts"] if not p["solids"]),
        "keys_numbered": notes["keys_numbered"], "names_changed": notes["names_changed"],
        "left_out_no_geometry": sorted(notes["left_out"]), "not_used": sorted(notes["not_used"]),
        "wrapped": notes["wrapped"],
        "not_kept": ["colours", "layers", "materials", "each product's own length unit: every part is written in mm"],
    }
    report_path = project_dir.joinpath(*REPORT_DIR, f"{planned['root']}.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if not report_path.is_file() or jsonio.load(report_path) != report:
        jsonio.write(report_path, report)
    print(f"[take_apart] {file.name}: {len(tree['products'])} product(s) read; {len(planned['parts'])} part(s) and "
          f"{len(planned['assemblies'])} assembly(ies); flattened from {planned['root']}: {planned['occurrences']} "
          f"occurrence(s), {planned['solids']} solid(s)")
    for what, items in (("key(s) numbered because two products gave the same", notes["keys_numbered"]),
                        ("usage name(s) changed", notes["names_changed"]),
                        ("product(s) without geometry left out", notes["left_out"]),
                        ("product(s) nothing uses left out", notes["not_used"])):
        if items:
            print(f"[take_apart] {len(items)} {what}; see {report_path}")
    without = report["parts_without_a_solid"]
    if without:
        print(f"[take_apart] {len(without)} part(s) have faces and no solid: {', '.join(without[:5])}")
    if said["colours"]:
        print(f"[take_apart] the file has {said['colours']} colour(s); none is kept")
    print(f"[take_apart] {project_dir}: {done['written']} file(s) written, {done['unchanged']} unchanged; "
          f"the root assembly is {planned['root']}")
    return 0


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except SystemExit as exc:
        rc = exc.code if isinstance(exc.code, int) else 2
    except Exception as exc:  # noqa: BLE001
        print(f"[take_apart] FAILED: {exc}")
        rc = 1
    print(f"[take_apart] exit status {rc}")
    sys.exit(rc)
