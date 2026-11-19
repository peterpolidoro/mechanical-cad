"""The lines that the round faces of a part or of an assembly's children turn about: where a joint could be.

    FreeCADCmd tools/axes.py --pass PROJECT KEY [-- --child "NAME[/NAME]"] [-- --top N] [-- --min-radius MM]

FreeCADCmd reads dashed options itself, even after --pass; put a bare `--`
before this script's own options.

A joint of the draft `motion.toml` (mechanical_cad/motion.py) is a line: a
point on it and a direction. In CAD that line is nearly always the axis of
something round, a pin, a shaft, a bore, and this tool lists them so that the
numbers can be copied and need not be worked out by hand.

KEY is an assembly or a part of the project. Of an assembly every placed
occurrence is read, or with `--child` only the child of that name (a path
reaches into a sub-assembly) and what is below it; of a part, its file. Every
cylindrical and conical face gives its axis; faces on one line are one row:

    origin_mm [x, y, z]   the point of the line nearest the frame's origin
    direction [x, y, z]   along it, with its first component that is not zero positive
    radii                 the radii of the cylinders on it (a cone is counted, not listed)
    from, to              how far the round faces reach along the line from that point, in millimetres
    whose                 the occurrences they belong to, the one with most round surface first

The rows come with most round surface first, `--top` of them (20 by
default); `--min-radius` leaves out what is thinner, screws and their holes
for example. The numbers are in KEY's own frame, which is the frame a joint
of that assembly is said in. For a joint with `frame = CHILD`, run the tool
on that child's own key.

Nothing is written. This reads geometry and proposes nothing: which of the
lines is a joint, and how far it goes, is for a person to say.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import FreeCAD as App  # noqa: E402
import Part  # noqa: E402

import kernel  # noqa: E402
from mechanical_cad import flatten, layout, solids  # noqa: E402
from mechanical_cad import transforms as T  # noqa: E402

PLACES = 4                  # a line is told from another by its numbers rounded to this many places


def options(argv):
    argv = [a for a in argv if a != "--"]
    opts = {"child": None, "top": 20, "min-radius": 0.0}
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--") and a[2:] in opts and i + 1 < len(argv):
            opts[a[2:]] = argv[i + 1] if a == "--child" else float(argv[i + 1])
            i += 1
        elif a.startswith("--"):
            raise SystemExit(__doc__)
        else:
            positional.append(a)
        i += 1
    if len(positional) != 2 or opts["top"] < 1 or opts["min-radius"] < 0:
        raise SystemExit(__doc__)
    opts["top"] = int(opts["top"])
    return Path(positional[0]), positional[1], opts


def line_of(center, axis):
    """A line as (the point on it nearest the origin, its direction with the first component that is not zero
    positive), each rounded: two faces on one line give the same pair."""
    d = App.Vector(axis)
    d.normalize()
    for c in (d.x, d.y, d.z):
        if abs(c) > 1e-9:
            if c < 0:
                d = d * -1.0
            break
    foot = center - d * center.dot(d)
    zero = lambda v: 0.0 if abs(v) < 0.5 * 10 ** -PLACES else round(v, PLACES)      # noqa: E731
    return (zero(foot.x), zero(foot.y), zero(foot.z)), (zero(d.x), zero(d.y), zero(d.z))


def round_faces(shape):
    """[(line, radius or None for a cone, area, lowest and highest reach along the line)] of a placed shape."""
    out = []
    for face in shape.Faces:
        surface = face.Surface
        if isinstance(surface, Part.Cylinder):
            radius = surface.Radius
        elif isinstance(surface, Part.Cone):
            radius = None
        else:
            continue
        origin, direction = line_of(surface.Center, surface.Axis)
        d, o = App.Vector(*direction), App.Vector(*origin)
        along = [(v.Point - o).dot(d) for v in face.Vertexes] or [0.0]
        out.append(((origin, direction), radius, face.Area, min(along), max(along)))
    return out


def main(argv):
    project_dir, key, opts = options(argv)
    project = layout.load(project_dir)
    comp = project.components.get(key)
    if comp is None:
        print(f"[axes] {project_dir} has no component {key!r}; its keys: {', '.join(sorted(project.components))}")
        return 2
    placed = []                         # (whose, the shape where it is)
    if comp.kind == "part":
        if opts["child"]:
            print(f"[axes] {key} is a part; --child names a child of an assembly")
            return 2
        placed.append((key, kernel.read_step_visible(comp.step_path)[0]))
    else:
        try:
            scene, assets, _ = flatten.flatten(project, key)
        except flatten.FlattenError as exc:
            for line in project.errors:
                print("ERROR  ", line)
            print(f"[axes] {exc}")
            return 2
        shapes = {part: kernel.read_step_visible(path)[0] for part, path in assets}
        child = opts["child"]
        wanted = [o for o in solids.placed(scene) if child is None or o["id"] == child or o["id"].startswith(child + "/")]
        if not wanted:
            print(f"[axes] {key} places nothing named {child!r}; its children: "
                  + ", ".join(sorted({o["id"].split("/", 1)[0] for o in solids.placed(scene)})))
            return 2
        for occurrence in wanted:
            shape = shapes[occurrence["part_id"]].copy()
            shape.transformShape(App.Matrix(*[float(v) for row in occurrence["transform_world"] for v in row]))
            placed.append((occurrence["id"], shape))

    lines = {}
    for whose, shape in placed:
        for line, radius, area, low, high in round_faces(shape):
            if radius is not None and radius < opts["min-radius"]:
                continue
            row = lines.setdefault(line, {"radii": set(), "cones": 0, "area": 0.0, "low": low, "high": high, "whose": {}})
            if radius is None:
                row["cones"] += 1
            else:
                row["radii"].add(round(radius, 3))
            row["area"] += area
            row["low"], row["high"] = min(row["low"], low), max(row["high"], high)
            row["whose"][whose] = row["whose"].get(whose, 0.0) + area
    rows = sorted(lines.items(), key=lambda item: (-item[1]["area"], item[0]))
    for (origin, direction), row in rows[:opts["top"]]:
        whose = sorted(row["whose"], key=lambda w: (-row["whose"][w], w))
        print(f"origin_mm = [{origin[0]:g}, {origin[1]:g}, {origin[2]:g}]  direction = [{direction[0]:g}, {direction[1]:g}, "
              f"{direction[2]:g}]  radii {', '.join(f'{r:g}' for r in sorted(row['radii'])) or 'none'}"
              + (f" and {row['cones']} cone(s)" if row["cones"] else "")
              + f"  from {row['low']:.2f} to {row['high']:.2f}  {whose[0]}"
              + (f" and {len(whose) - 1} more" if len(whose) > 1 else ""))
    what = f"{key}, {opts['child']}" if opts["child"] else key
    print(f"[axes] {what}: {len(rows)} line(s) of round faces over {len(placed)} occurrence(s)"
          + (f", the {opts['top']} with most surface shown" if len(rows) > opts["top"] else "")
          + f", in the frame of {key}")
    return 0


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
    print(f"[axes] exit status {rc}", flush=True)
    sys.exit(rc)
