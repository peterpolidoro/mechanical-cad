"""python3 -m mechanical_cad <command>

validate PROJECT            check a project repository against the layout
flatten PROJECT --out DIR   write the flattened scene.json and its assets
assemblies PROJECT          list the assemblies that can be built as one STEP file, and which are built
built PROJECT [KEY]         print the path of an assembly's built FreeCAD document, if it is current
check PROJECT               evaluate the checks of the authored parts, and what their interfaces say, against their facts
add-supplied PROJECT KEY FILE ...   put a STEP file from outside into the project as a supplied part
build-order PROJECT [KEY ...]       the authored parts, each after the parts it is built against
lock PROJECT                print the index vault-lock.json must equal
compare-scenes OLD NEW      are two flattened scenes the same assembly?
step-info FILE              what a STEP file says about itself
normalise-header IN OUT     rewrite a STEP header to fixed values
visible-only IN OUT         write a STEP file without the items it marks invisible
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import assemblies, compare, facts, flatten, interfaces, jsonio, layout, stepfile, supplied


def _validate(args):
    project = layout.load(args.project)
    report = project.report()
    if args.json:
        jsonio.write(args.json, report)
    for line in project.errors:
        print("ERROR  ", line)
    for line in project.findings:
        print("FINDING", line)
    counts = ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in report["counts"].items() if v)
    print(f"{args.project}: {counts or 'no components'}; {len(project.errors)} error(s), {len(project.findings)} finding(s)")
    return 0 if project.ok else 1


def _flatten(args):
    project = layout.load(args.project)
    if not project.ok:
        for line in project.errors:
            print("ERROR  ", line)
        print("the project does not validate; nothing written")
        return 1
    try:
        result = flatten.write(project, args.out, args.root)
    except flatten.FlattenError as exc:
        print("ERROR  ", exc)
        return 1
    print(json.dumps(result, indent=2))
    return 0


def _assemblies(args):
    project = layout.load(args.project)
    built_in = Path(args.dir) if args.dir else assemblies.default_dir(project.dir)
    try:
        rows = assemblies.listing(project, built_in)
    except flatten.FlattenError as exc:
        for line in project.errors:
            print("ERROR  ", line)
        print(f"{args.project}: {exc}")
        return 1
    if args.json:
        jsonio.write(args.json, {"schema_version": 1, "project": str(args.project), "built_in": str(built_in),
                                 "assemblies": rows})
    for line in assemblies.table(rows):
        print(line)
    built = sum(r["built"]["state"] == assemblies.CURRENT for r in rows)
    stale = sum(r["built"]["state"] == assemblies.OUT_OF_DATE for r in rows)
    print(f"{len(rows)} assembl{'y' if len(rows) == 1 else 'ies'}, {built} built and current"
          + (f", {stale} out of date (the records or the build changed since)" if stale else "")
          + f". Built files: {built_in / 'KEY.step'} and KEY.FCStd")
    return 0


def _built(args):
    """The path alone goes to standard output, so that a script can take it; anything else to standard error."""
    project = layout.load(args.project)
    built_in = Path(args.dir) if args.dir else assemblies.default_dir(project.dir)
    try:
        top = flatten.find_root(project, args.key)
        scene = flatten.flatten(project, top.key)[0]
    except flatten.FlattenError as exc:
        for line in project.errors:
            print("ERROR  ", line, file=sys.stderr)
        print(f"{args.project}: {exc}", file=sys.stderr)
        return 1
    found = assemblies.built(built_in, top.key, assemblies.scene_sha256(scene))
    if found["state"] != assemblies.CURRENT:
        print(f"{top.key}: {found['state']} in {built_in}; tools/assembly_step.py builds it", file=sys.stderr)
        return 1
    print(found["step"] if args.step else found["document"])
    return 0


def _check(args):
    project = layout.load(args.project)
    for line in project.errors:
        print("ERROR  ", line)
    failed = 0
    evaluated = 0
    parts = sorted(project.of(root="designs", kind="part"), key=lambda c: c.key)
    for comp in parts:
        checks_file = comp.dir / "checks.json"
        if not checks_file.is_file() and comp.interface is None:
            print(f"NO CHECKS {comp.path}")
            continue
        if comp.facts is None:
            print(f"FAIL    {comp.path}: no facts.json to check; {'measure' if comp.supplied else 'build'} the part")
            failed += 1
            continue
        try:
            results = facts.evaluate(jsonio.load(checks_file), comp.facts) if checks_file.is_file() else []
            if comp.interface is not None:      # what the interface says of the solid: a hole is empty, and so on
                results += facts.evaluate(interfaces.checks(comp.interface), comp.facts)
        except (facts.FactsError, jsonio.JsonError, KeyError) as exc:
            print(f"FAIL    {comp.path}/checks.json: {exc}")
            failed += 1
            continue
        for r in results:
            evaluated += 1
            if r["passed"]:
                print(f"PASS    {comp.path}: {r['id']}")
            else:
                failed += 1
                what = r["fact"] if "fact" in r else f"the point {json.dumps(r['point'])}"
                print(f"FAIL    {comp.path}: {r['id']}: {what} is {r['actual']}, expected {json.dumps(r['expected'])}")
    print(f"{args.project}: {len(parts)} authored part(s), {evaluated} check(s), {failed} failure(s), "
          f"{len(project.errors)} layout error(s)")
    return 0 if not failed and project.ok else 1


def _add_supplied(args):
    kind = "supplier" if args.supplier else "repository" if args.repository else "other"
    publishable = {"yes": True, "no": False, "unknown": None}[args.publishable]
    try:
        origin = supplied.origin_record(
            kind, args.retrieved, publishable, licence=args.licence, note=args.note,
            **({"supplier": args.supplier, "part_number": args.part_number, "url": args.url} if kind == "supplier" else
               {"repository": args.repository, "commit": args.commit, "path": args.path} if kind == "repository" else
               {"description": args.description, "url": args.url}))
        done = supplied.add(args.project, args.key, args.file, args.name or args.key, origin, replace=args.replace)
    except supplied.SuppliedError as exc:
        print(f"ERROR   {exc}")
        return 1
    print(json.dumps(done, indent=2))
    print(f"measure it next: FreeCADCmd tools/step_facts.py --pass {args.project} --only {args.key}")
    return 0


def _build_order(args):
    project = layout.load(args.project)
    try:
        order = layout.build_order(project, args.keys or None)
    except ValueError as exc:
        print(f"ERROR   {exc}")
        return 1
    unknown = sorted(set(args.keys) - set(order))
    if unknown:
        print(f"ERROR   not an authored part of {args.project}: {', '.join(unknown)}")
        return 1
    for key in order:
        comp = project.components[key]
        if not comp.supplied:           # a supplied part is not built
            print(key)
    return 0


def _lock(args):
    project = layout.load(args.project)
    sys.stdout.write(jsonio.dumps(layout.derive_lock(project)))
    return 0 if project.ok else 1


def _compare(args):
    old = jsonio.load(args.old, allow_bom=True)
    new = jsonio.load(args.new, allow_bom=True)
    part_map = jsonio.load(args.part_map) if args.part_map else None
    report = compare.compare(old, new, part_map, tuple(args.dropped or ()), other_export=args.other_export)
    if args.json:
        jsonio.write(args.json, report)
    for line in report["differences"][:args.limit]:
        print("DIFF", line)
    if len(report["differences"]) > args.limit:
        print(f"... and {len(report['differences']) - args.limit} more")
    summary = {k: report[k] for k in ("same", "counts", "largest_deviation", "fields_only_in_new")}
    summary["parts_whose_step_file_differs"] = len(report["assets_that_differ"])
    print(json.dumps(summary, indent=2))
    if args.other_export and report["assets_that_differ"]:
        print(f"{len(report['assets_that_differ'])} STEP file(s) differ and were not compared here; "
              "compare them by geometry with tools/compare_step_exports.py")
    return 0 if report["same"] else 1


def _step_info(args):
    print(json.dumps(stepfile.describe(args.file), indent=2))
    return 0


def _normalise(args):
    out = Path(args.out)
    if out.exists():
        print(f"ERROR   {out} exists")
        return 1
    data = Path(args.input).read_bytes()
    new = stepfile.normalise_header(data, args.name)
    out.write_bytes(new)
    print(json.dumps({"received_sha256": stepfile.sha256_bytes(data), "sha256": stepfile.sha256_bytes(new),
                      "data_sha256": stepfile.data_sha256(new), "changed": new != data}, indent=2))
    return 0


def _visible_only(args):
    out = Path(args.out)
    if out.exists():
        print(f"ERROR   {out} exists")
        return 1
    data = Path(args.input).read_bytes()
    try:
        left_out = stepfile.invisible_items(data)
        new = stepfile.visible_only(data)
    except stepfile.StepFileError as exc:
        print(f"ERROR   {args.input}: {exc}")
        return 1
    out.write_bytes(new)
    print(json.dumps({"invisible_items_left_out": len(left_out), "sha256": stepfile.sha256_bytes(new),
                      "changed": new != data}, indent=2))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python3 -m mechanical_cad", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="check a project repository against the layout")
    p.add_argument("project")
    p.add_argument("--json", help="also write the report to this file")
    p.set_defaults(func=_validate)

    p = sub.add_parser("flatten", help="write the flattened scene.json and its assets")
    p.add_argument("project")
    p.add_argument("--out", required=True, help="a new or empty directory")
    p.add_argument("--root", help="key of the assembly to flatten (default: the only unplaced assembly)")
    p.set_defaults(func=_flatten)

    p = sub.add_parser("assemblies", help="list the assemblies that can be built as one STEP file, and which are built")
    p.add_argument("project")
    p.add_argument("--dir", help="where the built files are (default: PROJECT/.cache/assemblies)")
    p.add_argument("--json", help="also write the list to this file")
    p.set_defaults(func=_assemblies)

    p = sub.add_parser("built", help="print the path of an assembly's built FreeCAD document, if it is current")
    p.add_argument("project")
    p.add_argument("key", nargs="?", help="key of the assembly (default: the only unplaced assembly)")
    p.add_argument("--step", action="store_true", help="print the path of the STEP file instead")
    p.add_argument("--dir", help="where the built files are (default: PROJECT/.cache/assemblies)")
    p.set_defaults(func=_built)

    p = sub.add_parser("check", help="evaluate the checks of the authored parts against their facts")
    p.add_argument("project")
    p.set_defaults(func=_check)

    p = sub.add_parser("add-supplied", help="put a STEP file from outside into the project as a supplied part",
                       description="The file is kept as it came, with its header normalised, in designs/parts/KEY/, "
                                   "and origin.json records where it came from. Say one origin: --supplier with "
                                   "--part-number, or --repository with --commit and --path, or --description.")
    p.add_argument("project")
    p.add_argument("key")
    p.add_argument("file", help="the STEP file, a path on this machine")
    p.add_argument("--name", help="the part's display name (default: the key)")
    p.add_argument("--supplier")
    p.add_argument("--part-number")
    p.add_argument("--repository", help="the repository the file is generated or kept in")
    p.add_argument("--commit", help="the commit of that repository the file was taken at")
    p.add_argument("--path", help="the file's path in that repository")
    p.add_argument("--description", help="where the file came from, when it is neither of the two")
    p.add_argument("--url")
    p.add_argument("--retrieved", required=True, help="the day the file was taken, YYYY-MM-DD")
    p.add_argument("--licence", help="the licence the file came under, if it names one")
    p.add_argument("--publishable", choices=("yes", "no", "unknown"), required=True,
                   help="may the file be in a public repository")
    p.add_argument("--note")
    p.add_argument("--replace", action="store_true", help="put this file in the place of the supplied part KEY")
    p.set_defaults(func=_add_supplied)

    p = sub.add_parser("build-order", help="the authored parts, each after the parts it is built against")
    p.add_argument("project")
    p.add_argument("keys", nargs="*", help="only these parts and what they are built against")
    p.set_defaults(func=_build_order)

    p = sub.add_parser("lock", help="print the index vault-lock.json must equal")
    p.add_argument("project")
    p.set_defaults(func=_lock)

    p = sub.add_parser("compare-scenes", help="are two flattened scenes the same assembly?")
    p.add_argument("old")
    p.add_argument("new")
    p.add_argument("--part-map", help="JSON object {new part id: old part id}")
    p.add_argument("--dropped", action="append", help="a field the new scene may lack (repeatable)")
    p.add_argument("--other-export", action="store_true",
                   help="the new scene is another export of the same Vault versions: STEP files that differ are "
                        "listed, not counted as differences")
    p.add_argument("--json", help="also write the report to this file")
    p.add_argument("--limit", type=int, default=40, help="differences to print (default 40)")
    p.set_defaults(func=_compare)

    p = sub.add_parser("step-info", help="what a STEP file says about itself")
    p.add_argument("file")
    p.set_defaults(func=_step_info)

    p = sub.add_parser("normalise-header", help="rewrite a STEP header to fixed values")
    p.add_argument("input")
    p.add_argument("out")
    p.add_argument("--name", default="part.step", help="the file name written into the header")
    p.set_defaults(func=_normalise)

    p = sub.add_parser("visible-only", help="write a STEP file without the items it marks invisible")
    p.add_argument("input")
    p.add_argument("out")
    p.set_defaults(func=_visible_only)

    args = parser.parse_args(argv)
    return args.func(args)
