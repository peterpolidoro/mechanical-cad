"""A plain box around a circuit board, from the board's interface: what is worked out without a kernel, and the two
halves built with build123d where it is installed (make test-build123d)."""
import importlib.util
import math

import pytest

from mechanical_cad import enclosures

with_build123d = pytest.mark.skipif(importlib.util.find_spec("build123d") is None,
                                    reason="build123d is not in this environment (make test-build123d)")
with_bd_warehouse = pytest.mark.skipif(importlib.util.find_spec("bd_warehouse") is None,
                                       reason="bd_warehouse is not in this environment (make test-build123d)")
TOP = 4.6           # the board's top face in the file's frame; the board is far from the file's origin


def interface():
    """A board of 60 x 40 x 1.6 mm with four holes, a connector of 12 mm that faces up, one that faces sideways,
    and parts that reach 12 mm above it and 2.5 mm below, as tools/board_interface.py writes it."""
    def hole(n, x, y):
        return {"id": f"h{n}", "kind": "hole", "center": [200.0 + x, -150.0 + y, TOP], "axis": [0.0, 0.0, 1.0],
                "diameter": 3.2, "depth": 1.6, "through": True, "reference": f"H{n}"}
    return {
        "schema_version": 1, "key": "test-board", "length_unit": "mm",
        "frames": {"board": {"transform": [[1.0, 0.0, 0.0, 200.0], [0.0, 1.0, 0.0, -150.0], [0.0, 0.0, 1.0, TOP],
                                           [0.0, 0.0, 0.0, 1.0]]}},
        "features": [
            {"id": "outline", "kind": "outline", "point": [200.0, -150.0, TOP], "normal": [0.0, 0.0, 1.0], "x": [1.0, 0.0, 0.0],
             "polygon": [[-30.0, -20.0], [30.0, -20.0], [30.0, 20.0], [-30.0, 20.0]], "corner_radius": 2.0},
            {"id": "top", "kind": "plane", "point": [200.0, -150.0, TOP], "normal": [0.0, 0.0, 1.0]},
            {"id": "bottom", "kind": "plane", "point": [200.0, -150.0, TOP - 1.6], "normal": [0.0, 0.0, -1.0]},
            hole(1, -26, 16), hole(2, 26, 16), hole(3, 26, -16), hole(4, -26, -16),
            {"id": "j1", "kind": "port", "box": {"min": [204.5, -144.5, TOP], "max": [215.5, -135.5, TOP + 12.0]},
             "direction": [0.0, 0.0, 1.0], "reference": "J1"},
            {"id": "j2", "kind": "port", "box": {"min": [171.5, -154.0, TOP], "max": [181.5, -146.0, TOP + 3.2]},
             "direction": [-1.0, 0.0, 0.0], "reference": "J2"},
            {"id": "parts-above", "kind": "keep_out", "box": {"min": [170.0, -170.0, TOP], "max": [230.0, -130.0, TOP + 12.0]}},
            {"id": "parts-below", "kind": "keep_out", "box": {"min": [170.0, -170.0, TOP - 4.1], "max": [230.0, -130.0, TOP - 1.6]}},
        ]}


def test_a_board_is_read_from_its_interface_into_its_own_frame():
    board = enclosures.Board(interface())
    assert (board.width, board.depth, board.corner_radius) == (60.0, 40.0, 2.0)
    assert board.thickness == pytest.approx(1.6) and board.above == pytest.approx(12.0) and board.below == pytest.approx(2.5)
    assert [(h["id"], h["x"], h["y"]) for h in board.holes] == [("h1", -26.0, 16.0), ("h2", 26.0, 16.0),
                                                              ("h3", 26.0, -16.0), ("h4", -26.0, -16.0)]
    j1 = board.port("J1")
    assert j1 is board.port("j1") and j1["min"][:2] == pytest.approx([4.5, 5.5]) and j1["height"] == pytest.approx(12.0)
    with pytest.raises(KeyError, match="it has: J1, J2"):
        board.port("J9")
    # placed with this, the board's frame is the assembly's
    assert board.placement == [[1.0, 0.0, 0.0, -200.0], [0.0, 1.0, 0.0, 150.0], [0.0, 0.0, 1.0, -TOP], [0.0, 0.0, 0.0, 1.0]]


def test_what_is_not_a_board_is_refused():
    with pytest.raises(ValueError, match="has no interface"):
        enclosures.Board(None)
    broken = interface()
    broken["features"][0]["kind"] = "slot"
    with pytest.raises(ValueError, match="not well formed"):
        enclosures.Board(broken)
    turned = interface()
    turned["frames"]["board"]["transform"] = [[0.0, -1.0, 0.0, 200.0], [1.0, 0.0, 0.0, -150.0], [0.0, 0.0, 1.0, TOP], [0.0, 0.0, 0.0, 1.0]]
    with pytest.raises(ValueError, match="turned against"):
        enclosures.Board(turned)
    no_frame = interface()
    del no_frame["frames"]
    with pytest.raises(KeyError, match="no frame 'board'"):
        enclosures.Board(no_frame)


def test_the_levels_of_the_box_follow_the_board_and_the_settings():
    board = enclosures.Board(interface())
    at = enclosures.levels(board)
    assert at["board_bottom"] == pytest.approx(-1.6) and at["floor_top"] == pytest.approx(-1.6 - 2.5 - 1.0)
    assert at["floor_bottom"] == pytest.approx(at["floor_top"] - 2.0)
    assert (at["split"], at["lid_inside"], at["lid_top"]) == pytest.approx((0.0, 13.0, 15.0))
    assert at["inner_min"] == [-31.0, -21.0] and at["outer_max"] == [33.0, 23.0]
    assert (at["inner_radius"], at["outer_radius"]) == (3.0, 5.0)
    low = enclosures.levels(board, inner_height=6.0, wall=3.0, clearance=0.5)
    assert low["lid_inside"] == 6.0 and low["outer_min"] == [-33.5, -23.5]
    with pytest.raises(ValueError, match="not a setting of a box: thickness"):
        enclosures.levels(board, thickness=2.0)
    with pytest.raises(ValueError, match="wall must be a positive number"):
        enclosures.levels(board, wall=0)
    assert enclosures.levels(board)["lip_top"] == 1.5 and enclosures.levels(board, lip=0)["lip_top"] == 0


@with_build123d
def test_the_base_holds_the_board_on_standoffs():
    board = enclosures.Board(interface())
    base = enclosures.box_base(board, lip=0)                # no lip: the plain shape, whose volume is known
    at = enclosures.levels(board)
    assert base.is_valid and len(base.solids()) == 1
    box = base.bounding_box()
    assert (box.min.X, box.min.Y, box.min.Z) == pytest.approx((-33.0, -23.0, at["floor_bottom"]))
    assert (box.max.X, box.max.Y, box.max.Z) == pytest.approx((33.0, 23.0, 0.0))        # without a lip, as here

    def area(w, d, r):                      # a rectangle with rounded corners
        return w * d - (4 - math.pi) * r * r
    floor = area(66, 46, 5) * 2.0
    walls = (area(66, 46, 5) - area(62, 42, 3)) * (0.0 - at["floor_top"])
    standoff = math.pi * 3.5 ** 2 * (at["board_bottom"] - at["floor_top"])
    # the insert hole goes through the standoff and on into the floor, and stops 0.6 mm short of going through it
    hole = math.pi * 2.0 ** 2 * (3.5 + 2.0 - 0.6)
    assert at["board_bottom"] - at["floor_top"] == pytest.approx(3.5)
    assert base.volume == pytest.approx(floor + walls + 4 * (standoff - hole), rel=1e-6)
    # with its lip the base has the inner half of its wall 1.5 mm higher
    lipped = enclosures.box_base(board)
    assert lipped.is_valid and len(lipped.solids()) == 1 and lipped.bounding_box().max.Z == pytest.approx(1.5)
    assert lipped.volume - base.volume == pytest.approx((area(64, 44, 4) - area(62, 42, 3)) * 1.5, rel=1e-5)
    with pytest.raises(ValueError, match="standoff_diameter must be more"):
        enclosures.box_base(board, standoff_diameter=4.0)


@with_build123d
def test_the_lid_has_posts_screw_holes_and_the_openings_asked_for():
    board = enclosures.Board(interface())
    closed = enclosures.box_lid(board)
    opened = enclosures.box_lid(board, openings=["J1"])
    for lid in (closed, opened):
        assert lid.is_valid and len(lid.solids()) == 1
        assert lid.bounding_box().min.Z == pytest.approx(0.0) and lid.bounding_box().max.Z == pytest.approx(15.0)
    # the opening is the port's extent, 11 x 9 mm, and half a millimetre more on every side, through the plate
    assert closed.volume - opened.volume == pytest.approx(12.0 * 10.0 * 2.0, rel=1e-6)
    with pytest.raises(KeyError, match="has no port 'J9'"):
        enclosures.box_lid(board, openings=["J9"])
    # base and lid meet in a step and share no volume: the lid goes over the base's lip with 0.15 mm to spare
    base = enclosures.box_base(board)
    assert (base & opened) is None or (base & opened).volume == pytest.approx(0.0, abs=1e-6)
    assert base.distance_to(opened) == pytest.approx(0.0, abs=1e-6)      # they touch where the outer walls meet
    with pytest.raises(ValueError, match="the lip is as high"):
        enclosures.box_lid(board, lip=13.0)


@with_build123d
def test_a_port_that_faces_sideways_gets_a_window_through_the_wall_of_both_halves():
    board = enclosures.Board(interface())
    base, lid = enclosures.box_base(board), enclosures.box_lid(board)
    open_base, open_lid = enclosures.box_base(board, openings=["J2"]), enclosures.box_lid(board, openings=["J2"])
    for half in (open_base, open_lid):
        assert half.is_valid and len(half.solids()) == 1
    # J2 faces -x and is 8 mm wide and 3.2 mm high on the board: the window is 9 mm wide, from 0.5 mm under the
    # board's top face to 3.7 mm over it. Of the lid it takes the wall, 2 mm thick, less what the lip's recess had
    # taken already (1.15 mm of the wall, 1.65 mm high); of the base the top of the wall and the lip, 1 x 1.5 mm.
    assert lid.volume - open_lid.volume == pytest.approx(9.0 * (2.0 * 3.7 - 1.15 * 1.65), rel=1e-6)
    assert base.volume - open_base.volume == pytest.approx(9.0 * (2.0 * 0.5 + 1.0 * 1.5), rel=1e-6)
    from build123d import Vector
    for half, solid in ((lid, open_lid), (base, open_base)):
        z = 2.5 if half is lid else -0.25
        assert half.is_inside(Vector(-32.5, 0.0, z)) and not solid.is_inside(Vector(-32.5, 0.0, z))
        assert solid.is_inside(Vector(-32.5, 10.0, z))                 # beside the window the wall is whole
    # the window is where the port faces: the wall on the other side is whole
    assert open_lid.is_inside(Vector(32.5, 0.0, 2.5))
    # asked for with a port that faces up, each gets its own
    both = enclosures.box_lid(board, openings=["J1", "J2"])
    assert lid.volume - both.volume == pytest.approx(12.0 * 10.0 * 2.0 + 9.0 * (2.0 * 3.7 - 1.15 * 1.65), rel=1e-6)
    assert enclosures.box_base(board, openings=["J1"]).volume == pytest.approx(base.volume, rel=1e-9)
    slanted = interface()
    next(f for f in slanted["features"] if f["id"] == "j2")["direction"] = [-0.6, 0.8, 0.0]
    with pytest.raises(ValueError, match="J2 faces along none of the board's axes"):
        enclosures.box_lid(enclosures.Board(slanted), openings=["J2"])


@with_bd_warehouse
def test_named_hardware_gives_the_holes_of_its_tables_and_is_refused_where_it_does_not_fit():
    board = enclosures.Board(interface())
    at = enclosures.levels(board)
    # a standoff of 3.5 mm and a floor of 2 mm: the short M3 insert has room, the standard one, 5.7 mm long, has not
    with pytest.raises(ValueError, match="M3-0.5-Standard is 5.7 mm long and needs 6.8 mm of material"):
        enclosures.box_base(board, insert="M3-0.5-Standard")
    plain = enclosures.box_base(board, lip=0, insert_hole_diameter=4.0, insert_hole_depth=4.8)
    short = enclosures.box_base(board, lip=0, insert="M3-0.5-Short")
    assert short.is_valid and len(short.solids()) == 1
    assert short.bounding_box().min.Z == pytest.approx(at["floor_bottom"])      # the floor is whole under the holes
    # the short insert is 4.3 mm long: a hole 4.8 mm deep, of a number 21 drill, 0.159 in, where the typed-in one is 4 mm
    drill = 0.159 * 25.4
    assert plain.volume - short.volume == pytest.approx(4 * math.pi / 4 * (drill ** 2 - 4.0 ** 2) * 4.8, rel=1e-3)
    roomy = enclosures.box_base(board, insert="M3-0.5-Standard", under=2.5)
    assert roomy.is_valid and len(roomy.solids()) == 1
    with pytest.raises(ValueError, match="Make `standoff_diameter` more"):
        enclosures.box_base(board, insert="M3-0.5-Short", standoff_diameter=6.0)

    lid = enclosures.box_lid(board, screw="M3-0.5")
    typed = enclosures.box_lid(board)
    assert lid.is_valid and len(lid.solids()) == 1
    assert lid.volume == pytest.approx(typed.volume, rel=0.01)       # the typed-in numbers are M3's, near enough
    with pytest.raises(ValueError, match="Make `post_diameter` more"):
        enclosures.box_lid(board, screw="M3-0.5", post_diameter=6.0)
    with pytest.raises(ValueError, match="insert is the name of a size"):
        enclosures.levels(board, insert=3)


@with_build123d
def test_the_board_in_a_polyhedron_gets_the_same_standoffs_posts_and_openings():
    board = enclosures.Board(interface())
    base, lid, solid = enclosures.polyhedron_halves(board, "truncated-octahedron", wall=2.5, clearance=1.5, openings=["J1"])
    for half in (base, lid):
        assert half.is_valid and len(half.solids()) == 1
    # divided at the board's top face, where the base's lip stands 1.5 mm into the lid
    assert base.bounding_box().max.Z == pytest.approx(1.5, abs=1e-6)
    assert lid.bounding_box().min.Z == pytest.approx(0.0, abs=1e-6)
    common = base & lid
    assert common is None or common.volume == pytest.approx(0.0, abs=1e-6)
    assert base.distance_to(lid) == pytest.approx(0.0, abs=1e-6)
    # the lip is upright though the walls lean there, so the lid lifts straight off
    from build123d import Pos
    for lift in (0.4, 1.0, 3.0):
        lifted = base & (Pos(0, 0, lift) * lid)
        assert lifted is None or lifted.volume == pytest.approx(0.0, abs=1e-6)
    flat_base, flat_lid, _ = enclosures.polyhedron_halves(board, "truncated-octahedron", wall=2.5, clearance=1.5, lip=0)
    assert flat_base.bounding_box().max.Z == pytest.approx(0.0, abs=1e-6)
    assert flat_base.volume < base.volume and flat_lid.volume > lid.volume
    # the solid holds what the board and its parts fill, with the clearance, behind its wall
    cavity = solid.inset(2.5)
    corners = [(x, y, z) for x in (-31.5, 31.5) for y in (-21.5, 21.5) for z in (-1.6 - 2.5 - 1.5, 12.0 + 1.5)]
    worst = max(sum(n[i] * c[i] for i in range(3)) - d for c in corners for n, d in zip(cavity.normals, cavity.distances))
    assert worst == pytest.approx(0.0, abs=1e-6)                # and it is the smallest that does: a corner touches
    # a standoff reaches from the wall below to the board, a post from the board to the wall above
    from build123d import Vector
    hole = board.holes[0]
    assert base.is_inside(Vector(hole["x"] + 2.9, hole["y"], -3.0)) and not base.is_inside(Vector(hole["x"], hole["y"], -3.0))
    assert lid.is_inside(Vector(hole["x"] + 2.9, hole["y"], 5.0)) and not lid.is_inside(Vector(hole["x"], hole["y"], 5.0))
    # over J1 the wall is open, and closed without the opening
    closed = enclosures.polyhedron_halves(board, "truncated-octahedron", wall=2.5, clearance=1.5)[1]
    assert closed.volume > lid.volume
    top = lid.bounding_box().max.Z
    assert closed.is_inside(Vector(10.0, 10.0, top - 1.0)) and not lid.is_inside(Vector(10.0, 10.0, top - 1.0))
    # J2 faces -x: its window goes through the wall on that side, which is a square face of the solid
    wall = solid.distances[solid.face_towards((-1.0, 0.0, 0.0))]
    side_base, side_lid, _ = enclosures.polyhedron_halves(board, "truncated-octahedron", wall=2.5, clearance=1.5, openings=["J2"])
    for half in (side_base, side_lid):
        assert half.is_valid and len(half.solids()) == 1
    assert closed.is_inside(Vector(-wall + 0.6, 0.0, 2.5)) and not side_lid.is_inside(Vector(-wall + 0.6, 0.0, 2.5))
    assert side_lid.is_inside(Vector(-wall + 0.6, 12.0, 2.5)) and side_lid.is_inside(Vector(wall - 0.6, 0.0, 2.5))
    assert side_base.volume < enclosures.polyhedron_halves(board, "truncated-octahedron", wall=2.5, clearance=1.5)[0].volume


@with_build123d
def test_a_lip_is_upright_and_is_refused_where_the_walls_lean_in_too_much():
    from build123d import Pos

    from mechanical_cad.shapes import forms, polyhedra

    board = enclosures.Board(interface())
    # an octahedron whose middle is 12 mm under the board's top face: there its walls lean inwards, 54.7 degrees
    # from the level. The wall is 2 mm thick, 2.45 mm measured level; a lip of 1.5 mm with its clearance takes 1.15
    # mm of that at the bottom, and the outside comes 1.17 mm nearer by the top of the cut: 0.13 mm would be left.
    solid = polyhedra.named("octahedron", edge=120.0)
    outer, cavity = Pos(0, 0, -12) * forms.solid(solid), Pos(0, 0, -12) * forms.solid(solid.inset(2.0))
    with pytest.raises(ValueError, match="a lip of 1.5 mm would leave less than a quarter of the wall outside it"):
        enclosures.halves(board, outer, cavity)
    base, lid = enclosures.halves(board, outer, cavity, lip=0.5)
    for half in (base, lid):
        assert half.is_valid and len(half.solids()) == 1
    assert base.bounding_box().max.Z == pytest.approx(0.5, abs=1e-6)
    for lift in (0.0, 0.3, 2.0):
        common = base & (Pos(0, 0, lift) * lid)
        assert common is None or common.volume == pytest.approx(0.0, abs=1e-6)
    # the lip stands straight: 0.5 mm high on an outline that is the cavity's at the board's top face, 1 mm wide
    flat = enclosures.halves(board, outer, cavity, lip=0)[0]
    reach = 120.0 / math.sqrt(2) - 2.0 * math.sqrt(3) - 12.0              # of the cavity's outline along x and y there
    assert base.volume - flat.volume == pytest.approx(2 * ((reach + math.sqrt(2)) ** 2 - reach ** 2) * 0.5, rel=1e-6)


@with_bd_warehouse
def test_a_screw_whose_head_the_post_does_not_hold_is_refused_in_a_prism_as_it_is_in_the_box():
    board = enclosures.Board(interface())
    # the head of an M4 screw is 7.22 mm across in the tables and its counterbore 7.62 mm: it would cut a post of
    # 7 mm open at its side, and a vent that keeps its web from the post would not keep it from the counterbore
    for make in (lambda **given: enclosures.box_lid(board, **given), lambda **given: enclosures.prism_halves(board, 6, **given),
                 lambda **given: enclosures.octagon_halves(board, **given)):
        with pytest.raises(ValueError, match="the head of the screw M4-0.7 is 7.22 mm across; a post of 7.0 mm leaves too "
                                             "little around its counterbore. Make `post_diameter` more"):
            make(screw="M4-0.7")
    lid = enclosures.prism_halves(board, 6, screw="M4-0.7", post_diameter=9.0)[1]
    assert lid.is_valid and len(lid.solids()) == 1


def test_the_polygon_of_a_prism_is_the_smallest_that_holds_the_board():
    board = enclosures.Board(interface())                       # 60 x 40 mm; with the clearance 62 x 42
    assert enclosures.prism_size(board, 4) == (pytest.approx(31.0), 0.0)
    assert enclosures.prism_size(board, 4, turn=45.0)[0] == pytest.approx((31.0 + 21.0) / math.sqrt(2))
    # a hexagon with a flat side along x has to reach 37.3 mm; turned by half a step, 33.7 mm
    assert enclosures.prism_size(board, 6, turn=0)[0] == pytest.approx(math.sqrt(3) / 2 * 31.0 + 21.0 / 2)
    assert enclosures.prism_size(board, 6) == (pytest.approx(31.0 / 2 + math.sqrt(3) / 2 * 21.0), 30.0)
    assert enclosures.prism_size(board, 6, clearance=3.0)[0] == pytest.approx(33.0 / 2 + math.sqrt(3) / 2 * 23.0)
    with pytest.raises(ValueError, match="three sides or more"):
        enclosures.prism_size(board, 2)
    with pytest.raises(ValueError, match="turn is an angle in degrees"):
        enclosures.prism_size(board, 6, turn="30")


@with_build123d
def test_the_board_in_a_prism_is_as_low_as_the_box():
    board = enclosures.Board(interface())
    at = enclosures.levels(board)
    base, lid, prism = enclosures.prism_halves(board, 6, openings=["J1", "J2"])
    for half in (base, lid):
        assert half.is_valid and len(half.solids()) == 1
    assert prism.counts == (12, 18, 8)
    inside = 31.0 / 2 + math.sqrt(3) / 2 * 21.0
    assert prism.volume == pytest.approx(2 * math.sqrt(3) * (inside + 2.0) ** 2 * (at["lid_top"] - at["floor_bottom"]))
    # the heights are the box's; two sides face along x, and the corners are on the y axis
    assert base.bounding_box().min.Z == pytest.approx(at["floor_bottom"]) and base.bounding_box().max.Z == pytest.approx(1.5)
    assert lid.bounding_box().min.Z == pytest.approx(0.0, abs=1e-6) and lid.bounding_box().max.Z == pytest.approx(at["lid_top"])
    assert lid.bounding_box().max.X == pytest.approx(inside + 2.0) and lid.bounding_box().min.X == pytest.approx(-inside - 2.0)
    assert lid.bounding_box().max.Y == pytest.approx((inside + 2.0) / math.cos(math.pi / 6))
    common = base & lid
    assert common is None or common.volume == pytest.approx(0.0, abs=1e-6)
    from build123d import Vector
    hole = board.holes[0]
    assert base.is_inside(Vector(hole["x"] + 2.9, hole["y"], -3.0)) and not base.is_inside(Vector(hole["x"], hole["y"], -3.0))
    assert lid.is_inside(Vector(hole["x"] + 2.9, hole["y"], 5.0)) and not lid.is_inside(Vector(hole["x"], hole["y"], 5.0))
    # the plate is open over J1, and the wall J2 faces, a side of the prism, has its window
    assert not lid.is_inside(Vector(10.0, 10.0, at["lid_top"] - 1.0)) and lid.is_inside(Vector(-10.0, 10.0, at["lid_top"] - 1.0))
    assert not lid.is_inside(Vector(-inside - 1.5, 0.0, 2.5)) and lid.is_inside(Vector(inside + 1.5, 0.0, 2.5))
    # four sides, no turn: a square box with sharp corners around the longer side
    square = enclosures.prism_halves(board, 4, lip=0)
    assert square[2].counts == (8, 12, 6)
    assert square[0].bounding_box().max.X == pytest.approx(33.0) and square[0].bounding_box().max.Y == pytest.approx(33.0)
    shell = 66.0 ** 2 * (at["lid_top"] - at["floor_bottom"]) - 62.0 ** 2 * (at["lid_inside"] - at["floor_top"])
    standoffs = 4 * math.pi / 4 * (7.0 ** 2 - 4.0 ** 2) * 3.5              # each 3.5 mm high, with its hole 5 mm deep into the floor
    assert square[0].volume + square[1].volume < shell + standoffs + 4 * math.pi / 4 * 7.0 ** 2 * 13.0


def test_the_octagon_follows_the_board_and_cuts_its_corners_as_far_as_they_are_round():
    board = enclosures.Board(interface())                       # 60 x 40 mm with corners of 2 mm; the clearance is 1 mm
    corners, cut = enclosures.octagon_size(board)
    assert cut == pytest.approx((2 - math.sqrt(2)) * 3.0)
    assert corners == [pytest.approx(p) for p in ((-31 + cut, -21), (31 - cut, -21), (31, -21 + cut), (31, 21 - cut),
                                                  (31 - cut, 21), (-31 + cut, 21), (-31, 21 - cut), (-31, -21 + cut))]
    # the cut wall is the clearance away from the board where the board comes nearest: halfway round its corner
    nearest = (30 - 2 + math.sqrt(2), 20 - 2 + math.sqrt(2))
    assert (31 + 21 - cut - sum(nearest)) / math.sqrt(2) == pytest.approx(1.0)
    assert enclosures.octagon_size(board, clearance=3.0)[1] == pytest.approx((2 - math.sqrt(2)) * 5.0)
    assert enclosures.octagon_size(board, cut=1.0)[1] == 1.0
    with pytest.raises(ValueError, match="a cut of 2.5 mm would bring the wall within 0.47 mm of the board's corner"):
        enclosures.octagon_size(board, cut=2.5)
    for cut_given in (0, -1.0, "3"):
        with pytest.raises(ValueError, match="cut is a length in millimetres, more than 0"):
            enclosures.octagon_size(board, cut=cut_given)
    # a board with sharp corners leaves little more than half the clearance to cut
    sharp = interface()
    del sharp["features"][0]["corner_radius"]
    assert enclosures.octagon_size(enclosures.Board(sharp))[1] == pytest.approx(2 - math.sqrt(2))

    # the prism and its cavity: the heights are the box's, the walls 2 mm at every side, the cut ones too
    walls, at = enclosures.octagon_walls(board), enclosures.levels(board)
    assert walls.outer.counts == walls.cavity.counts == (16, 24, 10) and walls.inner_radius == 0.0
    outside = cut + (2 - math.sqrt(2)) * 2.0                    # the cut of the outside: the wall adds its share
    assert walls.outer.volume == pytest.approx((66.0 * 46.0 - 2 * outside ** 2) * (at["lid_top"] - at["floor_bottom"]))
    assert walls.cavity.volume == pytest.approx((62.0 * 42.0 - 2 * cut ** 2) * (at["lid_inside"] - at["floor_top"]))
    upright = [f for f, n in enumerate(walls.outer.normals) if abs(n[2]) < 0.5]
    assert len(upright) == 8
    for f in upright:
        n = walls.outer.normals[f]
        behind = walls.cavity.face_towards(n)
        assert walls.cavity.normals[behind] == pytest.approx(n)
        assert walls.outer.distances[f] - walls.cavity.distances[behind] == pytest.approx(2.0)
    # it is as long and as wide as the box, where the hexagon is 71.4 x 82.4 mm
    assert (max(v[0] for v in walls.outer.vertices), max(v[1] for v in walls.outer.vertices)) == pytest.approx((33.0, 23.0))
    hexagon = enclosures.prism_walls(board, 6).outer
    assert 2 * max(v[0] for v in hexagon.vertices) == pytest.approx(2 * (31.0 / 2 + math.sqrt(3) / 2 * 21.0 + 2.0))


@with_build123d
def test_the_board_in_an_octagon_is_the_box_with_flat_corners():
    from build123d import Pos, Vector

    board = enclosures.Board(interface())
    at = enclosures.levels(board)
    base, lid, prism = enclosures.octagon_halves(board, openings=["J1", "J2"])
    box_base, box_lid = enclosures.box_base(board, openings=["J1", "J2"]), enclosures.box_lid(board, openings=["J1", "J2"])
    assert prism.counts == (16, 24, 10)
    for half, of_box in ((base, box_base), (lid, box_lid)):
        assert half.is_valid and len(half.solids()) == 1
        assert tuple(half.bounding_box().min) == pytest.approx(tuple(of_box.bounding_box().min), abs=1e-6)
        assert tuple(half.bounding_box().max) == pytest.approx(tuple(of_box.bounding_box().max), abs=1e-6)
    common = base & lid
    assert common is None or common.volume == pytest.approx(0.0, abs=1e-6)
    assert base.distance_to(lid) == pytest.approx(0.0, abs=1e-6)
    for lift in (0.4, 1.0, 3.0):                                # the lid lifts straight off the lip
        lifted = base & (Pos(0, 0, lift) * lid)
        assert lifted is None or lifted.volume == pytest.approx(0.0, abs=1e-6)
    # the flat corner touches the box's round one in its middle and holds it: beside the middle it has wall where
    # the box has none, and further out both end
    assert lid.is_inside(Vector(32.5, 20.5, 5.0)) and not box_lid.is_inside(Vector(32.5, 20.5, 5.0))
    assert not lid.is_inside(Vector(32.6, 22.6, 5.0)) and lid.is_inside(Vector(32.0, 0.0, 5.0))
    # standoffs, posts and openings are the box's
    hole = board.holes[0]
    assert base.is_inside(Vector(hole["x"] + 2.9, hole["y"], -3.0)) and not base.is_inside(Vector(hole["x"], hole["y"], -3.0))
    assert lid.is_inside(Vector(hole["x"] + 2.9, hole["y"], 5.0)) and not lid.is_inside(Vector(hole["x"], hole["y"], 5.0))
    assert not lid.is_inside(Vector(10.0, 10.0, at["lid_top"] - 1.0)) and lid.is_inside(Vector(-10.0, 10.0, at["lid_top"] - 1.0))
    assert not lid.is_inside(Vector(-32.0, 0.0, 2.5)) and lid.is_inside(Vector(32.0, 0.0, 2.5))
    # without a lip and openings the base is a floor, eight walls and four standoffs with their holes
    cut = (2 - math.sqrt(2)) * 3.0
    outside, inside = 66.0 * 46.0 - 2 * (cut + (2 - math.sqrt(2)) * 2.0) ** 2, 62.0 * 42.0 - 2 * cut ** 2
    plain = enclosures.octagon_halves(board, lip=0)[0]
    standoff, hole = math.pi * 3.5 ** 2 * 3.5, math.pi * 2.0 ** 2 * (3.5 + 2.0 - 0.6)
    assert plain.volume == pytest.approx(outside * 2.0 + (outside - inside) * 5.1 + 4 * (standoff - hole), rel=1e-6)
    # a smaller cut gives a smaller flat, and a base with more in it
    assert enclosures.octagon_halves(board, cut=1.0, lip=0)[0].volume > plain.volume
