"""Compare other exports of a project's imported parts with the files it tracks.

    FreeCADCmd tools/compare_step_exports.py --pass PROJECT MAP.json OUT.json

MAP.json is an object {part key: path of a STEP file}. Each file is measured
as the layout measures a part (without the items it marks invisible) and its
fingerprint is compared with the `facts.json` of references/parts/<key>, which
must describe the tracked part.step. Nothing in the project is written.

This is how an export in another protocol, or from another session, is shown
to be the same geometry: an AP242 export of a part whose tracked file is AP214
differs in every byte and is the same part when the fingerprints agree.

OUT.json, which must not exist, gets one record per key and a summary. The
script prints its own status line; trust that and the file, not the exit code
of FreeCADCmd.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import kernel  # noqa: E402
from mechanical_cad import facts, jsonio, layout, stepfile  # noqa: E402

FINGERPRINT = ("solids", "volume_mm3", "area_mm2", "center_of_mass_mm", "bounding_box_mm")


def identity(data):
    head = stepfile.header(data)
    return {"sha256": stepfile.sha256_bytes(data), "data_sha256": stepfile.data_sha256(data), "bytes": len(data),
            "protocol": head["protocol"], "header_normalised": stepfile.is_normalised(data),
            "length_unit": stepfile.length_unit(data)}


def compare(project, mapping):
    parts = {c.key: c for c in project.of(root="references", kind="part")}
    records, counts = {}, {"same": 0, "different": 0, "failed": 0}
    for key in sorted(mapping):
        rec = {"file": str(mapping[key])}
        records[key] = rec
        try:
            comp = parts.get(key)
            if comp is None:
                raise ValueError("the project has no imported part of this key")
            if not comp.facts or comp.facts.get("step", {}).get("sha256") != comp.step_sha256:
                raise ValueError("the part has no facts.json that describes its part.step; measure it first")
            data = Path(mapping[key]).read_bytes()
            rec["tracked"] = identity(comp.step_path.read_bytes())
            rec["other"] = identity(data)
            measured, hidden = kernel.measure_step(mapping[key], data)
            rec["other"]["invisible_items_left_out"] = hidden
            rec["tracked"]["invisible_items_left_out"] = comp.facts.get("invisible_items", 0)
            if not measured["valid"]:
                raise ValueError("the kernel does not find the other file's geometry valid")
            rec["same_bytes"] = rec["other"]["sha256"] == rec["tracked"]["sha256"]
            rec["same_data_section"] = rec["other"]["data_sha256"] == rec["tracked"]["data_sha256"]
            rec["same_geometry"], rec["differences"] = facts.compare(comp.facts, measured)
            rec["fingerprint"] = {"tracked": {f: comp.facts[f] for f in FINGERPRINT}, "other": {f: measured[f] for f in FINGERPRINT}}
            counts["same" if rec["same_geometry"] else "different"] += 1
        except Exception as exc:        # one unreadable file must not hide the others
            rec["error"] = str(exc)
            counts["failed"] += 1
        state = "FAILED: " + rec["error"] if "error" in rec else ("same geometry" if rec["same_geometry"] else
                                                                  "DIFFERENT: " + "; ".join(rec["differences"]))
        print(f"[compare_step_exports] {key}: {state}", flush=True)
    not_compared = sorted(set(parts) - set(mapping))
    return {"schema_version": 1, "tool": kernel.measuring_tool(), "tolerances": {"relative": facts.RELATIVE_TOL, "length_mm": facts.LENGTH_TOL_MM},
            "summary": dict(counts, compared=len(mapping), parts_in_project=len(parts), not_compared=not_compared),
            "parts": records}


def main(argv):
    argv = [a for a in argv if a != "--"]
    if len(argv) != 3:
        raise SystemExit(__doc__)
    project_dir, map_file, out = Path(argv[0]), Path(argv[1]), Path(argv[2])
    if out.exists():
        print(f"[compare_step_exports] {out} exists; choose a new file")
        return 2
    project = layout.load(project_dir)
    mapping = jsonio.load(map_file)
    if not isinstance(mapping, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
        print("[compare_step_exports] the map must be an object {part key: path}")
        return 2
    report = compare(project, mapping)
    jsonio.write(out, report)
    s = report["summary"]
    print(f"[compare_step_exports] {s['compared']} compared: {s['same']} the same geometry, {s['different']} different, "
          f"{s['failed']} failed; {len(s['not_compared'])} part(s) of the project not compared")
    return 0 if s["compared"] and not s["different"] and not s["failed"] else 1


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
    except BaseException:
        import traceback
        traceback.print_exc()
        rc = 1
    print(f"[compare_step_exports] exit status {rc}", flush=True)
    sys.exit(rc)
