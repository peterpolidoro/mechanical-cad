"""A plain box around a circuit board, made from the board's interface.

The first enclosure of the plan in docs/direction.md (stage 4.1): a base and a
lid, written so that a part's program is a few lines:

    def build(parameters, inputs):
        from mechanical_cad import enclosures
        board = enclosures.Board(inputs["board"].interface)
        return enclosures.box_base(board, **parameters["box"])

`Board` reads an interface written by tools/board_interface.py and gives what
a box needs, in the board's own frame: the frame `board` of the interface,
with its origin at the middle of the outline on the top face, x to the right,
y up and z away from the top face. Everything here is in that frame, in
millimetres, so the board lies in z from -thickness to 0 and its parts stand
above z = 0. An assembly puts the board there with `Board.placement` and the
two halves at the identity.

The box:

    base   a floor, walls up to the level of the board's top face, and a
           standoff under each mounting hole that the board rests on, with a
           hole for a heat-set insert or a screw
    lid    a top plate, walls down to the base, a post over each mounting
           hole that comes down onto the board with a clearance hole for a
           screw and a counterbore for its head, and an opening above each
           port that is asked for

An opening is asked for by a port's id or reference in `openings`. A port that
faces away from the board's top gets a window in the lid's plate. One that
faces sideways, or down, gets a window through the wall on that side: the
port's extent across its direction and `opening_margin` more, from the port
outwards. Such a window is in the lid, in the base, or in both, so both halves
are given the same `openings`.

Four screws go through the lid's posts and the board into the standoffs: they
hold the board and close the box. The walls follow the outline's rounded
corners. The halves meet in a step: the inner half of the base's wall stands
`lip` higher than the board's top face, and the lid's wall is cut back to go
over it with `lip_clearance` to spare, so that the lid sits where it should.

The holes are plain cylinders of the diameters in DEFAULTS, which are typed in
for M3. Name the hardware instead, `screw="M3-0.5"` and
`insert="M3-0.5-Standard"`, and the holes are those of bd_warehouse's tables:
the hole a heat-set insert of that size is pressed into, and the clearance
hole and counterbore of a socket head cap screw. The base is then refused when
the standoff and the floor together are less than the material that insert
needs.

The same in a polyhedron (stage 4.2): `polyhedron_halves(board, name, ...)`
sizes a solid of mechanical_cad/shapes to hold the board with its parts, a
clearance and a wall, and returns a base and a lid: the shell divided at the
board's top face, with the standoffs, the posts, the screw holes and the
openings of the box, each reaching to whatever wall is there. `halves` does
that for any closed outer solid and its cavity, and gives the base the same
lip: a ring half a wall thick that stands straight up from the cavity's
outline at the board's top face, with the lid cut back to go over it. It
stands straight whatever the walls do there, so the lid lifts off.

A prism (also stage 4.2): `prism_halves(board, sides, ...)` is a right prism
on a regular polygon with its axis square to the board. Its heights are the
box's (`levels`), so it is as low as the box; the polygon is the smallest of
that many sides that holds the board with its clearance.

A prism that follows the board: `octagon_halves(board, ...)` stands on the
board's rectangle grown by the clearance, with its four corners cut as far as
the board's rounded corners allow. It is as long, as wide and as high as the
box, with flat corners where the box has round ones.

Vents. `vents` in the settings is a list of fields, each a field of slots or
of round holes cut square through one wall:

    "vents": [{"wall": "floor", "width": 2.0, "length": 12.0, "web": 2.0, "margin": 8.0},
              {"wall": "+x", "half": "lid", "shape": "round", "diameter": 3.0, "rows": 2, "columns": 6}]

A wall is "lid", "floor", "+x", "-x", "+y" or "-y", or a direction [x, y, z]:
the face of the enclosure whose outward normal is nearest to it. A wall other
than the lid's plate and the floor is divided between the halves, and the
field says in which `half` it is. A field lies in the wall's plain part: where
the wall is flat, of one thickness, and has nothing but the cavity behind it,
which ends where it meets the next wall and, towards the other half, at the
lip. The field keeps `margin` from the edge of that part, leaves `web` between
its openings, and is centred on the part unless `centre` says where; `rows`
and `columns` say how many openings it has, and left out they are the most
that fit inside the margin. A place in a wall is (u, v): the board's x and y
for the lid and the floor; for any other wall u runs level, to the right as
the wall is seen from outside, and v up the wall, from the foot of the
perpendicular that falls from the frame's origin onto the wall's outside, so
that on an upright wall v is the board's z. A field that does not fit, or
that would leave less than `web` to a standoff, a post, the opening of a port
or an earlier field, is refused and the reason says which. `vent_fields` lays
the fields out without a kernel and gives every opening's place; what the
kernel cuts is held to the volume worked out there.

Feet. `feet` in the settings puts round bosses under the base, which then
stands on them: `"feet": {"diameter": 8.0, "height": 1.5, "inset": 2.0}`.
Four of them, one towards each corner of the underside's outline and as far
out as `inset` allows between a foot and the outline; or wherever `at` says,
a list of [x, y]. A foot is never under an opening: a vent in the floor, or
the window of a port that goes through it. They are bosses and not recesses
for stick-on feet because of how the base is built: the feet belong in the
corners, where the load of a plug pushed in comes down, and there the
standoffs stand with their insert holes ending 0.6 mm short of the outside,
so a recess would break into them while a boss adds material under them. The
price is in the making: a base with feet no longer lies on its floor, so
printed as it stands its floor hangs `height` above the plate, which
tools/print_check.py reports as an overhang: such a base is printed with
support, or without `feet` and stood on feet that are stuck on.
`foot_places` says where they stand without a kernel, and `standing` says of
any solid what it stands on and whether its centre of mass is over that.

`Board`, `levels`, `prism_size`, `octagon_size`, the `..._walls` functions,
`vent_fields` and `foot_places` need no CAD kernel. The functions that make
solids build with build123d and import it when called.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import interfaces
from . import transforms as T
from .shapes import polyhedra
from .shapes.polyhedra import add, cross, dot, norm, sub, times, unit

DEFAULTS = {
    "wall": 2.0,                    # the walls, floor aside
    "floor": 2.0,                   # the base's floor
    "top": 2.0,                     # the lid's plate
    "clearance": 1.0,               # between the board's edge and the walls
    "under": 1.0,                   # more room under the board than its parts need
    "over": 1.0,                    # more room over the board than its parts need
    "standoff_diameter": 7.0,
    "insert_hole_diameter": 4.0,    # for an M3 heat-set insert; a screw that cuts its own thread wants less
    "insert_hole_depth": 5.0,
    "post_diameter": 7.0,
    "screw_hole_diameter": 3.4,     # a normal clearance hole for M3
    "head_diameter": 6.0,           # the counterbore for the head of an M3 socket head cap screw
    "head_depth": 3.2,
    "opening_margin": 0.5,          # an opening is the port's extent and this much more on every side
    "lip": 1.5,                     # how far the inner half of the base's wall stands above the board's top face; 0 for none
    "lip_clearance": 0.15,          # between that lip and the lid, sideways and above
}

VENT_DEFAULTS = {
    "shape": "slot",                # "slot", straight with round ends, or "round"
    "width": 2.0,                   # of a slot
    "length": 12.0,                 # of a slot, from end to end
    "diameter": 3.0,                # of a round hole
    "web": 2.0,                     # what is left between two openings, and between one and a standoff, a post or a port's opening
    "margin": 3.0,                  # between the openings and the edge of the wall's plain part
    "along": "v",                   # the way a slot's length runs: "u", level along a wall, or "v", up it
}
WALLS = {"lid": (0.0, 0.0, 1.0), "floor": (0.0, 0.0, -1.0), "+x": (1.0, 0.0, 0.0), "-x": (-1.0, 0.0, 0.0),
         "+y": (0.0, 1.0, 0.0), "-y": (0.0, -1.0, 0.0)}

FEET_DEFAULTS = {
    "diameter": 8.0,
    "height": 1.5,                  # how far a foot stands out under the base
    "inset": 2.0,                   # between a foot and the edge of the underside
}

FAR = 1.0e4         # further than any enclosure reaches, in millimetres
# A vent is cut by a tool that begins this far inside the wall's inner face and ends this far outside its outer one.
VENT_REACH_IN, VENT_REACH_OUT = 0.2, 1.0
# How near the kernel's figure for a half with vents or feet has to be to the one worked out here, as a fraction of
# the half's volume. A half of 40 cm3 is held to 0.04 mm3: one round hole of 1 mm through a wall of 1 mm is 0.8 mm3.
HELD_VOLUME_REL = 1e-6


class Board:
    """What a box needs to know of a board, in the board's frame (see the head of this file)."""

    def __init__(self, interface):
        if not isinstance(interface, dict):
            raise ValueError("the board has no interface; write it with tools/board_interface.py")
        wrong = interfaces.problems(interface)
        if wrong:
            raise ValueError("the board's interface is not well formed: " + "; ".join(wrong[:3]))
        self.key = interface["key"]
        frame = T.check_matrix(interfaces.frame(interface, "board"), "frames.board")
        if any(abs(frame[i][j] - (1.0 if i == j else 0.0)) > 1e-9 for i in range(3) for j in range(3)):
            raise ValueError("the board's frame is turned against the part's; only a frame that is moved is handled")
        self.origin = [frame[i][3] for i in range(3)]

        def local(point):
            return [point[i] - self.origin[i] for i in range(3)]

        outline = interfaces.feature(interface, "outline")
        if outline["normal"] != [0.0, 0.0, 1.0] or outline["x"] != [1.0, 0.0, 0.0]:
            raise ValueError("the outline is not in the plane of the board's top face with x to the right")
        centre = local(outline["point"])
        xs = [centre[0] + p[0] for p in outline["polygon"]]
        ys = [centre[1] + p[1] for p in outline["polygon"]]
        self.min_x, self.max_x, self.min_y, self.max_y = min(xs), max(xs), min(ys), max(ys)
        self.corner_radius = float(outline.get("corner_radius", 0.0))
        top = local(interfaces.feature(interface, "top")["point"])[2]
        bottom = local(interfaces.feature(interface, "bottom")["point"])[2]
        if abs(top) > 1e-6:
            raise ValueError("the board's frame is not on its top face")
        self.thickness = top - bottom
        self.above = self.below = 0.0
        for f in interfaces.of_kind(interface, "keep_out"):
            low, high = local(f["box"]["min"])[2], local(f["box"]["max"])[2]
            self.above = max(self.above, high)
            self.below = max(self.below, -self.thickness - low)
        self.holes = [{"id": f["id"], "x": local(f["center"])[0], "y": local(f["center"])[1], "diameter": f["diameter"]}
                      for f in interfaces.of_kind(interface, "hole") if f.get("through")]
        self.ports = {}
        for f in interfaces.of_kind(interface, "port"):
            low, high = local(f["box"]["min"]), local(f["box"]["max"])
            self.ports[f["id"]] = {"min": low, "max": high, "direction": list(f["direction"]),
                                   "reference": f.get("reference"), "accepts": f.get("accepts"),
                                   "height": max(high[2], 0.0)}
            self.above = max(self.above, high[2])

    @property
    def width(self):
        return self.max_x - self.min_x

    @property
    def depth(self):
        return self.max_y - self.min_y

    @property
    def placement(self):
        """The 4x4 transform that places the board's part so that its frame `board` is the assembly's frame."""
        m = T.identity()
        for i in range(3):
            m[i][3] = -self.origin[i]
        return m

    def port(self, name):
        """A port by its id or by its reference (J201), whatever the case."""
        for fid, port in self.ports.items():
            if name.lower() in (fid, str(port["reference"]).lower()):
                return port
        raise KeyError(f"the board {self.key} has no port {name!r}; it has: "
                       + ", ".join(p["reference"] or fid for fid, p in sorted(self.ports.items())))


def _positive(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def settings(given):
    """DEFAULTS with what is given put over them; an unknown name or a number that is not positive is refused.
    `vents` comes back as a list of `vent_settings`, `feet` as `feet_settings` or None."""
    given = dict(given or {})
    unknown = sorted(set(given) - set(DEFAULTS) - {"inner_height", "openings", "screw", "insert", "vents", "feet"})
    if unknown:
        raise ValueError(f"not a setting of a box: {', '.join(unknown)}; they are: {', '.join(sorted(DEFAULTS))}, "
                         "inner_height, openings, screw, insert, vents, feet")
    for name in ("screw", "insert"):
        if given.get(name) is not None and (not isinstance(given[name], str) or not given[name]):
            raise ValueError(f"{name} is the name of a size in bd_warehouse's tables, such as "
                             + ('"M3-0.5"' if name == "screw" else '"M3-0.5-Standard"'))
    out = dict(DEFAULTS, **given)
    for name in DEFAULTS:
        if isinstance(out[name], bool) or not isinstance(out[name], (int, float)) or out[name] < 0:
            raise ValueError(f"{name} must be a positive number")
        if out[name] == 0 and name != "lip":            # a lip of 0 is no lip: the halves meet flat
            raise ValueError(f"{name} must be a positive number")
    out.setdefault("inner_height", None)
    out.setdefault("screw", None)
    out.setdefault("insert", None)
    out["openings"] = list(out.get("openings") or [])
    vents = out.get("vents") or []
    if not isinstance(vents, (list, tuple)):
        raise ValueError("vents is a list of fields, each with the wall it is in")
    out["vents"] = [vent_settings(vent) for vent in vents]
    out["feet"] = feet_settings(out["feet"]) if out.get("feet") is not None else None
    return out


def vent_settings(given):
    """One field of vents: VENT_DEFAULTS with what is given put over them, and

        wall       "lid", "floor", "+x", "-x", "+y", "-y", or a direction [x, y, z]
        half       "base" or "lid": needed for a wall that is divided between the two
        rows, columns   how many openings up the wall (along v) and along it (along u); the most that fit when left out
        centre     [u, v], where the middle of the field is; the middle of the wall's plain part when left out

    `towards` is added: the direction the wall faces. An unknown name or a value that cannot be is refused."""
    if not isinstance(given, dict):
        raise ValueError("a field of vents is given by its settings, the wall it is in among them")
    unknown = sorted(set(given) - set(VENT_DEFAULTS) - {"wall", "half", "rows", "columns", "centre", "towards"})
    if unknown:
        raise ValueError(f"not a setting of a field of vents: {', '.join(unknown)}; they are: "
                         f"{', '.join(sorted(VENT_DEFAULTS))}, wall, half, rows, columns, centre")
    out = dict(VENT_DEFAULTS, **given)
    wall = out.get("wall")
    if isinstance(wall, str) and wall in WALLS:
        out["towards"] = WALLS[wall]
    elif isinstance(wall, (list, tuple)) and len(wall) == 3 and all(
            isinstance(c, (int, float)) and not isinstance(c, bool) for c in wall) and any(wall):
        out["towards"] = unit(tuple(float(c) for c in wall))
        out["wall"] = [float(c) for c in wall]
    else:
        raise ValueError(f"a field of vents names its wall: {', '.join(WALLS)}, or a direction [x, y, z]; not {wall!r}")
    if out["shape"] not in ("slot", "round"):
        raise ValueError(f'the shape of a vent is "slot" or "round", not {out["shape"]!r}')
    for name in ("width", "length", "diameter", "web", "margin"):
        if not _positive(out[name]):
            raise ValueError(f"{name} of a field of vents must be a positive number")
    if out["shape"] == "slot" and out["length"] <= out["width"]:
        raise ValueError(f"a slot is longer than it is wide, not {out['length']} by {out['width']} mm; "
                         'a round hole is the shape "round"')
    if out["along"] not in ("u", "v"):
        raise ValueError('along is "u", level along the wall, or "v", up it')
    for name in ("rows", "columns"):
        out.setdefault(name, None)
        if out[name] is not None and (isinstance(out[name], bool) or not isinstance(out[name], int) or out[name] < 1):
            raise ValueError(f"{name} of a field of vents is a whole number, 1 or more")
    out.setdefault("half", None)
    if out["half"] not in (None, "base", "lid"):
        raise ValueError('half is "base" or "lid"')
    centre = out.setdefault("centre", None)
    if centre is not None:
        if not (isinstance(centre, (list, tuple)) and len(centre) == 2 and all(
                isinstance(c, (int, float)) and not isinstance(c, bool) for c in centre)):
            raise ValueError("centre of a field of vents is [u, v], a place in the wall")
        out["centre"] = (float(centre[0]), float(centre[1]))
    return out


def feet_settings(given):
    """FEET_DEFAULTS with what is given put over them, and `at`: a list of [x, y], where the feet stand, or None
    for one towards each corner of the underside. An unknown name or a value that cannot be is refused."""
    if not isinstance(given, dict):
        raise ValueError("feet are given by their settings: diameter, height, inset, at; {} for the usual ones")
    unknown = sorted(set(given) - set(FEET_DEFAULTS) - {"at"})
    if unknown:
        raise ValueError(f"not a setting of feet: {', '.join(unknown)}; they are: {', '.join(sorted(FEET_DEFAULTS))}, at")
    out = dict(FEET_DEFAULTS, **given)
    for name in FEET_DEFAULTS:
        if not _positive(out[name]):
            raise ValueError(f"{name} of the feet must be a positive number")
    at = out.setdefault("at", None)
    if at is not None:
        if not (isinstance(at, (list, tuple)) and at and all(
                isinstance(p, (list, tuple)) and len(p) == 2 and all(
                    isinstance(c, (int, float)) and not isinstance(c, bool) for c in p) for p in at)):
            raise ValueError("at is a list of [x, y], where the feet stand")
        out["at"] = [(float(p[0]), float(p[1])) for p in at]
    return out


def levels(board, **given):
    """The heights and the extent of the box around a board, in the board's frame, as a dict:

        floor_bottom, floor_top   the base's floor
        board_bottom, 0           the board
        split                     where the base's wall ends outside and the lid begins: the board's top face
        lip_top                   where the inner half of the base's wall ends, inside the lid
        lid_inside, lid_top       the lid's plate
        inner_min, inner_max      the cavity in x and y
        outer_min, outer_max      the box in x and y
        inner_radius, outer_radius   of the corners

    The room under the board is what its parts need there and `under` more;
    over it, the height of everything on the board and `over` more, unless
    `inner_height` says otherwise: a lower lid, for ports that reach through
    openings. Whether anything else on the board is then in the way is what
    the fit check is for.
    """
    s = settings(given)
    inner_height = s["inner_height"] if s["inner_height"] is not None else board.above + s["over"]
    if inner_height <= 0:
        raise ValueError("inner_height must be positive")
    board_bottom = -board.thickness
    floor_top = board_bottom - board.below - s["under"]
    c, w = s["clearance"], s["wall"]
    return {
        "floor_bottom": floor_top - s["floor"], "floor_top": floor_top, "board_bottom": board_bottom,
        "split": 0.0, "lid_inside": inner_height, "lid_top": inner_height + s["top"],
        "inner_min": [board.min_x - c, board.min_y - c], "inner_max": [board.max_x + c, board.max_y + c],
        "outer_min": [board.min_x - c - w, board.min_y - c - w], "outer_max": [board.max_x + c + w, board.max_y + c + w],
        "inner_radius": board.corner_radius + c, "outer_radius": board.corner_radius + c + w,
        "lip_top": s["lip"],
        # the step between the halves runs along the middle of the wall
        "middle_min": [board.min_x - c - w / 2, board.min_y - c - w / 2],
        "middle_max": [board.max_x + c + w / 2, board.max_y + c + w / 2],
        "middle_radius": board.corner_radius + c + w / 2,
    }


# ---- walls, vents and feet, laid out without a kernel ----------------------------------------------------------

@dataclass(frozen=True)
class Walls:
    """The walls of an enclosure, known without a kernel: its outside and its cavity as polyhedra of
    mechanical_cad/shapes in the board's frame. A box has the upright corners of its cavity rounded with
    `inner_radius` and those of its outside with `outer_radius`; the two polyhedra then have them sharp."""
    outer: polyhedra.Polyhedron
    cavity: polyhedra.Polyhedron
    inner_radius: float = 0.0
    outer_radius: float = 0.0


def _signed_area(polygon):
    return math.fsum(a[0] * b[1] - a[1] * b[0] for a, b in zip(polygon, polygon[1:] + polygon[:1])) / 2.0


def _outward(a, b):
    """The unit normal of the side from a to b of a counter-clockwise polygon that points out of it."""
    length = math.hypot(b[0] - a[0], b[1] - a[1])
    return ((b[1] - a[1]) / length, (a[0] - b[0]) / length)


def _sides(polygon):
    return list(zip(polygon, polygon[1:] + polygon[:1]))


def _to_segment(p, a, b):
    """The distance from the point p to the segment from a to b."""
    ax, ay = b[0] - a[0], b[1] - a[1]
    square = ax * ax + ay * ay
    t = 0.0 if square == 0.0 else min(1.0, max(0.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / square))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


def _segments_apart(a, b, c, d):
    """The least distance between the segment from a to b and the segment from c to d; 0 where they cross."""
    def side(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])

    if side(c, d, a) * side(c, d, b) < 0.0 and side(a, b, c) * side(a, b, d) < 0.0:
        return 0.0
    return min(_to_segment(a, c, d), _to_segment(b, c, d), _to_segment(c, a, b), _to_segment(d, a, b))


def _within(p, polygon):
    """How far inside a convex polygon a point is: the least of its distances from the lines of the sides,
    negative when it is outside one of them. The polygon runs counter-clockwise."""
    return min((a[0] - p[0]) * n[0] + (a[1] - p[1]) * n[1] for a, n in ((a, _outward(a, b)) for a, b in _sides(polygon)))


def _apart(polygon, core):
    """The least distance between a convex polygon, counter-clockwise, and a point or a segment given by its
    ends; 0 where they meet. A polygon of one or two corners is a point or a segment."""
    a, b = core[0], core[-1]
    if len(polygon) > 2 and _within(a, polygon) >= 0.0:
        return 0.0
    sides = _sides(polygon) if len(polygon) > 1 else [(polygon[0], polygon[0])]
    return min(_segments_apart(a, b, c, d) for c, d in sides)


def _room(p, outline, radius):
    """How far a point is inside a region, the region being everything within `radius` of the convex polygon
    `outline`: its distance from the region's edge, negative outside."""
    inside = _within(p, outline)
    return radius + inside if inside >= 0.0 else radius - _apart(outline, [p])


def _clipped(polygon, a, b, c):
    """The part of a convex polygon with a x + b y <= c."""
    out = []
    for p, q in _sides(polygon):
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0.0:
            out.append(p)
        if fp * fq < 0.0:
            t = fp / (fp - fq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def _grown(polygon, by):
    """A convex polygon, counter-clockwise, with every side moved outwards by `by`, inwards when it is negative.
    No side may vanish on the way."""
    out = []
    for k, p in enumerate(polygon):
        n1, n2 = _outward(polygon[k - 1], p), _outward(p, polygon[(k + 1) % len(polygon)])
        c1, c2 = n1[0] * p[0] + n1[1] * p[1] + by, n2[0] * p[0] + n2[1] * p[1] + by
        across = n1[0] * n2[1] - n1[1] * n2[0]
        out.append(((c1 * n2[1] - c2 * n1[1]) / across, (n1[0] * c2 - n2[0] * c1) / across))
    return out


def _hull(points):
    """The corners of the convex hull of points in a plane, counter-clockwise; one or two points for a hull
    that is a point or a segment."""
    if not points:
        return []
    size = max(max(abs(c) for c in p) for p in points) or 1.0
    corners = [points[i] for i in polyhedra._corners(points, 1e-12 * size)]
    return corners or [points[0]]


def _support(polygon, direction):
    """The point of a convex polygon that is furthest along a direction; the middle of a side that is square
    to it."""
    reach = [p[0] * direction[0] + p[1] * direction[1] for p in polygon]
    size = max(max(abs(c) for c in p) for p in polygon) or 1.0
    furthest = [p for p, r in zip(polygon, reach) if r >= max(reach) - 1e-9 * size]
    return (math.fsum(p[0] for p in furthest) / len(furthest), math.fsum(p[1] for p in furthest) / len(furthest))


def _axes(normal):
    """(u, v) of a wall that faces along `normal`: the board's x and y for a level wall; otherwise u level, to
    the right as the wall is seen from outside, and v up the wall."""
    level = math.hypot(normal[0], normal[1])
    if level < 1e-9:
        return (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
    u = (-normal[1] / level, normal[0] / level, 0.0)
    return u, cross(normal, u)


def _named(vent):
    wall = vent["wall"]
    return f"the wall towards ({wall[0]:g}, {wall[1]:g}, {wall[2]:g})" if isinstance(wall, list) else (
        {"lid": "the lid's plate", "floor": "the floor"}.get(wall, f"the wall {wall}"))


def _wall(walls, vent, half, s):
    """The plain part of the wall a field of vents names, in one half; None when the field is in the other half.

    A dict: `origin`, `u`, `v` and `normal`, the wall's frame on its outer face; `thickness`; `outline`, a
    convex polygon in (u, v), counter-clockwise, and `radius`: the plain part is everything within `radius` of
    the polygon; `split`, the v at which the part ends towards the other half, or None; `face`, the index of
    the face of `walls.outer`.
    """
    outer, cavity, name = walls.outer, walls.cavity, _named(vent)
    facing = [dot(n, vent["towards"]) for n in outer.normals]
    nearest = [f for f, value in enumerate(facing) if value >= max(facing) - 1e-9]
    if len(nearest) != 1:
        raise ValueError(f"{len(nearest)} walls face equally towards {vent['wall']}; name the wall by the "
                         "direction it faces, [x, y, z]")
    face = nearest[0]
    n, d = outer.normals[face], outer.distances[face]
    level = math.hypot(n[0], n[1]) < 1e-9
    if level:
        owner = "lid" if n[2] > 0.0 else "base"
        if vent["half"] not in (None, owner):
            raise ValueError(f"{name} is in the {owner}, not in the {vent['half']}")
    else:
        owner = vent["half"]
        if owner is None:
            raise ValueError(f"{name} is divided between the base and the lid: say in which `half` its vents are")
    if owner != half:
        return None
    behind = [g for g, m in enumerate(cavity.normals) if norm(sub(m, n)) < 1e-9]
    if len(behind) != 1:
        raise ValueError(f"{name}: the cavity has no flat face behind this wall, so it has no plain part")
    thickness = d - cavity.distances[behind[0]]
    origin = times(n, d)
    u, v = _axes(n)
    corners = cavity.polygon(behind[0])
    slack = 1e-9 * outer.circumradius
    for p in corners:                       # straight out from the cavity's face there is this wall and no other
        out = add(p, times(n, thickness))
        if thickness <= 0.0 or any(dot(m, out) > e + slack for m, e in zip(outer.normals, outer.distances)):
            raise ValueError(f"{name}: the wall is not of one thickness in front of the cavity's face")
    outline = [(dot(sub(p, origin), u), dot(sub(p, origin), v)) for p in corners]
    if _signed_area(outline) < 0.0:
        outline.reverse()
    radius, split = 0.0, None
    if level:
        if walls.inner_radius > 0.0:        # a box: the plate's and the floor's outline has round corners
            outline, radius = _grown(outline, -walls.inner_radius), walls.inner_radius
    else:
        if walls.inner_radius > 0.0:        # a box: the wall is flat between the round corners
            low, high = min(p[0] for p in outline), max(p[0] for p in outline)
            outline = _clipped(_clipped(outline, -1.0, 0.0, -(low + walls.inner_radius)), 1.0, 0.0, high - walls.inner_radius)
        # A cut square to a wall that leans ends lower or higher outside than inside: both ends stay in the half.
        rise, lean = math.hypot(n[0], n[1]), thickness * n[2]
        if half == "lid":
            lowest = s["lip"] + s["lip_clearance"] if s["lip"] > 0 else 0.0     # up to there the lid is cut back
            split = (lowest + max(0.0, lean) - origin[2]) / rise
            outline = _clipped(outline, 0.0, -1.0, -split)
        else:
            split = (min(0.0, lean) - origin[2]) / rise
            outline = _clipped(outline, 0.0, 1.0, split)
    if len(outline) < 3 or abs(_signed_area(outline)) < 1e-9:
        raise ValueError(f"the {half} has nothing of {name}")
    return {"name": name, "half": half, "face": face, "origin": origin, "u": u, "v": v, "normal": n,
            "thickness": thickness, "outline": outline, "radius": radius, "split": split,
            "lip": half == "lid" and s["lip"] > 0}


def _round(x, y, diameter, sides=24):
    """The corners of a polygon of that many sides that holds the circle about (x, y)."""
    radius = diameter / 2.0 / math.cos(math.pi / sides)
    return [(x + radius * math.cos(2.0 * math.pi * k / sides), y + radius * math.sin(2.0 * math.pi * k / sides))
            for k in range(sides)]


def _obstacles(board, s, half):
    """What a vent in one half must keep clear of, each as (what it is, the corners (x, y) of an upright prism
    that holds it, the prism's lowest and highest z, whether it is an opening): the standoffs of the base or
    the posts of the lid, and the openings of the ports that half has."""
    out = []
    for hole in board.holes:
        if half == "base":
            out.append((f"the standoff under {hole['id']}", _round(hole["x"], hole["y"], s["standoff_diameter"]),
                        -FAR, -board.thickness, False))
        else:
            across = s["post_diameter"] if s["screw"] else max(s["post_diameter"], s["head_diameter"])
            out.append((f"the post over {hole['id']}", _round(hole["x"], hole["y"], across), 0.0, FAR, False))
    for name in s["openings"]:
        port = board.port(name)
        if _faces_up(port):
            if half != "lid":
                continue
            m = s["opening_margin"]
            low = [port["min"][0] - m, port["min"][1] - m, max(port["max"][2], 0.0)]
            high = [port["max"][0] + m, port["max"][1] + m, FAR]
            what = f"the opening over {name}"
        else:
            low, high = _opening_box(port, s["opening_margin"], name)
            what = f"the opening for {name}"
        out.append((what, [(low[0], low[1]), (high[0], low[1]), (high[0], high[1]), (low[0], high[1])],
                    low[2], high[2], True))
    return out


def _shadow(corners, low, high, wall):
    """Where a vent in a wall would meet an upright prism: the part of the prism that lies within the wall and
    within a vent's reach before and behind it, seen square to the wall, as the corners (u, v) of a convex
    polygon; nothing when the prism does not come that near."""
    origin, n, u, v = wall["origin"], wall["normal"], wall["u"], wall["v"]
    near, far = -wall["thickness"] - VENT_REACH_IN, VENT_REACH_OUT
    count = len(corners)
    ring = [(x, y, z) for z in (low, high) for x, y in corners]
    edges = ([(ring[k], ring[(k + 1) % count]) for k in range(count)]
             + [(ring[count + k], ring[count + (k + 1) % count]) for k in range(count)]
             + [(ring[k], ring[count + k]) for k in range(count)])
    points = []
    for a, b in edges:
        sa, sb = dot(n, sub(a, origin)), dot(n, sub(b, origin))
        if sa == sb:
            if not near <= sa <= far:
                continue
            t0, t1 = 0.0, 1.0
        else:
            ta, tb = (near - sa) / (sb - sa), (far - sa) / (sb - sa)
            t0, t1 = max(0.0, min(ta, tb)), min(1.0, max(ta, tb))
            if t0 > t1:
                continue
        for t in (t0, t1):
            p = sub(add(a, times(sub(b, a), t)), origin)
            points.append((dot(p, u), dot(p, v)))
    return _hull(points)


def _field(wall, vent, obstacles, earlier):
    """One field of vents laid out in the plain part of a wall; see `vent_fields` for what comes back."""
    slot, web, margin, name = vent["shape"] == "slot", vent["web"], vent["margin"], wall["name"]
    rho = (vent["width"] if slot else vent["diameter"]) / 2.0
    reach = (vent["length"] - vent["width"]) / 2.0 if slot else 0.0
    du, dv = (1.0, 0.0) if not slot or vent["along"] == "u" else (0.0, 1.0)
    half_u, half_v = rho + reach * du, rho + reach * dv
    pitch_u, pitch_v = 2.0 * half_u + web, 2.0 * half_v + web
    outline, radius = wall["outline"], wall["radius"]
    low_u, high_u = min(p[0] for p in outline) - radius, max(p[0] for p in outline) + radius
    low_v, high_v = min(p[1] for p in outline) - radius, max(p[1] for p in outline) + radius
    centre = vent["centre"] or ((low_u + high_u) / 2.0, (low_v + high_v) / 2.0)
    what = (f"slots of {vent['width']:g} x {vent['length']:g} mm" if slot else f"holes of {vent['diameter']:g} mm")

    def ends(u, v):
        return (u - reach * du, v - reach * dv), (u + reach * du, v + reach * dv)

    def room(u, v):                         # how far the opening about (u, v) is from the edge of the plain part
        return min(_room(end, outline, radius) for end in ends(u, v)) - rho

    def place(k, count, pitch, middle):
        return middle + (k - (count - 1) / 2.0) * pitch

    def worst(rows, columns):               # the plain part is convex, so the four corners of a field decide
        return min(room(place(i, columns, pitch_u, centre[0]), place(j, rows, pitch_v, centre[1]))
                   for i in (0, columns - 1) for j in (0, rows - 1))

    def most(extent, opening, pitch):
        return max(0, int((extent - 2.0 * margin - opening) / pitch + 1e-9) + 1) if extent >= 2.0 * margin + opening else 0

    rows = [vent["rows"]] if vent["rows"] else range(1, most(high_v - low_v, 2.0 * half_v, pitch_v) + 1)
    columns = [vent["columns"]] if vent["columns"] else range(1, most(high_u - low_u, 2.0 * half_u, pitch_u) + 1)
    fitting = [(r * c, c, r) for r in rows for c in columns if worst(r, c) >= margin - 1e-9]
    if not fitting:
        part = f"{name}, whose plain part in the {wall['half']} is {high_u - low_u:.2f} x {high_v - low_v:.2f} mm"
        if vent["rows"] and vent["columns"]:
            least = worst(vent["rows"], vent["columns"])
            edge = "the edge of that part"
            if wall["split"] is not None:   # is it the end towards the other half that is too near?
                if wall["half"] == "lid":
                    spare = place(0, vent["rows"], pitch_v, centre[1]) - half_v - wall["split"]
                else:
                    spare = wall["split"] - place(vent["rows"] - 1, vent["rows"], pitch_v, centre[1]) - half_v
                if spare < margin - 1e-9:
                    edge, least = ("the lip, which the lid goes over" if wall["lip"] else "where the halves meet"), spare
            reaches = (f"comes within {least:.2f} mm of {edge}" if least >= 0.0
                       else f"reaches {-least:.2f} mm beyond {edge}")
            raise ValueError(f"a field of {vent['rows']} x {vent['columns']} {what} with a web of {web:g} mm does not fit "
                             f"{part}: about ({centre[0]:.2f}, {centre[1]:.2f}) it {reaches}, and a margin of "
                             f"{margin:g} mm is asked for")
        raise ValueError(f"no field of {what} fits {part}, with a margin of {margin:g} mm about "
                         f"({centre[0]:.2f}, {centre[1]:.2f})")
    _, columns, rows = max(fitting)
    openings = []
    for j in range(rows):
        for i in range(columns):
            u, v = place(i, columns, pitch_u, centre[0]), place(j, rows, pitch_v, centre[1])
            middle = add(add(wall["origin"], times(wall["u"], u)),
                         add(times(wall["v"], v), times(wall["normal"], -wall["thickness"] / 2.0)))
            openings.append({"centre": (u, v), "ends": ends(u, v), "point": middle})

    def refuse(opening, gap, other):
        u, v = opening["centre"]
        does = f"would come within {gap:.2f} mm of {other}" if gap > 0.0 else f"would cut into {other}"
        raise ValueError(f"the vent at ({u:.2f}, {v:.2f}) of the field in {name} {does}; {web:g} mm is to be left "
                         "between them. Move the field (`centre`), make it smaller (`rows`, `columns`) or keep "
                         "it further from the edge (`margin`)")

    for other, corners, low, high, _ in obstacles:
        shadow = _shadow(corners, low, high, wall)
        for opening in openings if shadow else ():
            gap = _apart(shadow, opening["ends"]) - rho
            if gap < web - 1e-9:
                refuse(opening, gap, other)
    for field in earlier:
        for opening in openings:
            for there in field["openings"]:
                gap = _segments_apart(*opening["ends"], *there["ends"]) - rho - field["radius"]
                if gap < web - 1e-9:
                    refuse(opening, gap, "a vent of an earlier field in the same wall")
    area = vent["width"] * (vent["length"] - vent["width"]) + math.pi * rho * rho if slot else math.pi * rho * rho
    return {"wall": vent["wall"], "half": wall["half"], "face": wall["face"], "shape": vent["shape"],
            "rows": rows, "columns": columns, "radius": rho, "reach": reach, "direction": (du, dv),
            "openings": openings, "area_mm2": area, "thickness": wall["thickness"],
            "volume_mm3": len(openings) * area * wall["thickness"],
            "frame": {key: wall[key] for key in ("origin", "u", "v", "normal")}}


def vent_fields(board, walls, half, **given):
    """The fields of vents the settings ask for in one half, "base" or "lid", of an enclosure with those
    `Walls`, laid out without a kernel; a list in the order of `vents`, without the fields of the other half.

    A field is a dict: `wall` and `half`; `rows` and `columns`; `openings`, row by row from the lowest v, each
    with its `centre` (u, v), the two `ends` of its middle line, which are one point for a round hole, and
    `point`, its middle in the board's frame halfway through the wall, which a check can ask to be empty;
    `radius`, half the width of a slot or the radius of a hole; `area_mm2` of one opening; `thickness` of the
    wall; `volume_mm3`, what the field takes out; and `frame`, the wall's origin, u, v and normal.

    A field that does not fit the plain part of its wall inside its margin, or that would leave less than its
    web to a standoff, a post, the opening of a port or a field before it, is a ValueError that says which.
    """
    if half not in ("base", "lid"):
        raise ValueError('a half is "base" or "lid"')
    s = settings(given)
    obstacles = _obstacles(board, s, half) if s["vents"] else []
    out = []
    for vent in s["vents"]:
        wall = _wall(walls, vent, half, s)
        if wall is not None:
            out.append(_field(wall, vent, obstacles, [field for field in out if field["face"] == wall["face"]]))
    return out


def foot_places(board, walls, **given):
    """Where the feet the settings ask for stand under an enclosure with those `Walls`, without a kernel; None
    when no feet are asked for.

    A dict: `z`, the underside of the base; `diameter` and `height`; `at`, the middle of every foot as (x, y);
    `points`, the middle of every foot in the board's frame, which a check can ask to be material; and
    `volume_mm3`, what the feet add.

    Left to themselves there are four, one towards each corner of the underside: the place furthest along
    (1, 1), (-1, 1), (-1, -1) and (1, -1) at which a foot keeps `inset` from the edge. Refused, with the
    reason: an enclosure that does not stand on a level face; feet that do not fit inside the inset, or that
    stand in each other; a foot under a vent of the floor or under the window of a port that goes through
    it; and feet the base would not stand on: fewer than three, all in a line, or with the middle of the
    underside outside what they span.
    """
    s = settings(given)
    feet = s["feet"]
    if feet is None:
        return None
    outer = walls.outer
    face = outer.face_towards((0.0, 0.0, -1.0))
    if outer.normals[face][2] > -1.0 + 1e-9:
        raise ValueError("the enclosure does not stand on a level face; feet are not built for it")
    z = -outer.distances[face]
    outline = [(p[0], p[1]) for p in outer.polygon(face)]
    if _signed_area(outline) < 0.0:
        outline.reverse()
    low = (min(p[0] for p in outline), min(p[1] for p in outline))
    high = (max(p[0] for p in outline), max(p[1] for p in outline))
    radius = walls.outer_radius
    if radius > 0.0:                        # a box: the underside is everything within the radius of this
        outline = _grown(outline, -radius)
    r, inset = feet["diameter"] / 2.0, feet["inset"]
    if feet["at"] is None:
        inner = outline
        for a, b in _sides(outline):
            n = _outward(a, b)
            inner = _clipped(inner, n[0], n[1], n[0] * a[0] + n[1] * a[1] - max(0.0, inset + r - radius)) if inner else []
        if not inner:
            raise ValueError(f"feet of {feet['diameter']:g} mm with an inset of {inset:g} mm do not fit under an "
                             f"underside of {high[0] - low[0]:.2f} x {high[1] - low[1]:.2f} mm")
        spare = max(0.0, radius - inset - r) / math.sqrt(2.0)
        at = []
        for sx, sy in ((1.0, 1.0), (-1.0, 1.0), (-1.0, -1.0), (1.0, -1.0)):
            p = _support(inner, (sx, sy))
            at.append((p[0] + spare * sx, p[1] + spare * sy))
    else:
        at = list(feet["at"])
        for x, y in at:
            room = _room((x, y), outline, radius) - r
            if room < inset - 1e-9:
                raise ValueError(f"the foot at ({x:.2f}, {y:.2f}) " + (
                    f"comes within {room:.2f} mm of" if room >= 0.0 else f"reaches {-room:.2f} mm beyond")
                    + f" the edge of the underside; an inset of {inset:g} mm is asked for")
    for k, (x, y) in enumerate(at):
        for ox, oy in at[:k]:
            if math.hypot(x - ox, y - oy) < 2.0 * r + 1e-9:
                raise ValueError(f"the feet at ({ox:.2f}, {oy:.2f}) and ({x:.2f}, {y:.2f}) stand in each other: "
                                 "the underside is small for them, or `at` names a place twice")
    span = _hull(at)
    middle = ((low[0] + high[0]) / 2.0, (low[1] + high[1]) / 2.0)
    if len(span) < 3 or _within(middle, span) <= 0.0:
        raise ValueError("the base would not stand on these feet: there are fewer than three, they are in a line, "
                         "or the middle of the underside is not between them")
    for what, corners, bottom, _, opening in _obstacles(board, s, "base"):
        if opening and bottom <= z + 1e-9:
            for x, y in at:
                if _apart(_hull(corners), [(x, y)]) < r - 1e-9:
                    raise ValueError(f"the foot at ({x:.2f}, {y:.2f}) would stand under {what}, which goes "
                                     "through the floor; move it (`at`) or change the `inset`")
    for field in vent_fields(board, walls, "base", **given):
        if field["face"] != face:
            continue
        for x, y in at:
            for opening in field["openings"]:
                if _apart(list(opening["ends"]), [(x, y)]) < r + field["radius"] - 1e-9:
                    u, v = opening["centre"]
                    raise ValueError(f"the foot at ({x:.2f}, {y:.2f}) would stand under the vent at ({u:.2f}, "
                                     f"{v:.2f}) of the floor; move it (`at`), change the `inset` or the field")
    return {"z": z, "diameter": feet["diameter"], "height": feet["height"], "at": at,
            "points": [(x, y, z - feet["height"] / 2.0) for x, y in at],
            "volume_mm3": len(at) * math.pi * r * r * feet["height"]}


def box_walls(board, **given):
    """The `Walls` of the box of `box_base` and `box_lid`: two boxes, and the radii of its upright corners."""
    at = levels(board, **given)

    def box(low, high, z0, z1, radius):
        width, depth = high[0] - low[0], high[1] - low[1]
        solid = polyhedra.box(width, depth, z1 - z0).translated(((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, (z0 + z1) / 2))
        return solid, (radius if 0 < radius < min(width, depth) / 2 else 0.0)      # as `_slab` rounds them

    outer, outer_radius = box(at["outer_min"], at["outer_max"], at["floor_bottom"], at["lid_top"], at["outer_radius"])
    cavity, inner_radius = box(at["inner_min"], at["inner_max"], at["floor_top"], at["lid_inside"], at["inner_radius"])
    return Walls(outer, cavity, inner_radius, outer_radius)


# ---- the solids, with build123d ---------------------------------------------------------------------------------

def _slab(low, high, radius, z0, z1):
    """A plate with rounded corners between two corners in x and y and two heights."""
    from build123d import Pos, Rectangle, RectangleRounded, extrude

    width, depth = high[0] - low[0], high[1] - low[1]
    profile = RectangleRounded(width, depth, radius) if 0 < radius < min(width, depth) / 2 else Rectangle(width, depth)
    return Pos((low[0] + high[0]) / 2, (low[1] + high[1]) / 2, z0) * extrude(profile, amount=z1 - z0)


def _cylinder(x, y, diameter, z0, z1):
    from build123d import Align, Cylinder, Pos

    return Pos(x, y, z0) * Cylinder(diameter / 2, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))


def _faces_up(port):
    return port["direction"] == [0.0, 0.0, 1.0]


def _opening_box(port, margin, name):
    """The two corners of what the opening for a port that does not face up removes: the port's extent across
    its direction and `margin` more on every side, from the port's inner end outwards without end."""
    direction = port["direction"]
    along = [i for i in range(3) if abs(abs(direction[i]) - 1.0) < 1e-9]
    if len(along) != 1 or any(abs(direction[i]) > 1e-9 for i in range(3) if i != along[0]):
        raise ValueError(f"the port {name} faces along none of the board's axes; an opening for it is not built")
    low = [port["min"][i] - margin for i in range(3)]
    high = [port["max"][i] + margin for i in range(3)]
    if direction[along[0]] > 0:
        low[along[0]], high[along[0]] = port["min"][along[0]], FAR
    else:
        low[along[0]], high[along[0]] = -FAR, port["max"][along[0]]
    return low, high


def _opening(port, margin, name):
    """What the opening for a port that does not face up removes, as a solid (`_opening_box`)."""
    from build123d import Box, Pos

    low, high = _opening_box(port, margin, name)
    return Pos(*[(low[i] + high[i]) / 2 for i in range(3)]) * Box(*[high[i] - low[i] for i in range(3)])


def _without_wall_openings(half, board, s):
    """The half with the windows of the ports in `openings` that do not face up cut through it."""
    for name in s["openings"]:
        port = board.port(name)
        if not _faces_up(port):
            half -= _opening(port, s["opening_margin"], name)
    return half


def _with_vents(half, fields, name):
    """A half with the fields of `vent_fields` cut through it, held to the volume worked out there."""
    from build123d import Circle, Plane, SlotOverall, extrude

    if not fields:
        return half
    tools = []
    for field in fields:
        frame, thickness = field["frame"], field["thickness"]
        along = add(times(frame["u"], field["direction"][0]), times(frame["v"], field["direction"][1]))
        for opening in field["openings"]:
            u, v = opening["centre"]
            inside = add(add(frame["origin"], times(frame["u"], u)),
                         add(times(frame["v"], v), times(frame["normal"], -thickness - VENT_REACH_IN)))
            profile = (SlotOverall(2.0 * (field["reach"] + field["radius"]), 2.0 * field["radius"])
                       if field["shape"] == "slot" else Circle(field["radius"]))
            tools.append(extrude(Plane(origin=inside, x_dir=along, z_dir=frame["normal"]) * profile,
                                 amount=thickness + VENT_REACH_IN + VENT_REACH_OUT))
    vented = half - tools
    expected = half.volume - math.fsum(field["volume_mm3"] for field in fields)
    if len(vented.solids()) != 1 or not vented.is_valid or abs(vented.volume - expected) > HELD_VOLUME_REL * half.volume:
        raise ValueError(f"the vents of {name} did not come out as worked out: {len(vented.solids())} solid(s) of "
                         f"{vented.volume:.3f} mm3 where one of {expected:.3f} mm3 was expected. Something that is "
                         "not a standoff, a post or a port's opening is in a vent's way")
    return vented


def standing(solid, tolerance=1e-6):
    """What a solid stands on when it is set down as it lies, on a level plate under it, and whether it stays.

    A dict: `z`, the height of the plate, the solid's lowest; `contacts`, the flat faces that lie on the plate,
    each with the `centre` (x, y) of its area and its `area_mm2`; `area_mm2`, their sum; `centre_of_mass` as
    (x, y); `margin_mm`, how far inside what the contacts span the centre of mass is, negative outside; and
    `stands`, whether it is inside: a solid that stands on a point, a line or a round face has no contact here
    and does not stand.
    """
    from build123d import CenterOf, GeomType

    low = solid.bounding_box().min.Z
    contacts, rim = [], []
    for face in solid.faces():
        if face.geom_type != GeomType.PLANE or abs(face.center().Z - low) > tolerance:
            continue
        if face.normal_at(face.center()).Z > -1.0 + 1e-9:
            continue
        middle = face.center(CenterOf.MASS)
        contacts.append({"centre": (middle.X, middle.Y), "area_mm2": face.area})
        for edge in face.outer_wire().edges():
            for k in range(8):
                point = edge.position_at(k / 8.0)
                rim.append((point.X, point.Y))
    contacts.sort(key=lambda contact: contact["centre"])
    mass = solid.center(CenterOf.MASS)
    span = _hull(rim)
    margin = _within((mass.X, mass.Y), span) if len(span) > 2 else (-_apart(span, [(mass.X, mass.Y)]) if span else -math.inf)
    return {"z": low, "contacts": contacts, "area_mm2": math.fsum(c["area_mm2"] for c in contacts),
            "centre_of_mass": (mass.X, mass.Y), "margin_mm": margin, "stands": margin > tolerance}


def _with_feet(base, places):
    """A base with the feet of `foot_places` under it, held to their volume and to standing on them."""
    if places is None:
        return base
    footed = base
    for x, y in places["at"]:
        footed += _cylinder(x, y, places["diameter"], places["z"] - places["height"], places["z"])
    expected, one = base.volume + places["volume_mm3"], math.pi * places["diameter"] ** 2 / 4.0
    if len(footed.solids()) != 1 or not footed.is_valid or abs(footed.volume - expected) > HELD_VOLUME_REL * base.volume:
        raise ValueError(f"the feet did not come out as worked out: {len(footed.solids())} solid(s) of "
                         f"{footed.volume:.3f} mm3 where one of {expected:.3f} mm3 was expected")
    on = standing(footed)
    if (abs(on["z"] - (places["z"] - places["height"])) > 1e-6 or len(on["contacts"]) != len(places["at"])
            or any(abs(contact["area_mm2"] - one) > 1e-6 * one for contact in on["contacts"])):
        raise ValueError(f"the base does not stand on its {len(places['at'])} feet alone: at z = {on['z']:.3f} it "
                         f"rests on {len(on['contacts'])} face(s) of {on['area_mm2']:.3f} mm2 together")
    if not on["stands"]:
        x, y = on["centre_of_mass"]
        raise ValueError(f"the base would tip: its centre of mass, at ({x:.2f}, {y:.2f}), is {-on['margin_mm']:.2f} mm "
                         "outside what its feet span")
    return footed


def box_base(board, **given):
    """The base: floor, walls up to the board's top face, and a standoff with an insert hole under each mounting hole.
    Of the `openings` it has those of ports that face sideways or down, where they reach it; of the `vents` those
    of the floor and of its part of the walls; and the `feet`."""
    s, at = settings(given), levels(board, **given)
    if s["standoff_diameter"] <= s["insert_hole_diameter"]:
        raise ValueError("standoff_diameter must be more than insert_hole_diameter")
    walls = box_walls(board, **given) if s["vents"] or s["feet"] else None
    fields = vent_fields(board, walls, "base", **given) if walls else []
    places = foot_places(board, walls, **given) if walls else None
    base = _slab(at["outer_min"], at["outer_max"], at["outer_radius"], at["floor_bottom"], at["split"])
    base -= _slab(at["inner_min"], at["inner_max"], at["inner_radius"], at["floor_top"], at["split"])
    if s["lip"] > 0:
        base += _slab(at["middle_min"], at["middle_max"], at["middle_radius"], at["split"], at["lip_top"])
        base -= _slab(at["inner_min"], at["inner_max"], at["inner_radius"], at["split"], at["lip_top"])
    for hole in board.holes:
        base += _cylinder(hole["x"], hole["y"], s["standoff_diameter"], at["floor_top"], at["board_bottom"])
    if s["insert"]:
        from bd_warehouse.fastener import HeatSetNut, InsertHole
        from build123d import Mode

        insert = HeatSetNut(s["insert"])
        # The table's hole, as wide as bd_warehouse drills it and half a millimetre deeper than the insert is
        # long, for the plastic it pushes ahead; without the drill's point, which a printed hole does not have.
        diameter = InsertHole(insert, depth=insert.nut_thickness, mode=Mode.PRIVATE).bounding_box().size.X
        depth = insert.nut_thickness + 0.5
        needed = max(float(insert.nut_data.get("material_thickness", 0.0)), depth + 0.6)
        have = at["board_bottom"] - at["floor_bottom"]
        if have < needed:
            raise ValueError(f"the insert {s['insert']} is {insert.nut_thickness:.1f} mm long and needs {needed:.1f} mm of "
                             f"material; a standoff and the floor are {have:.2f} mm together. Give the board more room "
                             "under it (`under`), a thicker `floor`, or a shorter insert")
        if s["standoff_diameter"] < diameter + 2.4:
            raise ValueError(f"the hole for the insert {s['insert']} is {diameter:.2f} mm across; a standoff of "
                             f"{s['standoff_diameter']} mm leaves less than 1.2 mm around it. Make `standoff_diameter` more")
    else:
        diameter = s["insert_hole_diameter"]
        depth = min(s["insert_hole_depth"], at["board_bottom"] - at["floor_bottom"] - 0.6)      # never through the floor
    for hole in board.holes:
        base -= _cylinder(hole["x"], hole["y"], diameter, at["board_bottom"] - depth, at["board_bottom"])
    base = _without_wall_openings(base, board, s)
    return _with_feet(_with_vents(base, fields, "the base"), places)


def box_lid(board, **given):
    """The lid: plate, walls down to the base, a post with a screw hole over each mounting hole, and the openings
    asked for in `openings`, each named by a port's id or reference: a window in the plate over a port that faces
    up, one through the wall for a port that faces sideways. Of the `vents` it has those of the plate and of its
    part of the walls."""
    from build123d import Box, Pos

    s, at = settings(given), levels(board, **given)
    if s["post_diameter"] <= s["screw_hole_diameter"]:
        raise ValueError("post_diameter must be more than screw_hole_diameter")
    fields = vent_fields(board, box_walls(board, **given), "lid", **given) if s["vents"] else []
    lid = _slab(at["outer_min"], at["outer_max"], at["outer_radius"], at["split"], at["lid_top"])
    lid -= _slab(at["inner_min"], at["inner_max"], at["inner_radius"], at["split"], at["lid_inside"])
    gap = s["lip_clearance"]
    if at["lip_top"] + gap >= at["lid_inside"]:
        raise ValueError("the lip is as high as the lid's inside; make the lip lower")
    if s["lip"] > 0:
        lid -= _slab([v - gap for v in at["middle_min"]], [v + gap for v in at["middle_max"]], at["middle_radius"] + gap,
                     at["split"], at["lip_top"] + gap)
    for hole in board.holes:
        lid += _cylinder(hole["x"], hole["y"], s["post_diameter"], at["split"], at["lid_inside"])
    if s["screw"]:
        from bd_warehouse.fastener import ClearanceHole, SocketHeadCapScrew
        from build123d import Mode

        screw = SocketHeadCapScrew(s["screw"], 10)              # the length plays no part in the hole
        if s["post_diameter"] <= screw.head_diameter + 0.8:
            raise ValueError(f"the head of the screw {s['screw']} is {screw.head_diameter:.2f} mm across; a post of "
                             f"{s['post_diameter']} mm leaves too little around its counterbore. Make `post_diameter` more")
        for hole in board.holes:                                 # from the top of the lid down through the post
            lid -= Pos(hole["x"], hole["y"], at["lid_top"]) * ClearanceHole(screw, depth=at["lid_top"] - at["split"],
                                                                            mode=Mode.PRIVATE)
    else:
        head = min(s["head_depth"], at["lid_top"] - at["split"] - 0.6)
        for hole in board.holes:
            lid -= _cylinder(hole["x"], hole["y"], s["screw_hole_diameter"], at["split"], at["lid_top"])
            lid -= _cylinder(hole["x"], hole["y"], s["head_diameter"], at["lid_top"] - head, at["lid_top"])
    m = s["opening_margin"]
    for name in s["openings"]:
        port = board.port(name)
        if not _faces_up(port):
            continue
        x0, y0, x1, y1 = port["min"][0] - m, port["min"][1] - m, port["max"][0] + m, port["max"][1] + m
        lid -= Pos((x0 + x1) / 2, (y0 + y1) / 2, (at["lid_inside"] + at["lid_top"]) / 2) * Box(
            x1 - x0, y1 - y0, at["lid_top"] - at["lid_inside"] + 0.2)
    return _with_vents(_without_wall_openings(lid, board, s), fields, "the lid")


def halves(board, outer, cavity, walls=None, **given):
    """(base, lid) of an enclosure whose outside is the solid `outer` and whose inside is the solid `cavity`,
    both given in the board's frame.

    The shell between them is divided at the board's top face. The base gets a standoff under each mounting hole,
    from the wall below up to the board, with the hole for an insert; the lid a post over each, from the board up
    to the wall above, with a clearance hole for the screw and a counterbore let into the outside. Each opening
    asked for is the port's extent and `opening_margin`, cut straight up through whatever wall is above it, or
    outwards through the wall a port faces that does not face up.

    The halves meet in a step, as the box's do. The base gets a lip: a ring `wall` / 2 thick and `lip` high that
    stands straight up from the cavity's outline at the board's top face. The lid is cut back to go over it with
    `lip_clearance` to spare. The ring is upright even where the walls lean, so the lid lifts straight off; where
    the walls lean inwards so much that the cut would leave less than a quarter of the wall outside it, the lip is
    refused. `lip=0` makes the halves meet flat.

    Settings are those of the box that apply: `wall` for the lip, the diameters and depths of the standoffs,
    posts and holes, the named `screw` and `insert`, `openings`, `lip`, `lip_clearance`, and `vents` and `feet`.
    The last two are laid out on flat walls, so they need `walls`: the same outside and cavity as `Walls`, two
    polyhedra of mechanical_cad/shapes. Without it they are refused.
    """
    from build123d import Align, Box, Pos

    s = settings(given)
    if (s["vents"] or s["feet"]) and walls is None:
        raise ValueError("vents and feet are laid out on flat walls: give `walls`, the outside and the cavity as "
                         "polyhedra (enclosures.Walls)")
    fields = {half: vent_fields(board, walls, half, **given) if walls else [] for half in ("base", "lid")}
    places = foot_places(board, walls, **given) if walls else None
    shell = outer - cavity
    below = Pos(0, 0, 0) * Box(FAR, FAR, FAR, align=(Align.CENTER, Align.CENTER, Align.MAX))
    above = Pos(0, 0, 0) * Box(FAR, FAR, FAR, align=(Align.CENTER, Align.CENTER, Align.MIN))
    base, lid = shell & below, shell & above
    lip = around_lip = None
    if s["lip"] > 0:
        from build123d import Kind, Plane, extrude, offset, section

        outline = section(cavity, section_by=Plane.XY)
        if len(outline.faces()) != 1:
            raise ValueError("the cavity does not cross the board's top face in one piece; a lip cannot follow it. "
                             "Give lip=0 for halves that meet flat")
        gap = s["lip_clearance"]
        lip = extrude(offset(outline, amount=s["wall"] / 2, kind=Kind.INTERSECTION), amount=s["lip"])
        lip -= extrude(outline, amount=s["lip"])
        room = extrude(offset(outline, amount=s["wall"] / 2 + gap, kind=Kind.INTERSECTION), amount=s["lip"] + gap)
        # a quarter of the wall is to be left outside the cut, all the way up
        kept = extrude(offset(outline, amount=3 * s["wall"] / 4 + gap, kind=Kind.INTERSECTION), amount=s["lip"] + gap)
        outside = kept - outer
        if outside is not None and outside.solids() and outside.volume > 1e-6:
            raise ValueError(f"a lip of {s['lip']} mm would leave less than a quarter of the wall outside it: the walls "
                             "lean inwards above the board's top face, or `lip_clearance` is much for this wall. Make "
                             "`lip` lower, or 0 for halves that meet flat")
        lid -= room                         # everything inside the lip's outline too: no feather of wall is left there
        around_lip = room - extrude(outline, amount=s["lip"] + gap)
    bottom = -board.thickness
    if s["insert"]:
        from bd_warehouse.fastener import HeatSetNut, InsertHole
        from build123d import Mode

        insert = HeatSetNut(s["insert"])
        insert_diameter = InsertHole(insert, depth=insert.nut_thickness, mode=Mode.PRIVATE).bounding_box().size.X
        insert_depth = insert.nut_thickness + 0.5
    else:
        insert_diameter, insert_depth = s["insert_hole_diameter"], s["insert_hole_depth"]
    if s["screw"]:
        from bd_warehouse.fastener import SocketHeadCapScrew

        screw = SocketHeadCapScrew(s["screw"], 10)
        screw_diameter = screw.clearance_hole_diameters["Normal"]
        head_diameter, head_depth = screw.head_diameter + 0.4, screw.head_height + 0.2
    else:
        screw_diameter, head_diameter, head_depth = s["screw_hole_diameter"], s["head_diameter"], s["head_depth"]
    for hole in board.holes:
        x, y = hole["x"], hole["y"]
        standoff = _cylinder(x, y, s["standoff_diameter"], -FAR, bottom) & outer
        post = _cylinder(x, y, s["post_diameter"], 0.0, FAR) & outer
        if not standoff.solids() or not post.solids():
            raise ValueError(f"the mounting hole {hole['id']} is not inside the enclosure")
        under = standoff.bounding_box().min.Z
        depth = insert_depth
        if not s["insert"]:                 # a typed-in hole ends 0.6 mm short of the outside, as the box's does
            depth = min(insert_depth, bottom - under - 0.6)
        if depth <= 0 or bottom - under < depth + 0.6 - 1e-9:
            raise ValueError(f"under the mounting hole {hole['id']} there are {bottom - under:.2f} mm of standoff and "
                             f"wall; the hole for the insert needs {insert_depth + 0.6:.2f} mm")
        base += standoff
        base -= _cylinder(x, y, insert_diameter, bottom - depth, bottom)
        if around_lip is not None:
            post -= around_lip              # a post that stands in the wall leaves room for the lip
        lid += post
        lid -= _cylinder(x, y, screw_diameter, 0.0, FAR)
        # the head sits below the lowest point of the outside over the post, so its seat is whole where the wall slopes
        lid -= _cylinder(x, y, head_diameter, _head_seat(outer, x, y, s["post_diameter"]) - head_depth, FAR)
    if lip is not None:
        base += lip
    m = s["opening_margin"]
    for name in s["openings"]:
        port = board.port(name)
        if not _faces_up(port):
            continue
        x0, y0, x1, y1 = port["min"][0] - m, port["min"][1] - m, port["max"][0] + m, port["max"][1] + m
        lid -= Pos((x0 + x1) / 2, (y0 + y1) / 2, max(port["max"][2], 0.0) + 0.01) * Box(
            x1 - x0, y1 - y0, FAR, align=(Align.CENTER, Align.CENTER, Align.MIN))
    base, lid = _without_wall_openings(base, board, s), _without_wall_openings(lid, board, s)
    for name, half in (("base", base), ("lid", lid)):
        if len(half.solids()) != 1:
            raise ValueError(f"the {name} came out as {len(half.solids())} solids, not one: a standoff, a post or an "
                             "opening has cut it apart")
    base, lid = _with_vents(base, fields["base"], "the base"), _with_vents(lid, fields["lid"], "the lid")
    return _with_feet(base, places), lid


def _head_seat(outer, x, y, diameter):
    """The height at which a screw's head can sit over (x, y): the lowest point of the outside within a post's
    width of the axis, so that the counterbore is whole even where the wall slopes."""
    column = _cylinder(x, y, diameter, 0.0, FAR) & outer
    tops = [v.Z for v in column.vertices() if v.Z > 1e-6]
    edge = min(tops) if tops else column.bounding_box().max.Z
    return min(edge, column.bounding_box().max.Z)


def _polyhedron(board, name, s):
    """(the solid of that name sized to the board, about the origin; where its centre goes in the board's frame)."""
    low, high = -board.thickness - board.below, board.above
    half = (board.width / 2, board.depth / 2, (high - low) / 2)
    solid = polyhedra.named(name)
    solid = solid.scaled(solid.scale_to_hold_box(half, wall=s["wall"], clearance=s["clearance"]))
    return solid, ((board.min_x + board.max_x) / 2, (board.min_y + board.max_y) / 2, (low + high) / 2)


def polyhedron_walls(board, name, **given):
    """The `Walls` of the enclosure of `polyhedron_halves`: the solid, and the solid with every face moved in
    by `wall`."""
    s = settings(given)
    solid, centre = _polyhedron(board, name, s)
    return Walls(solid.translated(centre), solid.inset(s["wall"]).translated(centre))


def polyhedron_halves(board, name, **given):
    """(base, lid, the polyhedron) of an enclosure that is a solid of mechanical_cad/shapes, by its name there.

    The solid is the smallest of its kind, as it lies in polyhedra.py, that holds the board with its parts and
    `clearance` behind a wall of `wall`; it is centred on the middle of what the board and its parts fill.
    """
    from build123d import Pos

    from .shapes import forms

    s = settings(given)
    p, centre = _polyhedron(board, name, s)
    outer = Pos(*centre) * forms.solid(p)
    cavity = Pos(*centre) * forms.solid(p.inset(s["wall"]))
    base, lid = halves(board, outer, cavity, walls=polyhedron_walls(board, name, **given), **given)
    return base, lid, p.translated(centre)


def prism_size(board, sides, turn=None, **given):
    """(the apothem of the cavity's polygon, the turn used in degrees) of the prism of `prism_halves`.

    The polygon is regular, has `sides` sides and is centred on the board's outline. Without a turn its lowest
    side, the one of least y, is parallel to the board's x; `turn` turns it counter-clockwise by that many
    degrees. Left out, the turn is 0 or half a step, whichever makes the smaller polygon. The apothem, the
    distance of a side from the centre, is the least at which the polygon holds the board's outline and
    `clearance` around it. Nothing here needs a kernel.
    """
    if isinstance(sides, bool) or not isinstance(sides, int) or sides < 3:
        raise ValueError("a prism has three sides or more")
    s = settings(given)
    half_x, half_y = board.width / 2 + s["clearance"], board.depth / 2 + s["clearance"]

    def apothem(degrees):
        normals = [math.radians(degrees) - math.pi / 2 + 2 * math.pi * k / sides for k in range(sides)]
        return max(abs(math.cos(a)) * half_x + abs(math.sin(a)) * half_y for a in normals)

    if turn is None:
        return min((apothem(t), t) for t in (0.0, 180.0 / sides))
    if isinstance(turn, bool) or not isinstance(turn, (int, float)):
        raise ValueError("turn is an angle in degrees")
    return apothem(float(turn)), float(turn)


def prism_walls(board, sides, turn=None, **given):
    """The `Walls` of the enclosure of `prism_halves`: the prism, and the prism of its cavity."""
    s, at = settings(given), levels(board, **given)
    inside, turn = prism_size(board, sides, turn, **given)
    centre = ((board.min_x + board.max_x) / 2, (board.min_y + board.max_y) / 2)
    c, k = math.cos(math.radians(turn)), math.sin(math.radians(turn))

    def prism(apothem, low, high):
        solid = polyhedra.prism(sides, edge=2 * apothem * math.tan(math.pi / sides), height=high - low)
        if turn:
            solid = solid.rotated([[c, -k, 0.0], [k, c, 0.0], [0.0, 0.0, 1.0]])
        return solid.translated((centre[0], centre[1], (low + high) / 2))

    return Walls(prism(inside + s["wall"], at["floor_bottom"], at["lid_top"]),
                 prism(inside, at["floor_top"], at["lid_inside"]))


def prism_halves(board, sides, turn=None, **given):
    """(base, lid, the prism) of an enclosure that is a right prism on a regular polygon of `sides` sides, its
    axis square to the board; the prism comes back as a solid of mechanical_cad/shapes.

    Floor, plate and the room under and over the board are the box's (`levels`), and so are the settings; the
    walls are `wall` thick. The polygon and its `turn` are those of `prism_size`. Four sides make a square box
    with sharp corners; more sides follow the board less closely than the box and stand no higher.
    """
    from .shapes import forms

    walls = prism_walls(board, sides, turn, **given)
    base, lid = halves(board, forms.solid(walls.outer), forms.solid(walls.cavity), walls=walls, **given)
    return base, lid, walls.outer


def octagon_size(board, cut=None, **given):
    """(the eight corners (x, y) of the cavity's outline, the cut in millimetres) of the prism of
    `octagon_halves`.

    The outline is the board's rectangle grown by `clearance` on every side, with each corner cut off at 45
    degrees: `cut` is how much the cut takes of each of the two sides that met there. The corners come
    counter-clockwise, from the one on the side of least y that is nearest to least x. Left out, the cut is the
    most that leaves `clearance` between the wall and the board's rounded corner, (2 - sqrt 2) times the
    corner's radius and the clearance together; a larger one is refused. A board with sharp corners leaves
    room for a cut of little more than half the clearance. Nothing here needs a kernel.
    """
    s = settings(given)
    c, radius = s["clearance"], board.corner_radius
    most = (2.0 - math.sqrt(2.0)) * (radius + c)
    if cut is None:
        cut = most
    elif isinstance(cut, bool) or not isinstance(cut, (int, float)) or not cut > 0:
        raise ValueError("cut is a length in millimetres, more than 0; leave it out for the most the board allows")
    elif cut > most + 1e-9:
        left = (2.0 * (radius + c) - cut) / math.sqrt(2.0) - radius
        raise ValueError(f"a cut of {cut:g} mm would bring the wall within {left:.2f} mm of the board's corner, "
                         f"which is rounded with {radius:g} mm; the clearance is {c:g} mm, and the most that leaves "
                         f"it is {most:.3f} mm")
    x0, x1, y0, y1 = board.min_x - c, board.max_x + c, board.min_y - c, board.max_y + c
    return [(x0 + cut, y0), (x1 - cut, y0), (x1, y0 + cut), (x1, y1 - cut),
            (x1 - cut, y1), (x0 + cut, y1), (x0, y1 - cut), (x0, y0 + cut)], float(cut)


def octagon_walls(board, cut=None, **given):
    """The `Walls` of the enclosure of `octagon_halves`: the prism on the outline of `octagon_size` moved out
    by `wall`, and the prism of its cavity."""
    s, at = settings(given), levels(board, **given)
    inside, _ = octagon_size(board, cut, **given)

    def prism(corners, low, high):
        return polyhedra.prism_on(corners, high - low, "octagonal-prism").translated((0.0, 0.0, (low + high) / 2))

    return Walls(prism(_grown(inside, s["wall"]), at["floor_bottom"], at["lid_top"]),
                 prism(inside, at["floor_top"], at["lid_inside"]))


def octagon_halves(board, cut=None, **given):
    """(base, lid, the prism) of an enclosure that follows a rectangular board: a right prism on the board's
    rectangle with its corners cut (`octagon_size`), its axis square to the board; the prism comes back as a
    solid of mechanical_cad/shapes.

    Floor, plate and the room under and over the board are the box's (`levels`), and so are the settings; the
    walls are `wall` thick, the cut ones too. It is as long and as wide as the box, where a prism on a regular
    polygon is wider than the board in one direction or both, and it has flat walls all round, which the box
    with its round corners has not.
    """
    from .shapes import forms

    walls = octagon_walls(board, cut, **given)
    base, lid = halves(board, forms.solid(walls.outer), forms.solid(walls.cavity), walls=walls, **given)
    return base, lid, walls.outer
