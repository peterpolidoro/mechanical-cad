"""A section of a part or of an assembly as a drawing: what a plane cuts, every part filled in its colour.

    python3 tools/section.py PROJECT KEY --cut +y [--up +Z] [--out DIR] [--finish]
    python3 tools/section.py PROJECT KEY --cut +y --measure "across 0,0,0 40,0,12 gap; up 0,0,0 0,0,21"
    python3 tools/section.py PROJECT KEY --cut -x=12.5
    python3 tools/section.py PROJECT KEY --cut +y --hatch --behind [--quick] --arcs
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
colour per solid. With `--finish` every part is filled in the colour of the
finish the project gives it in its finishes.toml, as a picture made with
`--finish` shows it, what lets through what lies behind it drawn paler; the
legend names each part's finish, and a part that is given none is plain and
said to have none. The drawing is then KEY-section-plus-y-finish.svg, and its
record has each part's finish, null for none.

`--measure` writes a dimension into the drawing between two points of the
model, given as X,Y,Z in millimetres in the frame the drawing is made in (a
part's own; for an assembly the one its built file has, Z up). Where they lie
along the axis the plane is square to does not matter: they are taken into
the plane. `across A B` is how far apart they are along the sheet, from left
to right, `up A B` how far apart from bottom to top, and `A B` alone the
straight distance between them; words after the points are written beside
the number. The option may be given more than once, and one value may hold
several, divided by `;`. The ones across stand above the drawing and the ones
up at its right, each with thin lines to the two points; the record lists
them with their values.

Three options make the drawing more of a section as a draughtsman draws
one, and a fourth goes with the second. None changes the drawing's name;
without them the drawing and its record are what they were before there
were any.

`--hatch` hatches every cut face over its colour: thin lines that lean one
way and lie one distance apart all over a part, so that all its pieces are
seen to be one part, and that differ from part to part. There are eighteen
hatches, six ways to lean and 1.5, 2 or 3 mm apart, which is a length on the
sheet whatever is drawn. The parts take them in the legend's order, and a
part passes over the hatches of its neighbours before it, the parts whose
outlines come within about a millimetre of its own: two parts side by side
are hatched differently while there are hatches enough. The lines end at the
face's outline and at its holes. They are dark on a light fill and white on a
dark one and never pale, so a part that lets light through is hatched as
clearly as any other. The legend shows each part's hatch, and the record has
its angle and how far apart its lines are.

`--behind` draws, in thin lines beneath the cut faces, the edges that
whoever looks at the cut sees behind its plane: of the half the cut leaves,
what no face covers, and the outline of every curved face. The sheet grows
to hold the edges, and the two dimensions of what is cut stand outside
them. The record says how many edges the drawing has and how they were
found, and the tool prints how long that took. They are found by the
kernel's hidden-line removal on the exact surfaces, through build123d's
`project_to_viewport`; an edge shorter than 0.01 mm is left out. That takes
no time for a part or two and very long for an assembly: the mechanical
example of 37 parts, 152 solids, cut at its middle, took 91 s seen from +X
(82 solids with 5455 faces behind the plane) and had not ended after 45
minutes seen from +Y, when it was stopped (2026-11-19, on a machine busy
with other work).

`--quick` with `--behind` finds the edges with the kernel's other
hidden-line removal, on a mesh of the half behind the plane that lies
within 0.02 mm of its surfaces: 20 to 45 s for either view of that example
on the same busy machine, the cutting of the solids the plane goes through
among them. The lines are the same to the eye. They are straight pieces put
end to end, and a curved face's outline runs along the sides of triangles,
within the mesh's 0.02 mm of where it belongs. The mesh is looked at a
hundred-thousandth of a radian askew, without which outlines were lost
beside faces seen on edge; so an edge 100 mm behind the plane lies a
thousandth of a millimetre from its place, and of two edges that lie one
behind the other both may be drawn, which made the lines of that example
4 % longer in all. The outline of a ball came with two gaps near the ends
of its axis.

`--arcs` writes every cut edge that is a circular arc as an arc, not as the
straight pieces that stand for it otherwise, so that a drawing program finds
a circle where the part has one; the two dimensions and the record's extent
then reach as far as the arcs do, which the straight pieces fall short of by
up to 0.02 mm at each end. The record says how many edges were written so.
Other curves, the hatch's ends on a curve and the edges behind the plane
stay straight pieces.

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
import time

sys.dont_write_bytecode = True
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from mechanical_cad import finishes, jsonio, layout  # noqa: E402

spec = importlib.util.spec_from_file_location("picture_tool", HERE / "picture.py")
picture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(picture)

RECORD_SCHEMA = 1
CHORD_MM = 0.02           # how far a straight piece may lie from the curve it stands for
MARGIN_MM = 8.0
AXIS = {"+X": (1, 0, 0), "-X": (-1, 0, 0), "+Y": (0, 1, 0), "-Y": (0, -1, 0), "+Z": (0, 0, 1), "-Z": (0, 0, -1)}
INK = "#1f2933"           # what outlines and words are drawn in
HATCH_DEG = (45, 135, 30, 150, 60, 120)   # how a hatch's lines lean, counter-clockwise from the sheet's right
HATCH_MM = (2.0, 3.0, 1.5)                # and how far apart they are, on the sheet
HATCH_FROM = 0.382        # where the first line lies, in spacings from the sheet's origin: no line of any hatch
                          # then runs along an edge that a part drawn in round numbers has
HATCH_LEAST_MM = 0.1      # a piece of a line shorter than this is a dot, and is left out
NEAR_MM = 1.0             # parts whose outlines come about this near each other are neighbours
BEHIND_TURN = 0.1         # how far an edge behind the plane may turn in one straight piece, in radians
BEHIND_LEAST_MM = 0.01    # an edge behind the plane shorter than this is left out
BEHIND_ASKEW = 1e-5       # how far from square to the sheet a mesh is looked at, in radians
STRAIGHT_MM = 0.002       # a point this near the straight way between its neighbours is not a corner


def measures(texts):
    """What `--measure` asks for, as [(kind, (x, y, z), (x, y, z), words)]: `kind` is "across", "up" or
    "between". Each text may hold several, divided by `;`."""
    out = []
    for piece in (piece.strip() for text in texts for piece in text.split(";")):
        if not piece:
            continue
        words = piece.split()
        kind = words.pop(0) if words[0] in ("across", "up", "between") else "between"
        try:
            a, b = (tuple(float(v) for v in word.split(",")) for word in words[:2])
            if len(words) < 2 or len(a) != 3 or len(b) != 3:
                raise ValueError
        except ValueError:
            raise ValueError(f"--measure {piece!r}: expected [across|up] X,Y,Z X,Y,Z and, if wanted, words to write "
                             "beside the number") from None
        out.append((kind, a, b, " ".join(words[2:])))
    return out


def options(argv):
    opts = {"cut": None, "up": "+Z", "out": None, "finish": False, "measure": [], "hatch": False, "behind": False,
            "quick": False, "arcs": False}
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--finish", "--hatch", "--behind", "--quick", "--arcs"):
            opts[a[2:]] = True
        elif a == "--measure" and i + 1 < len(argv):
            opts["measure"].append(argv[i + 1])
            i += 1
        elif a.startswith("--") and a[2:] in opts and i + 1 < len(argv):
            opts[a[2:]] = argv[i + 1]
            i += 1
        elif a.startswith("--"):
            raise SystemExit(__doc__)
        else:
            positional.append(a)
        i += 1
    if not 1 <= len(positional) <= 2 or opts["cut"] is None or opts["up"].upper() not in AXIS:
        raise SystemExit(__doc__)
    if opts["quick"] and not opts["behind"]:
        raise ValueError("--quick is a quicker way to find the edges behind the plane: it goes with --behind")
    opts["up"] = opts["up"].upper()
    opts["cut"] = picture.cut_plane(opts["cut"])
    opts["measure"] = measures(opts["measure"])
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


class Along(tuple):
    """A point of an outline that lies along a circular arc and is not an end of it: (x, y) as any other, and it
    knows the arc's centre and radius, so that `--arcs` can write the arc as one."""

    def __new__(cls, point, centre, radius):
        self = super().__new__(cls, point)
        self.centre, self.radius = centre, radius
        return self


def outline(wire):
    """A wire's points in order, straight pieces standing for its curves: [(x, y)] in the sheet's millimetres.
    The points between the ends of a circular arc are `Along` it."""
    from build123d import GeomType

    points = []
    for edge in wire.order_edges():
        centre = None
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
            if edge.geom_type == GeomType.CIRCLE:
                centre = (edge.arc_center.X, edge.arc_center.Y)
        for n in range(steps):
            at = edge.position_at(n / steps)
            points.append(Along((at.X, at.Y), centre, radius) if centre is not None and n else (at.X, at.Y))
    return points


def settled(loop):
    """A closed outline as it is always written: counter-clockwise, from its lowest point on the left. The kernel
    gives the pieces of a cut, and the edges of a piece, in an order that changes from one run to the next."""
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(loop, loop[1:] + loop[:1]))
    if area < 0:
        loop = loop[::-1]
    first = min(range(len(loop)), key=lambda i: (round(loop[i][0], 6), round(loop[i][1], 6)))
    return loop[first:] + loop[:first]


def with_arcs(loop, x, y):
    """A closed outline as the commands of a path, its circular arcs written as arcs: the points `Along` one
    arc are left out, and the arc goes from the point before them to the point after in pieces of about a
    quarter turn at the most, each ending on one of them. A piece that short is drawn where it belongs
    though its ends are written to four places. `x` and `y` take a point of the sheet into the file, where y
    runs downwards: an arc that turns counter-clockwise on the sheet has the sweep flag 0."""
    def at(point):
        return f"{x(point[0]):.4f},{y(point[1]):.4f}"

    def turned(centre, p, q):
        ax, ay, bx, by = p[0] - centre[0], p[1] - centre[1], q[0] - centre[0], q[1] - centre[1]
        return math.atan2(ax * by - ay * bx, ax * bx + ay * by)

    out = ["M " + at(loop[0])]
    n = 1
    while n <= len(loop):
        first = n
        while n < len(loop) and isinstance(loop[n], Along):
            n += 1
        run = loop[first - 1:n] + [loop[n % len(loop)]]              # one end, the points along the arc, the other end
        if len(run) > 2:
            total = sum(turned(run[1].centre, p, q) for p, q in zip(run, run[1:]))
            pieces = min(len(run) - 1, max(1, math.ceil(abs(total) / (math.pi / 2) - 1e-9)))
            for piece in range(1, pieces + 1):
                end = run[(piece * (len(run) - 1) + pieces // 2) // pieces]
                out.append(f"A {run[1].radius:.4f},{run[1].radius:.4f} 0 0,{0 if total > 0 else 1} {at(end)}")
        elif n < len(loop):
            out.append("L " + at(loop[n]))
        n += 1
    return " ".join(out) + " Z"


def arcs_in(loop):
    """How many circular arcs a closed outline has: its runs of points `Along` one, a run that goes round the
    outline's first point counted once."""
    along = [isinstance(point, Along) for point in loop]
    return sum(1 for n, mark in enumerate(along) if mark and not along[n - 1])


def crests(loop):
    """Where the circular arcs of a closed outline reach farthest upwards, downwards, to the left and to the
    right: [(x, y)], points of the arcs themselves. The straight pieces that stand for an arc end short of
    them, by CHORD_MM at the most."""
    found = []
    for p, q in zip(loop, loop[1:] + loop[:1]):
        on = q if isinstance(q, Along) else p if isinstance(p, Along) else None
        if on is None:
            continue
        (cx, cy), radius = on.centre, on.radius
        # a piece goes a quarter turn round its centre at the most: it passes over or under the centre where
        # its ends lie to either side of it, and on the side its middle lies
        if (p[0] - cx) * (q[0] - cx) <= 0:
            found.append((cx, cy + radius if p[1] + q[1] > 2 * cy else cy - radius))
        if (p[1] - cy) * (q[1] - cy) <= 0:
            found.append((cx + radius if p[0] + q[0] > 2 * cx else cx - radius, cy))
    return found


def hatch_kinds():
    """Every hatch there is, as [(degrees, millimetres)]: how its lines lean and how far apart they are on the
    sheet. No two are alike, and each leans another way than the one before it."""
    return [(HATCH_DEG[n % len(HATCH_DEG)], HATCH_MM[(n // len(HATCH_DEG) + n % len(HATCH_DEG) // 2) % len(HATCH_MM)])
            for n in range(len(HATCH_DEG) * len(HATCH_MM))]


def neighbours(parts):
    """Which parts lie beside which in a drawing, as {n: {m, ...}} of their places in `parts`: two whose
    outlines come about NEAR_MM near each other. Every outline is walked in steps of half that, and what
    comes into one square of the sheet, NEAR_MM wide, or into two that touch, is near."""
    squares = {}
    for n, (_, _, faces, *_) in enumerate(parts):
        for loop in (loop for loops in faces for loop in loops):
            for (x0, y0), (x1, y1) in zip(loop, loop[1:] + loop[:1]):
                steps = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / (NEAR_MM / 2)))
                for step in range(steps):
                    i = math.floor((x0 + (x1 - x0) * step / steps) / NEAR_MM)
                    j = math.floor((y0 + (y1 - y0) * step / steps) / NEAR_MM)
                    for square in ((i + di, j + dj) for di in (-1, 0, 1) for dj in (-1, 0, 1)):
                        squares.setdefault(square, set()).add(n)
    near = {n: set() for n in range(len(parts))}
    for found in squares.values():
        for n in found:
            near[n] |= found - {n}
    return near


def hatches(parts):
    """A hatch for every part of a drawing, [(degrees, millimetres)] in the order of `parts`. A part takes the
    kind that comes to it by its place, or the next after it that none of its neighbours before it has, so
    that two parts side by side are hatched differently as long as there are kinds enough."""
    kinds, near, given = hatch_kinds(), neighbours(parts), []
    for n in range(len(parts)):
        taken = {given[m] for m in near[n] if m < n}
        mine = [kinds[(n + k) % len(kinds)] for k in range(len(kinds))]
        given.append(next((kind for kind in mine if kind not in taken), mine[0]))
    return given


def hatch_lines(loops, degrees, apart):
    """The lines of a hatch inside one cut face, [((x, y), (x, y))] on the sheet: `loops` is the face's outline
    and its holes, and a line runs where it is inside an odd number of them, which is where the face is
    filled. The lines are counted from the sheet's origin, so the pieces of one part carry one hatch."""
    lean = math.radians(degrees)
    along, across = (math.cos(lean), math.sin(lean)), (-math.sin(lean), math.cos(lean))
    met = {}                                             # a line's number -> where outlines cross it, along the line
    for loop in loops:
        turned = [(px * along[0] + py * along[1], (px * across[0] + py * across[1]) / apart - HATCH_FROM)
                  for px, py in loop]
        for (t0, c0), (t1, c1) in zip(turned, turned[1:] + turned[:1]):
            for k in range(math.ceil(min(c0, c1)), math.ceil(max(c0, c1))):     # an end on a line counts once
                met.setdefault(k, []).append(t0 + (k - c0) / (c1 - c0) * (t1 - t0))
    lines = []
    for k in sorted(met):
        crossed, c = sorted(met[k]), (k + HATCH_FROM) * apart
        for t0, t1 in zip(crossed[::2], crossed[1::2]):
            if t1 - t0 >= HATCH_LEAST_MM:
                lines.append(tuple((t * along[0] + c * across[0], t * along[1] + c * across[1]) for t in (t0, t1)))
    return lines


def hatch_ink(colour, rest):
    """What a part's hatch is drawn in, so that it can be read on the part's fill: dark on a light fill and
    white on a dark one. The fill is taken as it is seen on the sheet's white, where a part that lets light
    through is paler; the lines themselves are never pale."""
    seen = [c * rest[0] + 1 - rest[0] if rest else c for c in colour]
    light = sum(weight * (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
                for weight, c in zip((0.2126, 0.7152, 0.0722), seen))
    return INK if light > 0.22 else "#ffffff"


def svg(title, lines, parts, low, high, measured=(), hatch=None, behind=(), arcs=False):
    """The drawing. `parts` is [(name, (r, g, b), [[outline, ...] per cut face])], or with a fourth member how
    much the part hides of what lies behind it, from above 0 to 1; the sheet's y runs upwards, an SVG file's
    downwards, so every y is turned over. `low` and `high` are the corners of all that is cut. `measured` is
    the dimensions asked for, [(kind, (u, v), (u, v), value, words)] with the points on the sheet. `hatch` is
    each part's hatch, [(degrees, millimetres)] in the order of `parts`, where the cut faces are hatched.
    `behind` is the edges seen behind the plane, [[(u, v), ...]], drawn thin beneath the cut faces; the two
    dimensions of what is cut then stand outside them. With `arcs` the points `Along` an arc are written as
    the arc."""
    legend_rows = len(parts)
    across, tall = high[0] - low[0], high[1] - low[1]
    rows = [m for m in measured if m[0] == "across"]
    columns = [m for m in measured if m[0] == "up"]
    # the sheet holds all that is cut, every point a dimension is taken from and every edge behind the plane
    points = [low, high] + [point for m in measured for point in m[1:3]] + [point for edge in behind for point in edge]
    least = (min(q[0] for q in points), min(q[1] for q in points))
    most = (max(q[0] for q in points), max(q[1] for q in points))
    width = max(most[0] - least[0], 60.0) + 2 * MARGIN_MM + 16.0 * (1 + len(columns))    # room at the right for the heights
    top = MARGIN_MM + 6.0 * (1 + len(lines)) + 8.0 + 7.0 * len(rows)                    # and above for the widths
    height = top + (most[1] - least[1]) + MARGIN_MM + 12.0 + 5.0 * legend_rows

    def x(v):
        return v - least[0] + MARGIN_MM

    def y(v):
        return top + (most[1] - v)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.3f}mm" height="{height:.3f}mm" '
           f'viewBox="0 0 {width:.3f} {height:.3f}">',
           f'<rect width="{width:.3f}" height="{height:.3f}" fill="#ffffff"/>',
           '<style>text{font-family:DejaVu Sans,Helvetica,Arial,sans-serif;fill:#1f2933}.t{font-size:4px;font-weight:bold}'
           '.s{font-size:3px}</style>',
           f'<text x="{MARGIN_MM}" y="{MARGIN_MM + 3:.1f}" class="t">{escape(title)}</text>']
    for n, line in enumerate(lines):
        out.append(f'<text x="{MARGIN_MM}" y="{MARGIN_MM + 9 + 6 * n:.1f}" class="s">{escape(line)}</text>')
    def paint(colour, rest):
        """A part's fill: its colour, and how pale it is drawn when it lets through what lies behind it."""
        fill = "#" + "".join(f"{round(255 * c):02x}" for c in colour)
        return f'fill="{fill}"' + (f' fill-opacity="{rest[0]:g}"' if rest and rest[0] < 1 else "")

    def hatched(pieces, colour, rest):
        """The lines of a hatch as one path, in what can be read on the part's fill."""
        return ('<path d="' + " ".join(f"M {x(a[0]):.3f},{y(a[1]):.3f} L {x(b[0]):.3f},{y(b[1]):.3f}" for a, b in pieces)
                + f'" stroke="{hatch_ink(colour, rest)}" stroke-width="0.1" fill="none"/>')

    if behind:
        out.append('<path d="' + " ".join("M " + " L ".join(f"{x(px):.3f},{y(py):.3f}" for px, py in edge) for edge in behind)
                   + f'" stroke="{INK}" stroke-width="0.08" stroke-linecap="round" stroke-linejoin="round" fill="none"/>')
    for n, (name, colour, faces, *rest) in enumerate(parts):
        for loops in faces:
            if arcs:
                path = " ".join(with_arcs(loop, x, y) for loop in loops)
            else:
                path = " ".join("M " + " L ".join(f"{x(px):.4f},{y(py):.4f}" for px, py in loop) + " Z" for loop in loops)
            out.append(f'<path d="{path}" {paint(colour, rest)} fill-rule="evenodd" stroke="#1f2933" stroke-width="0.15" '
                       f'stroke-linejoin="round"><title>{escape(name)}</title></path>')
        pieces = [piece for loops in faces for piece in hatch_lines(loops, *hatch[n])] if hatch else []
        if pieces:
            out.append(hatched(pieces, colour, rest))
    # how wide and how high all of it is, written above and at the right: beside what is cut, or with edges
    # behind the plane beyond all that is drawn, with thin lines from there to what is cut
    left, right_, upper, lower = x(low[0]), x(high[0]), y(high[1]), y(low[1])
    over, beside = (y(most[1]), x(most[0])) if behind else (upper, right_)
    if over < upper or beside > right_:
        out.append(f'<path d="M {left:.3f},{upper:.3f} V {over - 2:.3f} M {right_:.3f},{upper:.3f} V {over - 2:.3f} '
                   f'M {right_:.3f},{upper:.3f} H {beside + 2:.3f} M {right_:.3f},{lower:.3f} H {beside + 2:.3f}" '
                   'stroke="#9b1c31" stroke-width="0.1" stroke-dasharray="0.8,0.6" fill="none"/>')
    out.append(f'<path d="M {left:.3f},{over - 4:.3f} H {right_:.3f} M {left:.3f},{over - 6:.3f} v 4 M {right_:.3f},{over - 6:.3f} v 4 '
               f'M {beside + 4:.3f},{upper:.3f} V {lower:.3f} M {beside + 2:.3f},{upper:.3f} h 4 M {beside + 2:.3f},{lower:.3f} h 4" '
               'stroke="#9b1c31" stroke-width="0.2" fill="none"/>')
    out.append(f'<text x="{(left + right_) / 2:.3f}" y="{over - 5:.3f}" class="s" text-anchor="middle" style="fill:#9b1c31">{across:.2f}</text>')
    out.append(f'<text x="{beside + 5.5:.3f}" y="{(upper + lower) / 2 + 1:.3f}" class="s" style="fill:#9b1c31">{tall:.2f}</text>')
    # the dimensions that were asked for: the ones across in rows above, the ones up in columns at the right, each
    # with thin lines to its two points; a straight distance lies between its points
    blue = 'stroke="#1c4f9b" stroke-width="0.2" fill="none"'
    thin = 'stroke="#1c4f9b" stroke-width="0.1" stroke-dasharray="0.8,0.6" fill="none"'

    def words(value, said):
        return escape(f"{value:.2f}" + (f" {said}" if said else ""))

    for n, (_, a, b, value, said) in enumerate(rows):
        line = y(most[1]) - 4 - 7 * (n + 1) if most[1] > high[1] else upper - 4 - 7 * (n + 1)
        out.append(f'<path d="M {x(a[0]):.3f},{y(a[1]):.3f} V {line - 2:.3f} M {x(b[0]):.3f},{y(b[1]):.3f} V {line - 2:.3f}" {thin}/>')
        out.append(f'<path d="M {x(a[0]):.3f},{line:.3f} H {x(b[0]):.3f} M {x(a[0]):.3f},{line - 2:.3f} v 4 M {x(b[0]):.3f},{line - 2:.3f} v 4" {blue}/>')
        out.append(f'<text x="{(x(a[0]) + x(b[0])) / 2:.3f}" y="{line - 1:.3f}" class="s" text-anchor="middle" '
                   f'style="fill:#1c4f9b">{words(value, said)}</text>')
    for n, (_, a, b, value, said) in enumerate(columns):
        line = max(right_, x(most[0])) + 4 + 16 * (n + 1)
        out.append(f'<path d="M {x(a[0]):.3f},{y(a[1]):.3f} H {line + 2:.3f} M {x(b[0]):.3f},{y(b[1]):.3f} H {line + 2:.3f}" {thin}/>')
        out.append(f'<path d="M {line:.3f},{y(a[1]):.3f} V {y(b[1]):.3f} M {line - 2:.3f},{y(a[1]):.3f} h 4 M {line - 2:.3f},{y(b[1]):.3f} h 4" {blue}/>')
        out.append(f'<text x="{line + 1.5:.3f}" y="{(y(a[1]) + y(b[1])) / 2 + 1:.3f}" class="s" '
                   f'style="fill:#1c4f9b">{words(value, said)}</text>')
    for _, a, b, value, said in (m for m in measured if m[0] == "between"):
        out.append(f'<path d="M {x(a[0]):.3f},{y(a[1]):.3f} L {x(b[0]):.3f},{y(b[1]):.3f}" {blue}/>')
        out.append(f'<circle cx="{x(a[0]):.3f}" cy="{y(a[1]):.3f}" r="0.5" fill="#1c4f9b"/>'
                   f'<circle cx="{x(b[0]):.3f}" cy="{y(b[1]):.3f}" r="0.5" fill="#1c4f9b"/>')
        out.append(f'<text x="{(x(a[0]) + x(b[0])) / 2 + 1.5:.3f}" y="{(y(a[1]) + y(b[1])) / 2 - 1:.3f}" class="s" '
                   f'style="fill:#1c4f9b">{words(value, said)}</text>')
    # a scale: the largest of 1, 2, 5, 10, 20, 50, 100, 200, 500 mm that is no more than a third of the drawing
    span = high[0] - low[0]
    bar = max([b for b in (1, 2, 5, 10, 20, 50, 100, 200, 500) if b <= max(span / 3, 1)])
    base = top + (most[1] - least[1]) + MARGIN_MM
    out.append(f'<path d="M {MARGIN_MM},{base:.2f} h {bar} M {MARGIN_MM},{base - 1.5:.2f} v 3 M {MARGIN_MM + bar},{base - 1.5:.2f} v 3" '
               'stroke="#1f2933" stroke-width="0.3" fill="none"/>')
    out.append(f'<text x="{MARGIN_MM + bar + 2}" y="{base + 1:.2f}" class="s">{bar} mm</text>')
    for n, (name, colour, _, *rest) in enumerate(parts):
        row = base + 7 + 5 * n
        out.append(f'<rect x="{MARGIN_MM}" y="{row - 3:.2f}" width="5" height="3.5" {paint(colour, rest)} stroke="#1f2933" stroke-width="0.15"/>')
        if hatch:
            # the part's hatch in its square of the legend: the square's corners on the sheet, hatched as a cut face
            u, v = least[0], most[1] + top - (row + 0.5)
            pieces = hatch_lines([[(u, v), (u + 5, v), (u + 5, v + 3.5), (u, v + 3.5)]], *hatch[n])
            if pieces:
                out.append(hatched(pieces, colour, rest))
        out.append(f'<text x="{MARGIN_MM + 7}" y="{row:.2f}" class="s">{escape(name)}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def chained(pieces):
    """Straight pieces put end to end into lines, [((x, y), (x, y), ...)], always in the same order. A line
    goes on through a point where just two pieces meet and ends where one piece ends or more than two meet;
    pieces that go round and meet no other make a line that ends where it began."""
    pieces = sorted({min(piece, piece[::-1]) for piece in pieces if piece[0] != piece[1]})
    at_point = {}
    for piece in pieces:
        for point in piece:
            at_point.setdefault(point, []).append(piece)
    left, lines = set(pieces), []

    def line_from(point, piece):
        line = [point]
        while True:
            left.discard(piece)
            line.append(piece[1] if piece[0] == line[-1] else piece[0])
            onward = [other for other in at_point[line[-1]] if other in left]
            if len(at_point[line[-1]]) != 2 or not onward:
                return tuple(line)
            piece = onward[0]

    def straight(line):
        """The line without the points that lie on the straight way from the point before to the point after,
        or within STRAIGHT_MM of it."""
        kept = [line[0]]
        for (bx, by), (cx, cy) in zip(line[1:], line[2:]):
            ax, ay = kept[-1]
            aside = abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) > STRAIGHT_MM * math.hypot(cx - ax, cy - ay)
            if aside or (bx - ax) * (cx - bx) + (by - ay) * (cy - by) <= 0:
                kept.append((bx, by))
        return tuple(kept) + line[-1:]

    for point in sorted(at_point):
        if len(at_point[point]) != 2:
            lines += [line_from(point, piece) for piece in at_point[point] if piece in left]
    lines += [line_from(piece[0], piece) for piece in pieces if piece in left]                 # the rings
    return sorted(min(line, line[::-1]) for line in map(straight, lines))


def edges_behind(placed, spans, cut, box, origin, right, upward, towards, quick=False):
    """The edges that whoever looks at the cut sees behind its plane: [((x, y), ...)] on the sheet, straight
    pieces standing for curves, each edge once and always in the same order.

    The half that the cut leaves is put together as tools/picture.py cuts a model open: a solid wholly behind
    the plane as it is, one the plane goes through without what lies before it. build123d's
    `project_to_viewport` then looks at that half from before the plane, square to it and without
    perspective, which is the kernel's hidden-line removal on the exact surfaces: what another face covers is
    left out, a curved face has its outline, and the cut faces cover what is behind them. The edges come in the
    sheet's own axes. `cut` is (axis, side, where) and `box` the corners of all the solids.

    With `quick` the kernel's other hidden-line removal looks at the same half from the same place, on a mesh
    of it that lies within CHORD_MM of the surfaces and turns BEHIND_TURN at the most from one triangle to
    the next. It gives the straight pieces of what is seen, which are put end to end; a curved face's outline
    then runs along the sides of triangles.
    """
    from build123d import Align, Box, Compound, Pos
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.GCPnts import GCPnts_TangentialDeflection
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
    from OCP.HLRAlgo import HLRAlgo_Projector
    from OCP.HLRBRep import HLRBRep_PolyAlgo, HLRBRep_PolyHLRToShape
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp, TopExp_Explorer
    from OCP.TopoDS import TopoDS

    (axis, side, where), (low, high) = cut, box
    reach = 4 * max(h - l for l, h in zip(low, high)) + 10
    corner = [-reach / 2 + (l + h) / 2 for l, h in zip(low, high)]
    corner[axis] = where if side > 0 else where - reach
    before = Pos(*corner) * Box(reach, reach, reach, align=(Align.MIN, Align.MIN, Align.MIN))
    kept = []
    for (_, solid), (lo, hi) in zip(placed, spans):
        if (hi[axis] <= where) if side > 0 else (lo[axis] >= where):
            kept.append(solid)
        elif not ((lo[axis] >= where) if side > 0 else (hi[axis] <= where)):
            kept += (solid - before).solids()
    if not kept:
        return []
    half = Compound(children=kept)
    if quick:
        BRepMesh_IncrementalMesh(half.wrapped, CHORD_MM, False, BEHIND_TURN, True)
        hidden = HLRBRep_PolyAlgo()
        hidden.Load(half.wrapped)
        # The mesh is looked at a hair askew. Seen exactly on edge, as every face square to the sheet is, a
        # triangle made the kernel leave out outlines beside it: of the mechanical example cut at its middle,
        # seen from +X, a pillar had one of its sides or neither, as the mesh fell. BEHIND_ASKEW moves what lies
        # 100 mm behind the plane a thousandth of a millimetre, and what lies in the plane not at all.
        look = tuple(t + BEHIND_ASKEW * (r + 0.6 * u) for t, r, u in zip(towards, right, upward))
        hidden.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(*origin), gp_Dir(*look), gp_Dir(*right))))
        hidden.Update()
        shown = HLRBRep_PolyHLRToShape()
        shown.Update(hidden)
        pieces = []
        # what is seen of sharp edges, of edges where two faces meet smoothly, and of the outlines of curved faces;
        # to a thousandth of a millimetre, as the drawing has them, so that of two edges that lie one behind the
        # other, which the askew look draws both, most pieces are one piece again
        for found in (shown.VCompound(), shown.Rg1LineVCompound(), shown.OutLineVCompound()):
            explorer = TopExp_Explorer(found, TopAbs_EDGE) if not found.IsNull() else None
            while explorer is not None and explorer.More():
                edge = TopoDS.Edge(explorer.Current())
                ends = [BRep_Tool.Pnt_s(vertex) for vertex in (TopExp.FirstVertex_s(edge), TopExp.LastVertex_s(edge))]
                pieces.append(tuple((round(p.X(), 3), round(p.Y(), 3)) for p in ends))
                explorer.Next()
        return chained(pieces)
    eye = tuple(o + reach * t for o, t in zip(origin, towards))
    seen, _ = half.project_to_viewport(eye, viewport_up=upward, look_at=origin)
    edges = set()
    for edge in seen:
        if edge.length < BEHIND_LEAST_MM:
            continue
        # a straight edge is its two ends; a curve gets pieces that stay within CHORD_MM of it and turn little
        found = GCPnts_TangentialDeflection(BRepAdaptor_Curve(edge.wrapped), BEHIND_TURN, CHORD_MM)
        points = tuple((round(p.X(), 4), round(p.Y(), 4)) for p in (found.Value(n + 1) for n in range(found.NbPoints())))
        if len(set(points)) > 1:
            edges.add(min(points, points[::-1]))             # the same whichever end the kernel began at
    return sorted(edges)


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
    areas = {}                                           # name -> the area of each face the plane cuts of it
    for (name, solid), (lo, hi) in zip(placed, spans):
        if not lo[axis] - 1e-9 <= where <= hi[axis] + 1e-9:
            continue
        met = solid & sheet                              # nothing at all where the plane only touches the solid
        for face in (met.faces() if met is not None else ()):
            flat = plane.to_local_coords(face)
            entry = cut.setdefault(name, [0.0, []])
            areas.setdefault(name, []).append(face.area)
            holes = sorted((settled(outline(w)) for w in flat.inner_wires()), key=lambda loop: loop[0])
            entry[1].append([settled(outline(flat.outer_wire()))] + holes)
    for name, entry in cut.items():
        entry[1].sort(key=lambda loops: loops[0][0])
        # the kernel hands the pieces over in an order of its own: added up in theirs, the last digit moved
        # from one run to the next
        entry[0] = math.fsum(sorted(areas[name]))
    if not cut:
        print(f"[section] the plane {'XYZ'[axis]} = {where:g} cuts nothing")
        return 1
    names = {name for name, _ in placed}                 # the colours a picture of the same thing has
    # a part by itself that is one solid is called by its key, not "solid 0001"
    called = {name: (positional[1] if len(positional) == 2 and len(names) == 1 else name) for name in cut}
    given = {}
    if opts["finish"]:
        given, bare = picture.finishes_for(positional, names)
        if bare:
            print(f"[section] {len(bare)} part(s) have no finish and are drawn plain: {', '.join(bare)}")
        parts = [(f"{called[name]}: {given[name][0] or picture.NO_FINISH}", finishes.srgb(given[name][1]["color"]),
                  cut[name][1], given[name][1]["opacity"]) for name in sorted(cut)]
    else:
        shade = picture.colours(names) if len(names) > 1 else {}
        parts = [(called[name], shade.get(name, picture.PLAIN), cut[name][1]) for name in sorted(cut)]
    xs = [p[0] for _, _, faces, *_ in parts for loops in faces for loop in loops for p in loop]
    ys = [p[1] for _, _, faces, *_ in parts for loops in faces for loop in loops for p in loop]
    if opts["arcs"]:                                     # an arc reaches a little beyond the pieces that stood for it
        beyond = [p for _, _, faces, *_ in parts for loops in faces for loop in loops for p in crests(loop)]
        xs, ys = xs + [p[0] for p in beyond], ys + [p[1] for p in beyond]
    name_of = {"+": "plus-", "-": "minus-"}["+" if side > 0 else "-"] + "xyz"[axis]
    stem = f"{stem}-section-{name_of}" + ("-finish" if opts["finish"] else "")
    seen = ("+" if side > 0 else "-") + "XYZ"[axis]
    lines = [f"The plane {'XYZ'[axis]} = {where:g} mm, seen from {seen}. One unit of the drawing is one millimetre.",
             "To the right: " + direction(right) + "; upwards: " + direction(upward) + "."]
    # the dimensions that were asked for, their points taken into the plane and on to the sheet
    measured = []
    for kind, a, b, said in opts["measure"]:
        on_sheet = [tuple(sum(p[i] * axis_[i] for i in range(3)) for axis_ in (right, upward)) for p in (a, b)]
        du, dv = on_sheet[1][0] - on_sheet[0][0], on_sheet[1][1] - on_sheet[0][1]
        value = abs(du) if kind == "across" else abs(dv) if kind == "up" else math.hypot(du, dv)
        measured.append((kind, on_sheet[0], on_sheet[1], value, said))
    hatch = hatches(parts) if opts["hatch"] else None    # in the order of `parts`, which is that of sorted(cut)
    behind = []
    if opts["behind"]:
        if not opts["quick"] and len(placed) > 20:       # said before, because nothing is said while it lasts
            print(f"[section] looking behind the plane on the exact surfaces of {len(placed)} solids, which may take "
                  "minutes or not end; --quick with --behind looks on a mesh, in seconds", flush=True)
        began = time.monotonic()
        behind = edges_behind(placed, spans, (axis, side, where), (low3, high3), origin, right, upward, towards, opts["quick"])
        print(f"[section] behind the plane: {len(behind)} edge(s) seen, found {'on a mesh ' if opts['quick'] else ''}"
              f"in {time.monotonic() - began:.1f} s")
        if behind:
            lines.append("Thin lines: the edges seen behind the plane" + (", found on a mesh." if opts["quick"] else "."))
    drawing = out / f"{stem}.svg"
    drawing.write_text(svg(f"{positional[-1] if len(positional) == 2 else Path(positional[0]).name}: section", lines,
                           parts, (min(xs), min(ys)), (max(xs), max(ys)), measured, hatch=hatch, behind=behind,
                           arcs=opts["arcs"]), encoding="utf-8")
    for n, name in enumerate(sorted(cut)):
        print(f"[section] {called[name]}: {cut[name][0]:.3f} mm2 in {len(cut[name][1])} piece(s)"
              + (f", hatched at {hatch[n][0]} degrees, {hatch[n][1]:g} mm apart" if hatch else ""))
    record = {"schema_version": RECORD_SCHEMA, "drawing": drawing.name, "length_unit": "mm",
              "plane": {"axis": "XYZ"[axis], "at_mm": where, "seen_from": seen},
              "sheet_in_model": {"right": list(right), "up": list(upward), "origin_mm": list(origin)},
              "extent_on_sheet_mm": {"min": [min(xs), min(ys)], "max": [max(xs), max(ys)]},
              "chord_mm": CHORD_MM,
              "parts": [{"name": called[name], "area_mm2": cut[name][0], "pieces": len(cut[name][1]),
                         **({"finish": given[name][0]} if opts["finish"] else {}),
                         **({"hatch": {"angle_deg": hatch[n][0], "spacing_mm": hatch[n][1]}} if hatch else {})}
                        for n, name in enumerate(sorted(cut))]}
    if opts["behind"]:
        record["behind"] = {"edges": len(behind), "found_on": "a mesh" if opts["quick"] else "the exact surfaces"}
    if opts["arcs"]:
        record["arcs"] = sum(arcs_in(loop) for _, _, faces, *_ in parts for loops in faces for loop in loops)
        print(f"[section] {record['arcs']} edge(s) of the cut are circular arcs and written as arcs")
    if measured:
        record["measures"] = [{"kind": kind, "from_mm": list(a), "to_mm": list(b), "on_sheet_mm": [list(p), list(q)],
                               "value_mm": value, "words": said}
                              for (kind, a, b, said), (_, p, q, value, _) in zip(opts["measure"], measured)]
        for kind, _, _, value, said in measured:
            print(f"[section] {kind}: {value:.3f} mm" + (f" ({said})" if said else ""))
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
