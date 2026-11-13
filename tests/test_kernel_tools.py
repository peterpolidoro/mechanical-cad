"""The kernel-backed tools, run only where FreeCADCmd is on PATH (the CAD role):

    guix shell --pure -m manifest.scm -m .guix/manifest-cad.scm -- python3 -B -m pytest -q tests/test_kernel_tools.py
"""
import importlib.util
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from conftest import REPO, edit_json, invisible, replace_step, write_json

from mechanical_cad import assemblies, fcstd, layout

FREECAD = shutil.which("FreeCADCmd")
pytestmark = pytest.mark.skipif(FREECAD is None, reason="FreeCADCmd is not on PATH (use the CAD role)")
SPACER = "designs/parts/spacer"
# What is recorded of a shape is measured with the kernel's adaptive integration, through the OCP bindings.
measures = pytest.mark.skipif(importlib.util.find_spec("OCP") is None,
                              reason="the OCP bindings are not in this environment (make test-build123d)")


def run(tool, *args):
    proc = subprocess.run([FREECAD, str(REPO / "tools" / tool), "--pass", *map(str, args)], capture_output=True, text=True)
    return proc.stdout + proc.stderr


def derived(part_dir):
    return {name: (Path(part_dir) / name).read_bytes() for name in ("part.step", "receipt.json", "facts.json")}


@measures
def test_building_an_unchanged_part_changes_no_file(project_copy):
    before = derived(project_copy / SPACER)
    out = run("build_part.py", project_copy / SPACER)
    assert "[build_part] exit status 0" in out, out
    assert derived(project_copy / SPACER) == before
    assert layout.load(project_copy).errors == []


@measures
def test_a_changed_parameter_rebuilds_and_fails_its_check(project_copy):
    edit_json(project_copy / SPACER / "parameters.json", lambda d: d.update(height_mm=6.0))
    assert any("parameters.json has changed" in e for e in layout.load(project_copy).errors)
    out = run("build_part.py", project_copy / SPACER)
    assert "FAILED: outer-size" in out and "[build_part] exit status 1" in out
    project = layout.load(project_copy)
    assert project.errors == []                                   # the receipt is current again
    assert project.components["spacer"].facts["bounding_box_mm"]["max"][2] == pytest.approx(6.0)


@measures
def test_a_program_that_fails_is_reported(project_copy):
    edit_json(project_copy / SPACER / "parameters.json", lambda d: d.update(inner_diameter_mm=30.0))
    out = run("build_part.py", project_copy / SPACER)
    assert "need 0 < inner diameter < outer diameter" in out and "[build_part] exit status 1" in out


RING_WITH_BUILD123D = '''"""The fixture's spacer ring, written with build123d."""


def build(parameters):
    from build123d import Align, Cylinder

    outer = parameters["outer_diameter_mm"] / 2.0
    inner = parameters["inner_diameter_mm"] / 2.0
    height = parameters["height_mm"]
    if not 0 < inner < outer or height <= 0:
        raise ValueError("need 0 < inner diameter < outer diameter and a positive height")
    on_z0 = (Align.CENTER, Align.CENTER, Align.MIN)        # axis along Z, bottom face on Z = 0
    return Cylinder(outer, height, align=on_z0) - Cylinder(inner, height, align=on_z0)
'''


@pytest.mark.skipif(importlib.util.find_spec("build123d") is None,
                    reason="build123d is not in this environment (make test-build123d)")
def test_a_part_written_with_build123d_is_built_by_the_same_tool(project_copy):
    part = project_copy / SPACER
    with_freecad = json.loads((part / "facts.json").read_text())
    (part / "build.py").write_text(RING_WITH_BUILD123D, encoding="utf-8")
    assert any("build.py has changed" in e for e in layout.load(project_copy).errors)
    out = run("build_part.py", part)
    assert "re-import ok" in out and "4 check(s)" in out and "FAILED" not in out, out
    assert "[build_part] exit status 0" in out, out
    receipt = json.loads((part / "receipt.json").read_text())
    # FreeCAD still writes and measures the file; the receipt says what built the shape
    assert receipt["tool"]["name"] == "FreeCAD"
    library = receipt["tool"]["library"]
    assert library["name"] == "build123d" and library["version"] and library["bindings"] == "OCP", library
    facts = json.loads((part / "facts.json").read_text())
    assert "library" not in facts["tool"] and facts["tool"]["integration"]["method"] == "adaptive"
    # the same ring as FreeCAD's Part module builds from the same parameters
    assert facts["solids"] == with_freecad["solids"] == 1
    assert facts["volume_mm3"] == pytest.approx(with_freecad["volume_mm3"], rel=1e-9)
    assert facts["bounding_box_mm"]["min"] == pytest.approx(with_freecad["bounding_box_mm"]["min"], abs=1e-6)
    assert facts["bounding_box_mm"]["max"] == pytest.approx(with_freecad["bounding_box_mm"]["max"], abs=1e-6)
    assert layout.load(project_copy).errors == []
    # and a second build changes no file
    before = derived(part)
    assert "[build_part] exit status 0" in run("build_part.py", part)
    assert derived(part) == before


@pytest.mark.skipif(importlib.util.find_spec("OCP") is not None, reason="the OCP bindings are here")
def test_without_the_bindings_nothing_is_measured_and_the_tool_says_why(project_copy):
    before = derived(project_copy / SPACER)
    out = run("step_facts.py", project_copy, "--", "--force")
    assert "measuring needs the OCP bindings" in out and "[step_facts] exit status 2" in out, out
    out = run("build_part.py", project_copy / SPACER)
    assert "measuring needs the OCP bindings" in out and "[build_part] exit status 1" in out, out
    assert derived(project_copy / SPACER) == before          # and nothing was written


def test_instances_that_hold_the_same_share_one_product(project_copy, tmp_path):
    def unflex(assembly):
        pair = next(child for child in assembly["children"] if child["name"] == "PIN PAIR:2")
        pair["flexible"] = False
        del pair["overrides"]
    edit_json(project_copy / "references/assemblies/fixture-root/assembly.json", unflex)
    assert layout.load(project_copy).errors == []
    out = run("assembly_step.py", project_copy)
    assert "6 occurrence(s), 6 solid(s)" in out and "every solid is where the scene puts it" in out, out
    report = json.loads(cache(project_copy)[".json"])
    # four instances of an assembly in the scene; the two pin pairs are one container and a link to it
    assert report["assembly_nodes"] == 4 and report["assembly_containers"] == 3
    assert report["check"]["same"] and report["check"]["solids_matched"] == 6
    step = cache(project_copy)[".step"]
    names = re.findall(rb"PRODUCT\s*\(\s*'([^']*)'", step)
    assert names.count(b"PIN PAIR") == 1 and b"PIN PAIR (2)" not in names and len(names) == 7
    usages = re.findall(rb"NEXT_ASSEMBLY_USAGE_OCCURRENCE\s*\(\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'[^']*'\s*,\s*#\d+\s*,\s*(#\d+)", step)
    by_name = {n: used for i, n, used in usages}
    assert all(i == n for i, n, _ in usages) and len(usages) == 8
    assert by_name[b"PIN PAIR:1"] == by_name[b"PIN PAIR:2"]             # both usages are of the one product
    assert sorted(n for _, n, _ in usages).count(b"PIN:1") == 1         # and its two pins are in the file once
    # the FreeCAD document has a container for each pair all the same, so that one can be hidden by itself
    view = fcstd.read_view(project_copy / ".cache" / "assemblies" / f"{WHOLE}.FCStd")
    assert not any(name.startswith("asm_link") for name in view) and sum(view.values()) == 6 + 5


@measures
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


@measures
def test_a_body_the_file_marks_invisible_is_not_measured(project_copy, tmp_path):
    plate = "references/parts/base-plate"
    (tmp_path / "two.py").write_text(TWO_SOLIDS)
    subprocess.run([FREECAD, str(tmp_path / "two.py"), "--pass", str(tmp_path / "two.step")], capture_output=True, check=True)
    data = (tmp_path / "two.step").read_bytes()
    # a solid with an internal void is a BREP_WITH_VOIDS: both are solids
    solids = [int(i) for i in re.findall(rb"#(\d+) = (?:MANIFOLD_SOLID_BREP|BREP_WITH_VOIDS)", data)]
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


@measures
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


WHOLE = "fixture-with-spacer"


def cache(project_dir, key=WHOLE):
    d = project_dir / ".cache" / "assemblies"
    return {name: (d / f"{key}{name}").read_bytes() for name in (".step", ".FCStd", ".json")}


def test_a_whole_assembly_is_built_once_and_matches_its_scene(project_copy, tmp_path):
    tracked = {p: p.read_bytes() for p in project_copy.rglob("*") if p.is_file()}
    out = run("assembly_step.py", project_copy)                      # the only assembly nothing places
    assert "3 part(s), 6 occurrence(s), 6 solid(s)" in out and "every solid is where the scene puts it" in out, out
    assert "[assembly_step] exit status 0" in out
    report = json.loads(cache(project_copy)[".json"])
    assert report["key"] == WHOLE and report["frame"] == "z-up" and report["assembly_nodes"] == 4
    assert report["check"]["same"] and report["check"]["solids_matched"] == 6
    # the four pins and both pin pairs share one definition each: the file holds each part's geometry once
    assert report["step"]["solid_definitions"] == report["step"]["solids_in_the_part_files"] == 3
    step = cache(project_copy)[".step"]
    assert b"1970-01-01T00:00:00" in step and b"FIXTURE ROOT:1" in step and b"PIN PAIR:2" in step
    # every usage has its occurrence's name as its id, which is what Inventor shows, and the names FreeCAD
    # numbered anew (the second pair's pins) are the occurrences' own again
    usages = re.findall(rb"NEXT_ASSEMBLY_USAGE_OCCURRENCE\s*\(\s*'([^']*)'\s*,\s*'([^']*)'", step)
    assert len(usages) == report["step"]["usages"] == report["step"]["usages_with_their_name_as_id"] > 6
    assert all(i == n and not i.isdigit() for i, n in usages), usages
    assert report["step"]["names_put_back"] >= 2 and sorted(n for _, n in usages).count(b"PIN:1") == 2
    assert not any(re.search(rb":0\d\d$", n) for _, n in usages), usages
    # the second pin pair is flexible and places a pin differently, so it is an assembly of its own: two
    # products for the two pairs, named after their file, where the occurrences are PIN PAIR:1 and :2
    names = re.findall(rb"PRODUCT\s*\(\s*'([^']*)'", step)
    assert report["assembly_containers"] == 4 and report["step"]["products"] == len(names) == 8
    assert {b"FIXTURE ROOT", b"PIN PAIR", b"PIN PAIR (2)"} <= set(names) and b"PIN PAIR:1" not in names
    assert report["step"]["assembly_products_named_after_their_file"] == 3
    # the project is as it was, and what was derived is where the validator does not look
    assert {p: p.read_bytes() for p in tracked} == tracked and layout.load(project_copy).errors == []

    before = cache(project_copy)
    assert "already current" in run("assembly_step.py", project_copy, WHOLE)
    assert cache(project_copy) == before
    again = run("assembly_step.py", project_copy, "--", "--force")
    assert "unchanged" in again and "exit status 0" in again, again
    assert cache(project_copy) == before                             # built again: the same bytes, nothing rewritten
    # the FreeCAD document says what its window shows: the six occurrences and their containers, not the part files
    view = fcstd.read_view(project_copy / ".cache" / "assemblies" / f"{WHOLE}.FCStd")
    assert sum(view.values()) == 6 + 5 and {k for k, v in view.items() if not v} == {"definitions", "part_000", "part_001",
                                                                                 "part_002"}
    with zipfile.ZipFile(project_copy / ".cache" / "assemblies" / f"{WHOLE}.FCStd") as archive:
        assert archive.namelist()[0] == "Document.xml" and archive.namelist()[-1] == "GuiDocument.xml"
        assert b'<Camera settings="OrthographicCamera {' in archive.read("GuiDocument.xml")
    listed = {r["key"]: r["built"]["state"] for r in assemblies.listing(layout.load(project_copy))}
    assert listed == {WHOLE: "current", "fixture-root": "not built", "pin-pair": "not built"}

    # a sub-assembly, in its own frame, somewhere else
    sub = run("assembly_step.py", project_copy, "fixture-root", "--", "--out", tmp_path / "sub", "--", "--frame", "own")
    assert "2 part(s), 5 occurrence(s), 5 solid(s)" in sub and "exit status 0" in sub, sub
    assert json.loads((tmp_path / "sub" / "fixture-root.json").read_text())["frame"] == "own"
    refused = run("assembly_step.py", project_copy, "nothing")                 # and says which there are
    assert "'nothing' is not an assembly of this project; its assemblies: fixture-root, fixture-with-spacer, pin-pair" in refused

    # a child that is not visible is left out and named
    manifest = project_copy / "designs/assemblies" / WHOLE / "assembly.json"
    edit_json(manifest, lambda d: d["children"][1].update(visible=False))
    hidden = run("assembly_step.py", project_copy)
    assert "5 occurrence(s), 5 solid(s)" in hidden and "written" in hidden, hidden
    assert json.loads(cache(project_copy)[".json"])["occurrences_not_visible_left_out"] == ["SPACER:1"]
    edit_json(manifest, lambda d: d["children"][1].update(visible=True))        # the records change after the build
    assert assemblies.listing(layout.load(project_copy))[0]["built"]["state"] == "out of date"


def test_another_file_of_the_whole_assembly_is_compared_with_the_records(project_copy, tmp_path):
    made = run("assembly_step.py", project_copy, "--", "--out", tmp_path / "own", "--", "--frame", "own")
    assert "exit status 0" in made, made
    other = tmp_path / "own" / f"{WHOLE}.step"
    before = {p: p.read_bytes() for p in project_copy.rglob("*") if p.is_file()}
    out = run("compare_assembly_step.py", project_copy, WHOLE, other, tmp_path / "same.json")
    assert "the same assembly: 6 of 6 solid(s)" in out and "exit status 0" in out, out
    assert "exists; choose a new file" in run("compare_assembly_step.py", project_copy, WHOLE, other, tmp_path / "same.json")
    # read in the wrong frame nothing but what lies on the turn's axis is in place
    turned = run("compare_assembly_step.py", project_copy, WHOLE, other, tmp_path / "turned.json", "--", "--frame", "z-up")
    assert "DIFFERENT" in turned and "exit status 1" in turned, turned
    assert {p: p.read_bytes() for p in project_copy.rglob("*") if p.is_file()} == before     # nothing in the project is written

    # the records now put the spacer 5 mm from where the file has it
    manifest = project_copy / "designs/assemblies" / WHOLE / "assembly.json"
    edit_json(manifest, lambda d: d["children"][1]["transform"][0].__setitem__(3, -20.0))
    moved = run("compare_assembly_step.py", project_copy, WHOLE, other, tmp_path / "moved.json")
    assert "DIFFERENT: 1 of 6 solid(s) are not where the records put them; 1 solid(s) of the file are not expected" in moved, moved
    report = json.loads((tmp_path / "moved.json").read_text())
    assert not report["same_assembly"] and report["other"]["invisible_items_left_out"] == 0
    assert report["unmatched_by_part"]["spacer"]["nearest_solid_of_this_volume_mm"] == [pytest.approx(5.0, abs=1e-6)]
