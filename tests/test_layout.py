"""The validator: the fixture is clean, and each rule of the layout is enforced."""
import shutil

import pytest
from conftest import add_invisible_point, edit_json, relock, write_json

from mechanical_cad import layout

PLATE = "references/parts/base-plate"
PIN = "references/parts/pin"
ROOT = "references/assemblies/fixture-root"
PAIR = "references/assemblies/pin-pair"
SPACER = "designs/parts/spacer"
TOP = "designs/assemblies/fixture-with-spacer"


def errors(project_dir):
    return layout.load(project_dir).errors


def has(messages, *words):
    return any(all(w in m for w in words) for m in messages)


def test_fixture_is_clean(fixture_dir):
    project = layout.load(fixture_dir)
    assert project.errors == []
    assert project.report()["counts"] == {"references_part": 2, "references_assembly": 2, "designs_part": 1, "designs_assembly": 1}
    # one finding: the pin's header is the kind an exporter leaves when it does not normalise
    assert len(project.findings) == 1 and "1 of 3 STEP headers are not normalised" in project.findings[0]
    assert project.lock == layout.derive_lock(project)


def test_not_a_project(tmp_path):
    assert has(errors(tmp_path), "neither references/ nor designs/")
    assert has(errors(tmp_path / "missing"), "not a directory")


def test_keys(project_copy):
    (project_copy / "references/parts/Bad_Name").mkdir()
    shutil.copytree(project_copy / SPACER, project_copy / "designs/parts/pin")        # a key used in both roots
    (project_copy / "references/parts/loose.txt").write_text("x")
    e = errors(project_copy)
    assert has(e, "references/parts/Bad_Name", "not a valid key")
    assert has(e, "designs/parts/pin", "already used by references/parts/pin")
    assert has(e, "references/parts/loose.txt", "expected a component directory")


@pytest.mark.parametrize("key, ok", [("base-plate", True), ("m5x20", True), ("plate@flat-pattern", True),
                                     ("Base", False), ("base--plate", False), ("-base", False), ("base_plate", False),
                                     ("base@", False), ("a" * 81, False)])
def test_key_pattern(key, ok):
    assert (bool(layout.KEY.match(key)) and len(key) <= layout.KEY_MAX) is ok


def test_files_of_a_component(project_copy):
    (project_copy / PLATE / "notes.txt").write_text("by hand")
    (project_copy / PIN / "source.json").unlink()
    (project_copy / SPACER / "sketch.FCStd").write_text("x")
    (project_copy / SPACER / "README.md").write_text("what the part is for")      # prose beside a program is expected
    (project_copy / TOP / "README.md").write_text("what the assembly is for")
    project = layout.load(project_copy)
    assert has(project.errors, PLATE, "unexpected file(s) notes.txt")
    assert has(project.errors, PIN, "source.json is missing")
    assert has(project.findings, SPACER, "outside the layout: sketch.FCStd")
    assert not has(project.findings + project.errors, "README.md")


def test_other_entries_under_a_root_are_reported_not_refused(project_copy):
    (project_copy / "references/enclosure").mkdir()
    project = layout.load(project_copy)
    assert project.errors == []
    assert has(project.findings, "references/enclosure", "not part of the layout")


def test_step_file_must_match_its_record(project_copy):
    step = project_copy / PLATE / "part.step"
    step.write_bytes(step.read_bytes().replace(b"FreeCAD Model", b"FreeCAD model"))
    e = errors(project_copy)
    assert has(e, PLATE + "/source.json", "step.sha256 does not match")
    assert not has(e, PLATE + "/source.json", "step.data_sha256")          # only the header changed
    assert has(e, PLATE + "/facts.json", "describe a different part.step")
    assert has(e, "vault-lock.json", "base-plate", "step_sha256")


def test_step_record_fields(project_copy):
    def change(d):
        d["step"]["length_unit"] = "in"
        d["step"]["header_normalised"] = False
        d["step"]["protocol"] = "AP242"
        del d["step"]["bytes"]
    edit_json(project_copy / PLATE / "source.json", change)
    e = errors(project_copy)
    assert has(e, "step.length_unit is 'in' but the file declares 'mm'")
    assert has(e, "step.header_normalised is false but the file's header says otherwise")
    assert has(e, "step.protocol is 'AP242' but the file's schema is 'AP214'")
    assert has(e, "step.bytes is missing")


def test_a_file_that_names_two_schemas_is_an_error(project_copy):
    step = project_copy / PLATE / "part.step"
    data = step.read_bytes()
    at = data.index(b"FILE_SCHEMA")
    start, end = data.index(b"'", at), data.index(b"'", data.index(b"'", at) + 1) + 1
    step.write_bytes(data[:start] + b"'PROCESS_PLANNING_SCHEMA'," + data[start:end] + data[end:])   # the data section stays
    assert has(errors(project_copy), PLATE, "FILE_SCHEMA names more than one schema: PROCESS_PLANNING_SCHEMA,")


def test_a_file_that_is_not_step(project_copy):
    (project_copy / PIN / "part.step").write_text("not a step file")
    assert has(errors(project_copy), PIN + "/part.step", "not readable as a STEP file")


def test_source_record(project_copy):
    def change(d):
        d["key"] = "something-else"
        d["kind"] = "assembly"
        del d["vault"]["revision"]
        d["vault"]["version_number"] = "1"
        d["vault"]["native_sha256"] = "abc"
        d["export"]["run"] = "no-such-run"
        d["properties"]["nested"] = {"a": 1}
        d["extra"] = True
    edit_json(project_copy / PIN / "source.json", change)
    e = errors(project_copy)
    for words in (("key must equal the directory name",), ("kind must be 'part'",), ("vault.revision is missing",),
                  ("vault.version_number must be an integer",), ("vault.native_sha256 is not a SHA-256",),
                  ("references/receipts/no-such-run/ does not exist",), ("properties must be an object of scalar values",),
                  ("unknown field(s) extra",)):
        assert has(e, PIN + "/source.json", *words), words


def test_unknown_vault_identity_is_a_finding(project_copy):
    edit_json(project_copy / PIN / "source.json", lambda d: d["vault"].update(master_id=None))
    edit_json(project_copy / PAIR / "assembly.json", lambda d: [c.update(master_id=None) for c in d["children"]])
    relock(project_copy)
    project = layout.load(project_copy)
    assert project.errors == []
    assert has(project.findings, PIN + "/source.json", "vault.master_id is unknown")


def test_model_state_and_key_suffix_go_together(project_copy):
    edit_json(project_copy / PIN / "source.json", lambda d: d.update(model_state="Flat Pattern"))
    assert has(errors(project_copy), "a key carries @state exactly when the model state is not the primary one")


def test_assembly_children(project_copy):
    def change(d):
        a, b, c = d["children"]
        a["component"] = "no-such-part"
        b["kind"] = "part"
        c["transform"][0][0] = 2.0
        d["children"].append(dict(b, name="PIN PAIR:1", kind="assembly"))
        d["children"].append(dict(b, name="A/B", kind="assembly"))
        del a["visible"]
        d["length_unit"] = "furlong"
    edit_json(project_copy / ROOT / "assembly.json", change)
    e = errors(project_copy)
    assert has(e, "child 'BASE PLATE:1'", "component 'no-such-part' does not exist")
    assert has(e, "child 'BASE PLATE:1'", "visible is missing")
    assert has(e, "child 'PIN PAIR:1'", "kind is 'part' but references/assemblies/pin-pair is a assembly")
    assert has(e, "child 'PIN PAIR:2'", "not orthonormal")
    assert has(e, "child 'PIN PAIR:1'", "used twice")
    assert has(e, "name must be a non-empty string without '/'")
    assert has(e, "length_unit must be one of")


def test_mirrored_is_refused_and_suppressed_is_reported(project_copy):
    def change(d):
        d["children"][0]["mirrored"] = True
        d["children"][1]["suppressed"] = True
    edit_json(project_copy / PAIR / "assembly.json", change)
    project = layout.load(project_copy)
    assert has(project.errors, "child 'PIN:1'", "mirrored occurrence is not supported")
    assert has(project.findings, "child 'PIN:2'", "suppressed")


def test_overrides(project_copy):
    def change(d):
        rigid, flexible = d["children"][1], d["children"][2]
        rigid["overrides"] = [dict(flexible["overrides"][0])]                     # not a flexible instance
        flexible["overrides"].append({"path": ["PIN:9"], "transform": flexible["overrides"][0]["transform"]})
        flexible["overrides"].append(dict(flexible["overrides"][0]))             # the same path twice
    edit_json(project_copy / ROOT / "assembly.json", change)
    e = errors(project_copy)
    assert has(e, "child 'PIN PAIR:1'", "only a flexible assembly instance may carry overrides")
    assert has(e, "child 'PIN PAIR:2'", "override path PIN:9 does not exist in pin-pair")
    assert has(e, "the path PIN:2 is overridden twice")


def test_child_identity_must_agree_with_the_component(project_copy):
    edit_json(project_copy / PAIR / "assembly.json", lambda d: d["children"][0].update(master_id="1", model_state="Other"))
    e = errors(project_copy)
    assert has(e, "master_id '1' is not that of references/parts/pin")
    assert has(e, "model_state 'Other' is not that of references/parts/pin")


def test_an_imported_assembly_cannot_place_an_authored_part(project_copy):
    def change(d):
        d["children"].append(dict(d["children"][0], name="SPACER:1", component="spacer", master_id=None))
    edit_json(project_copy / ROOT / "assembly.json", change)
    assert has(errors(project_copy), "an imported assembly cannot place designs/parts/spacer")


def test_an_assembly_cannot_contain_itself(project_copy):
    def change(d):
        d["children"].append(dict(d["children"][1], name="FIXTURE ROOT:1", component="fixture-root", master_id="900004"))
    edit_json(project_copy / PAIR / "assembly.json", change)
    assert has(errors(project_copy), "contains itself")


def test_authored_assembly_may_omit_flags(project_copy):
    project = layout.load(project_copy)
    top = project.components["fixture-with-spacer"]
    assert top.children[1].flags == {"visible": True, "suppressed": False, "grounded": False, "flexible": False, "mirrored": False}
    assert top.children[1].bom_structure == "Normal"


def test_the_lock_must_equal_the_directories(project_copy):
    edit_json(project_copy / "vault-lock.json", lambda d: d["components"][0].update(version_id="1"))
    assert has(errors(project_copy), "vault-lock.json", "base-plate", "version_id")
    edit_json(project_copy / "vault-lock.json", lambda d: d["components"].pop())
    assert has(errors(project_copy), "vault-lock.json", "is in references/ but not in the index")
    (project_copy / "vault-lock.json").unlink()
    project = layout.load(project_copy)
    assert project.errors == [] and has(project.findings, "vault-lock.json", "missing")


def test_an_old_lock_is_not_the_index(project_copy):
    write_json(project_copy / "vault-lock.json", {"schema_version": 1, "references": {}, "publications": []})
    assert has(errors(project_copy), "vault-lock.json", "schema_version must be 2")


def test_facts(project_copy):
    def change(d):
        d["valid"] = False
        d["solids"] = -1
        d["tool"].pop("kernel_version")
        d["length_unit_declared"] = "in"
        d["measured_at"] = "today"
    edit_json(project_copy / PLATE / "facts.json", change)
    (project_copy / PIN / "facts.json").unlink()
    project = layout.load(project_copy)
    for words in (("did not find the geometry valid",), ("solids must be a non-negative integer",),
                  ("tool must record name, version, kernel and kernel_version",),
                  ("length_unit_declared is 'in'",), ("unknown field(s) measured_at",)):
        assert has(project.errors, PLATE + "/facts.json", *words), words
    assert has(project.findings, PIN, "no facts.json")


def test_facts_say_how_many_invisible_items_were_left_out(project_copy):
    facts = project_copy / PLATE / "facts.json"
    edit_json(facts, lambda d: d.update(invisible_items=2))
    assert has(errors(project_copy), PLATE + "/facts.json", "invisible_items is 2 but part.step marks 0 item(s) invisible")
    edit_json(facts, lambda d: d.update(invisible_items=0))
    assert has(errors(project_copy), PLATE + "/facts.json", "absent when nothing was left out")
    edit_json(facts, lambda d: d.pop("invisible_items"))
    assert errors(project_copy) == []
    add_invisible_point(project_copy, PLATE)
    assert errors(project_copy) == []
    edit_json(facts, lambda d: d.pop("invisible_items"))        # as facts measured without the filter would be
    assert has(errors(project_copy), PLATE + "/facts.json", "invisible_items is 0 but part.step marks 1 item(s) invisible",
               "measure it again")
    step = project_copy / PLATE / "part.step"
    step.write_bytes(step.read_bytes().replace(b"INVISIBILITY((#9002))", b"INVISIBILITY((#15))"))
    assert has(errors(project_copy), PLATE + "/part.step", "marks something invisible in a way that is not understood")


def test_receipt_goes_stale_when_the_program_or_parameters_change(project_copy):
    edit_json(project_copy / SPACER / "parameters.json", lambda d: d.update(height_mm=6.0))
    with open(project_copy / SPACER / "build.py", "a") as f:
        f.write("\n# edited\n")
    e = errors(project_copy)
    assert has(e, SPACER + "/receipt.json", "parameters.json has changed since the part was built")
    assert has(e, SPACER + "/receipt.json", "build.py has changed since the part was built")


def test_a_checkout_that_wrote_crlf_is_named_as_the_cause(project_copy):
    """Git for Windows converts text it is not told to leave alone; the hashes then differ, and nothing was edited."""
    for name in (SPACER + "/build.py", SPACER + "/parameters.json", PLATE + "/part.step"):
        path = project_copy / name
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    e = errors(project_copy)
    assert e[0].startswith(".gitattributes: 3 file(s) differ from their records only in line endings")
    for name in (SPACER + "/build.py", SPACER + "/parameters.json", PLATE + "/part.step"):
        assert name in e[0]
    assert "build nothing and measure nothing again" in e[0]
    assert has(e, SPACER + "/receipt.json", "build.py has changed since the part was built")     # still said, below


def test_an_edit_is_not_taken_for_a_converted_checkout(project_copy):
    path = project_copy / SPACER / "build.py"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n") + b"# edited\r\n")
    e = errors(project_copy)
    assert has(e, SPACER + "/receipt.json", "build.py has changed since the part was built")
    assert not has(e, ".gitattributes")


def test_publication_record(project_copy):
    sha = layout.load(project_copy).components["spacer"].step_sha256
    record = {"schema_version": 1, "publications": [
        {"request_id": "r-1", "master_id": "910001", "version_id": "910002", "git_commit": "0" * 40, "step_sha256": sha}]}
    write_json(project_copy / SPACER / "vault.json", record)
    relock(project_copy)
    project = layout.load(project_copy)
    assert project.errors == []
    assert project.lock["publications"] == [{"key": "spacer", "path": SPACER, "request_id": "r-1", "master_id": "910001",
                                             "version_id": "910002", "step_sha256": sha, "git_commit": "0" * 40}]
    record["publications"][0]["step_sha256"] = "f" * 64
    write_json(project_copy / SPACER / "vault.json", record)
    relock(project_copy)
    project = layout.load(project_copy)
    assert has(project.findings, SPACER, "differs from the file last published to Vault")
    write_json(project_copy / SPACER / "vault.json", {"schema_version": 1, "publications": [{"request_id": ""}]})
    assert has(errors(project_copy), "vault.json publications[0]", "request_id must be a non-empty string")

