"""Measure the imported STEP files of a project and write their facts.json.

    FreeCADCmd tools/step_facts.py --pass PROJECT [-- --force] [-- --only KEY ...]

FreeCADCmd reads dashed options itself, even after --pass; put a bare `--`
before this script's own options.

Writes references/parts/<key>/facts.json for every imported part whose facts
are missing or describe a different part.step, a different unit or a different
tool or kernel version. A file that marks items invisible (the hidden bodies of
an AP242 export) is measured without them, and the facts say how many were
left out. With --force every part is measured again. A file
whose measurement has not changed is not rewritten.

The facts of authored parts under designs/ are written by tools/build_part.py.

FreeCADCmd prints an uncaught exception and still exits 0, so this script
prints its own status line; trust that and the files, not the exit code.
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import kernel  # noqa: E402
from mechanical_cad import jsonio, layout, stepfile  # noqa: E402


def facts_for(comp, tool):
    data = comp.step_path.read_bytes()
    out = {"schema_version": layout.SCHEMA_VERSION, "key": comp.key,
           "step": {"sha256": stepfile.sha256_bytes(data), "data_sha256": stepfile.data_sha256(data)},
           "tool": tool, "length_unit_declared": stepfile.length_unit(data)}
    hidden = stepfile.invisible_items(data)
    if hidden:
        with tempfile.TemporaryDirectory() as tmp:
            visible = Path(tmp) / "visible.step"
            visible.write_bytes(stepfile.visible_only(data))
            out.update(kernel.measure(kernel.read_step(visible)))
        out["invisible_items"] = len(hidden)
    else:
        out.update(kernel.measure(kernel.read_step(comp.step_path)))
    notes = out.pop("notes")
    if notes:
        out["notes"] = notes
    return out


def main(argv):
    argv = [a for a in argv if a != "--"]
    if not argv:
        raise SystemExit(__doc__)
    force = "--force" in argv
    only = set()
    if "--only" in argv:
        only = set(argv[argv.index("--only") + 1:]) - {"--force"}
        argv = argv[:argv.index("--only")]
    project_dir = Path([a for a in argv if not a.startswith("--")][0])
    project = layout.load(project_dir)
    tool = kernel.tool()
    parts = sorted(project.of(root="references", kind="part"), key=lambda c: c.key)
    if only:
        missing = only - {c.key for c in parts}
        if missing:
            print(f"[step_facts] no such imported part: {', '.join(sorted(missing))}")
            return 2
        parts = [c for c in parts if c.key in only]
    measured = kept = failed = 0
    for comp in parts:
        if comp.step_sha256 is None:
            print(f"[step_facts] {comp.key}: part.step is missing or unreadable")
            failed += 1
            continue
        old = comp.facts or {}
        current = (old.get("step", {}).get("sha256") == comp.step_sha256 and old.get("tool") == tool
                   and old.get("length_unit_declared") == comp.step_length_unit
                   and old.get("invisible_items", 0) == (comp.step_invisible_items or 0))
        if current and not force:
            kept += 1
            continue
        t0 = time.time()
        try:
            new = facts_for(comp, tool)
        except Exception as exc:        # a kernel failure on one file must not hide the others
            print(f"[step_facts] {comp.key}: FAILED: {exc}")
            failed += 1
            continue
        if new != old:
            jsonio.write(comp.dir / "facts.json", new)
        measured += 1
        e = [new["bounding_box_mm"]["max"][i] - new["bounding_box_mm"]["min"][i] for i in range(3)]
        print(f"[step_facts] {comp.key}: valid={new['valid']} solids={new['solids']} "
              f"extent_mm={[round(v, 3) for v in e]} volume_mm3={new['volume_mm3']:.3f} "
              f"invisible_left_out={new.get('invisible_items', 0)} ({time.time() - t0:.1f} s)", flush=True)
    print(f"[step_facts] {len(parts)} part(s): {measured} measured, {kept} already current, {failed} failed; "
          f"{tool['name']} {tool['version']}, {tool['kernel']} {tool['kernel_version']}")
    return 1 if failed else 0


def _is_entry():
    """True when this file is the script FreeCADCmd or python was asked to run
    (FreeCADCmd executes a script in its own namespace, not as __main__)."""
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
    print(f"[step_facts] exit status {rc}", flush=True)
    sys.exit(rc)
