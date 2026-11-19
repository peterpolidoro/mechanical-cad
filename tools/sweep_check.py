"""Walk a joint through its range and say where what it moves runs into something. A draft, as the joints are.

    FreeCADCmd tools/sweep_check.py --pass PROJECT KEY -- --joint NAME [-- --steps N] [-- --refine N]
                                    [-- --pose NAME] [-- --at "JOINT=VALUE,JOINT=VALUE"]
                                    [-- --clearance MM] [-- --out FILE] [-- --motion FILE]

FreeCADCmd reads dashed options itself, even after --pass; put a bare `--`
before each of this script's own options.

KEY is an assembly of the project and NAME a joint of the project's
`motion.toml` (mechanical_cad/motion.py; a draft that the layout does not
know yet, read from PROJECT/motion.toml or from `--motion FILE`). The
assembly is flattened and the joint is set to `--steps` values from its lower
limit to its upper (13 by default), the other joints staying at 0, or where
`--pose` and `--at` put them. A joint that follows NAME, as a gear follows
the gear it meshes with, goes with it. At every step each solid that the
joint moves is compared with every solid that stands still, and what NAME
moves with what its followers move, as tools/fit_check.py compares a subject
with the rest: interference, contact, and the nearest pair that does not
touch among those whose boxes are within `--clearance` (1 mm by default).

An assembly is seldom free of interference where it stands: a thread is
modelled as a cylinder in a hole that is too small for it, a shaft is pressed
into its bearing. So the assembled position is measured first, with every
joint at 0, and a step is blocked only by an interference that is not there
as assembled, or that has grown since by more than a fiftieth. What
interferes as assembled is counted and named once.

Printed: the assembled position, a line per step, and the stretch that is free around the
step nearest 0, with what blocks it at either end. Between the last free step
and the first blocked one the limit is then looked for by halving, `--refine`
times (5 by default; 0 leaves it at the steps), and the stretch is given to
that. `--out FILE` writes the same as JSON, without a timestamp. The exit
status is 0 when every step is free and 1 when one is blocked; FreeCADCmd does
not hand it on reliably, so read the status line.

Solids are what is compared, as in tools/fit_check.py: a part whose file
holds faces and no solid is not seen, and the tool names such parts.

This samples. Something thinner than the distance a step moves it can be
passed through between two steps without being seen; take more steps where
that matters. A free range is not a statement about the made thing: it says
that the solids of the model, as they are placed, do not share volume.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fit_check  # noqa: E402
import kernel  # noqa: E402
from mechanical_cad import assemblies, flatten, jsonio, layout, motion, solids  # noqa: E402

REPORT_SCHEMA = 1
DEFAULT_STEPS = 13
DEFAULT_REFINE = 5
DEFAULT_CLEARANCE_MM = 1.0
GROWN = 1.02                # an interference of the assembled position counts against a step when it is this much larger


def options(argv):
    argv = [a for a in argv if a != "--"]
    opts = {"joint": None, "steps": DEFAULT_STEPS, "refine": DEFAULT_REFINE, "pose": None, "at": None,
            "clearance": DEFAULT_CLEARANCE_MM, "out": None, "motion": None}
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--") and a[2:] in opts and i + 1 < len(argv):
            opts[a[2:]] = argv[i + 1]
            i += 1
        elif a.startswith("--"):
            raise SystemExit(__doc__)
        else:
            positional.append(a)
        i += 1
    try:
        opts["steps"], opts["refine"], opts["clearance"] = int(opts["steps"]), int(opts["refine"]), float(opts["clearance"])
    except ValueError:
        raise SystemExit(__doc__) from None
    if len(positional) != 2 or not opts["joint"] or opts["steps"] < 2 or opts["refine"] < 0 or opts["clearance"] < 0:
        raise SystemExit(__doc__)
    return Path(positional[0]), positional[1], opts


def pair(finding):
    return finding["subject"], finding["subject_solid"], finding["other"], finding["other_solid"]


def said(finding):
    return (f"{finding['subject']} [{finding['subject_solid']}] shares {finding['common_volume_mm3']:.3f} mm3 with "
            f"{finding['other']} [{finding['other_solid']}]")


class Walk:
    """One joint of one scene, ready to be put anywhere in its range and measured there."""

    def __init__(self, scene, shapes, derived, name, base, clearance):
        self.scene, self.shapes, self.derived, self.name, self.base, self.clearance = scene, shapes, derived, name, base, clearance
        led = [name] + sorted(j for j, spec in derived["joints"].items() if spec.get("follows", {}).get("joint") == name)
        # what goes together is one group: what the joint moves, what each follower moves, what both do
        self.group = {i: tuple(j for j in led if j in chain) for i, chain in derived["moved"].items()}
        self.group = {i: g for i, g in self.group.items() if g}
        placed = {o["id"] for o in solids.placed(scene)}
        self.moving = sorted(i for i in self.group if i in placed)
        self.others = self.standing(base)
        # the assembled position, every joint at 0: what interferes there is not held against the motion
        self.rest = self.measure(0.0, {}, self.standing({}) if base else self.others)
        self.at_rest = {pair(f): f["common_volume_mm3"] for f in self.rest["interferences"]}

    def standing(self, base):
        """The solids that this joint does not move, where the other joints at `base` put them."""
        still = motion.posed(self.derived, self.scene, motion.values(self.derived, given=base))
        return fit_check.placed_solids(dict(still, occurrences=[o for o in still["occurrences"]
                                                                if o["id"] not in self.group]), self.shapes)

    def measure(self, value, base=None, others=None):
        """What is found with the joint at `value`: {"interferences", "contacts", "closest", "measured"}. The
        other joints are where the walk has them, unless `base` and the solids that stand there are given."""
        at = motion.values(self.derived, given={**(self.base if base is None else base), self.name: value})
        there = motion.posed(self.derived, self.scene, at)
        mine = fit_check.placed_solids(dict(there, occurrences=[o for o in there["occurrences"] if o["id"] in self.group]),
                                       self.shapes)
        found, measured, closest = fit_check.compare(mine, self.others if others is None else others, self.clearance)
        groups = sorted(set(self.group.values()))
        for n, first in enumerate(groups):                  # what the joint moves against what its followers move
            for second in groups[n + 1:]:
                more, count, near = fit_check.compare([s for s in mine if self.group[s["occurrence"]] == first],
                                                      [s for s in mine if self.group[s["occurrence"]] == second],
                                                      self.clearance)
                found += more
                measured += count
                if near and (closest is None or near["distance_mm"] < closest["distance_mm"]):
                    closest = near
        order = lambda f: pair(f)                           # noqa: E731
        return {"interferences": sorted((f for f in found if f["kind"] == "interference"), key=order),
                "contacts": sum(f["kind"] == "contact" for f in found), "closest": closest, "measured": measured}

    def blocking(self, found):
        """The interferences that are not those of the assembled position."""
        return [f for f in found["interferences"]
                if f["common_volume_mm3"] > self.at_rest.get(pair(f), 0.0) * GROWN + fit_check.VOLUME_TOL_MM3]

    def limit(self, free, blocked, by, times):
        """Between a value that is free and one that is blocked by `by`, the last free value found by halving
        `times` times, and what blocks just beyond it."""
        for _ in range(times):
            middle = (free + blocked) / 2
            found = self.blocking(self.measure(middle))
            if found:
                blocked, by = middle, found
            else:
                free = middle
        return free, blocked, by


def main(argv):
    project_dir, key, opts = options(argv)
    project = layout.load(project_dir)
    try:
        top = flatten.find_root(project, key)
        scene, assets, _ = flatten.flatten(project, top.key)
        derived = motion.of_scene(project, scene, top.key, Path(opts["motion"]) if opts["motion"] else None)
        base = motion.given(opts["at"])
        if opts["pose"]:
            base = {**derived["poses"].get(opts["pose"], {}), **base}
            motion.values(derived, opts["pose"])            # says so when there is no such pose
        names = [j for j in derived["joints"] if j == opts["joint"]] or \
                [j for j in derived["joints"] if j.split("@", 1)[0] == opts["joint"]]
        if len(names) != 1:
            raise motion.MotionError(f"{top.key} has " + (f"the joint {opts['joint']} in several places; name one: "
                                                          + ", ".join(sorted(names)) if names else
                                                          f"no joint {opts['joint']!r}; its joints: "
                                                          + (", ".join(sorted(derived["joints"])) or "none")))
        name = names[0]
        joint = derived["joints"][name]
        if "follows" in joint:
            raise motion.MotionError(f"{name} follows {joint['follows']['joint']}; walk that joint")
        base = {j: v for j, v in motion.values(derived, given=base).items()
                if v and j != name and "follows" not in derived["joints"][j]}
    except (flatten.FlattenError, motion.MotionError) as exc:
        for line in project.errors:
            print("ERROR  ", line)
        print(f"[sweep_check] {exc}")
        return 2

    shapes = {part: kernel.read_step_visible(path)[0] for part, path in assets}
    bare = sorted(part for part, shape in shapes.items() if not shape.Solids)
    if bare:
        print(f"[sweep_check] {len(bare)} part(s) have no solid and are not compared: {', '.join(bare)}")
    walk = Walk(scene, shapes, derived, name, base, opts["clearance"])
    if not walk.moving:
        print(f"[sweep_check] {name} moves nothing that {top.key} shows")
        return 2
    unit = joint["unit"]
    print(f"[sweep_check] {name} of {top.key}: {joint['kind']}, {joint['lower']:g} to {joint['upper']:g} {unit}; "
          f"{len(walk.moving)} occurrence(s) move, {sum(len(g) > 1 or g[0] != name for g in walk.group.values())} of them "
          "with a joint that follows it" + (f"; the other joints at {', '.join(f'{j} = {v:g}' for j, v in sorted(base.items()))}"
                                           if base else ""))
    print(f"as assembled, every joint at 0: {len(walk.rest['interferences'])} interference(s) and "
          f"{walk.rest['contacts']} contact(s) between what moves and the rest" + (":" if walk.rest["interferences"] else ""))
    for f in walk.rest["interferences"]:
        print(f"    {said(f)}")

    values = motion.steps(joint, opts["steps"])
    rows = []
    for value in values:
        found = walk.measure(value) if value or base else walk.rest
        by = walk.blocking(found)
        rows.append({"value": value, "free": not by, "blocked_by": by, "contacts": found["contacts"],
                     "interferences_as_assembled": len(found["interferences"]) - len(by), "closest_apart": found["closest"],
                     "pairs_measured": found["measured"]})
        near = found["closest"]
        print(f"{value:9.3f} {unit}  " + (
            "free" + (f"; nearest {near['distance_mm']:.3f} mm: {near['subject']} [{near['subject_solid']}] and "
                      f"{near['other']} [{near['other_solid']}]" if near else f"; nothing nearer than {opts['clearance']:g} mm "
                      "that does not touch")
            if not by else f"BLOCKED: {said(by[0])}" + (f"; and {len(by) - 1} more" if len(by) > 1 else "")))

    start = min(range(len(rows)), key=lambda n: (abs(rows[n]["value"]), n))
    free = None
    if rows[start]["free"]:
        low = high = start
        while low > 0 and rows[low - 1]["free"]:
            low -= 1
        while high < len(rows) - 1 and rows[high + 1]["free"]:
            high += 1
        free = {"from": rows[low]["value"], "to": rows[high]["value"], "blocked_below": None, "blocked_above": None}
        for side, at, beyond in (("blocked_below", low, low - 1), ("blocked_above", high, high + 1)):
            if 0 <= beyond < len(rows):
                last, first, by = walk.limit(rows[at]["value"], rows[beyond]["value"], rows[beyond]["blocked_by"],
                                             opts["refine"])
                free["from" if side == "blocked_below" else "to"] = last
                free[side] = {"value": first, "by": by}
    blocked = [r for r in rows if not r["free"]]
    step = values[1] - values[0]
    if free:
        ends = []
        for side, word in (("blocked_below", "below"), ("blocked_above", "above")):
            if free[side]:
                ends.append(f"{word} that, at {free[side]['value']:.3f}, {said(free[side]['by'][0])}")
        print(f"[sweep_check] free from {free['from']:.3f} to {free['to']:.3f} {unit}"
              + ("; " + "; ".join(ends) if ends else ", the whole range walked"))
    else:
        print(f"[sweep_check] blocked at the step nearest the assembled position, {rows[start]['value']:g} {unit}")
    report = {"schema_version": REPORT_SCHEMA, "draft": "the joints are a draft that the layout does not know yet",
              "key": top.key, "scene_sha256": assemblies.scene_sha256(scene), "motion": derived["source"],
              "joint": name, "kind": joint["kind"], "unit": unit, "lower": joint["lower"], "upper": joint["upper"],
              "other_joints_at": base, "followers": sorted(j for j, spec in derived["joints"].items()
                                                           if spec.get("follows", {}).get("joint") == name),
              "clearance_mm": opts["clearance"], "tool": kernel.tool(),
              "solids": {"moving": sum(len(shapes[o["part_id"]].Solids) for o in solids.placed(scene) if o["id"] in walk.group),
                         "others": len(walk.others)},
              "at_rest": {"interferences": walk.rest["interferences"], "contacts": walk.rest["contacts"]},
              "steps": rows, "step": step, "refined": opts["refine"], "free": free}
    if bare:
        report["parts_without_a_solid"] = bare
    if opts["out"]:
        out = Path(opts["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        jsonio.write(out, report)
    print(f"[sweep_check] {name}: {len(rows)} step(s) of {step:g} {unit}, {len(rows) - len(blocked)} free and "
          f"{len(blocked)} blocked; {report['solids']['moving']} solid(s) moving against {report['solids']['others']}")
    return 1 if blocked else 0


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
    print(f"[sweep_check] exit status {rc}", flush=True)
    sys.exit(rc)
