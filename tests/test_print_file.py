"""tools/print_file.py: what a mesh is, without a kernel; and a part's print file written where build123d is
(make test-build123d)."""
import importlib.util
import json
import struct
import subprocess
import sys

import pytest
from conftest import REPO

TOOL = REPO / "tools" / "print_file.py"
spec = importlib.util.spec_from_file_location("print_file_tool", TOOL)
print_file = importlib.util.module_from_spec(spec)
spec.loader.exec_module(print_file)

with_build123d = pytest.mark.skipif(importlib.util.find_spec("build123d") is None,
                                    reason="build123d is not in this environment (make test-build123d)")
O, X, Y, Z = (0.0, 0.0, 0.0), (6.0, 0.0, 0.0), (0.0, 6.0, 0.0), (0.0, 0.0, 6.0)
TETRAHEDRON = [(O, Y, X), (O, X, Z), (O, Z, Y), (X, Y, Z)]          # each seen counter-clockwise from outside


def run(*args):
    done = subprocess.run([sys.executable, "-B", str(TOOL), *map(str, args)], capture_output=True, text=True)
    return done.stdout + done.stderr


def test_a_closed_mesh_has_an_inside_and_a_volume():
    facts = print_file.mesh_facts(TETRAHEDRON)
    assert facts["closed"] and facts["open_edges"] == 0 and facts["triangles"] == 4
    assert facts["volume_mm3"] == pytest.approx(36.0)                # a corner of a cube of 6 mm: 6^3 / 6
    assert facts["bounding_box_mm"] == {"min": [0.0, 0.0, 0.0], "max": [6.0, 6.0, 6.0]}


def test_a_mesh_with_a_hole_or_a_face_turned_over_is_not_closed():
    assert not print_file.mesh_facts(TETRAHEDRON[:3])["closed"]
    assert print_file.mesh_facts(TETRAHEDRON[:3])["open_edges"] == 3
    turned = TETRAHEDRON[:3] + [(X, Z, Y)]
    assert not print_file.mesh_facts(turned)["closed"]
    assert not print_file.mesh_facts([])["closed"]
    flat = print_file.mesh_facts(TETRAHEDRON + [(O, O, X)])
    assert flat["degenerate_triangles"] == 1 and flat["closed"]


def test_a_binary_stl_file_is_read(tmp_path):
    body = b"".join(struct.pack("<12fH", 0, 0, 0, *a, *b, *c, 0) for a, b, c in TETRAHEDRON)
    (tmp_path / "t.stl").write_bytes(b"\0" * 80 + struct.pack("<I", 4) + body)
    assert print_file.read_stl(tmp_path / "t.stl") == TETRAHEDRON
    (tmp_path / "short.stl").write_bytes(b"\0" * 80 + struct.pack("<I", 5) + body)
    with pytest.raises(ValueError, match="not a binary STL"):
        print_file.read_stl(tmp_path / "short.stl")


@with_build123d
def test_the_print_file_of_a_part_is_closed_and_has_the_solids_volume(project_copy):
    out = run(project_copy, "spacer")
    assert "closed" in out and "NOT" not in out and "[print_file] exit status 0" in out, out
    record = json.loads((project_copy / ".cache/print/spacer.print.json").read_text())
    assert record["passed"] and record["checks"]["closed"] and record["checks"]["volume"] and record["checks"]["extent"]
    assert record["mesh"]["file"] == "spacer.stl" and (project_copy / ".cache/print/spacer.stl").is_file()
    assert 0 < record["volume_relative_difference"] < 0.005          # a ring: the triangles cut its round faces short
    again = run(project_copy, "spacer")
    assert json.loads((project_copy / ".cache/print/spacer.print.json").read_text()) == record, again
    # a coarse mesh of a ring is too far from the solid, and the tool says so
    coarse = run(project_copy, "spacer", "--deflection", "2", "--angle", "1.5")
    assert "MORE THAN 0.5 %" in coarse and "[print_file] exit status 1" in coarse, coarse
    assert "has no part 'nothing'" in run(project_copy, "nothing")
