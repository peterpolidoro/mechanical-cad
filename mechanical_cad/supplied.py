"""A supplied part: a STEP file that came from outside, kept as it came.

A part of `designs/` has one source. Beside the program and the document drawn
in FreeCAD there is a third: the file itself, from a supplier, from another
repository (a circuit board's model), or from somewhere else that the record
describes. Nothing builds it. `add` puts it into a project:

    designs/parts/<key>/
      part.step      the file with its header normalised; the data section is
                     byte for byte what was received
      origin.json    where it came from, the day, whether it may be published,
                     and the hashes: of the file here and of the file received

The facts command measures it like any other part, and `interface.json` may
state what other parts are designed to. A newer file of the same part is
added over the old one with `replace`; the part's key stays.

Nothing here needs a CAD kernel, and nothing here fetches anything: the file
is a path on this machine, and what is recorded of its origin is what the
caller says.
"""
from __future__ import annotations

import datetime
import os
from pathlib import Path

from . import jsonio, layout, stepfile


class SuppliedError(ValueError):
    pass


def origin_record(kind, retrieved, publishable, licence=None, note=None, **fields):
    """The `origin` block, with the fields of its kind checked: supplier, repository or other."""
    if kind not in layout.ORIGIN_KINDS:
        raise SuppliedError(f"origin kind {kind!r}: one of {', '.join(sorted(layout.ORIGIN_KINDS))}")
    required, optional = layout.ORIGIN_KINDS[kind]
    given = {k: v for k, v in fields.items() if v is not None}
    missing = [f for f in required if not given.get(f)]
    if missing:
        raise SuppliedError(f"a file from a {kind} needs: {', '.join(missing)}")
    unknown = sorted(set(given) - set(required) - set(optional))
    if unknown:
        raise SuppliedError(f"{', '.join(unknown)}: not said of a file from a {kind}")
    try:
        datetime.date.fromisoformat(retrieved)
    except (TypeError, ValueError):
        raise SuppliedError(f"retrieved {retrieved!r}: the day the file was taken, as YYYY-MM-DD") from None
    if publishable not in (True, False, None):
        raise SuppliedError("publishable is true, false, or None when it is not known")
    out = {"kind": kind}
    out.update({f: given[f] for f in required + optional if f in given})
    out.update({"retrieved": retrieved, "licence": licence, "publishable": publishable})
    if note:
        out["note"] = note
    return out


def add(project_dir, key, file, name, origin, replace=False):
    """Put a STEP file into a project as the supplied part `key`. Returns what was written, as a dict.

    Refused: a key that is not a key, a key another component has, a supplied
    part that is there already unless `replace` is given, and a file that is
    not a STEP file with one schema and a length unit.
    """
    project_dir, file = Path(project_dir), Path(file)
    if not layout.KEY.match(key) or len(key) > layout.KEY_MAX:
        raise SuppliedError(f"{key!r} is not a key: lower-case letters, digits and single hyphens")
    if not isinstance(name, str) or not name:
        raise SuppliedError("a supplied part needs a name")
    if not any((project_dir / r).is_dir() for r in layout.ROOTS):
        raise SuppliedError(f"{project_dir} is not a project: neither references/ nor designs/ exists")
    part_dir = project_dir / "designs" / "parts" / key
    project = layout.load(project_dir)
    existing = project.components.get(key)
    if existing is not None and not existing.supplied:
        raise SuppliedError(f"{key} is {existing.path} already, and it is not a supplied part")
    if existing is not None and not replace:
        raise SuppliedError(f"{existing.path} exists; give replace to put a newer file in its place")
    try:
        received = file.read_bytes()
        data = stepfile.normalise_header(received)
        head = stepfile.header(data)
        unit = stepfile.length_unit(data)
    except OSError as exc:
        raise SuppliedError(f"{file}: {exc}") from None
    except stepfile.StepFileError as exc:
        raise SuppliedError(f"{file} is not a STEP file this layout can hold: {exc}") from None
    if len(head["schemas"]) != 1:
        raise SuppliedError(f"{file}: FILE_SCHEMA names {len(head['schemas'])} schemas; a part has one")
    record = {
        "schema_version": layout.SCHEMA_VERSION, "key": key, "name": name, "origin": origin,
        "step": {"sha256": stepfile.sha256_bytes(data), "data_sha256": stepfile.data_sha256(data), "bytes": len(data),
                 "protocol": head.get("protocol"), "length_unit": unit, "header_normalised": True,
                 "received_sha256": stepfile.sha256_bytes(received)},
    }
    part_dir.mkdir(parents=True, exist_ok=True)
    step = part_dir / "part.step"
    changed = not step.is_file() or step.read_bytes() != data
    if changed:
        tmp = part_dir / "part.step.tmp"
        tmp.write_bytes(data)
        os.replace(tmp, step)
    origin_file = part_dir / layout.ORIGIN
    if not origin_file.is_file() or jsonio.load(origin_file) != record:
        jsonio.write(origin_file, record)
    return {"key": key, "path": f"designs/parts/{key}", "step_changed": changed, "bytes": len(data),
            "protocol": head.get("protocol"), "length_unit": unit, "sha256": record["step"]["sha256"],
            "received_sha256": record["step"]["received_sha256"]}
