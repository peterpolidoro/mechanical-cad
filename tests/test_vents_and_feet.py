"""Vents through the walls of an enclosure and feet under its base, bosses or pockets for feet that are stuck on
(mechanical_cad/enclosures.py): where they go is worked out without a kernel, and what build123d cuts and adds is
held to that where it is installed (make test-build123d)."""
import math

import pytest
from test_enclosures import TOP, interface, with_build123d

from mechanical_cad import enclosures
from mechanical_cad.shapes.polyhedra import dot

SLOT = 2.0 * 10.0 + math.pi                 # the area of a slot 2 mm wide and 12 mm long: a rectangle and two half discs


def board_and_box(**given):
    board = enclosures.Board(interface())
    return board, enclosures.box_walls(board, **given)


def without_holes():
    """The board of the other tests without its mounting holes: no standoff and no post is in a vent's way."""
    plain = interface()
    plain["features"] = [f for f in plain["features"] if f["kind"] != "hole"]
    return enclosures.Board(plain)


def test_slots_in_the_lids_plate_keep_their_margin_and_their_web():
    board, walls = board_and_box()
    # the plate's plain part is the cavity's outline, 62 x 42 mm. Inside a margin of 9 mm there is room for one
    # row of slots 12 mm long, and for eleven of them 2 mm wide with 2 mm between: 10 x 4 + 2 = 42 <= 62 - 18
    (field,) = enclosures.vent_fields(board, walls, "lid", vents=[{"wall": "lid", "margin": 9}])
    assert (field["wall"], field["half"], field["shape"], field["rows"], field["columns"]) == ("lid", "lid", "slot", 1, 11)
    assert [opening["centre"] for opening in field["openings"]] == [pytest.approx((-20.0 + 4.0 * k, 0.0)) for k in range(11)]
    first = field["openings"][0]
    assert first["ends"] == (pytest.approx((-20.0, -5.0)), pytest.approx((-20.0, 5.0))) and field["radius"] == 1.0
    assert first["point"] == pytest.approx((-20.0, 0.0, 14.0))             # halfway through the plate, 13 to 15
    assert field["thickness"] == pytest.approx(2.0) and field["area_mm2"] == pytest.approx(SLOT)
    assert field["volume_mm3"] == pytest.approx(11 * SLOT * 2.0)
    # the plate is the lid's: the base has nothing of it, and a field cannot say otherwise
    assert enclosures.vent_fields(board, walls, "base", vents=[{"wall": "lid", "margin": 9}]) == []
    with pytest.raises(ValueError, match="the lid's plate is in the lid, not in the base"):
        enclosures.vent_fields(board, walls, "lid", vents=[{"wall": "lid", "half": "base"}])
    # level along the plate instead, about another place, as many as are asked for
    (field,) = enclosures.vent_fields(board, walls, "lid", vents=[
        {"wall": "lid", "along": "u", "rows": 3, "columns": 2, "centre": [-4.0, -3.0], "margin": 4}])
    assert [opening["centre"] for opening in field["openings"]] == [
        pytest.approx((x, y)) for y in (-7.0, -3.0, 1.0) for x in (-11.0, 3.0)]
    assert field["openings"][0]["ends"] == (pytest.approx((-16.0, -7.0)), pytest.approx((-6.0, -7.0)))
    # round holes: a square grid, a hole and a web apart
    (field,) = enclosures.vent_fields(without_holes(), walls, "lid", vents=[{"wall": "lid", "shape": "round", "margin": 5}])
    assert (field["rows"], field["columns"]) == (6, 10) and field["area_mm2"] == pytest.approx(math.pi * 1.5 ** 2)
    assert field["openings"][0]["centre"] == pytest.approx((-22.5, -12.5))
    assert field["openings"][0]["ends"][0] == field["openings"][0]["ends"][1]
    assert field["volume_mm3"] == pytest.approx(60 * math.pi * 1.5 ** 2 * 2.0)


def test_the_plain_part_of_a_boxs_plate_has_the_round_corners_of_the_cavity():
    board, walls = without_holes(), board_and_box()[1]
    # The cavity is 62 x 42 mm with corners of 3 mm about (28, 18). Round holes of 2 mm with a margin of 1 mm may
    # have their middle 2 mm from a straight wall, at x = 29 or y = 19; a hole at (29, 19) would be 1 mm from both
    # walls of a sharp corner, and is 0.59 mm from the arc of this one
    assert (walls.inner_radius, walls.outer_radius) == (3.0, 5.0)
    holes = {"wall": "lid", "shape": "round", "diameter": 2.0, "web": 1.0, "margin": 1.0, "rows": 3, "columns": 3}
    with pytest.raises(ValueError, match=r"does not fit the lid's plate, .* it comes within 0.59 mm of the edge of that part"):
        enclosures.vent_fields(board, walls, "lid", vents=[dict(holes, centre=[26.0, 16.0])])
    (field,) = enclosures.vent_fields(board, walls, "lid", vents=[dict(holes, centre=[25.7, 15.7])])
    x, y = field["openings"][-1]["centre"]
    assert (x, y) == pytest.approx((28.7, 18.7)) and 3.0 - math.hypot(x - 28.0, y - 18.0) - 1.0 >= 1.0
    # left to itself the field is the largest about the middle that keeps the margin, in the corners too
    (field,) = enclosures.vent_fields(board, walls, "lid", vents=[dict(holes, rows=None, columns=None)])
    assert (field["rows"], field["columns"]) == (13, 20) and field["openings"][-1]["centre"] == pytest.approx((28.5, 18.0))
    # in a box whose cavity is rounded with 9 mm the same field has to give way: its corner hole would be too near
    rounder = interface()
    rounder["features"][0]["corner_radius"] = 8.0
    rounder["features"] = [f for f in rounder["features"] if f["kind"] != "hole"]
    board9 = enclosures.Board(rounder)
    (field,) = enclosures.vent_fields(board9, enclosures.box_walls(board9), "lid", vents=[dict(holes, rows=None, columns=None)])
    assert field["rows"] * field["columns"] < 13 * 20
    x, y = field["openings"][-1]["centre"]
    assert 9.0 - math.hypot(max(x - 22.0, 0.0), max(y - 12.0, 0.0)) - 1.0 >= 1.0 - 1e-9


def test_a_field_that_does_not_fit_or_that_meets_something_is_refused_with_the_reason():
    board, walls = board_and_box()

    def fields(half="lid", **given):
        return enclosures.vent_fields(board, walls, half, **given)

    # with the usual margin of 3 mm two rows of fourteen slots fit the plate, and the outermost meet the posts
    with pytest.raises(ValueError, match=r"the vent at \(-26.00, 7.00\) of the field in the lid's plate would cut into "
                                         "the post over h1; 2 mm is to be left"):
        fields(vents=[{"wall": "lid"}])
    with pytest.raises(ValueError, match=r"the vent at \(4.00, 0.00\) .* would cut into the opening over J1"):
        fields(vents=[{"wall": "lid", "margin": 9}], openings=["J1"])
    # beside the opening, 2 mm of web is asked for and 1.5 mm would be left
    with pytest.raises(ValueError, match=r"the vent at \(1.50, 0.00\) .* would come within 1.50 mm of the opening over J1"):
        fields(vents=[{"wall": "lid", "rows": 1, "columns": 2, "centre": [-0.5, 0.0]}], openings=["J1"])
    (clear,) = fields(vents=[{"wall": "lid", "rows": 1, "columns": 2, "centre": [-1.0, 0.0]}], openings=["J1"])
    assert clear["openings"][-1]["centre"] == pytest.approx((1.0, 0.0))
    with pytest.raises(ValueError, match=r"a field of 2 x 20 slots of 2 x 12 mm with a web of 2 mm does not fit the lid's "
                                         r"plate, whose plain part in the lid is 62.00 x 42.00 mm: about \(0.00, 0.00\) it "
                                         "reaches 8.00 mm beyond the edge of that part, and a margin of 3 mm is asked for"):
        fields(vents=[{"wall": "lid", "rows": 2, "columns": 20}])
    with pytest.raises(ValueError, match="no field of slots of 2 x 50 mm fits the lid's plate"):
        fields(vents=[{"wall": "lid", "length": 50}])
    # in the floor it is the standoffs
    with pytest.raises(ValueError, match="of the field in the floor would cut into the standoff under h1"):
        fields("base", vents=[{"wall": "floor"}])
    # a second field in the same wall keeps the web from the first
    one = {"wall": "lid", "rows": 1, "columns": 3, "centre": [-10.0, 0.0]}
    with pytest.raises(ValueError, match="would come within 1.00 mm of a vent of an earlier field in the same wall"):
        fields(vents=[one, dict(one, centre=[1.0, 0.0])])
    assert len(fields(vents=[one, dict(one, centre=[2.0, 0.0])])) == 2
    # what is not a field of vents
    for vent, message in (({"wall": "lid", "pitch": 3}, "not a setting of a field of vents: pitch"),
                          ({"width": 2}, "a field of vents names its wall"),
                          ({"wall": "roof"}, "a field of vents names its wall"),
                          ({"wall": "lid", "shape": "square"}, 'is "slot" or "round"'),
                          ({"wall": "lid", "length": 2.0}, "a slot is longer than it is wide"),
                          ({"wall": "lid", "web": 0}, "web of a field of vents must be a positive number"),
                          ({"wall": "lid", "rows": 1.5}, "rows of a field of vents is a whole number"),
                          ({"wall": "lid", "centre": [1]}, "centre of a field of vents"),
                          ({"wall": "+x", "half": "top"}, 'half is "base" or "lid"'),
                          ({"wall": "+x"}, "the wall \\+x is divided between the base and the lid: say in which `half`")):
        with pytest.raises(ValueError, match=message):
            fields(vents=[vent])
    with pytest.raises(ValueError, match="vents is a list of fields"):
        fields(vents={"wall": "lid"})
    with pytest.raises(ValueError, match='a half is "base" or "lid"'):
        fields("top", vents=[])


def test_a_wall_of_the_box_is_divided_between_the_halves_and_ends_at_the_lip():
    board, walls = board_and_box()
    # the wall towards +x is flat between the round corners, y from -18 to 18; the lid has it from the top of the
    # lip's recess, z = 1.65, to its plate at z = 13, and the base from its floor at z = -5.1 to the board's top face
    (field,) = enclosures.vent_fields(board, walls, "lid", vents=[{"wall": "+x", "half": "lid", "length": 6, "margin": 2}])
    assert (field["rows"], field["columns"]) == (1, 8) and field["thickness"] == pytest.approx(2.0)
    assert field["openings"][0]["centre"] == pytest.approx((-14.0, 7.325))
    assert field["openings"][0]["point"] == pytest.approx((32.0, -14.0, 7.325))       # u runs along y, v is z
    assert field["volume_mm3"] == pytest.approx(8 * (2.0 * 4.0 + math.pi) * 2.0)
    assert enclosures.vent_fields(board, walls, "base", vents=[{"wall": "+x", "half": "lid", "length": 6, "margin": 2}]) == []
    # seen from outside, u runs to the right: on the wall towards -x that is towards -y
    (field,) = enclosures.vent_fields(board, walls, "lid", vents=[{"wall": "-x", "half": "lid", "length": 6, "margin": 2}])
    assert field["openings"][0]["point"] == pytest.approx((-32.0, 14.0, 7.325))
    (field,) = enclosures.vent_fields(board, walls, "base", vents=[
        {"wall": "+y", "half": "base", "shape": "round", "diameter": 2.0, "margin": 1}])
    assert (field["rows"], field["columns"]) == (1, 14)
    assert field["openings"][0]["point"] == pytest.approx((26.0, 22.0, -2.55))
    # a slot that would end 0.85 mm above the lip's recess
    low = {"wall": "+y", "half": "lid", "length": 6, "rows": 1, "columns": 3, "centre": [0.0, 5.5]}
    with pytest.raises(ValueError, match="it comes within 0.85 mm of the lip, which the lid goes over, and a margin of 3 mm"):
        enclosures.vent_fields(board, walls, "lid", vents=[low])
    with pytest.raises(ValueError, match="it comes within 2.50 mm of where the halves meet"):
        enclosures.vent_fields(board, walls, "lid", vents=[low], lip=0)
    with pytest.raises(ValueError, match="it reaches 0.50 mm beyond where the halves meet"):
        enclosures.vent_fields(board, walls, "base", vents=[dict(low, half="base", length=4, centre=[0.0, -1.5])])
    # J2 faces -x: its window takes the wall from z = -0.5 to 3.7, and a field over it has to keep its web
    over = {"wall": "-x", "half": "lid", "length": 6, "margin": 2}
    with pytest.raises(ValueError, match=r"the vent at \(-6.00, 7.33\) of the field in the wall -x would come within 1.21 mm "
                                         "of the opening for J2"):
        enclosures.vent_fields(board, walls, "lid", vents=[over], openings=["J2"])
    (field,) = enclosures.vent_fields(board, walls, "lid", vents=[dict(over, length=4, centre=[0.0, 8.5])], openings=["J2"])
    assert field["columns"] == 8


def test_the_walls_of_a_prism_and_of_a_polyhedron_take_fields_too():
    board = enclosures.Board(interface())
    prism = enclosures.prism_walls(board, 6)
    assert prism.outer.counts == (12, 18, 8) and prism.inner_radius == 0.0
    inside = 31.0 / 2 + math.sqrt(3) / 2 * 21.0                 # the hexagon's apothem; two of its sides face along x
    (field,) = enclosures.vent_fields(board, prism, "lid", vents=[{"wall": "lid", "margin": 12}])
    assert (field["rows"], field["columns"]) == (2, 11)
    sides = [(math.cos(math.radians(60 * k)), math.sin(math.radians(60 * k))) for k in range(6)]
    for opening in field["openings"]:                           # every slot keeps its margin from all six sides
        for end in opening["ends"]:
            assert min(inside - end[0] * c - end[1] * s for c, s in sides) - 1.0 >= 12.0 - 1e-9
    # and it is the largest that does: one more column, or one more row with more than five, does not fit
    for rows, columns, fits in ((2, 12, False), (3, 6, False), (3, 5, True)):
        vent = {"wall": "lid", "margin": 12, "rows": rows, "columns": columns}
        if fits:
            assert len(enclosures.vent_fields(board, prism, "lid", vents=[vent])[0]["openings"]) == rows * columns
        else:
            with pytest.raises(ValueError, match="does not fit the lid's plate"):
                enclosures.vent_fields(board, prism, "lid", vents=[vent])
    # a side by the direction it faces; "+y" names none, a corner of this hexagon points that way
    with pytest.raises(ValueError, match=r"2 walls face equally towards \+y; name the wall by the direction it faces"):
        enclosures.vent_fields(board, prism, "lid", vents=[{"wall": "+y", "half": "lid"}])
    towards = [0.5, math.sqrt(3) / 2, 0.0]
    (field,) = enclosures.vent_fields(board, prism, "lid", vents=[{"wall": towards, "half": "lid", "length": 6, "margin": 2}])
    assert (field["rows"], field["columns"]) == (1, 9) and field["thickness"] == pytest.approx(2.0)
    for opening in field["openings"]:
        assert dot(towards, opening["point"]) == pytest.approx(inside + 1.0) and opening["point"][2] == pytest.approx(7.325)

    # a truncated octahedron: its hexagons lean, and a field lies in the face, cut square to it
    given = {"wall": 2.5, "clearance": 1.5}
    solid = enclosures.polyhedron_walls(board, "truncated-octahedron", **given)
    up = {"wall": [1, 1, 1], "half": "lid"}
    with pytest.raises(ValueError, match=r"of the field in the wall towards \(1, 1, 1\) would come within 1.15 mm of the "
                                         "post over h2"):
        enclosures.vent_fields(board, solid, "lid", vents=[up], **given)
    (field,) = enclosures.vent_fields(board, solid, "lid", vents=[dict(up, rows=1, columns=3, centre=[12.0, 6.0])], **given)
    face = solid.outer.face_towards((1, 1, 1))
    assert field["thickness"] == pytest.approx(2.5) and field["volume_mm3"] == pytest.approx(3 * SLOT * 2.5)
    for opening in field["openings"]:
        assert dot(solid.outer.normals[face], opening["point"]) == pytest.approx(solid.outer.distances[face] - 1.25)
    # a face that leans outwards on its way up is nearly all in the base: a cut through it comes out lower than it
    # went in, and both ends stay below the board's top face
    down = {"wall": [1, 1, -1], "half": "base", "shape": "round", "diameter": 1.0, "margin": 0.5, "rows": 1, "columns": 1}
    (field,) = enclosures.vent_fields(board, solid, "base", vents=[dict(down, centre=[10.0, 22.9])], **given)
    normal, (middle,) = field["frame"]["normal"], [opening["point"] for opening in field["openings"]]
    rise = math.hypot(normal[0], normal[1])                     # of the face, for a step up it
    inner_end = middle[2] + 1.25 * abs(normal[2])               # where the hole's axis meets the cavity
    assert normal[2] < 0 and -1.0 < inner_end + 0.5 * rise < -0.5 * rise + 1e-9      # its rim keeps the margin from z = 0
    with pytest.raises(ValueError, match="reaches 0.08 mm beyond where the halves meet"):
        enclosures.vent_fields(board, solid, "base", vents=[dict(down, centre=[10.0, 23.5])], **given)
    with pytest.raises(ValueError, match="no field of slots of 2 x 12 mm fits the wall towards"):
        enclosures.vent_fields(board, solid, "lid", vents=[{"wall": [1, 1, -1], "half": "lid"}], **given)


def test_feet_stand_towards_the_corners_of_the_underside_inside_their_inset():
    board, walls = board_and_box()
    places = enclosures.foot_places(board, walls, feet={})
    # the underside is 66 x 46 mm with corners of 5 mm; a foot of 8 mm keeps 2 mm from its straight edges
    assert places["at"] == [pytest.approx(p) for p in ((27.0, 17.0), (-27.0, 17.0), (-27.0, -17.0), (27.0, -17.0))]
    assert places["z"] == pytest.approx(-7.1) and (places["diameter"], places["height"]) == (8.0, 1.5)
    assert places["points"][0] == pytest.approx((27.0, 17.0, -7.85))
    assert places["volume_mm3"] == pytest.approx(4 * math.pi * 16.0 * 1.5)
    assert enclosures.foot_places(board, walls) is None
    # a small foot goes into the round corner: its edge 1 mm from the arc, on the diagonal
    small = enclosures.foot_places(board, walls, feet={"diameter": 4.0, "inset": 1.0})
    x, y = small["at"][0]
    assert (x, y) == pytest.approx((28.0 + math.sqrt(2), 18.0 + math.sqrt(2)))
    assert 5.0 - math.hypot(x - 28.0, y - 18.0) - 2.0 == pytest.approx(1.0)
    # a hexagon: four of its six corners; an octagon whose cut is long enough: the middle of each cut
    prism = enclosures.prism_walls(board, 6)
    out = 31.0 / 2 + math.sqrt(3) / 2 * 21.0 + 2.0              # the apothem of the prism's outside
    assert enclosures.foot_places(board, prism, feet={})["at"][0] == pytest.approx(((out - 6.0), (out - 6.0) / math.sqrt(3)))
    rounder = interface()
    rounder["features"][0]["corner_radius"] = 8.0
    board8 = enclosures.Board(rounder)
    cut = (2 - math.sqrt(2)) * (8.0 + 1.0 + 2.0)                # of the outside: the cavity's and the wall's share
    x, y = enclosures.foot_places(board8, enclosures.octagon_walls(board8), feet={})["at"][0]
    assert x - y == pytest.approx(10.0) and (33.0 + 23.0 - cut - x - y) / math.sqrt(2) == pytest.approx(6.0)
    # where the feet are is said instead
    three = enclosures.foot_places(board, walls, feet={"at": [[-25.0, -15.0], [25.0, -15.0], [0.0, 15.0]], "height": 3.0})
    assert three["at"] == [(-25.0, -15.0), (25.0, -15.0), (0.0, 15.0)] and three["points"][2] == pytest.approx((0.0, 15.0, -8.6))


def test_feet_that_do_not_fit_or_would_not_carry_the_base_are_refused():
    board, walls = board_and_box()

    def places(use=walls, **given):
        return enclosures.foot_places(board, use, **given)

    with pytest.raises(ValueError, match="feet of 8 mm with an inset of 20 mm do not fit under an underside of 66.00 x 46.00 mm"):
        places(feet={"inset": 20.0})
    with pytest.raises(ValueError, match=r"the feet at \(15.00, 5.00\) and \(-15.00, 5.00\) stand in each other"):
        places(feet={"diameter": 32.0})
    with pytest.raises(ValueError, match=r"the foot at \(30.00, 0.00\) reaches 1.00 mm beyond the edge of the underside"):
        places(feet={"at": [[30.0, 0.0], [-20.0, 10.0], [-20.0, -10.0]]})
    with pytest.raises(ValueError, match=r"the foot at \(28.00, 0.00\) comes within 1.00 mm of the edge of the underside; an "
                                         "inset of 2 mm is asked for"):
        places(feet={"at": [[28.0, 0.0], [-20.0, 10.0], [-20.0, -10.0]]})
    for at in ([[-20.0, 0.0], [20.0, 0.0]], [[-20.0, 0.0], [0.0, 0.0], [20.0, 0.0]],
               [[10.0, -10.0], [20.0, -10.0], [15.0, 10.0]]):                # two; three in a line; all on one side
        with pytest.raises(ValueError, match="the base would not stand on these feet"):
            places(feet={"at": at})
    # never under an opening: a vent of the floor, or the window of a port that goes through the floor
    floor = [{"wall": "floor", "shape": "round", "margin": 8}]
    with pytest.raises(ValueError, match=r"the foot at \(20.00, 10.00\) would stand under the vent at \(20.00, 5.00\) of the floor"):
        places(vents=floor, feet={"at": [[20.0, 10.0], [-20.0, 10.0], [0.0, -15.0]]})
    assert places(vents=floor, feet={})["at"][0] == pytest.approx((27.0, 17.0))       # beside the field they stand
    down = interface()
    down["features"].append({"id": "j3", "kind": "port", "direction": [0.0, 0.0, -1.0], "reference": "J3",
                             "box": {"min": [195.0, -155.0, TOP - 3.6], "max": [205.0, -145.0, TOP - 1.6]}})
    under = enclosures.Board(down)
    with pytest.raises(ValueError, match=r"the foot at \(0.00, 8.00\) would stand under the opening for J3, which goes through"):
        enclosures.foot_places(under, walls, openings=["J3"], feet={"at": [[0.0, 8.0], [-20.0, -10.0], [20.0, -10.0]]})
    assert enclosures.foot_places(under, walls, openings=["J3"], feet={"at": [[0.0, 10.0], [-20.0, -10.0], [20.0, -10.0]]})
    # an octahedron as it lies stands on a corner
    with pytest.raises(ValueError, match="does not stand on a level face"):
        places(enclosures.polyhedron_walls(board, "octahedron"), feet={})
    for feet, message in (({"radius": 4}, "not a setting of feet: radius"), ({"height": 0}, "height of the feet must be"),
                          ({"at": [[1, 2, 3]]}, r"at is a list of \[x, y\]"), (4, "feet are given by their settings")):
        with pytest.raises(ValueError, match=message):
            places(feet=feet)


def test_two_fields_in_one_wall_keep_the_wider_web_of_the_two_whichever_comes_first():
    board, walls = board_and_box()
    # two slots 8 mm apart about x = -10 and two 3 mm apart about x = 0: 2.5 mm are left between the fields. The
    # first field asks for 6 mm between openings, the second for 1 mm
    wide = {"wall": "lid", "rows": 1, "columns": 2, "centre": [-10.0, 0.0], "web": 6.0}
    narrow = {"wall": "lid", "rows": 1, "columns": 2, "centre": [0.0, 0.0], "web": 1.0}
    for vents in ([narrow, wide], [wide, narrow]):
        with pytest.raises(ValueError, match="would come within 2.50 mm of a vent of an earlier field in the same wall; "
                                             "6 mm is to be left between them"):
            enclosures.vent_fields(board, walls, "lid", vents=vents)
    # 6 mm apart they are both accepted, in either order
    apart = dict(narrow, centre=[3.5, 0.0])
    for vents in ([apart, wide], [wide, apart]):
        assert len(enclosures.vent_fields(board, walls, "lid", vents=vents)) == 2


def test_a_setting_that_would_be_ignored_is_refused():
    board, walls = board_and_box()
    # a round hole has a diameter and a slot a width and a length: the other shape's sizes say nothing
    hole = {"wall": "lid", "shape": "round"}
    for vent, message in ((dict(hole, width=2.5), "width is a setting of a slot; a round hole has its `diameter`"),
                          (dict(hole, length=8.0), "length is a setting of a slot"),
                          (dict(hole, along="u"), "along is a setting of a slot"),
                          ({"wall": "lid", "diameter": 2.5}, "diameter is a setting of a round hole; a slot has its `width` and `length`"),
                          # the direction a wall faces follows from its name
                          ({"wall": "lid", "towards": [1.0, 0.0, 0.0]}, "not a setting of a field of vents: towards"),
                          # a number that is none
                          ({"wall": [float("nan"), 0.0, 1.0]}, "a field of vents names its wall"),
                          ({"wall": "lid", "centre": [0.0, float("inf")]}, "centre of a field of vents is")):
        with pytest.raises(ValueError, match=message):
            enclosures.vent_fields(board, walls, "lid", vents=[vent])
    with pytest.raises(ValueError, match=r"at is a list of \[x, y\]"):
        enclosures.foot_places(board, walls, feet={"at": [[float("nan"), 0.0], [-20.0, -10.0], [20.0, -10.0]]})
    # what `settings` gives back is what was asked for, and is accepted again as it is
    given = {"vents": [{"wall": [1, 1, 0], "half": "lid", "shape": "round", "centre": [0, 5]}, {"wall": "floor", "length": 9}],
             "feet": {"at": [[-20, -10], [20, -10], [0, 15]]}}
    once = enclosures.settings(given)
    assert enclosures.settings(once) == once
    assert once["vents"][0] == {"wall": [1.0, 1.0, 0.0], "half": "lid", "shape": "round", "diameter": 3.0, "web": 2.0,
                                "margin": 3.0, "stagger": False, "rows": None, "columns": None, "centre": (0.0, 5.0)}
    assert once["vents"][1]["length"] == 9 and "diameter" not in once["vents"][1]


def test_pockets_for_stick_on_feet_are_placed_as_bosses_are_and_keep_clear_of_what_else_is_cut():
    board, walls = board_and_box()
    recess = {"kind": "recess"}

    def places(use=walls, on=board, **given):
        return enclosures.foot_places(on, use, **given)

    # A pocket for a foot of 8 mm is 8.4 mm across, with 0.2 mm around the foot, and 1 mm deep in a floor of 2 mm.
    # Towards the corners, 2 mm from the edge, it would lie under a standoff, whose hole for the insert comes down
    # to 0.6 mm over the underside: refused. 8 mm from the edge the four are 1.15 mm clear of the holes
    with pytest.raises(ValueError, match=r"the pocket at \(-26.80, 16.80\) would run into the hole for the insert under h1; "
                                         "0.8 mm is to be left between them"):
        places(feet=recess)
    with pytest.raises(ValueError, match=r"the pocket at \(-21.30, 11.30\) would come within 0.45 mm of the hole for the insert"):
        places(feet=dict(recess, inset=7.5))
    four = places(feet=dict(recess, inset=8))
    assert four["at"] == [pytest.approx(p) for p in ((20.8, 10.8), (-20.8, 10.8), (-20.8, -10.8), (20.8, -10.8))]
    assert math.hypot(26.0 - 20.8, 16.0 - 10.8) - 4.2 - 2.0 == pytest.approx(1.154, abs=1e-3)
    assert (four["kind"], four["z"], four["diameter"], four["depth"]) == ("recess", pytest.approx(-7.1), 8.0, 1.0)
    assert (four["across"], four["floor"]) == (pytest.approx(8.4), pytest.approx(1.0))
    assert four["points"][0] == pytest.approx((20.8, 10.8, -6.6))                 # halfway up the pocket: nothing there
    assert four["volume_mm3"] == pytest.approx(4 * math.pi * 4.2 ** 2 * 1.0)
    assert places(feet={})["kind"] == "boss"
    # where the standoffs are high their holes end well over the floor, and a pocket may lie under one
    high = enclosures.box_walls(board, under=5)
    assert places(high, feet=recess, under=5)["at"][0] == pytest.approx((26.8, 16.8))
    # how wide and how deep the hole of a named insert is only its table says: a pocket keeps clear of the standoff
    with pytest.raises(ValueError, match=r"the pocket at \(-20.80, 10.80\) would run into the standoff under h1, which holds "
                                         "the hole for the insert"):
        places(feet=dict(recess, inset=8), insert="M3-0.5-Short")
    with pytest.raises(ValueError, match="would run into the standoff under h1"):
        places(high, feet=recess, under=5, insert="M3-0.5-Short")
    assert places(feet=dict(recess, inset=9), insert="M3-0.5-Short")["at"][0] == pytest.approx((19.8, 9.8))
    # too little floor is left over a pocket
    with pytest.raises(ValueError, match="a pocket 1.5 mm deep would leave 0.50 mm of the floor, which is 2 mm thick; 0.8 mm "
                                         "is the least"):
        places(feet=dict(recess, inset=8, depth=1.5))
    assert places(enclosures.box_walls(board, floor=3), feet=dict(recess, inset=8, depth=1.5), floor=3)["floor"] == pytest.approx(1.5)
    # a vent of the floor: its field's web is left; the window of a port that comes down into the floor: 0.8 mm
    vent = [{"wall": "floor", "shape": "round", "rows": 1, "columns": 3}]
    with pytest.raises(ValueError, match=r"the pocket at \(0.00, 7.50\) would come within 1.80 mm of the vent at \(0.00, 0.00\) "
                                         "of the floor; 2 mm is to be left between them"):
        places(vents=vent, feet=dict(recess, at=[[0.0, 7.5], [-20.0, -10.0], [20.0, -10.0]]))
    assert places(vents=vent, feet=dict(recess, at=[[0.0, 8.0], [-20.0, -10.0], [20.0, -10.0]]))["at"][0] == (0.0, 8.0)
    down = interface()
    down["features"].append({"id": "j3", "kind": "port", "direction": [0.0, 0.0, -1.0], "reference": "J3",
                             "box": {"min": [195.0, -155.0, TOP - 3.6], "max": [205.0, -145.0, TOP - 1.6]}})
    under = enclosures.Board(down)
    with pytest.raises(ValueError, match=r"the pocket at \(0.00, 10.00\) would come within 0.30 mm of the opening for J3, which "
                                         "comes down into the floor; 0.8 mm is to be left"):
        places(on=under, openings=["J3"], feet=dict(recess, at=[[0.0, 10.0], [-20.0, -10.0], [20.0, -10.0]]))
    assert places(on=under, openings=["J3"], feet=dict(recess, at=[[0.0, 10.5], [-20.0, -10.0], [20.0, -10.0]]))
    # the window of J2 is in the wall, well over the floor: a pocket may lie under it
    assert places(openings=["J2"], feet=dict(recess, at=[[-26.0, 0.0], [20.0, -10.0], [20.0, 10.0]]))
    # the edge of the underside is kept from by the pocket, not by the foot in it
    with pytest.raises(ValueError, match=r"the pocket at \(28.50, 0.00\) comes within 0.30 mm of the edge of the underside"):
        places(feet=dict(recess, at=[[28.5, 0.0], [-20.0, -10.0], [-20.0, 10.0]]))
    with pytest.raises(ValueError, match="pockets of 8.4 mm with an inset of 20 mm do not fit under an underside"):
        places(feet=dict(recess, inset=20.0))
    # a polyhedron that stands on a face has a floor as thick as its wall; a cavity without a level floor has none
    given = {"wall": 2.5, "clearance": 1.5}
    solid = enclosures.polyhedron_walls(board, "truncated-octahedron", **given)
    assert places(solid, feet=dict(recess, diameter=6.0), **given)["floor"] == pytest.approx(1.5)
    from mechanical_cad.shapes import polyhedra
    with pytest.raises(ValueError, match="the cavity has no level floor over the underside"):
        places(enclosures.Walls(walls.outer, polyhedra.named("octahedron", edge=20.0)), feet=dict(recess, inset=8))
    for feet, message in ((dict(recess, height=2.0), "height is a setting of a boss; a recess has its `depth` and `clearance`"),
                          ({"depth": 1.0}, "depth is a setting of a recess for a stick-on foot; a boss has its `height`"),
                          ({"clearance": 0.3}, "clearance is a setting of a recess"),
                          ({"kind": "pad"}, 'the kind of feet is "boss" or "recess"'),
                          (dict(recess, clearance=0), "clearance of the feet must be a positive number")):
        with pytest.raises(ValueError, match=message):
            places(feet=feet)


def apart(field):
    """The least that is left between two openings of a field, and how many pairs are that near."""
    gaps = sorted(enclosures._segments_apart(*a["ends"], *b["ends"]) - 2 * field["radius"]
                  for k, a in enumerate(field["openings"]) for b in field["openings"][:k])
    return gaps[0], sum(1 for gap in gaps if gap < gaps[0] + 1e-9)


def test_every_second_row_of_a_staggered_field_stands_between_the_openings_of_the_row_before():
    board, walls = without_holes(), board_and_box()[1]
    # round holes of 3 mm with 2 mm between: 5 mm from hole to hole along a row, and the rows 5 x sin 60 apart,
    # so that every hole is 5 mm from the two it stands between. Inside a margin of 5 mm the plate, 62 x 42 mm,
    # holds seven such rows where it holds six that are not staggered; every second one has nine holes for ten
    holes = {"wall": "lid", "shape": "round", "margin": 5}
    (plain,) = enclosures.vent_fields(board, walls, "lid", vents=[holes])
    (field,) = enclosures.vent_fields(board, walls, "lid", vents=[dict(holes, stagger=True)])
    assert (plain["rows"], plain["columns"], len(plain["openings"]), plain["stagger"]) == (6, 10, 60, False)
    assert (field["rows"], field["columns"], len(field["openings"]), field["stagger"]) == (7, 10, 67, True)
    rise = 5.0 * math.sqrt(3) / 2
    assert [opening["centre"] for opening in field["openings"][:10]] == [pytest.approx((-22.5 + 5.0 * k, -3 * rise)) for k in range(10)]
    assert [opening["centre"] for opening in field["openings"][10:19]] == [pytest.approx((-20.0 + 5.0 * k, -2 * rise)) for k in range(9)]
    assert field["openings"][-1]["centre"] == pytest.approx((22.5, 3 * rise))
    assert field["volume_mm3"] == pytest.approx(67 * math.pi * 1.5 ** 2 * 2.0)
    # 2 mm are left between a hole and each of its neighbours: the next in its row, nine pairs in a row of ten and
    # eight in a row of nine, and the two it stands between, 18 pairs from each row to the next. In the field that
    # is not staggered a hole has four neighbours
    assert apart(field) == (pytest.approx(2.0), 4 * 9 + 3 * 8 + 6 * 18) and apart(plain) == (pytest.approx(2.0), 6 * 9 + 5 * 10)

    # slots that stand up the wall, 2 x 12 mm: the second row stands half of 4 mm along, and its round ends come
    # between those of the first until 2 mm are left: 10 + sqrt(4^2 - 2^2) from row to row where it was 14
    (field,) = enclosures.vent_fields(board, walls, "lid", vents=[{"wall": "lid", "margin": 4, "stagger": True}])
    assert (field["rows"], field["columns"], len(field["openings"])) == (2, 14, 27)
    assert field["openings"][14]["centre"][0] - field["openings"][0]["centre"][0] == pytest.approx(2.0)
    assert field["openings"][14]["centre"][1] - field["openings"][0]["centre"][1] == pytest.approx(10.0 + math.sqrt(12.0))
    assert apart(field)[0] == pytest.approx(2.0)
    # slots that lie along the wall: long ones lie over each other in the next row and keep the rows 4 mm apart;
    # short ones, 2 x 3 mm, let the next row come nearer
    for length, rise in ((6.0, 4.0), (3.0, math.sqrt(16.0 - 1.5 ** 2))):
        (field,) = enclosures.vent_fields(board, walls, "lid", vents=[
            {"wall": "lid", "along": "u", "length": length, "rows": 3, "columns": 4, "stagger": True}])
        assert [len([o for o in field["openings"] if o["centre"][1] == pytest.approx(v)]) for v in (-rise, 0.0, rise)] == [4, 3, 4]
        assert field["openings"][4]["centre"] == pytest.approx((-(length + 2.0), 0.0))
        assert apart(field)[0] == pytest.approx(2.0)
    # the margin is kept by the rows that are shorter too: in a hexagon it is the second row from the end that
    # comes nearest to a side
    hexagon = enclosures.prism_walls(board, 6)
    inside = 31.0 / 2 + math.sqrt(3) / 2 * 21.0
    sides = [(math.cos(math.radians(60 * k)), math.sin(math.radians(60 * k))) for k in range(6)]
    (field,) = enclosures.vent_fields(board, hexagon, "lid", vents=[dict(holes, stagger=True, margin=4)])
    rooms = [min(inside - o["centre"][0] * c - o["centre"][1] * s for c, s in sides) - 1.5 for o in field["openings"]]
    assert min(rooms) >= 4.0 - 1e-9 and len(field["openings"]) == sum(field["columns"] - j % 2 for j in range(field["rows"]))
    for more in ({"rows": field["rows"] + 1, "columns": field["columns"]}, {"rows": field["rows"], "columns": field["columns"] + 1}):
        with pytest.raises(ValueError, match="a staggered field of .* holes of 3 mm with a web of 2 mm does not fit the lid's plate"):
            enclosures.vent_fields(board, hexagon, "lid", vents=[dict(holes, stagger=True, margin=4, **more)])
    # a field of one row or one column has nothing to stagger
    for vent, message in ((dict(holes, stagger=True, rows=1), "a staggered field has 2 rows and 2 columns or more"),
                          (dict(holes, stagger=True, columns=1), "a staggered field has 2 rows and 2 columns or more"),
                          (dict(holes, stagger="yes"), "stagger of a field of vents is true or false"),
                          ({"wall": "+x", "half": "lid", "stagger": True}, "no staggered field of slots of 2 x 12 mm fits the wall")):
        with pytest.raises(ValueError, match=message):
            enclosures.vent_fields(board, walls, "lid", vents=[vent])


def rounder_board(holes=False):
    """The board of the other tests with its corners rounded with 8 mm, and without its mounting holes unless
    they are asked for: the cavity of its box is rounded with 9 mm about (22, 12), the outside with 11 mm."""
    rounder = interface()
    rounder["features"][0]["corner_radius"] = 8.0
    if not holes:
        rounder["features"] = [f for f in rounder["features"] if f["kind"] != "hole"]
    return enclosures.Board(rounder)


def through_a_corner(u, radius, reach=0.0, level=False, inner=9.0, outer=11.0, strips=4000):
    """What an opening takes out of a round corner when it is cut along the corner's middle, added up strip by
    strip: to the side by x the opening is `chord` high and the wall sqrt(outer^2 - x^2) - sqrt(inner^2 - x^2) deep."""
    half = radius + reach if level else radius
    total = 0.0
    for k in range(strips):
        x = -half + (k + 0.5) * 2 * half / strips
        beyond = max(0.0, abs(x) - reach) if level else abs(x)
        chord = 2 * math.sqrt(radius * radius - beyond * beyond) + (0.0 if level else 2 * reach)
        total += chord * (math.sqrt(outer ** 2 - (u + x) ** 2) - math.sqrt(inner ** 2 - (u + x) ** 2)) * 2 * half / strips
    return total


def test_a_round_corner_of_the_box_takes_a_field_cut_along_its_middle():
    board = rounder_board()
    walls = enclosures.box_walls(board)
    # Seen along the corner's middle, the direction between its two walls, the round of the cavity is 9 x sqrt 2 =
    # 12.73 mm across; a cut there has to go 11 - 9 / sqrt 2 = 4.64 mm deep, where the wall is 2 mm in the middle
    corner = {"wall": [1, 1, 0], "half": "lid", "shape": "round", "diameter": 2.0, "web": 1.5, "margin": 1.4}
    (field,) = enclosures.vent_fields(board, walls, "lid", vents=[corner])
    assert (field["rows"], field["columns"]) == (2, 3) and field["thickness"] == pytest.approx(11.0 - 9.0 / math.sqrt(2))
    assert [o["centre"] for o in field["openings"]] == [pytest.approx((u, v)) for v in (5.575, 9.075) for u in (-3.5, 0.0, 3.5)]
    assert field["frame"]["normal"] == pytest.approx((math.sqrt(0.5), math.sqrt(0.5), 0.0))
    assert field["frame"]["origin"] == pytest.approx((22.0 + 11.0 * math.sqrt(0.5), 12.0 + 11.0 * math.sqrt(0.5), 0.0))
    # the middle of every opening is in the wall, halfway through it along the cut
    assert field["openings"][1]["point"] == pytest.approx((22.0 + 10.0 * math.sqrt(0.5), 12.0 + 10.0 * math.sqrt(0.5), 5.575))
    for opening in field["openings"]:
        x, y, _ = opening["point"]
        assert 9.9 < math.hypot(x - 22.0, y - 12.0) < 10.1
    # a hole along the middle takes a little more than its area times the wall, one beside it more than that
    assert field["volume_mm3"] == pytest.approx(2 * (through_a_corner(0.0, 1.0) + 2 * through_a_corner(3.5, 1.0)), rel=1e-5)
    assert math.pi * 2.0 < through_a_corner(0.0, 1.0) < math.pi * 2.01 < through_a_corner(3.5, 1.0) < math.pi * 2.2
    # slots, upright and level, in the corner opposite; the base has the corner up to the board's top face
    for vent, level in (({"length": 5.0, "margin": 1.0}, False), ({"length": 4.0, "along": "u", "margin": 0.8}, True)):
        (slots,) = enclosures.vent_fields(board, walls, "lid", vents=[dict(vent, wall=[-1, -1, 0], half="lid")])
        assert slots["frame"]["normal"] == pytest.approx((-math.sqrt(0.5), -math.sqrt(0.5), 0.0))
        reach = (vent["length"] - 2.0) / 2
        assert slots["volume_mm3"] == pytest.approx(sum(through_a_corner(o["centre"][0], 1.0, reach, level)
                                                        for o in slots["openings"]), rel=1e-5)
    (low,) = enclosures.vent_fields(board, walls, "base", vents=[dict(corner, half="base", margin=0.8)])
    assert [o["centre"] for o in low["openings"]] == [pytest.approx((u, -2.55)) for u in (-3.5, 0.0, 3.5)]
    assert enclosures.vent_fields(board, walls, "base", vents=[corner]) == []
    # a second field in the same corner keeps its web from the first, and the lid's part ends over the lip
    one = dict(corner, rows=1, columns=1, centre=[-2.0, 8.0])
    with pytest.raises(ValueError, match="would come within 1.00 mm of a vent of an earlier field in the same wall"):
        enclosures.vent_fields(board, walls, "lid", vents=[one, dict(one, centre=[1.0, 8.0])])
    with pytest.raises(ValueError, match=r"does not fit the round corner towards \(1, 1, 0\), whose plain part in the lid is "
                                         "12.73 x 11.35 mm: .* it comes within 0.35 mm of the lip"):
        enclosures.vent_fields(board, walls, "lid", vents=[dict(one, centre=[0.0, 3.0])])
    with pytest.raises(ValueError, match=r"the round corner towards \(1, 1, 0\) is divided between the base and the lid"):
        enclosures.vent_fields(board, walls, "lid", vents=[{"wall": [1, 1, 0]}])
    # where a post stands in the corner, as the mounting holes of this board would have it, the field is refused
    with_posts = rounder_board(holes=True)
    with pytest.raises(ValueError, match=r"of the field in the round corner towards \(1, 1, 0\) would cut into the post over h2"):
        enclosures.vent_fields(with_posts, enclosures.box_walls(with_posts), "lid", vents=[corner])
    # the corner of the board the other tests use is rounded with 3 mm inside: 4.24 mm across, too little for this
    small = enclosures.Board(interface())
    with pytest.raises(ValueError, match=r"no field of holes of 2 mm fits the round corner towards \(1, 1, 0\), whose plain "
                                         "part in the lid is 4.24 x 11.35 mm"):
        enclosures.vent_fields(small, enclosures.box_walls(small), "lid", vents=[corner])
    # a box with sharp corners has none, and neither has a prism: there the direction names no wall
    sharp = enclosures.Walls(walls.outer, walls.cavity)
    with pytest.raises(ValueError, match="2 walls face equally towards"):
        enclosures.vent_fields(board, sharp, "lid", vents=[corner])


def test_a_prism_on_a_triangle_gets_three_feet():
    board = enclosures.Board(interface())
    # the triangle's outside has an apothem of 39.35 mm; a foot of 8 mm with an inset of 2 mm stands 6 mm inside
    # each of the two sides that meet in a corner. Two of the four directions the feet are looked for in meet
    # the same corner
    inside = math.sqrt(3) / 2 * 31.0 + 21.0 / 2 + 2.0 - 6.0
    places = enclosures.foot_places(board, enclosures.prism_walls(board, 3), feet={})
    assert places["at"] == [pytest.approx(p) for p in ((0.0, 2 * inside), (-math.sqrt(3) * inside, -inside),
                                                       (math.sqrt(3) * inside, -inside))]
    assert places["volume_mm3"] == pytest.approx(3 * math.pi * 16.0 * 1.5)


@with_build123d
def test_the_vents_of_a_box_take_out_what_was_worked_out_and_nothing_else():
    from build123d import Vector

    board = enclosures.Board(interface())
    given = {"openings": ["J1", "J2"]}
    vents = [{"wall": "lid", "margin": 9, "centre": [-10.0, 0.0], "columns": 6},
             {"wall": "+x", "half": "lid", "length": 6, "margin": 2},
             {"wall": "+y", "half": "lid", "shape": "round", "diameter": 2.5, "rows": 2, "columns": 8, "margin": 2},
             {"wall": "floor", "shape": "round", "margin": 8},
             {"wall": "-y", "half": "base", "shape": "round", "diameter": 2.0, "margin": 1}]
    walls = enclosures.box_walls(board, **given)
    for half, make in (("lid", enclosures.box_lid), ("base", enclosures.box_base)):
        plain, vented = make(board, **given), make(board, vents=vents, **given)
        fields = enclosures.vent_fields(board, walls, half, vents=vents, **given)
        assert len(fields) == (3 if half == "lid" else 2)
        assert vented.is_valid and len(vented.solids()) == 1
        assert plain.volume - vented.volume == pytest.approx(sum(field["volume_mm3"] for field in fields), rel=1e-9)
        assert tuple(vented.bounding_box().size) == pytest.approx(tuple(plain.bounding_box().size))
        for field in fields:
            n, u = field["frame"]["normal"], field["frame"]["u"]
            for opening in field["openings"]:
                middle = Vector(*opening["point"])
                assert plain.is_inside(middle) and not vented.is_inside(middle)
                # the web beside a vent, and the wall just outside the vent's round end, are whole
                beside = middle + Vector(*u) * (field["radius"] + 0.5)
                assert vented.is_inside(beside)
    # the plate has six slots where it had none: through it at one of them, whole between two
    lid = enclosures.box_lid(board, vents=vents, **given)
    assert not lid.is_inside(Vector(-20.0, 4.0, 14.0)) and lid.is_inside(Vector(-18.0, 4.0, 14.0))
    assert not lid.is_inside(Vector(32.0, -14.0, 7.325)) and lid.is_inside(Vector(-32.0, -14.0, 7.325))


@with_build123d
def test_vents_and_feet_in_a_prism_and_in_a_polyhedron_are_held_to_their_volume():
    board = enclosures.Board(interface())
    cases = [
        (enclosures.prism_halves, enclosures.prism_walls, (6,), {}, [
            {"wall": "lid", "margin": 12}, {"wall": "+x", "half": "lid", "length": 5, "margin": 2},
            {"wall": "floor", "shape": "round", "diameter": 4, "margin": 10, "rows": 3, "columns": 6}], {}),
        (enclosures.octagon_halves, enclosures.octagon_walls, (), {}, [
            {"wall": [1, 1, 0], "half": "lid", "shape": "round", "diameter": 1.0, "web": 1, "margin": 0.5},
            {"wall": "floor", "margin": 9}, {"wall": "-y", "half": "lid", "length": 6, "margin": 2}], {}),
        (enclosures.polyhedron_halves, enclosures.polyhedron_walls, ("truncated-octahedron",), {"wall": 2.5, "clearance": 1.5}, [
            {"wall": "lid"}, {"wall": [1, 1, 1], "half": "lid", "centre": [12, 6], "rows": 1, "columns": 3},
            {"wall": [1, 1, -1], "half": "base", "centre": [10, -8], "along": "u", "rows": 3, "columns": 1},
            {"wall": "+x", "half": "lid"}, {"wall": "floor", "shape": "round", "diameter": 2.0, "margin": 9}], {"diameter": 6.0}),
    ]
    for make, describe, args, given, vents, feet in cases:
        plain = make(board, *args, **given)
        both = make(board, *args, vents=vents, feet=feet, **given)
        walls = describe(board, *args, **given)
        places = enclosures.foot_places(board, walls, vents=vents, feet=feet, **given)
        for k, half in enumerate(("base", "lid")):
            fields = enclosures.vent_fields(board, walls, half, vents=vents, **given)
            assert fields and both[k].is_valid and len(both[k].solids()) == 1
            added = places["volume_mm3"] if half == "base" else 0.0
            removed = sum(field["volume_mm3"] for field in fields)
            assert both[k].volume - plain[k].volume == pytest.approx(added - removed, rel=1e-7)
        # the base stands on its feet and on nothing else, 1.5 mm lower than without
        on = enclosures.standing(both[0])
        assert on["stands"] and len(on["contacts"]) == 4 and on["z"] == pytest.approx(places["z"] - 1.5)
        assert [contact["centre"] for contact in on["contacts"]] == [pytest.approx(p, abs=1e-6) for p in sorted(places["at"])]
        assert enclosures.standing(plain[0])["z"] == pytest.approx(places["z"])
    # without the walls as polyhedra nothing says where a wall is flat
    from mechanical_cad.shapes import forms

    walls = enclosures.prism_walls(board, 6)
    with pytest.raises(ValueError, match="vents and feet are laid out on flat walls: give `walls`"):
        enclosures.halves(board, forms.solid(walls.outer), forms.solid(walls.cavity), feet={})


@with_build123d
def test_a_base_with_feet_stands_on_them_and_what_does_not_stand_is_said():
    from build123d import Box, Pos, Sphere

    board = enclosures.Board(interface())
    plain, footed = enclosures.box_base(board), enclosures.box_base(board, feet={})
    assert footed.is_valid and len(footed.solids()) == 1
    assert footed.volume - plain.volume == pytest.approx(4 * math.pi * 16.0 * 1.5, rel=1e-9)
    assert footed.bounding_box().min.Z == pytest.approx(-7.1 - 1.5) and plain.bounding_box().min.Z == pytest.approx(-7.1)
    on = enclosures.standing(footed)
    assert on["z"] == pytest.approx(-8.6) and on["stands"]
    assert [contact["centre"] for contact in on["contacts"]] == [
        pytest.approx(p, abs=1e-6) for p in ((-27.0, -17.0), (-27.0, 17.0), (27.0, -17.0), (27.0, 17.0))]
    assert all(contact["area_mm2"] == pytest.approx(math.pi * 16.0) for contact in on["contacts"])
    # the centre of mass is well inside what the feet span, which reaches to their far edges at 31 and 21 mm
    assert on["centre_of_mass"] == pytest.approx((0.0, 0.0), abs=0.5) and on["margin_mm"] == pytest.approx(21.0, abs=0.2)
    # without feet the base lies on its floor
    flat = enclosures.standing(plain)
    assert len(flat["contacts"]) == 1 and flat["stands"]
    assert flat["area_mm2"] == pytest.approx(66.0 * 46.0 - (4 - math.pi) * 25.0)
    # an arm that reaches out further than its foot does not stand: its centre of mass is 5 mm outside the foot
    arm = Box(10, 10, 10) + Pos(25, 0, 7.5) * Box(60, 10, 5)
    tips = enclosures.standing(arm)
    assert len(tips["contacts"]) == 1 and not tips["stands"]
    assert tips["centre_of_mass"][0] == pytest.approx(60 * 10 * 5 * 25 / (1000 + 3000)) and tips["margin_mm"] == pytest.approx(5.0 - 18.75)
    # nor does a ball, which has no flat face to stand on
    assert not enclosures.standing(Sphere(5))["stands"] and enclosures.standing(Sphere(5))["contacts"] == []
    # feet on three sides of the middle carry the base; a foot under the floor's vents is refused before anything is built
    three = enclosures.box_base(board, feet={"at": [[-25.0, -15.0], [25.0, -15.0], [0.0, 15.0]]})
    assert len(enclosures.standing(three)["contacts"]) == 3 and enclosures.standing(three)["stands"]
    with pytest.raises(ValueError, match="would stand under the vent"):
        enclosures.box_base(board, vents=[{"wall": "floor", "shape": "round", "margin": 8}],
                            feet={"at": [[20.0, 10.0], [-20.0, 10.0], [0.0, -15.0]]})


def measured(solid):
    """A solid's volume by the kernel's adaptive integration, asked for more closely than the module asks."""
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps

    properties = GProp_GProps()
    BRepGProp.VolumeProperties_s(solid.wrapped, properties, 1e-9)
    return properties.Mass()


@with_build123d
def test_staggered_fields_and_fields_in_round_corners_take_out_what_was_worked_out():
    from build123d import Vector

    board = rounder_board()
    walls = enclosures.box_walls(board)
    vents = [{"wall": "lid", "shape": "round", "margin": 8, "stagger": True},
             {"wall": "-y", "half": "lid", "length": 3.5, "margin": 1.0, "stagger": True},
             {"wall": [1, 1, 0], "half": "lid", "shape": "round", "diameter": 2.0, "web": 1.5, "margin": 1.4},
             {"wall": [-1, 1, 0], "half": "lid", "length": 5, "margin": 1.0},
             {"wall": [-1, -1, 0], "half": "lid", "length": 4, "along": "u", "margin": 0.8},
             {"wall": [1, -1, 0], "half": "base", "shape": "round", "diameter": 1.5, "web": 1.0, "margin": 0.6, "stagger": True},
             {"wall": "floor", "along": "u", "length": 5, "margin": 10, "stagger": True}]
    for half, make, count in (("lid", enclosures.box_lid, 5), ("base", enclosures.box_base, 2)):
        plain, vented = make(board), make(board, vents=vents)
        fields = enclosures.vent_fields(board, walls, half, vents=vents)
        assert len(fields) == count and vented.is_valid and len(vented.solids()) == 1
        assert measured(plain) - measured(vented) == pytest.approx(sum(field["volume_mm3"] for field in fields), abs=1e-5)
        assert tuple(vented.bounding_box().size) == pytest.approx(tuple(plain.bounding_box().size))
        for field in fields:
            assert field["stagger"] == (len(field["openings"]) != field["rows"] * field["columns"])
            for opening in field["openings"]:
                middle = Vector(*opening["point"])
                assert plain.is_inside(middle) and not vented.is_inside(middle)
    # in the corner towards +x and +y the lid is open along the corner's middle and whole between two holes
    lid = enclosures.box_lid(board, vents=vents)
    along = Vector(math.sqrt(0.5), math.sqrt(0.5), 0.0)
    axis, aside = Vector(22.0, 12.0, 5.575), Vector(-math.sqrt(0.5), math.sqrt(0.5), 0.0)
    for reach in (9.2, 10.0, 10.8):
        assert not lid.is_inside(axis + along * reach) and lid.is_inside(axis + along * reach + aside * 1.75)
    # build123d's own figure for the lid, the kernel's plain integration, is out by more than the module allows
    assert abs((enclosures.box_lid(board).volume - lid.volume) - sum(
        field["volume_mm3"] for field in enclosures.vent_fields(board, walls, "lid", vents=vents))) > 0.02


@with_build123d
def test_a_base_with_pockets_for_stick_on_feet_still_lies_on_its_floor():
    from build123d import Vector

    board = enclosures.Board(interface())
    recess = {"kind": "recess", "inset": 8}
    plain, pocketed, footed = enclosures.box_base(board), enclosures.box_base(board, feet=recess), enclosures.box_base(board, feet={})
    places = enclosures.foot_places(board, enclosures.box_walls(board), feet=recess)
    assert pocketed.is_valid and len(pocketed.solids()) == 1
    assert plain.volume - pocketed.volume == pytest.approx(4 * math.pi * 4.2 ** 2 * 1.0, rel=1e-9)
    # it is as high as without feet and lies on the same face, less the four mouths; bosses lift it by 1.5 mm
    assert pocketed.bounding_box().min.Z == pytest.approx(-7.1) and footed.bounding_box().min.Z == pytest.approx(-8.6)
    on, flat = enclosures.standing(pocketed), enclosures.standing(plain)
    assert on["z"] == pytest.approx(-7.1) and on["stands"] and len(on["contacts"]) == 1
    assert flat["area_mm2"] - on["area_mm2"] == pytest.approx(4 * math.pi * 4.2 ** 2)
    assert enclosures.standing(footed)["area_mm2"] == pytest.approx(4 * math.pi * 16.0)
    for x, y, z in places["points"]:
        assert plain.is_inside(Vector(x, y, z)) and not pocketed.is_inside(Vector(x, y, z))
        assert pocketed.is_inside(Vector(x, y, z + 1.0))                # the millimetre of floor over the pocket
        assert pocketed.is_inside(Vector(x + 4.2 + 0.3, y, z))          # the floor beside it
    # in a prism, beside a staggered field in the floor
    vents = [{"wall": "floor", "shape": "round", "rows": 3, "columns": 4, "stagger": True}]
    without, both = enclosures.octagon_halves(board)[0], enclosures.octagon_halves(board, vents=vents, feet=recess)[0]
    assert both.is_valid and len(both.solids()) == 1
    assert without.volume - both.volume == pytest.approx(11 * math.pi * 1.5 ** 2 * 2.0 + 4 * math.pi * 4.2 ** 2, rel=1e-9)
    assert enclosures.standing(both)["z"] == pytest.approx(-7.1) and enclosures.standing(both)["stands"]


@with_build123d
def test_what_is_built_is_held_to_what_was_worked_out_and_refused_when_it_differs():
    board = enclosures.Board(interface())
    walls, base = enclosures.box_walls(board), enclosures.box_base(board)
    # a field laid out for a board without mounting holes, cut into a base that has standoffs: a slot meets one
    (field,) = enclosures.vent_fields(without_holes(), walls, "base", vents=[{"wall": "floor"}])
    with pytest.raises(ValueError, match="the vents of the base did not come out as worked out: 1 solid"):
        enclosures._with_vents(base, [field], "the base")
    places = enclosures.foot_places(board, walls, feet={})
    assert enclosures._with_feet(base, places).volume == pytest.approx(base.volume + places["volume_mm3"])
    # two feet that stand in each other add less than two
    with pytest.raises(ValueError, match="the feet did not come out as worked out"):
        enclosures._with_feet(base, dict(places, at=[(27.0, 17.0), (24.0, 17.0), (-27.0, -17.0), (27.0, -17.0)]))
    # feet of 1 mm under a base that stands on feet of 1.5 mm already
    lower = dict(places, height=1.0, at=[(15.0, 10.0), (-15.0, 10.0), (-15.0, -10.0), (15.0, -10.0)], volume_mm3=4 * math.pi * 16.0)
    with pytest.raises(ValueError, match="the base does not stand on its 4 feet alone: at z = -8.600 it rests on 4 face"):
        enclosures._with_feet(enclosures.box_base(board, feet={}), lower)
    # three feet on one side of the middle, the nearest 11 mm from it
    aside = dict(places, at=[(27.0, 17.0), (27.0, -17.0), (15.0, 0.0)], volume_mm3=3 * math.pi * 16.0 * 1.5)
    with pytest.raises(ValueError, match=r"the base would tip: its centre of mass, at \(0.58, -?0.00\), is 9.\d\d mm outside"):
        enclosures._with_feet(base, aside)
    # a pocket under a standoff breaks into the hole for its insert and takes less than a whole pocket
    pockets = enclosures.foot_places(board, walls, feet={"kind": "recess", "inset": 8})
    with pytest.raises(ValueError, match="the pockets did not come out as worked out"):
        enclosures._with_feet(base, dict(pockets, at=[(26.0, 16.0)] + pockets["at"][1:]))
    # pockets in a base that stands on bosses are not in what it lies on
    with pytest.raises(ValueError, match="the base does not lie on its floor around its 4 pockets: at z = -8.600"):
        enclosures._with_feet(enclosures.box_base(board, feet={}), pockets)
