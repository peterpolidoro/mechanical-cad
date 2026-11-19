"""The file to cut a part from sheet: its outline as a drawing, checked against the solid.

    python3 tools/cut_file.py PROJECT KEY [--out DIR]
    python3 tools/cut_file.py PROJECT KEY --pattern [--root -z] [--out DIR]      a solid's flat pattern, to cut and fold

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

What it does not do: curves other than straight lines and circles (an
ellipse or a spline in the outline is refused), an allowance for the width of
the cut, several parts laid out on one sheet, and engraved lines.

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

What is checked of a pattern, and recorded:

    polyhedron the part is the convex solid on its corners: that solid's
               volume and area, worked out from the corners without the
               kernel, are the part's. A hollow, a hole or a round face makes
               them differ, and no drawing is written.
    closed     read back from the file, the lines of the layer `cut` join
               into closed loops and nothing is left over.
    area       the area inside the outline is the sum of the areas of the
               solid's faces, worked out without the kernel.
    length     the outline is as long as the edges that are cut, twice over:
               each is on it once for each of its two faces.
    folds      the layer `fold` has one line fewer than the solid has faces;
               each runs from the outline to the outline, inside it and
               across none of it; together they are as long as the edges that
               are folded.
    extent, unit   as for a plate.
    layers     nothing in the drawing is on a third layer.

What a pattern does not have: an allowance for the thickness of the sheet or
for the radius of a bend, so it is true for a sheet without thickness and a
bend without radius; tabs, or any other way to join the cut edges, since the
library lays out none; and a choice among the patterns a solid has: it is
the first of the library's that lays no face over another.
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
LAYER = "cut"
FOLD_LAYER = "fold"
AXES = {"+x": (1.0, 0.0, 0.0), "-x": (-1.0, 0.0, 0.0), "+y": (0.0, 1.0, 0.0), "-y": (0.0, -1.0, 0.0),
        "+z": (0.0, 0.0, 1.0), "-z": (0.0, 0.0, -1.0)}
NOT_IN_A_PATTERN = ["an allowance for the thickness of the sheet", "an allowance for the radius of a bend",
                    "tabs to join the cut edges by"]


def options(argv):
    """((the project, the key), the directory to write to or None, whether a flat pattern is asked for, its root)."""
    out, pattern, root, positional = None, False, "-z", []
    i = 0
    while i < len(argv):
        if argv[i] == "--out" and i + 1 < len(argv):
            out = argv[i + 1]
            i += 1
        elif argv[i] == "--root" and i + 1 < len(argv):
            root = argv[i + 1].lower()
            i += 1
        elif argv[i] == "--pattern":
            pattern = True
        elif argv[i].startswith("--"):
            raise SystemExit(__doc__)
        else:
            positional.append(argv[i])
        i += 1
    if len(positional) != 2 or root not in AXES:
        raise SystemExit(__doc__)
    return positional, out, pattern, root


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
    the outline, lies inside it, and crosses none of it. Empty when all do.
    """
    lines = [piece for piece in cut if piece[0] == "line"]
    astray = []
    for k, fold in enumerate(folds):
        if fold[0] != "line":
            astray.append((k, "is not a straight line"))
            continue
        a, b = fold[1], fold[2]
        if not lines or any(min(_to_segment(end, c, d) for _, c, d in lines) > join for end in (a, b)):
            astray.append((k, "does not run from the outline to the outline"))
        elif not all(inside((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])), lines) for t in (0.25, 0.5, 0.75)):
            astray.append((k, "is not inside the outline"))
        elif any(_cross(a, b, c, d, join) for _, c, d in lines):
            astray.append((k, "crosses the outline"))
    return astray


def read_dxf(path, layer=None):
    """The pieces of a DXF file's model space, the kinds of entity it has that are none of the three, and its unit.
    With `layer`, only what is on that layer."""
    import ezdxf

    doc = ezdxf.readfile(str(path))
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
    return pieces, other, doc.header.get("$INSUNITS")


def plate_of(shape, volume):
    """The two faces a plate is cut between, as (the face to draw, the other, thickness); a ValueError otherwise.

    The largest flat face and the largest flat face that looks the other way.
    The one drawn is the one whose normal points along a positive axis more
    than a negative one, so that a plate lying in X and Y is drawn as seen
    from +Z. `volume` is the solid's: a plate cut square through has the
    volume of that face times the distance between the two, and its outline
    is straight lines and circles.
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
    has round faces that the corners do not show.
    """
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
    return solid


def write_pattern(key, comp, shape, out, root):
    """Write the flat pattern of a part that is a convex solid with flat faces, check it and record it (see the
    head of this file). Returns the exit status."""
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
        pattern = unfold.unfold(solid, face)
        loops = unfold.outline(pattern)
    except unfold.UnfoldError as exc:
        print(f"[cut_file] {key}: NO FLAT PATTERN from the face towards {root}: {exc}; no drawing is written")
        return 1

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
    area_off = abs(drawn["area_mm2"] - solid.area) / solid.area
    checks = {
        "polyhedron": True,
        "closed": drawn["closed"] and not unknown,
        "area": area_off <= RELATIVE,
        "length": abs(drawn["cut_length_mm"] - 2.0 * cut_edges) <= RELATIVE * 2.0 * cut_edges,
        "folds": (len(folds) == len(solid.faces) - 1 and not astray
                  and abs(fold_length - folded_edges) <= RELATIVE * folded_edges),
        "extent": (all(abs(a - b) <= 1e-4 for a, b in zip(drawn["extent_mm"], pattern.size))
                   and all(abs(low) <= 1e-4 for low in drawn["min_mm"])),
        "unit": unit == 4,
        "layers": len(everything) == len(cut) + len(folds),
    }
    counts = dict(zip(("vertices", "edges", "faces"), solid.counts))
    print(f"[cut_file] {key}: the flat pattern of a solid of {counts['faces']} faces, from the face towards {root}; "
          f"{pattern.size[0]:.3f} x {pattern.size[1]:.3f} mm; {drawn['loops']} loop(s), {drawn['cut_length_mm']:.1f} mm of "
          f"cut; {len(folds)} fold line(s), {fold_length:.1f} mm")
    if unknown:
        print(f"[cut_file] {key}: the file holds entities that were NOT CHECKED: {unknown}")
    if not drawn["closed"]:
        print(f"[cut_file] {key}: NOT CLOSED: {drawn['left_over']} piece(s) of the outline are in no closed loop")
    print(f"[cut_file] {key}: area {drawn['area_mm2']:.3f} mm2 inside the outline against the faces' {solid.area:.3f}"
          + ("" if checks["area"] else ": THEY DIFFER"))
    if not checks["length"]:
        print(f"[cut_file] {key}: the outline is {drawn['cut_length_mm']:.3f} mm long and NOT twice the cut edges, "
              f"{2.0 * cut_edges:.3f} mm")
    for k, wrong in astray:
        print(f"[cut_file] {key}: fold line {k} {wrong.upper()}")
    if not checks["folds"] and not astray:
        print(f"[cut_file] {key}: {len(folds)} fold line(s) of {fold_length:.3f} mm together are NOT the "
              f"{len(solid.faces) - 1} folded edges of {folded_edges:.3f} mm")
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
            "size_mm": list(pattern.size), "faces": len(pattern.polygons), "cut_edges": len(pattern.cuts),
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
    jsonio.write(out / f"{key}.pattern.json", record)
    print(f"[cut_file] {dxf}")
    return 0 if record["passed"] else 1


def main(argv):
    (project_dir, key), out_dir, pattern, root = options(argv)
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
    import build123d
    import ezdxf
    from build123d import ExportDXF, Plane, Unit, Vector, import_step

    shape = import_step(str(comp.step_path))
    if len(shape.solids()) != 1:
        print(f"[cut_file] {key}: {len(shape.solids())} solids; a part to cut is one")
        return 2
    out = Path(out_dir) if out_dir else project_dir.joinpath(*CUT_DIR)
    if pattern:
        return write_pattern(key, comp, shape, out, root)
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

    out.mkdir(parents=True, exist_ok=True)
    dxf = out / f"{key}.dxf"
    ezdxf.options.write_fixed_meta_data_for_testing = True       # no time and no random identifier in the file
    exporter = ExportDXF(unit=Unit.MM)
    exporter.add_layer(LAYER)
    exporter.add_shape(flat_face, layer=LAYER)
    _save(exporter, dxf)

    pieces, unknown, unit = read_dxf(dxf)
    drawn = drawing_facts(pieces)
    box = flat_face.bounding_box()
    area_off = abs(drawn["area_mm2"] - face.area) / face.area
    checks = {
        "plate": True,
        "closed": drawn["closed"] and not unknown,
        "area": area_off <= RELATIVE,
        "extent": all(abs(a - b) <= 1e-4 for a, b in zip(drawn["extent_mm"], (box.size.X, box.size.Y))),
        "unit": unit == 4,
    }
    print(f"[cut_file] {key}: a plate {thickness:.4f} mm thick, {box.size.X:.3f} x {box.size.Y:.3f} mm; "
          f"{drawn['loops']} loop(s): the outline and {drawn['holes']} hole(s); {drawn['cut_length_mm']:.1f} mm of cut")
    if unknown:
        print(f"[cut_file] {key}: the file holds entities that were NOT CHECKED: {unknown}")
    if not drawn["closed"]:
        print(f"[cut_file] {key}: NOT CLOSED: {drawn['left_over']} piece(s) of the drawing are in no closed loop")
    print(f"[cut_file] {key}: area {drawn['area_mm2']:.3f} mm2 in the drawing against the face's {face.area:.3f}"
          + ("" if checks["area"] else ": THEY DIFFER"))
    if not checks["extent"]:
        print(f"[cut_file] {key}: the drawing's extent {drawn['extent_mm']} IS NOT the face's")
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
    jsonio.write(out / f"{key}.cut.json", record)
    print(f"[cut_file] {dxf}")
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except Exception as exc:  # noqa: BLE001
        print(f"[cut_file] FAILED: {exc}")
        rc = 1
    print(f"[cut_file] exit status {rc}")
    sys.exit(rc)
