"""tools/cut_file.py: what a drawing's lines, arcs and circles close, without a kernel; and a plate's cut file
written where build123d is (make test-build123d)."""
import importlib.util
import json
import math
import os
import subprocess
import sys

import pytest
from conftest import REPO

TOOL = REPO / "tools" / "cut_file.py"
spec = importlib.util.spec_from_file_location("cut_file_tool", TOOL)
cut_file = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cut_file)

with_build123d = pytest.mark.skipif(importlib.util.find_spec("build123d") is None,
                                    reason="build123d is not in this environment (make test-build123d)")


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
