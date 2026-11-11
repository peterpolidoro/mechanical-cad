"""The kernel-backed tools, run only where FreeCADCmd is on PATH (the CAD role):

    guix shell --pure -m manifest.scm -m .guix/manifest-cad.scm -- python3 -B -m pytest -q tests/test_kernel_tools.py
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import REPO, edit_json, invisible, replace_step, write_json

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


TWO_SOLIDS = """
import sys
import FreeCAD as App
import Part
small = Part.makeBox(2, 2, 2)
small.translate(App.Vector(20, 0, 0))
Part.makeCompound([Part.makeBox(10, 10, 10), small]).exportStep(sys.argv[-1])
"""


def test_a_body_the_file_marks_invisible_is_not_measured(project_copy, tmp_path):
    plate = "references/parts/base-plate"
    (tmp_path / "two.py").write_text(TWO_SOLIDS)
    subprocess.run([FREECAD, str(tmp_path / "two.py"), "--pass", str(tmp_path / "two.step")], capture_output=True, check=True)
    data = (tmp_path / "two.step").read_bytes()
    solids = [int(i) for i in re.findall(rb"#(\d+) = MANIFOLD_SOLID_BREP", data)]
    assert len(solids) == 2
    replace_step(project_copy, plate, invisible(data, solids[1]))
    out = run("step_facts.py", project_copy, "--", "--only", "base-plate")
    assert "1 measured" in out and "invisible_left_out=1" in out, out
    project = layout.load(project_copy)
    facts = project.components["base-plate"].facts
    assert facts["solids"] == 1 and facts["invisible_items"] == 1
    assert facts["volume_mm3"] == pytest.approx(1000.0) and facts["bounding_box_mm"]["max"] == pytest.approx([10, 10, 10])
    assert not [e for e in project.errors if "facts.json" in e]
    assert "0 measured, 1 already current" in run("step_facts.py", project_copy, "--", "--only", "base-plate")


def test_another_export_is_compared_by_its_geometry(project_copy, tmp_path):
    plate = project_copy / "references/parts/base-plate/part.step"
    pin = project_copy / "references/parts/pin/part.step"
    # the plate again with another header (other bytes, the same data section), and the pin standing in for the plate
    other = tmp_path / "plate-again.step"
    other.write_bytes(plate.read_bytes().replace(b"1970-01-01T00:00:00", b"2026-11-11T09:00:00"))
    write_json(tmp_path / "map.json", {"base-plate": str(other), "pin": str(plate), "nothing": str(other)})
    out = run("compare_step_exports.py", project_copy, tmp_path / "map.json", tmp_path / "report.json")
    assert "3 compared: 1 the same geometry, 1 different, 1 failed" in out and "exit status 1" in out, out
    report = json.loads((tmp_path / "report.json").read_text())
    same = report["parts"]["base-plate"]
    assert same["same_geometry"] and same["same_data_section"] and not same["same_bytes"] and not same["other"]["header_normalised"]
    assert not report["parts"]["pin"]["same_geometry"] and any("volume_mm3" in d for d in report["parts"]["pin"]["differences"])
    assert "no imported part of this key" in report["parts"]["nothing"]["error"]
    assert "exists; choose a new file" in run("compare_step_exports.py", project_copy, tmp_path / "map.json", tmp_path / "report.json")
    before = {p: p.read_bytes() for p in project_copy.rglob("*") if p.is_file()}
    write_json(tmp_path / "all.json", {"base-plate": str(plate), "pin": str(pin)})
    assert "2 compared: 2 the same geometry, 0 different, 0 failed; 0 part(s) of the project not compared" in run(
        "compare_step_exports.py", project_copy, tmp_path / "all.json", tmp_path / "all-report.json")
    assert {p: p.read_bytes() for p in project_copy.rglob("*") if p.is_file()} == before          # nothing in the project is written
