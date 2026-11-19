"""The Makefile's short commands, looked at without running them: `make -n` prints what a target would run.

Until 2026-11-18 no test ran `make`, and two faults were found by hand that day: `make fit` divided a child's name
at its spaces, and a project's own Makefile lost its default assembly. These tests need `make` on PATH, which
manifest.scm provides; they run nothing a target names.
"""
import shutil
import subprocess

import pytest
from conftest import REPO

pytestmark = pytest.mark.skipif(shutil.which("make") is None, reason="make is not on PATH (manifest.scm provides it)")
PROJECT = "/somewhere/a-project"            # never read: nothing is run


def would_run(*args):
    """What `make` would run for those targets and variables, and its exit status."""
    done = subprocess.run(["make", "-n", "-C", str(REPO), *args], capture_output=True, text=True)
    return done.stdout + done.stderr, done.returncode


def test_make_alone_lists_the_commands_and_every_one_it_lists_is_a_target():
    out, status = would_run()
    assert status == 0, out
    done = subprocess.run(["make", "-C", str(REPO)], capture_output=True, text=True)
    listed = {line.split()[1] for line in done.stdout.splitlines() if line.startswith("make ") and len(line.split()) > 1}
    assert {"test", "validate", "part", "parts", "fit", "assembly", "open", "picture", "print", "print-check", "cut"} <= listed
    phony = next(line for line in (REPO / "Makefile").read_text().splitlines() if line.startswith(".PHONY:")).split()[1:]
    assert listed <= set(phony), sorted(listed - set(phony))


def test_a_project_is_handed_on_as_an_absolute_path_and_a_missing_one_is_said():
    out, status = would_run("validate", f"PROJECT={PROJECT}")
    assert status == 0 and f'validate "{PROJECT}"' in out, out
    out, status = would_run("validate", "PROJECT=tmp/some-project")
    assert f'validate "{REPO}/tmp/some-project"' in out, out
    out, status = would_run("validate")
    assert status != 0 and "name the project repository" in out
    # make divides a value at spaces; a path that holds one would reach the tool in pieces
    out, status = would_run("validate", "PROJECT=/somewhere/a project")
    assert status != 0 and "holds a space" in out and "python3" not in out


def test_fit_hands_the_subjects_on_whole_whatever_spaces_their_names_hold():
    out, status = would_run("fit", f"PROJECT={PROJECT}", "KEY=with-my-part", "SUBJECT=TANK SUPPORT FRAME:1,MY PART:1", "CLEARANCE=2")
    assert status == 0, out
    assert '--subjects "TANK SUPPORT FRAME:1,MY PART:1"' in out and "--clearance 2" in out and "with-my-part" in out
    assert "--subject " not in out                                   # not one argument per word
    out, status = would_run("fit", f"PROJECT={PROJECT}", "KEY=with-my-part")
    assert status != 0 and "name the children to check" in out
    out, status = would_run("fit", f"PROJECT={PROJECT}", "SUBJECT=A:1")
    assert status != 0 and "name the assembly" in out


def test_parts_are_built_in_the_order_the_project_gives_for_the_keys_that_are_named():
    out, status = would_run("parts", f"PROJECT={PROJECT}", "KEY=plug frame")
    assert status == 0 and f'build-order "{PROJECT}" plug frame' in out and "tools/build_part.py" in out, out
    out, status = would_run("part", f"PROJECT={PROJECT}", "KEY=plug")
    assert f'--pass "{PROJECT}/designs/parts/plug"' in out and "manifest-build123d.scm" in out, out
    out, status = would_run("part", f"PROJECT={PROJECT}")
    assert status != 0 and "name the part" in out


def test_a_picture_takes_the_kernel_only_when_it_is_cut_or_coloured():
    out, status = would_run("picture", f"PROJECT={PROJECT}", "KEY=machine", "VIEWS=iso,+x", "UP=+Y")
    assert status == 0 and "--views iso,+x --up +Y" in out and "manifest-view.scm" in out, out
    assert "manifest-build123d.scm" not in out and "--cut" not in out and "--colour" not in out and "--finish" not in out
    out, status = would_run("picture", f"PROJECT={PROJECT}", "KEY=machine", "CUT=-x=12.5", "COLOUR=1")
    assert status == 0 and "--cut -x=12.5 --colour" in out, out
    assert "manifest-build123d.scm" in out and "manifest-view.scm" in out
    # with the project's finishes: the kernel as well, and the word handed on
    out, status = would_run("picture", f"PROJECT={PROJECT}", "KEY=machine", "FINISH=1")
    assert status == 0 and "--finish" in out and "--colour" not in out and "--cut" not in out, out
    assert "manifest-build123d.scm" in out and "manifest-view.scm" in out


def test_a_file_is_taken_apart_into_a_project_with_what_says_where_it_came_from():
    out, status = would_run("take-apart", "FILE=tmp/a.step", f"PROJECT={PROJECT}",
                            "ORIGIN=--retrieved 2026-11-18 --publishable unknown --description 'a file'")
    assert status == 0 and f'tools/take_apart.py "{REPO}/tmp/a.step" "{PROJECT}"' in out, out
    assert "--retrieved 2026-11-18 --publishable unknown --description 'a file'" in out
    out, status = would_run("take-apart", f"PROJECT={PROJECT}")
    assert status != 0 and "name the file" in out


def test_a_section_needs_its_plane():
    out, status = would_run("section", f"PROJECT={PROJECT}", "KEY=machine", "CUT=-x=12.5", "UP=+Y")
    assert status == 0 and f'tools/section.py "{PROJECT}" machine' in out and "--cut -x=12.5 --up +Y" in out, out
    assert "--finish" not in out
    out, status = would_run("section", f"PROJECT={PROJECT}", "KEY=machine", "CUT=+y", "FINISH=1")
    assert status == 0 and "--cut +y" in out and "--finish" in out and "--measure" not in out, out
    # dimensions go on whole, however many there are in the one value
    out, status = would_run("section", f"PROJECT={PROJECT}", "KEY=machine", "CUT=+y", "MEASURE=across 0,0,0 40,0,12 gap; up 0,0,0 0,0,21")
    assert status == 0 and '--measure "across 0,0,0 40,0,12 gap; up 0,0,0 0,0,21"' in out, out
    out, status = would_run("section", f"PROJECT={PROJECT}", "KEY=machine")
    assert status != 0 and "name the plane" in out


def test_the_files_to_make_a_part_from_and_the_print_check():
    out, _ = would_run("cut", f"PROJECT={PROJECT}", "KEY=plate")
    assert f'tools/cut_file.py "{PROJECT}" plate' in out and "--pattern" not in out and "--root" not in out, out
    out, _ = would_run("cut", f"PROJECT={PROJECT}", "KEY=solid", "PATTERN=1", "ROOT=+x")
    assert f'tools/cut_file.py "{PROJECT}" solid' in out and "--pattern --root +x" in out, out
    out, _ = would_run("print", f"PROJECT={PROJECT}", "KEY=plug", "DEFLECTION=0.05")
    assert f'tools/print_file.py "{PROJECT}" plug' in out and "--deflection 0.05" in out and "manifest-print.scm" in out, out
    out, _ = would_run("print-check", f"PROJECT={PROJECT}", "KEY=plug", "UP=-X", "ANGLE=50", "STEP=0.2")
    assert f'tools/print_check.py --pass "{PROJECT}" plug' in out, out
    assert "-- --up -X" in out and "-- --angle 50" in out and "-- --step 0.2" in out
