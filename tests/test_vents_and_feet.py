"""Vents through the walls of an enclosure and feet under its base (mechanical_cad/enclosures.py): where they go is
worked out without a kernel, and what build123d cuts and adds is held to that where it is installed
(make test-build123d)."""
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
