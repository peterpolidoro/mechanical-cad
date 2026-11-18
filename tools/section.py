"""A section of a part or of an assembly as a drawing: what a plane cuts, every part filled in its colour.

    python3 tools/section.py PROJECT KEY --cut +y [--up +Z] [--out DIR]
    python3 tools/section.py PROJECT KEY --cut -x=12.5
    python3 tools/section.py FILE.step --cut +z

Run it where build123d is (.guix/manifest-build123d.scm).

Where tools/picture.py draws a solid cut open, this draws only what lies in
the cutting plane, true to scale: an SVG file in millimetres, one unit of the
drawing to one millimetre, which a browser shows and a drawing program can
measure and add dimensions to. It carries two dimensions of its own, how wide
and how high all that is cut is, a scale, and a legend. `--cut` names the plane as it does for a
picture: `+y` is the plane through the middle of what is drawn, square to Y,
seen from +Y; `-x=12.5` the plane X = 12.5 seen from -X. `--up` names the
axis that points up on the sheet (+Z unless given); a plane square to that
axis is seen with +Y up.

KEY is a component of the project. An assembly is put together from its
parts' files and the placements the project records, so it need not be built
first; every part gets a colour of its own, the same one tools/picture.py
gives it, and the drawing has a legend. A part by itself, or a file, has one
colour per solid.

The drawing goes to PROJECT/.cache/pictures/KEY-section-plus-y.svg, with
KEY-section-plus-y.json beside it: where the plane is, how the sheet's axes
lie in the model, and for every part the area the plane cuts of it, in
square millimetres, as the kernel measures the cut faces. Neither carries a
timestamp. Curved edges are drawn as short straight pieces (0.02 mm from the
curve at most), so the drawing is for looking and measuring by eye, and the
areas in the record are the kernel's, not the drawing's.

Prints a line per part and a status line.
"""
from __future__ import annotations

import importlib.util
import math
import sys

sys.dont_write_bytecode = True
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from mechanical_cad import jsonio, layout  # noqa: E402

spec = importlib.util.spec_from_file_location("picture_tool", HERE / "picture.py")
picture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(picture)

RECORD_SCHEMA = 1
CHORD_MM = 0.02           # how far a straight piece may lie from the curve it stands for
MARGIN_MM = 8.0
AXIS = {"+X": (1, 0, 0), "-X": (-1, 0, 0), "+Y": (0, 1, 0), "-Y": (0, -1, 0), "+Z": (0, 0, 1), "-Z": (0, 0, -1)}


def options(argv):
    opts = {"cut": None, "up": "+Z", "out": None}
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--") and a[2:] in opts and i + 1 < len(argv):
            opts[a[2:]] = argv[i + 1]
            i += 1
        elif a.startswith("--"):
            raise SystemExit(__doc__)
        else:
            positional.append(a)
        i += 1
    if not 1 <= len(positional) <= 2 or opts["cut"] is None or opts["up"].upper() not in AXIS:
        raise SystemExit(__doc__)
    opts["up"] = opts["up"].upper()
    opts["cut"] = picture.cut_plane(opts["cut"])
    return positional, opts


def sheet_axes(axis, side, up):
    """How a sheet lies in the model for a plane square to `axis`, seen from the side `side`:
    (the direction that runs to the right on the sheet, the one that runs up, the one towards whoever looks)."""
    towards = tuple(side if i == axis else 0 for i in range(3))
    upward = AXIS[up]
    if [abs(c) for c in upward].index(1) == axis:
        upward = AXIS["+Y"] if axis != 1 else AXIS["+Z"]
    right = (upward[1] * towards[2] - upward[2] * towards[1], upward[2] * towards[0] - upward[0] * towards[2],
             upward[0] * towards[1] - upward[1] * towards[0])                  # up x towards
    return right, upward, towards


def outline(wire):
    """A wire's points in order, straight pieces standing for its curves: [(x, y)] in the sheet's millimetres."""
    from build123d import GeomType

    points = []
    for edge in wire.order_edges():
        if edge.geom_type == GeomType.LINE:
            steps = 1
        else:
            # pieces short enough to stay within CHORD_MM of a circle of the edge's own tightest radius
            try:
                radius = edge.radius
            except (ValueError, AttributeError):
                radius = edge.length / (2 * math.pi)
            turn = 2 * math.acos(max(0.0, 1 - CHORD_MM / max(radius, CHORD_MM)))
            steps = max(4, min(720, math.ceil(edge.length / max(radius * turn, 1e-6))))
        for n in range(steps):
            at = edge.position_at(n / steps)
            points.append((at.X, at.Y))
    return points


def settled(loop):
    """A closed outline as it is always written: counter-clockwise, from its lowest point on the left. The kernel
    gives the pieces of a cut, and the edges of a piece, in an order that changes from one run to the next."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(loop, loop[1:] + loop[:1]))
    if area < 0:
        loop = loop[::-1]
    first = min(range(len(loop)), key=lambda i: (round(loop[i][0], 6), round(loop[i][1], 6)))
    return loop[first:] + loop[:first]


def svg(title, lines, parts, low, high):
    """The drawing. `parts` is [(name, (r, g, b), [[outline, ...] per cut face])]; the sheet's y runs upwards,
    an SVG file's downwards, so every y is turned over."""
    legend_rows = len(parts)
    across, tall = high[0] - low[0], high[1] - low[1]
    width = max(across, 60.0) + 2 * MARGIN_MM + 16.0                 # room at the right for the height
    top = MARGIN_MM + 6.0 * (1 + len(lines)) + 8.0                   # and above for the width
    height = top + tall + MARGIN_MM + 12.0 + 5.0 * legend_rows

    def x(v):
        return v - low[0] + MARGIN_MM

    def y(v):
        return top + (high[1] - v)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.3f}mm" height="{height:.3f}mm" '
           f'viewBox="0 0 {width:.3f} {height:.3f}">',
           f'<rect width="{width:.3f}" height="{height:.3f}" fill="#ffffff"/>',
           '<style>text{font-family:DejaVu Sans,Helvetica,Arial,sans-serif;fill:#1f2933}.t{font-size:4px;font-weight:bold}'
           '.s{font-size:3px}</style>',
           f'<text x="{MARGIN_MM}" y="{MARGIN_MM + 3:.1f}" class="t">{escape(title)}</text>']
    for n, line in enumerate(lines):
        out.append(f'<text x="{MARGIN_MM}" y="{MARGIN_MM + 9 + 6 * n:.1f}" class="s">{escape(line)}</text>')
    for name, colour, faces in parts:
        fill = "#" + "".join(f"{round(255 * c):02x}" for c in colour)
        for loops in faces:
            path = " ".join("M " + " L ".join(f"{x(px):.4f},{y(py):.4f}" for px, py in loop) + " Z" for loop in loops)
            out.append(f'<path d="{path}" fill="{fill}" fill-rule="evenodd" stroke="#1f2933" stroke-width="0.15" '
                       f'stroke-linejoin="round"><title>{escape(name)}</title></path>')
    # how wide and how high all of it is, written above and at the right
    left, right_, upper, lower = x(low[0]), x(high[0]), y(high[1]), y(low[1])
    out.append(f'<path d="M {left:.3f},{upper - 4:.3f} H {right_:.3f} M {left:.3f},{upper - 6:.3f} v 4 M {right_:.3f},{upper - 6:.3f} v 4 '
               f'M {right_ + 4:.3f},{upper:.3f} V {lower:.3f} M {right_ + 2:.3f},{upper:.3f} h 4 M {right_ + 2:.3f},{lower:.3f} h 4" '
               'stroke="#9b1c31" stroke-width="0.2" fill="none"/>')
    out.append(f'<text x="{(left + right_) / 2:.3f}" y="{upper - 5:.3f}" class="s" text-anchor="middle" style="fill:#9b1c31">{across:.2f}</text>')
    out.append(f'<text x="{right_ + 5.5:.3f}" y="{(upper + lower) / 2 + 1:.3f}" class="s" style="fill:#9b1c31">{tall:.2f}</text>')
    # a scale: the largest of 1, 2, 5, 10, 20, 50, 100, 200, 500 mm that is no more than a third of the drawing
    span = high[0] - low[0]
    bar = max([b for b in (1, 2, 5, 10, 20, 50, 100, 200, 500) if b <= max(span / 3, 1)])
    base = top + (high[1] - low[1]) + MARGIN_MM
    out.append(f'<path d="M {MARGIN_MM},{base:.2f} h {bar} M {MARGIN_MM},{base - 1.5:.2f} v 3 M {MARGIN_MM + bar},{base - 1.5:.2f} v 3" '
               'stroke="#1f2933" stroke-width="0.3" fill="none"/>')
    out.append(f'<text x="{MARGIN_MM + bar + 2}" y="{base + 1:.2f}" class="s">{bar} mm</text>')
    for n, (name, colour, _) in enumerate(parts):
        fill = "#" + "".join(f"{round(255 * c):02x}" for c in colour)
        row = base + 7 + 5 * n
        out.append(f'<rect x="{MARGIN_MM}" y="{row - 3:.2f}" width="5" height="3.5" fill="{fill}" stroke="#1f2933" stroke-width="0.15"/>')
        out.append(f'<text x="{MARGIN_MM + 7}" y="{row:.2f}" class="s">{escape(name)}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main(argv):
    positional, opts = options(argv)
    if len(positional) == 2:
        project_dir, key = Path(positional[0]), positional[1]
        if key not in layout.load(project_dir).components:
            picture.source(positional)                  # says what the project has, and stops
        stem, default_out = key, project_dir.joinpath(*picture.PICTURES_DIR)
    else:
        _, stem, default_out = picture.source(positional)
    out = Path(opts["out"]) if opts["out"] else default_out
    out.mkdir(parents=True, exist_ok=True)
    placed = picture.placed_solids(positional, out)
    from build123d import Plane, Rectangle

    axis, side, where = opts["cut"]
    (low3, high3), spans = picture.extent(placed)
    where = (low3[axis] + high3[axis]) / 2 if where is None else where
    right, upward, towards = sheet_axes(axis, side, opts["up"])
    origin = tuple(where if i == axis else 0.0 for i in range(3))
    plane = Plane(origin=origin, x_dir=right, z_dir=towards)
    reach = 4 * max(h - l for l, h in zip(low3, high3)) + 10
    sheet = plane * Rectangle(reach, reach)

    cut = {}                                             # name -> [area, [[outline, ...] per face]]
    for (name, solid), (lo, hi) in zip(placed, spans):
        if not lo[axis] - 1e-9 <= where <= hi[axis] + 1e-9:
            continue
        for face in (solid & sheet).faces():
            flat = plane.to_local_coords(face)
            entry = cut.setdefault(name, [0.0, []])
            entry[0] += face.area
            holes = sorted((settled(outline(w)) for w in flat.inner_wires()), key=lambda loop: loop[0])
            entry[1].append([settled(outline(flat.outer_wire()))] + holes)
    for entry in cut.values():
        entry[1].sort(key=lambda loops: loops[0][0])
    if not cut:
        print(f"[section] the plane {'XYZ'[axis]} = {where:g} cuts nothing")
        return 1
    names = {name for name, _ in placed}                 # the colours a picture of the same thing has
    shade = picture.colours(names) if len(names) > 1 else {}
    # a part by itself that is one solid is called by its key, not "solid 0001"
    called = {name: (positional[1] if len(positional) == 2 and len(names) == 1 else name) for name in cut}
    parts = [(called[name], shade.get(name, picture.PLAIN), cut[name][1]) for name in sorted(cut)]
    xs = [p[0] for _, _, faces in parts for loops in faces for loop in loops for p in loop]
    ys = [p[1] for _, _, faces in parts for loops in faces for loop in loops for p in loop]
    name_of = {"+": "plus-", "-": "minus-"}["+" if side > 0 else "-"] + "xyz"[axis]
    stem = f"{stem}-section-{name_of}"
    seen = ("+" if side > 0 else "-") + "XYZ"[axis]
    lines = [f"The plane {'XYZ'[axis]} = {where:g} mm, seen from {seen}. One unit of the drawing is one millimetre.",
             "To the right: " + direction(right) + "; upwards: " + direction(upward) + "."]
    drawing = out / f"{stem}.svg"
    drawing.write_text(svg(f"{positional[-1] if len(positional) == 2 else Path(positional[0]).name}: section", lines,
                           parts, (min(xs), min(ys)), (max(xs), max(ys))), encoding="utf-8")
    for name in sorted(cut):
        print(f"[section] {called[name]}: {cut[name][0]:.3f} mm2 in {len(cut[name][1])} piece(s)")
    record = {"schema_version": RECORD_SCHEMA, "drawing": drawing.name, "length_unit": "mm",
              "plane": {"axis": "XYZ"[axis], "at_mm": where, "seen_from": seen},
              "sheet_in_model": {"right": list(right), "up": list(upward), "origin_mm": list(origin)},
              "extent_on_sheet_mm": {"min": [min(xs), min(ys)], "max": [max(xs), max(ys)]},
              "chord_mm": CHORD_MM,
              "parts": [{"name": called[name], "area_mm2": cut[name][0], "pieces": len(cut[name][1])} for name in sorted(cut)]}
    jsonio.write(out / f"{stem}.json", record)
    print(f"[section] {drawing}")
    return 0


def direction(vector):
    return next(name for name, v in AXIS.items() if tuple(v) == tuple(vector))


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except SystemExit as exc:
        print(exc)
        rc = 2
    except ValueError as exc:
        print(f"[section] {exc}")
        rc = 2
    print(f"[section] exit status {rc}", flush=True)
    sys.exit(rc)
