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
    with pytest.raises(ValueError, match="an opening in a wall is not built yet"):
        enclosures.box_lid(board, openings=["J2"])
    with pytest.raises(KeyError, match="has no port 'J9'"):
        enclosures.box_lid(board, openings=["J9"])
    # base and lid meet in a step and share no volume: the lid goes over the base's lip with 0.15 mm to spare
    base = enclosures.box_base(board)
    assert (base & opened) is None or (base & opened).volume == pytest.approx(0.0, abs=1e-6)
    assert base.distance_to(opened) == pytest.approx(0.0, abs=1e-6)      # they touch where the outer walls meet
    with pytest.raises(ValueError, match="the lip is as high"):
        enclosures.box_lid(board, lip=13.0)


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
    assert base.bounding_box().max.Z == pytest.approx(0.0, abs=1e-6)        # divided at the board's top face
    assert lid.bounding_box().min.Z == pytest.approx(0.0, abs=1e-6)
    common = base & lid
    assert common is None or common.volume == pytest.approx(0.0, abs=1e-6)
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
    with pytest.raises(ValueError, match="an opening in a wall is not built yet"):
        enclosures.polyhedron_halves(board, "truncated-octahedron", openings=["J2"])
