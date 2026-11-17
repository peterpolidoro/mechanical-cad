"""A file from outside as a part of designs/, the interface a part states, and the inputs a part is built against:
what the validator and the commands say of them without a kernel."""
import json

import pytest
from conftest import edit_json, write_json

from mechanical_cad import interfaces, layout, stepfile, supplied
from mechanical_cad.cli import main

PIN_STEP = "references/parts/pin/part.step"          # a STEP file with an author in its header, as one from outside has
BRACKET = "designs/parts/bracket"
SPACER = "designs/parts/spacer"
FROM_SUPPLIER = ["--supplier", "Acme", "--part-number", "A-100", "--retrieved", "2026-11-17", "--publishable", "yes"]


def add(project, *more, key="bracket", file=None):
    return main(["add-supplied", str(project), key, str(file or project / PIN_STEP), "--name", "Bracket", *more])


def errors(project_dir):
    return layout.load(project_dir).errors


def has(messages, *words):
    return any(all(w in m for w in words) for m in messages)


# ------------------------------------------------------------------ a supplied part

def test_a_file_from_a_supplier_becomes_a_part(project_copy, capsys):
    received = (project_copy / PIN_STEP).read_bytes()
    assert add(project_copy, *FROM_SUPPLIER, "--url", "https://example.org/a-100") == 0
    part = project_copy / BRACKET
    assert sorted(p.name for p in part.iterdir()) == ["origin.json", "part.step"]
    data = (part / "part.step").read_bytes()
    assert data != received and stepfile.is_normalised(data)                    # the header no longer names an author
    assert stepfile.data_sha256(data) == stepfile.data_sha256(received)         # and the geometry is what was received
    origin = json.loads((part / "origin.json").read_text())
    assert origin["name"] == "Bracket" and origin["step"]["received_sha256"] == stepfile.sha256_bytes(received)
    assert origin["origin"] == {"kind": "supplier", "supplier": "Acme", "part_number": "A-100",
                                "url": "https://example.org/a-100", "retrieved": "2026-11-17", "licence": None,
                                "publishable": True}
    project = layout.load(project_copy)
    assert project.errors == []
    assert project.report()["counts"]["designs_part"] == 2
    comp = project.components["bracket"]
    assert comp.supplied and comp.name == "Bracket" and comp.receipt is None
    assert has(project.findings, BRACKET, "no facts.json")
    assert not has(project.findings, "publish")
    assert "measure it next" in capsys.readouterr().out


def test_a_file_from_another_repository_names_its_commit(project_copy):
    args = ["--repository", "https://example.org/board.git", "--commit", "0123abc", "--path", "docs/board.step",
            "--retrieved", "2026-11-17", "--publishable", "unknown", "--licence", "CC-BY-SA-4.0"]
    assert add(project_copy, *args, key="board") == 0
    project = layout.load(project_copy)
    assert project.errors == []
    assert has(project.findings, "designs/parts/board", "not recorded as publishable")
    edit_json(project_copy / "designs/parts/board/origin.json", lambda d: d["origin"].update(commit="main"))
    assert has(errors(project_copy), "origin.commit must be a commit hash")


def test_the_same_file_again_changes_nothing_and_a_newer_one_replaces_it(project_copy, capsys):
    assert add(project_copy, *FROM_SUPPLIER) == 0
    before = {p.name: p.read_bytes() for p in (project_copy / BRACKET).iterdir()}
    assert add(project_copy, *FROM_SUPPLIER) == 1 and "give replace" in capsys.readouterr().out
    assert add(project_copy, *FROM_SUPPLIER, "--replace") == 0
    assert {p.name: p.read_bytes() for p in (project_copy / BRACKET).iterdir()} == before
    newer = project_copy / "references/parts/base-plate/part.step"
    assert add(project_copy, *FROM_SUPPLIER, "--replace", file=newer) == 0
    assert (project_copy / BRACKET / "part.step").read_bytes() != before["part.step"]
    assert layout.load(project_copy).errors == []


def test_what_is_refused(project_copy, tmp_path, capsys):
    def refused(*words, **kw):
        assert add(project_copy, *kw.pop("args", FROM_SUPPLIER), **kw) == 1
        out = capsys.readouterr().out
        assert all(w in out for w in words), out
    refused("not a key", key="Bad_Key")
    refused("is references/parts/pin already", key="pin")                       # a key another component has
    refused("is designs/parts/spacer already", "not a supplied part", key="spacer")
    (tmp_path / "notes.step").write_text("not a STEP file")
    refused("not a STEP file", file=tmp_path / "notes.step")
    refused("needs: part_number", args=["--supplier", "Acme", "--retrieved", "2026-11-17", "--publishable", "yes"])
    refused("needs: description", args=["--retrieved", "2026-11-17", "--publishable", "yes"])
    refused("YYYY-MM-DD", args=["--supplier", "Acme", "--part-number", "1", "--retrieved", "today", "--publishable", "no"])
    assert not (project_copy / BRACKET).exists()
    with pytest.raises(supplied.SuppliedError, match="not a project"):
        supplied.add(tmp_path, "bracket", project_copy / PIN_STEP, "Bracket", {})


def test_the_validator_holds_a_supplied_part_to_its_record(project_copy):
    assert add(project_copy, *FROM_SUPPLIER) == 0
    part = project_copy / BRACKET
    edit_json(part / "origin.json", lambda d: d["origin"].pop("publishable"))
    assert has(errors(project_copy), "origin.publishable must be true, false, or null")
    edit_json(part / "origin.json", lambda d: d["origin"].update(publishable=False, kind="shop"))
    assert has(errors(project_copy), "origin.kind must be one of")
    edit_json(part / "origin.json", lambda d: d["origin"].update(kind="supplier", owner="x"))
    assert has(errors(project_copy), "unknown field(s) owner")
    edit_json(part / "origin.json", lambda d: (d["origin"].pop("owner"), d["origin"].update(retrieved="17 Nov")))
    assert has(errors(project_copy), "origin.retrieved must be the day")
    edit_json(part / "origin.json", lambda d: d["origin"].update(retrieved="2026-11-17"))
    project = layout.load(project_copy)
    assert project.errors == [] and has(project.findings, BRACKET, "may not be published")
    # the file is what the record says, and nothing else is the part's source
    (part / "part.step").write_bytes((project_copy / "references/parts/base-plate/part.step").read_bytes())
    assert has(errors(project_copy), "origin.json", "step.sha256 does not match")
    assert add(project_copy, *FROM_SUPPLIER, "--replace") == 0
    (part / "build.py").write_text("def build(parameters):\n    return None\n")
    assert has(errors(project_copy), "origin.json and build.py", "a supplied part is not built")
    (part / "build.py").unlink()
    write_json(part / "receipt.json", {})
    assert has(errors(project_copy), "origin.json and receipt.json")


def test_a_part_that_is_built_still_needs_its_receipt(project_copy):
    (project_copy / SPACER / "receipt.json").unlink()
    assert has(errors(project_copy), SPACER, "receipt.json is missing")


# ------------------------------------------------------------------ an interface

BORE = {"id": "bore", "kind": "hole", "center": [0.0, 0.0, 5.0], "axis": [0.0, 0.0, 1.0], "diameter": 10.5, "through": True}


def interface(*features, **more):
    return {"schema_version": 1, "key": "spacer", "length_unit": "mm", "features": list(features), **more}


def test_a_well_formed_interface_has_no_problems():
    data = interface(
        BORE,
        {"id": "seat", "kind": "plane", "point": [0, 0, 0], "normal": [0, 0, -1], "note": "sits on the plate"},
        {"id": "rim", "kind": "outline", "point": [0, 0, 5], "normal": [0, 0, 1], "x": [1, 0, 0],
         "polygon": [[-10, -10], [10, -10], [10, 10], [-10, 10]], "corner_radius": 10.0},
        {"id": "j1", "kind": "port", "box": {"min": [-2, -2, 5], "max": [2, 2, 9]}, "direction": [0, 0, 1],
         "accepts": "a plug", "reference": "J1"},
        {"id": "above", "kind": "keep_out", "box": {"min": [-10, -10, 5], "max": [10, 10, 20]}},
        {"id": "datum.a", "kind": "point", "point": [10, 0, 0], "expect": [{"point": [9.0, 0, 2.5], "is": "material"}]},
        {"id": "centre-line", "kind": "axis", "point": [0, 0, 0], "direction": [0, 0, 1]},
        frames={"top": {"transform": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 5], [0, 0, 0, 1]], "note": "on the top face"}})
    assert interfaces.problems(data, "spacer") == []
    assert interfaces.feature(data, "j1")["reference"] == "J1"
    assert [f["id"] for f in interfaces.of_kind(data, "hole")] == ["bore"]
    assert interfaces.frame(data, "top")[2][3] == 5
    with pytest.raises(KeyError, match="there are: bore, seat"):
        interfaces.feature(data, "j2")
    # a hole is empty half-way down, or just inside the face when no depth is given; an expectation is one check more
    assert interfaces.checks(data)["checks"] == [
        {"id": "interface:bore", "point": [0.0, 0.0, 4.99], "is": "empty"},
        {"id": "interface:datum.a:1", "point": [9.0, 0, 2.5], "is": "material"}]
    deep = interfaces.checks(interface(dict(BORE, depth=5.0)))["checks"]
    assert deep == [{"id": "interface:bore", "point": [0.0, 0.0, 2.5], "is": "empty"}]


@pytest.mark.parametrize("change, said", [
    (lambda d: d.update(schema_version=2), "schema_version must be 1"),
    (lambda d: d.update(key="other"), "key must equal the directory name"),
    (lambda d: d.update(length_unit="in"), 'length_unit must be "mm"'),
    (lambda d: d.update(extra=1), "unknown field(s) extra"),
    (lambda d: d.update(features={}), "features must be a list"),
    (lambda d: d["features"].append(dict(BORE)), "the id is used twice"),
    (lambda d: d["features"][0].update(id="Bore"), "id must be lower-case"),
    (lambda d: d["features"][0].update(kind="slot"), "kind must be one of"),
    (lambda d: d["features"][0].pop("diameter"), "diameter is missing"),
    (lambda d: d["features"][0].update(axis=[0, 0, 2]), "axis must be a unit vector"),
    (lambda d: d["features"][0].update(diameter=-1), "diameter must be a positive number"),
    (lambda d: d["features"][0].update(through=False), "a hole that is not through needs its depth"),
    (lambda d: d["features"][0].update(box={"min": [0, 0, 0], "max": [1, 1, 1]}), "box is not a field of a hole"),
    (lambda d: d["features"][0].update(expect=[{"point": [0, 0, 0], "is": "surface"}]), "expect must list"),
    (lambda d: d.update(frames={"top": {"transform": [[2, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]}}), "not orthonormal"),
    (lambda d: d.update(frames={"Top": {"transform": layout.T.identity()}}), "a frame's name is lower-case"),
])
def test_a_malformed_interface_is_said_to_be(change, said):
    data = interface(dict(BORE))
    change(data)
    assert any(said in line for line in interfaces.problems(data, "spacer")), interfaces.problems(data, "spacer")


def test_the_validator_reads_an_interface_and_check_holds_it_to_the_solid(project_copy, capsys):
    part = project_copy / SPACER
    write_json(part / "interface.json", interface(BORE))
    project = layout.load(project_copy)
    assert project.errors == [] and project.components["spacer"].interface["features"][0]["id"] == "bore"
    # the facts in the fixture were written before the interface asked about a point: the check fails until a build
    assert main(["check", str(project_copy)]) == 1
    assert "interface:bore: the point [0.0, 0.0, 4.99] is not looked at; build the part again" in capsys.readouterr().out
    edit_json(part / "facts.json", lambda d: d.update(points=[{"point": [0.0, 0.0, 4.99], "is": "empty"}]))
    assert main(["check", str(project_copy)]) == 0
    assert "PASS    designs/parts/spacer: interface:bore" in capsys.readouterr().out
    edit_json(part / "facts.json", lambda d: d.update(points=[{"point": [0.0, 0.0, 4.99], "is": "material"}]))
    assert main(["check", str(project_copy)]) == 1
    edit_json(part / "interface.json", lambda d: d["features"][0].update(kind="slot"))
    assert has(errors(project_copy), "interface.json", "kind must be one of")
    assert layout.load(project_copy).components["spacer"].interface is None
    assert interfaces.points_asked(part) == []                  # a malformed interface asks nothing


def test_an_interface_is_not_for_a_mirrored_part(project_copy):
    write_json(project_copy / "references/parts/pin/interface.json", dict(interface(), key="pin"))
    assert has(errors(project_copy), "references/parts/pin", "unexpected file(s) interface.json")


# ------------------------------------------------------------------ inputs

def with_inputs(project, inputs):
    edit_json(project / SPACER / "parameters.json", lambda d: d.update(inputs=inputs))


def test_the_inputs_a_part_names_have_to_be_parts(project_copy):
    with_inputs(project_copy, {"shaft": "pin"})
    project = layout.load(project_copy)
    assert project.components["spacer"].inputs == {"shaft": "pin"}
    # the parameters changed, and the receipt does not record the input: both say build it again
    assert has(project.errors, "parameters.json has changed since the part was built")
    assert has(project.errors, "receipt.json", "the inputs recorded are not the inputs parameters.json declares")
    for inputs, said in (({"shaft": "nothing"}, "no component 'nothing'"),
                         ({"shaft": "fixture-root"}, "is an assembly; an input is a part"),
                         ({"shaft": "spacer"}, "is the part itself"),
                         ({"the shaft": "pin"}, "inputs must map names"),
                         (["pin"], "inputs must map names")):
        with_inputs(project_copy, inputs)
        assert has(errors(project_copy), "parameters.json", said), said


def test_a_changed_input_makes_the_part_stale(project_copy):
    pin = layout.load(project_copy).components["pin"]
    with_inputs(project_copy, {"shaft": "pin"})
    receipt = project_copy / SPACER / "receipt.json"

    def record(step_sha256, interface_sha256=None, **more):
        edit_json(receipt, lambda d: d.update(
            inputs=[{"name": "shaft", "key": "pin", "step_sha256": step_sha256, "interface_sha256": interface_sha256, **more}],
            parameters=dict(d["parameters"], sha256=stepfile.sha256_file(project_copy / SPACER / "parameters.json"))))

    record(pin.step_sha256)
    assert errors(project_copy) == []
    record("0" * 64)
    assert has(errors(project_copy), "input 'shaft' (pin) has changed since the part was built; build it again")
    record(pin.step_sha256, "0" * 64)
    assert has(errors(project_copy), "the interface of input 'shaft' (pin) has changed")
    record(pin.step_sha256, extra=1)
    assert has(errors(project_copy), "inputs must list each input")


def test_inputs_in_a_circle_are_refused_and_the_rest_is_ordered(project_copy, capsys):
    for key, needs in (("ring-a", {"other": "ring-b"}), ("ring-b", {"other": "spacer"})):
        part = project_copy / "designs/parts" / key
        part.mkdir()
        write_json(part / "parameters.json", {"inputs": needs})
        (part / "build.py").write_text("def build(parameters, inputs):\n    return None\n")
    project = layout.load(project_copy)
    assert layout.build_order(project) == ["spacer", "ring-b", "ring-a"]
    assert layout.build_order(project, ["ring-b"]) == ["spacer", "ring-b"]
    assert main(["build-order", str(project_copy), "ring-a"]) == 0
    assert capsys.readouterr().out.split() == ["spacer", "ring-b", "ring-a"]
    assert main(["build-order", str(project_copy), "pin"]) == 1 and "not an authored part" in capsys.readouterr().out
    with_inputs(project_copy, {"other": "ring-a"})
    project = layout.load(project_copy)
    assert has(project.errors, "designs/parts/ring-a/parameters.json", "go in a circle: ring-a -> ring-b -> spacer -> ring-a")
    with pytest.raises(ValueError, match="go in a circle"):
        layout.build_order(project)
    assert main(["build-order", str(project_copy)]) == 1


def test_a_supplied_part_is_in_the_order_and_is_not_built(project_copy, capsys):
    assert add(project_copy, *FROM_SUPPLIER) == 0
    with_inputs(project_copy, {"bracket": "bracket"})
    capsys.readouterr()
    assert layout.build_order(layout.load(project_copy)) == ["bracket", "spacer"]
    assert main(["build-order", str(project_copy)]) == 0
    assert capsys.readouterr().out.split() == ["spacer"]
