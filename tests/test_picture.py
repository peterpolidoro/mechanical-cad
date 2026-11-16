"""tools/picture.py: where a camera stands, and pictures made with f3d where it is on PATH with EGL:

    guix shell --pure -m manifest.scm -m .guix/manifest-view.scm -- python3 -B -m pytest -q tests/test_picture.py
"""
import importlib.util
import shutil
import subprocess
import sys

import pytest
from conftest import REPO

TOOL = REPO / "tools" / "picture.py"
spec = importlib.util.spec_from_file_location("picture_tool", TOOL)
picture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(picture)

F3D = shutil.which("f3d")


def egl():
    if F3D is None:
        return False
    listed = subprocess.run([F3D, "--list-rendering-backends"], capture_output=True, text=True)
    return "egl: available" in listed.stdout + listed.stderr


draws = pytest.mark.skipif(not egl(), reason="f3d with EGL is not on PATH (use .guix/manifest-view.scm)")


def run(*args):
    done = subprocess.run([sys.executable, "-B", str(TOOL), *map(str, args)], capture_output=True, text=True)
    return done.stdout + done.stderr


def test_a_view_says_where_the_camera_stands():
    assert picture.stands("iso", "+Z") == (1, -1, 0.8)
    assert picture.stands("iso-back", "+Z") == (-1, 1, 0.8)
    assert picture.stands("below", "+Z") == (1, -1, -0.8)
    assert picture.stands("+x", "+Z") == (1, 0, 0) and picture.stands("-Y", "+Z") == (0, -1, 0)
    # with Y up, the two other axes are Z and X: above is +Y
    assert picture.stands("iso", "+Y") == (-1, 0.8, 1)
    assert picture.stands("iso", "-Z")[2] == -0.8
    # straight along the up axis the camera leans a little, so that it has an up
    assert picture.stands("+z", "+Z") == (0.02, 0, 1) and picture.stands("-y", "+Y") == (0, -1, 0.02)
    with pytest.raises(ValueError, match="unknown view"):
        picture.stands("front", "+Z")
    assert [picture.file_name(v) for v in ("iso", "+x", "-Z")] == ["iso", "plus-x", "minus-z"]


def test_what_cannot_be_drawn_is_said(project_copy):
    assert "exit status 2" in run(project_copy)                                      # no key
    if F3D is None:
        assert "f3d is not on PATH" in run(project_copy, "spacer")
        return
    out = run(project_copy, "washer")
    assert "has no component 'washer'; its keys:" in out and "spacer" in out and "exit status 2" in out
    out = run(project_copy, "fixture-root")
    assert "fixture-root is an assembly and is not built" in out and "exit status 2" in out
    assert "unknown view 'front'" in run(project_copy, "spacer", "--views", "front")


@draws
def test_a_part_is_drawn_from_its_step_file(project_copy, tmp_path):
    out = run(project_copy, "spacer", "--views", "iso,-z", "--size", "400x300")
    assert "[picture] exit status 0" in out, out
    for name in ("spacer-iso.png", "spacer-minus-z.png"):
        png = project_copy / ".cache" / "pictures" / name
        assert png.read_bytes()[:8] == picture.PNG and png.stat().st_size > 1000, name
    # a file by itself, to a directory that is named
    out = run(project_copy / "designs/parts/spacer/part.step", "--views", "below", "--up", "+Y", "--out", tmp_path / "out")
    assert "[picture] exit status 0" in out and (tmp_path / "out" / "part-below.png").read_bytes()[:8] == picture.PNG
