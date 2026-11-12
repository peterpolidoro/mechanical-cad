"""Flattening the manifests into the scene mechanical-docs reads."""
import json

import pytest
from conftest import add_invisible_point, edit_json

from mechanical_cad import flatten, layout
from mechanical_cad import transforms as T

TOP = "designs/assemblies/fixture-with-spacer"


def scene_of(project_dir, root=None):
    scene, assets, skipped = flatten.flatten(layout.load(project_dir), root)
    return scene, assets, skipped


def world(scene, occurrence_id):
    occ = next(o for o in scene["occurrences"] if o["id"] == occurrence_id)
    return T.translation(occ["transform_world"]), occ


def test_fixture_scene(fixture_dir):
    scene, assets, skipped = scene_of(fixture_dir)
    assert scene["schema_version"] == "draft-1" and scene["units"] == "mm"
    assert scene["id"] == "fixture-with-spacer"                       # the only assembly nothing else places
    assert [p["id"] for p in scene["parts"]] == ["base-plate", "pin", "spacer"]
    assert [a["id"] for a in scene["assemblies"]] == ["root", "FIXTURE ROOT:1", "FIXTURE ROOT:1/PIN PAIR:1", "FIXTURE ROOT:1/PIN PAIR:2"]
    assert [o["id"] for o in scene["occurrences"]] == [
        "FIXTURE ROOT:1/BASE PLATE:1", "FIXTURE ROOT:1/PIN PAIR:1/PIN:1", "FIXTURE ROOT:1/PIN PAIR:1/PIN:2",
        "FIXTURE ROOT:1/PIN PAIR:2/PIN:1", "FIXTURE ROOT:1/PIN PAIR:2/PIN:2", "SPACER:1"]
    assert skipped == [] and [k for k, _ in assets] == ["base-plate", "pin", "spacer"]
    for o in scene["occurrences"]:
        T.check_matrix(o["transform"])
        T.check_matrix(o["transform_world"])


def test_units_and_composition(fixture_dir):
    scene, _, _ = scene_of(fixture_dir)
    # pin-pair is written in centimetres: -2.5 cm is 25 mm; the pair sits at (0, 8, -15) with part Z on assembly Y
    t, occ = world(scene, "FIXTURE ROOT:1/PIN PAIR:1/PIN:1")
    assert T.translation(occ["transform"]) == [-25.0, 0.0, 0.0]
    assert t == pytest.approx([-25.0, 8.0, -15.0])
    assert occ["parent_id"] == "FIXTURE ROOT:1/PIN PAIR:1" and occ["part_id"] == "pin"
    assert occ["position_overridden_vs_definition"] is False and occ["parent_flexible"] is False
    assert occ["grounded"] is True and occ["model_state"] == "[Primary]"


def test_flexible_instance_takes_its_override(fixture_dir):
    scene, _, _ = scene_of(fixture_dir)
    moved, occ = world(scene, "FIXTURE ROOT:1/PIN PAIR:2/PIN:2")
    assert moved == pytest.approx([35.0, 8.0, 15.0])                  # the definition says 25
    assert occ["position_overridden_vs_definition"] is True and occ["parent_flexible"] is True
    kept, other = world(scene, "FIXTURE ROOT:1/PIN PAIR:2/PIN:1")
    assert kept == pytest.approx([-25.0, 8.0, 15.0])
    assert other["position_overridden_vs_definition"] is False and other["parent_flexible"] is True
    # the rigid instance of the same definition is untouched
    assert world(scene, "FIXTURE ROOT:1/PIN PAIR:1/PIN:2")[0] == pytest.approx([25.0, 8.0, -15.0])
    assert next(a for a in scene["assemblies"] if a["id"] == "FIXTURE ROOT:1/PIN PAIR:2")["flexible"] is True


def test_outer_override_wins_over_inner(project_copy):
    def change(d):
        d["children"][0]["flexible"] = True
        d["children"][0]["overrides"] = [
            {"path": ["PIN PAIR:2", "PIN:2"], "transform": [[1, 0, 0, 40.0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]},
            {"path": ["PIN PAIR:1"], "transform": [[1, 0, 0, 0], [0, 0, 1, 8.0], [0, -1, 0, -20.0], [0, 0, 0, 1]]}]
    edit_json(project_copy / TOP / "assembly.json", change)
    scene, _, _ = scene_of(project_copy)
    assert world(scene, "FIXTURE ROOT:1/PIN PAIR:2/PIN:2")[0] == pytest.approx([40.0, 8.0, 15.0])
    assert world(scene, "FIXTURE ROOT:1/PIN PAIR:1/PIN:1")[0] == pytest.approx([-25.0, 8.0, -20.0])
    pair = next(a for a in scene["assemblies"] if a["id"] == "FIXTURE ROOT:1/PIN PAIR:1")
    assert T.translation(pair["transform"]) == [0.0, 8.0, -20.0]


def test_named_root_and_frame(fixture_dir):
    scene, _, _ = scene_of(fixture_dir, "fixture-root")
    assert scene["id"] == "fixture-root-900104" and "900104" in scene["title"]
    assert [o["id"] for o in scene["occurrences"]][:2] == ["BASE PLATE:1", "PIN PAIR:1/PIN:1"]
    cs = scene["coordinate_system"]
    assert cs["up_axis"] == "+Y" and cs["basis_to_z_up"] == T.basis_to_z_up("+Y")
    assert scene["source"]["root_master_id"] == "900004" and scene["source"]["export_run"] == "synthetic-export-0001"
    assert all(not isinstance(v, (dict, list)) for v in scene["source"].values())     # the loader takes scalars only
    assert scene["assemblies"][0] == {"id": "root", "parent_id": None, "transform": T.identity(), "document": "FIXTURE ROOT.iam"}
    with pytest.raises(flatten.FlattenError, match="not an assembly of this project; its assemblies: fixture-root, fixture-with-spacer, pin-pair"):
        scene_of(fixture_dir, "pin")


def test_ambiguous_root_must_be_named(project_copy):
    edit_json(project_copy / TOP / "assembly.json", lambda d: d["children"].pop(0))     # fixture-root is now unplaced too
    with pytest.raises(flatten.FlattenError, match="name the root assembly: fixture-root, fixture-with-spacer"):
        scene_of(project_copy)


def test_part_records(fixture_dir):
    scene, _, _ = scene_of(fixture_dir)
    plate, pin, spacer = scene["parts"]
    assert plate["asset"] == {"path": "assets/base-plate.step", "format": "step", "units": "mm",
                              "sha256": layout.load(fixture_dir).components["base-plate"].step_sha256}
    assert plate["name"] == "BASE PLATE" and plate["identifying_dimensions_mm"]["extent"] == [100.0, 60.0, 8.0]
    assert plate["source"]["master_id"] == "900001" and plate["properties"]["part_number"] == "FX-001"
    assert spacer["name"] == "Spacer" and "source" not in spacer                 # authored: no Vault identity
    assert spacer["asset"]["units"] == "mm"


def test_suppressed_child_is_left_out(project_copy):
    edit_json(project_copy / "references/assemblies/pin-pair/assembly.json", lambda d: d["children"][1].update(suppressed=True))
    edit_json(project_copy / "references/assemblies/fixture-root/assembly.json", lambda d: d["children"][2].pop("overrides"))
    scene, _, skipped = scene_of(project_copy)
    assert skipped == ["FIXTURE ROOT:1/PIN PAIR:1/PIN:2", "FIXTURE ROOT:1/PIN PAIR:2/PIN:2"]
    assert len(scene["occurrences"]) == 4


def test_hidden_parent_hides_its_children(project_copy):
    edit_json(project_copy / "references/assemblies/fixture-root/assembly.json", lambda d: d["children"][1].update(visible=False))
    scene, _, _ = scene_of(project_copy)
    _, occ = world(scene, "FIXTURE ROOT:1/PIN PAIR:1/PIN:1")
    assert occ["visible"] is True and occ["visible_effective"] is False


def test_write(fixture_dir, tmp_path):
    out = tmp_path / "flat"
    result = flatten.write(layout.load(fixture_dir), out)
    assert result["parts"] == 3 and result["occurrences"] == 6
    scene = json.loads((out / "scene.json").read_text())
    for part in scene["parts"]:
        assert (out / part["asset"]["path"]).is_file()
    assert (out / "assets/pin.step").read_bytes() == (fixture_dir / "references/parts/pin/part.step").read_bytes()
    with pytest.raises(flatten.FlattenError, match="not empty"):
        flatten.write(layout.load(fixture_dir), out)


def test_an_asset_leaves_out_what_the_file_marks_invisible(project_copy, tmp_path):
    from mechanical_cad import stepfile
    assert flatten.write(layout.load(project_copy), tmp_path / "before")["invisible_items_left_out"] == {}
    add_invisible_point(project_copy)
    tracked = (project_copy / "references/parts/base-plate/part.step").read_bytes()
    result = flatten.write(layout.load(project_copy), tmp_path / "flat")
    assert result["invisible_items_left_out"] == {"base-plate": 1}
    asset = (tmp_path / "flat/assets/base-plate.step").read_bytes()
    assert asset == stepfile.visible_only(tracked) != tracked and stepfile.invisible_items(asset) == []
    scene = json.loads((tmp_path / "flat/scene.json").read_text())
    record = next(p for p in scene["parts"] if p["id"] == "base-plate")
    assert record["asset"]["sha256"] == stepfile.sha256_bytes(asset)        # the scene describes the file beside it
    assert (tmp_path / "flat/assets/pin.step").read_bytes() == (project_copy / "references/parts/pin/part.step").read_bytes()


def test_a_project_with_errors_is_not_flattened(project_copy):
    (project_copy / "references/parts/pin/part.step").write_text("broken")
    with pytest.raises(flatten.FlattenError, match="does not validate"):
        scene_of(project_copy)
