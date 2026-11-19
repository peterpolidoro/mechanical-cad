"""tools/section.py: how a sheet lies in the model and what the drawing is, without a kernel; and sections of
the fixture where build123d is (make test-build123d)."""
import importlib.util
import json
import math
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


def test_a_dimension_is_asked_for_between_two_points_of_the_model():
    asked = section.measures(["across 0,0,0 40,0,12 gap between the walls; up 0,0,0 0,0,21", " -1.5,2,0 3,2,4 "])
    assert asked == [("across", (0.0, 0.0, 0.0), (40.0, 0.0, 12.0), "gap between the walls"),
                     ("up", (0.0, 0.0, 0.0), (0.0, 0.0, 21.0), ""), ("between", (-1.5, 2.0, 0.0), (3.0, 2.0, 4.0), "")]
    assert section.measures([]) == [] and section.measures([" ; "]) == []
    for wrong in ("across 0,0,0", "0,0 1,1", "up here there", "sideways 0,0,0 1,1,1"):
        with pytest.raises(ValueError, match="--measure"):
            section.measures([wrong])
    positional, opts = section.options(["project", "key", "--cut", "+y", "--measure", "up 0,0,0 0,0,5", "--measure", "0,0,0 3,0,4"])
    assert [m[0] for m in opts["measure"]] == ["up", "between"] and positional == ["project", "key"]


def test_dimensions_stand_outside_the_drawing_with_lines_to_their_points():
    square = [(0.0, 0.0), (30.0, 0.0), (30.0, 20.0), (0.0, 20.0)]
    plain = section.svg("thing: section", [], [("plate", (0.2, 0.4, 0.6), [[square]])], (0.0, 0.0), (30.0, 20.0))
    text = section.svg("thing: section", [], [("plate", (0.2, 0.4, 0.6), [[square]])], (0.0, 0.0), (30.0, 20.0),
                       [("across", (5.0, 0.0), (25.0, 20.0), 20.0, "between <holes>"), ("up", (0.0, 0.0), (0.0, 12.5), 12.5, ""),
                        ("between", (0.0, 0.0), (3.0, 4.0), 5.0, "")])
    root, bare = ET.fromstring(text), ET.fromstring(plain)
    words = [t.text for t in root.iter(SVG + "text")]
    assert "20.00 between <holes>" in words and "12.50" in words and "5.00" in words
    assert "30.00" in words and "20.00" in words                     # how wide and how high all of it is, as before
    # a row above and a column at the right were made room for
    grown = [float(a) - float(b) for a, b in zip(root.get("viewBox").split()[2:], bare.get("viewBox").split()[2:])]
    assert grown == [16.0, 7.0]
    # a point outside what is cut is on the sheet as well: 70 across where a sheet is 60 at the least
    wide = section.svg("thing: section", [], [("plate", (0.2, 0.4, 0.6), [[square]])], (0.0, 0.0), (30.0, 20.0),
                       [("between", (-40.0, 0.0), (30.0, 0.0), 70.0, "")])
    assert float(ET.fromstring(wide).get("viewBox").split()[2]) == float(bare.get("viewBox").split()[2]) + 10.0


def test_a_part_that_lets_light_through_is_drawn_paler():
    square = [(0.0, 0.0), (30.0, 0.0), (30.0, 20.0), (0.0, 20.0)]
    text = section.svg("thing: section", [], [("plate: aluminium", (0.2, 0.4, 0.6), [[square]], 1.0),
                                               ("window: clear", (1.0, 0.5, 0.0), [[square]], 0.4)], (0.0, 0.0), (30.0, 20.0))
    root = ET.fromstring(text)
    paths = [p for p in root.iter(SVG + "path") if p.get("fill") != "none"]
    assert [(p.get("fill"), p.get("fill-opacity")) for p in paths] == [("#336699", None), ("#ff8000", "0.4")]
    swatches = [r for r in root.iter(SVG + "rect") if r.get("stroke")]
    assert [(r.get("fill"), r.get("fill-opacity")) for r in swatches] == [("#336699", None), ("#ff8000", "0.4")]


def inside(point, loops):
    """Whether a point lies in a face, by the rule the face is filled by: inside an odd number of its outlines."""
    px, py = point
    crossed = 0
    for loop in loops:
        for (x0, y0), (x1, y1) in zip(loop, loop[1:] + loop[:1]):
            if (y0 > py) != (y1 > py) and px < x0 + (py - y0) / (y1 - y0) * (x1 - x0):
                crossed += 1
    return crossed % 2 == 1


def strokes(path):
    """The straight pieces of a path written as `M x,y L x,y` over and over: [((x, y), (x, y))]."""
    numbers = [tuple(float(v) for v in word.split(",")) for word in path.get("d").split() if "," in word]
    return list(zip(numbers[::2], numbers[1::2]))


def test_a_hatch_stays_inside_the_face_and_out_of_its_holes():
    square = [(0.0, 0.0), (30.0, 0.0), (30.0, 20.0), (0.0, 20.0)]
    hole = [(10.0, 5.0), (20.0, 5.0), (20.0, 15.0), (10.0, 15.0)]
    for degrees, apart in section.hatch_kinds():
        lines = section.hatch_lines([square, hole], degrees, apart)
        lean = math.radians(degrees)
        across = (-math.sin(lean), math.cos(lean))
        where = set()
        for a, b in lines:
            assert math.hypot(b[0] - a[0], b[1] - a[1]) >= section.HATCH_LEAST_MM
            # a little in from each end and half way along it is in the face, and so not in the hole
            for t in (0.001, 0.5, 0.999):
                assert inside((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), [square, hole]), (degrees, apart, a, b)
            # it leans as it should: both ends are as far across the lean
            assert a[0] * across[0] + a[1] * across[1] == pytest.approx(b[0] * across[0] + b[1] * across[1], abs=1e-9)
            where.add(round(a[0] * across[0] + a[1] * across[1], 6))
        # the lines are `apart` from each other, and none is missing between the first and the last
        where = sorted(where)
        assert [round(q - p, 6) for p, q in zip(where, where[1:])] == [apart] * (len(where) - 1), (degrees, apart)
        # and they cover the face: their length times how far apart they are is its area, 600 less the hole's 100
        covered = apart * sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in lines)
        assert covered == pytest.approx(500.0, rel=0.06), (degrees, apart, covered)
    # the lines are counted from the sheet's origin, not from the face: two pieces of one part carry one hatch
    moved = [(x + 41.3, y + 7.7) for x, y in square]
    both = section.hatch_lines([square], 45, 2.0) + section.hatch_lines([moved], 45, 2.0)
    offsets = {round(((a[1] - a[0]) / math.sqrt(2) / 2.0) % 1, 6) for a, _ in both}
    assert offsets == {section.HATCH_FROM}
    # a face smaller than the hatch is far apart may have no line, and a line never begins outside it
    assert all(inside(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), [[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]])
               for a, b in section.hatch_lines([[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]], 45, 3.0))
    # a line that only clips a corner is a dot, and is left out: the fourth line at 45 degrees leaves this face's
    # left side 0.03 below its top corner, and is there when the corner is 0.1 higher
    def block(top):
        return [(0.0, 0.0), (10.0, 0.0), (10.0, top), (0.0, top)]

    leaves = (3 + section.HATCH_FROM) * 2.0 * math.sqrt(2)
    clipped, whole = section.hatch_lines([block(leaves + 0.03)], 45, 2.0), section.hatch_lines([block(leaves + 0.13)], 45, 2.0)
    assert len(whole) == len(clipped) + 1 and any(a == pytest.approx((0.0, leaves), abs=1e-9) for a, _ in whole)
    assert min(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in whole) == pytest.approx(0.13 * math.sqrt(2))
    assert min(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in clipped) > 1.0
    # the same face, the same lines
    assert section.hatch_lines([square, hole], 30, 3.0) == section.hatch_lines([square, hole], 30, 3.0)


def test_parts_side_by_side_are_hatched_differently():
    def square(x, y, side=10.0):
        return [(x, y), (x + side, y), (x + side, y + side), (x, y + side)]

    kinds = section.hatch_kinds()
    assert len(set(kinds)) == len(kinds) == 18 and all(0 < degrees < 180 and degrees != 90 for degrees, _ in kinds)
    assert all(a[0] != b[0] for a, b in zip(kinds, kinds[1:]))        # one after another they lean differently
    # two that touch, one 0.3 mm from the first on its other side, and one 3.5 mm from the second, which is not near
    parts = [("a", (0.5, 0.5, 0.5), [[square(0.0, 0.0)]]), ("b", (0.5, 0.5, 0.5), [[square(10.0, 0.0)]]),
             ("c", (0.5, 0.5, 0.5), [[square(-10.3, 0.0)]]), ("d", (0.5, 0.5, 0.5), [[square(23.5, 0.0)]])]
    assert section.neighbours(parts) == {0: {1, 2}, 1: {0}, 2: {0}, 3: set()}
    assert section.hatches(parts) == kinds[:4] == [(45, 2.0), (135, 2.0), (30, 3.0), (150, 3.0)]
    # a part inside another's hole is its neighbour
    ring = [square(0.0, 0.0, 30.0), square(10.0, 10.0)]
    assert section.neighbours([("ring", (0, 0, 0), [ring]), ("core", (0, 0, 0), [[square(10.0, 10.0)]])]) == {0: {1}, 1: {0}}
    # the nineteenth part would take the first one's kind by its place; beside the first it takes the next
    apart = [(f"p{n:02d}", (0.5, 0.5, 0.5), [[square(40.0 * n, 0.0)]]) for n in range(18)]
    assert section.hatches(apart + [("q", (0.5, 0.5, 0.5), [[square(200.0, 100.0)]])])[18] == kinds[0]
    beside = section.hatches(apart + [("q", (0.5, 0.5, 0.5), [[square(0.0, 10.0)]])])
    assert beside[:18] == kinds and beside[18] == kinds[1] != beside[0]
    # every part against every other: each has a kind none of the ones before it has, while there are enough
    crowd = [(f"p{n:02d}", (0.5, 0.5, 0.5), [[square(0.2 * n, 0.0)]]) for n in range(20)]
    given = section.hatches(crowd)
    assert sorted(given[:18]) == sorted(kinds) and given == section.hatches(crowd)


def test_the_cut_faces_are_hatched_over_their_colour_and_the_legend_shows_the_hatch():
    square = [(0.0, 0.0), (30.0, 0.0), (30.0, 20.0), (0.0, 20.0)]
    hole = [(10.0, 5.0), (20.0, 5.0), (20.0, 15.0), (10.0, 15.0)]
    beside = [(30.0, 0.0), (50.0, 0.0), (50.0, 20.0), (30.0, 20.0)]
    parts = [("plate: aluminium", (0.8, 0.8, 0.8), [[square, hole]], 1.0), ("window: clear", (0.18, 0.44, 0.82), [[beside]], 0.4),
             ("pad: black", (0.02, 0.02, 0.02), [[hole]], 1.0)]
    plain = section.svg("thing: section", [], parts, (0.0, 0.0), (50.0, 20.0))
    assert section.svg("thing: section", [], parts, (0.0, 0.0), (50.0, 20.0), hatch=None, behind=(), arcs=False) == plain
    hatch = section.hatches(parts)
    assert hatch == [(45, 2.0), (135, 2.0), (30, 3.0)]
    text = section.svg("thing: section", [], parts, (0.0, 0.0), (50.0, 20.0), hatch=hatch)
    assert text == section.svg("thing: section", [], parts, (0.0, 0.0), (50.0, 20.0), hatch=hatch)
    # the drawing without a hatch, and lines more: nothing of it is changed or moved
    assert [line for line in text.splitlines() if line in plain.splitlines()] == plain.splitlines()
    root = ET.fromstring(text)
    assert root.get("viewBox") == ET.fromstring(plain).get("viewBox")
    drawn = list(root)
    lines = [p for p in drawn if p.tag == SVG + "path" and p.get("stroke-width") == "0.1" and not p.get("stroke-dasharray")]
    assert len(lines) == 6                                            # a hatch on each part, and one in each square of the legend
    # each part's hatch comes after its faces and before the next part's
    faces = [p for p in drawn if p.tag == SVG + "path" and p.get("fill") != "none"]
    assert [drawn.index(p) for p in faces + lines[:3]] == [3, 5, 7, 4, 6, 8]
    # dark on a light fill and white on a dark one, and never pale: the see-through part's hatch is as dark as any
    assert [(p.get("stroke"), p.get("stroke-opacity"), p.get("opacity")) for p in lines] == [
        ("#1f2933", None, None), ("#1f2933", None, None), ("#ffffff", None, None)] * 2
    # in the file, where one unit is one millimetre and y runs downwards, the lines of the plate are inside it and
    # out of its hole, 2 mm apart, and lean up to the right
    left, bottom = 8.0, max(float(v.split(",")[1]) for v in faces[0].get("d").split() if "," in v)
    for (ax, ay), (bx, by) in strokes(lines[0]):
        for t in (0.1, 0.5, 0.9):
            at = (ax + t * (bx - ax) - left, bottom - (ay + t * (by - ay)))
            assert inside(at, [square, hole]), at
        assert (bx - ax) * (by - ay) < 0 and abs(bx - ax) == pytest.approx(abs(by - ay), abs=0.002)
    across = sorted((ax + ay) / math.sqrt(2) for (ax, ay), _ in strokes(lines[0]))
    steps = [q - p for p, q in zip(across, across[1:]) if q - p > 0.01]          # from one line to the next
    assert len(steps) > 10 and all(step == pytest.approx(2.0, abs=0.005) for step in steps)
    # the window's lean the other way, and the squares of the legend carry the same hatches
    assert all((bx - ax) * (by - ay) > 0 for (ax, ay), (bx, by) in strokes(lines[1]))
    swatches = [r for r in root.iter(SVG + "rect") if r.get("stroke")]
    for swatch, line in zip(swatches, lines[3:]):
        x0, y0 = float(swatch.get("x")), float(swatch.get("y"))
        assert drawn.index(line) == drawn.index(swatch) + 1 and strokes(line)
        for a, b in strokes(line):
            assert all(x0 - 0.001 <= px <= x0 + 5.001 and y0 - 0.001 <= py <= y0 + 3.501 for px, py in (a, b))
    assert all((bx - ax) * (by - ay) < 0 for (ax, ay), (bx, by) in strokes(lines[3]))


def test_edges_behind_the_plane_are_thin_lines_beneath_the_cut_faces():
    square = [(0.0, 0.0), (30.0, 0.0), (30.0, 20.0), (0.0, 20.0)]
    parts = [("plate", (0.2, 0.4, 0.6), [[square]])]
    plain = ET.fromstring(section.svg("thing: section", [], parts, (0.0, 0.0), (30.0, 20.0)))
    behind = [((-10.0, 0.0), (-10.0, 45.0)), ((-10.0, 45.0), (0.0, 50.0), (75.0, 50.0)), ((0.0, 0.0), (30.0, 0.0))]
    text = section.svg("thing: section", [], parts, (0.0, 0.0), (30.0, 20.0), behind=behind)
    root = ET.fromstring(text)
    drawn = list(root)
    thin = [p for p in drawn if p.tag == SVG + "path" and p.get("stroke-width") == "0.08"]
    face = next(p for p in drawn if p.tag == SVG + "path" and p.get("fill") != "none")
    assert len(thin) == 1 and thin[0].get("fill") == "none" and drawn.index(thin[0]) < drawn.index(face)
    assert thin[0].get("d").count("M ") == 3 and thin[0].get("d").count("L ") == 4       # three edges, one of two pieces
    # the sheet holds them: 85 across where the cut alone has the 60 a sheet is at the least, and 30 higher
    grown = [float(a) - float(b) for a, b in zip(root.get("viewBox").split()[2:], plain.get("viewBox").split()[2:])]
    assert grown == [25.0, 30.0]
    # the cut face lies where it lay among them: 10 from the left edge of all that is drawn, on its lower edge
    assert face.get("d").startswith("M 18.0000,72.0000 L 48.0000,72.0000")
    assert thin[0].get("d").startswith("M 8.000,72.000 L 8.000,27.000 M 8.000,27.000 L 18.000,22.000 L 93.000,22.000")
    # how wide and how high what is cut is still says so, from outside everything, with thin lines to the cut
    words = [t.text for t in root.iter(SVG + "text")]
    assert "30.00" in words and "20.00" in words
    red = [p for p in drawn if p.tag == SVG + "path" and p.get("stroke") == "#9b1c31"]
    assert len(red) == 2 and red[0].get("stroke-dasharray") and red[0].get("stroke-width") == "0.1"
    assert red[1].get("d").startswith("M 18.000,18.000 H 48.000") and "M 97.000,52.000 V 72.000" in red[1].get("d")
    assert red[0].get("d") == "M 18.000,52.000 V 20.000 M 48.000,52.000 V 20.000 M 48.000,52.000 H 95.000 M 48.000,72.000 H 95.000"
    # edges that go no further than the cut move nothing: the dimensions stand where they stood
    within = ET.fromstring(section.svg("thing: section", [], parts, (0.0, 0.0), (30.0, 20.0), behind=[((0.0, 0.0), (30.0, 20.0))]))
    assert within.get("viewBox") == plain.get("viewBox")
    assert [p.get("d") for p in within.iter(SVG + "path") if p.get("stroke") == "#9b1c31"] == [
        p.get("d") for p in plain.iter(SVG + "path") if p.get("stroke") == "#9b1c31"]
    # a dimension that was asked for stands above the two of what is cut, as it does without the edges
    asked = section.svg("thing: section", [], parts, (0.0, 0.0), (30.0, 20.0), [("across", (0.0, 0.0), (30.0, 0.0), 30.0, "")],
                        behind=behind)
    blue = [p.get("d") for p in ET.fromstring(asked).iter(SVG + "path") if p.get("stroke") == "#1c4f9b" and not p.get("stroke-dasharray")]
    assert blue[0].startswith("M 18.000,18.000 H 48.000")              # 7 above the red line, which the sheet's 7 more made room for


def arc_centre(start, end, radius, sweep):
    """The centre of an arc of less than half a turn as an SVG file gives it, from one point to another with a
    radius and a sweep flag. With y downwards, the flag 1 goes clockwise as the eye sees it."""
    (x0, y0), (x1, y1) = start, end
    half = math.hypot(x1 - x0, y1 - y0) / 2
    back = math.sqrt(max(radius * radius - half * half, 0.0))
    side = 1 if sweep else -1
    return ((x0 + x1) / 2 - side * back * (y1 - y0) / (2 * half), (y0 + y1) / 2 + side * back * (x1 - x0) / (2 * half))


def arcs_of(d):
    """The arcs of a path's commands: [(start, end, radius, large, sweep)]."""
    words, found, at = d.split(), [], None
    for n, word in enumerate(words):
        if word in ("M", "L"):
            at = tuple(float(v) for v in words[n + 1].split(","))
        elif word == "A":
            radius = float(words[n + 1].split(",")[0])
            large, sweep = (int(v) for v in words[n + 3].split(","))
            end = tuple(float(v) for v in words[n + 4].split(","))
            assert words[n + 1] == f"{radius:.4f},{radius:.4f}" and words[n + 2] == "0"
            found.append((at, end, radius, large, sweep))
            at = end
    return found


def test_a_circular_edge_is_written_as_arcs_when_asked():
    def on(centre, radius, degrees):
        return (centre[0] + radius * math.cos(math.radians(degrees)), centre[1] + radius * math.sin(math.radians(degrees)))

    def along(centre, radius, degrees):
        return section.Along(on(centre, radius, degrees), centre, radius)

    # a plate 40 x 20 with one corner rounded at 5, counter-clockwise, and in it a hole 6 across that is one
    # edge all the way round, clockwise from its seam at 20 degrees
    corner, middle = (35.0, 15.0), (12.0, 10.0)
    plate = [(0.0, 0.0), (40.0, 0.0), (40.0, 15.0)] + [along(corner, 5.0, a) for a in range(10, 90, 10)] + [(35.0, 20.0), (0.0, 20.0)]
    hole = [on(middle, 3.0, 20)] + [along(middle, 3.0, 20 - a) for a in range(15, 360, 15)]
    assert section.arcs_in(plate) == 1 and section.arcs_in(hole) == 1 and section.arcs_in(plate[:3]) == 0
    # an outline that begins in the middle of an arc still has the one
    assert section.arcs_in(plate[5:] + plate[:5]) == 1
    parts = [("plate", (0.2, 0.4, 0.6), [[plate, hole]])]
    straight = section.svg("thing: section", [], parts, (0.0, 0.0), (40.0, 20.0))
    assert " A " not in straight and straight == section.svg("thing: section", [], [("plate", (0.2, 0.4, 0.6), [
        [[tuple(p) for p in plate], [tuple(p) for p in hole]]])], (0.0, 0.0), (40.0, 20.0))
    text = section.svg("thing: section", [], parts, (0.0, 0.0), (40.0, 20.0), arcs=True)
    assert [line for line in text.splitlines() if line not in straight.splitlines()] == [text.splitlines()[4]]
    d = next(p for p in ET.fromstring(text).iter(SVG + "path") if p.get("fill") != "none").get("d")
    outer, inner = (piece.strip() for piece in d.split(" Z")[:2])
    # the plate's lower left corner is at 8, 42 in the file; the rounded corner is one arc of a quarter turn
    assert outer == "M 8.0000,42.0000 L 48.0000,42.0000 L 48.0000,27.0000 A 5.0000,5.0000 0 0,0 43.0000,22.0000 L 8.0000,22.0000"
    assert arc_centre(*arcs_of(outer)[0][:3], arcs_of(outer)[0][4]) == pytest.approx((8.0 + 35.0, 42.0 - 15.0))
    # the hole is four arcs of a quarter turn, the other way round, each about the hole's middle, and closes
    found = arcs_of(inner)
    assert len(found) == 4 and found[0][0] == found[-1][1] and all(arc[2:] == (3.0, 0, 1) for arc in found)
    for start, end, radius, _, sweep in found:
        assert arc_centre(start, end, radius, sweep) == pytest.approx((8.0 + 12.0, 42.0 - 10.0), abs=2e-4)
        assert math.hypot(end[0] - start[0], end[1] - start[1]) == pytest.approx(3.0 * math.sqrt(2), abs=2e-4)
    assert "L" not in inner
    # begun in the middle of an arc, the arc is written in two parts and is the same arc
    turned = section.svg("thing: section", [], [("plate", (0.2, 0.4, 0.6), [[plate[5:] + plate[:5]]])], (0.0, 0.0), (40.0, 20.0), arcs=True)
    d = next(p for p in ET.fromstring(turned).iter(SVG + "path") if p.get("fill") != "none").get("d")
    assert d.count(" A ") == 2 and d.count(" L ") == 4 and d.endswith(" Z")
    assert all(arc_centre(start, end, radius, sweep) == pytest.approx((43.0, 27.0), abs=2e-4) and (large, sweep) == (0, 0)
               for start, end, radius, large, sweep in arcs_of(d))
    # where the arcs reach farthest: the hole on all four sides, the rounded corner no further than its two ends
    assert sorted(section.crests(hole)) == [(9.0, 10.0), (12.0, 7.0), (12.0, 13.0), (15.0, 10.0)]
    assert set(section.crests(plate)) == {(40.0, 15.0), (35.0, 20.0)} and section.crests([tuple(p) for p in hole]) == []
    # the straight pieces end short of them: from the highest of the hole's points to the lowest is less than its 6
    assert max(p[1] for p in hole) - min(p[1] for p in hole) < 6.0 - 0.02


def test_the_options_are_words_alone():
    positional, opts = section.options(["project", "key", "--cut", "+y", "--hatch", "--behind", "--arcs", "--up", "+Y"])
    assert positional == ["project", "key"] and (opts["hatch"], opts["behind"], opts["arcs"], opts["finish"]) == (True, True, True, False)
    assert opts["up"] == "+Y"
    _, opts = section.options(["project", "key", "--cut", "+y"])
    assert (opts["hatch"], opts["behind"], opts["quick"], opts["arcs"]) == (False, False, False, False)
    # the quicker way to find the edges behind the plane goes with them
    assert section.options(["project", "key", "--cut", "+y", "--behind", "--quick"])[1]["quick"] is True
    with pytest.raises(ValueError, match="--quick .* goes with --behind"):
        section.options(["project", "key", "--cut", "+y", "--quick"])


def test_straight_pieces_are_put_end_to_end_into_lines():
    pieces = [((1.0, 0.0), (0.0, 0.0)), ((2.0, 0.0), (2.0, 1.0)), ((1.0, 0.0), (2.0, 0.0)),            # two in line, then a corner
              ((6.0, 5.0), (5.0, 5.0)), ((6.0, 5.0), (6.0, 6.0)), ((6.0, 6.0), (5.0, 6.0)), ((5.0, 6.0), (5.0, 5.0)),   # a ring
              ((10.0, 0.0), (11.0, 0.0)), ((12.0, 0.0), (11.0, 0.0)), ((11.0, 0.0), (11.0, 1.0)),      # three that meet
              ((0.0, 0.0), (1.0, 0.0)), ((3.0, 3.0), (3.0, 3.0))]                                      # one again, one of no length
    lines = section.chained(pieces)
    assert lines == [((0.0, 0.0), (2.0, 0.0), (2.0, 1.0)),                         # the point between the two in line is left out
                     ((5.0, 5.0), (5.0, 6.0), (6.0, 6.0), (6.0, 5.0), (5.0, 5.0)),
                     ((10.0, 0.0), (11.0, 0.0)), ((11.0, 0.0), (11.0, 1.0)), ((11.0, 0.0), (12.0, 0.0))]
    assert section.chained(pieces[::-1]) == lines and section.chained([]) == []
    # a line that turns keeps its points, and one that doubles back keeps the point where it turns round
    bow = [(5 * math.cos(n / 10), 5 * math.sin(n / 10)) for n in range(12)]
    assert section.chained(list(zip(bow, bow[1:]))) == [tuple(bow[::-1])]
    assert section.chained([((0.0, 0.0), (3.0, 0.0)), ((3.0, 0.0), (1.0, 0.0))]) == [((0.0, 0.0), (3.0, 0.0), (1.0, 0.0))]


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
    # dimensions between points of the part, taken into the plane: the ring is 20 across and 5 high, and its
    # bore is 10.5
    out = run(project_copy, "spacer", "--cut", "+y=0", "--measure", "across -10,7,0 10,-3,0 outside; up 0,0,0 0,0,5",
              "--measure", "across -5.25,0,5 5.25,0,5 bore")
    assert "[section] across: 20.000 mm (outside)" in out and "[section] up: 5.000 mm" in out, out
    record = json.loads((pictures / "spacer-section-plus-y.json").read_text())
    assert [(m["kind"], m["value_mm"], m["words"]) for m in record["measures"]] == [
        ("across", 20.0, "outside"), ("up", 5.0, ""), ("across", 10.5, "bore")]
    assert record["measures"][0]["on_sheet_mm"] == [[10.0, 0.0], [-10.0, 0.0]]      # seen from +Y, X runs to the left
    words = [t.text for t in ET.fromstring(drawing.read_text()).iter(SVG + "text")]
    assert "20.00 outside" in words and "10.50 bore" in words and "5.00" in words
    assert "--measure 'up 1,2'" in run(project_copy, "spacer", "--cut", "+y=0", "--measure", "up 1,2")
    run(project_copy, "spacer", "--cut", "+y=0")
    assert drawing.read_bytes() == first and "measures" not in json.loads((pictures / "spacer-section-plus-y.json").read_text())
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


def thin_lines(root):
    """The edges behind the plane as a drawing has them: the one path of thin lines, and its straight pieces."""
    paths = [p for p in root.iter(SVG + "path") if p.get("stroke-width") == "0.08"]
    assert len(paths) == 1 and paths[0].get("fill") == "none"
    pieces = []
    for edge in paths[0].get("d").split("M ")[1:]:
        points = [tuple(float(v) for v in word.split(",")) for word in edge.split() if "," in word]
        pieces += zip(points, points[1:])
    return paths[0], pieces


@with_build123d
def test_a_ring_s_section_is_hatched_and_shows_the_bore_behind_the_plane(project_copy):
    pictures = project_copy / ".cache" / "pictures"
    drawing, record = pictures / "spacer-section-plus-y.svg", pictures / "spacer-section-plus-y.json"
    assert "[section] exit status 0" in run(project_copy, "spacer", "--cut", "+y=0")
    plain, plain_record = drawing.read_bytes(), record.read_bytes()
    out = run(project_copy, "spacer", "--cut", "+y=0", "--hatch", "--behind")
    assert "[section] exit status 0" in out, out
    assert "spacer: 47.500 mm2 in 2 piece(s), hatched at 45 degrees, 2 mm apart" in out and "behind the plane: 10 edge(s) seen" in out, out
    said = json.loads(record.read_text())
    assert said["parts"] == [{"name": "spacer", "area_mm2": pytest.approx(47.5), "pieces": 2,
                              "hatch": {"angle_deg": 45, "spacing_mm": 2.0}}]
    assert said["behind"] == {"edges": 10, "found_on": "the exact surfaces"} and "arcs" not in said
    assert {key: value for key, value in said.items() if key not in ("parts", "behind")} == {
        key: value for key, value in json.loads(plain_record).items() if key != "parts"}
    both = drawing.read_bytes()
    root = ET.fromstring(both)
    assert "Thin lines: the edges seen behind the plane." in [t.text for t in root.iter(SVG + "text")]
    path, pieces = thin_lines(root)
    assert path.get("d").count("M ") == 10
    # seen from +Y the far half of the bore shows between the two cut faces: its rim at the top and at the bottom,
    # 10.5 long. On this sheet the ring's left end is 8 from the edge and its top 40 down.
    assert ((12.75, 40.0), (23.25, 40.0)) in pieces and ((12.75, 45.0), (23.25, 45.0)) in pieces
    # the rest are the edges of the two cut faces themselves, which lie in the plane
    assert all(8.0 <= x <= 28.0 and 40.0 <= y <= 45.0 for piece in pieces for x, y in piece)
    drawn = list(root)
    faces = [p for p in drawn if p.tag == SVG + "path" and p.get("fill") != "none"]
    assert len(faces) == 2 and drawn.index(path) < drawn.index(faces[0])                  # beneath the cut faces
    # the hatch is inside the two rectangles: 4.75 wide from either end of the ring's 20
    hatch = [p for p in drawn if p.tag == SVG + "path" and p.get("stroke-width") == "0.1" and not p.get("stroke-dasharray")]
    assert len(hatch) == 2 and len(strokes(hatch[0])) >= 4
    for a, b in strokes(hatch[0]):
        assert all((8.0 <= x <= 12.75 or 23.25 <= x <= 28.0) and 40.0 <= y <= 45.0 for x, y in (a, b)), (a, b)
    run(project_copy, "spacer", "--cut", "+y=0", "--hatch", "--behind")
    assert drawing.read_bytes() == both and json.loads(record.read_text()) == said        # the same part, the same files
    # the quicker way, on a mesh, finds the same: the bore's rim at the top and at the bottom, each one straight
    # piece though the mesh has it in many, and the outlines of the two cut faces put end to end
    out = run(project_copy, "spacer", "--cut", "+y=0", "--behind", "--quick")
    assert "[section] exit status 0" in out and "found on a mesh" in out, out
    said = json.loads(record.read_text())
    root = ET.fromstring(drawing.read_text())
    path, pieces = thin_lines(root)
    assert said["behind"] == {"edges": path.get("d").count("M "), "found_on": "a mesh"} and 2 <= said["behind"]["edges"] < 10
    assert ((12.75, 40.0), (23.25, 40.0)) in pieces and ((12.75, 45.0), (23.25, 45.0)) in pieces and len(pieces) == 10
    assert all(8.0 <= x <= 28.0 and 40.0 <= y <= 45.0 for piece in pieces for x, y in piece)
    assert "Thin lines: the edges seen behind the plane, found on a mesh." in [t.text for t in root.iter(SVG + "text")]
    quick = drawing.read_bytes()
    run(project_copy, "spacer", "--cut", "+y=0", "--behind", "--quick")
    assert drawing.read_bytes() == quick
    # and without the options the drawing and its record are what they were
    run(project_copy, "spacer", "--cut", "+y=0")
    assert drawing.read_bytes() == plain and record.read_bytes() == plain_record


@with_build123d
def test_a_ring_s_plan_has_its_circles_as_arcs_when_asked(project_copy):
    pictures = project_copy / ".cache" / "pictures"
    drawing, record = pictures / "spacer-section-plus-z.svg", pictures / "spacer-section-plus-z.json"
    assert "[section] exit status 0" in run(project_copy, "spacer", "--cut", "+z")
    plain, plain_record = drawing.read_text(), json.loads(record.read_text())
    assert " A " not in plain and "arcs" not in plain_record
    # the straight pieces end short of where a circle reaches farthest: the ring is 20 across
    low, high = plain_record["extent_on_sheet_mm"]["min"], plain_record["extent_on_sheet_mm"]["max"]
    assert 19.9 < high[1] - low[1] < 20.0 - 1e-3
    out = run(project_copy, "spacer", "--cut", "+z", "--arcs")
    assert "[section] exit status 0" in out and "2 edge(s) of the cut are circular arcs and written as arcs" in out, out
    said = json.loads(record.read_text())
    assert said["arcs"] == 2 and said["parts"] == plain_record["parts"]
    assert said["extent_on_sheet_mm"] == {"min": [pytest.approx(-10.0, abs=1e-9)] * 2, "max": [pytest.approx(10.0, abs=1e-9)] * 2}
    root = ET.fromstring(drawing.read_text())
    assert [t.text for t in root.iter(SVG + "text")].count("20.00") == 2                 # how wide and how high it is
    faces = [p for p in root.iter(SVG + "path") if p.get("fill") != "none"]
    assert len(faces) == 1 and " L " not in faces[0].get("d") and faces[0].get("d").count(" Z") == 2
    found = arcs_of(faces[0].get("d"))
    assert sorted({arc[2] for arc in found}) == [5.25, 10.0] and all(arc[3] == 0 for arc in found)
    # every arc is about the ring's axis, which is 18 from the sheet's left edge and 44 down: the ring's rim and
    # its bore are circles again, each written a quarter turn at a time
    assert len(found) >= 8
    for start, end, radius, _, sweep in found:
        assert arc_centre(start, end, radius, sweep) == pytest.approx((18.0, 44.0), abs=5e-4), (start, end, radius, sweep)
    first = drawing.read_bytes()
    run(project_copy, "spacer", "--cut", "+z", "--arcs")
    assert drawing.read_bytes() == first
    run(project_copy, "spacer", "--cut", "+z")
    assert drawing.read_text() == plain and json.loads(record.read_text()) == plain_record


@with_build123d
def test_an_assembly_s_section_shows_what_stands_behind_the_plane(project_copy):
    pictures = project_copy / ".cache" / "pictures"
    # by the exact surfaces, and by the quicker way on a mesh, whose lines lie within the mesh's 0.02 mm of them
    for quick in ((), ("--quick",)):
        out = run(project_copy, "fixture-with-spacer", "--cut", "-y=0", "--hatch", "--behind", *quick)
        assert "[section] exit status 0" in out, out
        assert "base-plate: 800.000 mm2 in 1 piece(s), hatched at 45 degrees, 2 mm apart" in out and "behind the plane: " in out, out
        record = json.loads((pictures / "fixture-with-spacer-section-minus-y.json").read_text())
        assert [part["name"] for part in record["parts"]] == ["base-plate"]              # the plane cuts the plate alone
        assert record["extent_on_sheet_mm"] == {"min": [-50.0, 0.0], "max": [50.0, 8.0]}
        root = ET.fromstring((pictures / "fixture-with-spacer-section-minus-y.svg").read_text())
        path, pieces = thin_lines(root)
        assert record["behind"] == {"edges": path.get("d").count("M "), "found_on": "a mesh" if quick else "the exact surfaces"}
        assert record["behind"]["edges"] >= (5 if quick else 12)
        # on the sheet: the plate's left end is 8 from the edge, and its top, 8 above its foot, is 70 down
        on_sheet = [((ax - 58.0, 78.0 - ay), (bx - 58.0, 78.0 - by)) for (ax, ay), (bx, by) in pieces]

        def drawn_between(a, b):
            return any(min(math.dist(p, a) + math.dist(q, b), math.dist(p, b) + math.dist(q, a)) < 0.03 for p, q in on_sheet)

        upright = sorted({round(a[0], 1) for a, b in on_sheet if abs(a[0] - b[0]) < 0.03 and abs(a[1] - b[1]) > 1.0})
        # behind the plane stand the two pins at X = -25 and 25, 10 across, and the spacer round the first, 20
        # across: seen from -Y, +X is to the right, and the spacer is on the left
        assert upright == [-50.0, -35.0, -30.0, -20.0, -15.0, 20.0, 30.0, 50.0], (quick, upright)
        assert max(max(a[1], b[1]) for a, b in on_sheet) == pytest.approx(38.0, abs=1e-3)
        assert drawn_between((-30.0, 38.0), (-20.0, 38.0)) and drawn_between((20.0, 38.0), (30.0, 38.0))     # the pins' tops
        assert drawn_between((-30.0, 13.0), (-30.0, 38.0)) and not drawn_between((-30.0, 8.0), (-30.0, 38.0))   # the spacer hides a pin's foot
        # the two dimensions are still the plate's, written beyond the pins
        words = [t.text for t in root.iter(SVG + "text")]
        assert "100.00" in words and "8.00" in words and "38.00" not in words
    # with finishes, cut through the pins: every part its own hatch, the see-through spacer's as dark as the others
    before = None
    for again in (False, True):
        out = run(project_copy, "fixture-with-spacer", "--cut", "-y=12", "--finish", "--hatch", "--behind", "--arcs")
        assert "[section] exit status 0" in out, out
        files = [(pictures / f"fixture-with-spacer-section-minus-y-finish.{kind}").read_bytes() for kind in ("svg", "json")]
        assert not again or files == before                           # the same assembly, the same files
        before = files
    record = json.loads(files[1])
    assert [(part["name"], part["finish"], part["hatch"]) for part in record["parts"]] == [
        ("base-plate", "aluminium", {"angle_deg": 45, "spacing_mm": 2.0}), ("pin", "grey-plastic", {"angle_deg": 135, "spacing_mm": 2.0}),
        ("spacer", "clear-blue", {"angle_deg": 30, "spacing_mm": 3.0})]
    assert record["arcs"] == 0 and record["behind"]["edges"] > 12     # nothing round lies in this plane
    drawn = list(ET.fromstring(files[0]))
    spacer = [n for n, p in enumerate(drawn) if p.tag == SVG + "path" and p.find(SVG + "title") is not None
              and p.find(SVG + "title").text == "spacer: clear-blue"]
    assert len(spacer) == 2 and drawn[spacer[0]].get("fill-opacity") == "0.4"
    hatch = drawn[spacer[1] + 1]
    assert (hatch.get("stroke"), hatch.get("stroke-width"), hatch.get("stroke-opacity"), hatch.get("opacity")) == ("#1f2933", "0.1", None, None)
    assert strokes(hatch)
    # the drawing that tells the parts apart, made without the options, has none of this
    run(project_copy, "fixture-with-spacer", "--cut", "-y=0")
    record = json.loads((pictures / "fixture-with-spacer-section-minus-y.json").read_text())
    assert "behind" not in record and "arcs" not in record and "hatch" not in record["parts"][0]
    assert 'stroke-width="0.08"' not in (pictures / "fixture-with-spacer-section-minus-y.svg").read_text()
