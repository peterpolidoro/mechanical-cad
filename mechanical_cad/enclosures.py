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

Four screws go through the lid's posts and the board into the standoffs: they
hold the board and close the box. The walls follow the outline's rounded
corners. The halves meet in a step: the inner half of the base's wall stands
`lip` higher than the board's top face, and the lid's wall is cut back to go
over it with `lip_clearance` to spare, so that the lid sits where it should.
What this does not have yet: openings in the walls for ports that face
sideways, vents, feet.

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
that for any closed outer solid and its cavity.

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


def box_base(board, **given):
    """The base: floor, walls up to the board's top face, and a standoff with an insert hole under each mounting hole."""
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
        return base
    depth = min(s["insert_hole_depth"], at["board_bottom"] - at["floor_bottom"] - 0.6)      # never through the floor
    for hole in board.holes:
        base -= _cylinder(hole["x"], hole["y"], s["insert_hole_diameter"], at["board_bottom"] - depth, at["board_bottom"])
    return base


def box_lid(board, **given):
    """The lid: plate, walls down to the base, a post with a screw hole over each mounting hole, and the openings
    asked for in `openings`, each named by a port's id or reference."""
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
        if port["direction"] != [0.0, 0.0, 1.0]:
            raise ValueError(f"the port {name} does not face away from the board's top; an opening in a wall is not built yet")
        x0, y0, x1, y1 = port["min"][0] - m, port["min"][1] - m, port["max"][0] + m, port["max"][1] + m
        lid -= Pos((x0 + x1) / 2, (y0 + y1) / 2, (at["lid_inside"] + at["lid_top"]) / 2) * Box(
            x1 - x0, y1 - y0, at["lid_top"] - at["lid_inside"] + 0.2)
    return lid


FAR = 1.0e4         # further than any enclosure reaches, in millimetres


def halves(board, outer, cavity, **given):
    """(base, lid) of an enclosure whose outside is the solid `outer` and whose inside is the solid `cavity`,
    both given in the board's frame.

    The shell between them is divided at the board's top face. The base gets a standoff under each mounting hole,
    from the wall below up to the board, with the hole for an insert; the lid a post over each, from the board up
    to the wall above, with a clearance hole for the screw and a counterbore let into the outside. Each opening
    asked for is the port's extent and `opening_margin`, cut straight up through whatever wall is above it.
    Settings are those of the box that apply: the diameters and depths of the standoffs, posts and holes, the
    named `screw` and `insert`, `openings`. There is no step between the halves yet: they meet flat.
    """
    from build123d import Align, Box, Pos

    s = settings(given)
    shell = outer - cavity
    below = Pos(0, 0, 0) * Box(FAR, FAR, FAR, align=(Align.CENTER, Align.CENTER, Align.MAX))
    above = Pos(0, 0, 0) * Box(FAR, FAR, FAR, align=(Align.CENTER, Align.CENTER, Align.MIN))
    base, lid = shell & below, shell & above
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
        if bottom - under < insert_depth + 0.6:
            raise ValueError(f"under the mounting hole {hole['id']} there are {bottom - under:.2f} mm of standoff and "
                             f"wall; the hole for the insert needs {insert_depth + 0.6:.2f} mm")
        base += standoff
        base -= _cylinder(x, y, insert_diameter, bottom - insert_depth, bottom)
        lid += post
        lid -= _cylinder(x, y, screw_diameter, 0.0, FAR)
        # the head sits below the lowest point of the outside over the post, so its seat is whole where the wall slopes
        lid -= _cylinder(x, y, head_diameter, _head_seat(outer, x, y, s["post_diameter"]) - head_depth, FAR)
    m = s["opening_margin"]
    for name in s["openings"]:
        port = board.port(name)
        if port["direction"] != [0.0, 0.0, 1.0]:
            raise ValueError(f"the port {name} does not face away from the board's top; an opening in a wall is not built yet")
        x0, y0, x1, y1 = port["min"][0] - m, port["min"][1] - m, port["max"][0] + m, port["max"][1] + m
        lid -= Pos((x0 + x1) / 2, (y0 + y1) / 2, max(port["max"][2], 0.0) + 0.01) * Box(
            x1 - x0, y1 - y0, FAR, align=(Align.CENTER, Align.CENTER, Align.MIN))
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
