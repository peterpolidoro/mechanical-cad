"""tools/cut_file.py: what a drawing's lines, arcs and circles close, without a kernel; and a plate's cut file,
with arcs and with an allowance for the width of the cut, and a solid's flat pattern, closed or with faces left
open, written where build123d is (make test-build123d)."""
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import types

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


def measured(shape):
    """What the tool reads of a part's records, for a shape of build123d that is in no project."""
    return types.SimpleNamespace(facts={"volume_mm3": shape.volume, "area_mm2": shape.area}, step_sha256="-", step_data_sha256="-")


def kinds(pieces):
    return {kind: sum(1 for piece in pieces if piece[0] == kind) for kind in ("line", "arc", "circle")}


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


# ---- arcs, and an allowance for the width of the cut -----------------------------------------------------------

def slotted_plate():
    """A plate 80 x 50 x 3 with corners rounded with 6, two holes of 4.2, a slot 30 x 5 with round ends, a window
    16 x 9 turned 20 degrees, and a slot 4 wide with a round end cut 7 deep in from the side towards +x."""
    from build123d import Box, Cylinder, Pos, RectangleRounded, Rot, SlotCenterToCenter, extrude

    plate = extrude(RectangleRounded(80, 50, 6), amount=3)
    for x, y in ((-32, -17), (32, 17)):
        plate -= Pos(x, y, 0) * Cylinder(2.1, 9)
    plate -= Pos(-10, 8, -3) * extrude(SlotCenterToCenter(25, 5), amount=9)
    plate -= Pos(12, -10, 0) * Rot(0, 0, 20) * Box(16, 9, 9)
    return plate - Pos(40, 5, -3) * extrude(SlotCenterToCenter(10, 4), amount=9)


SLOTTED_AREA = 80 * 50 - (4 - math.pi) * 36 - 2 * math.pi * 2.1 ** 2 - (25 * 5 + math.pi * 2.5 ** 2) - 16 * 9 - (5 * 4 + math.pi * 2)
SLOTTED_CUT = (2 * 68 + 38 + 34 + 2 * math.pi * 6) + (2 * 5 + math.pi * 2) + (2 * 25 + 2 * math.pi * 2.5) + 2 * (16 + 9) + 2 * 2 * math.pi * 2.1


def turned(shape):
    """A plate as it was made, on edge, upside down, and moved and turned about all three axes."""
    from build123d import Pos, Rot

    return {"flat": shape, "on edge": Rot(0, 90, 0) * shape, "upside down": Rot(180, 0, 0) * shape,
            "tilted": Pos(10, 20, 30) * Rot(31, 17, 59) * shape}


@with_build123d
def test_round_corners_and_the_round_ends_of_a_slot_are_written_as_arcs_whichever_way_the_plate_lies(tmp_path, capsys):
    for name, plate in turned(slotted_plate()).items():
        assert cut_file.write_plate("plate", measured(plate), plate, tmp_path / name) == 0, name
        record = json.loads((tmp_path / name / "plate.cut.json").read_text())
        assert record["passed"] and set(record["checks"]) == {"plate", "closed", "area", "extent", "unit"} and "allowance" not in record
        pieces, other, unit = cut_file.read_dxf(tmp_path / name / "plate.dxf")
        # four corners, two ends of the slot and the end of the slot from the side are arcs, not chords
        assert kinds(pieces) == {"line": 13, "arc": 7, "circle": 2} and other == {} and unit == 4, name
        assert sorted(round(piece[2], 9) for piece in pieces if piece[0] == "arc") == [2.0, 2.5, 2.5, 6.0, 6.0, 6.0, 6.0]
        drawing = record["drawing"]
        assert drawing["loops"] == 5 and drawing["holes"] == 4 and drawing["closed"]
        assert drawing["area_mm2"] == pytest.approx(SLOTTED_AREA, rel=1e-9) and drawing["cut_length_mm"] == pytest.approx(SLOTTED_CUT, rel=1e-9)
        assert record["plate"]["face_area_mm2"] == pytest.approx(SLOTTED_AREA, rel=1e-9) and record["area_relative_difference"] < 1e-9
    assert "NOT" not in capsys.readouterr().out
    # the plate as it lies in X and Y is drawn where it is: as wide and as high as the part, about the part's origin
    drawing = json.loads((tmp_path / "flat" / "plate.cut.json").read_text())["drawing"]
    assert drawing["extent_mm"] == pytest.approx([80.0, 50.0]) and drawing["min_mm"] == pytest.approx([-40.0, -25.0])


@with_build123d
def test_an_ellipse_in_the_outline_is_refused_and_nothing_is_written(tmp_path, capsys):
    from build123d import Ellipse, extrude

    oval = extrude(Ellipse(20, 12), amount=3)
    assert cut_file.write_plate("oval", measured(oval), oval, tmp_path) == 1
    out = capsys.readouterr().out
    assert "NOT A PLATE CUT SQUARE THROUGH" in out and "neither straight nor circular (ELLIPSE)" in out and "no drawing is written" in out
    assert not list(tmp_path.iterdir())


@with_build123d
def test_an_allowance_moves_the_outline_outward_and_a_hole_inward_by_half_the_width_of_the_cut(tmp_path, capsys):
    from build123d import Box, Cylinder

    plate = Box(40, 30, 3) - Cylinder(5, 9)
    assert cut_file.write_plate("plate", measured(plate), plate, tmp_path, 0.4) == 0
    out = capsys.readouterr().out
    assert "allowing for a cut 0.4 mm wide" in out and "NOT" not in out and "DIFFER" not in out, out
    record = json.loads((tmp_path / "plate.cut.json").read_text())
    assert record["passed"] and set(record["checks"]) == {"plate", "closed", "area", "extent", "unit", "allowance"}
    assert all(record["checks"].values())
    pieces, other, unit = cut_file.read_dxf(tmp_path / "plate.dxf")
    # the four sides where they were, 0.2 further out, an arc of 0.2 round each corner, and the hole 0.2 smaller
    assert kinds(pieces) == {"line": 4, "arc": 4, "circle": 1} and other == {} and unit == 4
    assert {round(piece[2], 9) for piece in pieces if piece[0] == "arc"} == {0.2}
    assert [piece[1:] for piece in pieces if piece[0] == "circle"] == [(pytest.approx((0.0, 0.0), abs=1e-9), pytest.approx(4.8))]
    assert sorted(round(cut_file.length(piece), 9) for piece in pieces if piece[0] == "line") == [30.0, 30.0, 40.0, 40.0]
    drawing, allowance = record["drawing"], record["allowance"]
    by_hand = 40 * 30 + 2 * (40 + 30) * 0.2 + math.pi * 0.2 ** 2 - math.pi * 4.8 ** 2
    assert drawing["area_mm2"] == pytest.approx(by_hand, rel=1e-9) and drawing["extent_mm"] == pytest.approx([40.4, 30.4])
    assert drawing["cut_length_mm"] == pytest.approx(2 * (40 + 30) + 2 * math.pi * 0.2 + 2 * math.pi * 4.8, rel=1e-9)
    assert allowance["cut_width_mm"] == 0.4 and allowance["outline_moved_outward_mm"] == 0.2 and allowance["holes_moved_inward_mm"] == 0.2
    assert allowance["face_with_allowance"]["area_mm2"] == pytest.approx(by_hand, rel=1e-9)
    assert allowance["face_with_allowance"]["extent_mm"] == pytest.approx([40.4, 30.4])
    assert allowance["drawing_from_face_mm"] == pytest.approx([0.2, 0.2], abs=1e-9)
    assert allowance["edges_from_drawing_mm"] == pytest.approx([0.2, 0.2], abs=1e-9)
    assert (allowance["loops"], allowance["face_loops"], allowance["sharp_inside_corners_left_round"]) == (2, 2, 0)
    # the solid's own face is still in the record, and the drawing is held to the face with the allowance
    assert record["plate"]["face_area_mm2"] == pytest.approx(40 * 30 - math.pi * 25, rel=1e-9) and record["plate"]["extent_mm"] == pytest.approx([40.0, 30.0])
    assert record["area_relative_difference"] < 1e-9
    # without the allowance the same plate is the face itself: four lines and the hole as it is
    assert cut_file.write_plate("plate", measured(plate), plate, tmp_path / "plain") == 0
    plain = json.loads((tmp_path / "plain" / "plate.cut.json").read_text())
    assert "allowance" not in plain and "allowance" not in plain["checks"]
    assert kinds(cut_file.read_dxf(tmp_path / "plain" / "plate.dxf")[0]) == {"line": 4, "arc": 0, "circle": 1}
    assert plain["drawing"]["area_mm2"] == pytest.approx(40 * 30 - math.pi * 25, rel=1e-9)


@with_build123d
def test_an_allowance_is_kept_whichever_way_the_plate_lies(tmp_path, capsys):
    areas = set()
    for name, plate in turned(slotted_plate()).items():
        assert cut_file.write_plate("plate", measured(plate), plate, tmp_path / name, 0.2) == 0, name
        record = json.loads((tmp_path / name / "plate.cut.json").read_text())
        assert record["passed"] and record["checks"]["allowance"] and record["checks"]["area"] and record["checks"]["extent"], name
        pieces, other, _ = cut_file.read_dxf(tmp_path / name / "plate.dxf")
        # two more arcs: round the two corners where the slot from the side opens. The window's corners point
        # into the material and stay sharp in the drawing; the cut leaves them round
        assert kinds(pieces) == {"line": 13, "arc": 9, "circle": 2} and other == {}, name
        assert sorted(round(piece[2], 9) for piece in pieces if piece[0] == "circle") == [2.0, 2.0]
        assert sorted(round(piece[2], 9) for piece in pieces if piece[0] == "arc") == [0.1, 0.1, 1.9, 2.4, 2.4, 6.1, 6.1, 6.1, 6.1]
        allowance = record["allowance"]
        assert allowance["drawing_from_face_mm"] == pytest.approx([0.1, 0.1], abs=1e-9)
        assert allowance["edges_from_drawing_mm"] == pytest.approx([0.1, 0.1], abs=1e-9)
        assert (allowance["loops"], allowance["face_loops"], allowance["sharp_inside_corners_left_round"]) == (5, 5, 4)
        assert record["plate"]["face_area_mm2"] == pytest.approx(SLOTTED_AREA, rel=1e-9)
        assert record["drawing"]["area_mm2"] > SLOTTED_AREA + 0.1 * SLOTTED_CUT * 0.99
        areas.add(round(record["drawing"]["area_mm2"], 6))
    assert len(areas) == 1 and "NOT" not in capsys.readouterr().out
    # the check itself: the same drawing held to a cut of another width, and the face's own outline held to any
    from build123d import Pos

    plate = slotted_plate()
    flat = Pos(0, 0, -3) * cut_file.plate_of(plate, plate.volume)[0]            # the face, in the drawing's plane
    pieces = cut_file.read_dxf(tmp_path / "flat" / "plate.dxf")[0]
    assert cut_file.allowance_kept(pieces, flat, 0.1)["passed"]
    wider = cut_file.allowance_kept(pieces, flat, 0.15)
    assert not wider["passed"] and wider["drawing_from_face_mm"] == pytest.approx([0.1, 0.1], abs=1e-9) and wider["corners_too_near"] > 0
    assert cut_file.write_plate("plate", measured(plate), plate, tmp_path / "plain") == 0
    plain = cut_file.allowance_kept(cut_file.read_dxf(tmp_path / "plain" / "plate.dxf")[0], flat, 0.1)
    assert not plain["passed"] and plain["drawing_from_face_mm"] == pytest.approx([0.0, 0.0], abs=1e-9)
    # a hole left out of the drawing is found by the edge the cut then does not reach, and by the count of loops
    fewer = [piece for piece in pieces if piece[0] != "circle"]
    missing = cut_file.allowance_kept(fewer, flat, 0.1)
    assert not missing["passed"] and (missing["loops"], missing["face_loops"]) == (3, 5) and len(missing["unreached"]) == 2


@with_build123d
def test_an_allowance_that_closes_a_hole_a_slot_or_an_inside_round_is_refused(tmp_path, capsys):
    from build123d import Axis, Box, Cylinder, Pos, SlotCenterToCenter, extrude, fillet

    def cut(name, plate, kerf):
        status = cut_file.write_plate(name, measured(plate), plate, tmp_path / f"{name} {kerf}", kerf)
        written = sorted(p.name for p in (tmp_path / f"{name} {kerf}").glob("*")) if (tmp_path / f"{name} {kerf}").exists() else []
        return status, written, capsys.readouterr().out

    refused = "DOES NOT MAKE THIS PLATE"
    # a hole of 2: a cut of 1.9 leaves a hole of 0.1 to follow; one of 2 or more leaves nothing
    drilled = Box(40, 30, 3) - Cylinder(1, 9)
    assert cut("hole", drilled, 1.9)[:2] == (0, ["hole.cut.json", "hole.dxf"])
    for kerf in (2.0, 2.5):
        status, written, out = cut("hole", drilled, kerf)
        assert status == 1 and written == [] and refused in out and "the drawing has 1 loop(s) and the face 2" in out, out
        assert "does not reach 1 edge(s) of the plate" in out and "no drawing is written" in out
    # a slot 5 wide: its two sides meet at a cut of 5, and are gone at more
    slotted = Box(40, 30, 3) - Pos(0, 0, -3) * extrude(SlotCenterToCenter(15, 5), amount=9)
    assert cut("slot", slotted, 4.9)[0] == 0
    status, written, out = cut("slot", slotted, 5.0)
    assert status == 1 and written == [] and refused in out and "1 loop(s) of the drawing enclose nothing" in out, out
    status, written, out = cut("slot", slotted, 5.5)
    assert status == 1 and written == [] and "the drawing has 1 loop(s) and the face 2" in out and "does not reach 4 edge(s)" in out, out
    # a notch 2 wide in from the side: the outline stays one loop, and the cut does not reach the notch's three sides
    notched = Box(40, 30, 3) - Pos(20, 0, 0) * Box(10, 2, 9)
    status, written, out = cut("notch", notched, 1.9)
    assert status == 0 and "2 sharp inside corner(s) come out round" in out
    status, written, out = cut("notch", notched, 2.4)
    assert status == 1 and written == [] and refused in out and "does not reach 3 edge(s) of the plate" in out and "loop(s) and the face" not in out, out
    # a hole of two rounds joined by a neck 1 wide: with the neck closed the cut would follow two loops
    dumbbell = Box(60, 30, 3) - Pos(-12, 0, 0) * Cylinder(5, 9) - Pos(12, 0, 0) * Cylinder(5, 9) - Box(24, 1, 9)
    assert cut("neck", dumbbell, 0.6)[0] == 0
    status, written, out = cut("neck", dumbbell, 1.2)
    assert status == 1 and written == [] and "the drawing has 3 loop(s) and the face 2" in out and "does not reach 2 edge(s)" in out, out
    # an L: its sharp inside corner comes out round and is counted; an inside round of 1 is followed by a cut up
    # to 2 wide, and not reached by a wider one
    ell = Box(40, 30, 3) - Pos(10, 10, 0) * Box(20, 10, 9)
    status, written, out = cut("ell", ell, 3.0)
    assert status == 0 and "1 sharp inside corner(s) come out round" in out
    inside = [e for e in ell.edges().filter_by(Axis.Z) if abs(e.center().X) < 1 and abs(e.center().Y - 5) < 1]
    rounded_ell = fillet(inside, 1.0)
    status, written, out = cut("round", rounded_ell, 2.0)
    assert status == 0 and "0 sharp inside corner(s)" in out
    status, written, out = cut("round", rounded_ell, 3.0)
    assert status == 1 and written == [] and refused in out and "does not reach 1 edge(s) of the plate, the furthest 1.7071 mm" in out, out


SLOTTED = '''"""The plate of tests/test_cut_file.py with arcs in its outline, drawn as it is and with an allowance."""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import test_cut_file as tests

plate = tests.slotted_plate()
for kerf, where in ((None, "plain"), (0.2, "allowance")):
    assert tests.cut_file.write_plate("plate", tests.measured(plate), plate, Path(sys.argv[2]) / where, kerf) == 0
'''


@with_build123d
def test_a_drawing_with_lines_arcs_and_circles_is_the_same_file_whatever_the_hash_seed(tmp_path):
    (tmp_path / "draw.py").write_text(SLOTTED, encoding="utf-8")
    written = {}
    for seed in (0, 4):
        done = subprocess.run([sys.executable, "-B", str(tmp_path / "draw.py"), str(REPO / "tests"), str(tmp_path / str(seed))],
                              capture_output=True, text=True, env=dict(os.environ, PYTHONHASHSEED=str(seed)))
        assert done.returncode == 0, done.stdout + done.stderr
        written[seed] = {str(p.relative_to(tmp_path / str(seed))): p.read_bytes() for p in sorted((tmp_path / str(seed)).rglob("*.*"))}
    assert sorted(written[0]) == ["allowance/plate.cut.json", "allowance/plate.dxf", "plain/plate.cut.json", "plain/plate.dxf"]
    assert written[0] == written[4]
    assert kinds(cut_file.read_dxf(tmp_path / "0" / "allowance" / "plate.dxf")[0]) == {"line": 13, "arc": 9, "circle": 2}


@with_build123d
def test_the_cut_file_with_an_allowance_is_the_same_file_every_time(project_copy):
    out = run(project_copy, "spacer", "--kerf", "0.2", seed=0)
    assert "[cut_file] exit status 0" in out and "NOT" not in out and "allowing for a cut 0.2 mm wide" in out, out
    record = json.loads((project_copy / ".cache/cut/spacer.cut.json").read_text())
    assert record["passed"] and record["checks"]["allowance"] and record["allowance"]["cut_width_mm"] == 0.2
    # the ring 0.1 wider outside and 0.1 narrower inside: two circles
    dxf = project_copy / ".cache/cut/spacer.dxf"
    pieces, other, unit = cut_file.read_dxf(dxf)
    assert sorted(round(piece[2], 9) for piece in pieces) == [5.15, 10.1] and kinds(pieces)["circle"] == 2 and other == {} and unit == 4
    assert record["drawing"]["area_mm2"] == pytest.approx(math.pi * (10.1 ** 2 - 5.15 ** 2), rel=1e-9)
    assert record["plate"]["face_area_mm2"] == pytest.approx(math.pi * (10.0 ** 2 - 5.25 ** 2), rel=1e-9)
    first = dxf.read_bytes()
    again = run(project_copy, "spacer", "--kerf", "0.2", seed=4)
    assert dxf.read_bytes() == first, again
    assert json.loads((project_copy / ".cache/cut/spacer.cut.json").read_text()) == record
    # an allowance wider than the ring's hole: refused, and the files that were there are left as they were
    out = run(project_copy, "spacer", "--kerf", "11")
    assert "DOES NOT MAKE THIS PLATE" in out and "[cut_file] exit status 1" in out and dxf.read_bytes() == first
    # the options that do not go together are refused before anything is read
    assert "a flat pattern has no such allowance" in run(project_copy, "spacer", "--pattern", "--kerf", "0.2")
    assert "give --pattern with it" in run(project_copy, "spacer", "--open", "+z")
    # and without the option the drawing is the face again
    out = run(project_copy, "spacer")
    assert "[cut_file] exit status 0" in out and "allowing" not in out
    assert "allowance" not in json.loads((project_copy / ".cache/cut/spacer.cut.json").read_text())
    assert sorted(round(piece[2], 9) for piece in cut_file.read_dxf(dxf)[0]) == [5.25, 10.0]


# ---- a flat pattern: an outline to cut and lines to fold along -------------------------------------------------

def polygon(*corners):
    return [("line", a, b) for a, b in zip(corners, corners[1:] + corners[:1])]


def test_the_options_of_a_pattern():
    assert cut_file.options(["PROJECT", "KEY"]) == (["PROJECT", "KEY"], None, False, "-z", (), None)
    assert cut_file.options(["PROJECT", "KEY", "--pattern", "--root", "+X", "--out", "DIR"]) == (["PROJECT", "KEY"], "DIR", True, "+x", (), None)
    for wrong in (["PROJECT", "KEY", "--root", "up"], ["PROJECT", "KEY", "--tabs"], ["PROJECT"]):
        with pytest.raises(SystemExit):
            cut_file.options(wrong)


def test_the_options_of_an_allowance_and_of_an_open_shell():
    assert cut_file.options(["PROJECT", "KEY", "--kerf", "0.2"]) == (["PROJECT", "KEY"], None, False, "-z", (), 0.2)
    # the faces to leave open, each once, in the order given
    assert cut_file.options(["PROJECT", "KEY", "--pattern", "--open", "+Z,-y, +z", "--root", "-x"]) == (
        ["PROJECT", "KEY"], None, True, "-x", ("+z", "-y"), None)
    for wrong, why in ((["--kerf", "0"], "more than 0"), (["--kerf", "-0.2"], "more than 0"), (["--kerf", "wide"], "more than 0"),
                       (["--kerf", "inf"], "more than 0"), (["--kerf", "nan"], "more than 0"),
                       (["--pattern", "--kerf", "0.2"], "a flat pattern has no such allowance"),
                       (["--open", "+z"], "give --pattern with it")):
        with pytest.raises(SystemExit, match=why):
            cut_file.options(["PROJECT", "KEY"] + wrong)
    for wrong in (["--pattern", "--open", "up"], ["--pattern", "--open", "+z,"], ["--pattern", "--open"], ["--kerf"]):
        with pytest.raises(SystemExit, match="python3 tools/cut_file.py PROJECT KEY"):
            cut_file.options(["PROJECT", "KEY"] + wrong)


def test_a_piece_is_measured_at_its_ends_and_its_middle_and_from_a_point():
    line = ("line", (0.0, 0.0), (10.0, 0.0))
    assert cut_file._samples(line) == [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0)]
    assert cut_file._to_piece((5.0, 3.0), line) == pytest.approx(3.0) and cut_file._to_piece((13.0, 4.0), line) == pytest.approx(5.0)
    circle = ("circle", (1.0, 2.0), 5.0)
    assert cut_file._samples(circle) == [pytest.approx(p) for p in ((6.0, 2.0), (1.0, 7.0), (-4.0, 2.0), (1.0, -3.0))]
    assert cut_file._to_piece((1.0, 2.0), circle) == pytest.approx(5.0) and cut_file._to_piece((1.0, 10.0), circle) == pytest.approx(3.0)
    # a quarter of that circle, counter-clockwise from 270 degrees to 0: from (1, -3) through 315 degrees to (6, 2)
    arc = ("arc", (1.0, 2.0), 5.0, 270.0, 0.0)
    middle = (1.0 + 5.0 * math.cos(math.radians(315)), 2.0 + 5.0 * math.sin(math.radians(315)))
    assert cut_file._samples(arc) == [pytest.approx(p) for p in ((1.0, -3.0), middle, (6.0, 2.0))]
    # a point within the arc's angle is as far from it as from the circle; any other, as far as from the nearer end
    assert cut_file._to_piece((1.0 + 8.0 * math.cos(-0.5), 2.0 + 8.0 * math.sin(-0.5)), arc) == pytest.approx(3.0)
    assert cut_file._to_piece((2.0, 1.5), arc) == pytest.approx(5.0 - math.hypot(1.0, 0.5))
    assert cut_file._to_piece((1.0, 10.0), arc) == pytest.approx(math.dist((1.0, 10.0), (6.0, 2.0)))
    assert cut_file._to_piece((-4.0, 2.0), arc) == pytest.approx(math.dist((-4.0, 2.0), (1.0, -3.0)))
    # an arc that passes 0 degrees
    over = ("arc", (0.0, 0.0), 2.0, 350.0, 10.0)
    assert cut_file._to_piece((3.0, 0.0), over) == pytest.approx(1.0) and cut_file._samples(over)[1] == pytest.approx((2.0, 0.0))
    assert cut_file._to_piece((-3.0, 0.0), over) == pytest.approx(math.dist((-3.0, 0.0), (2.0 * math.cos(math.radians(10)), 2.0 * math.sin(math.radians(10)))))


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


def test_a_fold_line_on_the_outline_or_touching_it_is_not_where_a_fold_is():
    sheet = polygon((0, 0), (30, 0), (30, 20), (12, 20), (12, 5), (11, 5), (11, 20), (0, 20))
    touching = "touches the outline between its ends"
    astray = cut_file.folds_astray(sheet, [
        ("line", (0.0, 0.0), (30.0, 0.0)),                      # a side of the outline drawn again as a fold
        ("line", (0.0, 20.0), (0.0, 0.0)),                      # another, the other way round
        ("line", (5.0, 0.0), (25.0, 0.0)),                      # along part of a side
        ("line", (30.0, 0.0), (30.0, 20.0)),
        ("line", (0.0, 5.0), (30.0, 5.0)),                      # from side to side, along the end of the slot
        ("line", (0.0, 0.0), (30.0, 12.5)),                     # through a corner of the slot
        ("line", (5.0, 0.0), (5.0, 0.0)),                       # a point
        ("line", (0.0, 0.0), (30.0, 12.0)),                     # just under that corner: a fold
    ])
    assert astray == [(0, touching), (1, touching), (2, touching), (3, touching), (4, touching), (5, touching),
                      (6, "has no length")]
    # every side of an outline, drawn as a fold, is found, whichever way the outline runs
    for outline in (sheet, [("line", end, start) for _, start, end in sheet]):
        assert cut_file.folds_astray(outline, outline) == [(k, touching) for k in range(len(outline))]


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
    # round edges so small that volume and area do not show them: the corners are those of a solid with flat
    # faces, sixteen of them, and four of the part's faces are round all the same
    tray = Box(400, 300, 20)
    barely = fillet(tray.edges().filter_by(Axis.Z), 0.005)
    assert abs(barely.volume - tray.volume) < 1e-6 * tray.volume and abs(barely.area - tray.area) < 1e-6 * tray.area
    with pytest.raises(ValueError, match="4 of its 10 faces are not flat"):
        cut_file.polyhedron_of(barely, "barely", barely.volume, barely.area)


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
    # open on top, a shell to fold: the top hexagon is left out, and the same files come whatever the hash seed
    out = run(project_copy, "folded", "--pattern", "--open", "+z", "--out", project_copy / "open", seed=0)
    assert "[cut_file] exit status 0" in out and "NOT" not in out and "1 of them left open (towards +z)" in out, out
    open_record = json.loads((project_copy / "open/folded.pattern.json").read_text())
    assert open_record["passed"] and open_record["checks"]["open"] and open_record["pattern"]["faces"] == 13
    assert len(open_record["pattern"]["folds"]) == 12 and open_record["pattern"]["rim"]["length_mm"] == pytest.approx(6 * 30.0, rel=1e-9)
    hexagon = 1.5 * math.sqrt(3) * 30.0 ** 2
    assert open_record["pattern"]["left_open"][0]["area_mm2"] == pytest.approx(hexagon, rel=1e-9)
    assert open_record["drawing"]["area_mm2"] == pytest.approx(solid.area - hexagon, rel=1e-9)
    assert open_record["drawing"]["cut_length_mm"] == pytest.approx((2 * (36 - 12 - 6) + 6) * 30.0, rel=1e-9)
    open_bytes = (project_copy / "open/folded.pattern.dxf").read_bytes()
    again = run(project_copy, "folded", "--pattern", "--open", "+z", "--out", project_copy / "open", seed=4)
    assert (project_copy / "open/folded.pattern.dxf").read_bytes() == open_bytes, again
    assert json.loads((project_copy / "open/folded.pattern.json").read_text()) == open_record
    out = run(project_copy, "folded", "--pattern", "--open", "-z")
    assert "THE FACE LAID FIRST IS LEFT OPEN" in out and "[cut_file] exit status 1" in out
    # a plate is cut, not folded, and its pattern does not get in the way of its cut file; a ring has no pattern
    assert not (project_copy / ".cache/cut/folded.dxf").exists()
    out = run(project_copy, "spacer", "--pattern")
    assert "NOT A CONVEX SOLID WITH FLAT FACES" in out and "[cut_file] exit status 1" in out
    assert not (project_copy / ".cache/cut/spacer.pattern.dxf").exists()
    out = run(project_copy, "folded")
    assert "NOT A PLATE CUT SQUARE THROUGH" in out and "[cut_file] exit status 1" in out


# ---- a flat pattern with faces left open: a tray, half of an enclosure -----------------------------------------

@with_build123d
def test_a_box_without_its_top_is_the_pattern_of_a_tray(tmp_path, capsys):
    from build123d import Box, Pos

    box = Pos(10, 20, 12.5) * Box(120, 80, 25)
    assert cut_file.write_pattern("tray", measured(box), box, tmp_path, "-z", ("+z",)) == 0
    out = capsys.readouterr().out
    assert "a solid of 6 faces, 1 of them left open (towards +z), from the face towards -z" in out and "NOT" not in out and "DIFFER" not in out, out
    record = json.loads((tmp_path / "tray.pattern.json").read_text())
    assert record["passed"] and all(record["checks"].values())
    assert set(record["checks"]) == {"polyhedron", "closed", "area", "length", "folds", "extent", "unit", "layers", "open"}
    drawing, pattern = record["drawing"], record["pattern"]
    # the floor with a wall on each side: four folds of a right angle, and the outline round the five faces
    assert (pattern["faces"], len(pattern["folds"]), drawing["fold_lines"]) == (5, 4, 4)
    assert {round(fold["angle_deg"], 9) for fold in pattern["folds"]} == {90.0}
    assert sorted(round(fold["length_mm"], 9) for fold in pattern["folds"]) == [80.0, 80.0, 120.0, 120.0]
    assert drawing["loops"] == 1 and drawing["closed"] and drawing["pieces"] == 12
    assert drawing["area_mm2"] == pytest.approx(120 * 80 + 2 * 25 * (120 + 80), rel=1e-9) and pattern["kept_area_mm2"] == pytest.approx(19600.0, rel=1e-9)
    # the four upright edges are cut twice, between two walls; the four round the opening once: the rim
    assert pattern["cut_edges"] == 8 and pattern["rim"]["edges"] == 4 and pattern["rim"]["length_mm"] == pytest.approx(400.0, rel=1e-9)
    assert drawing["cut_length_mm"] == pytest.approx(2 * 4 * 25 + 400, rel=1e-9)
    assert sorted(drawing["extent_mm"]) == pytest.approx([130.0, 170.0]) and drawing["min_mm"] == pytest.approx([0.0, 0.0], abs=1e-9)
    # the face left out is the part's top: its corners, its area by them and as the kernel has it
    (left,) = pattern["left_open"]
    assert left["towards"] == "+z" and {corner[2] for corner in left["corners_in_part_mm"]} == {25.0}
    assert left["area_mm2"] == pytest.approx(9600.0, rel=1e-9) and left["area_of_the_parts_faces_there_mm2"] == pytest.approx(9600.0, rel=1e-9)
    assert record["polyhedron"]["area_mm2"] == pytest.approx(2 * 9600 + 10000, rel=1e-9) and len(pattern["without"]) == 3
    # read back: every fold from the outline to the outline, and no line where the top's edges would be folded
    cut, _, _ = cut_file.read_dxf(tmp_path / "tray.pattern.dxf", "cut")
    folds, _, _ = cut_file.read_dxf(tmp_path / "tray.pattern.dxf", "fold")
    assert (len(cut), len(folds)) == (12, 4) and cut_file.folds_astray(cut, folds) == []
    # the closed box from the same face has the top hung on one wall: one face and one fold more, and no rim
    assert cut_file.write_pattern("box", measured(box), box, tmp_path, "-z") == 0
    closed = json.loads((tmp_path / "box.pattern.json").read_text())
    assert (closed["pattern"]["faces"], len(closed["pattern"]["folds"]), closed["pattern"]["cut_edges"]) == (6, 5, 7)
    assert "left_open" not in closed["pattern"] and "rim" not in closed["pattern"] and "open" not in closed["checks"]
    assert closed["drawing"]["area_mm2"] == pytest.approx(29200.0, rel=1e-9)
    # open on two sides: a tray without one of its long walls
    assert cut_file.write_pattern("scoop", measured(box), box, tmp_path, "-z", ("+z", "-y")) == 0
    scoop = json.loads((tmp_path / "scoop.pattern.json").read_text())
    assert scoop["passed"] and (scoop["pattern"]["faces"], len(scoop["pattern"]["folds"])) == (4, 3)
    assert [left["towards"] for left in scoop["pattern"]["left_open"]] == ["+z", "-y"]
    assert scoop["drawing"]["area_mm2"] == pytest.approx(19600 - 120 * 25, rel=1e-9)
    # the edge between the two faces left out is nowhere; the rim is the other seven edges of the two
    assert scoop["pattern"]["rim"]["edges"] == 6 and scoop["pattern"]["rim"]["length_mm"] == pytest.approx(2 * 80 + 120 + 2 * 25 + 120, rel=1e-9)
    assert "DIFFER" not in capsys.readouterr().out


@with_build123d
def test_what_an_open_pattern_refuses(tmp_path, capsys):
    from build123d import Box

    from mechanical_cad.shapes import forms, polyhedra

    box = Box(120, 80, 25)

    def refused(name, shape, root, left_open):
        status = cut_file.write_pattern(name, measured(shape), shape, tmp_path / name, root, left_open)
        return status, (tmp_path / name).exists(), capsys.readouterr().out

    # the face laid first is -z unless said: a shell open below needs another
    status, written, out = refused("lid", box, "-z", ("-z",))
    assert status == 1 and not written and "THE FACE LAID FIRST IS LEFT OPEN" in out and "--root" in out, out
    assert cut_file.write_pattern("lid", measured(box), box, tmp_path / "lid", "+z", ("-z",)) == 0
    lid = json.loads((tmp_path / "lid" / "lid.pattern.json").read_text())
    assert lid["passed"] and lid["pattern"]["root"]["towards"] == "+z" and lid["pattern"]["left_open"][0]["towards"] == "-z"
    # floor and top without the walls between them do not hang together
    status, written, out = refused("apart", box, "-z", ("+x", "-x", "+y", "-y"))
    assert status == 1 and not written and "NO FLAT PATTERN" in out and "without the 4 faces left open the others do not hang together" in out, out
    # a face is named by an axis it faces squarely: a tetrahedron as the library has it has none along z
    tetrahedron = forms.solid(polyhedra.named("tetrahedron", 30.0))
    status, written, out = refused("tetrahedron", tetrahedron, "-z", ("+z",))
    assert status == 1 and not written and "NO FACE TO LEAVE OPEN" in out, out
    assert "no face that faces +z squarely; the nearest leans 54.736 degrees away from it" in out


@with_build123d
def test_half_of_a_solid_open_where_it_was_divided_is_the_pattern_of_an_enclosure_half(tmp_path, capsys):
    from mechanical_cad.shapes import forms, polyhedra

    p = polyhedra.named("truncated-octahedron", 30.0)
    p = p.resting_on(p.faces_with(6)[0])
    height = max(v[2] for v in p.vertices)
    base, lid = p.clipped((0, 0, 1), height / 2), p.clipped((0, 0, -1), -height / 2)
    for name, half, root, left_open in (("base", base, "-z", ("+z",)), ("lid", lid, "+z", ("-z",))):
        solid = forms.solid(half)
        assert cut_file.write_pattern(name, measured(solid), solid, tmp_path, root, left_open) == 0, name
        record = json.loads((tmp_path / f"{name}.pattern.json").read_text())
        assert record["passed"] and record["checks"]["open"] and record["checks"]["folds"], name
        drawing, pattern = record["drawing"], record["pattern"]
        # a hexagon to stand on, three squares, and six hexagons that the plane crosses: three keep three
        # quarters of their height here and three a quarter. Open where it was divided
        assert record["polyhedron"]["faces"] == 11 and (pattern["faces"], len(pattern["folds"]), drawing["loops"]) == (10, 9, 1)
        (left,) = pattern["left_open"]
        cut = half.face_towards((0, 0, 1) if name == "base" else (0, 0, -1))
        assert left["area_mm2"] == pytest.approx(half.face_areas[cut], rel=1e-9)
        assert left["area_of_the_parts_faces_there_mm2"] == pytest.approx(half.face_areas[cut], rel=1e-9)
        assert {round(corner[2], 6) for corner in left["corners_in_part_mm"]} == {round(height / 2, 6)}
        assert drawing["area_mm2"] == pytest.approx(half.area - half.face_areas[cut], rel=1e-9)
        # the rim is the outline of the cut: a hexagon, each side across one of the six hexagons where it is one
        # and a half edges wide
        assert pattern["rim"]["edges"] == len(half.faces[cut]) == 6 and pattern["rim"]["length_mm"] == pytest.approx(6 * 45.0, rel=1e-9)
    # the two halves together are the whole surface
    areas = [json.loads((tmp_path / f"{name}.pattern.json").read_text())["drawing"]["area_mm2"] for name in ("base", "lid")]
    assert sum(areas) == pytest.approx(p.area, rel=1e-9) and "NOT" not in capsys.readouterr().out
