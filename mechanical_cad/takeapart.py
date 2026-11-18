"""A project from one STEP file of an assembly: its products become parts, its structure assemblies.

Some projects begin as a single file: a collaborator exported the whole
assembly from a CAD system and that file is all there is. The layout holds an
assembly as a STEP file per part and the placements of each assembly's direct
children (docs/layout-specification.md), so such a file is taken apart:

    designs/parts/<key>/          one for every product of the file that has geometry of its own;
      part.step                   that product's shape, written out by the kernel, in millimetres
      origin.json                 a supplied part: where the file came from, and which product of it this is
    designs/assemblies/<key>/     one for every product that is made of other products
      assembly.json               its direct children, each with the name its usage has in the file and
                                  the placement it has there

A product used several times is one part, placed several times. Nothing comes
from Vault, so everything goes under designs/, as supplied parts placed by
authored assemblies.

This module is the half that needs no CAD kernel: the rules for keys and
names, and the writing. tools/take_apart.py reads the file with the kernel and
hands over what it found:

    tree = {"roots": [product id, ...],
            "products": {product id: {"name": "PIN", "solids": 1, "geometry": True, "children": []},
                         product id: {"name": "PIN PAIR", "children": [
                             {"name": "PIN:1", "product": product id, "transform": [[...4x4...]]}, ...]}}}

A product with children is an assembly; one without is a part. `solids` and
`geometry` are of a part's own shape; transforms are in millimetres.

The rules, each of which the plan reports when it was applied:

    keys         A key is the product's name in lower case, with a native CAD file's extension dropped and
                 every run of other characters made one hyphen. A name that gives nothing is "part" or
                 "assembly". Two products that would have one key are numbered in the order the file is
                 walked: the first keeps it, the next are <key>-2, <key>-3.
    names        A child keeps its usage's name. An empty one becomes the product's name; "/" becomes "-";
                 a name used twice in one assembly gets " (2)", " (3)".
    left out     A part without any geometry, an assembly that holds nothing else, and products nothing uses.
    the root     A file with one product at the top that is an assembly: that is the root. Several at the
                 top, or a part beside an assembly: an assembly named after the file holds them, each where
                 the file has it.
    refused      A file that is one part and no assembly (add it with add-supplied), and a placement that
                 mirrors or scales: the layout places rigidly, and a mirrored part is its own geometry.
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

from . import jsonio, layout, stepfile
from . import transforms as T

NATIVE_EXTENSIONS = (".ipt", ".iam", ".sldprt", ".sldasm", ".prt", ".asm", ".par", ".catpart", ".catproduct",
                     ".step", ".stp")
TOOL = "tools/take_apart.py"


class TakeApartError(ValueError):
    pass


def key_of(name):
    """The key a name gives, or "" when it gives none: lower case, hyphens for everything else."""
    text = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode("ascii").lower().strip()
    for ext in NATIVE_EXTENSIONS:
        if text.endswith(ext) and len(text) > len(ext):
            text = text[:-len(ext)]
            break
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:layout.KEY_MAX].strip("-")


def _numbered(base, taken):
    """`base`, or the first of base-2, base-3 ... that is not taken, within the length a key may have."""
    if base not in taken:
        return base
    n = 2
    while True:
        tail = f"-{n}"
        key = base[:layout.KEY_MAX - len(tail)].rstrip("-") + tail
        if key not in taken:
            return key
        n += 1


def plan(tree, file_name, root_name=None):
    """What a tree becomes in the layout, as a dictionary; a TakeApartError when it is refused.

    Returns {"root": key, "parts": [{"key", "name", "product", "solids"}], "assemblies": [{"key", "name",
    "children": [{"name", "component", "kind", "transform"}]}], "occurrences": part occurrences when the
    root is flattened, "solids": solids when it is, "notes": what the rules changed or left out}.
    """
    products = tree["products"]
    roots = list(tree["roots"])
    if not roots:
        raise TakeApartError("the file has no product at its top")

    def is_assembly(pid):
        return bool(products[pid].get("children"))

    empty = {}

    def holds_nothing(pid, trail=()):
        if pid in trail:
            raise TakeApartError(f"the product {products[pid]['name']!r} contains itself")
        if pid not in empty:
            p = products[pid]
            empty[pid] = (all(holds_nothing(c["product"], trail + (pid,)) for c in p["children"]) if is_assembly(pid)
                          else not p.get("geometry", True))
        return empty[pid]

    notes = {"keys_numbered": [], "names_changed": [], "left_out": [], "wrapped": None, "not_used": []}
    stem = file_name.rsplit(".", 1)[0] if "." in file_name.strip(".") else file_name
    if len(roots) > 1 or not is_assembly(roots[0]):
        if len(roots) == 1:
            raise TakeApartError("the file is one part and no assembly; a single part is added with add-supplied")
        wrapper = "\0file"
        products = dict(products)
        products[wrapper] = {"name": root_name or stem, "children": [
            {"name": "", "product": pid, "transform": T.identity()} for pid in roots]}
        notes["wrapped"] = f"{len(roots)} products at the top of the file are held by an assembly named after it"
        roots = [wrapper]
    root = roots[0]
    if holds_nothing(root):
        raise TakeApartError("the file holds no geometry")

    # Keys in the order of the walk: an assembly, then what it holds, depth first, each product once.
    order, seen = [], set()

    def walk(pid):
        if pid in seen or holds_nothing(pid):
            return
        seen.add(pid)
        order.append(pid)
        for c in products[pid].get("children") or ():
            walk(c["product"])
    walk(root)
    keys, taken = {}, set()
    for pid in order:
        name = (root_name if pid == root and root_name else products[pid]["name"]) or ""
        base = key_of(name) or ("assembly" if is_assembly(pid) else "part")
        keys[pid] = _numbered(base, taken)
        taken.add(keys[pid])
        if keys[pid] != base:
            notes["keys_numbered"].append({"name": name, "key": keys[pid]})
    for pid, p in tree["products"].items():
        if pid not in seen:
            notes["left_out" if holds_nothing(pid) else "not_used"].append(p["name"] or "(no name)")

    parts, assemblies = [], []
    for pid in order:
        p = products[pid]
        name = (root_name if pid == root and root_name else p["name"]) or keys[pid]
        if not is_assembly(pid):
            parts.append({"key": keys[pid], "name": name, "product": pid, "solids": int(p.get("solids", 0))})
            continue
        children, used = [], set()
        for c in p["children"]:
            target = products[c["product"]]
            if holds_nothing(c["product"]):
                continue
            given = c.get("name") or ""
            wanted = given.strip().replace("/", "-") or (target["name"] or keys[c["product"]]).strip().replace("/", "-")
            unique, n = wanted, 1
            while unique in used:
                n += 1
                unique = f"{wanted} ({n})"
            used.add(unique)
            if unique != given:
                notes["names_changed"].append({"assembly": keys[pid], "was": given, "is": unique})
            try:
                transform = T.check_matrix([[float(v) + 0.0 for v in row] for row in c["transform"]],
                                           f"{name}: the placement of {unique!r}")
            except T.TransformError as exc:
                raise TakeApartError(f"{exc}. The layout places rigidly; a mirrored or scaled part is its own "
                                     "geometry and has to be a product of its own in the file") from None
            children.append({"name": unique, "component": keys[c["product"]],
                             "kind": "assembly" if is_assembly(c["product"]) else "part", "transform": transform})
        assemblies.append({"key": keys[pid], "name": name, "children": children})

    solids_of = {p["key"]: p["solids"] for p in parts}
    by_key = {a["key"]: a for a in assemblies}
    counted = {}

    def count(key):
        if key not in counted:
            if key in solids_of:
                counted[key] = (1, solids_of[key])
            else:
                each = [count(c["component"]) for c in by_key[key]["children"]]
                counted[key] = (sum(e[0] for e in each), sum(e[1] for e in each))
        return counted[key]
    occurrences, solids = count(keys[root])
    return {"root": keys[root], "parts": parts, "assemblies": assemblies, "occurrences": occurrences,
            "solids": solids, "notes": notes}


def _others(project_dir, received_sha256, planned):
    """What is in a directory that an earlier run on the same file did not put there, as sentences."""
    out = []
    if (project_dir / "references").exists():
        out.append("it has references/, which mirrors Vault")
    keys = {p["key"] for p in planned["parts"]}, {a["key"] for a in planned["assemblies"]}
    for kind, wanted in (("parts", keys[0]), ("assemblies", keys[1])):
        root = project_dir / "designs" / kind
        for d in sorted(root.iterdir()) if root.is_dir() else ():
            if d.name not in wanted:
                out.append(f"designs/{kind}/{d.name} is not of this file")
            elif kind == "parts":
                try:
                    record = jsonio.load(d / layout.ORIGIN)
                    same = record.get("step", {}).get("received_sha256") == received_sha256
                except (OSError, jsonio.JsonError, AttributeError):
                    same = False
                if not same:
                    out.append(f"designs/parts/{d.name} is not a part taken out of this file")
    return out


def _put(path, data):
    """Write bytes unless the file holds them already. Returns whether it was written."""
    if path.is_file() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return True


def write(project_dir, planned, part_files, origin, file_name, received_sha256, up_axis=None):
    """Write a plan into a project directory. Returns {"written": n, "unchanged": n}.

    `part_files` is {key: the bytes of that part's STEP file as the kernel
    wrote it}; `origin` the origin block every part gets (mechanical_cad/
    supplied.py, origin_record), to whose note the product is added;
    `received_sha256` the hash of the file that was taken apart, which every
    part records as the file it was received in. The directory is new, or holds
    what an earlier run on the same file wrote: then a file that would be
    written with the same bytes is left alone.
    """
    project_dir = Path(project_dir)
    wrong = _others(project_dir, received_sha256, planned) if project_dir.exists() else []
    if wrong:
        raise TakeApartError(f"{project_dir} holds more than this file's parts: " + "; ".join(wrong[:5]))
    if up_axis is not None and up_axis not in layout.UP_AXES:
        raise TakeApartError(f"the up axis is one of {', '.join(layout.UP_AXES)}")
    missing = sorted(p["key"] for p in planned["parts"] if p["key"] not in part_files)
    if missing:
        raise TakeApartError("no STEP file was written for: " + ", ".join(missing[:5]))
    written = unchanged = 0
    for part in planned["parts"]:
        try:
            data = stepfile.normalise_header(part_files[part["key"]])
            head = stepfile.header(data)
            unit = stepfile.length_unit(data)
        except stepfile.StepFileError as exc:
            raise TakeApartError(f"{part['key']}: the file the kernel wrote is not one the layout can hold: {exc}") from None
        said = f"The product {part['name']!r} of {file_name}, written out by {TOOL}; step.received_sha256 is that file's."
        own = dict(origin)
        own["note"] = f"{said} {origin['note']}" if origin.get("note") else said
        record = {
            "schema_version": layout.SCHEMA_VERSION, "key": part["key"], "name": part["name"], "origin": own,
            "step": {"sha256": stepfile.sha256_bytes(data), "data_sha256": stepfile.data_sha256(data), "bytes": len(data),
                     "protocol": head.get("protocol"), "length_unit": unit, "header_normalised": True,
                     "received_sha256": received_sha256},
        }
        part_dir = project_dir / "designs" / "parts" / part["key"]
        for path, content in ((part_dir / "part.step", data), (part_dir / layout.ORIGIN, jsonio.dumps(record).encode("utf-8"))):
            if _put(path, content):
                written += 1
            else:
                unchanged += 1
    for assembly in planned["assemblies"]:
        manifest = {"schema_version": layout.SCHEMA_VERSION, "key": assembly["key"], "name": assembly["name"],
                    "length_unit": "mm"}
        if up_axis is not None and assembly["key"] == planned["root"]:
            manifest["frame"] = {"handedness": "right", "up_axis": up_axis}
        manifest["children"] = assembly["children"]
        path = project_dir / "designs" / "assemblies" / assembly["key"] / "assembly.json"
        if _put(path, jsonio.dumps(manifest).encode("utf-8")):
            written += 1
        else:
            unchanged += 1
    return {"written": written, "unchanged": unchanged}
