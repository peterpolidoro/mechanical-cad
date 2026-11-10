"""What a kernel measured of a STEP file, compared and checked without a kernel.

`facts.json` is written by the kernel-backed tools (tools/step_facts.py,
tools/build_part.py). This module reads it: it compares two sets of facts as a
geometry fingerprint, and it evaluates a part's `checks.json`, the statements
of what the geometry must satisfy.

The fingerprint is solid count, volume, surface area, centre of mass and
bounding box. Two fingerprints are the same geometry when the counts are equal
and the numbers agree within a tolerance. The default tolerances are
provisional: they have been tried against one kernel version only.
"""
from __future__ import annotations

RELATIVE_TOL = 1e-6        # volume and area, relative
LENGTH_TOL_MM = 1e-6       # centre of mass and box corners, plus RELATIVE_TOL times the part's size

FACT_NAMES = ("solids", "volume_mm3", "area_mm2", "center_of_mass_mm", "extent_mm", "bounding_box_min_mm",
              "bounding_box_max_mm")


class FactsError(ValueError):
    pass


def extent(facts):
    box = facts["bounding_box_mm"]
    return [box["max"][i] - box["min"][i] for i in range(3)]


def value(facts, name):
    """One named fact, as checks.json refers to it."""
    if name == "extent_mm":
        return extent(facts)
    if name == "bounding_box_min_mm":
        return list(facts["bounding_box_mm"]["min"])
    if name == "bounding_box_max_mm":
        return list(facts["bounding_box_mm"]["max"])
    if name in ("solids", "volume_mm3", "area_mm2", "center_of_mass_mm"):
        return facts[name]
    raise FactsError(f"unknown fact {name!r}; known: {', '.join(FACT_NAMES)}")


def compare(a, b, relative=RELATIVE_TOL, length_mm=LENGTH_TOL_MM):
    """Are two sets of facts the same geometry? Returns (same, differences)."""
    diffs = []
    if a["solids"] != b["solids"]:
        diffs.append(f"solids: {a['solids']} against {b['solids']}")
    for name in ("volume_mm3", "area_mm2"):
        x, y = a[name], b[name]
        if abs(x - y) > relative * max(abs(x), abs(y), 1e-12):
            diffs.append(f"{name}: {x!r} against {y!r} (relative {abs(x - y) / max(abs(x), abs(y), 1e-12):.3g})")
    size = max(max(extent(a)), max(extent(b)), 1.0)
    tol = length_mm + relative * size
    for name, va, vb in (("center_of_mass_mm", a["center_of_mass_mm"], b["center_of_mass_mm"]),
                         ("bounding_box_mm.min", a["bounding_box_mm"]["min"], b["bounding_box_mm"]["min"]),
                         ("bounding_box_mm.max", a["bounding_box_mm"]["max"], b["bounding_box_mm"]["max"])):
        worst = max(abs(p - q) for p, q in zip(va, vb))
        if worst > tol:
            diffs.append(f"{name}: differs by {worst:.3g} mm")
    return not diffs, diffs


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def evaluate(checks, facts):
    """Evaluate a checks.json document against facts. Returns a list of
    {"id", "passed", "fact", "actual", "expected"}; raises FactsError when the
    document itself is malformed."""
    if not isinstance(checks, dict) or checks.get("schema_version") != 1 or not isinstance(checks.get("checks"), list):
        raise FactsError("checks.json: expected schema_version 1 and a list of checks")
    out, seen = [], set()
    for i, c in enumerate(checks["checks"]):
        if not isinstance(c, dict) or not isinstance(c.get("id"), str) or not c.get("id"):
            raise FactsError(f"checks[{i}]: needs an id")
        if c["id"] in seen:
            raise FactsError(f"check {c['id']!r} appears twice")
        seen.add(c["id"])
        unknown = sorted(set(c) - {"id", "fact", "equals", "tolerance", "min", "max", "note"})
        if unknown:
            raise FactsError(f"check {c['id']!r}: unknown field(s) {', '.join(unknown)}")
        if not any(k in c for k in ("equals", "min", "max")):
            raise FactsError(f"check {c['id']!r}: needs equals, min or max")
        actual = value(facts, c.get("fact"))
        tol = c.get("tolerance", 0)
        if not _number(tol) or tol < 0:
            raise FactsError(f"check {c['id']!r}: tolerance must be a non-negative number")
        passed = True
        if "equals" in c:
            want = c["equals"]
            if isinstance(actual, list):
                if not isinstance(want, list) or len(want) != len(actual) or not all(_number(w) for w in want):
                    raise FactsError(f"check {c['id']!r}: equals must be {len(actual)} numbers")
                passed &= all(abs(x - w) <= tol for x, w in zip(actual, want))
            else:
                if not _number(want):
                    raise FactsError(f"check {c['id']!r}: equals must be a number")
                passed &= abs(actual - want) <= tol
        for bound, ok in (("min", lambda x, b: x >= b), ("max", lambda x, b: x <= b)):
            if bound in c:
                if isinstance(actual, list) or not _number(c[bound]):
                    raise FactsError(f"check {c['id']!r}: {bound} applies to a single number")
                passed &= ok(actual, c[bound])
        out.append({"id": c["id"], "passed": bool(passed), "fact": c["fact"], "actual": actual,
                    "expected": {k: c[k] for k in ("equals", "tolerance", "min", "max") if k in c}})
    return out
