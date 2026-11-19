"""finishes.toml: the one hand-edited file of a project that says what a picture draws each part with, the
validator's rules for it, and the finishes.json that the flatten step writes beside the scene."""
import json

import pytest

from mechanical_cad import finishes, flatten, layout, stepfile

FILE = "finishes.toml"
HEAD = 'schema_version = 1\n[finishes.steel]\ncolor = "#7f8286"\n'


def errors(project_dir):
    return [e for e in layout.load(project_dir).errors if e.startswith(FILE)]


def has(messages, *words):
    return any(all(w in m for w in words) for m in messages)


def test_the_fixture_gives_every_part_a_finish(fixture_dir):
    project = layout.load(fixture_dir)
    assert project.errors == [] and not has(project.findings, FILE)
    data = project.finishes
    assert finishes.of(data, "base-plate") == ("aluminium", {"color": "#c8cacd", "metallic": 0.8, "roughness": 0.55, "opacity": 1.0})
    # the pin is given none of its own and takes the file's default; what a finish leaves out is said
    assert finishes.of(data, "pin") == ("grey-plastic", {"color": "#8a8d91", "metallic": 0.0, "roughness": 0.5, "opacity": 1.0})
    assert finishes.of(data, "spacer")[1]["opacity"] == 0.4
    assert finishes.of(None, "pin") == (None, None)


def test_a_colour_is_written_in_srgb_and_counted_as_light_adds_up():
    assert finishes.srgb("#ff8000") == (1.0, 128 / 255, 0.0)
    assert finishes.linear("#000000") == (0.0, 0.0, 0.0) and finishes.linear("#ffffff") == pytest.approx((1.0, 1.0, 1.0))
    assert finishes.linear("#808080") == pytest.approx((0.21586, 0.21586, 0.21586), abs=1e-5)      # mid grey is a fifth of white
    assert finishes.linear("#0a0a0a")[0] == pytest.approx(10 / 255 / 12.92)                       # the straight piece near black
    data = {"finishes": {"steel": {"color": "#7F8286", "metallic": 1}}}
    assert finishes.finish(data, "steel") == {"color": "#7f8286", "metallic": 1.0, "roughness": 0.5, "opacity": 1.0}


@pytest.mark.parametrize("text, words", [
    ("schema_version = 1\n[finishes.steel\n", ("not readable as TOML",)),
    (HEAD.replace("= 1", "= 2"), ("schema_version must be 1",)),
    (HEAD + 'colour = "#000000"\n', ("finishes.steel", "unknown field(s) colour")),
    ('units = "mm"\n' + HEAD, ("unknown field(s) units",)),
    (HEAD.replace("#7f8286", "grey"), ("finishes.steel", '"#rrggbb"')),
    (HEAD.replace('color = "#7f8286"\n', "metallic = 1.0\n"), ("finishes.steel", '"#rrggbb"')),
    (HEAD + "metallic = 1.5\n", ("metallic must be a number from 0 to 1",)),
    (HEAD + 'roughness = "rough"\n', ("roughness must be a number from 0 to 1",)),
    (HEAD + "opacity = 0\n", ("opacity must be a number above 0",)),
    (HEAD + 'note = ""\n', ("note must be a non-empty string",)),
    (HEAD.replace("finishes.steel", "finishes.Stainless_Steel"), ("lower-case letters and digits",)),
    ('schema_version = 1\ndefault = "brass"\n' + HEAD.split("\n", 1)[1], ("default", "'brass' is not a finish of this file")),
    (HEAD + '[parts]\npin = "brass"\n', ("parts.pin", "'brass' is not a finish of this file")),
    (HEAD + '[parts]\nwasher = "steel"\n', ("parts.washer", "the project has no part 'washer'")),
    (HEAD + '[parts]\npin-pair = "steel"\n', ("parts.pin-pair", "is an assembly; a finish is given to a part")),
    (HEAD + '[parts]\npin = 3\n', ("parts.pin", "3 is not a finish of this file")),
    ('schema_version = 1\nfinishes = ["steel"]\n', ("finishes must be a table",)),
    ('schema_version = 1\nparts = ["pin"]\n', ("parts must be a table",)),
])
def test_what_is_wrong_with_the_file_is_said(project_copy, text, words):
    (project_copy / FILE).write_text(text)
    found = errors(project_copy)
    assert has(found, *words), found
    project = layout.load(project_copy)
    assert project.finishes is None                                   # a file that is wrong gives no finishes
    with pytest.raises(flatten.FlattenError, match="does not validate"):
        flatten.flatten(project)


def test_parts_that_are_given_no_finish_are_pointed_out(project_copy):
    (project_copy / FILE).write_text(HEAD + '[parts]\npin = "steel"\n')
    project = layout.load(project_copy)
    assert project.errors == []
    assert has(project.findings, FILE, "2 of 3 part(s) have no finish", "no default: base-plate, spacer")
    assert finishes.of(project.finishes, "spacer") == (None, None)
    # with a default every part has one, and nothing is pointed out
    (project_copy / FILE).write_text('default = "steel"\n' + HEAD)
    assert not has(layout.load(project_copy).findings, FILE)


def test_a_project_without_the_file_is_what_it_was(project_copy, tmp_path):
    with_finishes = flatten.write(layout.load(project_copy), tmp_path / "with")
    (project_copy / FILE).unlink()
    project = layout.load(project_copy)
    assert project.errors == [] and project.finishes is None
    without = flatten.write(project, tmp_path / "without")
    assert without["finishes"] is None and not (tmp_path / "without" / "finishes.json").exists()
    # the finishes are no part of the scene: it is the same file with them and without them
    assert without["scene_sha256"] == with_finishes["scene_sha256"]
    assert sorted(p.name for p in (tmp_path / "without").iterdir()) == ["assets", "scene.json"]


def test_the_flatten_step_writes_the_finishes_beside_the_scene(project_copy, tmp_path):
    text = (project_copy / FILE).read_text()
    (project_copy / FILE).write_text(text + '\n[finishes.brass]\ncolor = "#B5A642"\nmetallic = 1.0\n')     # one no part has
    result = flatten.write(layout.load(project_copy), tmp_path / "flat")
    assert result["finishes"] == str(tmp_path / "flat" / "finishes.json")
    record = json.loads((tmp_path / "flat" / "finishes.json").read_text())
    assert record["schema_version"] == 1 and record["scene"] == "scene.json"
    assert record["source"] == {"kind": "mechanical-cad-finishes", "file": FILE,
                                "sha256": stepfile.sha256_file(project_copy / FILE)}
    # every part of the scene, the default applied; and only the finishes those parts have, every number said
    assert record["parts"] == {"base-plate": "aluminium", "pin": "grey-plastic", "spacer": "clear-blue"}
    assert sorted(record["finishes"]) == ["aluminium", "clear-blue", "grey-plastic"]
    assert record["finishes"]["clear-blue"] == {"color": "#2f6fd0", "metallic": 0.0, "roughness": 0.2, "opacity": 0.4}
    assert all(sorted(f) == ["color", "metallic", "opacity", "roughness"] for f in record["finishes"].values())
    # another root, another scene: the assembly without the spacer says nothing of the spacer or its finish
    flatten.write(layout.load(project_copy), tmp_path / "root", "fixture-root")
    record = json.loads((tmp_path / "root" / "finishes.json").read_text())
    assert record["parts"] == {"base-plate": "aluminium", "pin": "grey-plastic"} and "clear-blue" not in record["finishes"]


def test_a_part_without_a_finish_is_there_with_null(project_copy, tmp_path):
    (project_copy / FILE).write_text(HEAD + '[parts]\npin = "steel"\n')
    flatten.write(layout.load(project_copy), tmp_path / "flat")
    record = json.loads((tmp_path / "flat" / "finishes.json").read_text())
    assert record["parts"] == {"base-plate": None, "pin": "steel", "spacer": None} and list(record["finishes"]) == ["steel"]


def test_a_part_in_a_model_state_is_named_in_quotes(project_copy):
    """A key with @state is no bare key of TOML; the file says it in quotes, and the validator knows the part."""
    kinds = {"lid@open": "part", "lid": "part"}
    data = finishes.tomllib.loads(HEAD + '[parts]\n"lid@open" = "steel"\nlid = "steel"\n')
    assert finishes.problems(data, kinds) == []
    assert finishes.name_of(data, "lid@open") == "steel"
