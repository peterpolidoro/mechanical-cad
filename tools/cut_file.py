"""The file to cut a part from sheet: its outline as a drawing, checked against the solid.

    python3 tools/cut_file.py PROJECT KEY [--out DIR]

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


def options(argv):
    out, positional = None, []
    i = 0
    while i < len(argv):
        if argv[i] == "--out" and i + 1 < len(argv):
            out = argv[i + 1]
            i += 1
        elif argv[i].startswith("--"):
            raise SystemExit(__doc__)
        else:
            positional.append(argv[i])
        i += 1
    if len(positional) != 2:
        raise SystemExit(__doc__)
    return positional, out


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


def read_dxf(path):
    """The pieces of a DXF file's model space, the kinds of entity it has that are none of the three, and its unit."""
    import ezdxf

    doc = ezdxf.readfile(str(path))
    pieces, other = [], {}
    for e in doc.modelspace():
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


def main(argv):
    (project_dir, key), out_dir = options(argv)
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

    out = Path(out_dir) if out_dir else project_dir.joinpath(*CUT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    dxf = out / f"{key}.dxf"
    ezdxf.options.write_fixed_meta_data_for_testing = True       # no time and no random identifier in the file
    exporter = ExportDXF(unit=Unit.MM)
    exporter.add_layer(LAYER)
    exporter.add_shape(flat_face, layer=LAYER)
    # When it saves, ezdxf adds a class record for every kind of entity the document holds, going through a set:
    # their order changes from one run of Python to the next. Added here first, in order, they keep that order,
    # because a record that is there already is not added again.
    document = exporter._document
    for kind in sorted(document.entitydb.dxf_types_in_use()):
        document.classes.add_class(kind)
    exporter.write(str(dxf))

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
