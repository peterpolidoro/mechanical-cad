"""Reading and writing the layout's JSON files.

Machine-written files are JSON in UTF-8 without a byte-order mark, LF line
endings and a trailing newline. Lists of scalars (the rows of a matrix, a
vector) stay on one line so a placement change is a small diff.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


class JsonError(ValueError):
    pass


def load(path, allow_bom=False):
    """Parse a JSON file. A byte-order mark is an error unless `allow_bom`
    (records written by PowerShell carry one)."""
    raw = Path(path).read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        if not allow_bom:
            raise JsonError(f"{path}: starts with a UTF-8 byte-order mark")
        raw = raw[3:]
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JsonError(f"{path}: {exc}") from None


def _reject_constant(name):
    raise json.JSONDecodeError(f"{name} is not valid JSON", "", 0)


def _scalar(v):
    return v is None or isinstance(v, (bool, int, float, str))


def dumps(obj, indent=2):
    """JSON text with lists of scalars on one line and everything else indented."""
    out = []
    _emit(obj, 0, indent, out)
    return "".join(out) + "\n"


def _emit(v, level, indent, out):
    pad = " " * (indent * level)
    inner = " " * (indent * (level + 1))
    if isinstance(v, dict):
        if not v:
            out.append("{}")
            return
        out.append("{\n")
        items = list(v.items())
        for i, (k, x) in enumerate(items):
            if not isinstance(k, str):
                raise JsonError(f"non-string key {k!r}")
            out.append(inner + json.dumps(k, ensure_ascii=False) + ": ")
            _emit(x, level + 1, indent, out)
            out.append(",\n" if i < len(items) - 1 else "\n")
        out.append(pad + "}")
    elif isinstance(v, (list, tuple)):
        if not v:
            out.append("[]")
        elif all(_scalar(x) for x in v):
            out.append("[" + ", ".join(_dump_scalar(x) for x in v) + "]")
        else:
            out.append("[\n")
            for i, x in enumerate(v):
                out.append(inner)
                _emit(x, level + 1, indent, out)
                out.append(",\n" if i < len(v) - 1 else "\n")
            out.append(pad + "]")
    elif _scalar(v):
        out.append(_dump_scalar(v))
    else:
        raise JsonError(f"cannot serialise {type(v).__name__}")


def _dump_scalar(v):
    if isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))):
        raise JsonError("non-finite number")
    return json.dumps(v, ensure_ascii=False)


def write(path, obj):
    """Write atomically: a temporary file beside the target, then a rename."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(dumps(obj).encode("utf-8"))
    os.replace(tmp, path)
