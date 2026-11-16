import copy
import json

import pytest

from mechanical_cad import facts


@pytest.fixture
def spacer(fixture_dir):
    d = fixture_dir / "designs/parts/spacer"
    return json.loads((d / "facts.json").read_text()), json.loads((d / "checks.json").read_text())


def test_fixture_checks_pass(spacer):
    f, checks = spacer
    results = facts.evaluate(checks, f)
    assert [r["id"] for r in results] == ["one-solid", "outer-size", "sits-on-z0", "volume-of-a-ring"]
    assert all(r["passed"] for r in results)
    assert facts.extent(f) == pytest.approx([20.0, 20.0, 5.0], abs=1e-6)


def test_a_failing_check_says_what_it_saw(spacer):
    f, checks = spacer
    checks["checks"][3]["max"] = 1000.0
    checks["checks"][1]["equals"] = [20.0, 20.0, 6.0]
    results = {r["id"]: r for r in facts.evaluate(checks, f)}
    assert not results["volume-of-a-ring"]["passed"] and results["volume-of-a-ring"]["actual"] == pytest.approx(1137.8456, abs=1e-3)
    assert not results["outer-size"]["passed"]
    assert results["one-solid"]["passed"]


@pytest.mark.parametrize("change, message", [
    (lambda c: c.update(schema_version=2), "schema_version 1"),
    (lambda c: c["checks"].append(dict(c["checks"][0])), "appears twice"),
    (lambda c: c["checks"][0].update(fact="mass_kg"), "unknown fact"),
    (lambda c: c["checks"][0].pop("equals"), "needs equals, min or max"),
    (lambda c: c["checks"][0].update(about="x"), "unknown field"),
    (lambda c: c["checks"][1].update(equals=[20.0, 20.0]), "must be 3 numbers"),
    (lambda c: c["checks"][1].update(min=1.0), "applies to a single number"),
    (lambda c: c["checks"][0].update(tolerance=-1), "tolerance"),
])
def test_malformed_checks_are_errors_not_failures(spacer, change, message):
    f, checks = spacer
    change(checks)
    with pytest.raises(facts.FactsError, match=message):
        facts.evaluate(checks, f)


def test_same_geometry_within_tolerance(spacer):
    f, _ = spacer
    other = copy.deepcopy(f)
    other["volume_mm3"] *= 1 + 1e-9
    other["center_of_mass_mm"][2] += 1e-8
    assert facts.compare(f, other) == (True, [])
    other["volume_mm3"] *= 1.01
    other["solids"] = 2
    other["bounding_box_mm"]["max"][2] += 0.5
    same, diffs = facts.compare(f, other)
    assert not same and len(diffs) == 3


POINTS = [{"id": "wall", "point": [7.5, 0, 2.5], "is": "material"},
          {"id": "bore", "point": [0.0, 0.0, 2.5], "is": "empty"}]


def with_points(spacer, looked_at):
    f, checks = spacer
    checks["checks"] += copy.deepcopy(POINTS)
    f["points"] = looked_at
    return f, checks


def test_a_check_may_name_a_point_and_say_what_is_there(spacer):
    f, checks = with_points(spacer, [{"point": [7.5, 0.0, 2.5], "is": "material"}, {"point": [0.0, 0.0, 2.5], "is": "empty"}])
    assert facts.points(checks) == [[7.5, 0.0, 2.5], [0.0, 0.0, 2.5]]
    results = {r["id"]: r for r in facts.evaluate(checks, f)}
    assert results["wall"]["passed"] and results["bore"]["passed"] and len(results) == 6
    # what the kernel found there is what counts, and a point on the surface is neither
    f["points"][1]["is"] = "material"
    f["points"][0]["is"] = "surface"
    results = {r["id"]: r for r in facts.evaluate(checks, f)}
    assert not results["bore"]["passed"] and results["bore"]["actual"] == "material" and results["bore"]["expected"] == {"is": "empty"}
    assert not results["wall"]["passed"] and results["wall"]["actual"] == "surface"


def test_a_point_the_build_did_not_look_at_fails_until_the_part_is_built_again(spacer):
    f, checks = with_points(spacer, [{"point": [7.5, 0.0, 2.5], "is": "material"}])
    results = {r["id"]: r for r in facts.evaluate(checks, f)}
    assert results["wall"]["passed"]
    assert not results["bore"]["passed"] and "build the part again" in results["bore"]["actual"]
    del f["points"]
    assert not any(r["passed"] for r in facts.evaluate(checks, f) if "point" in r)


@pytest.mark.parametrize("change, message", [
    (lambda c: c.update({"is": "solid"}), "is must be"),
    (lambda c: c.pop("is"), "is must be"),
    (lambda c: c.update(point=[1.0, 2.0]), "point must be three numbers"),
    (lambda c: c.update(point=[1.0, 2.0, "3"]), "point must be three numbers"),
    (lambda c: c.update(fact="solids"), "unknown field"),
    (lambda c: c.update(tolerance=0.1), "unknown field"),
])
def test_a_malformed_point_check_is_an_error(spacer, change, message):
    f, checks = with_points(spacer, [])
    change(checks["checks"][-1])
    with pytest.raises(facts.FactsError, match=message):
        facts.evaluate(checks, f)
