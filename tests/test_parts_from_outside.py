"""A supplied part measured, and a part built against another, by the kernel-backed tools (the CAD role with the
OCP bindings):

    guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm -- python3 -B -m pytest -q tests/test_parts_from_outside.py
"""
import importlib.util
import json
import shutil
import subprocess

import pytest
from conftest import REPO, edit_json, write_json

from mechanical_cad import layout
from mechanical_cad.cli import main

FREECAD = shutil.which("FreeCADCmd")
pytestmark = [pytest.mark.skipif(FREECAD is None, reason="FreeCADCmd is not on PATH (use the CAD role)"),
              pytest.mark.skipif(importlib.util.find_spec("OCP") is None,
                                 reason="the OCP bindings are not in this environment (make test-build123d)")]
with_build123d = pytest.mark.skipif(importlib.util.find_spec("build123d") is None,
                                    reason="build123d is not in this environment (make test-build123d)")
PIN_STEP = "references/parts/pin/part.step"           # a pin of 10 mm diameter, 30 mm long, standing on z = 0
PLATE_STEP = "references/parts/base-plate/part.step"  # a plate of 100 x 60 x 8 mm
SHAFT, SLEEVE = "designs/parts/shaft", "designs/parts/sleeve"
PIN_VOLUME = 2356.194490192345

SLEEVE_WITH_FREECAD = '''"""A block around whatever its input is, with the input cut out of it."""


def build(parameters, inputs):
    import FreeCAD as App
    import Part

    shaft = inputs["shaft"]
    low, high = shaft.facts["bounding_box_mm"]["min"], shaft.facts["bounding_box_mm"]["max"]
    wall = parameters["wall_mm"]
    block = Part.makeBox(high[0] - low[0] + 2 * wall, high[1] - low[1] + 2 * wall, high[2] - low[2],
                         App.Vector(low[0] - wall, low[1] - wall, low[2]))
    return block.cut(shaft.shape())
'''

SLEEVE_WITH_BUILD123D = '''"""The same block, written with build123d."""


def build(parameters, inputs):
    from build123d import Align, Box, Pos

    shaft = inputs["shaft"].build123d()
    box, wall = shaft.bounding_box(), parameters["wall_mm"]
    block = Pos(box.min.X - wall, box.min.Y - wall, box.min.Z) * Box(
        box.size.X + 2 * wall, box.size.Y + 2 * wall, box.size.Z, align=Align.MIN)
    return block - shaft
'''


def run(tool, *args):
    proc = subprocess.run([FREECAD, str(REPO / "tools" / tool), "--pass", *map(str, args)], capture_output=True, text=True)
    return proc.stdout + proc.stderr


def supply(project, file=PIN_STEP, *more):
    assert main(["add-supplied", str(project), "shaft", str(project / file), "--name", "Shaft", "--supplier", "Acme",
                 "--part-number", "S-10", "--retrieved", "2026-11-17", "--publishable", "yes", *more]) == 0
    out = run("step_facts.py", project, "--", "--only", "shaft")
    assert "[step_facts] exit status 0" in out, out
    return out


def sleeve(project, program=SLEEVE_WITH_FREECAD, **parameters):
    part = project / SLEEVE
    part.mkdir(exist_ok=True)
    (part / "build.py").write_text(program, encoding="utf-8")
    write_json(part / "parameters.json", {"name": "Sleeve", "inputs": {"shaft": "shaft"}, "wall_mm": 2.0, **parameters})
    return part


def facts_of(part):
    return json.loads((part / "facts.json").read_text())


def test_a_supplied_part_is_measured_like_a_mirrored_one(project_copy):
    out = supply(project_copy)
    assert "shaft: valid=True solids=1" in out and "1 part(s): 1 measured" in out
    project = layout.load(project_copy)
    assert project.errors == [] and not any("designs/parts/shaft" in f for f in project.findings)
    assert project.components["shaft"].facts["volume_mm3"] == pytest.approx(PIN_VOLUME, rel=1e-6)
    assert "1 already current" in run("step_facts.py", project_copy, "--", "--only", "shaft")
    # every part nothing here builds is measured by the one command: the two mirrored ones and the supplied one
    assert "3 part(s)" in run("step_facts.py", project_copy)
    assert "a supplied part is not built" in run("build_part.py", project_copy / SHAFT)


def test_a_part_is_built_against_another_and_goes_stale_with_it(project_copy):
    supply(project_copy)
    part = sleeve(project_copy)
    out = run("build_part.py", part)
    assert "[build_part] exit status 0" in out and "re-import ok" in out, out
    assert facts_of(part)["volume_mm3"] == pytest.approx(14 * 14 * 30 - PIN_VOLUME, rel=1e-6)
    project = layout.load(project_copy)
    assert project.errors == []
    shaft = project.components["shaft"]
    assert project.components["sleeve"].receipt["inputs"] == [
        {"name": "shaft", "key": "shaft", "step_sha256": shaft.step_sha256, "interface_sha256": None}]
    before = {n: (part / n).read_bytes() for n in ("part.step", "receipt.json", "facts.json")}
    assert "[build_part] exit status 0" in run("build_part.py", part)
    assert {n: (part / n).read_bytes() for n in before} == before          # built again, nothing changes

    # a newer file of the shaft: the sleeve is stale, and it is not built against a shaft that is not measured
    assert main(["add-supplied", str(project_copy), "shaft", str(project_copy / PLATE_STEP), "--name", "Shaft",
                 "--supplier", "Acme", "--part-number", "S-10", "--retrieved", "2026-11-18", "--publishable", "yes",
                 "--replace"]) == 0
    errors = layout.load(project_copy).errors
    assert any("input 'shaft' (shaft) has changed since the part was built; build it again" in e for e in errors)
    out = run("build_part.py", part)
    assert "input 'shaft' (designs/parts/shaft) does not validate; build or measure it first" in out
    assert "[build_part] exit status 1" in out
    assert "[step_facts] exit status 0" in run("step_facts.py", project_copy, "--", "--only", "shaft")
    assert "[build_part] exit status 0" in run("build_part.py", part)
    assert layout.load(project_copy).errors == []
    assert facts_of(part)["volume_mm3"] == pytest.approx(104 * 64 * 8 - 100 * 60 * 8, rel=1e-6)


@with_build123d
def test_a_program_written_with_build123d_gets_its_input_as_a_build123d_shape(project_copy):
    supply(project_copy)
    part = sleeve(project_copy, SLEEVE_WITH_BUILD123D)
    out = run("build_part.py", part)
    assert "[build_part] exit status 0" in out, out
    assert facts_of(part)["volume_mm3"] == pytest.approx(14 * 14 * 30 - PIN_VOLUME, rel=1e-6)
    receipt = json.loads((part / "receipt.json").read_text())
    assert receipt["tool"]["library"]["name"] == "build123d" and receipt["inputs"][0]["key"] == "shaft"
    assert layout.load(project_copy).errors == []


def test_an_interface_is_held_to_the_solid_and_handed_to_what_is_built_against_it(project_copy):
    supply(project_copy)
    tip = {"id": "tip", "kind": "point", "point": [0.0, 0.0, 30.0],
           "expect": [{"point": [0.0, 0.0, 29.0], "is": "material"}, {"point": [0.0, 0.0, 31.0], "is": "empty"}]}
    write_json(project_copy / SHAFT / "interface.json",
               {"schema_version": 1, "key": "shaft", "length_unit": "mm", "features": [tip]})
    # the supplied part is measured again because its interface now asks about two points
    assert "1 measured" in run("step_facts.py", project_copy, "--", "--only", "shaft")
    assert facts_of(project_copy / SHAFT)["points"] == [{"point": [0.0, 0.0, 29.0], "is": "material"},
                                                         {"point": [0.0, 0.0, 31.0], "is": "empty"}]
    assert main(["check", str(project_copy)]) == 0

    # the sleeve reads the shaft's interface, and states its own: the bore the shaft goes through
    program = SLEEVE_WITH_FREECAD.replace('    wall = parameters["wall_mm"]\n',
                                          '    wall = parameters["wall_mm"]\n'
                                          '    assert shaft.interface["features"][0]["id"] == "tip", shaft.interface\n'
                                          '    assert shaft.key == "shaft" and shaft.name == "Shaft"\n')
    part = sleeve(project_copy, program)
    bore = {"id": "bore", "kind": "hole", "center": [0.0, 0.0, 30.0], "axis": [0.0, 0.0, 1.0], "diameter": 10.0, "through": True}
    write_json(part / "interface.json", {"schema_version": 1, "key": "sleeve", "length_unit": "mm", "features": [bore]})
    out = run("build_part.py", part)
    assert "1 check(s)" in out and "FAILED" not in out and "[build_part] exit status 0" in out, out
    project = layout.load(project_copy)
    assert project.errors == [] and project.components["sleeve"].receipt["inputs"][0]["interface_sha256"]
    assert main(["check", str(project_copy)]) == 0

    # a bore stated where the wall is: the build says so
    edit_json(part / "interface.json", lambda d: d["features"][0].update(center=[6.0, 0.0, 30.0]))
    out = run("build_part.py", part)
    assert "FAILED: interface:bore" in out and "[build_part] exit status 1" in out, out
    edit_json(part / "interface.json", lambda d: d["features"][0].update(center=[0.0, 0.0, 30.0]))
    assert "[build_part] exit status 0" in run("build_part.py", part)

    # the shaft's interface changes: the sleeve was built against the old one
    edit_json(project_copy / SHAFT / "interface.json", lambda d: d["features"][0].update(note="the free end"))
    assert any("the interface of input 'shaft' (shaft) has changed" in e for e in layout.load(project_copy).errors)


def test_what_the_build_refuses_of_inputs(project_copy):
    supply(project_copy)
    part = sleeve(project_copy, "def build(parameters):\n    return None\n")
    assert "parameters.json names inputs and build() does not take them" in run("build_part.py", part)
    part = sleeve(project_copy, inputs={"shaft": "nothing"})
    assert "input 'shaft': 'nothing' is not another part of the project" in run("build_part.py", part)
    part = sleeve(project_copy, inputs={"shaft": "fixture-root"})
    assert "is not another part of the project" in run("build_part.py", part)
    # a program that takes inputs and is given none builds as before
    part = sleeve(project_copy, "def build(parameters, inputs):\n    import Part\n    assert inputs == {}\n"
                                "    return Part.makeBox(1, 2, 3)\n", inputs={})
    assert "[build_part] exit status 0" in run("build_part.py", part)
    assert "inputs" not in json.loads((part / "receipt.json").read_text())
