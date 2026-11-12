"""Which assemblies a project holds, and which of them have been built.

Every assembly of a project, a top-level one or a sub-assembly, can be built
as one STEP file and one FreeCAD document (`tools/assembly_step.py`).
`listing()` says what there is to build and whether the built files are those
of the records as they stand. Nothing here needs a kernel.
"""
from __future__ import annotations

from pathlib import Path

from . import flatten, jsonio, solids, stepfile

BUILT_DIR = (".cache", "assemblies")
NOT_BUILT, OUT_OF_DATE, CURRENT = "not built", "out of date", "current"


def default_dir(project_dir):
    """Where the built files of a project's assemblies go unless another place is named."""
    return Path(project_dir).joinpath(*BUILT_DIR)


def scene_sha256(scene):
    """What identifies the records a file was built from: the hash of the flattened scene."""
    return stepfile.sha256_bytes(jsonio.dumps(scene).encode("utf-8"))


def built(out_dir, key, scene_hash):
    """The state of the built files of one assembly, and where they are.

    "current": the files were built from the records as they stand and the
    STEP file is the one its report names. "out of date": files are there, but
    not those. The frame and the tool they were built with are not judged here;
    the build is, by tools/assembly_step.py, which rebuilds when they differ.
    """
    out_dir = Path(out_dir)
    step, document, report = (out_dir / f"{key}{ext}" for ext in (".step", ".FCStd", ".json"))
    if not (step.is_file() and document.is_file() and report.is_file()):
        return {"state": NOT_BUILT}
    out = {"state": OUT_OF_DATE, "step": str(step), "document": str(document)}
    try:
        old = jsonio.load(report)
    except (jsonio.JsonError, OSError):
        return out
    if (isinstance(old, dict) and old.get("scene_sha256") == scene_hash and (old.get("check") or {}).get("same") is True
            and (old.get("step") or {}).get("sha256") == stepfile.sha256_file(step)):
        out["state"] = CURRENT
        out["frame"] = old.get("frame")
    return out


def listing(project, out_dir=None):
    """Every assembly of the project, the ones nothing places first.

    Raises flatten.FlattenError when the project does not validate.
    """
    out_dir = default_dir(project.dir) if out_dir is None else Path(out_dir)
    assemblies = sorted(project.of(kind="assembly"), key=lambda c: c.key)
    placed_by = {c.key: set() for c in assemblies}
    for c in assemblies:
        for child in c.children:
            if child.component in placed_by:
                placed_by[child.component].add(c.key)
    rows = []
    for c in assemblies:
        scene, assets, suppressed = flatten.flatten(project, c.key)
        rows.append({
            "key": c.key, "name": scene["assemblies"][0]["document"], "path": c.path,
            "top_level": not placed_by[c.key], "placed_by": sorted(placed_by[c.key]),
            "parts": len(assets), "occurrences": len(solids.placed(scene)),
            "sub_assembly_instances": len(scene["assemblies"]) - 1,
            "built": built(out_dir, c.key, scene_sha256(scene)),
        })
    rows.sort(key=lambda r: (not r["top_level"], r["key"]))
    return rows


def table(rows):
    """The listing as lines of text for a terminal."""
    if not rows:
        return []
    head = ("KEY", "FILE", "PARTS", "OCCURRENCES", "BUILT", "PART OF")
    body = [(r["key"], r["name"], str(r["parts"]), str(r["occurrences"]), r["built"]["state"],
             ", ".join(r["placed_by"]) or "nothing (top level)") for r in rows]
    widths = [max(len(line[i]) for line in [head] + body) for i in range(len(head))]
    right = {2, 3}
    lines = []
    for line in [head] + body:
        cells = [cell.rjust(widths[i]) if i in right else cell.ljust(widths[i]) for i, cell in enumerate(line)]
        lines.append("  ".join(cells).rstrip())
    return lines
