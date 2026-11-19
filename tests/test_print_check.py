"""tools/print_check.py: the plate, the faces that hang over and what starts in mid-air, where FreeCADCmd is on PATH:

    guix shell --pure -m manifest.scm -m .guix/manifest-cad.scm -- python3 -B -m pytest -q tests/test_print_check.py
"""
import json
import math
import shutil
import subprocess

import pytest
from conftest import REPO

FREECAD = shutil.which("FreeCADCmd")
pytestmark = pytest.mark.skipif(FREECAD is None, reason="FreeCADCmd is not on PATH (use the CAD role)")

# Shapes with known answers, each written as a STEP file. All stand on Z = 0.
SHAPES = '''
import math, sys
import FreeCAD as App
import Part
V = App.Vector
out = sys.argv[sys.argv.index("--pass") + 1]

def prism(profile, depth):
    """A profile in the XZ plane, pushed along Y."""
    points = [V(x, 0, z) for x, z in profile]
    return Part.Face(Part.makePolygon(points + points[:1])).extrude(V(0, depth, 0))

block = Part.makeBox(20, 10, 5)
# a post with a wider slab on it: the slab's underside is a flat ceiling on both sides of the post
tee = Part.makeBox(10, 10, 10).fuse(Part.makeBox(30, 10, 5, V(-10, 0, 10))).removeSplitter()
# one face leans out at 45 degrees
wedge = prism([(0, 0), (10, 0), (20, 10), (20, 15), (0, 15)], 10)
# a block over a dome: the dome is upright at the plate and flat at its top
dome = Part.makeBox(30, 30, 15, V(-15, -15, 0)).cut(Part.makeSphere(10))
# three roofs at 45 degrees that meet from three sides: the material between them begins as a point in mid-air
s, r = 24.0, 20.0
axes = [V(s / math.sqrt(3) * math.cos(a), s / math.sqrt(3) * math.sin(a), 0) for a in (0, 2 * math.pi / 3, 4 * math.pi / 3)]
vaults = Part.makeBox(70, 70, 25, V(-35, -35, 0))
for axis in axes:
    vaults = vaults.cut(Part.makeCone(r, 0, r, axis))
# ... and the same with a wall from the plate up to where they meet
walled = vaults.fuse(Part.makeBox(2, 35, 20, V(-1, 0, 0))).removeSplitter()
# a plate with a round pocket 8 across and 1 deep in its underside, and a slot 4 by 30 beside it
pocketed = Part.makeBox(60, 40, 3).cut(Part.makeCylinder(4, 1, V(15, 20, 0))).cut(Part.makeBox(4, 30, 1, V(40, 5, 0)))
for name, shape in (("block", block), ("tee", tee), ("wedge", wedge), ("dome", dome), ("vaults", vaults), ("walled", walled),
                    ("pocketed", pocketed)):
    assert shape.isValid() and len(shape.Solids) == 1, name
    shape.exportStep(out + "/" + name + ".step")
print("[shapes] written")
'''


@pytest.fixture(scope="module")
def shapes(tmp_path_factory):
    where = tmp_path_factory.mktemp("print-check-shapes")
    (where / "shapes.py").write_text(SHAPES)
    done = subprocess.run([FREECAD, str(where / "shapes.py"), "--pass", str(where)], capture_output=True, text=True)
    assert "[shapes] written" in done.stdout, done.stdout + done.stderr
    return where


def run(*args):
    proc = subprocess.run([FREECAD, str(REPO / "tools" / "print_check.py"), "--pass", *map(str, args)],
                          capture_output=True, text=True)
    return proc.stdout + proc.stderr


def check(shapes, name, *options):
    """The record of one shape, and what the tool printed."""
    record = shapes / f"{name}{'-'.join(o.strip('-+') for o in options if o != '--')}.json"
    out = run(shapes / f"{name}.step", "--", "--out", record, *options)
    return json.loads(record.read_text()), out


def test_a_block_on_the_plate_passes(shapes):
    record, out = check(shapes, "block")
    assert "[print_check] exit status 0" in out, out
    assert record["passed"] and record["checks"] == {"plate": True, "overhang": True, "islands": True}
    assert record["plate"]["area_mm2"] == pytest.approx(200.0) and record["plate"]["build_height_mm"] == pytest.approx(5.0)
    assert record["plate"]["level_mm"] == 0.0 and record["up"] == "+Z"
    assert record["overhang"]["faces_looking_down"] == 0 and record["overhang"]["lowest_angle_deg"] is None
    assert record["layers"]["samples"] == 10 and record["layers"]["islands"] == []
    assert record["file"] == "block.step" and len(record["step"]["sha256"]) == 64
    assert "timestamp" not in json.dumps(record)


def test_a_flat_ceiling_hangs_over(shapes):
    record, out = check(shapes, "tee")
    assert "[print_check] exit status 1" in out and out.count("OVERHANG") == 2, out
    assert record["checks"] == {"plate": True, "overhang": False, "islands": True}
    below = record["overhang"]["below_the_angle"]
    assert [f["lowest_angle_deg"] for f in below] == [pytest.approx(0.0, abs=1e-6)] * 2
    assert record["overhang"]["area_below_the_angle_mm2"] == pytest.approx(200.0)       # 10 x 10 on each side of the post
    assert all(f["at"][2] == pytest.approx(10.0) for f in below)                         # under the slab


def test_a_flat_ceiling_that_a_printer_lays_across_is_a_bridge_when_that_is_asked(shapes):
    """The roofs of a pocket for a stick-on foot, 8 mm across, and of a slot 4 mm wide and 30 long."""
    record, out = check(shapes, "pocketed")
    assert "[print_check] exit status 1" in out and out.count("OVERHANG") == 2 and "BRIDGE" not in out, out
    assert "bridges" not in record["overhang"] and "bridge_mm" not in record["overhang"]       # the record is what it was
    record, out = check(shapes, "pocketed", "--", "--bridge", "8")
    assert "[print_check] exit status 0" in out and out.count("BRIDGE") == 2 and "OVERHANG" not in out, out
    assert "none below 45 degrees, 2 flat ceiling(s) taken as bridges of up to 8 mm" in out
    bridges = sorted(record["overhang"]["bridges"], key=lambda f: f["width_mm"])
    assert [f["width_mm"] for f in bridges] == [pytest.approx(4.0, abs=1e-6), pytest.approx(8.0, abs=1e-6)]
    assert bridges[1]["area_mm2"] == pytest.approx(math.pi * 16.0, rel=1e-6) and bridges[0]["at"][2] == pytest.approx(1.0)
    assert record["overhang"]["bridge_mm"] == 8.0 and record["overhang"]["below_the_angle"] == []
    assert record["overhang"]["faces_looking_down"] == 2 and record["checks"]["overhang"] is True
    # a narrower limit takes the slot, which is laid across its 4 mm, and not the pocket
    record, out = check(shapes, "pocketed", "--", "--bridge", "5")
    assert "[print_check] exit status 1" in out and out.count("BRIDGE") == 1 and out.count("OVERHANG") == 1, out
    assert record["overhang"]["below_the_angle"][0]["area_mm2"] == pytest.approx(math.pi * 16.0, rel=1e-6)
    # the slab on a post is no bridge however wide one may be: it is held at one end and hangs free at the other
    record, out = check(shapes, "tee", "--", "--bridge", "50")
    assert "[print_check] exit status 1" in out and out.count("OVERHANG") == 2 and "BRIDGE" not in out, out
    assert record["overhang"]["bridges"] == []
    assert "exit status 2" in run(shapes / "tee.step", "--", "--bridge", "-1")


def test_a_face_at_the_angle_passes_and_a_flatter_limit_fails_it(shapes):
    record, out = check(shapes, "wedge")
    assert "[print_check] exit status 0" in out, out
    assert record["overhang"]["lowest_angle_deg"] == pytest.approx(45.0)
    assert record["overhang"]["area_looking_down_mm2"] == pytest.approx(10.0 * math.sqrt(200.0))
    stricter, out = check(shapes, "wedge", "--", "--angle", "50")
    assert "[print_check] exit status 1" in out and "BELOW 50 degrees" in out, out
    assert stricter["overhang"]["area_below_the_angle_mm2"] == pytest.approx(10.0 * math.sqrt(200.0))


def test_a_part_is_checked_the_way_up_that_is_named(shapes):
    # the wedge on its back: the leaning face now looks up, and the 15 x 10 face that was its top is the plate
    record, out = check(shapes, "wedge", "--", "--up", "-Z")
    assert "[print_check] exit status 0" in out, out
    assert record["up"] == "-Z" and record["plate"]["area_mm2"] == pytest.approx(200.0)
    assert record["plate"]["level_mm"] == pytest.approx(-15.0) and record["overhang"]["faces_looking_down"] == 0
    # on its side, growing along +X: its low end face is the plate, and nothing looks down
    side, out = check(shapes, "wedge", "--", "--up", "+X")
    assert side["plate"]["area_mm2"] == pytest.approx(150.0) and side["plate"]["build_height_mm"] == pytest.approx(20.0)
    assert "exit status 2" in run(shapes / "wedge.step", "--", "--up", "sideways")


def test_a_curved_face_is_measured_where_it_hangs_over(shapes):
    record, out = check(shapes, "dome")
    assert "[print_check] exit status 1" in out and out.count("OVERHANG") == 1, out
    (face,) = record["overhang"]["below_the_angle"]
    assert face["surface"] == "Sphere" and face["lowest_angle_deg"] < 3.0
    # of the half sphere of radius 10, the cap within 45 degrees of its top is flatter than 45 degrees
    cap = 2.0 * math.pi * 10.0 ** 2 * (1.0 - math.cos(math.radians(45.0)))
    assert face["area_below_the_angle_mm2"] == pytest.approx(cap, rel=0.03)
    assert face["area_mm2"] == pytest.approx(2.0 * math.pi * 10.0 ** 2, rel=1e-6)
    assert face["at"][2] > 9.9 and math.hypot(face["at"][0], face["at"][1]) < 1.5       # at the top of the dome
    assert record["layers"]["islands"] == []


def test_material_between_roofs_that_all_pass_starts_in_mid_air(shapes):
    record, out = check(shapes, "vaults")
    assert "[print_check] exit status 1" in out and out.count("ISLAND") == 1 and "OVERHANG" not in out, out
    assert record["checks"] == {"plate": True, "overhang": True, "islands": False}
    assert record["overhang"]["lowest_angle_deg"] == pytest.approx(45.0, abs=1e-6)
    (island,) = record["layers"]["islands"]
    # the three roofs leave the middle uncovered from 20 - 24 / sqrt(3) = 6.14 mm up; the next slice is at 6.25
    assert island["height_mm"] == pytest.approx(6.25) and 0.0 < island["area_mm2"] < 0.2
    assert math.hypot(island["at"][0], island["at"][1]) < 0.05 and 6.25 <= island["at"][2] <= 6.27
    # a wall from the plate up to that point holds it
    held, out = check(shapes, "walled")
    assert "[print_check] exit status 0" in out and "nothing starts in mid-air" in out, out
    assert held["passed"]
    # with slices 4 mm apart the piece has joined the rest before a slice meets it: a coarse step can miss a start
    coarse, out = check(shapes, "vaults", "--", "--step", "4")
    assert coarse["layers"]["islands"] == [] and coarse["layers"]["samples"] == 6      # at 2, 6, 10 ... 22 mm


def test_a_part_of_a_project_gets_a_record_beside_its_print_file(project_copy):
    out = run(project_copy, "spacer")
    assert "[print_check] exit status 0" in out, out
    path = project_copy / ".cache" / "print" / "spacer.check.json"
    first = path.read_bytes()
    record = json.loads(first)
    assert record["key"] == "spacer" and record["passed"] and record["schema_version"] == 1
    facts = json.loads((project_copy / "designs/parts/spacer/facts.json").read_text())
    assert record["step"]["sha256"] == facts["step"]["sha256"]
    assert record["plate"]["build_height_mm"] == pytest.approx(facts["bounding_box_mm"]["max"][2] - facts["bounding_box_mm"]["min"][2])
    run(project_copy, "spacer")
    assert path.read_bytes() == first                               # the same part, the same bytes
    assert "has no part 'nothing'" in run(project_copy, "nothing") and "exit status 2" in run(project_copy, "nothing")
