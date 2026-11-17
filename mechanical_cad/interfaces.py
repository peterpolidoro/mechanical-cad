"""A part's interface: the named features that other parts are designed to.

`interface.json` is an optional file of any part. It states, in the part's own
frame and in millimetres, the holes, planes, outlines, ports and volumes that
whoever designs a neighbour needs: where a board's mounting holes are, where a
connector sits and from which direction something enters it, how high the
board's parts reach. It is written by hand for an authored part and by a
command for a circuit board (tools/board_interface.py).

Nothing here needs a CAD kernel. `problems` checks the form of the file.
`checks` turns the features that can be held to the solid into the point
checks of mechanical_cad/facts.py: a hole must be empty at its centre, and a
feature may name points of its own that must be material or empty.

The file:

    {"schema_version": 1, "key": "the-part", "length_unit": "mm",
     "frames": {"board": {"transform": [[...4x4...]], "note": "..."}},
     "features": [
       {"id": "h101", "kind": "hole", "center": [x, y, z], "axis": [0, 0, 1],
        "diameter": 3.2, "depth": 1.6, "through": true},
       {"id": "top", "kind": "plane", "point": [x, y, z], "normal": [0, 0, 1]},
       {"id": "outline", "kind": "outline", "point": [x, y, z], "normal": [0, 0, 1],
        "x": [1, 0, 0], "polygon": [[u, v], ...], "corner_radius": 5.0},
       {"id": "j201", "kind": "port", "box": {"min": [..], "max": [..]},
        "direction": [0, 0, 1], "accepts": "USB-C plug"},
       {"id": "parts-above", "kind": "keep_out", "box": {"min": [..], "max": [..]}},
       {"id": "pin-1", "kind": "point", "point": [x, y, z]},
       {"id": "shaft", "kind": "axis", "point": [x, y, z], "direction": [0, 0, 1]}
     ]}

A frame is a 4x4 matrix that places a named frame in the part's own frame: it
takes a point given in the named frame to the part's frame. Features are
always given in the part's own frame.

A hole's `center` is where its axis meets the face it is drilled from, and
`axis` points out of the material there, so the hole runs from `center`
against `axis`. A port's `direction` points the way out: what plugs in comes
against it. Any feature may carry `note`, `reference` (a name the part's own
documents use, a connector's J201), and `expect`, a list of
`{"point": [x, y, z], "is": "material" | "empty"}` that the solid must satisfy.
"""
from __future__ import annotations

import math
import re

from . import facts, jsonio
from . import transforms as T
from .facts import POINT_STATES

SCHEMA_VERSION = 1
FILE = "interface.json"
ID = re.compile(r"^[a-z0-9]+(?:[-_.][a-z0-9]+)*$")
KINDS = {
    #  kind       required fields                              optional fields
    "hole": (("center", "axis", "diameter"), ("depth", "through")),
    "plane": (("point", "normal"), ()),
    "outline": (("point", "normal", "x", "polygon"), ("corner_radius",)),
    "port": (("box", "direction"), ("accepts",)),
    "keep_out": (("box",), ()),
    "point": (("point",), ()),
    "axis": (("point", "direction"), ()),
}
COMMON = ("id", "kind", "note", "reference", "expect")
TOP = {"schema_version", "key", "length_unit", "frames", "features"}
UNIT_TOLERANCE = 1e-6


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _vec(v, n=3):
    return isinstance(v, list) and len(v) == n and all(_number(x) for x in v)


def _unit(v):
    return _vec(v) and abs(math.sqrt(sum(x * x for x in v)) - 1.0) <= UNIT_TOLERANCE


def _box(v):
    return (isinstance(v, dict) and set(v) == {"min", "max"} and _vec(v["min"]) and _vec(v["max"])
            and all(a <= b for a, b in zip(v["min"], v["max"])))


def _field(name, value):
    """What is wrong with one field of a feature, or None."""
    if name in ("center", "point"):
        return None if _vec(value) else "must be three numbers"
    if name in ("axis", "normal", "direction", "x"):
        return None if _unit(value) else "must be a unit vector of three numbers"
    if name in ("diameter", "depth", "corner_radius"):
        return None if _number(value) and value > 0 else "must be a positive number"
    if name == "through":
        return None if isinstance(value, bool) else "must be true or false"
    if name == "box":
        return None if _box(value) else "must have min and max, three numbers each, min not above max"
    if name == "polygon":
        ok = isinstance(value, list) and len(value) >= 3 and all(_vec(p, 2) for p in value)
        return None if ok else "must be at least three points of two numbers"
    if name in ("accepts", "note", "reference"):
        return None if isinstance(value, str) and value else "must be a non-empty string"
    if name == "expect":
        ok = isinstance(value, list) and value and all(
            isinstance(e, dict) and set(e) == {"point", "is"} and _vec(e["point"]) and e["is"] in POINT_STATES[:2]
            for e in value)
        return None if ok else 'must list {"point": [x, y, z], "is": "material" or "empty"}'
    return "is not a field of this kind of feature"


def problems(data, key=None):
    """What is wrong with the form of an interface, as a list of sentences. Empty when it is well formed."""
    if not isinstance(data, dict):
        return ["expected a JSON object"]
    out = []
    extra = sorted(set(data) - TOP)
    if extra:
        out.append(f"unknown field(s) {', '.join(extra)}")
    if data.get("schema_version") != SCHEMA_VERSION:
        out.append(f"schema_version must be {SCHEMA_VERSION}")
    if key is not None and data.get("key") != key:
        out.append("key must equal the directory name")
    if data.get("length_unit") != "mm":
        out.append('length_unit must be "mm"')
    frames = data.get("frames", {})
    if not isinstance(frames, dict):
        out.append("frames must be an object of named frames")
        frames = {}
    for name, frame in sorted(frames.items()):
        where = f"frames.{name}"
        if not ID.match(name):
            out.append(f"{where}: a frame's name is lower-case letters and digits joined by - _ or .")
        if not isinstance(frame, dict) or set(frame) - {"transform", "note"} or "transform" not in frame:
            out.append(f"{where}: expected a transform and an optional note")
            continue
        try:
            T.check_matrix(frame["transform"], where)
        except T.TransformError as exc:
            out.append(str(exc))
    features = data.get("features")
    if not isinstance(features, list):
        out.append("features must be a list")
        return out
    seen = set()
    for i, feature in enumerate(features):
        if not isinstance(feature, dict):
            out.append(f"features[{i}]: expected an object")
            continue
        fid = feature.get("id")
        where = f"feature {fid!r}" if isinstance(fid, str) else f"features[{i}]"
        if not isinstance(fid, str) or not ID.match(fid):
            out.append(f"{where}: id must be lower-case letters and digits joined by - _ or .")
        elif fid in seen:
            out.append(f"{where}: the id is used twice")
        seen.add(fid)
        kind = feature.get("kind")
        if kind not in KINDS:
            out.append(f"{where}: kind must be one of {', '.join(sorted(KINDS))}")
            continue
        required, optional = KINDS[kind]
        for name in required:
            if name not in feature:
                out.append(f"{where}: {name} is missing")
        for name in sorted(set(feature) - {"id", "kind"}):
            if name not in required and name not in optional and name not in COMMON:
                out.append(f"{where}: {name} is not a field of a {kind}")
                continue
            wrong = _field(name, feature[name])
            if wrong:
                out.append(f"{where}: {name} {wrong}")
        if kind == "hole" and feature.get("through") is False and "depth" not in feature:
            out.append(f"{where}: a hole that is not through needs its depth")
    return out


def checks(data):
    """The point checks an interface asks of the solid, in the form of checks.json.

    A hole must be empty on its axis: at half its depth, or 0.01 mm inside the
    face when no depth is given. Every `expect` of a feature is one check more.
    The ids begin with "interface:" so they stand apart from a part's own.
    """
    out = []
    for feature in data.get("features", []):
        fid = feature["id"]
        if feature["kind"] == "hole":
            inside = feature["depth"] / 2 if "depth" in feature else 0.01
            point = [c - a * inside for c, a in zip(feature["center"], feature["axis"])]
            out.append({"id": f"interface:{fid}", "point": point, "is": "empty"})
        for n, expect in enumerate(feature.get("expect", [])):
            out.append({"id": f"interface:{fid}:{n + 1}", "point": list(expect["point"]), "is": expect["is"]})
    return {"schema_version": 1, "checks": out}


def feature(data, fid):
    """The feature of that id, or a KeyError that names the ids there are."""
    for f in data.get("features", []):
        if f.get("id") == fid:
            return f
    raise KeyError(f"no feature {fid!r} in the interface of {data.get('key')!r}; "
                   f"there are: {', '.join(f.get('id', '?') for f in data.get('features', []))}")


def of_kind(data, kind):
    return [f for f in data.get("features", []) if f.get("kind") == kind]


def frame(data, name):
    """The 4x4 matrix of a named frame: it takes a point of that frame to the part's own frame."""
    frames = data.get("frames", {})
    if name not in frames:
        raise KeyError(f"no frame {name!r} in the interface of {data.get('key')!r}; there are: {', '.join(sorted(frames))}")
    return frames[name]["transform"]


def points_asked(part_dir):
    """The points a part's files ask about, each once: those of its checks.json, then those its interface.json
    holds the solid to. What a build or a measurement has to look at, so that the checks can be read later
    without a kernel. A file that is missing or malformed asks nothing here; the validator says what is wrong."""
    out = []
    for name, to_checks in (("checks.json", lambda d: d), (FILE, lambda d: checks(d) if not problems(d) else {})):
        path = part_dir / name
        if not path.is_file():
            continue
        try:
            document = to_checks(jsonio.load(path))
        except (jsonio.JsonError, OSError):
            continue
        for point in facts.points(document):
            if point not in out:
                out.append(point)
    return out
