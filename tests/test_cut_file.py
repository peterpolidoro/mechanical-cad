"""tools/cut_file.py: what a drawing's lines, arcs and circles close, without a kernel; and a plate's cut file
and a solid's flat pattern written where build123d is (make test-build123d)."""
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys

import pytest
from conftest import REPO, write_json

TOOL = REPO / "tools" / "cut_file.py"
spec = importlib.util.spec_from_file_location("cut_file_tool", TOOL)
cut_file = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cut_file)

with_build123d = pytest.mark.skipif(importlib.util.find_spec("build123d") is None,
                                    reason="build123d is not in this environment (make test-build123d)")
FREECAD = shutil.which("FreeCADCmd")


def run(*args, seed=None):
    """The tool's output. `seed` fixes Python's hash seed for that run; without it Python picks one."""
    env = None if seed is None else dict(os.environ, PYTHONHASHSEED=str(seed))
    done = subprocess.run([sys.executable, "-B", str(TOOL), *map(str, args)], capture_output=True, text=True, env=env)
    return done.stdout + done.stderr


def rectangle(x0, y0, x1, y1):
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return [("line", a, b) for a, b in zip(corners, corners[1:] + corners[:1])]


def rounded(w, h, r):
    """A rectangle about the origin with its corners rounded: four lines and four arcs, as a DXF file has them."""
    a, b = w / 2, h / 2
    return [("line", (-a + r, -b), (a - r, -b)), ("arc", (a - r, -b + r), r, 270.0, 0.0),
            ("line", (a, -b + r), (a, b - r)), ("arc", (a - r, b - r), r, 0.0, 90.0),
            ("line", (a - r, b), (-a + r, b)), ("arc", (-a + r, b - r), r, 90.0, 180.0),
            ("line", (-a, b - r), (-a, -b + r)), ("arc", (-a + r, -b + r), r, 180.0, 270.0)]


def test_lines_close_a_loop_whatever_their_order_and_direction():
    facts = cut_file.drawing_facts(rectangle(0, 0, 30, 20))
    assert facts["closed"] and facts["loops"] == 1 and facts["holes"] == 0 and facts["left_over"] == 0
    assert facts["area_mm2"] == pytest.approx(600.0) and facts["cut_length_mm"] == pytest.approx(100.0)
    assert facts["extent_mm"] == pytest.approx([30.0, 20.0]) and facts["min_mm"] == pytest.approx([0.0, 0.0])
    a, b, c, d = rectangle(0, 0, 30, 20)
    turned = [c, ("line", b[2], b[1]), a, ("line", d[2], d[1])]                # shuffled, two of them backwards
    assert cut_file.drawing_facts(turned)["area_mm2"] == pytest.approx(600.0)
    assert cut_file.drawing_facts(turned)["closed"]


def test_arcs_are_measured_as_arcs():
    facts = cut_file.drawing_facts(rounded(40.0, 30.0, 5.0))
    assert facts["closed"] and facts["loops"] == 1 and facts["pieces"] == 8
    assert facts["area_mm2"] == pytest.approx(40 * 30 - (4 - math.pi) * 25, rel=1e-12)
    assert facts["cut_length_mm"] == pytest.approx(2 * (30 + 20) + 2 * math.pi * 5, rel=1e-12)
    assert facts["extent_mm"] == pytest.approx([40.0, 30.0], abs=1e-12)
    # two half circles are a circle, and an arc reaches as far as the circle does between its ends
    halves = [("arc", (3.0, 4.0), 10.0, 20.0, 200.0), ("arc", (3.0, 4.0), 10.0, 200.0, 20.0)]
    facts = cut_file.drawing_facts(halves)
    assert facts["closed"] and facts["area_mm2"] == pytest.approx(math.pi * 100, rel=1e-12)
    assert facts["extent_mm"] == pytest.approx([20.0, 20.0], abs=1e-12)
    assert facts["min_mm"] == pytest.approx([-7.0, -6.0], abs=1e-12)
    # an arc of a full turn is a circle too
    assert cut_file.drawing_facts([("arc", (0.0, 0.0), 2.0, 90.0, 90.0)])["area_mm2"] == pytest.approx(4 * math.pi)


def test_holes_are_taken_off_the_outline():
    plate = rounded(100.0, 60.0, 3.0) + [("circle", (-25.0, 0.0), 10.0), ("circle", (25.0, 0.0), 10.0)]
    facts = cut_file.drawing_facts(plate)
    assert facts["closed"] and facts["loops"] == 3 and facts["holes"] == 2
    assert facts["area_mm2"] == pytest.approx(6000 - (4 - math.pi) * 9 - 2 * math.pi * 100, rel=1e-12)
    assert facts["cut_length_mm"] == pytest.approx(2 * (94 + 54) + 2 * math.pi * 3 + 2 * 2 * math.pi * 10, rel=1e-12)


def test_a_drawing_with_a_gap_or_a_branch_is_not_closed():
    open_box = rectangle(0, 0, 30, 20)[:3]
    facts = cut_file.drawing_facts(open_box)
    assert not facts["closed"] and facts["loops"] == 0 and facts["left_over"] == 3
    # a closed outline with a line hanging on one corner: the corner has three ends, and nothing there is a loop
    branch = rectangle(0, 0, 30, 20) + [("line", (0.0, 0.0), (-5.0, -5.0))]
    assert not cut_file.drawing_facts(branch)["closed"]
    # a hair's breadth is a gap; less than the joining distance is not
    gap = rectangle(0, 0, 30, 20)
    gap[0] = ("line", (0.001, 0.0), (30.0, 0.0))
    assert not cut_file.drawing_facts(gap)["closed"]
    gap[0] = ("line", (1e-8, 0.0), (30.0, 0.0))
    assert cut_file.drawing_facts(gap)["closed"]
    assert not cut_file.drawing_facts([])["closed"]
    # a closed loop beside an open one: the drawing is not closed, and the loop is still counted
    facts = cut_file.drawing_facts(rectangle(0, 0, 30, 20) + [("line", (50.0, 0.0), (60.0, 0.0))])
    assert not facts["closed"] and facts["loops"] == 1 and facts["left_over"] == 1


@with_build123d
def test_only_a_plate_cut_square_through_is_a_plate():
    from build123d import Box, Cylinder, Pos, chamfer

    plate = Box(40, 30, 3) - Cylinder(5, 10)
    face, other, thickness = cut_file.plate_of(plate, plate.volume)
    assert thickness == pytest.approx(3.0) and face.area == pytest.approx(1200 - 25 * math.pi)
    assert face.normal_at(face.center()).Z == pytest.approx(1.0)                # drawn as seen from +Z
    assert other.normal_at(other.center()).Z == pytest.approx(-1.0)
    pocket = Box(40, 30, 3) - Pos(0, 0, 1) * Box(10, 10, 2)
    with pytest.raises(ValueError, match="not cut from sheet in one pass"):
        cut_file.plate_of(pocket, pocket.volume)
    edge_broken = chamfer(Box(40, 30, 3).edges().group_by()[-1], 0.5)
    with pytest.raises(ValueError, match="not cut from sheet in one pass"):
        cut_file.plate_of(edge_broken, edge_broken.volume)
    # a plate that stands on edge is still a plate: it is drawn in its own plane
    upright = Pos(0, 0, 20) * Box(3, 40, 30)
    face, _, thickness = cut_file.plate_of(upright, upright.volume)
    assert thickness == pytest.approx(3.0) and face.normal_at(face.center()).X == pytest.approx(1.0)


@with_build123d
def test_the_cut_file_of_a_ring_is_two_circles_and_has_the_solids_area(project_copy):
    out = run(project_copy, "spacer", seed=0)
    assert "[cut_file] exit status 0" in out and "NOT" not in out, out
    record = json.loads((project_copy / ".cache/cut/spacer.cut.json").read_text())
    assert record["passed"] and all(record["checks"].values())
    drawing = record["drawing"]
    assert drawing["loops"] == 2 and drawing["holes"] == 1 and drawing["closed"] and drawing["other_entities"] == {}
    assert drawing["area_mm2"] == pytest.approx(math.pi * (10.0 ** 2 - 5.25 ** 2), rel=1e-9)
    assert drawing["cut_length_mm"] == pytest.approx(2 * math.pi * (10.0 + 5.25), rel=1e-9)
    assert record["plate"]["thickness_mm"] == pytest.approx(5.0)
    assert record["frame_in_part"]["x"] == pytest.approx([1.0, 0.0, 0.0])
    dxf = project_copy / ".cache/cut/spacer.dxf"
    first = dxf.read_bytes()
    pieces, other, unit = cut_file.read_dxf(dxf)
    assert sorted(p[0] for p in pieces) == ["circle", "circle"] and other == {} and unit == 4
    # The same part again gives the same two files, byte for byte, whatever order Python's sets come in: the
    # DXF library writes some records from a set, and under these two hash seeds their order differed.
    again = run(project_copy, "spacer", seed=4)
    assert dxf.read_bytes() == first, again
    assert json.loads((project_copy / ".cache/cut/spacer.cut.json").read_text()) == record
    assert "has no part 'nothing'" in run(project_copy, "nothing")


# ---- a flat pattern: an outline to cut and lines to fold along -------------------------------------------------

def polygon(*corners):
    return [("line", a, b) for a, b in zip(corners, corners[1:] + corners[:1])]


def test_the_options_of_a_pattern():
    assert cut_file.options(["PROJECT", "KEY"]) == (["PROJECT", "KEY"], None, False, "-z")
    assert cut_file.options(["PROJECT", "KEY", "--pattern", "--root", "+X", "--out", "DIR"]) == (["PROJECT", "KEY"], "DIR", True, "+x")
    for wrong in (["PROJECT", "KEY", "--root", "up"], ["PROJECT", "KEY", "--tabs"], ["PROJECT"]):
        with pytest.raises(SystemExit):
            cut_file.options(wrong)


def test_a_point_is_inside_what_the_lines_enclose():
    ell = polygon((0, 0), (30, 0), (30, 10), (10, 10), (10, 20), (0, 20))
    assert cut_file.inside((5, 15), ell) and cut_file.inside((20, 5), ell) and cut_file.inside((5, 10), ell)
    assert not cut_file.inside((20, 15), ell) and not cut_file.inside((-1, 5), ell) and not cut_file.inside((31, 5), ell)
    # a ray through a corner of the outline is counted once, whichever way the outline was drawn
    backwards = [("line", end, start) for _, start, end in ell]
    assert cut_file.inside((5, 10), backwards) and not cut_file.inside((20, 10.001), ell)
    assert not cut_file.inside((5, 5), [])


def test_fold_lines_that_are_not_where_a_fold_is_are_found():
    # a sheet with a slot 1 mm wide cut into it from above
    sheet = polygon((0, 0), (30, 0), (30, 20), (12, 20), (12, 5), (11, 5), (11, 20), (0, 20))
    good = [("line", (5.0, 0.0), (5.0, 20.0)), ("line", (0.0, 3.0), (30.0, 3.0)), ("line", (11.0, 5.0), (0.0, 0.0))]
    assert cut_file.folds_astray(sheet, good) == []
    astray = cut_file.folds_astray(sheet, [
        good[0],
        ("line", (5.0, 2.0), (5.0, 20.0)),                      # begins inside the sheet
        ("line", (30.0, 10.0), (40.0, 10.0)),                   # leaves it
        ("line", (11.0, 20.0), (12.0, 20.0)),                   # bridges the slot: on the outline at both ends, and outside
        ("line", (0.0, 10.0), (30.0, 10.0)),                    # from side to side, through the slot
        ("arc", (15.0, 0.0), 5.0, 0.0, 180.0),
        ("line", (0.0, 0.0), (30.0, 8.0)),                      # from a corner to the far side, under the slot: a fold
    ])
    assert astray == [(1, "does not run from the outline to the outline"), (2, "does not run from the outline to the outline"),
                      (3, "is not inside the outline"), (4, "crosses the outline"), (5, "is not a straight line")]
    assert cut_file.folds_astray([], good) == [(k, "does not run from the outline to the outline") for k in range(3)]


@with_build123d
def test_only_a_convex_solid_with_flat_faces_is_a_polyhedron():
    from build123d import Axis, Box, Cylinder, Pos, Rot, fillet

    from mechanical_cad.shapes import forms, polyhedra

    p = polyhedra.named("truncated-octahedron", 30.0)
    solid = Pos(200, -150, 40) * Rot(30, 20, 10) * forms.solid(p)        # anywhere, turned any way
    found = cut_file.polyhedron_of(solid, "moved", solid.volume, solid.area)
    assert found.counts == (24, 36, 14) and found.volume == pytest.approx(p.volume, rel=1e-9)
    assert found.area == pytest.approx(p.area, rel=1e-9) and found.edge_length == pytest.approx(30.0, rel=1e-9)
    box = Box(40, 30, 20)
    assert cut_file.polyhedron_of(box, "box", box.volume, box.area).counts == (8, 12, 6)
    # round edges: every corner is a corner of the convex solid on them, which is smaller than the part
    rounded = fillet(box.edges().filter_by(Axis.Z), 5)
    with pytest.raises(ValueError, match="the convex solid on its 16 corners has a volume of 23000.000 mm3 .* and the part 23570.796"):
        cut_file.polyhedron_of(rounded, "rounded", rounded.volume, rounded.area)
    drilled = box - Cylinder(5, 30)
    with pytest.raises(ValueError, match="corners are not corners of the convex solid on them"):
        cut_file.polyhedron_of(drilled, "drilled", drilled.volume, drilled.area)
    hollow = forms.shell(p, 3.0)
    with pytest.raises(ValueError, match="corners are not corners of the convex solid on them"):
        cut_file.polyhedron_of(hollow, "hollow", hollow.volume, hollow.area)


SOLID = '''"""A truncated octahedron as a solid, resting on a hexagon: what a sheet is folded into."""


def build(parameters):
    from mechanical_cad.shapes import forms, polyhedra

    p = polyhedra.named("truncated-octahedron", edge=parameters["edge_mm"])
    return forms.solid(p.resting_on(p.faces_with(6)[0]))
'''


@with_build123d
@pytest.mark.skipif(FREECAD is None, reason="FreeCADCmd is not on PATH (use the CAD role)")
def test_the_flat_pattern_of_a_solid_is_an_outline_and_fold_lines_and_is_the_same_file_every_time(project_copy):
    from mechanical_cad.shapes import polyhedra

    part = project_copy / "designs" / "parts" / "folded"
    part.mkdir()
    (part / "build.py").write_text(SOLID, encoding="utf-8")
    write_json(part / "parameters.json", {"name": "Folded", "edge_mm": 30.0})
    built = subprocess.run([FREECAD, str(REPO / "tools" / "build_part.py"), "--pass", str(part)], capture_output=True, text=True)
    assert "[build_part] exit status 0" in built.stdout + built.stderr, built.stdout + built.stderr

    out = run(project_copy, "folded", "--pattern", seed=0)
    assert "[cut_file] exit status 0" in out and "NOT" not in out, out
    record = json.loads((project_copy / ".cache/cut/folded.pattern.json").read_text())
    assert record["passed"] and all(record["checks"].values())
    assert set(record["checks"]) == {"polyhedron", "closed", "area", "length", "folds", "extent", "unit", "layers"}
    solid = polyhedra.named("truncated-octahedron", 30.0)
    drawing, pattern = record["drawing"], record["pattern"]
    # the outline: one closed loop round the area of the fourteen faces, as long as the 23 cut edges twice over
    assert drawing["loops"] == 1 and drawing["holes"] == 0 and drawing["closed"] and drawing["other_entities"] == {}
    assert drawing["area_mm2"] == pytest.approx(solid.area, rel=1e-9) and drawing["pieces"] == 46
    assert drawing["cut_length_mm"] == pytest.approx(2 * 23 * 30.0, rel=1e-9)
    assert drawing["min_mm"] == pytest.approx([0.0, 0.0], abs=1e-9) and drawing["extent_mm"] == pytest.approx(pattern["size_mm"])
    # the folds: thirteen edges, each bent by what is left of 180 degrees between a hexagon and a square or two hexagons
    assert drawing["fold_lines"] == 13 and drawing["fold_length_mm"] == pytest.approx(13 * 30.0, rel=1e-9)
    assert (pattern["faces"], pattern["cut_edges"], len(pattern["folds"])) == (14, 23, 13)
    assert {round(fold["angle_deg"], 2) for fold in pattern["folds"]} == {54.74, 70.53}
    assert record["polyhedron"]["volume_mm3"] == pytest.approx(solid.volume, rel=1e-9)
    assert record["volume_relative_difference"] < 1e-9 and len(pattern["without"]) == 3
    # the face it stands on is laid first, with its first edge along the drawing's x
    root = pattern["root"]
    assert root["towards"] == "-z" and {round(corner[2], 6) for corner in root["corners_in_part_mm"]} == {0.0}
    first, second = root["corners_in_drawing_mm"][:2]
    assert second[0] - first[0] == pytest.approx(30.0) and second[1] == pytest.approx(first[1])
    # read back: two layers and nothing else, in millimetres
    dxf = project_copy / ".cache/cut/folded.pattern.dxf"
    cut, _, unit = cut_file.read_dxf(dxf, "cut")
    folds, _, _ = cut_file.read_dxf(dxf, "fold")
    everything, other, _ = cut_file.read_dxf(dxf)
    assert {piece[0] for piece in everything} == {"line"} and other == {} and unit == 4
    assert (len(cut), len(folds), len(everything)) == (46, 13, 59)
    assert cut_file.drawing_facts(cut)["closed"] and not cut_file.drawing_facts(folds)["closed"]
    assert cut_file.folds_astray(cut, folds) == []
    assert cut_file.folds_astray(cut, folds + [("line", (0.0, 0.0), (5.0, 5.0))]) == [(13, "does not run from the outline to the outline")]
    # the same part again gives the same two files, whatever order Python's sets come in
    first_bytes = dxf.read_bytes()
    again = run(project_copy, "folded", "--pattern", seed=4)
    assert dxf.read_bytes() == first_bytes, again
    assert json.loads((project_copy / ".cache/cut/folded.pattern.json").read_text()) == record
    # laid out from the face on top instead: another drawing of the same solid, checked the same way
    out = run(project_copy, "folded", "--pattern", "--root", "+z", "--out", project_copy / "other")
    assert "[cut_file] exit status 0" in out and "NOT" not in out, out
    other_record = json.loads((project_copy / "other/folded.pattern.json").read_text())
    assert other_record["passed"] and other_record["pattern"]["root"]["towards"] == "+z"
    assert {round(corner[2], 3) for corner in other_record["pattern"]["root"]["corners_in_part_mm"]} == {round(30.0 * math.sqrt(6), 3)}
    assert other_record["drawing"]["area_mm2"] == pytest.approx(solid.area, rel=1e-9)
    # a plate is cut, not folded, and its pattern does not get in the way of its cut file; a ring has no pattern
    assert not (project_copy / ".cache/cut/folded.dxf").exists()
    out = run(project_copy, "spacer", "--pattern")
    assert "NOT A CONVEX SOLID WITH FLAT FACES" in out and "[cut_file] exit status 1" in out
    assert not (project_copy / ".cache/cut/spacer.pattern.dxf").exists()
    out = run(project_copy, "folded")
    assert "NOT A PLATE CUT SQUARE THROUGH" in out and "[cut_file] exit status 1" in out
