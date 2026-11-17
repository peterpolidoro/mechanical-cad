"""bd_warehouse as the channel module packages it: a screw from its tables, and the holes build123d cuts for it
and for a heat-set insert. Run where it is installed (.guix/manifest-build123d.scm):

    guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm -- python3 -B -m pytest -q tests/test_bd_warehouse.py
"""
from math import pi

import pytest

pytest.importorskip("bd_warehouse.fastener", reason="bd_warehouse is not in this environment (make test-build123d)")

from bd_warehouse.fastener import ClearanceHole, HeatSetNut, InsertHole, SocketHeadCapScrew
from build123d import Axis, Box, BuildPart, Locations


def one_valid_solid(shape):
    return len(shape.solids()) == 1 and shape.is_valid


def drilled(thickness, hole):
    """A plate 20 mm square (400 mm2) of that thickness, with what `hole()` makes at the middle of its top face."""
    with BuildPart() as plate:
        Box(20, 20, thickness)
        with Locations(plate.faces().sort_by(Axis.Z)[-1]):
            hole()
    return plate.part


def test_a_socket_head_cap_screw_is_one_valid_solid():
    screw = SocketHeadCapScrew("M3-0.5", 10)                      # ISO 4762, without the modelled thread
    assert one_valid_solid(screw) and screw.volume > 0
    assert screw.bounding_box().min.Z == pytest.approx(-10)       # the length is measured from under the head


def test_a_clearance_hole_for_the_screw_is_cut_through_a_plate():
    screw = SocketHeadCapScrew("M3-0.5", 10)
    plate = drilled(5, lambda: ClearanceHole(screw, counter_sunk=False))
    assert one_valid_solid(plate)
    assert 400 * 5 - plate.volume == pytest.approx(pi * 1.7 ** 2 * 5)    # 3.4 mm across, the normal fit of M3
    sunk = drilled(5, lambda: ClearanceHole(screw))                      # by default with room for the head
    assert one_valid_solid(sunk) and sunk.volume < plate.volume


def test_a_hole_for_a_heat_set_insert_is_cut_into_a_block():
    insert = HeatSetNut("M3-0.5-Standard")                        # of the McMaster-Carr table, the default
    assert one_valid_solid(insert)
    block = drilled(10, lambda: InsertHole(insert, depth=8))
    assert one_valid_solid(block)
    # more than the insert's own metal goes, less than a bore as wide as its knurls: the plastic has to grip them
    assert insert.volume < 400 * 10 - block.volume < pi * (insert.nut_diameter / 2) ** 2 * 8
