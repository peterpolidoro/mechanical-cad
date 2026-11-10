import copy

from mechanical_cad import compare, flatten, layout


def scenes(fixture_dir):
    scene, _, _ = flatten.flatten(layout.load(fixture_dir))
    return scene, copy.deepcopy(scene)


def test_a_scene_equals_itself(fixture_dir):
    old, new = scenes(fixture_dir)
    report = compare.compare(old, new)
    assert report["same"] and report["differences"] == []
    assert report["counts"]["old"] == {"parts": 3, "assemblies": 4, "occurrences": 6}


def test_renamed_parts_need_the_map(fixture_dir):
    old, new = scenes(fixture_dir)
    for p in old["parts"]:
        p["id"] = "OLD|" + p["id"]
    for o in old["occurrences"]:
        o["part_id"] = "OLD|" + o["part_id"]
    assert not compare.compare(old, new)["same"]
    assert compare.compare(old, new, {p["id"]: "OLD|" + p["id"] for p in new["parts"]})["same"]


def test_numerical_noise_is_not_a_difference_but_a_move_is(fixture_dir):
    old, new = scenes(fixture_dir)
    new["occurrences"][1]["transform"][0][3] += 1e-9
    new["occurrences"][1]["transform_world"][0][3] += 1e-9
    report = compare.compare(old, new)
    assert report["same"] and report["largest_deviation"]["translation"] > 0
    new["occurrences"][1]["transform_world"][0][3] += 0.01
    report = compare.compare(old, new)
    assert not report["same"] and "transform_world differs" in report["differences"][0]


def test_what_counts_as_a_difference(fixture_dir):
    old, new = scenes(fixture_dir)
    new["occurrences"][0]["grounded"] = False
    new["parts"][0]["asset"]["sha256"] = "0" * 64
    new["assemblies"][1]["document"] = "C:\\somewhere\\FIXTURE ROOT.iam"         # only the file name is compared
    del new["occurrences"][2]
    new["parts"][1]["properties"]["material"] = "Brass"
    diffs = compare.compare(old, new)["differences"]
    assert any("grounded was True, is False" in d for d in diffs)
    assert any("asset.sha256" in d for d in diffs)
    assert any("is only in the old scene" in d for d in diffs)
    assert any("properties" in d for d in diffs)
    assert not any("document" in d for d in diffs)


def test_fields_only_one_side_has(fixture_dir):
    old, new = scenes(fixture_dir)
    for a in old["assemblies"]:
        a.pop("flexible", None)
    report = compare.compare(old, new)
    assert report["same"] and report["fields_only_in_new"] == ["assembly.flexible"]
    report = compare.compare(new, old)
    assert not report["same"]
    assert compare.compare(new, old, dropped_fields=("flexible",))["same"]
