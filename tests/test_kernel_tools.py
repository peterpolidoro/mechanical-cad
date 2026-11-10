"""The kernel-backed tools, run only where FreeCADCmd is on PATH (the CAD role):

    guix shell --pure -m manifest.scm -m .guix/manifest-cad.scm -- python3 -B -m pytest -q tests/test_kernel_tools.py
"""
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import REPO, edit_json

from mechanical_cad import layout

FREECAD = shutil.which("FreeCADCmd")
pytestmark = pytest.mark.skipif(FREECAD is None, reason="FreeCADCmd is not on PATH (use the CAD role)")
SPACER = "designs/parts/spacer"


def run(tool, *args):
    proc = subprocess.run([FREECAD, str(REPO / "tools" / tool), "--pass", *map(str, args)], capture_output=True, text=True)
    return proc.stdout + proc.stderr


def derived(part_dir):
    return {name: (Path(part_dir) / name).read_bytes() for name in ("part.step", "receipt.json", "facts.json")}


def test_building_an_unchanged_part_changes_no_file(project_copy):
    before = derived(project_copy / SPACER)
    out = run("build_part.py", project_copy / SPACER)
    assert "[build_part] exit status 0" in out, out
    assert derived(project_copy / SPACER) == before
    assert layout.load(project_copy).errors == []


def test_a_changed_parameter_rebuilds_and_fails_its_check(project_copy):
    edit_json(project_copy / SPACER / "parameters.json", lambda d: d.update(height_mm=6.0))
    assert any("parameters.json has changed" in e for e in layout.load(project_copy).errors)
    out = run("build_part.py", project_copy / SPACER)
    assert "FAILED: outer-size" in out and "[build_part] exit status 1" in out
    project = layout.load(project_copy)
    assert project.errors == []                                   # the receipt is current again
    assert project.components["spacer"].facts["bounding_box_mm"]["max"][2] == pytest.approx(6.0)


def test_a_program_that_fails_is_reported(project_copy):
    edit_json(project_copy / SPACER / "parameters.json", lambda d: d.update(inner_diameter_mm=30.0))
    out = run("build_part.py", project_copy / SPACER)
    assert "need 0 < inner diameter < outer diameter" in out and "[build_part] exit status 1" in out


def test_facts_are_kept_when_current_and_reproduced_when_forced(project_copy):
    plate = project_copy / "references/parts/base-plate/facts.json"
    before = plate.read_bytes()
    assert "0 measured, 2 already current" in run("step_facts.py", project_copy)
    assert "2 measured, 0 already current" in run("step_facts.py", project_copy, "--", "--force")
    assert plate.read_bytes() == before
    plate.unlink()
    out = run("step_facts.py", project_copy, "--", "--only", "base-plate")
    assert "1 measured" in out and plate.read_bytes() == before
    assert "no such imported part: nothing" in run("step_facts.py", project_copy, "--", "--only", "nothing")
