"""Compose the per-assembly manifests into the flattened scene mechanical-docs reads.

The scene is derived, never stored in the repository: `write()` puts
`scene.json` and a copy of every STEP file it names into an output directory
(the documentation pipeline resolves assets below the scene's own directory).

Occurrence ids are the paths of occurrence names from the root, joined by "/",
and the root group is "root", as the Inventor exporter writes them.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from . import __version__, jsonio, stepfile
from . import transforms as T

SCENE_SCHEMA = "draft-1"
SCENE_UNITS = "mm"


class FlattenError(ValueError):
    pass


def find_root(project, root=None):
    """The assembly to flatten: the named one, or the only assembly that no
    other assembly places."""
    assemblies = {c.key: c for c in project.of(kind="assembly")}
    if root is not None:
        if root not in assemblies:
            raise FlattenError(f"{root!r} is not an assembly of this project")
        return assemblies[root]
    placed = {ch.component for c in assemblies.values() for ch in c.children}
    tops = sorted(k for k in assemblies if k not in placed)
    if len(tops) != 1:
        raise FlattenError("name the root assembly: " + (", ".join(tops) if tops else "no assembly is unplaced"))
    return assemblies[tops[0]]


def _document(comp):
    """What stands for the definition's document in the scene: the native file
    name when the assembly came from Vault, else the key."""
    vault = (comp.source or {}).get("vault") or {}
    path = vault.get("path")
    return path.replace("\\", "/").split("/")[-1] if isinstance(path, str) and path else comp.key


def _part_record(comp):
    src = comp.source or {}
    step = src.get("step") or (comp.receipt or {}).get("step") or {}
    rec = {
        "id": comp.key,
        "name": comp.name,
        "asset": {"path": f"assets/{comp.key}.step", "format": "step",
                  "units": step.get("length_unit") or comp.step_length_unit, "sha256": comp.step_sha256},
    }
    native = src.get("native") or {}
    if native.get("extent_mm") is not None:
        rec["identifying_dimensions_mm"] = {"extent": list(native["extent_mm"])}
    if src.get("model_state") is not None:
        rec["model_state"] = src["model_state"]
    if isinstance(native.get("bodies"), dict):
        rec["bodies"] = dict(native["bodies"])
    if native.get("volume_mm3") is not None:
        rec["volume_mm3"] = native["volume_mm3"]
    if src.get("bom_structure_default") is not None:
        rec["bom_structure_default"] = src["bom_structure_default"]
    if isinstance(src.get("properties"), dict):
        rec["properties"] = dict(src["properties"])
    vault = src.get("vault")
    if isinstance(vault, dict):
        rec["source"] = {k: v for k, v in (("vault_id", vault.get("vault_id")), ("version_id", vault.get("version_id")),
                                           ("master_id", vault.get("master_id")), ("vault_path", vault.get("path")),
                                           ("native_sha256", vault.get("native_sha256"))) if v is not None}
    return rec


def flatten(project, root=None):
    """Return (scene, assets, skipped): the draft-1 scene as a dict, the list of
    (part key, path of its STEP file) the scene refers to, and the ids of the
    suppressed children that were left out."""
    if project.errors:
        raise FlattenError("the project does not validate; fix that first")
    top = find_root(project, root)
    comps = project.components
    assemblies = [{"id": "root", "parent_id": None, "transform": T.identity(), "document": _document(top)}]
    occurrences = []
    used = {}
    skipped = []

    def walk(asm, node_id, world, inherited, visible_eff, flexible):
        factor = T.unit_factor(asm.assembly["length_unit"], SCENE_UNITS)
        for child in asm.children:
            cid = child.name if node_id == "root" else f"{node_id}/{child.name}"
            if child.flags["suppressed"]:
                skipped.append(cid)
                continue
            local = T.scaled_translation(child.transform, factor)
            overridden = (child.name,) in inherited
            if overridden:
                local = inherited[(child.name,)]
            world_c = T.multiply(world, local)
            target = comps[child.component]
            vis = child.flags["visible"]
            state = child.model_state if child.model_state is not None else (target.source or {}).get("model_state")
            if target.kind == "part":
                used[target.key] = target
                rec = {"id": cid, "part_id": target.key, "parent_id": node_id, "transform": local,
                       "transform_world": world_c, "position_overridden_vs_definition": overridden,
                       "parent_flexible": flexible, "visible": vis, "visible_effective": vis and visible_eff,
                       "suppressed": False, "grounded": child.flags["grounded"], "mirrored": False,
                       "bom_structure": child.bom_structure}
                if state is not None:
                    rec["model_state"] = state
                occurrences.append(rec)
            else:
                rec = {"id": cid, "parent_id": node_id, "transform": local, "document": _document(target),
                       "visible": vis, "suppressed": False, "bom_structure": child.bom_structure,
                       "flexible": child.flags["flexible"]}
                if state is not None:
                    rec["model_state"] = state
                assemblies.append(rec)
                # placements declared on this child entry, then those an outer instance declared for the same
                # node: the outermost statement is the one that holds
                below = {path: T.scaled_translation(m, factor) for path, m in child.overrides}
                below.update({p[1:]: m for p, m in inherited.items() if p[0] == child.name and len(p) > 1})
                walk(target, cid, world_c, below, vis and visible_eff, child.flags["flexible"])

    walk(top, "root", T.identity(), {}, True, False)

    frame = top.assembly.get("frame") or {}
    up = frame.get("up_axis", "+Z")
    coord = {"handedness": "right", "up_axis": up, "origin": frame.get("origin") or f"origin of the assembly {top.key}"}
    if up != "+Z":
        coord["basis_to_z_up"] = T.basis_to_z_up(up)
        coord["note"] = ("Transforms are in the root assembly's own frame. basis_to_z_up maps it to a +Z-up frame; "
                         "apply it once at the scene root.")
    vault = (top.source or {}).get("vault") or {}
    export = (top.source or {}).get("export") or {}
    source = {"kind": "mechanical-cad-flattened-layout", "root": top.path, "flattened_by": f"mechanical-cad {__version__}",
              "qualification": "geometry and hierarchy flattened from per-assembly manifests; "
                               "not a reviewed assembly procedure or stock inventory",
              "occurrence_id_scope": "paths of occurrence names from the root; stable only while those names are"}
    for k, v in (("vault_id", vault.get("vault_id")), ("root_version_id", vault.get("version_id")),
                 ("root_master_id", vault.get("master_id")), ("root_vault_path", vault.get("path")),
                 ("exporter", export.get("exporter")), ("export_run", export.get("run"))):
        if isinstance(v, (str, int, float)) and not isinstance(v, bool):
            source[k] = v
    version = vault.get("version_id")
    scene = {
        "schema_version": SCENE_SCHEMA,
        "id": f"{top.key}-{version}" if version else top.key,
        "title": f"{top.name} (Vault file-version {version})" if version else top.name,
        "units": SCENE_UNITS,
        "coordinate_system": coord,
        "source": source,
        "parts": [_part_record(used[k]) for k in sorted(used)],
        "assemblies": assemblies,
        "occurrences": occurrences,
    }
    assets = [(k, used[k].step_path) for k in sorted(used)]
    return scene, assets, skipped


def write(project, out_dir, root=None):
    """Write scene.json and assets/<key>.step into a new directory."""
    out = Path(out_dir)
    if out.exists() and any(out.iterdir()):
        raise FlattenError(f"{out} exists and is not empty; the flattened scene is written to a fresh directory")
    scene, assets, skipped = flatten(project, root)
    (out / "assets").mkdir(parents=True, exist_ok=True)
    for key, src in assets:
        dst = out / "assets" / f"{key}.step"
        shutil.copyfile(src, dst)
        if stepfile.sha256_file(dst) != project.components[key].step_sha256:
            raise FlattenError(f"{dst}: the copy does not match {src}")
    jsonio.write(out / "scene.json", scene)
    return {"scene": str(out / "scene.json"), "parts": len(scene["parts"]), "assemblies": len(scene["assemblies"]),
            "occurrences": len(scene["occurrences"]), "suppressed_left_out": skipped,
            "scene_sha256": stepfile.sha256_file(out / "scene.json")}
