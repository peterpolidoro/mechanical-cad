"""Say whether some children of an assembly fit among the others: interference, contact and clearance.

    FreeCADCmd tools/fit_check.py --pass PROJECT KEY -- --subject NAME [--subject NAME ...]
                                                       [-- --clearance MM] [-- --out FILE]
    FreeCADCmd tools/fit_check.py --pass PROJECT KEY -- --subjects "NAME,NAME" ...

`--subjects` takes several names in one argument, separated by commas: the
form a Makefile can hand on whole, since a name may hold spaces.

FreeCADCmd reads dashed options itself, even after --pass; put a bare `--`
before this script's own options.

KEY is an assembly of the project, usually an authored one that places what
is mirrored from Vault together with what is being designed. Each NAME is the
name of one of its direct children, a part or a sub-assembly: a subject. KEY
is flattened, each part file is read once, without the items it marks
invisible, and every solid of every subject is compared with every solid of
the assembly that is not in the same subject, other subjects included:

    interference  the two solids share volume (more than VOLUME_TOL_MM3)
    contact       they touch and share none
    close         they are apart by less than --clearance (default 5 mm)

Two solids whose bounding boxes are further apart than the clearance are not
compared further; the rest are measured by the kernel (the smallest distance,
and the common volume where that is zero). Solids of one subject are not
compared with each other: what a sub-assembly does inside itself is its own
affair, and a part that is its own subject has one occurrence.

Printed: a line per finding, the smallest clearance that is left, and a status
line. `--out FILE` writes the same as JSON, without a timestamp, so that
checking an unchanged assembly again writes the same bytes. The exit status is
0 when nothing interferes and 1 when something does; FreeCADCmd does not hand
it on reliably, so read the status line.

Distances and common volumes are FreeCAD's, in millimetres, in the assembly's
own frame. A contact is reported, not judged: parts that are bolted together
touch.

Solids are what is compared. A part whose file holds faces and no solid, as a
supplier's model of surfaces does, is not compared with anything; the tool
names such parts, and the record has them as `parts_without_a_solid`.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import FreeCAD as App  # noqa: E402

import kernel  # noqa: E402
from mechanical_cad import assemblies, flatten, jsonio, layout, solids  # noqa: E402

REPORT_SCHEMA = 1
VOLUME_TOL_MM3 = 1e-3       # less common volume than this is a contact
CONTACT_TOL_MM = 1e-6       # a smallest distance below this is zero
DEFAULT_CLEARANCE_MM = 5.0


def options(argv):
    argv = [a for a in argv if a != "--"]
    opts = {"subjects": [], "clearance": DEFAULT_CLEARANCE_MM, "out": None}
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--subject" and i + 1 < len(argv):
            opts["subjects"].append(argv[i + 1])
            i += 1
        elif a == "--subjects" and i + 1 < len(argv):
            opts["subjects"].extend(name.strip() for name in argv[i + 1].split(",") if name.strip())
            i += 1
        elif a == "--clearance" and i + 1 < len(argv):
            opts["clearance"] = float(argv[i + 1])
            i += 1
        elif a == "--out" and i + 1 < len(argv):
            opts["out"] = argv[i + 1]
            i += 1
        elif a.startswith("--"):
            raise SystemExit(__doc__)
        else:
            positional.append(a)
        i += 1
    if len(positional) != 2 or not opts["subjects"] or opts["clearance"] < 0:
        raise SystemExit(__doc__)
    return Path(positional[0]), positional[1], opts


def box_gap(a, b):
    """How far apart two bounding boxes are at least: 0 when they overlap."""
    gaps = (max(a.XMin - b.XMax, b.XMin - a.XMax, 0.0), max(a.YMin - b.YMax, b.YMin - a.YMax, 0.0),
            max(a.ZMin - b.ZMax, b.ZMin - a.ZMax, 0.0))
    return (gaps[0] ** 2 + gaps[1] ** 2 + gaps[2] ** 2) ** 0.5


def placed_solids(scene, shapes):
    """Every solid of every placed occurrence, where the scene puts it:
    [{"occurrence", "solid" (its number in the part file), "top" (the direct child it belongs to), "shape", "box"}]."""
    out = []
    for occurrence in solids.placed(scene):
        matrix = App.Matrix(*[float(v) for row in occurrence["transform_world"] for v in row])
        for number, solid in enumerate(shapes[occurrence["part_id"]].Solids):
            shape = solid.copy()
            shape.transformShape(matrix)
            out.append({"occurrence": occurrence["id"], "solid": number, "top": occurrence["id"].split("/", 1)[0],
                        "shape": shape, "box": shape.BoundBox})
    return out


def compare(subject_solids, other_solids, clearance):
    """(findings, pairs measured, the closest pair that does not touch or None)."""
    findings, measured, closest = [], 0, None
    for a in subject_solids:
        for b in other_solids:
            if box_gap(a["box"], b["box"]) > clearance:
                continue
            measured += 1
            distance = a["shape"].distToShape(b["shape"])[0]
            pair = {"subject": a["occurrence"], "subject_solid": a["solid"], "other": b["occurrence"], "other_solid": b["solid"]}
            if distance <= CONTACT_TOL_MM:
                volume = a["shape"].common(b["shape"]).Volume
                if volume > VOLUME_TOL_MM3:
                    findings.append(dict(pair, kind="interference", common_volume_mm3=volume))
                else:
                    findings.append(dict(pair, kind="contact"))
                continue
            if closest is None or distance < closest["distance_mm"]:
                closest = dict(pair, distance_mm=distance)
            if distance < clearance:
                findings.append(dict(pair, kind="close", distance_mm=distance))
    return findings, measured, closest


def main(argv):
    project_dir, key, opts = options(argv)
    project = layout.load(project_dir)
    try:
        top = flatten.find_root(project, key)
        scene, assets, _ = flatten.flatten(project, top.key)
    except flatten.FlattenError as exc:
        for line in project.errors:
            print("ERROR  ", line)
        print(f"[fit_check] {exc}")
        return 2
    children = sorted({o["id"].split("/", 1)[0] for o in solids.placed(scene)})
    unknown = [s for s in opts["subjects"] if s not in children]
    if unknown:
        print(f"[fit_check] {top.key} has no child named {', '.join(repr(u) for u in unknown)}; its children: {', '.join(children)}")
        return 2
    subjects = sorted(set(opts["subjects"]))

    shapes = {part: kernel.read_step_visible(path)[0] for part, path in assets}
    bare = sorted(part for part, shape in shapes.items() if not shape.Solids)
    if bare:
        print(f"[fit_check] {len(bare)} part(s) have no solid and are not compared: {', '.join(bare)}")
    everything = placed_solids(scene, shapes)
    findings, measured, closest = [], 0, None
    for position, subject in enumerate(subjects):
        mine = [s for s in everything if s["top"] == subject]
        # another subject is compared once, from the subject that comes first
        others = [s for s in everything if s["top"] != subject and s["top"] not in subjects[:position]]
        found, count, near = compare(mine, others, opts["clearance"])
        findings += found
        measured += count
        if near and (closest is None or near["distance_mm"] < closest["distance_mm"]):
            closest = near
    order = {"interference": 0, "contact": 1, "close": 2}
    findings.sort(key=lambda f: (order[f["kind"]], f["subject"], f["subject_solid"], f["other"], f["other_solid"]))
    counts = {kind: sum(1 for f in findings if f["kind"] == kind) for kind in order}

    for f in findings:
        what = {"interference": lambda: f"shares {f['common_volume_mm3']:.3f} mm3 with",
                "contact": lambda: "touches",
                "close": lambda: f"is {f['distance_mm']:.3f} mm from"}[f["kind"]]()
        print(f"{f['kind'].upper():13s} {f['subject']} [{f['subject_solid']}] {what} {f['other']} [{f['other_solid']}]")
    if closest:
        print(f"[fit_check] the closest pair that does not touch: {closest['distance_mm']:.3f} mm, "
              f"{closest['subject']} [{closest['subject_solid']}] and {closest['other']} [{closest['other_solid']}]")
    else:
        print(f"[fit_check] no pair within {opts['clearance']:g} mm that does not touch")
    report = {"schema_version": REPORT_SCHEMA, "key": top.key, "scene_sha256": assemblies.scene_sha256(scene),
              "subjects": subjects, "clearance_mm": opts["clearance"], "tool": kernel.tool(),
              "solids": {"subjects": sum(1 for s in everything if s["top"] in subjects),
                         "others": sum(1 for s in everything if s["top"] not in subjects)},
              "pairs_measured": measured, "counts": counts, "closest_apart": closest, "findings": findings}
    if bare:
        report["parts_without_a_solid"] = bare
    if opts["out"]:
        out = Path(opts["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        jsonio.write(out, report)
    print(f"[fit_check] {top.key}: {', '.join(subjects)} against the rest: {report['solids']['subjects']} and "
          f"{report['solids']['others']} solids, {measured} pair(s) measured; {counts['interference']} interference(s), "
          f"{counts['contact']} contact(s), {counts['close']} closer than {opts['clearance']:g} mm")
    return 1 if counts["interference"] else 0


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
    print(f"[fit_check] exit status {rc}", flush=True)
    sys.exit(rc)
