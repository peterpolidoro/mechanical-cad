"""Compare two flattened scenes: are they the same assembly?

Used for the conversion's acceptance test (the scene flattened from the layout
against the scene the exporter wrote) and later for comparing a re-export with
the converted snapshot. Part ids may differ between the two; a map from the new
id to the old one says which part is which. Assembly and occurrence ids are
paths of occurrence names and must be the same on both sides.

Numbers are compared within a tolerance, everything else exactly. A field that
only the new scene has is reported, not counted as a difference; a field that
only the old scene has is a difference unless it is listed as dropped.

A STEP file that differs is a difference, unless the new scene is said to come
from another export of the same Vault versions (another protocol, another
header). Then every byte of a file may differ while the part is the same, and
this module cannot tell: the parts whose files differ are listed, and their
geometry is compared with the kernel (tools/compare_step_exports.py).
"""
from __future__ import annotations

from . import transforms as T

# rotation cells are compared absolutely; lengths relative to the scene's size
ROTATION_TOL = 1e-9
RELATIVE_TOL = 1e-6

PART_FIELDS = ("name", "model_state", "bodies", "bom_structure_default", "properties")
PART_NUMBERS = ("volume_mm3",)
ASSEMBLY_FIELDS = ("parent_id", "visible", "suppressed", "bom_structure", "model_state", "flexible")
OCCURRENCE_FIELDS = ("parent_id", "position_overridden_vs_definition", "parent_flexible", "visible", "visible_effective",
                     "suppressed", "grounded", "mirrored", "bom_structure", "model_state")


def _basename(path):
    return path.replace("\\", "/").split("/")[-1] if isinstance(path, str) else path


def _scale(scene):
    """The largest translation magnitude in the scene, at least 1."""
    best = 1.0
    for o in scene.get("occurrences", []):
        for m in (o.get("transform_world"), o.get("transform")):
            if m:
                best = max(best, max(abs(v) for v in T.translation(m)))
    return best


def compare(old, new, part_map=None, dropped_fields=(), other_export=False):
    """Return a report dict; report["same"] says whether the scenes agree.

    part_map: {new part id: old part id}. Parts missing from the map are
    matched by equal id.
    other_export: a part whose STEP file differs is listed under
    "assets_that_differ" and is not a difference.
    """
    part_map = dict(part_map or {})
    diffs, added, assets = [], set(), []
    tol = RELATIVE_TOL * max(_scale(old), _scale(new))
    worst = {"rotation": 0.0, "translation": 0.0, "world_rotation": 0.0, "world_translation": 0.0}

    def field(where, a, b, name):
        if name in a and name not in b:
            if name not in dropped_fields:
                diffs.append(f"{where}: {name} is missing from the new scene")
        elif name in b and name not in a:
            added.add(f"{where.split(' ')[0]}.{name}")
        elif name in a and a[name] != b[name]:
            diffs.append(f"{where}: {name} was {a[name]!r}, is {b[name]!r}")

    def matrix(where, a, b, name, kind):
        if (name in a) != (name in b):
            (diffs.append(f"{where}: {name} is missing from the new scene") if name in a else added.add(f"{where.split(' ')[0]}.{name}"))
            return
        if name not in a:
            return
        rot, tra = T.deviation(a[name], b[name])
        worst[kind + "rotation"] = max(worst[kind + "rotation"], rot)
        worst[kind + "translation"] = max(worst[kind + "translation"], tra)
        if rot > ROTATION_TOL or tra > tol:
            diffs.append(f"{where}: {name} differs (rotation {rot:.3g}, translation {tra:.3g} {new.get('units')})")

    for name in ("schema_version", "units"):
        if old.get(name) != new.get(name):
            diffs.append(f"scene: {name} was {old.get(name)!r}, is {new.get(name)!r}")
    oc, nc = old.get("coordinate_system", {}), new.get("coordinate_system", {})
    for name in ("handedness", "up_axis", "basis_to_z_up"):
        if oc.get(name) != nc.get(name):
            diffs.append(f"scene: coordinate_system.{name} was {oc.get(name)!r}, is {nc.get(name)!r}")

    old_parts = {p["id"]: p for p in old.get("parts", [])}
    new_parts = {p["id"]: p for p in new.get("parts", [])}
    to_old = {nid: part_map.get(nid, nid) for nid in new_parts}
    if len(set(to_old.values())) != len(to_old):
        diffs.append("parts: the id map sends two new parts to the same old part")
    for nid, oid in sorted(to_old.items()):
        if oid not in old_parts:
            diffs.append(f"part {nid}: no part {oid!r} in the old scene")
            continue
        a, b = old_parts[oid], new_parts[nid]
        where = f"part {nid}"
        for name in PART_FIELDS:
            field(where, a, b, name)
        aa, ba = a.get("asset", {}), b.get("asset", {})
        for name in ("format", "units", "sha256"):
            if aa.get(name) != ba.get(name):
                if name == "sha256":
                    assets.append(nid)
                    if other_export:
                        continue
                diffs.append(f"{where}: asset.{name} was {aa.get(name)!r}, is {ba.get(name)!r}")
        for name in PART_NUMBERS:
            if name in a and name in b:
                if abs(a[name] - b[name]) > RELATIVE_TOL * max(1.0, abs(a[name])):
                    diffs.append(f"{where}: {name} was {a[name]!r}, is {b[name]!r}")
            else:
                field(where, a, b, name)
        ae = (a.get("identifying_dimensions_mm") or {}).get("extent")
        be = (b.get("identifying_dimensions_mm") or {}).get("extent")
        if (ae is None) != (be is None) or (ae is not None and any(abs(x - y) > RELATIVE_TOL * max(1.0, abs(x)) for x, y in zip(ae, be))):
            diffs.append(f"{where}: identifying_dimensions_mm.extent was {ae!r}, is {be!r}")
        asrc, bsrc = a.get("source") or {}, b.get("source") or {}
        for name in ("vault_id", "version_id", "master_id", "vault_path", "native_sha256"):
            if asrc.get(name) != bsrc.get(name):
                diffs.append(f"{where}: source.{name} was {asrc.get(name)!r}, is {bsrc.get(name)!r}")
    for oid in sorted(set(old_parts) - set(to_old.values())):
        diffs.append(f"part {oid!r} of the old scene has no counterpart")

    old_asm = {a["id"]: a for a in old.get("assemblies", [])}
    new_asm = {a["id"]: a for a in new.get("assemblies", [])}
    for aid in sorted(set(old_asm) | set(new_asm)):
        if aid not in new_asm or aid not in old_asm:
            diffs.append(f"assembly {aid!r} is only in the {'old' if aid in old_asm else 'new'} scene")
            continue
        a, b = old_asm[aid], new_asm[aid]
        where = f"assembly {aid!r}"
        for name in ASSEMBLY_FIELDS:
            field(where, a, b, name)
        matrix(where, a, b, "transform", "")
        if _basename(a.get("document")) != _basename(b.get("document")):
            diffs.append(f"{where}: document was {_basename(a.get('document'))!r}, is {_basename(b.get('document'))!r}")

    old_occ = {o["id"]: o for o in old.get("occurrences", [])}
    new_occ = {o["id"]: o for o in new.get("occurrences", [])}
    for oid in sorted(set(old_occ) | set(new_occ)):
        if oid not in new_occ or oid not in old_occ:
            diffs.append(f"occurrence {oid!r} is only in the {'old' if oid in old_occ else 'new'} scene")
            continue
        a, b = old_occ[oid], new_occ[oid]
        where = f"occurrence {oid!r}"
        if to_old.get(b.get("part_id"), b.get("part_id")) != a.get("part_id"):
            diffs.append(f"{where}: part was {a.get('part_id')!r}, is {b.get('part_id')!r}")
        for name in OCCURRENCE_FIELDS:
            field(where, a, b, name)
        matrix(where, a, b, "transform", "")
        matrix(where, a, b, "transform_world", "world_")

    return {
        "same": not diffs,
        "counts": {"old": {k: len(old.get(k, [])) for k in ("parts", "assemblies", "occurrences")},
                   "new": {k: len(new.get(k, [])) for k in ("parts", "assemblies", "occurrences")}},
        "tolerance": {"rotation_cell": ROTATION_TOL, "length": tol, "length_relative": RELATIVE_TOL},
        "largest_deviation": worst,
        "fields_only_in_new": sorted(added),
        "assets_that_differ": sorted(assets),
        "differences": diffs,
    }
