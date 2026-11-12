"""Listing the assemblies of a project and the state of their built files; no kernel needed."""
import pytest
from conftest import edit_json, relock

from mechanical_cad import assemblies, flatten, jsonio, layout, stepfile

PAIR = "pin-pair"


def fake_build(out_dir, key, project_dir, step=b"ISO-10303-21; stands for a built file\n"):
    """The three files tools/assembly_step.py leaves, as far as the listing reads them."""
    scene = flatten.flatten(layout.load(project_dir), key)[0]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{key}.step").write_bytes(step)
    (out_dir / f"{key}.FCStd").write_bytes(b"")
    jsonio.write(out_dir / f"{key}.json", {"scene_sha256": assemblies.scene_sha256(scene), "frame": "z-up",
                                           "step": {"sha256": stepfile.sha256_bytes(step)}, "check": {"same": True}})


def state(project_dir, key=PAIR, out_dir=None):
    rows = assemblies.listing(layout.load(project_dir), out_dir)
    return next(r for r in rows if r["key"] == key)["built"]


def test_every_assembly_is_listed_the_top_level_one_first(fixture_dir):
    rows = assemblies.listing(layout.load(fixture_dir))
    assert [r["key"] for r in rows] == ["fixture-with-spacer", "fixture-root", PAIR]
    assert [r["top_level"] for r in rows] == [True, False, False]
    assert [r["placed_by"] for r in rows] == [[], ["fixture-with-spacer"], ["fixture-root"]]
    assert [(r["parts"], r["occurrences"], r["sub_assembly_instances"]) for r in rows] == [(3, 6, 3), (2, 5, 2), (1, 2, 0)]
    assert [r["name"] for r in rows] == ["fixture-with-spacer", "FIXTURE ROOT.iam", "PIN PAIR.iam"]
    assert rows[1]["path"] == "references/assemblies/fixture-root"
    assert all(r["built"] == {"state": assemblies.NOT_BUILT} for r in rows)
    lines = assemblies.table(rows)
    assert lines[0].split()[:3] == ["KEY", "FILE", "PARTS"] and len(lines) == 4
    assert lines[1].endswith("nothing (top level)") and lines[3].endswith("fixture-root")
    assert assemblies.table([]) == []


def test_built_files_are_current_until_the_records_or_the_files_change(project_copy):
    built_in = assemblies.default_dir(project_copy)
    assert built_in == project_copy / ".cache" / "assemblies"
    fake_build(built_in, PAIR, project_copy)
    assert state(project_copy) == {"state": assemblies.CURRENT, "frame": "z-up", "step": str(built_in / f"{PAIR}.step"),
                                   "document": str(built_in / f"{PAIR}.FCStd")}
    assert state(project_copy, "fixture-root") == {"state": assemblies.NOT_BUILT}      # only the one that was built
    assert layout.load(project_copy).errors == []                                      # the validator does not look in .cache

    # a pin moves: the pair, and what holds the pair, were built from other records
    fake_build(built_in, "fixture-root", project_copy)
    edit_json(project_copy / "references/assemblies" / PAIR / "assembly.json",
              lambda d: d["children"][0]["transform"][0].__setitem__(3, -3.0))
    relock(project_copy)
    assert state(project_copy)["state"] == state(project_copy, "fixture-root")["state"] == assemblies.OUT_OF_DATE
    fake_build(built_in, PAIR, project_copy)
    assert state(project_copy)["state"] == assemblies.CURRENT

    (built_in / f"{PAIR}.step").write_bytes(b"another file")                           # not the file the report names
    assert state(project_copy)["state"] == assemblies.OUT_OF_DATE
    fake_build(built_in, PAIR, project_copy)
    (built_in / f"{PAIR}.json").write_text("not JSON")
    assert state(project_copy)["state"] == assemblies.OUT_OF_DATE
    (built_in / f"{PAIR}.FCStd").unlink()
    assert state(project_copy) == {"state": assemblies.NOT_BUILT}


def test_built_files_are_looked_for_where_they_were_put(project_copy, tmp_path):
    fake_build(tmp_path / "elsewhere", PAIR, project_copy)
    assert state(project_copy)["state"] == assemblies.NOT_BUILT
    assert state(project_copy, out_dir=tmp_path / "elsewhere")["state"] == assemblies.CURRENT


def test_a_project_that_does_not_validate_is_not_listed(project_copy):
    (project_copy / "references/parts/pin/part.step").write_text("broken")
    with pytest.raises(flatten.FlattenError, match="does not validate"):
        assemblies.listing(layout.load(project_copy))
