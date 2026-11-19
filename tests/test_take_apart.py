"""Taking one STEP file of an assembly apart into the layout: the rules for keys and names and the writing,
without a kernel (mechanical_cad/takeapart.py); and the whole way round on a file made from the fixture, where
FreeCADCmd and the OCP bindings are (tools/take_apart.py; make test-build123d)."""
import importlib.util
import json
import shutil
import subprocess
import sys

import pytest
from conftest import FIXTURE, REPO

from mechanical_cad import finishes, layout, stepfile, supplied, takeapart
from mechanical_cad import transforms as T

FREECAD = shutil.which("FreeCADCmd")
with_kernel = pytest.mark.skipif(FREECAD is None or importlib.util.find_spec("OCP") is None,
                                 reason="FreeCADCmd and the OCP bindings are not both in this environment (make test-build123d)")
ORIGIN = supplied.origin_record("other", "2026-11-18", True, description="a synthetic assembly made for this test")
SPACER_STEP = (FIXTURE / "designs" / "parts" / "spacer" / "part.step").read_bytes()
MIRROR = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, -1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


def at(x=0.0, y=0.0, z=0.0):
    return [[1.0, 0.0, 0.0, x], [0.0, 1.0, 0.0, y], [0.0, 0.0, 1.0, z], [0.0, 0.0, 0.0, 1.0]]


def part(name, solids=1, geometry=True):
    return {"name": name, "children": [], "solids": solids, "geometry": geometry}


def use(product, name, transform=None):
    return {"name": name, "product": product, "transform": transform or at()}


def machine():
    """A root that holds a plate, a pair of pins twice (once as another product, posed differently), a second
    product called Bracket, a part that is only a sketch, and an assembly that holds nothing but that sketch."""
    return {"roots": ["r"], "products": {
        "r": {"name": "Machine.iam", "children": [
            use("plate", "PLATE:1"), use("pair", "PAIR:1", at(10)), use("pair2", "PAIR:1", at(20)),
            use("b1", "", at(0, 5)), use("b2", "a/b", at(0, 9)), use("sketch", "SKETCH:1"), use("hollow", "HOLLOW:1")]},
        "plate": part("Plate"),
        "pair": {"name": "PIN PAIR", "children": [use("pin", "PIN:1", at(-1)), use("pin", "PIN:2", at(1))]},
        "pair2": {"name": "PIN PAIR (2)", "children": [use("pin", "PIN:1", at(-1)), use("pin", "PIN:2", at(3))]},
        "pin": part("PIN", solids=2),
        "b1": part("Bracket"), "b2": part("bracket"),
        "sketch": part("Sketch only", solids=0, geometry=False),
        "hollow": {"name": "Hollow", "children": [use("sketch", "SKETCH:1")]},
        "spare": part("Spare"),
    }}


def test_a_key_is_the_name_in_lower_case_with_hyphens():
    assert takeapart.key_of("PIN PAIR (2)") == "pin-pair-2"
    assert takeapart.key_of("Free Standing Enclosure.iam") == "free-standing-enclosure"
    assert takeapart.key_of("MCMASTER 47065T245") == "mcmaster-47065t245"
    assert takeapart.key_of("Ø8 × 20 Träger.ipt") == "8-20-trager"
    assert takeapart.key_of("  ") == "" and takeapart.key_of("()") == "" and takeapart.key_of(None) == ""
    assert takeapart.key_of(".ipt") == "ipt"                                  # nothing would be left of it
    long = takeapart.key_of("x" * 79 + " y z")
    assert len(long) <= layout.KEY_MAX and not long.endswith("-") and layout.KEY.match(long)


def test_products_become_parts_and_assemblies_under_the_rules():
    planned = takeapart.plan(machine(), "machine.stp")
    assert planned["root"] == "machine"
    assert [p["key"] for p in planned["parts"]] == ["plate", "pin", "bracket", "bracket-2"]
    assert [a["key"] for a in planned["assemblies"]] == ["machine", "pin-pair", "pin-pair-2"]
    root = planned["assemblies"][0]
    assert [(c["name"], c["component"], c["kind"]) for c in root["children"]] == [
        ("PLATE:1", "plate", "part"), ("PAIR:1", "pin-pair", "assembly"), ("PAIR:1 (2)", "pin-pair-2", "assembly"),
        ("Bracket", "bracket", "part"), ("a-b", "bracket-2", "part")]
    assert root["children"][2]["transform"] == at(20)
    # a product used several times is one part: the pin is placed four times and has two solids
    assert planned["occurrences"] == 7 and planned["solids"] == 11
    notes = planned["notes"]
    assert notes["keys_numbered"] == [{"name": "bracket", "key": "bracket-2"}]
    assert {(n["was"], n["is"]) for n in notes["names_changed"]} == {("PAIR:1", "PAIR:1 (2)"), ("", "Bracket"), ("a/b", "a-b")}
    assert sorted(notes["left_out"]) == ["Hollow", "Sketch only"] and notes["not_used"] == ["Spare"]
    for a in planned["assemblies"]:
        assert all(layout.KEY.match(c["component"]) for c in a["children"])


def test_several_products_at_the_top_are_held_by_an_assembly_named_after_the_file():
    tree = {"roots": ["a", "b"], "products": {"a": part("Left"), "b": {"name": "Right", "children": [use("a", "L:1", at(4))]}}}
    planned = takeapart.plan(tree, "Two Things.step")
    assert planned["root"] == "two-things" and planned["notes"]["wrapped"]
    top = planned["assemblies"][0]
    assert [(c["name"], c["component"], c["transform"]) for c in top["children"]] == [("Left", "left", T.identity()),
                                                                                      ("Right", "right", T.identity())]
    assert takeapart.plan(tree, "two.step", root_name="Both")["root"] == "both"


def test_what_the_layout_cannot_hold_is_refused():
    with pytest.raises(takeapart.TakeApartError, match="one part and no assembly"):
        takeapart.plan({"roots": ["a"], "products": {"a": part("Alone")}}, "alone.step")
    mirrored = {"roots": ["r"], "products": {"r": {"name": "R", "children": [use("a", "A:1", MIRROR)]}, "a": part("A")}}
    with pytest.raises(takeapart.TakeApartError, match="reflection.*its own geometry"):
        takeapart.plan(mirrored, "m.step")
    scaled = {"roots": ["r"], "products": {"r": {"name": "R", "children": [
        use("a", "A:1", [[2.0, 0, 0, 0], [0, 2.0, 0, 0], [0, 0, 2.0, 0], [0, 0, 0, 1.0]])]}, "a": part("A")}}
    with pytest.raises(takeapart.TakeApartError, match="not orthonormal"):
        takeapart.plan(scaled, "s.step")
    loop = {"roots": ["r"], "products": {"r": {"name": "R", "children": [use("r", "R:1")]}}}
    with pytest.raises(takeapart.TakeApartError, match="contains itself"):
        takeapart.plan(loop, "l.step")
    nothing = {"roots": ["r"], "products": {"r": {"name": "R", "children": [use("a", "A:1")]},
                                            "a": part("A", solids=0, geometry=False)}}
    with pytest.raises(takeapart.TakeApartError, match="no geometry"):
        takeapart.plan(nothing, "n.step")


def test_the_plan_is_written_as_supplied_parts_and_assemblies_that_validate(tmp_path):
    planned = takeapart.plan(machine(), "machine.stp")
    files = {p["key"]: SPACER_STEP for p in planned["parts"]}
    project_dir = tmp_path / "project"
    done = takeapart.write(project_dir, planned, files, ORIGIN, "machine.stp", "ab" * 32, up_axis="+Y")
    assert done == {"written": 11, "unchanged": 0}                           # four parts of two files, three assemblies
    project = layout.load(project_dir)
    assert project.errors == []
    assert all("no facts.json" in f for f in project.findings) and len(project.findings) == 4
    pin = project.components["pin"]
    assert pin.supplied and pin.name == "PIN"
    record = json.loads((project_dir / "designs/parts/pin/origin.json").read_text())
    assert record["step"]["received_sha256"] == "ab" * 32 and record["step"]["header_normalised"] is True
    assert record["origin"]["kind"] == "other" and "The product 'PIN' of machine.stp" in record["origin"]["note"]
    assert stepfile.is_normalised((project_dir / "designs/parts/pin/part.step").read_bytes())
    root = json.loads((project_dir / "designs/assemblies/machine/assembly.json").read_text())
    assert root["frame"] == {"handedness": "right", "up_axis": "+Y"} and root["length_unit"] == "mm"
    assert "frame" not in json.loads((project_dir / "designs/assemblies/pin-pair/assembly.json").read_text())
    # the same again changes no file
    before = {p: p.read_bytes() for p in project_dir.rglob("*") if p.is_file()}
    assert takeapart.write(project_dir, planned, files, ORIGIN, "machine.stp", "ab" * 32, up_axis="+Y") == {
        "written": 0, "unchanged": 11}
    assert {p: p.read_bytes() for p in project_dir.rglob("*") if p.is_file()} == before
    # a note of the caller's stays beside the product
    noted = dict(ORIGIN, note="From the workshop.")
    takeapart.write(tmp_path / "noted", planned, files, noted, "machine.stp", "ab" * 32)
    said = json.loads((tmp_path / "noted/designs/parts/pin/origin.json").read_text())["origin"]["note"]
    assert said.startswith("The product 'PIN'") and said.endswith("From the workshop.")


def test_a_directory_that_holds_something_else_is_left_alone(tmp_path, project_copy):
    planned = takeapart.plan(machine(), "machine.stp")
    files = {p["key"]: SPACER_STEP for p in planned["parts"]}
    with pytest.raises(takeapart.TakeApartError, match="references/.*is not of this file"):
        takeapart.write(project_copy, planned, files, ORIGIN, "machine.stp", "ab" * 32)
    project_dir = tmp_path / "apart"                                       # project_copy is tmp_path / "project"
    takeapart.write(project_dir, planned, files, ORIGIN, "machine.stp", "ab" * 32)
    with pytest.raises(takeapart.TakeApartError, match="designs/parts/pin is not a part taken out of this file"):
        takeapart.write(project_dir, planned, files, ORIGIN, "other.stp", "cd" * 32)       # another file's hash
    with pytest.raises(takeapart.TakeApartError, match="no STEP file was written for: pin"):
        takeapart.write(tmp_path / "new", planned, {k: v for k, v in files.items() if k != "pin"}, ORIGIN, "machine.stp", "ab" * 32)
    with pytest.raises(takeapart.TakeApartError, match="up axis"):
        takeapart.write(tmp_path / "new", planned, files, ORIGIN, "machine.stp", "ab" * 32, up_axis="-X")


def test_a_part_gets_the_colour_most_of_its_surface_has():
    planned = takeapart.plan(machine(), "machine.stp")
    colours = {"plate": {"#B9B9B9": 9200.0},                                       # one colour, as the file wrote it
               "pin": {"#1f1fb4": 2000.0, "#ffdc40": 150.0, "#cc2211": 400.0},      # solids and a face of their own
               "b1": {"": 500.0, "#404040": 100.0},                                 # mostly without a colour
               "b2": {"": 80.0}}                                                    # none at all
    named, given, rows = takeapart.finishes_of(planned, colours)
    assert named == {"colour-b9b9b9": {"color": "#b9b9b9"}, "colour-1f1fb4": {"color": "#1f1fb4"},
                     "colour-404040": {"color": "#404040"}}
    assert given == {"plate": "colour-b9b9b9", "pin": "colour-1f1fb4", "bracket": "colour-404040"}
    assert rows == [{"key": "plate", "finish": "colour-b9b9b9", "share": 1.0, "colours": 1},
                    {"key": "pin", "finish": "colour-1f1fb4", "share": 0.784, "colours": 3},
                    {"key": "bracket", "finish": "colour-404040", "share": 0.167, "colours": 1},
                    {"key": "bracket-2", "finish": None, "share": None, "colours": 0}]
    # two colours that cover the same: the first in the order of the colours, whatever order they came in
    assert takeapart.finishes_of(planned, {"plate": {"#bbbbbb": 5.0, "#aaaaaa": 5.0}})[1] == {"plate": "colour-aaaaaa"}
    assert takeapart.finishes_of(planned, {}) == ({}, {}, [{"key": k, "finish": None, "share": None, "colours": 0}
                                                         for k in ("plate", "pin", "bracket", "bracket-2")])


def test_the_finishes_are_written_once_and_are_a_person_s_from_then_on(tmp_path):
    planned = takeapart.plan(machine(), "machine.stp")
    files = {p["key"]: SPACER_STEP for p in planned["parts"]}
    named, given, _ = takeapart.finishes_of(planned, {"plate": {"#b9b9b9": 1.0}, "pin": {"#1f1fb4": 1.0}})
    text = finishes.text(named, given, heading=("What a picture draws each part with.", "", "Yours to edit."))
    assert text.startswith("# What a picture draws each part with.\n#\n# Yours to edit.\nschema_version = 1\n")
    project_dir = tmp_path / "project"
    done = takeapart.write(project_dir, planned, files, ORIGIN, "machine.stp", "ab" * 32, finishes_text=text)
    assert done == {"written": 11, "unchanged": 0, "finishes": "written"}
    project = layout.load(project_dir)
    assert project.errors == [] and finishes.of(project.finishes, "pin")[1]["color"] == "#1f1fb4"
    assert [f for f in project.findings if f.startswith("finishes.toml")] == [
        "finishes.toml: 2 of 4 part(s) have no finish, and the file names no default: bracket, bracket-2"]
    # the same again changes nothing
    again = takeapart.write(project_dir, planned, files, ORIGIN, "machine.stp", "ab" * 32, finishes_text=text)
    assert again == {"written": 0, "unchanged": 11, "finishes": "unchanged"}
    # someone names a finish and gives the brackets one: the file is theirs, and is left as it is
    edited = text.replace("colour-1f1fb4", "blue-anodized") + 'bracket = "blue-anodized"\n'
    (project_dir / "finishes.toml").write_text(edited)
    kept = takeapart.write(project_dir, planned, files, ORIGIN, "machine.stp", "ab" * 32, finishes_text=text)
    assert kept["finishes"] == "kept" and (project_dir / "finishes.toml").read_text() == edited
    assert layout.load(project_dir).errors == []
    # a file without colours writes none
    assert "finishes" not in takeapart.write(tmp_path / "plain", planned, files, ORIGIN, "machine.stp", "ab" * 32)
    assert not (tmp_path / "plain" / "finishes.toml").exists()


def test_the_file_a_command_starts_is_one_the_validator_takes():
    named = {"clear": {"color": "#DFEEF5", "roughness": 0.1, "opacity": 0.3, "note": 'cast "sheet"'}, "steel": {"color": "#7f8286", "metallic": 1}}
    text = finishes.text(named, {"lid@open": "clear", "pin": "steel"})
    data = finishes.tomllib.loads(text)
    assert finishes.problems(data, {"lid@open": "part", "pin": "part"}) == []
    assert data["parts"] == {"lid@open": "clear", "pin": "steel"} and '"lid@open" = "clear"' in text
    assert finishes.finish(data, "clear") == {"color": "#dfeef5", "metallic": 0.0, "roughness": 0.1, "opacity": 0.3}
    assert data["finishes"]["clear"]["note"] == 'cast "sheet"' and data["finishes"]["steel"]["metallic"] == 1


def coloured_assembly(path):
    """A STEP file of an assembly with colours where a CAD system puts them: a part of one colour, a part of two
    solids each of its own colour with one face of a third, and a part without any."""
    from OCP.BRep import BRep_Builder
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.gp import gp_Pnt, gp_Trsf, gp_Vec
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.Quantity import Quantity_Color, Quantity_TOC_sRGB
    from OCP.STEPCAFControl import STEPCAFControl_Writer
    from OCP.STEPControl import STEPControl_AsIs
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDocStd import TDocStd_Document
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS_Compound
    from OCP.XCAFDoc import XCAFDoc_ColorSurf, XCAFDoc_DocumentTool

    document = TDocStd_Document(TCollection_ExtendedString("coloured"))
    shapes = XCAFDoc_DocumentTool.ShapeTool_s(document.Main())
    colours = XCAFDoc_DocumentTool.ColorTool_s(document.Main())

    def box(size, at=(0.0, 0.0, 0.0)):
        return BRepPrimAPI_MakeBox(gp_Pnt(*at), size, size, size).Shape()

    def paint(label, colour):
        colours.SetColor(label, Quantity_Color(*finishes.srgb(colour), Quantity_TOC_sRGB), XCAFDoc_ColorSurf)

    def named(label, name):
        TDataStd_Name.Set_s(label, TCollection_ExtendedString(name))
        return label

    root = named(shapes.NewShape(), "Coloured Thing")
    whole = named(shapes.AddShape(box(10.0), False), "Whole")
    paint(whole, "#b9b9b9")
    big, small = box(20.0), box(5.0, (40.0, 0.0, 0.0))
    both = TopoDS_Compound()
    BRep_Builder().MakeCompound(both)
    BRep_Builder().Add(both, big)
    BRep_Builder().Add(both, small)
    two = named(shapes.AddShape(both, False), "Two Tone")
    paint(shapes.AddSubShape(two, big), "#1f1fb4")                # 2400 mm2, of which one face is another colour
    paint(shapes.AddSubShape(two, small), "#ffdc40")              # 150 mm2
    paint(shapes.AddSubShape(two, TopExp_Explorer(big, TopAbs_FACE).Current()), "#cc2211")     # 400 mm2
    plain = named(shapes.AddShape(box(8.0), False), "Plain")
    for n, (label, x) in enumerate(((whole, 0.0), (two, 30.0), (plain, 90.0), (whole, 120.0))):
        move = gp_Trsf()
        move.SetTranslation(gp_Vec(x, 0.0, 0.0))
        named(shapes.AddComponent(root, label, TopLoc_Location(move)), f"ITEM:{n + 1}")
    shapes.UpdateAssemblies()
    writer = STEPCAFControl_Writer()
    writer.SetColorMode(True)
    writer.SetNameMode(True)
    assert writer.Transfer(document, STEPControl_AsIs) and writer.Write(str(path)) == IFSelect_RetDone


@with_kernel
def test_the_colours_of_a_file_become_the_finishes_of_the_project(tmp_path):
    whole = tmp_path / "coloured.step"
    coloured_assembly(whole)
    project_dir = tmp_path / "apart"
    origin = ["--retrieved", "2026-11-19", "--publishable", "yes", "--description", "made for a test, with colours"]
    out = take_apart(whole, project_dir, *origin)
    assert "[take_apart] exit status 0" in out, out
    assert "2 part(s) have a finish, 2 finish(es) in all" in out and "1 part(s) have more than one colour" in out, out
    assert "finishes.toml written" in out
    project = layout.load(project_dir)
    assert project.errors == []
    data = project.finishes
    assert data["parts"] == {"whole": "colour-b9b9b9", "two-tone": "colour-1f1fb4"}       # the colours as the file wrote them
    assert sorted(data["finishes"]) == ["colour-1f1fb4", "colour-b9b9b9"] and "default" not in data
    assert any("1 of 3 part(s) have no finish" in f and "plain" in f for f in project.findings)
    report = json.loads((project_dir / ".cache/take-apart/coloured-thing.json").read_text())
    rows = {row["key"]: row for row in report["finishes"]["parts"]}
    assert rows["whole"] == {"key": "whole", "finish": "colour-b9b9b9", "share": 1.0, "colours": 1}
    # the big solid's five other faces, of the surface of both solids: 2000 of 2550 mm2
    assert rows["two-tone"] == {"key": "two-tone", "finish": "colour-1f1fb4", "share": 0.784, "colours": 3}
    assert rows["plain"]["finish"] is None and report["finishes"]["parts_without_a_colour"] == ["plain"]
    assert report["finishes"]["file"] == "written"
    # no colour reaches a part's own file
    assert b"COLOUR_RGB" not in (project_dir / "designs/parts/two-tone/part.step").read_bytes()
    # the same file again changes nothing; a file someone has edited is theirs
    assert "finishes.toml unchanged" in take_apart(whole, project_dir, *origin)
    path = project_dir / "finishes.toml"
    path.write_text(path.read_text().replace("colour-b9b9b9", "aluminium"))
    out = take_apart(whole, project_dir, *origin)
    assert "finishes.toml is there and says something else: it is left as it is" in out, out
    assert "aluminium" in path.read_text() and layout.load(project_dir).errors == []


def freecad(tool, *args):
    proc = subprocess.run([FREECAD, str(REPO / "tools" / tool), "--pass", *map(str, args)], capture_output=True, text=True)
    return proc.stdout + proc.stderr


def take_apart(*args):
    proc = subprocess.run([sys.executable, "-B", str(REPO / "tools" / "take_apart.py"), *map(str, args)],
                          capture_output=True, text=True)
    return proc.stdout + proc.stderr


@with_kernel
def test_a_file_made_from_the_fixture_comes_apart_and_goes_together_again(project_copy, tmp_path):
    """The fixture's top assembly as one STEP file: nested, a part used four times, a sub-assembly used twice of
    which one instance is posed differently and so is a product of its own, names with spaces and brackets."""
    made = freecad("assembly_step.py", project_copy, "fixture-with-spacer", "--", "--out", tmp_path / "made", "--", "--frame", "own")
    assert "[assembly_step] exit status 0" in made, made
    whole = tmp_path / "made" / "fixture-with-spacer.step"
    project_dir = tmp_path / "apart"
    origin = ["--retrieved", "2026-11-18", "--publishable", "yes", "--description", "made from the layout fixture for a test"]
    out = take_apart(whole, project_dir, *origin)
    assert "[take_apart] exit status 0" in out, out
    assert "7 product(s) read; 3 part(s) and 4 assembly(ies)" in out and "6 occurrence(s), 6 solid(s)" in out
    project = layout.load(project_dir)
    assert project.errors == []
    assert sorted(c.key for c in project.of("designs", "part")) == ["base-plate", "pin", "spacer"]
    assert sorted(c.key for c in project.of("designs", "assembly")) == ["fixture-root", "fixture-with-spacer",
                                                                         "pin-pair", "pin-pair-2"]
    pose = {c.name: c.transform[0][3] for c in project.components["pin-pair-2"].children}
    assert pose == {"PIN:1": pytest.approx(-25.0), "PIN:2": pytest.approx(35.0)}     # the instance that was posed differently
    report = json.loads((project_dir / ".cache/take-apart/fixture-with-spacer.json").read_text())
    assert report["file"]["sha256"] == stepfile.sha256_file(whole) and report["parts_without_a_solid"] == []

    # measured, built again and held against the file it came from, solid for solid
    assert "[step_facts] exit status 0" in freecad("step_facts.py", project_dir)
    project = layout.load(project_dir)
    assert project.errors == [] and project.findings == []
    again = freecad("assembly_step.py", project_dir, "fixture-with-spacer", "--", "--frame", "own")
    assert "[assembly_step] exit status 0" in again, again
    same = freecad("compare_assembly_step.py", project_dir, "fixture-with-spacer", whole, tmp_path / "compare.json")
    assert "the same assembly: 6 of 6 solid(s)" in same and "[compare_assembly_step] exit status 0" in same, same

    # the same file again writes the same bytes
    kept = {p: p.read_bytes() for p in (project_dir / "designs").rglob("*") if p.is_file()}
    out = take_apart(whole, project_dir, *origin)
    assert "0 file(s) written, 10 unchanged" in out, out
    assert {p: p.read_bytes() for p in (project_dir / "designs").rglob("*") if p.is_file()} == kept


@with_kernel
def test_a_file_that_is_one_part_is_refused(tmp_path):
    out = take_apart(FIXTURE / "designs/parts/spacer/part.step", tmp_path / "apart", "--retrieved", "2026-11-18",
                     "--publishable", "yes", "--description", "one part")
    assert "REFUSED: the file is one part and no assembly" in out and "[take_apart] exit status 1" in out, out
    assert not (tmp_path / "apart").exists()
    out = take_apart(tmp_path / "nothing.step", tmp_path / "apart", "--retrieved", "2026-11-18", "--publishable", "yes",
                     "--description", "no file")
    assert "[take_apart] exit status 2" in out, out
