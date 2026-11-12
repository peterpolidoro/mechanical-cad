"""Matching the solids of a whole-assembly file against a flattened scene; no kernel needed."""
import copy

import pytest
from conftest import FIXTURE

from mechanical_cad import flatten, layout, solids

# one solid per part, with volumes no two parts share: (volume in mm3, centre of mass in the part's frame)
PART_SOLIDS = {"base-plate": [(48000.0, [50.0, 30.0, 4.0])], "pin": [(2356.0, [0.0, 0.0, 15.0])],
               "spacer": [(1000.0, [0.0, 0.0, 2.5]), (10.0, [1.0, 2.0, 3.0])]}


@pytest.fixture(scope="module")
def scene():
    return flatten.flatten(layout.load(FIXTURE), "fixture-with-spacer")[0]


def found(expected):
    return [(e["volume_mm3"], list(e["center_of_mass_mm"])) for e in expected]


def test_every_solid_of_every_occurrence_is_expected_once(scene):
    expected = solids.expected(scene, PART_SOLIDS)
    assert len(expected) == 1 + 4 + 2                              # the plate, four pins, the spacer's two solids
    assert {e["occurrence"] for e in expected} == {o["id"] for o in scene["occurrences"]}
    spacer = next(o for o in scene["occurrences"] if o["part_id"] == "spacer")
    first = next(e for e in expected if e["part_id"] == "spacer")
    assert first["center_of_mass_mm"] == pytest.approx(solids.apply(spacer["transform_world"], [0.0, 0.0, 2.5]))


def test_the_file_the_scene_describes_matches(scene):
    expected = solids.expected(scene, PART_SOLIDS)
    report = solids.match(expected, list(reversed(found(expected))))
    assert report["same"] and report["solids_matched"] == 7 and report["worst_position_deviation_mm"] == 0.0
    assert report["unmatched"] == [] and report["found_but_not_expected"] == []


def test_a_part_in_the_wrong_place_says_how_far(scene):
    expected = solids.expected(scene, PART_SOLIDS)
    there = found(expected)
    plate = next(i for i, e in enumerate(expected) if e["part_id"] == "base-plate")
    there[plate][1][0] += 5.0
    report = solids.match(expected, there)
    assert not report["same"] and report["solids_matched"] == 6
    (miss,) = report["unmatched"]
    assert miss["part_id"] == "base-plate" and miss["nearest_solid_of_this_volume_mm"] == pytest.approx(5.0)
    assert len(report["found_but_not_expected"]) == 1


def test_a_missing_and_an_extra_solid_are_differences(scene):
    expected = solids.expected(scene, PART_SOLIDS)
    plate = next(i for i, e in enumerate(expected) if e["part_id"] == "base-plate")
    missing = solids.match(expected, [s for i, s in enumerate(found(expected)) if i != plate])
    assert not missing["same"] and missing["unmatched"][0]["nearest_solid_of_this_volume_mm"] is None
    extra = solids.match(expected, found(expected) + [(7.0, [0.0, 0.0, 0.0])])
    assert not extra["same"] and extra["unmatched"] == [] and extra["found_but_not_expected"][0]["volume_mm3"] == 7.0


def test_the_volume_may_move_a_little_and_no_more(scene):
    expected = solids.expected(scene, PART_SOLIDS)
    report = solids.match(expected, [(v * (1 + 5e-4), c) for v, c in found(expected)])
    assert report["same"] and report["worst_relative_volume_deviation"] == pytest.approx(5e-4)
    assert not solids.match(expected, [(v * 1.01, c) for v, c in found(expected)])["same"]


def test_an_occurrence_that_is_not_visible_is_not_expected(scene):
    hidden = copy.deepcopy(scene)
    next(o for o in hidden["occurrences"] if o["part_id"] == "base-plate")["visible_effective"] = False
    assert len(solids.placed(hidden)) == len(scene["occurrences"]) - 1
    assert "base-plate" not in {e["part_id"] for e in solids.expected(hidden, PART_SOLIDS)}


def test_z_up_turns_a_y_up_scene_and_leaves_a_z_up_scene(scene):
    basis = scene["coordinate_system"]["basis_to_z_up"]              # the fixture's frame is +Y up
    own, turned = solids.expected(scene, PART_SOLIDS), solids.expected(scene, PART_SOLIDS, frame="z-up")
    for a, b in zip(own, turned):
        assert b["center_of_mass_mm"] == pytest.approx(solids.apply(basis, a["center_of_mass_mm"]))
    assert not solids.match(own, found(turned))["same"]
    z_scene = copy.deepcopy(scene)
    del z_scene["coordinate_system"]["basis_to_z_up"]
    assert solids.expected(z_scene, PART_SOLIDS, frame="z-up") == solids.expected(z_scene, PART_SOLIDS)
    with pytest.raises(ValueError, match="unknown frame"):
        solids.expected(scene, PART_SOLIDS, frame="x-up")
