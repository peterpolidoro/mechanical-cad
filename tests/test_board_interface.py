"""A circuit board's interface written from its geometry file and its solid model (the CAD role with the OCP bindings):

    guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm -- python3 -B -m pytest -q tests/test_board_interface.py
"""
import importlib.util
import json
import shutil
import subprocess

import pytest
from conftest import REPO, write_json

from mechanical_cad import interfaces, layout
from mechanical_cad.cli import main

FREECAD = shutil.which("FreeCADCmd")
pytestmark = [pytest.mark.skipif(FREECAD is None, reason="FreeCADCmd is not on PATH (use the CAD role)"),
              pytest.mark.skipif(importlib.util.find_spec("OCP") is None,
                                 reason="the OCP bindings are not in this environment (make test-build123d)")]

# A board of 60 x 40 x 1.6 mm with a hole in each corner and two connectors on top, one of them of two solids, and a
# pin below. It is written where a board's exporter might put it: far from the origin of the file.
AT = (200.0, -150.0, 3.0)
MAKE_BOARD = '''
import sys
import FreeCAD as App
import Part

out = sys.argv[sys.argv.index("--pass") + 1]
at = App.Vector(%r, %r, %r)
board = Part.makeBox(60, 40, 1.6, App.Vector(-30, -20, 0))
for x, y in ((-26, 16), (26, 16), (26, -16), (-26, -16)):
    board = board.cut(Part.makeCylinder(1.6, 1.6, App.Vector(x, y, 0)))
usb = Part.makeBox(9, 7, 3.2, App.Vector(-28, -3.5, 1.6))
block = Part.makeBox(10, 8, 9, App.Vector(5, 6, 1.6))
plug_guide = Part.makeBox(4, 4, 12, App.Vector(8, 8, 1.6))
pin = Part.makeCylinder(0.5, 2.5, App.Vector(10, 10, -2.5))
whole = Part.makeCompound([board, usb, block, plug_guide, pin])
whole.translate(at)
whole.exportStep(out)
print("made", out)
''' % AT
GEOMETRY = {
    "generated_by": "a test", "board": "test-board", "units": "mm",
    "frame": {"origin": "centre of the board outline bounding box", "x_axis": "right", "y_axis": "up"},
    "outline": {"shape": "rounded_rectangle", "width_mm": 60.0, "height_mm": 40.0, "corner_radius_mm": 2.0,
                "bbox": {"min_x": -30.0, "min_y": -20.0, "max_x": 30.0, "max_y": 20.0}},
    "stackup": {"board_thickness_mm": 1.6},
    "mounting_holes": [{"reference": f"H{n}", "x_mm": x, "y_mm": y, "drill_diameter_mm": 3.2}
                       for n, (x, y) in enumerate(((-26, 16), (26, 16), (26, -16), (-26, -16)), 1)],
    "connectors": [
        {"reference": "J1", "value": "USB-C", "side": "top", "x_mm": -23.5, "y_mm": 0.0,
         "courtyard": {"min_x": -28.5, "min_y": -4.0, "max_x": -18.5, "max_y": 4.0}},
        {"reference": "J2", "value": "TERMINAL", "side": "top", "x_mm": 10.0, "y_mm": 10.0,
         "courtyard": {"min_x": 4.5, "min_y": 5.5, "max_x": 15.5, "max_y": 14.5}}],
}
DATUMS = {"connectors": [{"reference": "J2", "mating_direction": "+z", "plug_series": "a plug of the series"}]}
PART = "designs/parts/test-board"


def freecad(script, *args):
    proc = subprocess.run([FREECAD, str(script), "--pass", *map(str, args)], capture_output=True, text=True)
    return proc.stdout + proc.stderr


@pytest.fixture
def board(tmp_path):
    """A project with the board in it as a supplied part, measured; and the paths of its geometry and datum files."""
    (tmp_path / "make_board.py").write_text(MAKE_BOARD, encoding="utf-8")
    assert "made" in freecad(tmp_path / "make_board.py", tmp_path / "board.step")
    project = tmp_path / "project"
    (project / "designs" / "parts").mkdir(parents=True)
    assert main(["add-supplied", str(project), "test-board", str(tmp_path / "board.step"), "--name", "Test board",
                 "--repository", "https://example.org/test-board.git", "--commit", "abc1234", "--path", "board.step",
                 "--retrieved", "2026-11-17", "--publishable", "yes"]) == 0
    assert "exit status 0" in freecad(REPO / "tools" / "step_facts.py", project)
    write_json(tmp_path / "geometry.json", GEOMETRY)
    write_json(tmp_path / "datums.json", DATUMS)
    return project, tmp_path / "geometry.json", tmp_path / "datums.json"


def test_the_interface_of_a_board_is_written_from_its_files_and_its_model(board, capsys):
    project, geometry, datums = board
    out = freecad(REPO / "tools" / "board_interface.py", project / PART, geometry, datums)
    assert "[board_interface] exit status 0" in out, out
    assert "its frame at (200.000, -150.000) of the file's" in out
    assert "parts reach 12.000 mm above the top face and 2.500 mm below the bottom face" in out
    data = json.loads((project / PART / "interface.json").read_text())
    assert interfaces.problems(data, "test-board") == []
    top = AT[2] + 1.6
    assert interfaces.frame(data, "board") == [[1, 0, 0, 200.0], [0, 1, 0, -150.0], [0, 0, 1, top], [0, 0, 0, 1]]
    assert [f["id"] for f in data["features"]] == ["outline", "top", "bottom", "h1", "h2", "h3", "h4", "j1", "j2",
                                                   "parts-above", "parts-below"]
    outline = interfaces.feature(data, "outline")
    assert outline["corner_radius"] == 2.0 and outline["point"] == [200.0, -150.0, top]
    h1 = interfaces.feature(data, "h1")
    assert h1 == {"id": "h1", "kind": "hole", "center": [174.0, -134.0, top], "axis": [0.0, 0.0, 1.0], "diameter": 3.2,
                  "depth": 1.6, "through": True, "reference": "H1"}
    # a port is the courtyard from the board to the top of the solids over it; J2 is two solids, the taller counts
    j1, j2 = interfaces.feature(data, "j1"), interfaces.feature(data, "j2")
    assert j1["box"] == {"min": [171.5, -154.0, top], "max": [181.5, -146.0, pytest.approx(top + 3.2)]}
    assert j2["box"]["max"][2] == pytest.approx(top + 12.0)
    assert j2["direction"] == [0.0, 0.0, 1.0] and j2["accepts"] == "a plug of the series" and "taken as" not in j2["note"]
    assert "do not say from where a plug comes" in j1["note"] and "accepts" not in j1
    assert interfaces.feature(data, "parts-below")["box"]["min"][2] == pytest.approx(AT[2] - 2.5)

    # written again it is as it was; measured again, the holes are held to the solid
    assert "interface.json is as it was" in freecad(REPO / "tools" / "board_interface.py", project / PART, geometry, datums)
    assert main(["check", str(project)]) == 1 and "not looked at" in capsys.readouterr().out
    assert "1 measured" in freecad(REPO / "tools" / "step_facts.py", project)
    assert main(["check", str(project)]) == 0
    assert capsys.readouterr().out.count("PASS") == 4
    assert layout.load(project).errors == []


def test_a_model_that_is_not_the_geometry_files_board_is_refused(board):
    project, geometry, _ = board
    tool = REPO / "tools" / "board_interface.py"

    def with_geometry(change):
        data = json.loads(json.dumps(GEOMETRY))
        change(data)
        write_json(geometry, data)
        return freecad(tool, project / PART, geometry)

    out = with_geometry(lambda g: g["outline"]["bbox"].update(max_x=35.0))
    assert "no solid of the file is 65.0 x 40.0 mm" in out and "[board_interface] exit status 1" in out
    out = with_geometry(lambda g: g["mounting_holes"][0].update(x_mm=-20.0))
    assert "the board is solid where the geometry file has the mounting hole(s) H1" in out
    out = with_geometry(lambda g: [c["courtyard"].update(min_y=-19.0, max_y=-15.0) for c in g["connectors"]])
    assert "no solid stands over the courtyard of 2 of 2 connectors" in out
    out = with_geometry(lambda g: g.update(units="in"))
    assert "expected mm" in out
    assert not (project / PART / "interface.json").exists()
    assert "not a supplied part" in freecad(tool, project / "designs" / "parts", geometry)
