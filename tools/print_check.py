"""Will a part print as it stands: what rests on the plate, which faces hang over, and what starts in mid-air.

    FreeCADCmd tools/print_check.py --pass PROJECT KEY [-- --up +Z] [-- --angle 45] [-- --step 0.5] [-- --bridge MM] [-- --out DIR]
    FreeCADCmd tools/print_check.py --pass FILE.step   [-- --up +Z] [-- --angle 45] [-- --step 0.5] [-- --bridge MM] [-- --out FILE.json]

FreeCADCmd reads dashed options itself, even after --pass; put a bare `--`
before each of this script's own options. It needs FreeCAD alone
(.guix/manifest-cad.scm).

KEY is a part of the project; its `part.step` is read, without the items it
marks invisible. The part is taken to be printed as it lies in its own frame,
growing along `--up` (+Z unless another axis is named), with the build plate
through its lowest point. A part that is to be printed another way up is
either written that way up, with its placement in an assembly turning it to
where it belongs, or checked with `--up`.

Three screens of the geometry, each recorded:

    plate      the part's lowest level and its height above it, and the area
               of the flat faces that lie on the plate. A part that meets the
               plate in an edge or a point has none, and that is a fault.
    overhang   every face that looks down at less than `--angle` degrees above
               the plate (45 unless given), other than those on the plate. 0
               is a flat ceiling, 90 an upright wall. A flat face has one
               direction; a curved face is looked at over a mesh of it
               (`--deflection`, 0.1 mm), by the surface's own normal, and a
               triangle that lies across the limit is divided further, so that
               the part of a face that hangs over is found and measured where
               the rest of it does not. An allowance
               of 0.05 degree keeps a face made at exactly the angle from
               failing on the last digit. With `--bridge MM` a flat ceiling
               is not held against the part when a printer can lay it across:
               it is no wider than MM where it is narrowest, and at both ends
               of that width there is a wall under its edge. Such a ceiling
               is listed as a bridge. Without the option every flat ceiling
               hangs over, as before.
    islands    material that begins above the plate with nothing under it. The
               part is cut into thin slices (0.02 mm) every `--step` (0.5 mm)
               from half a step up; every separate piece of a slice has to
               lie over material of the slice before it. A piece that does
               not is the foot of something that starts in mid-air, and is
               reported with its height, its area and where it is. Faces that
               all pass the angle can still enclose such a piece: where
               sloping roofs meet from several sides, the material between
               them first appears as a point.

What this is not: a slicer's verdict or a process qualification. The slices
are samples: a piece thinner than the sideways shift of one step (a leaning
wall thinner than `step / tan(angle)`) can be reported without cause, and a
start between two samples is seen only once it has grown into the next one.
Minimum walls, heat and warping, adhesion and supports chosen by a slicer are
not looked at, and a bridge only as `--bridge` says: by its width, measured
every five degrees round, and by what is under its two ends, not along its
whole edge. How far a printer bridges is the printer's and the material's;
no width is assumed. Use the printer's layer height as `--step` before a
real print, and a slicer after.

The record, `KEY.check.json` beside the print file in PROJECT/.cache/print/,
carries no timestamp, so checking an unchanged part again writes the same
bytes. Printed: a line per finding and a status line. The exit status is 0
when the three screens pass, 1 when one does not, 2 when the command cannot
be run; FreeCADCmd does not hand it on reliably, so read the status line.
"""
from __future__ import annotations

import math
import sys

sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402

import kernel  # noqa: E402
from mechanical_cad import jsonio, layout, stepfile  # noqa: E402

RECORD_SCHEMA = 1
PRINT_DIR = (".cache", "print")
# The two axes that complete each build direction to a right-handed frame: (first, second, up).
FRAMES = {"+Z": ((1, 0, 0), (0, 1, 0), (0, 0, 1)), "-Z": ((0, 1, 0), (1, 0, 0), (0, 0, -1)),
          "+X": ((0, 1, 0), (0, 0, 1), (1, 0, 0)), "-X": ((0, 0, 1), (0, 1, 0), (-1, 0, 0)),
          "+Y": ((0, 0, 1), (1, 0, 0), (0, 1, 0)), "-Y": ((1, 0, 0), (0, 0, 1), (0, -1, 0))}
LEVEL_TOL_MM = 1e-6             # a point this near the lowest level is on the plate
DOWN_TOL = 1e-7                 # a normal has to point down by more than this to count as looking down
ANGLE_ALLOWANCE_DEG = 0.05
SUBDIVIDE = 3                   # how often a triangle of a mesh that lies across a border is divided in four
SLICE_MM = 0.02
PIECE_MIN_MM3 = 1e-8            # a piece of a slice smaller than this is not a piece
SUPPORT_MIN_MM3 = 1e-9          # ... and it is held when it shares more than this with the slice before
FLAT_TOL = 1e-9                 # a normal this near straight down is a flat ceiling
BRIDGE_PROBE_MM = 0.05          # how far beyond and below a ceiling's edge the wall that carries it is looked for
BRIDGE_TOL_MM = 1e-6


def options(argv):
    argv = [a for a in argv if a != "--"]
    opts = {"up": "+Z", "angle": 45.0, "step": 0.5, "deflection": 0.1, "bridge": 0.0, "out": None}
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--") and a[2:] in opts and i + 1 < len(argv):
            name, value = a[2:], argv[i + 1]
            try:
                opts[name] = value if name in ("up", "out") else float(value)
            except ValueError:
                raise SystemExit(__doc__) from None
            i += 1
        elif a.startswith("--"):
            raise SystemExit(__doc__)
        else:
            positional.append(a)
        i += 1
    if len(positional) not in (1, 2) or opts["up"] not in FRAMES:
        raise SystemExit(__doc__)
    if not (0.0 < opts["angle"] <= 90.0 and opts["step"] > SLICE_MM and opts["deflection"] > 0.0 and opts["bridge"] >= 0.0):
        raise SystemExit("[print_check] the angle is above 0 and at most 90 degrees, the step more than the slice of "
                         f"{SLICE_MM} mm, the deflection positive, a bridge's width not negative")
    return positional, opts


def stood_up(shape, up):
    """The shape turned so that it grows along +Z from Z = 0, and what brings a point back to the part's frame:
    (shape, the level of the plate along `up` in the part's frame, back(point) -> [x, y, z])."""
    first, second, third = FRAMES[up]
    turned = shape.copy()
    turned.transformShape(App.Matrix(first[0], first[1], first[2], 0, second[0], second[1], second[2], 0,
                                     third[0], third[1], third[2], 0, 0, 0, 0, 1))
    level = turned.optimalBoundingBox(True, False).ZMin        # the box of the shape itself, not of its mesh
    turned.translate(App.Vector(0, 0, -level))
    level = round(level, 9) + 0.0

    def back(p):
        z = p.z + level
        return [p.x * first[i] + p.y * second[i] + z * third[i] + 0.0 for i in range(3)]

    return turned, level, back


def kind(z, angle):
    """What a normal with the upward part z does: 0 it does not look down, 1 it looks down at the angle or
    steeper, 2 it looks down flatter than the angle."""
    if z >= -DOWN_TOL:
        return 0
    return 2 if math.degrees(math.acos(min(1.0, -z))) < angle - ANGLE_ALLOWANCE_DEG else 1


def looks(face, angle, deflection):
    """Where a face looks: [(the normal's upward part, area, a point)] over the face.

    A flat face is one entry. A curved one is meshed, and the surface's own normal is taken at the corners and
    the middle of each triangle. A triangle whose samples agree (all not looking down, all at the angle or
    steeper, all flatter) is one entry, with its flattest sample; one that lies across a border is divided in
    four, up to SUBDIVIDE times, so that the area on each side of the border is measured and not guessed from
    one point.
    """
    if isinstance(face.Surface, Part.Plane):
        u0, u1, v0, v1 = face.ParameterRange
        return [(face.normalAt((u0 + u1) / 2.0, (v0 + v1) / 2.0).z, face.Area, face.CenterOfMass)]
    surface = face.Surface

    def upward(point):
        try:
            return face.normalAt(*surface.parameter(point)).z
        except Exception:                               # where the surface has no normal: the tip of a cone
            return None

    out = []

    def take(corners, depth):
        (a, za), (b, zb), (c, zc) = corners
        middle = (a + b + c) * (1.0 / 3.0)
        samples = [(z, q) for z, q in ((za, a), (zb, b), (zc, c), (upward(middle), middle)) if z is not None]
        if not samples:
            return
        kinds = {kind(z, angle) for z, _ in samples}
        if len(kinds) > 1 and depth > 0:
            ab, bc, ca = (a + b) * 0.5, (b + c) * 0.5, (c + a) * 0.5
            ab, bc, ca = (ab, upward(ab)), (bc, upward(bc)), (ca, upward(ca))
            for part in ((corners[0], ab, ca), (ab, corners[1], bc), (ca, bc, corners[2]), (ab, bc, ca)):
                take(part, depth - 1)
            return
        area = (b - a).cross(c - a).Length / 2.0
        if area > 0.0:
            # one kind throughout: its flattest sample stands for it; a small one still across a border: its last
            # sample, which is its middle wherever the surface has a normal there
            z, q = min(samples, key=lambda s: s[0]) if len(kinds) == 1 else samples[-1]
            out.append((z, area, q))

    points, triangles = face.tessellate(deflection)
    at_corner = [upward(q) for q in points]
    for i, j, k in triangles:
        take(((points[i], at_corner[i]), (points[j], at_corner[j]), (points[k], at_corner[k])), SUBDIVIDE)
    # the triangles cut a curved face short: each stands for its share of the face's own area
    meshed = math.fsum(area for _, area, _ in out)
    scale = face.Area / meshed if meshed > 0.0 else 0.0
    return [(z, area * scale, q) for z, area, q in out]


def bridge_of(shape, face):
    """A flat ceiling as a bridge: (how wide it is where it is narrowest, whether a wall stands under its edge
    at both ends of that width). The width is the least of the face's extents in directions five degrees
    apart, each the face's own and not a mesh's; the wall is looked for a little beyond each end and a little
    below the ceiling."""
    best = None
    for step in range(36):
        turned = face.copy()
        turned.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), -5.0 * step)       # the direction looked along is now X
        box = turned.optimalBoundingBox(True, False)
        if best is None or box.XLength < best[0] - BRIDGE_TOL_MM:
            best = (box.XLength, step, box.XMin, box.XMax)
    width, step, low, high = best
    angle = math.radians(5.0 * step)
    d = App.Vector(math.cos(angle), math.sin(angle), 0.0)
    points = [q for edge in face.OuterWire.Edges for q in edge.discretize(Number=120)]
    z = points[0].z
    held = True
    for end, sign in ((low, -1.0), (high, 1.0)):
        q = min(points, key=lambda q: sign * (end - q.dot(d)))                       # the point of the edge furthest that way
        probe = q + d * (end - q.dot(d) + sign * BRIDGE_PROBE_MM)
        held = held and shape.isInside(App.Vector(probe.x, probe.y, z - BRIDGE_PROBE_MM), BRIDGE_TOL_MM, False)
    return width, held


def overhang_screen(shape, angle, deflection, back, bridge=0.0):
    """(what lies on the plate, the faces that look down, those below the angle). With `bridge`, a width in
    millimetres, flat ceilings no wider than it and held at both ends are listed as bridges instead."""
    plate_area, plate_faces = 0.0, 0
    down_faces, down_area, lowest = 0, 0.0, 90.0
    below, bridges = [], []
    for number, face in enumerate(shape.Faces):
        if face.Vertexes and max(v.Point.z for v in face.Vertexes) <= LEVEL_TOL_MM:
            if isinstance(face.Surface, Part.Plane):
                plate_area += face.Area
                plate_faces += 1
            continue
        if bridge > 0.0 and isinstance(face.Surface, Part.Plane):
            (z, area, point), = looks(face, angle, deflection)
            if z <= -1.0 + FLAT_TOL:
                width, held = bridge_of(shape, face)
                if held and width <= bridge + BRIDGE_TOL_MM:
                    down_faces += 1
                    down_area += area
                    lowest = 0.0
                    bridges.append({"face": number, "area_mm2": area, "width_mm": width, "at": back(point)})
                    continue
        face_down, face_below, face_lowest, worst = 0.0, 0.0, 90.0, None
        for z, area, point in looks(face, angle, deflection):
            if z >= -DOWN_TOL:
                continue
            tilt = math.degrees(math.acos(min(1.0, -z)))
            face_down += area
            if tilt < face_lowest:
                face_lowest, worst = tilt, point
            if tilt < angle - ANGLE_ALLOWANCE_DEG:
                face_below += area
        if face_down > 0.0:
            down_faces += 1
            down_area += face_down
            lowest = min(lowest, face_lowest)
            if face_below > 0.0:
                below.append({"face": number, "surface": type(face.Surface).__name__, "area_mm2": face.Area,
                              "area_below_the_angle_mm2": face_below, "lowest_angle_deg": face_lowest,
                              "at": back(worst)})
    plate = {"faces": plate_faces, "area_mm2": plate_area}
    screen = {"angle_deg": angle, "allowance_deg": ANGLE_ALLOWANCE_DEG, "mesh_deflection_mm": deflection,
              "faces_looking_down": down_faces, "area_looking_down_mm2": down_area,
              "lowest_angle_deg": lowest if down_faces else None,
              "area_below_the_angle_mm2": math.fsum(f["area_below_the_angle_mm2"] for f in below),
              "below_the_angle": below}
    if bridge > 0.0:                    # a record made without the option is what it was
        screen.update(bridge_mm=bridge, bridges=bridges)
    return plate, screen


def layer_screen(shape, height, step, back):
    """The pieces of thin slices, every `step` from half a step up, that lie over nothing of the slice before."""
    box = shape.BoundBox
    reach = 2.0 * max(box.XLength, box.YLength) + 10.0
    corner = App.Vector(box.Center.x - reach / 2.0, box.Center.y - reach / 2.0, 0.0)
    previous, islands, samples = None, [], 0
    while (samples + 0.5) * step < height:
        h = (samples + 0.5) * step
        samples += 1
        slab = Part.makeBox(reach, reach, SLICE_MM, corner + App.Vector(0, 0, h))
        section = shape.common(slab)
        if previous is not None:
            previous.translate(App.Vector(0, 0, step))
            for piece in section.Solids:
                if piece.Volume > PIECE_MIN_MM3 and piece.common(previous).Volume < SUPPORT_MIN_MM3:
                    islands.append({"height_mm": h, "area_mm2": piece.Volume / SLICE_MM, "at": back(piece.CenterOfMass)})
        previous = section
    return {"step_mm": step, "slice_mm": SLICE_MM, "first_sample_mm": step / 2.0, "samples": samples, "islands": islands}


def check(shape, up, angle, step, deflection, bridge=0.0):
    turned, level, back = stood_up(shape, up)
    height = round(turned.optimalBoundingBox(True, False).ZMax, 9)
    plate, overhang = overhang_screen(turned, angle, deflection, back, bridge)
    layers = layer_screen(turned, height, step, back)
    checks = {"plate": plate["area_mm2"] > 0.0, "overhang": not overhang["below_the_angle"],
              "islands": not layers["islands"]}
    return {"up": up, "plate": dict(plate, level_mm=level, build_height_mm=height),
            "overhang": overhang, "layers": layers, "checks": checks, "passed": all(checks.values())}


def main(argv):
    positional, opts = options(argv)
    if len(positional) == 2:
        project_dir, key = Path(positional[0]), positional[1]
        project = layout.load(project_dir)
        comp = project.components.get(key)
        if comp is None or comp.kind != "part":
            print(f"[print_check] {project_dir} has no part {key!r}")
            return 2
        if comp.step_sha256 is None:
            print(f"[print_check] {key}: no part.step; build the part first")
            return 2
        path, name = comp.step_path, key
        identity = {"key": key, "step": {"sha256": comp.step_sha256, "data_sha256": comp.step_data_sha256}}
        out = (Path(opts["out"]) if opts["out"] else project_dir.joinpath(*PRINT_DIR)) / f"{key}.check.json"
    else:
        path = Path(positional[0])
        if not path.is_file():
            print(f"[print_check] {path}: no such file")
            return 2
        name = path.name
        data = path.read_bytes()
        identity = {"file": path.name, "step": {"sha256": stepfile.sha256_bytes(data), "data_sha256": stepfile.data_sha256(data)}}
        out = Path(opts["out"]) if opts["out"] else None
    shape = kernel.read_step_visible(path)[0]
    if not shape.Solids:
        print(f"[print_check] {name}: the file has no solid")
        return 2
    result = check(shape, opts["up"], opts["angle"], opts["step"], opts["deflection"], opts["bridge"])
    plate, overhang, layers = result["plate"], result["overhang"], result["layers"]
    print(f"[print_check] {name}: grows along {opts['up']} from {plate['level_mm']:g} mm, {plate['build_height_mm']:.4f} mm high; "
          + (f"{plate['faces']} flat face(s) of {plate['area_mm2']:.3f} mm2 on the plate" if result["checks"]["plate"]
             else "NO FLAT FACE ON THE PLATE"))
    for f in overhang["below_the_angle"]:
        print(f"OVERHANG      face {f['face']} ({f['surface']}): {f['area_below_the_angle_mm2']:.3f} mm2 at down to "
              f"{f['lowest_angle_deg']:.2f} degrees above the plate, at {[round(c, 3) for c in f['at']]}")
    for f in overhang.get("bridges", ()):
        print(f"BRIDGE        face {f['face']}: a flat ceiling of {f['area_mm2']:.3f} mm2, {f['width_mm']:.3f} mm across where it "
              f"is narrowest, at {[round(c, 3) for c in f['at']]}")
    lowest = overhang["lowest_angle_deg"]
    bridged = len(overhang.get("bridges", ()))
    print(f"[print_check] {name}: {overhang['faces_looking_down']} face(s) look down, {overhang['area_looking_down_mm2']:.3f} mm2, "
          + ("none of them" if lowest is None else f"the flattest at {lowest:.4f} degrees") + "; "
          + (f"{len(overhang['below_the_angle'])} BELOW {opts['angle']:g} degrees, {overhang['area_below_the_angle_mm2']:.3f} mm2"
             if overhang["below_the_angle"] else f"none below {opts['angle']:g} degrees")
          + (f", {bridged} flat ceiling(s) taken as bridges of up to {opts['bridge']:g} mm" if bridged else ""))
    for island in layers["islands"]:
        print(f"ISLAND        at {island['height_mm']:g} mm above the plate: {island['area_mm2']:.4f} mm2 with nothing "
              f"under it, at {[round(c, 3) for c in island['at']]}")
    print(f"[print_check] {name}: {layers['samples']} slice(s) every {layers['step_mm']:g} mm; "
          + (f"{len(layers['islands'])} PIECE(S) START IN MID-AIR" if layers["islands"] else "nothing starts in mid-air"))
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        jsonio.write(out, {"schema_version": RECORD_SCHEMA, **identity, "tool": kernel.tool(), **result})
        print(f"[print_check] {out}")
    return 0 if result["passed"] else 1


def _is_entry():
    here = Path(__file__).resolve()
    return any(a and Path(a).resolve() == here for a in sys.argv[:2])


if _is_entry():
    if "--pass" in sys.argv:
        args = sys.argv[sys.argv.index("--pass") + 1:]
    else:
        args = [a for a in sys.argv[1:] if Path(a).resolve() != Path(__file__).resolve()]
    try:
        rc = main(args)
    except SystemExit as exc:
        print(exc)
        rc = 2
    except BaseException:
        import traceback

        traceback.print_exc()
        rc = 1
    print(f"[print_check] exit status {rc}", flush=True)
    sys.exit(rc)
