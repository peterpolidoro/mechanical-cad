import json

from conftest import edit_json

from mechanical_cad.cli import main


def test_validate(fixture_dir, project_copy, tmp_path, capsys):
    assert main(["validate", str(fixture_dir), "--json", str(tmp_path / "report.json")]) == 0
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["ok"] and report["counts"]["references_part"] == 2
    assert "0 error(s), 1 finding(s)" in capsys.readouterr().out
    (project_copy / "references/parts/pin/facts.json").unlink()
    (project_copy / "references/parts/pin/source.json").unlink()
    assert main(["validate", str(project_copy)]) == 1
    assert "ERROR   references/parts/pin: source.json is missing" in capsys.readouterr().out


def test_flatten_then_compare(fixture_dir, tmp_path, capsys):
    a, b = tmp_path / "a", tmp_path / "b"
    assert main(["flatten", str(fixture_dir), "--out", str(a)]) == 0
    assert main(["flatten", str(fixture_dir), "--out", str(b)]) == 0
    assert main(["flatten", str(fixture_dir), "--out", str(b)]) == 1            # not a fresh directory
    assert (a / "scene.json").read_bytes() == (b / "scene.json").read_bytes()   # the same project flattens to the same bytes
    capsys.readouterr()
    assert main(["compare-scenes", str(a / "scene.json"), str(b / "scene.json")]) == 0
    edit_json(b / "scene.json", lambda d: d["occurrences"][0]["transform_world"][0].__setitem__(3, 1.0))
    assert main(["compare-scenes", str(a / "scene.json"), str(b / "scene.json"), "--json", str(tmp_path / "cmp.json")]) == 1
    assert "DIFF occurrence" in capsys.readouterr().out
    assert json.loads((tmp_path / "cmp.json").read_text())["same"] is False


def test_flatten_refuses_a_broken_project(project_copy, tmp_path):
    (project_copy / "references/parts/pin/part.step").write_text("broken")
    assert main(["flatten", str(project_copy), "--out", str(tmp_path / "out")]) == 1
    assert not (tmp_path / "out").exists()


def test_assemblies_lists_what_can_be_built(fixture_dir, project_copy, tmp_path, capsys):
    assert main(["assemblies", str(fixture_dir), "--json", str(tmp_path / "list.json")]) == 0
    out = capsys.readouterr().out
    assert "fixture-root         FIXTURE ROOT.iam" in out and "3 assemblies, 0 built and current." in out
    assert f"Built files: {fixture_dir}/.cache/assemblies/KEY.step and KEY.FCStd" in out
    listed = json.loads((tmp_path / "list.json").read_text())
    assert [a["key"] for a in listed["assemblies"]] == ["fixture-with-spacer", "fixture-root", "pin-pair"]
    assert listed["built_in"] == f"{fixture_dir}/.cache/assemblies"
    assert main(["assemblies", str(fixture_dir), "--dir", str(tmp_path / "built")]) == 0
    assert f"Built files: {tmp_path}/built/KEY.step" in capsys.readouterr().out
    (project_copy / "references/parts/pin/part.step").write_text("broken")
    assert main(["assemblies", str(project_copy)]) == 1
    out = capsys.readouterr().out
    assert "ERROR   references/parts/pin" in out and "does not validate" in out and "KEY" not in out


def test_check(fixture_dir, project_copy, capsys):
    assert main(["check", str(fixture_dir)]) == 0
    assert "1 authored part(s), 4 check(s), 0 failure(s)" in capsys.readouterr().out
    edit_json(project_copy / "designs/parts/spacer/checks.json", lambda d: d["checks"][0].update(equals=2))
    assert main(["check", str(project_copy)]) == 1
    assert "FAIL    designs/parts/spacer: one-solid: solids is 1" in capsys.readouterr().out
    (project_copy / "designs/parts/spacer/facts.json").unlink()
    assert main(["check", str(project_copy)]) == 1


def test_lock_prints_the_index(fixture_dir, capsys):
    assert main(["lock", str(fixture_dir)]) == 0
    assert json.loads(capsys.readouterr().out) == json.loads((fixture_dir / "vault-lock.json").read_text())


def test_step_info_and_normalise(fixture_dir, tmp_path, capsys):
    pin = fixture_dir / "references/parts/pin/part.step"
    assert main(["step-info", str(pin)]) == 0
    info = json.loads(capsys.readouterr().out)
    assert info["length_unit"] == "mm" and info["header"]["author"] == ["fixture-author"]
    out = tmp_path / "pin.step"
    assert main(["normalise-header", str(pin), str(out)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["changed"] and result["data_sha256"] == info["data_sha256"] and result["received_sha256"] == info["sha256"]
    assert main(["normalise-header", str(pin), str(out)]) == 1                  # never overwrites


def test_visible_only(fixture_dir, project_copy, tmp_path, capsys):
    from conftest import add_invisible_point
    add_invisible_point(project_copy)
    step = project_copy / "references/parts/base-plate/part.step"
    assert main(["visible-only", str(step), str(tmp_path / "out.step")]) == 0
    assert json.loads(capsys.readouterr().out) | {"sha256": ""} == {"invisible_items_left_out": 1, "sha256": "", "changed": True}
    assert b"INVISIBILITY" not in (tmp_path / "out.step").read_bytes()
    assert main(["visible-only", str(step), str(tmp_path / "out.step")]) == 1          # never overwrites
    plain = fixture_dir / "references/parts/pin/part.step"
    assert main(["visible-only", str(plain), str(tmp_path / "pin.step")]) == 0
    assert (tmp_path / "pin.step").read_bytes() == plain.read_bytes()
