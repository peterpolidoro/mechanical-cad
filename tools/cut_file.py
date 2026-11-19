"""The file to cut a part from sheet: its outline as a drawing, checked against the solid.

    python3 tools/cut_file.py PROJECT KEY [--kerf 0.2] [--out DIR]
    python3 tools/cut_file.py PROJECT KEY --pattern [--root -z] [--open +z] [--out DIR]     a flat pattern, to cut and fold

Run it where build123d is (.guix/manifest-build123d.scm).

KEY is a part of the project that is a plate cut square through: two flat
faces, parallel and alike, and nothing between them but what stands square to
them, so that a laser, a water jet or a router makes it from sheet in one
pass. Its `part.step` is read and the outline of one of those faces, with
every hole in it, is written as `KEY.dxf` into PROJECT/.cache/cut/, which the
project ignores, with `KEY.cut.json` beside it: what the drawing was made from
and how it compares.

The drawing's frame is the part's own where that can be: for a plate that
lies in the part's X and Y, a point (x, y) of the drawing is the point (x, y)
of the part, and the drawing is the plate seen from +Z. For another plate the
record says where the drawing's origin and axes lie in the part. Lengths are
millimetres, and the file says so.

What is checked, and recorded:

    plate      the solid's volume is the area of that face times the distance
               between the two faces. A pocket, a chamfer, a countersink or a
               wall that leans makes it differ: such a part is not cut in one
               pass, and no drawing is written.
    closed     read back from the file, the lines, arcs and circles of the
               drawing join into closed loops and nothing is left over. A
               cutter follows loops.
    area       the area inside the outer loop less the holes, worked out from
               the file, is the face's.
    extent     the drawing is as wide and as high as the face.

The record carries no timestamp and the file is written with fixed metadata,
so the same part gives the same two files. Prints a line per check and a
status line; the exit status is 0 when every check passed.

Curves. A straight edge of the outline is written as a line, an arc of a
circle as an arc and a whole circle as a circle: a round corner and the round
end of a slot are arcs in the file, not chords, and the area and the extent
are worked out from them as arcs. An ellipse or a spline is not written: a
plate with one in its outline is refused, and no drawing is written.

The width of the cut. A laser, a water jet or a router takes away a strip as
wide as its beam, its jet or its tool, half of it on either side of the line
it follows. `--kerf W` allows for a cut W millimetres wide: the outline is
moved outward by half of W and every hole inward by as much, with an arc
round every corner that sticks out, so that what is left is the part at its
size. The drawing is then not the solid's face, and it is held to that face
moved by the same amount:

    area       the area in the drawing is that of the face with the
               allowance, as the kernel measures it.
    extent     the drawing is as wide and as high as the face with the
               allowance: the face and the width of the cut.
    allowance  read back from the file, every line and arc lies half the
               width from the solid's face at its ends and in its middle, and
               every circle at four points, outside the material; the middle
               of every edge of the face has the drawing half the width away;
               no corner of the face has it nearer; no loop is a line gone
               over twice; and there are as many loops as the face has.

An allowance that closes a hole or a slot is refused, and no drawing is
written: where a hole, a slot, a notch or a round inside corner is not wider
than the cut, an edge of the face is further from the line than half the
width, or the line there encloses nothing, and the cut would not make it. A
slot exactly as wide as the cut is refused with the narrower ones. A sharp
corner that points into the
material, the corner of a window, comes out round with half the width
whatever line is followed; the record counts those. The record says the
width, how far the outline and the holes were moved, and how far the drawing
lies from the face. Without `--kerf` the drawing is the face itself, and the
two files are what they were before there was the option.

What it does not do: an ellipse or a spline (above), several parts laid out
on one sheet, engraved lines, and where a cut begins or in which order the
loops are cut, which is the machine's program.

A flat pattern. With `--pattern`, KEY is a part that is a convex solid with
flat faces: a polyhedron of mechanical_cad/shapes built as a solid, a box and
a prism among them. What is written is the solid's surface laid out in one
plane (mechanical_cad/shapes/unfold.py), to be cut from sheet and folded up
into the solid: `KEY.pattern.dxf` with `KEY.pattern.json` beside it. The
drawing has two layers: `cut`, the outline, and `fold`, the lines along which
two faces stay joined. It is seen from outside the solid, so every fold bends
the sheet away from the viewer, by the angle the record gives for it. `--root`
names the face that is laid first by the axis it faces (+x, -x, +y, -y, +z,
-z): the face the part stands on, -z, unless said. The record says where
that face's corners are in the part and in the drawing.

An open shell. `--open +z` leaves out the face of the part that faces +z
(`--open +z,-y`: two faces), and the pattern is that of the rest of the
surface: a shell that is open where the face was, which is what folded sheet
makes. A tray is a box without its top; half of an enclosure is a solid
without the face in which the halves meet. The part stays the closed solid,
the space the shell goes round. A face is named by the axis it faces
squarely: a part with no face square to that axis is refused, and so is one
whose other faces do not hang together. An edge of a face that is left out is
cut once: it is the rim of the opening. The root is a face that is kept, so a
shell open below needs another (`--open -z --root +z`).

What is checked of a pattern, and recorded:

    polyhedron the part is the convex solid on its corners: that solid's
               volume and area, worked out from the corners without the
               kernel, are the part's, and every face of the part is flat. A
               hollow, a hole or a round face is found by one or the other,
               and no drawing is written.
    closed     read back from the file, the lines of the layer `cut` join
               into closed loops and nothing is left over.
    area       the area inside the outline is the sum of the areas of the
               solid's faces, worked out without the kernel; with faces left
               open, of the faces that are kept.
    length     the outline is as long as the edges that are cut, twice over:
               each is on it once for each of its two faces. The edges round
               a face left open are on it once.
    folds      the layer `fold` has one line fewer than the solid has faces,
               or than are kept; each runs from the outline to the outline,
               inside it, across none of it and touching it nowhere between;
               together they are as long as the edges that are folded.
    open       with `--open`: each face left out is a face of the part. The
               part's flat faces that face that way in that plane, as the
               kernel has them, have the area of the face left out.
    extent, unit   as for a plate.
    layers     nothing in the drawing is on a third layer.

What a pattern does not have: an allowance for the thickness of the sheet or
for the radius of a bend, so it is true for a sheet without thickness and a
bend without radius, an open shell's as much as a closed solid's: folded
from real sheet along these lines, a tray is not the size of its part; tabs,
flanges, or any other way to join the cut edges, since the library lays out
none; a face named other than by an axis it faces squarely; an allowance for
the width of the cut (`--kerf` is for a plate, and is refused here); and a
choice among the patterns a solid has: it is the first of the library's that
lays no face over another.
"""
from __future__ import annotations

import math
import sys

sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mechanical_cad import jsonio, layout, stepfile  # noqa: E402

CUT_DIR = (".cache", "cut")
RECORD_SCHEMA = 1
RELATIVE = 1e-6          # how far the plate's volume, and the drawing's area, may be from the solid's
JOIN_MM = 1e-6           # how far apart two ends may lie and still be one point
PLACE_MM = 1e-6          # how far a line that allows for the width of the cut may lie from where that puts it
SQUARE = 1e-9            # how far the cosine of the angle between a face's normal and an axis may be from 1
LAYER = "cut"
FOLD_LAYER = "fold"
AXES = {"+x": (1.0, 0.0, 0.0), "-x": (-1.0, 0.0, 0.0), "+y": (0.0, 1.0, 0.0), "-y": (0.0, -1.0, 0.0),
        "+z": (0.0, 0.0, 1.0), "-z": (0.0, 0.0, -1.0)}
NOT_IN_A_PATTERN = ["an allowance for the thickness of the sheet", "an allowance for the radius of a bend",
                    "tabs to join the cut edges by"]


def options(argv):
    """((the project, the key), the directory to write to or None, whether a flat pattern is asked for, its root,
    the axes of the faces it leaves open, the width of the cut to allow for or None)."""
    out, pattern, root, left_open, kerf, positional = None, False, "-z", (), None, []
    i = 0
    while i < len(argv):
        if argv[i] == "--out" and i + 1 < len(argv):
            out = argv[i + 1]
            i += 1
        elif argv[i] == "--root" and i + 1 < len(argv):
            root = argv[i + 1].lower()
            i += 1
        elif argv[i] == "--open" and i + 1 < len(argv):
            left_open = tuple(dict.fromkeys(axis.strip().lower() for axis in argv[i + 1].split(",")))
            i += 1
        elif argv[i] == "--kerf" and i + 1 < len(argv):
            try:
                kerf = float(argv[i + 1])
            except ValueError:
                kerf = math.nan
            i += 1
        elif argv[i] == "--pattern":
            pattern = True
        elif argv[i].startswith("--"):
            raise SystemExit(__doc__)
        else:
            positional.append(argv[i])
        i += 1
    if len(positional) != 2 or root not in AXES or any(axis not in AXES for axis in left_open):
        raise SystemExit(__doc__)
    if kerf is not None and not 0.0 < kerf < math.inf:
        raise SystemExit("[cut_file] --kerf is the width of the cut in millimetres, more than 0")
    if kerf is not None and pattern:
        raise SystemExit("[cut_file] --kerf allows for the width of the cut round a plate; "
                         "a flat pattern has no such allowance")
    if left_open and not pattern:
        raise SystemExit("[cut_file] --open names faces that a flat pattern leaves out; give --pattern with it")
    return positional, out, pattern, root, left_open, kerf


# A drawing is a list of pieces, each one of
#     ("line", (x0, y0), (x1, y1))
#     ("arc", (cx, cy), radius, start_deg, end_deg)      counter-clockwise from start to end, as a DXF file has it
#     ("circle", (cx, cy), radius)

def _ends(piece):
    """The two ends of a line or an arc, in the direction it is given."""
    if piece[0] == "line":
        return piece[1], piece[2]
    (cx, cy), r, a0, a1 = piece[1:]
    return tuple((cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in (a0, a1))


def _sweep(piece):
    """How far an arc turns, in radians: more than 0 and at most a full turn."""
    turn = math.radians(piece[4] - piece[3]) % (2 * math.pi)
    return turn if turn > 0 else 2 * math.pi


def length(piece):
    if piece[0] == "line":
        return math.dist(piece[1], piece[2])
    if piece[0] == "circle":
        return 2 * math.pi * piece[2]
    return piece[2] * _sweep(piece)


def _turned(piece, forwards):
    """What a piece adds to the integral of (x dy - y dx) / 2 round a loop, walked forwards or backwards."""
    if piece[0] == "line":
        (x0, y0), (x1, y1) = piece[1], piece[2]
        value = (x0 * y1 - x1 * y0) / 2
    else:
        (cx, cy), r, a0 = piece[1], piece[2], math.radians(piece[3])
        a1 = a0 + _sweep(piece)
        value = (r * cx * (math.sin(a1) - math.sin(a0)) - r * cy * (math.cos(a1) - math.cos(a0)) + r * r * (a1 - a0)) / 2
    return value if forwards else -value


def loops(pieces, join=JOIN_MM):
    """The closed loops a drawing's pieces join into, and the pieces that are in none.

    Returns ([{"area": signed area, "length": ..., "pieces": n, "box": (xmin, ymin, xmax, ymax)}], [left over]).
    A loop is closed when every end in it meets exactly one other end; a piece
    whose end meets none, or more than one, is left over with everything that
    hangs on it. A circle is a loop by itself.
    """
    found, open_pieces = [], []
    lines = []
    for piece in pieces:
        if piece[0] == "circle":
            (cx, cy), r = piece[1], piece[2]
            found.append({"area": math.pi * r * r, "length": length(piece), "pieces": 1,
                          "box": (cx - r, cy - r, cx + r, cy + r)})
        else:
            lines.append(piece)
    ends = [(i, k, p) for i, piece in enumerate(lines) for k, p in enumerate(_ends(piece))]
    partner = {}
    for i, k, p in ends:
        near = [(j, m) for j, m, q in ends if (j, m) != (i, k) and math.dist(p, q) <= join]
        partner[(i, k)] = near[0] if len(near) == 1 else None
    used = set()
    for start in range(len(lines)):
        if start in used:
            continue
        chain, at, closed = [], (start, 0), True
        while True:
            i, k = at
            if i in used:
                closed = closed and i == start and k == 0 and bool(chain)
                break
            used.add(i)
            chain.append((i, k == 0))
            onward = partner[(i, 1 - k)]
            if onward is None or partner[(i, k)] is None:
                closed = False
                if onward is None:
                    break
            at = onward
        if not closed:
            open_pieces.extend(lines[i] for i, _ in chain)
            continue
        xs, ys = [], []
        for i, _ in chain:
            piece = lines[i]
            for x, y in _ends(piece):
                xs.append(x)
                ys.append(y)
            if piece[0] == "arc":
                # An arc reaches furthest where it crosses a direction of an axis, if it does.
                (cx, cy), r = piece[1], piece[2]
                a0, turn = math.radians(piece[3]), _sweep(piece)
                for quarter in range(4):
                    a = quarter * math.pi / 2
                    if (a - a0) % (2 * math.pi) <= turn:
                        xs.append(cx + r * math.cos(a))
                        ys.append(cy + r * math.sin(a))
        found.append({"area": sum(_turned(lines[i], forwards) for i, forwards in chain),
                      "length": sum(length(lines[i]) for i, _ in chain), "pieces": len(chain),
                      "box": (min(xs), min(ys), max(xs), max(ys))})
    return found, open_pieces


def drawing_facts(pieces, join=JOIN_MM):
    """What a drawing is: its loops, whether all of it is closed, the area inside the outer loop less the holes."""
    found, left = loops(pieces, join)
    areas = sorted((abs(loop["area"]) for loop in found), reverse=True)
    boxes = [loop["box"] for loop in found]
    return {"pieces": len(pieces), "loops": len(found), "holes": max(len(found) - 1, 0), "left_over": len(left),
            "closed": bool(found) and not left,
            "area_mm2": areas[0] - sum(areas[1:]) if areas else 0.0,
            "cut_length_mm": sum(loop["length"] for loop in found) + sum(length(p) for p in left),
            "extent_mm": [max(b[2] for b in boxes) - min(b[0] for b in boxes),
                          max(b[3] for b in boxes) - min(b[1] for b in boxes)] if boxes else [0.0, 0.0],
            "min_mm": [min(b[0] for b in boxes), min(b[1] for b in boxes)] if boxes else [0.0, 0.0]}


def _to_segment(p, a, b):
    """The distance from the point p to the segment from a to b."""
    ax, ay = b[0] - a[0], b[1] - a[1]
    square = ax * ax + ay * ay
    t = 0.0 if square == 0.0 else min(1.0, max(0.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / square))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


def _samples(piece):
    """The points a piece is measured at: the ends and the middle of a line or an arc, four points of a circle."""
    if piece[0] == "line":
        (x0, y0), (x1, y1) = piece[1], piece[2]
        return [(x0, y0), ((x0 + x1) / 2, (y0 + y1) / 2), (x1, y1)]
    (cx, cy), r = piece[1], piece[2]
    if piece[0] == "circle":
        angles = [0.0, math.pi / 2, math.pi, 3 * math.pi / 2]
    else:
        a0, turn = math.radians(piece[3]), _sweep(piece)
        angles = [a0, a0 + turn / 2, a0 + turn]
    return [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in angles]


def _to_piece(p, piece):
    """The distance from the point p to a line, an arc or a circle."""
    if piece[0] == "line":
        return _to_segment(p, piece[1], piece[2])
    (cx, cy), r = piece[1], piece[2]
    if piece[0] == "circle" or (math.atan2(p[1] - cy, p[0] - cx) - math.radians(piece[3])) % (2 * math.pi) <= _sweep(piece):
        return abs(math.hypot(p[0] - cx, p[1] - cy) - r)
    return min(math.dist(p, end) for end in _ends(piece))


def inside(point, lines):
    """Whether a point lies inside what a drawing's lines enclose: a ray from it along +x crosses them an odd
    number of times."""
    x, y = point
    crossed = 0
    for _, (x0, y0), (x1, y1) in lines:
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            crossed += 1
    return crossed % 2 == 1


def _cross(a, b, c, d, join):
    """Whether the segment from a to b and the segment from c to d cross, each passing from one side of the other
    to the other side by more than `join`. Two that only touch do not cross."""
    def off(p, q, r):                       # how far r lies to the left of the line from p to q
        return ((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])) / math.dist(p, q)

    def across(one, other):
        return (one > join and other < -join) or (one < -join and other > join)

    return across(off(c, d, a), off(c, d, b)) and across(off(a, b, c), off(a, b, d))


def folds_astray(cut, folds, join=JOIN_MM):
    """The fold lines of a pattern's drawing that are not where a fold is, each as (its number, what is wrong).

    `cut` and `folds` are the pieces of the two layers. A fold line is a straight line that begins and ends on
    the outline, lies inside it, and crosses none of it. Between its ends it does not touch the outline either:
    a line drawn along a side of the outline, or through one of its corners, is no fold. Empty when all do.
    """
    lines = [piece for piece in cut if piece[0] == "line"]
    astray = []
    for k, fold in enumerate(folds):
        if fold[0] != "line":
            astray.append((k, "is not a straight line"))
            continue
        a, b = fold[1], fold[2]
        middle = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if math.dist(a, b) <= join:
            astray.append((k, "has no length"))
        elif not lines or any(min(_to_segment(end, c, d) for _, c, d in lines) > join for end in (a, b)):
            astray.append((k, "does not run from the outline to the outline"))
        elif (any(_to_segment(middle, c, d) <= join for _, c, d in lines)
              or any(_to_segment(p, a, b) <= join < min(math.dist(p, a), math.dist(p, b))
                     for _, c, d in lines for p in (c, d))):
            # Whether a point of the outline is inside it is a matter of rounding, so this is asked first.
            astray.append((k, "touches the outline between its ends"))
        elif not all(inside((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), lines) for t in (0.25, 0.5, 0.75)):
            astray.append((k, "is not inside the outline"))
        elif any(_cross(a, b, c, d, join) for _, c, d in lines):
            astray.append((k, "crosses the outline"))
    return astray


def _pieces(doc, layer=None):
    """The pieces of a drawing's model space, and the kinds of entity it has that are none of the three. With
    `layer`, only what is on that layer."""
    pieces, other = [], {}
    for e in doc.modelspace():
        if layer is not None and e.dxf.layer != layer:
            continue
        kind = e.dxftype()
        if kind == "LINE":
            pieces.append(("line", (e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)))
        elif kind == "ARC":
            pieces.append(("arc", (e.dxf.center.x, e.dxf.center.y), e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle))
        elif kind == "CIRCLE":
            pieces.append(("circle", (e.dxf.center.x, e.dxf.center.y), e.dxf.radius))
        else:
            other[kind] = other.get(kind, 0) + 1
    return pieces, other


def read_dxf(path, layer=None):
    """The pieces of a DXF file's model space, the kinds of entity it has that are none of the three, and its unit.
    With `layer`, only what is on that layer."""
    import ezdxf

    doc = ezdxf.readfile(str(path))
    return *_pieces(doc, layer), doc.header.get("$INSUNITS")


def plate_of(shape, volume):
    """The two faces a plate is cut between, as (the face to draw, the other, thickness); a ValueError otherwise.

    The largest flat face and the largest flat face that looks the other way.
    The one drawn is the one whose normal points along a positive axis more
    than a negative one, so that a plate lying in X and Y is drawn as seen
    from +Z. `volume` is the solid's: a plate cut square through has the
    volume of that face times the distance between the two, and its outline
    is straight lines, arcs of circles and whole circles.
    """
    from build123d import GeomType

    flat = [f for f in shape.faces() if f.geom_type == GeomType.PLANE]
    if not flat:
        raise ValueError("the part has no flat face")
    first = max(flat, key=lambda f: f.area)
    normal = first.normal_at(first.center())
    opposite = [f for f in flat if f.normal_at(f.center()).dot(normal) < -1 + 1e-9]
    if not opposite:
        raise ValueError("the part's largest flat face has no flat face opposite and parallel to it")
    second = max(opposite, key=lambda f: f.area)
    thickness = abs((second.center() - first.center()).dot(normal))
    prism = first.area * thickness
    if abs(first.area - second.area) > RELATIVE * first.area or abs(prism - volume) > RELATIVE * abs(volume):
        raise ValueError(f"its largest face, {first.area:.3f} mm2, times the {thickness:.4f} mm to the face opposite "
                         f"is {prism:.3f} mm3, and the solid is {volume:.3f} mm3. A pocket, a chamfer or a leaning "
                         "wall is not cut from sheet in one pass")
    curved = sorted({e.geom_type.name for e in first.edges() if e.geom_type not in (GeomType.LINE, GeomType.CIRCLE)})
    if curved:
        raise ValueError(f"its outline has edges that are neither straight nor circular ({', '.join(curved)}); "
                         "writing those is not built")
    dominant = max((normal.X, normal.Y, normal.Z), key=abs)
    return (first, second, thickness) if dominant > 0 else (second, first, thickness)


def with_allowance(face, half):
    """The lines a cut follows so that it leaves a flat face: the wires of the face's outline moved outward by
    `half` and of its holes moved inward by as much, with an arc round every corner that sticks out.

    `face` lies in the plane z = 0. Each wire is moved by itself: the outline and the holes move apart, so
    none comes nearer to another. A hole that closes is not among the wires that come back, and one that closes
    in its middle comes back as two; `allowance_kept` finds both, and anything else that is not where it has to
    be. A wire that is one whole circle is made here, as the circle of that much more or less radius: the
    kernel's offset puts such a wire somewhere else when the face has been moved (OpenCASCADE 7.9.3).
    """
    from build123d import Edge, GeomType, Plane, Shape, Wire
    from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffset
    from OCP.GeomAbs import GeomAbs_JoinType

    def moved(wire, by):
        edges = wire.edges()
        if len(edges) == 1 and edges[0].geom_type == GeomType.CIRCLE:
            centre, radius = edges[0].arc_center, edges[0].radius + by
            return [Wire([Edge.make_circle(radius, Plane(origin=(centre.X, centre.Y, 0.0)))])] if radius > 0.0 else []
        builder = BRepOffsetAPI_MakeOffset()
        builder.Init(GeomAbs_JoinType.GeomAbs_Arc)
        builder.AddWire(wire.wrapped)
        try:
            builder.Perform(by)                                  # more than 0: away from what the wire encloses
            made = builder.Shape() if builder.IsDone() else None
        except Exception:  # noqa: BLE001
            made = None                                          # the kernel raises for some wires that close
        return [] if made is None or made.IsNull() else list(Shape(made).wires())

    wires = moved(face.outer_wire(), half)
    for hole in face.inner_wires():
        wires += moved(hole, -half)
    return wires


def _enclosed(wire):
    """The area a closed flat wire encloses; 0 for one that encloses nothing the kernel makes a face of."""
    from build123d import Face

    try:
        return Face(wire).area
    except Exception:  # noqa: BLE001
        return 0.0


def allowance_kept(pieces, face, half, slack=PLACE_MM):
    """How a drawing that allows for the width of a cut lies about the flat face that the cut is to leave.

    `pieces` are the drawing's, `face` the solid's face in the drawing's plane, `half` half the width of the
    cut. Returns a dictionary:

        drawing_from_face_mm    the least and the most distance from the face of the points the drawing is
                                measured at (`_samples`). A point inside the material is at 0. Both are `half`
                                when the cut takes none of the part and no more than it has to.
        edges_from_drawing_mm   the least and the most distance from the drawing of the middles of the face's
                                edges. An edge further than `half` is not made by the cut.
        unreached               those middles, each as (x, y, distance): where a hole, a slot or a round inside
                                corner is narrower than the cut.
        corners_too_near        how many corners of the face have the drawing nearer than `half`.
        inside_corners          how many have it further: sharp corners that point into the material, which a
                                cut of any width leaves round.
        flat_loops              how many loops of the drawing enclose nothing: a line gone over twice.
        loops, face_loops       how many loops the drawing has, and the face.
        passed                  whether all of that is as it has to be.
    """
    from build123d import Vertex

    found, left = loops(pieces)
    from_face = [face.distance_to(Vertex(x, y, 0.0)) for piece in pieces for x, y in _samples(piece)]

    def from_drawing(point):
        return min(_to_piece((point.X, point.Y), piece) for piece in pieces)

    middles = [(middle.X, middle.Y, from_drawing(middle)) for middle in (edge.position_at(0.5) for edge in face.edges())]
    corners = [from_drawing(corner) for corner in face.vertices()]
    kept = {
        "drawing_from_face_mm": [min(from_face), max(from_face)],
        "edges_from_drawing_mm": [min(m[2] for m in middles), max(m[2] for m in middles)],
        "unreached": [m for m in middles if m[2] > half + slack],
        "corners_too_near": sum(1 for d in corners if d < half - slack),
        "inside_corners": sum(1 for d in corners if d > half + slack),
        "flat_loops": sum(1 for loop in found if abs(loop["area"]) <= slack * loop["length"]),
        "loops": len(found), "face_loops": len(face.wires()),
    }
    kept["passed"] = (not left and not kept["unreached"] and not kept["corners_too_near"] and not kept["flat_loops"]
                      and kept["loops"] == kept["face_loops"]
                      and all(abs(d - half) <= slack for d in kept["drawing_from_face_mm"])
                      and kept["edges_from_drawing_mm"][0] >= half - slack)
    return kept


def _save(exporter, path):
    """Write a drawing so that the same drawing gives the same bytes.

    When it saves, ezdxf adds a class record for every kind of entity the document holds, going through a set:
    their order changes from one run of Python to the next. Added here first, in order, they keep that order,
    because a record that is there already is not added again.
    """
    document = exporter._document
    for kind in sorted(document.entitydb.dxf_types_in_use()):
        document.classes.add_class(kind)
    exporter.write(str(path))


def polyhedron_of(shape, name, volume, area):
    """The convex polyhedron a solid is, as a Polyhedron of mechanical_cad/shapes on the solid's corners; a
    ValueError when the solid is none.

    `volume` and `area` are the solid's, as measured. The corners are put in a fixed order, so that the faces
    and the pattern do not depend on the order in which the kernel hands them out. The solid is that polyhedron
    when both have the same volume and the same area: a solid lies within the convex solid on its corners, or
    has round faces that the corners do not show. Every face of the solid has to be flat besides: a round so
    small that volume and area agree all the same would otherwise pass, and leave its corners in the pattern.
    """
    from build123d import GeomType

    from mechanical_cad.shapes import polyhedra

    corners = []
    for point in sorted((v.X, v.Y, v.Z) for v in shape.vertices()):
        if all(math.dist(point, corner) > JOIN_MM for corner in corners):
            corners.append(point)
    try:
        faces = polyhedra.hull(corners)
    except ValueError as exc:
        raise ValueError(f"its {len(corners)} corners bound no solid ({exc})") from None
    inside = len(corners) - len({corner for face in faces for corner in face})
    if inside:
        raise ValueError(f"{inside} of its {len(corners)} corners are not corners of the convex solid on them: the part "
                         "has a hollow or a hole, or a corner in the middle of a face or of an edge")
    solid = polyhedra.from_vertices(name, corners)
    if abs(solid.volume - volume) > RELATIVE * abs(volume) or abs(solid.area - area) > RELATIVE * abs(area):
        raise ValueError(f"the convex solid on its {len(corners)} corners has a volume of {solid.volume:.3f} mm3 and "
                         f"an area of {solid.area:.3f} mm2, and the part {volume:.3f} mm3 and {area:.3f} mm2. A part "
                         "with a hollow, a hole or a round face has no flat pattern here")
    faces = shape.faces()
    curved = [f.geom_type.name for f in faces if f.geom_type != GeomType.PLANE]
    if curved:
        raise ValueError(f"{len(curved)} of its {len(faces)} faces are not flat ({', '.join(sorted(set(curved)))}), "
                         "too small to show in its volume and its area")
    return solid


def face_left_open(shape, solid, axis):
    """(the face of the polyhedron `solid` that faces `axis` squarely, the area of the flat faces of the kernel's
    `shape` that face that way in the same plane); a ValueError when the polyhedron has no such face."""
    from build123d import GeomType, Vector

    from mechanical_cad.shapes import polyhedra

    face = solid.face_towards(AXES[axis])
    lean = polyhedra.dot(solid.normals[face], AXES[axis])
    if lean < 1.0 - SQUARE:
        raise ValueError(f"the part has no face that faces {axis} squarely; the nearest leans "
                         f"{math.degrees(math.acos(max(-1.0, min(1.0, lean)))):.3f} degrees away from it")
    direction, level = Vector(*AXES[axis]), solid.distances[face]
    area = math.fsum(f.area for f in shape.faces() if f.geom_type == GeomType.PLANE
                     and f.normal_at(f.center()).dot(direction) >= 1.0 - SQUARE
                     and abs(f.center().dot(direction) - level) <= JOIN_MM)
    return face, area


def write_pattern(key, comp, shape, out, root, left_open=()):
    """Write the flat pattern of a part that is a convex solid with flat faces, check it and record it (see the
    head of this file). `left_open` are the axes of the faces to leave out. Returns the exit status."""
    import build123d
    import ezdxf
    from build123d import Edge, ExportDXF, Unit
    from build123d.exporters import ColorIndex

    from mechanical_cad.shapes import unfold

    try:
        solid = polyhedron_of(shape, key, comp.facts["volume_mm3"], comp.facts["area_mm2"])
    except ValueError as exc:
        print(f"[cut_file] {key}: NOT A CONVEX SOLID WITH FLAT FACES: {exc}; no drawing is written")
        return 1
    face = solid.face_towards(AXES[root])
    try:
        opened = {axis: face_left_open(shape, solid, axis) for axis in left_open}
    except ValueError as exc:
        print(f"[cut_file] {key}: NO FACE TO LEAVE OPEN: {exc}; no drawing is written")
        return 1
    open_faces = sorted(f for f, _ in opened.values())
    if face in open_faces:
        print(f"[cut_file] {key}: THE FACE LAID FIRST IS LEFT OPEN: the face towards {root} is one of those --open leaves "
              "out; name a face that is kept with --root; no drawing is written")
        return 1
    try:
        pattern = unfold.unfold(solid, face, open_faces)
        loops = unfold.outline(pattern)
    except unfold.UnfoldError as exc:
        print(f"[cut_file] {key}: NO FLAT PATTERN from the face towards {root}: {exc}; no drawing is written")
        return 1
    kept = len(solid.faces) - len(open_faces)
    rim = [cut_edge for cut_edge in pattern.cuts if len(cut_edge.segments) == 1]

    def lines(segments):
        return [Edge.make_line((ax, ay, 0.0), (bx, by, 0.0)) for (ax, ay), (bx, by) in segments]

    out.mkdir(parents=True, exist_ok=True)
    dxf = out / f"{key}.pattern.dxf"
    ezdxf.options.write_fixed_meta_data_for_testing = True       # no time and no random identifier in the file
    exporter = ExportDXF(unit=Unit.MM)
    exporter.add_layer(LAYER)
    exporter.add_layer(FOLD_LAYER, color=ColorIndex.BLUE)        # a colour of their own, so that a viewer tells them apart
    for loop in loops:
        exporter.add_shape(lines(zip(loop, loop[1:] + loop[:1])), layer=LAYER)
    exporter.add_shape(lines(fold.segment for fold in pattern.folds), layer=FOLD_LAYER)
    _save(exporter, dxf)

    cut, _, unit = read_dxf(dxf, LAYER)
    folds, _, _ = read_dxf(dxf, FOLD_LAYER)
    everything, unknown, _ = read_dxf(dxf)
    drawn = drawing_facts(cut)
    edge_length = dict(zip(solid.edges, solid.edge_lengths))
    cut_edges = math.fsum(edge_length[cut_edge.edge] for cut_edge in pattern.cuts)
    folded_edges = math.fsum(edge_length[fold.edge] for fold in pattern.folds)
    fold_length = math.fsum(length(piece) for piece in folds)
    astray = folds_astray(cut, folds)
    # The outline goes round the faces that are kept, along every cut edge once for each of them that has it.
    kept_area = solid.area - math.fsum(solid.face_areas[f] for f in open_faces) if open_faces else solid.area
    outline_length = math.fsum(edge_length[cut_edge.edge] * len(cut_edge.segments) for cut_edge in pattern.cuts)
    area_off = abs(drawn["area_mm2"] - kept_area) / kept_area
    checks = {
        "polyhedron": True,
        "closed": drawn["closed"] and not unknown,
        "area": area_off <= RELATIVE,
        "length": abs(drawn["cut_length_mm"] - outline_length) <= RELATIVE * outline_length,
        "folds": (len(folds) == kept - 1 and not astray
                  and abs(fold_length - folded_edges) <= RELATIVE * folded_edges),
        "extent": (all(abs(a - b) <= 1e-4 for a, b in zip(drawn["extent_mm"], pattern.size))
                   and all(abs(low) <= 1e-4 for low in drawn["min_mm"])),
        "unit": unit == 4,
        "layers": len(everything) == len(cut) + len(folds),
    }
    if open_faces:
        checks["open"] = all(abs(area - solid.face_areas[f]) <= RELATIVE * solid.face_areas[f]
                             for f, area in opened.values())
    counts = dict(zip(("vertices", "edges", "faces"), solid.counts))
    print(f"[cut_file] {key}: the flat pattern of a solid of {counts['faces']} faces, "
          + (f"{len(open_faces)} of them left open (towards {', '.join(opened)}), " if open_faces else "")
          + f"from the face towards {root}; "
          f"{pattern.size[0]:.3f} x {pattern.size[1]:.3f} mm; {drawn['loops']} loop(s), {drawn['cut_length_mm']:.1f} mm of "
          f"cut; {len(folds)} fold line(s), {fold_length:.1f} mm")
    if unknown:
        print(f"[cut_file] {key}: the file holds entities that were NOT CHECKED: {unknown}")
    if not drawn["closed"]:
        print(f"[cut_file] {key}: NOT CLOSED: {drawn['left_over']} piece(s) of the outline are in no closed loop")
    print(f"[cut_file] {key}: area {drawn['area_mm2']:.3f} mm2 inside the outline against the faces' {kept_area:.3f}"
          + (f" (the solid's {solid.area:.3f} less the faces left open)" if open_faces else "")
          + ("" if checks["area"] else ": THEY DIFFER"))
    for axis, (f, area) in opened.items():
        if abs(area - solid.face_areas[f]) > RELATIVE * solid.face_areas[f]:
            print(f"[cut_file] {key}: the face left open towards {axis} has {solid.face_areas[f]:.3f} mm2 by its corners, "
                  f"and the part's flat faces that face that way there have {area:.3f}: THEY DIFFER")
    if not checks["length"]:
        print(f"[cut_file] {key}: the outline is {drawn['cut_length_mm']:.3f} mm long and NOT twice the cut edges"
              + (" and once the rim" if open_faces else "") + f", {outline_length:.3f} mm")
    for k, wrong in astray:
        print(f"[cut_file] {key}: fold line {k} {wrong.upper()}")
    if not checks["folds"] and not astray:
        print(f"[cut_file] {key}: {len(folds)} fold line(s) of {fold_length:.3f} mm together are NOT the "
              f"{kept - 1} folded edges of {folded_edges:.3f} mm")
    if not checks["extent"]:
        print(f"[cut_file] {key}: the drawing's extent {drawn['extent_mm']} from {drawn['min_mm']} IS NOT the pattern's")
    if not checks["unit"]:
        print(f"[cut_file] {key}: the file does NOT say its unit is the millimetre")
    if not checks["layers"]:
        print(f"[cut_file] {key}: {len(everything) - len(cut) - len(folds)} piece(s) of the drawing are on NEITHER layer")
    record = {
        "schema_version": RECORD_SCHEMA, "key": key,
        "step": {"sha256": comp.step_sha256, "data_sha256": comp.step_data_sha256},
        "drawing": {"file": dxf.name, "sha256": stepfile.sha256_file(dxf), "format": "DXF", "length_unit": "mm",
                    "layers": {"cut": LAYER, "fold": FOLD_LAYER}, "other_entities": unknown, **drawn,
                    "fold_lines": len(folds), "fold_length_mm": fold_length},
        "pattern": {
            "seen_from": "outside the solid: every fold bends the sheet away from the viewer",
            "size_mm": list(pattern.size), "faces": kept, "cut_edges": len(pattern.cuts),
            "cut_edges_length_mm": cut_edges, "folded_edges_length_mm": folded_edges,
            "root": {"towards": root, "corners_in_part_mm": [list(p) for p in solid.polygon(face)],
                     "corners_in_drawing_mm": [list(p) for p in pattern.polygons[face]]},
            "folds": [{"from_mm": list(fold.segment[0]), "to_mm": list(fold.segment[1]),
                       "length_mm": edge_length[fold.edge], "angle_deg": math.degrees(fold.angle)}
                      for fold in pattern.folds],
            "without": NOT_IN_A_PATTERN},
        "polyhedron": {**counts, "volume_mm3": solid.volume, "area_mm2": solid.area},
        "solid": {"volume_mm3": comp.facts["volume_mm3"], "area_mm2": comp.facts["area_mm2"]},
        "volume_relative_difference": abs(solid.volume - comp.facts["volume_mm3"]) / comp.facts["volume_mm3"],
        "area_relative_difference": area_off, "tolerance": RELATIVE,
        "tool": {"library": "build123d", "version": build123d.__version__, "dxf": "ezdxf", "dxf_version": ezdxf.__version__},
        "checks": checks, "passed": all(checks.values()),
    }
    if open_faces:
        record["pattern"]["left_open"] = [
            {"towards": axis, "corners_in_part_mm": [list(p) for p in solid.polygon(f)], "area_mm2": solid.face_areas[f],
             "area_of_the_parts_faces_there_mm2": area} for axis, (f, area) in opened.items()]
        record["pattern"]["rim"] = {"edges": len(rim),
                                    "length_mm": math.fsum(edge_length[cut_edge.edge] for cut_edge in rim),
                                    "on_the_outline": "once each; every other cut edge twice"}
        record["pattern"]["kept_area_mm2"] = kept_area
    jsonio.write(out / f"{key}.pattern.json", record)
    print(f"[cut_file] {dxf}")
    return 0 if record["passed"] else 1


def write_plate(key, comp, shape, out, kerf=None):
    """Write the drawing of a part that is a plate cut square through, check it and record it (see the head of
    this file). `kerf` is the width of the cut to allow for, in millimetres, or None. Returns the exit status."""
    import build123d
    import ezdxf
    from build123d import ExportDXF, Plane, Unit, Vector

    solid_volume = comp.facts["volume_mm3"]
    try:
        face, other, thickness = plate_of(shape, solid_volume)
    except ValueError as exc:
        print(f"[cut_file] {key}: NOT A PLATE CUT SQUARE THROUGH: {exc}; no drawing is written")
        return 1
    off = abs(face.area * thickness - solid_volume) / solid_volume

    # The drawing's frame: the part's origin dropped onto the face, x along the part's X where the plate allows it.
    normal = face.normal_at(face.center())
    origin = normal * face.center().dot(normal)
    along = Vector(1, 0, 0) if abs(normal.X) < 0.9 else Vector(0, 1, 0)
    x_dir = (along - normal * along.dot(normal)).normalized()
    frame = Plane(origin=origin, x_dir=x_dir, z_dir=normal)
    flat_face = frame.to_local_coords(face)
    box = flat_face.bounding_box()
    # What is drawn, and the area and the extent it has to have: the face, or the face with the allowance.
    to_draw, to_be_area, to_be_extent = flat_face, face.area, (box.size.X, box.size.Y)
    if kerf is not None:
        to_draw = with_allowance(flat_face, kerf / 2)
        if not to_draw:
            print(f"[cut_file] {key}: NO ALLOWANCE of {kerf:g} mm for the width of the cut: the kernel made nothing of the "
                  "outline moved outward; no drawing is written")
            return 1
        areas = sorted((_enclosed(wire) for wire in to_draw), reverse=True)
        to_be_area = areas[0] - sum(areas[1:])
        boxes = [wire.bounding_box() for wire in to_draw]
        to_be_extent = (max(b.max.X for b in boxes) - min(b.min.X for b in boxes),
                        max(b.max.Y for b in boxes) - min(b.min.Y for b in boxes))

    ezdxf.options.write_fixed_meta_data_for_testing = True       # no time and no random identifier in the file
    exporter = ExportDXF(unit=Unit.MM)
    exporter.add_layer(LAYER)
    exporter.add_shape(to_draw, layer=LAYER)
    if kerf is not None:
        # Held to the face before anything is written: a cut that does not make the part is no drawing of it.
        kept = allowance_kept(_pieces(exporter._document)[0], flat_face, kerf / 2)
        if not kept["passed"]:
            print(f"[cut_file] {key}: A CUT {kerf:g} mm WIDE DOES NOT MAKE THIS PLATE: {_not_kept(kept, kerf / 2)}. A hole, "
                  "a slot, a notch or an inside round that is not wider than the cut closes; no drawing is written")
            return 1
    out.mkdir(parents=True, exist_ok=True)
    dxf = out / f"{key}.dxf"
    _save(exporter, dxf)

    pieces, unknown, unit = read_dxf(dxf)
    drawn = drawing_facts(pieces)
    area_off = abs(drawn["area_mm2"] - to_be_area) / to_be_area
    checks = {
        "plate": True,
        "closed": drawn["closed"] and not unknown,
        "area": area_off <= RELATIVE,
        "extent": all(abs(a - b) <= 1e-4 for a, b in zip(drawn["extent_mm"], to_be_extent)),
        "unit": unit == 4,
    }
    if kerf is not None:
        kept = allowance_kept(pieces, flat_face, kerf / 2)
        checks["allowance"] = kept["passed"]
    print(f"[cut_file] {key}: a plate {thickness:.4f} mm thick, {box.size.X:.3f} x {box.size.Y:.3f} mm; "
          f"{drawn['loops']} loop(s): the outline and {drawn['holes']} hole(s); {drawn['cut_length_mm']:.1f} mm of cut")
    if unknown:
        print(f"[cut_file] {key}: the file holds entities that were NOT CHECKED: {unknown}")
    if not drawn["closed"]:
        print(f"[cut_file] {key}: NOT CLOSED: {drawn['left_over']} piece(s) of the drawing are in no closed loop")
    if kerf is None:
        print(f"[cut_file] {key}: area {drawn['area_mm2']:.3f} mm2 in the drawing against the face's {face.area:.3f}"
              + ("" if checks["area"] else ": THEY DIFFER"))
    else:
        low, high = kept["drawing_from_face_mm"]
        print(f"[cut_file] {key}: allowing for a cut {kerf:g} mm wide: the outline moved outward and the holes inward by "
              f"{kerf / 2:g} mm; the drawing lies {low:.6f} to {high:.6f} mm from the face; {kept['inside_corners']} sharp "
              "inside corner(s) come out round with that radius")
        if not checks["allowance"]:
            print(f"[cut_file] {key}: THE ALLOWANCE IS NOT KEPT in the file: {_not_kept(kept, kerf / 2)}")
        print(f"[cut_file] {key}: area {drawn['area_mm2']:.3f} mm2 in the drawing against {to_be_area:.3f} of the face with "
              f"the allowance (the face itself: {face.area:.3f})" + ("" if checks["area"] else ": THEY DIFFER"))
    if not checks["extent"]:
        print(f"[cut_file] {key}: the drawing's extent {drawn['extent_mm']} IS NOT the face's"
              + ("" if kerf is None else f" with the allowance, {list(to_be_extent)}"))
    if not checks["unit"]:
        print(f"[cut_file] {key}: the file does NOT say its unit is the millimetre")
    record = {
        "schema_version": RECORD_SCHEMA, "key": key,
        "step": {"sha256": comp.step_sha256, "data_sha256": comp.step_data_sha256},
        "drawing": {"file": dxf.name, "sha256": stepfile.sha256_file(dxf), "format": "DXF", "length_unit": "mm",
                    "layer": LAYER, "other_entities": unknown, **drawn},
        "frame_in_part": {"origin_mm": [origin.X, origin.Y, origin.Z], "x": [x_dir.X, x_dir.Y, x_dir.Z],
                          "normal": [normal.X, normal.Y, normal.Z]},
        "plate": {"thickness_mm": thickness, "face_area_mm2": face.area, "extent_mm": [box.size.X, box.size.Y]},
        "solid": {"volume_mm3": solid_volume},
        "volume_relative_difference": off, "area_relative_difference": area_off, "tolerance": RELATIVE,
        "tool": {"library": "build123d", "version": build123d.__version__, "dxf": "ezdxf", "dxf_version": ezdxf.__version__},
        "checks": checks, "passed": all(checks.values()),
    }
    if kerf is not None:
        record["allowance"] = {
            "cut_width_mm": kerf, "outline_moved_outward_mm": kerf / 2, "holes_moved_inward_mm": kerf / 2,
            "corners_that_stick_out": "an arc of that radius round each",
            "face_with_allowance": {"area_mm2": to_be_area, "extent_mm": list(to_be_extent)},
            "drawing_from_face_mm": kept["drawing_from_face_mm"], "edges_from_drawing_mm": kept["edges_from_drawing_mm"],
            "loops": kept["loops"], "face_loops": kept["face_loops"],
            "sharp_inside_corners_left_round": kept["inside_corners"], "tolerance_mm": PLACE_MM,
        }
    jsonio.write(out / f"{key}.cut.json", record)
    print(f"[cut_file] {dxf}")
    return 0 if record["passed"] else 1


def _not_kept(kept, half):
    """In words, what `allowance_kept` found wrong."""
    wrong = []
    if kept["loops"] != kept["face_loops"]:
        wrong.append(f"the drawing has {kept['loops']} loop(s) and the face {kept['face_loops']}")
    if kept["flat_loops"]:
        wrong.append(f"{kept['flat_loops']} loop(s) of the drawing enclose nothing")
    if kept["unreached"]:
        x, y, distance = max(kept["unreached"], key=lambda m: m[2])
        wrong.append(f"the cut does not reach {len(kept['unreached'])} edge(s) of the plate, the furthest {distance:.4f} mm "
                     f"from the line at ({x:.3f}, {y:.3f}) of the drawing, where it would be {half:g} mm")
    if kept["corners_too_near"]:
        wrong.append(f"the line comes nearer than {half:g} mm to {kept['corners_too_near']} corner(s) of the plate")
    low, high = kept["drawing_from_face_mm"]
    if abs(low - half) > PLACE_MM or abs(high - half) > PLACE_MM:
        wrong.append(f"the line lies {low:.6f} to {high:.6f} mm from the face, not {half:g} mm")
    if kept["edges_from_drawing_mm"][0] < half - PLACE_MM:
        wrong.append(f"the line comes within {kept['edges_from_drawing_mm'][0]:.6f} mm of an edge of the plate")
    return "; ".join(wrong) or "the drawing does not close"


def main(argv):
    (project_dir, key), out_dir, pattern, root, left_open, kerf = options(argv)
    project_dir = Path(project_dir)
    project = layout.load(project_dir)
    comp = project.components.get(key)
    if comp is None or comp.kind != "part":
        print(f"[cut_file] {project_dir} has no part {key!r}")
        return 2
    if comp.facts is None or comp.step_sha256 is None or comp.facts.get("step", {}).get("sha256") != comp.step_sha256:
        print(f"[cut_file] {key}: no facts.json of the part.step that is there; build or measure the part first")
        return 2
    if stepfile.invisible_items(comp.step_path.read_bytes()):
        print(f"[cut_file] {key}: the STEP file marks items invisible; a part to cut has none")
        return 2
    from build123d import import_step

    shape = import_step(str(comp.step_path))
    if len(shape.solids()) != 1:
        print(f"[cut_file] {key}: {len(shape.solids())} solids; a part to cut is one")
        return 2
    out = Path(out_dir) if out_dir else project_dir.joinpath(*CUT_DIR)
    if pattern:
        return write_pattern(key, comp, shape, out, root, left_open)
    return write_plate(key, comp, shape, out, kerf)


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except Exception as exc:  # noqa: BLE001
        print(f"[cut_file] FAILED: {exc}")
        rc = 1
    print(f"[cut_file] exit status {rc}")
    sys.exit(rc)
