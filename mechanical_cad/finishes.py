"""The finishes of a project: what a picture draws each part with.

`finishes.toml`, at the top of a project repository, is one hand-edited file
for the whole project (Peter, 2026-11-19), and optional. It names finishes and
gives them to parts by key:

    schema_version = 1
    default = "grey-plastic"            # optional: the finish of every part that is given none

    [finishes.grey-plastic]
    color = "#8c8f94"                   # an sRGB colour, as a colour picker gives it

    [finishes.aluminium]
    color = "#c9cbcf"
    metallic = 0.8                      # 0 to 1; 0 when left out
    roughness = 0.55                    # 0 to 1; 0.5 when left out

    [finishes.clear-acrylic]
    color = "#dfeef5"
    roughness = 0.1
    opacity = 0.3                       # above 0, up to 1; 1 when left out: how much it hides of what lies behind
    note = "cast sheet"                 # optional

    [parts]
    base-plate = "aluminium"
    "lid@open" = "clear-acrylic"        # a key that is not letters, digits and hyphens is written in quotes

A finish says how a part looks in a picture and nothing else: it is not the
record of what a part is made of, and nothing is built or measured from it.
One part has one finish, whatever its solids.

Nothing here needs a CAD kernel. `problems` checks the file against the keys
of a project; `finish` gives a finish with every number said; `derived` is the
`finishes.json` that the flatten step writes beside `scene.json` for whatever
draws the scene, so that nothing else has to read TOML or know the default.
The colour stays out of the STEP files and out of the scene: a changed colour
changes no geometry, and no hash that stands for geometry.
"""
from __future__ import annotations

import json
import math
import re
import tomllib

FILE = "finishes.toml"
DERIVED = "finishes.json"
SCHEMA_VERSION = 1
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
TOP = {"schema_version", "default", "finishes", "parts"}
FIELDS = {"color", "metallic", "roughness", "opacity", "note"}
DEFAULTS = {"metallic": 0.0, "roughness": 0.5, "opacity": 1.0}
NUMBERS = tuple(DEFAULTS)


class FinishError(ValueError):
    pass


def read(path):
    """The file as it is written. Raises FinishError when it is not TOML."""
    try:
        with open(path, "rb") as handle:
            return tomllib.load(handle)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise FinishError(str(exc)) from None


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def problems(data, kinds):
    """What is wrong with the file, as a list of sentences; empty when nothing is.

    `kinds` maps every key of the project to "part" or "assembly".
    """
    wrong = []
    extra = sorted(set(data) - TOP)
    if extra:
        wrong.append(f"unknown field(s) {', '.join(extra)}")
    if data.get("schema_version") != SCHEMA_VERSION or isinstance(data.get("schema_version"), bool):
        wrong.append(f"schema_version must be {SCHEMA_VERSION}")
    named = data.get("finishes", {})
    if not isinstance(named, dict):
        wrong.append("finishes must be a table of named finishes: [finishes.NAME] with a color")
        named = {}
    for name in sorted(named):
        where = f"finishes.{name}"
        spec = named[name]
        if not NAME.match(name):
            wrong.append(f"{where}: a finish's name is lower-case letters and digits in groups joined by single hyphens")
        if not isinstance(spec, dict):
            wrong.append(f"{where}: expected a table with a color")
            continue
        extra = sorted(set(spec) - FIELDS)
        if extra:
            wrong.append(f"{where}: unknown field(s) {', '.join(extra)}")
        color = spec.get("color")
        if not isinstance(color, str) or not COLOR.match(color):
            wrong.append(f'{where}: color must be an sRGB colour written "#rrggbb"')
        for field in ("metallic", "roughness"):
            if field in spec and not (_number(spec[field]) and 0 <= spec[field] <= 1):
                wrong.append(f"{where}: {field} must be a number from 0 to 1")
        if "opacity" in spec and not (_number(spec["opacity"]) and 0 < spec["opacity"] <= 1):
            wrong.append(f"{where}: opacity must be a number above 0 and no more than 1")
        if "note" in spec and not (isinstance(spec["note"], str) and spec["note"]):
            wrong.append(f"{where}: note must be a non-empty string")
    default = data.get("default")
    if "default" in data and (not isinstance(default, str) or default not in named):
        wrong.append(f"default: {default!r} is not a finish of this file")
    given = data.get("parts", {})
    if not isinstance(given, dict):
        wrong.append('parts must be a table of part keys and finish names: [parts] with KEY = "NAME"')
        given = {}
    for key in sorted(given):
        where = f"parts.{key}"
        if kinds.get(key) is None:
            wrong.append(f"{where}: the project has no part {key!r}")
        elif kinds[key] != "part":
            wrong.append(f"{where}: {key} is an assembly; a finish is given to a part")
        if not isinstance(given[key], str) or given[key] not in named:
            wrong.append(f"{where}: {given[key]!r} is not a finish of this file")
    return wrong


def name_of(data, key):
    """The name of the finish a part has: the one it is given, else the file's default, else None."""
    return data.get("parts", {}).get(key, data.get("default"))


def finish(data, name):
    """A finish with every number said: `color` as "#rrggbb" in lower case, `metallic`, `roughness`, `opacity`."""
    spec = data["finishes"][name]
    return {"color": spec["color"].lower(), **{field: float(spec.get(field, DEFAULTS[field])) for field in NUMBERS}}


def of(data, key):
    """(the name, the finish) a part has, or (None, None)."""
    name = name_of(data, key) if data is not None else None
    return (name, finish(data, name)) if name is not None else (None, None)


def srgb(color):
    """A "#rrggbb" colour as three numbers from 0 to 1, as it is written: in sRGB."""
    return tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))


def linear(color):
    """The same colour as light adds up, which is what a renderer and a glTF file count in."""
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb(color))


def text(named, parts, heading=()):
    """finishes.toml as a command writes it once, for people to edit from then on: `named` is {a finish's name:
    {"color": "#rrggbb", and whatever else it says}}, `parts` {a part's key: a finish's name}, `heading` lines
    of comment for the top. Finishes and parts are in the order of their names and keys."""
    def key(k):
        return k if re.fullmatch(r"[A-Za-z0-9_-]+", k) else json.dumps(k)

    out = [f"# {line}".rstrip() for line in heading] + [f"schema_version = {SCHEMA_VERSION}"]
    for name in sorted(named):
        out += ["", f"[finishes.{key(name)}]", f"color = {json.dumps(named[name]['color'].lower())}"]
        out += [f"{field} = {float(named[name][field]):g}" for field in NUMBERS if field in named[name]]
        if named[name].get("note"):
            out.append(f"note = {json.dumps(named[name]['note'])}")
    out += ["", "[parts]"] + [f"{key(k)} = {json.dumps(parts[k])}" for k in sorted(parts)]
    return "\n".join(out) + "\n"


def derived(data, keys, source_sha256):
    """What the flatten step writes beside scene.json: the finish of every part of the scene, by name, with the
    finishes those names stand for. A part that has none is there with null; the default is applied here, so
    that whoever draws the scene need not know of it."""
    parts = {key: name_of(data, key) for key in keys}
    used = sorted({name for name in parts.values() if name is not None})
    return {"schema_version": SCHEMA_VERSION, "scene": "scene.json",
            "source": {"kind": "mechanical-cad-finishes", "file": FILE, "sha256": source_sha256},
            "finishes": {name: finish(data, name) for name in used},
            "parts": parts}
