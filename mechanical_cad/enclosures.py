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
What this does not have yet: vents, feet.

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

`Board` and `levels` need no CAD kernel. The functions that make solids build
with build123d and import it when called.
"""
from __future__ import annotations

from . import interfaces
from . import transforms as T

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


def settings(given):
    """DEFAULTS with what is given put over them; an unknown name or a number that is not positive is refused."""
    given = dict(given or {})
    unknown = sorted(set(given) - set(DEFAULTS) - {"inner_height", "openings", "screw", "insert"})
    if unknown:
        raise ValueError(f"not a setting of a box: {', '.join(unknown)}; they are: {', '.join(sorted(DEFAULTS))}, "
                         "inner_height, openings, screw, insert")
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


def _opening(port, margin, name):
    """What the opening for a port that does not face up removes: the port's extent across its direction and
    `margin` more on every side, from the port's inner end outwards without end."""
    from build123d import Box, Pos

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
    return Pos(*[(low[i] + high[i]) / 2 for i in range(3)]) * Box(*[high[i] - low[i] for i in range(3)])


def _without_wall_openings(half, board, s):
    """The half with the windows of the ports in `openings` that do not face up cut through it."""
    for name in s["openings"]:
        port = board.port(name)
        if not _faces_up(port):
            half -= _opening(port, s["opening_margin"], name)
    return half


def box_base(board, **given):
    """The base: floor, walls up to the board's top face, and a standoff with an insert hole under each mounting hole.
    Of the `openings` it has those of ports that face sideways or down, where they reach it."""
    s, at = settings(given), levels(board, **given)
    if s["standoff_diameter"] <= s["insert_hole_diameter"]:
        raise ValueError("standoff_diameter must be more than insert_hole_diameter")
    base = _slab(at["outer_min"], at["outer_max"], at["outer_radius"], at["floor_bottom"], at["split"])
    base -= _slab(at["inner_min"], at["inner_max"], at["inner_radius"], at["floor_top"], at["split"])
    if s["lip"] > 0:
        base += _slab(at["middle_min"], at["middle_max"], at["middle_radius"], at["split"], at["lip_top"])
        base -= _slab(at["inner_min"], at["inner_max"], at["inner_radius"], at["split"], at["lip_top"])
    for hole in board.holes:
        base += _cylinder(hole["x"], hole["y"], s["standoff_diameter"], at["floor_top"], at["board_bottom"])
    if s["insert"]:
        from bd_warehouse.fastener import HeatSetNut, InsertHole
        from build123d import Mode, Pos

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
        for hole in board.holes:
            base -= _cylinder(hole["x"], hole["y"], diameter, at["board_bottom"] - depth, at["board_bottom"])
        return _without_wall_openings(base, board, s)
    depth = min(s["insert_hole_depth"], at["board_bottom"] - at["floor_bottom"] - 0.6)      # never through the floor
    for hole in board.holes:
        base -= _cylinder(hole["x"], hole["y"], s["insert_hole_diameter"], at["board_bottom"] - depth, at["board_bottom"])
    return _without_wall_openings(base, board, s)


def box_lid(board, **given):
    """The lid: plate, walls down to the base, a post with a screw hole over each mounting hole, and the openings
    asked for in `openings`, each named by a port's id or reference: a window in the plate over a port that faces
    up, one through the wall for a port that faces sideways."""
    from build123d import Box, Pos

    s, at = settings(given), levels(board, **given)
    if s["post_diameter"] <= s["screw_hole_diameter"]:
        raise ValueError("post_diameter must be more than screw_hole_diameter")
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
    return _without_wall_openings(lid, board, s)


FAR = 1.0e4         # further than any enclosure reaches, in millimetres


def halves(board, outer, cavity, **given):
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
    posts and holes, the named `screw` and `insert`, `openings`, `lip`, `lip_clearance`.
    """
    from build123d import Align, Box, Pos

    s = settings(given)
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
    return base, lid


def _head_seat(outer, x, y, diameter):
    """The height at which a screw's head can sit over (x, y): the lowest point of the outside within a post's
    width of the axis, so that the counterbore is whole even where the wall slopes."""
    column = _cylinder(x, y, diameter, 0.0, FAR) & outer
    tops = [v.Z for v in column.vertices() if v.Z > 1e-6]
    edge = min(tops) if tops else column.bounding_box().max.Z
    return min(edge, column.bounding_box().max.Z)


def polyhedron_halves(board, name, **given):
    """(base, lid, the polyhedron) of an enclosure that is a solid of mechanical_cad/shapes, by its name there.

    The solid is the smallest of its kind, as it lies in polyhedra.py, that holds the board with its parts and
    `clearance` behind a wall of `wall`; it is centred on the middle of what the board and its parts fill.
    """
    from build123d import Pos

    from .shapes import forms, polyhedra

    s = settings(given)
    low, high = -board.thickness - board.below, board.above
    middle = (low + high) / 2
    half = (board.width / 2, board.depth / 2, (high - low) / 2)
    unit = polyhedra.named(name)
    p = unit.scaled(unit.scale_to_hold_box(half, wall=s["wall"], clearance=s["clearance"]))
    centre = ((board.min_x + board.max_x) / 2, (board.min_y + board.max_y) / 2, middle)
    outer = Pos(*centre) * forms.solid(p)
    cavity = Pos(*centre) * forms.solid(p.inset(s["wall"]))
    base, lid = halves(board, outer, cavity, **given)
    return base, lid, p.translated(centre)


def prism_size(board, sides, turn=None, **given):
    """(the apothem of the cavity's polygon, the turn used in degrees) of the prism of `prism_halves`.

    The polygon is regular, has `sides` sides and is centred on the board's outline. Without a turn its lowest
    side, the one of least y, is parallel to the board's x; `turn` turns it counter-clockwise by that many
    degrees. Left out, the turn is 0 or half a step, whichever makes the smaller polygon. The apothem, the
    distance of a side from the centre, is the least at which the polygon holds the board's outline and
    `clearance` around it. Nothing here needs a kernel.
    """
    import math

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


def prism_halves(board, sides, turn=None, **given):
    """(base, lid, the prism) of an enclosure that is a right prism on a regular polygon of `sides` sides, its
    axis square to the board; the prism comes back as a solid of mechanical_cad/shapes.

    Floor, plate and the room under and over the board are the box's (`levels`), and so are the settings; the
    walls are `wall` thick. The polygon and its `turn` are those of `prism_size`. Four sides make a square box
    with sharp corners; more sides follow the board less closely than the box and stand no higher.
    """
    import math

    from build123d import Pos

    from .shapes import forms, polyhedra

    s, at = settings(given), levels(board, **given)
    inside, turn = prism_size(board, sides, turn, **given)
    centre = ((board.min_x + board.max_x) / 2, (board.min_y + board.max_y) / 2)
    c, k = math.cos(math.radians(turn)), math.sin(math.radians(turn))

    def prism(apothem, low, high):
        solid = polyhedra.prism(sides, edge=2 * apothem * math.tan(math.pi / sides), height=high - low)
        if turn:
            solid = solid.rotated([[c, -k, 0.0], [k, c, 0.0], [0.0, 0.0, 1.0]])
        return solid.translated((centre[0], centre[1], (low + high) / 2))

    outer = prism(inside + s["wall"], at["floor_bottom"], at["lid_top"])
    cavity = prism(inside, at["floor_top"], at["lid_inside"])
    base, lid = halves(board, forms.solid(outer), forms.solid(cavity), **given)
    return base, lid, outer
