"""The tools of the draft of joints and poses that need a kernel, run only where FreeCADCmd is on PATH:

    guix shell --pure -m manifest.scm -m .guix/manifest-cad.scm -- python3 -B -m pytest -q tests/test_sweep.py

The fixture's spacer sits on the base plate round a pin, a quarter of a millimetre clear of it all round.
"""
import json
import shutil
import subprocess

import pytest
from conftest import REPO, replace_step

from mechanical_cad import motion

FREECAD = shutil.which("FreeCADCmd")
pytestmark = pytest.mark.skipif(FREECAD is None, reason="FreeCADCmd is not on PATH (use the CAD role)")

RECORD = """
schema_version = 1

[joints.slide]
assembly = "fixture-with-spacer"
kind = "prismatic"
origin_mm = [0.0, 0.0, 0.0]
direction = [1.0, 0.0, 0.0]
range_mm = [-3.0, 3.0]
moves = ["SPACER:1"]

[joints.spin]
assembly = "fixture-with-spacer"
kind = "revolute"
origin_mm = [-25.0, 8.0, -15.0]
direction = [0.0, 1.0, 0.0]
range_deg = [-90.0, 90.0]
moves = ["SPACER:1"]
carried_by = "slide"

[joints.pin]
assembly = "pin-pair"
kind = "prismatic"
origin_mm = [0.0, 0.0, 0.0]
direction = [1.0, 0.0, 0.0]
range_mm = [-1.0, 1.0]
moves = ["PIN:1"]

[poses.aside]
slide = 0.2
"""


def run(tool, *args):
    proc = subprocess.run([FREECAD, str(REPO / "tools" / tool), "--pass", *map(str, args)], capture_output=True, text=True)
    return proc.stdout + proc.stderr


@pytest.fixture
def moving(project_copy):
    (project_copy / motion.FILE).write_text(RECORD, encoding="utf-8")
    return project_copy


def test_a_joint_is_walked_and_the_stretch_that_is_free_is_found(moving, tmp_path):
    report = tmp_path / "sweep.json"
    out = run("sweep_check.py", moving, "fixture-with-spacer", "--", "--joint", "slide", "--", "--out", report)
    assert "[sweep_check] exit status 1" in out, out
    assert "as assembled, every joint at 0: 0 interference(s) and 1 contact(s) between what moves and the rest" in out
    assert "    0.000 mm  free; nearest 0.250 mm: SPACER:1 [0] and FIXTURE ROOT:1/PIN PAIR:1/PIN:1 [0]" in out
    assert "    0.500 mm  BLOCKED: SPACER:1 [0] shares" in out and "   -3.000 mm  BLOCKED" in out
    assert "slide: 13 step(s) of 0.5 mm, 1 free and 12 blocked; 1 solid(s) moving against 5" in out
    found = json.loads(report.read_text())
    # the spacer is 0.25 mm clear of its pin: that is how far it slides either way, found to a 32nd of a step
    assert found["free"]["from"] == pytest.approx(-0.25, abs=0.5 / 32) and found["free"]["from"] >= -0.25
    assert found["free"]["to"] == pytest.approx(0.25, abs=0.5 / 32) and found["free"]["to"] <= 0.25
    above = found["free"]["blocked_above"]
    assert 0.25 < above["value"] <= 0.25 + 0.5 / 32 and above["by"][0]["other"] == "FIXTURE ROOT:1/PIN PAIR:1/PIN:1"
    assert [s["value"] for s in found["steps"]][:3] == [-3.0, -2.5, -2.0] and found["steps"][6]["free"] is True
    assert (found["joint"], found["unit"], found["refined"], found["followers"]) == ("slide", "mm", 5, [])
    assert found["motion"]["file"] == "motion.toml" and len(found["scene_sha256"]) == 64
    first = report.read_bytes()
    run("sweep_check.py", moving, "fixture-with-spacer", "--", "--joint", "slide", "--", "--out", report)
    assert report.read_bytes() == first                            # no timestamp: the same walk, the same bytes

    # without the halving the stretch ends at the last free step
    out = run("sweep_check.py", moving, "fixture-with-spacer", "--", "--joint", "slide", "--", "--refine", "0")
    assert "[sweep_check] free from 0.000 to 0.000 mm; below that, at -0.500," in out


def test_a_turn_about_its_own_line_is_free_all_the_way_and_another_joint_can_be_set_aside(moving):
    out = run("sweep_check.py", moving, "fixture-with-spacer", "--", "--joint", "spin", "--", "--steps", "5")
    assert "[sweep_check] exit status 0" in out, out
    assert "[sweep_check] free from -90.000 to 90.000 deg, the whole range walked" in out
    assert "spin: 5 step(s) of 45 deg, 5 free and 0 blocked" in out
    # with the spacer slid 0.2 aside first it is 0.05 from the pin on one side, and stays there as it turns
    out = run("sweep_check.py", moving, "fixture-with-spacer", "--", "--joint", "spin", "--", "--steps", "3",
              "--", "--pose", "aside")
    assert "the other joints at slide = 0.2" in out and "free; nearest 0.050 mm" in out, out
    # slid 0.3 it is in the pin wherever it is turned to, and that is held against the turn: it is not there
    # as assembled
    out = run("sweep_check.py", moving, "fixture-with-spacer", "--", "--joint", "spin", "--", "--steps", "3",
              "--", "--at", "slide=0.3")
    assert "as assembled, every joint at 0: 0 interference(s)" in out, out
    assert "[sweep_check] blocked at the step nearest the assembled position, 0 deg" in out
    assert "spin: 3 step(s) of 90 deg, 0 free and 3 blocked" in out


def test_a_joint_in_two_places_is_named_with_its_place(moving):
    out = run("sweep_check.py", moving, "fixture-with-spacer", "--", "--joint", "pin")
    assert "[sweep_check] exit status 2" in out
    assert "has the joint pin in several places; name one: pin@FIXTURE ROOT:1/PIN PAIR:1, pin@FIXTURE ROOT:1/PIN PAIR:2" in out
    # the first pin of the first pair moved towards the spacer round it: 0.25 either way
    out = run("sweep_check.py", moving, "fixture-with-spacer", "--", "--joint", "pin@FIXTURE ROOT:1/PIN PAIR:1",
              "--", "--steps", "5")
    assert "[sweep_check] exit status 1" in out, out
    assert "BLOCKED: FIXTURE ROOT:1/PIN PAIR:1/PIN:1 [0] shares" in out and "with SPACER:1 [0]" in out
    out = run("sweep_check.py", moving, "fixture-with-spacer", "--", "--joint", "lever")
    assert "no joint 'lever'; its joints: pin@FIXTURE ROOT:1/PIN PAIR:1, pin@FIXTURE ROOT:1/PIN PAIR:2, slide, spin" in out


def test_without_the_record_or_with_a_wrong_one_nothing_is_walked(project_copy):
    out = run("sweep_check.py", project_copy, "fixture-with-spacer", "--", "--joint", "slide")
    assert "[sweep_check] exit status 2" in out and "a pose or a joint needs the project's motion.toml" in out
    (project_copy / motion.FILE).write_text(RECORD.replace("range_mm = [-3.0, 3.0]", "range_mm = [3.0, -3.0]"), encoding="utf-8")
    out = run("sweep_check.py", project_copy, "fixture-with-spacer", "--", "--joint", "slide")
    assert "[sweep_check] exit status 2" in out and "joints.slide: range_mm must be [lower, upper]" in out


def test_a_follower_goes_with_its_joint_and_is_measured_against_what_that_joint_moves(moving):
    """The second pin of a pair follows the first at one to one: the two keep their distance, and the walk ends
    where the first meets the spacer, not where the pins would meet each other."""
    (moving / motion.FILE).write_text(RECORD + """
[joints.other]
assembly = "pin-pair"
kind = "prismatic"
origin_mm = [0.0, 0.0, 0.0]
direction = [1.0, 0.0, 0.0]
moves = ["PIN:2"]
follows = "pin"
ratio = 1.0
""", encoding="utf-8")
    out = run("sweep_check.py", moving, "fixture-with-spacer", "--", "--joint", "pin@FIXTURE ROOT:1/PIN PAIR:2",
              "--", "--steps", "3")
    assert "[sweep_check] exit status 0" in out, out
    assert "2 occurrence(s) move, 1 of them with a joint that follows it" in out
    out = run("sweep_check.py", moving, "fixture-with-spacer", "--", "--joint", "other@FIXTURE ROOT:1/PIN PAIR:2")
    assert "other@FIXTURE ROOT:1/PIN PAIR:2 follows pin@FIXTURE ROOT:1/PIN PAIR:2; walk that joint" in out


def test_a_part_without_a_solid_is_not_compared_and_is_named(moving, tmp_path):
    """A supplier's model may be faces without a solid. The pins are made that here: the spacer then slides
    through where its pin stands, and both tools say which part they did not see."""
    pin = moving / "references/parts/pin"
    data = (pin / "part.step").read_bytes()
    assert data.count(b"MANIFOLD_SOLID_BREP('',#16)") == 1 and data.count(b"ADVANCED_BREP_SHAPE_REPRESENTATION") == 1
    replace_step(moving, "references/parts/pin",
                 data.replace(b"MANIFOLD_SOLID_BREP('',#16)", b"SHELL_BASED_SURFACE_MODEL('',(#16))")
                     .replace(b"ADVANCED_BREP_SHAPE_REPRESENTATION", b"MANIFOLD_SURFACE_SHAPE_REPRESENTATION"))
    report = tmp_path / "sweep.json"
    out = run("sweep_check.py", moving, "fixture-with-spacer", "--", "--joint", "slide", "--", "--steps", "5", "--", "--out", report)
    assert "[sweep_check] 1 part(s) have no solid and are not compared: pin" in out, out
    assert "[sweep_check] exit status 0" in out and "free from -3.000 to 3.000 mm, the whole range walked" in out
    assert json.loads(report.read_text())["parts_without_a_solid"] == ["pin"]
    report = tmp_path / "fit.json"
    out = run("fit_check.py", moving, "fixture-with-spacer", "--", "--subject", "SPACER:1", "--", "--out", report)
    assert "[fit_check] 1 part(s) have no solid and are not compared: pin" in out, out
    assert "CLOSE" not in out and json.loads(report.read_text())["parts_without_a_solid"] == ["pin"]


def test_the_lines_of_round_faces_are_listed_in_the_assembly_s_frame(project_copy):
    out = run("axes.py", project_copy, "fixture-with-spacer", "--", "--child", "SPACER:1")
    assert "[axes] exit status 0" in out, out
    # the spacer's bore and rim are on one line: upright, through where the first pin stands
    assert "origin_mm = [-25, 0, -15]  direction = [0, 1, 0]  radii " in out and "SPACER:1" in out
    assert "[axes] fixture-with-spacer, SPACER:1: 1 line(s) of round faces over 1 occurrence(s), in the frame of fixture-with-spacer" in out
    out = run("axes.py", project_copy, "fixture-with-spacer")
    assert "FIXTURE ROOT:1/PIN PAIR:1/PIN:1" in out and "over 6 occurrence(s)" in out
    out = run("axes.py", project_copy, "fixture-with-spacer", "--", "--child", "WASHER:1")
    assert "[axes] exit status 2" in out and "places nothing named 'WASHER:1'; its children: FIXTURE ROOT:1, SPACER:1" in out
    out = run("axes.py", project_copy, "spacer")
    assert "[axes] exit status 0" in out and "in the frame of spacer" in out
