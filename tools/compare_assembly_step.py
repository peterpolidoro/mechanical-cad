"""Is a STEP file of a whole assembly the assembly a project's records describe?

    FreeCADCmd tools/compare_assembly_step.py --pass PROJECT KEY OTHER.step OUT.json [-- --frame z-up]

OTHER.step is a file of the whole assembly KEY that something else wrote: the
CAD system the project mirrors exporting its own assembly document, or
tools/assembly_step.py. The project is flattened from KEY, the solids of its
part files are measured, and every solid of every visible occurrence is looked
for in OTHER.step, by volume and centre of mass, at the place the manifests
give it (mechanical_cad/solids.py). OTHER.step is read without the items it
marks invisible. Nothing in the project is written.

An export from the mirrored CAD system is an independent check of the recorded
placements, including those of sub-assemblies posed differently per instance:
a part in the wrong place is reported with the distance to the nearest solid
of its volume.

OTHER.step is taken to be in the assembly's own frame, as such an export is;
--frame z-up reads a file that tools/assembly_step.py turned upright. The
file need not have one length unit: Inventor writes each product of an
assembly in its document's unit, and the kernel reads all of it in
millimetres.

OUT.json, which must not exist, gets the comparison. The script prints its own
status line; trust that and the file, not the exit code of FreeCADCmd.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import kernel  # noqa: E402
from mechanical_cad import assemblies, flatten, jsonio, layout, solids, stepfile  # noqa: E402

REPORT_SCHEMA = 1


def identity(path, data):
    out = {"file": str(path), "sha256": stepfile.sha256_bytes(data), "bytes": len(data)}
    try:
        out["protocol"] = stepfile.header(data)["protocol"]
    except Exception as exc:                       # the comparison does not depend on the header
        out["header_error"] = str(exc)
    try:
        out["length_unit"] = stepfile.length_unit(data)
    except stepfile.StepFileError as exc:          # an assembly export may keep each document's own unit
        out["length_unit"] = None
        out["length_units"] = str(exc)
    return out


def compare(project, key, other, frame):
    top = flatten.find_root(project, key)
    scene, assets, suppressed = flatten.flatten(project, top.key)
    part_solids = {k: kernel.solids(kernel.read_step_visible(path)[0]) for k, path in assets}
    data = Path(other).read_bytes()
    shape, hidden = kernel.read_step_visible(other, data)
    check = solids.match(solids.expected(scene, part_solids, frame), kernel.solids(shape))
    by_part = {}
    for u in check["unmatched"]:
        rec = by_part.setdefault(u["part_id"], {"solids": 0, "nearest_solid_of_this_volume_mm": []})
        rec["solids"] += 1
        rec["nearest_solid_of_this_volume_mm"].append(u["nearest_solid_of_this_volume_mm"])
    other_id = identity(other, data)
    other_id["invisible_items_left_out"] = hidden
    return {
        "schema_version": REPORT_SCHEMA, "key": top.key, "root": top.path,
        "scene_sha256": assemblies.scene_sha256(scene),
        "frame": frame, "tool": kernel.tool(), "other": other_id,
        "parts": len(assets), "occurrences": len(solids.placed(scene)), "suppressed_left_out": suppressed,
        "same_assembly": check["same"], "unmatched_by_part": by_part, "check": check,
    }


def main(argv):
    argv = [a for a in argv if a != "--"]
    frame = "own"
    if "--frame" in argv:
        i = argv.index("--frame")
        if i + 1 >= len(argv):
            raise SystemExit(__doc__)
        frame = argv[i + 1]
        del argv[i:i + 2]
    if len(argv) != 4 or frame not in solids.FRAMES:
        raise SystemExit(__doc__)
    project_dir, key, other, out = Path(argv[0]), argv[1], Path(argv[2]), Path(argv[3])
    if out.exists():
        print(f"[compare_assembly_step] {out} exists; choose a new file")
        return 2
    project = layout.load(project_dir)
    try:
        report = compare(project, key, other, frame)
    except flatten.FlattenError as exc:
        for line in project.errors:
            print("ERROR  ", line)
        print(f"[compare_assembly_step] {exc}")
        return 2
    jsonio.write(out, report)
    c = report["check"]
    if report["same_assembly"]:
        print(f"[compare_assembly_step] the same assembly: {c['solids_matched']} of {c['solids_expected']} solid(s) where "
              f"the records put them, within {c['worst_position_deviation_mm']:.2g} mm; none unexpected")
        return 0
    print(f"[compare_assembly_step] DIFFERENT: {len(c['unmatched'])} of {c['solids_expected']} solid(s) are not where the "
          f"records put them; {len(c['found_but_not_expected'])} solid(s) of the file are not expected")
    return 1


def _is_entry():
    here = Path(__file__).resolve()
    return any(a and Path(a).resolve() == here for a in sys.argv[:2])


if _is_entry():
    if "--pass" in sys.argv:
        args = sys.argv[sys.argv.index("--pass") + 1:]
    else:
        args = [a for a in sys.argv[1:] if Path(a).resolve() != Path(__file__).resolve()]
    try:
        rc = main(args)
    except SystemExit as exc:
        print(exc)
        rc = 2
    except BaseException:
        import traceback
        traceback.print_exc()
        rc = 1
    print(f"[compare_assembly_step] exit status {rc}", flush=True)
    sys.exit(rc)
