#!/usr/bin/env python3
"""Acceptance test for converting an exporter package into the layout.

Runs the checks of docs/layout-proposal.md, "Acceptance test for the
conversion", and writes a report. Nothing in the package or in the converted
project is modified; everything it writes goes into --out, which must be new.

    python3 tools/conversion_acceptance.py \
        --package  PROJECT/references/enclosure      (what the exporter wrote) \
        --converted DIR                              (the layout written from it) \
        --docs-project DIR                           (a mechanical-docs project built on the package's scene) \
        --mechanical-docs ~/Repositories/.../mechanical-docs \
        --out NEW_DIR

Checks:

1. The converted project validates against the layout.
2. Every STEP file is byte-identical to the file it came from, and the
   exporter's receipt, kept with the project, still verifies them.
3. The scene flattened from the converted project equals the package's scene:
   same parts, assembly nodes and occurrences, compared under the ids the
   exporter used, transforms within tolerance.
4. The documentation project, with its manifests re-keyed to the new part ids
   by this script, loads in `mechanical_docs inspect` with the same counts,
   findings, world placements, steps and inventory as the original.

Checks 3 and 4 are independent of each other: 3 compares the two scene files,
4 compares what the documentation loader makes of them after its own unit and
frame handling.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mechanical_cad import compare, flatten, jsonio, layout, stepfile  # noqa: E402
from mechanical_cad import transforms as T  # noqa: E402

DOCS_MANIFESTS = ("inventory.json", "instructions.json", "supplement.json", "build-scope.json", "render.json")


def rekey_manifest(name, data, to_new):
    """Replace part ids in one mechanical-docs manifest. Returns (data, rows)."""
    data = copy.deepcopy(data)
    rows = 0
    if name == "inventory.json":
        for item in data.get("items", []):
            item["part_id"] = to_new[item["part_id"]]
            rows += 1
    elif name == "supplement.json":
        for item in data.get("items", []):
            inc = item.get("included_with")
            if isinstance(inc, dict) and inc.get("kind") == "scene_part":
                inc["id"] = to_new[inc["id"]]
            rows += 1
    elif name == "render.json":
        if isinstance(data.get("looks"), dict):
            data["looks"] = {to_new[k]: v for k, v in data["looks"].items()}
            rows = len(data["looks"])
    return data, rows


def leftovers(value, old_ids, found=None):
    """Any string equal to an old part id that is still somewhere in the data."""
    found = set() if found is None else found
    if isinstance(value, dict):
        for k, v in value.items():
            if k in old_ids:
                found.add(k)
            leftovers(v, old_ids, found)
    elif isinstance(value, list):
        for v in value:
            leftovers(v, old_ids, found)
    elif isinstance(value, str) and value in old_ids:
        found.add(value)
    return found


def run_inspect(mechanical_docs, project, out):
    proc = subprocess.run([sys.executable, "-B", "-m", "mechanical_docs", "inspect", str(project), "--json", str(out)],
                          cwd=mechanical_docs, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr)[-4000:]


def compare_inspect(old, new, to_old):
    """Differences between two inspect reports, part ids of `new` mapped back."""
    diffs = []
    back = lambda pid: to_old.get(pid, pid)  # noqa: E731
    if old["counts"] != new["counts"]:
        diffs.append(f"counts: {old['counts']} became {new['counts']}")
    for name in ("checks_passed", "not_checked"):
        if old.get(name) != new.get(name):
            diffs.append(f"{name} changed")
    of, nf = old.get("findings", {}), new.get("findings", {})
    if set(of) != set(nf):
        diffs.append(f"finding kinds: {sorted(of)} became {sorted(nf)}")
    oc = sorted((c["part_id"], tuple(sorted(c["occurrences"]))) for c in of.get("coincident_occurrences", []))
    nc = sorted((back(c["part_id"]), tuple(sorted(c["occurrences"]))) for c in nf.get("coincident_occurrences", []))
    if oc != nc:
        diffs.append(f"coincident occurrences: {oc} became {nc}")

    op = {p["id"]: p for p in old["parts"]}
    np_ = {back(p["id"]): p for p in new["parts"]}
    if set(op) != set(np_):
        diffs.append("the two reports do not list the same parts")
    for pid in sorted(set(op) & set(np_)):
        for f in ("name", "asset_units", "bytes", "sha256", "format"):
            if op[pid].get(f) != np_[pid].get(f):
                diffs.append(f"part {pid}: {f} was {op[pid].get(f)!r}, is {np_[pid].get(f)!r}")

    oo = {o["id"]: o for o in old["occurrences"]}
    no = {o["id"]: o for o in new["occurrences"]}
    if set(oo) != set(no):
        diffs.append("the two reports do not list the same occurrences")
    scale = max([1.0] + [abs(v) for o in oo.values() for v in T.translation(o["world"])])
    worst = [0.0, 0.0]
    for oid in sorted(set(oo) & set(no)):
        a, b = oo[oid], no[oid]
        if a["part_id"] != back(b["part_id"]) or a["parent_id"] != b["parent_id"] or a.get("path") != b.get("path"):
            diffs.append(f"occurrence {oid}: part or parent changed")
        rot, tra = T.deviation(a["world"], b["world"])
        worst = [max(worst[0], rot), max(worst[1], tra)]
        if rot > compare.ROTATION_TOL or tra > compare.RELATIVE_TOL * scale:
            diffs.append(f"occurrence {oid}: world placement differs (rotation {rot:.3g}, translation {tra:.3g} mm)")

    def steps(report):
        return [(s["id"], s.get("requires"), s.get("add")) for s in report.get("steps", [])]
    if steps(old) != steps(new):
        diffs.append("the steps differ")

    def inventory(report, mapper):
        return sorted((mapper(i["part_id"]), json.dumps({k: v for k, v in i.items() if k != "part_id"}, sort_keys=True))
                      for i in report.get("inventory", []))
    if inventory(old, lambda p: p) != inventory(new, back):
        diffs.append("the inventory rows differ")
    def scope(report, mapper):
        s = copy.deepcopy(report.get("build_scope"))
        if isinstance(s, dict):          # the summary counts per part; put both under the same ids
            if isinstance(s.get("part_quantities"), dict):
                s["part_quantities"] = {mapper(k): v for k, v in s["part_quantities"].items()}
            if isinstance(s.get("parts_deferred_entirely"), list):
                s["parts_deferred_entirely"] = sorted(mapper(k) for k in s["parts_deferred_entirely"])
        return s
    if scope(old, lambda p: p) != scope(new, back):
        diffs.append("build_scope differs")
    if old.get("inventory_status") != new.get("inventory_status"):
        diffs.append("inventory_status differs")
    if (old.get("supplement") or {}).get("rows") != (new.get("supplement") or {}).get("rows"):
        diffs.append("the number of supplement rows differs")
    return diffs, {"world_rotation": worst[0], "world_translation_mm": worst[1]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--package", required=True)
    ap.add_argument("--converted", required=True)
    ap.add_argument("--docs-project", help="mechanical-docs project built on the package's scene (optional)")
    ap.add_argument("--mechanical-docs", help="mechanical-docs checkout (needed with --docs-project)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    package, converted, out = Path(args.package), Path(args.converted), Path(args.out)
    if out.exists():
        print(f"{out} exists; choose a new directory")
        return 2
    out.mkdir(parents=True)
    report = {"package": str(package), "converted": str(converted), "checks": {}, "not_run": []}

    def check(name, passed, **detail):
        report["checks"][name] = dict(passed=bool(passed), **detail)
        print(("PASS " if passed else "FAIL ") + name + ("" if passed else f": {json.dumps(detail)[:600]}"))

    # 1. the layout
    project = layout.load(converted)
    check("1 layout validates", project.ok, errors=project.errors, findings=len(project.findings),
          counts=project.report()["counts"])
    if not project.ok:
        jsonio.write(out / "acceptance-report.json", report)
        return 1

    # 2. bytes and the exporter's receipt
    problems = []
    parts = project.of(root="references", kind="part")
    runs = set()
    for comp in parts:
        export = comp.source["export"]
        runs.add(export["run"])
        original = package / export["package_path"]
        if not original.is_file() or original.read_bytes() != comp.step_path.read_bytes():
            problems.append(f"{comp.path}: part.step is not byte-identical to {export['package_path']}")
        receipt = jsonio.load(converted / "references" / "receipts" / export["run"] / "export-receipt.json", allow_bom=True)
        if receipt["files"].get(export["package_path"], {}).get("sha256") != comp.step_sha256:
            problems.append(f"{comp.path}: the kept export receipt does not verify part.step")
    kept = 0
    for run in sorted(runs):
        d = converted / "references" / "receipts" / run
        receipt = jsonio.load(d / "export-receipt.json", allow_bom=True)
        for rel, rec in receipt["files"].items():
            f = d / rel
            if f.is_file():
                kept += 1
                if stepfile.sha256_file(f) != rec["sha256"]:
                    problems.append(f"references/receipts/{run}/{rel}: not the bytes the receipt names")
    check("2 STEP files and records are the exporter's bytes", not problems, problems=problems, parts=len(parts),
          record_files_verified=kept)

    # 3. the flattened scene against the exporter's
    result = flatten.write(project, out / "flattened")
    old_scene = jsonio.load(package / "scene.json", allow_bom=True)
    new_scene = jsonio.load(out / "flattened" / "scene.json")
    to_old = {c.key: c.source["export"]["package_id"] for c in parts}
    jsonio.write(out / "part-map.json", to_old)
    cmp_report = compare.compare(old_scene, new_scene, to_old)
    jsonio.write(out / "scene-comparison.json", cmp_report)
    check("3 flattened scene equals the exporter's scene", cmp_report["same"], counts=cmp_report["counts"],
          largest_deviation=cmp_report["largest_deviation"], fields_only_in_new=cmp_report["fields_only_in_new"],
          differences=cmp_report["differences"][:20], flattened=result)

    # 4. the documentation project
    if not args.docs_project or not args.mechanical_docs:
        report["not_run"].append("4 documentation project: no --docs-project and --mechanical-docs given")
    else:
        src = Path(args.docs_project)
        docs = out / "docs-project"
        shutil.copytree(out / "flattened", docs)
        to_new = {v: k for k, v in to_old.items()}
        rows, problems = {}, []
        for name in DOCS_MANIFESTS:
            if not (src / name).is_file():
                continue
            data = jsonio.load(src / name, allow_bom=True)
            try:
                new, n = rekey_manifest(name, data, to_new)
            except KeyError as exc:
                problems.append(f"{name}: names a part the converted project does not have: {exc}")
                continue
            left = leftovers(new, set(to_new))
            if left:
                problems.append(f"{name}: {len(left)} old part id(s) were not re-keyed")
            if name == "inventory.json" and len(new.get("items", [])) != len(data.get("items", [])):
                problems.append("inventory.json: rows were lost")
            rows[name] = n
            jsonio.write(docs / name, new)
        code_old, log_old = run_inspect(args.mechanical_docs, src, out / "inspect-original.json")
        code_new, log_new = run_inspect(args.mechanical_docs, docs, out / "inspect-converted.json")
        (out / "inspect-original.log").write_text(log_old)
        (out / "inspect-converted.log").write_text(log_new)
        if code_old or code_new:
            problems.append(f"mechanical_docs inspect exited {code_old} (original) and {code_new} (converted)")
            check("4 documentation project loads the same", False, problems=problems, log=log_new[-1500:])
        else:
            old_r = json.loads((out / "inspect-original.json").read_text())
            new_r = json.loads((out / "inspect-converted.json").read_text())
            diffs, worst = compare_inspect(old_r, new_r, to_old)
            check("4 documentation project loads the same", not problems and not diffs, problems=problems,
                  differences=diffs[:20], counts=new_r["counts"], findings=sorted(new_r.get("findings", {})),
                  manifests_rekeyed=rows, largest_deviation=worst)

    report["passed"] = all(c["passed"] for c in report["checks"].values())
    report["python"] = sys.version.split()[0]
    report["cwd"] = os.getcwd()
    jsonio.write(out / "acceptance-report.json", report)
    print(("ACCEPTED" if report["passed"] else "NOT ACCEPTED") + (f"; not run: {report['not_run']}" if report["not_run"] else ""))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
