"""tools/section.py: how a sheet lies in the model and what the drawing is, without a kernel; and sections of
the fixture where build123d is (make test-build123d)."""
import importlib.util
import json
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest
from conftest import REPO

TOOL = REPO / "tools" / "section.py"
spec = importlib.util.spec_from_file_location("section_tool", TOOL)
section = importlib.util.module_from_spec(spec)
spec.loader.exec_module(section)

with_build123d = pytest.mark.skipif(importlib.util.find_spec("build123d") is None,
                                    reason="build123d is not in this environment (make test-build123d)")
SVG = "{http://www.w3.org/2000/svg}"


def run(*args):
    done = subprocess.run([sys.executable, "-B", str(TOOL), *map(str, args)], capture_output=True, text=True)
    return done.stdout + done.stderr


def test_a_sheet_lies_in_the_model_as_whoever_looks_at_the_cut_sees_it():
    # standing at +Y and looking back at the plane, with Z up, X runs to the left
    assert section.sheet_axes(1, 1, "+Z") == ((-1, 0, 0), (0, 0, 1), (0, 1, 0))
    assert section.sheet_axes(1, -1, "+Z") == ((1, 0, 0), (0, 0, 1), (0, -1, 0))
    assert section.sheet_axes(0, 1, "+Z") == ((0, 1, 0), (0, 0, 1), (1, 0, 0))
    # a plane square to the up axis is a plan: seen from above, X to the right and Y up
    assert section.sheet_axes(2, 1, "+Z") == ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    # and where the up axis is the one the plane is square to, another is taken to point up
    assert section.sheet_axes(1, 1, "+Y") == ((-1, 0, 0), (0, 0, 1), (0, 1, 0))
    for axis in range(3):
        for side in (1, -1):
            for up in ("+Z", "+Y", "-X"):
                right, upward, towards = section.sheet_axes(axis, side, up)
                cross = (right[1] * upward[2] - right[2] * upward[1], right[2] * upward[0] - right[0] * upward[2],
                         right[0] * upward[1] - right[1] * upward[0])
                assert cross == towards                              # right, up, towards: a right hand


def test_the_drawing_is_an_svg_in_millimetres_with_a_scale_and_a_legend():
    square = [(0.0, 0.0), (30.0, 0.0), (30.0, 20.0), (0.0, 20.0)]
    hole = [(10.0, 5.0), (20.0, 5.0), (20.0, 15.0), (10.0, 15.0)]
    text = section.svg("thing: section", ["The plane Y = 0 mm, seen from +Y."],
                       [("plate & more", (0.2, 0.4, 0.6), [[square, hole]]), ("pin", (1.0, 0.5, 0.0), [[hole]])],
                       (0.0, 0.0), (30.0, 20.0))
    root = ET.fromstring(text)
    assert root.get("width").endswith("mm") and root.get("height").endswith("mm")
    width, height = (float(v) for v in root.get("viewBox").split()[2:])
    assert root.get("width") == f"{width:.3f}mm"                     # one unit of the drawing is one millimetre
    paths = [p for p in root.iter(SVG + "path") if p.get("fill") != "none"]
    assert [p.get("fill") for p in paths] == ["#336699", "#ff8000"] and paths[0].get("fill-rule") == "evenodd"
    assert paths[0].get("d").count("M ") == 2 and paths[0].get("d").count("Z") == 2      # the outline and its hole
    assert paths[0].find(SVG + "title").text == "plate & more"
    words = [t.text for t in root.iter(SVG + "text")]
    assert "thing: section" in words and "10 mm" in words and "plate & more" in words and "pin" in words
    assert "30.00" in words and "20.00" in words                     # how wide and how high all of it is
    # y is turned over: what is highest in the model is nearest the top of the sheet
    first = paths[0].get("d").split()[1].split(",")
    assert float(first[1]) > float(paths[0].get("d").split("L")[2].split()[0].split(",")[1])


def test_a_part_that_lets_light_through_is_drawn_paler():
    square = [(0.0, 0.0), (30.0, 0.0), (30.0, 20.0), (0.0, 20.0)]
    text = section.svg("thing: section", [], [("plate: aluminium", (0.2, 0.4, 0.6), [[square]], 1.0),
                                               ("window: clear", (1.0, 0.5, 0.0), [[square]], 0.4)], (0.0, 0.0), (30.0, 20.0))
    root = ET.fromstring(text)
    paths = [p for p in root.iter(SVG + "path") if p.get("fill") != "none"]
    assert [(p.get("fill"), p.get("fill-opacity")) for p in paths] == [("#336699", None), ("#ff8000", "0.4")]
    swatches = [r for r in root.iter(SVG + "rect") if r.get("stroke")]
    assert [(r.get("fill"), r.get("fill-opacity")) for r in swatches] == [("#336699", None), ("#ff8000", "0.4")]


@with_build123d
def test_a_section_is_filled_with_the_finishes_the_project_gives_its_parts(project_copy):
    out = run(project_copy, "fixture-with-spacer", "--cut", "-y=12", "--finish")
    assert "[section] exit status 0" in out and "no finish" not in out, out
    pictures = project_copy / ".cache" / "pictures"
    record = json.loads((pictures / "fixture-with-spacer-section-minus-y-finish.json").read_text())
    assert [(part["name"], part["finish"]) for part in record["parts"]] == [
        ("base-plate", "aluminium"), ("pin", "grey-plastic"), ("spacer", "clear-blue")]
    root = ET.fromstring((pictures / "fixture-with-spacer-section-minus-y-finish.svg").read_text())
    fills = {p.find(SVG + "title").text: (p.get("fill"), p.get("fill-opacity")) for p in root.iter(SVG + "path") if p.get("fill") != "none"}
    assert fills == {"base-plate: aluminium": ("#c8cacd", None), "pin: grey-plastic": ("#8a8d91", None),
                     "spacer: clear-blue": ("#2f6fd0", "0.4")}
    assert "spacer: clear-blue" in {t.text for t in root.iter(SVG + "text")}          # the legend names the finish
    # the drawing that tells the parts apart is another file, and has no finish in its record
    out = run(project_copy, "fixture-with-spacer", "--cut", "-y=12")
    assert "[section] exit status 0" in out, out
    assert "finish" not in json.loads((pictures / "fixture-with-spacer-section-minus-y.json").read_text())["parts"][0]
    # a plane that only touches a solid cuts nothing of it: the pins are 5 mm round their axes at y = 15
    out = run(project_copy, "fixture-with-spacer", "--cut", "-y=10", "--finish")
    assert "[section] exit status 0" in out and "[section] pin" not in out and "[section] base-plate" in out, out
    # a part the project gives no finish is drawn plain, named in the legend as having none, and null in the record
    text = (project_copy / "finishes.toml").read_text().replace('default = "grey-plastic"', "")
    (project_copy / "finishes.toml").write_text(text)
    out = run(project_copy, "fixture-with-spacer", "--cut", "-y=12", "--finish")
    assert "1 part(s) have no finish and are drawn plain: pin" in out, out
    record = json.loads((pictures / "fixture-with-spacer-section-minus-y-finish.json").read_text())
    assert [part["finish"] for part in record["parts"]] == ["aluminium", None, "clear-blue"]
    root = ET.fromstring((pictures / "fixture-with-spacer-section-minus-y-finish.svg").read_text())
    assert "pin: no finish" in {t.text for t in root.iter(SVG + "text")}
    (project_copy / "finishes.toml").unlink()
    assert "finishes.toml is not there" in run(project_copy, "fixture-with-spacer", "--cut", "-y=12", "--finish")


@with_build123d
def test_the_section_of_a_ring_is_two_rectangles_and_has_their_area(project_copy):
    out = run(project_copy, "spacer", "--cut", "+y=0")
    assert "[section] exit status 0" in out and "spacer: 47.500 mm2 in 2 piece(s)" in out, out
    pictures = project_copy / ".cache" / "pictures"
    record = json.loads((pictures / "spacer-section-plus-y.json").read_text())
    assert record["plane"] == {"axis": "Y", "at_mm": 0.0, "seen_from": "+Y"}
    assert record["parts"] == [{"name": "spacer", "area_mm2": pytest.approx(47.5), "pieces": 2}]   # (20 - 10.5) / 2 x 5, twice
    assert record["sheet_in_model"]["right"] == [-1, 0, 0] and record["sheet_in_model"]["up"] == [0, 0, 1]
    assert record["extent_on_sheet_mm"]["max"][0] - record["extent_on_sheet_mm"]["min"][0] == pytest.approx(20.0)
    drawing = pictures / "spacer-section-plus-y.svg"
    first = drawing.read_bytes()
    root = ET.fromstring(first)
    assert len([p for p in root.iter(SVG + "path") if p.get("fill") != "none"]) == 2
    run(project_copy, "spacer", "--cut", "+y=0")
    assert drawing.read_bytes() == first                              # the same part, the same drawing
    # a plan of the ring is one piece with a hole, and its area is the ring's
    out = run(project_copy, "spacer", "--cut", "+z")
    assert "spacer: 227.569 mm2 in 1 piece(s)" in out, out
    assert "cuts nothing" in run(project_copy, "spacer", "--cut", "+x=500")
    assert "--cut" in run(project_copy, "spacer")                     # the plane has to be named


@with_build123d
def test_an_assembly_s_section_names_its_parts(project_copy):
    out = run(project_copy, "fixture-with-spacer", "--cut", "-y")
    assert "[section] exit status 0" in out, out
    record = json.loads((project_copy / ".cache/pictures/fixture-with-spacer-section-minus-y.json").read_text())
    names = [part["name"] for part in record["parts"]]
    assert names == sorted(names) and set(names) <= {"base-plate", "pin", "spacer"} and "base-plate" in names
    root = ET.fromstring((project_copy / ".cache/pictures/fixture-with-spacer-section-minus-y.svg").read_text())
    assert set(names) <= {t.text for t in root.iter(SVG + "text")}
    assert not (project_copy / ".cache" / "assemblies").exists()     # nothing was built for it
    assert "has no component 'washer'" in run(project_copy, "washer", "--cut", "+y")
