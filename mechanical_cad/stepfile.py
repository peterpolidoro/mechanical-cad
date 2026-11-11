"""What a STEP file (ISO 10303-21) says about itself, read without a CAD kernel.

Three things are taken from the text of the file:

- its identities: the SHA-256 of the whole file, and the SHA-256 of the data
  section, from the `DATA;` keyword to the end of the file. The header carries a
  file name and a timestamp that change with every export; the data section is
  what the exporter wrote for the geometry.
- its header fields (`FILE_NAME`, `FILE_SCHEMA`), and a way to rewrite
  `FILE_NAME` to fixed values without touching any other byte.
- its declared length unit: the LENGTH_UNIT referenced from
  GLOBAL_UNIT_ASSIGNED_CONTEXT.

The unit reader is adapted from mechanical-docs (mechanical_docs/stepinfo.py).
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

NORMALISED_TIMESTAMP = "1970-01-01T00:00:00"

PROTOCOLS = (
    ("AP242_MANAGED_MODEL_BASED_3D_ENGINEERING", "AP242"),
    ("AP203_CONFIGURATION_CONTROLLED_3D_DESIGN", "AP203E2"),
    ("AUTOMOTIVE_DESIGN", "AP214"),
    ("CONFIG_CONTROL_DESIGN", "AP203"),
)


class StepFileError(ValueError):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ sections

def _skip(data, i):
    """If a string or a comment starts at i, return the index just past it; else i."""
    c = data[i:i + 1]
    if c == b"'":
        j = i + 1
        while True:
            k = data.find(b"'", j)
            if k < 0:
                raise StepFileError("unterminated string")
            if data[k + 1:k + 2] == b"'":       # '' is an escaped quote
                j = k + 2
                continue
            return k + 1
    if data[i:i + 2] == b"/*":
        k = data.find(b"*/", i + 2)
        if k < 0:
            raise StepFileError("unterminated comment")
        return k + 2
    return i


def _statements(data, start, stop):
    """Yield (start, end) of each `...;` statement between start and stop,
    ignoring semicolons inside strings and comments. `end` is past the `;`."""
    i = start
    begin = None
    while i < stop:
        j = _skip(data, i)
        if j != i:
            if begin is None and data[i:i + 1] == b"'":
                begin = i
            i = j
            continue
        c = data[i:i + 1]
        if c == b";":
            if begin is not None:
                yield begin, i + 1
            begin = None
        elif begin is None and not c.isspace():
            begin = i
        i += 1


def sections(data):
    """Offsets of the header and of the data section.

    Returns (header_start, header_end, data_start): the header's statements lie
    in [header_start, header_end) and the `DATA` keyword starts at data_start.
    """
    head = None
    for s, e in _statements(data, 0, len(data)):
        word = data[s:e - 1].strip().upper()
        if head is None:
            if word == b"HEADER":
                head = e
            continue
        if word == b"ENDSEC":
            header_end = s
            for s2, e2 in _statements(data, e, len(data)):
                if data[s2:e2 - 1].strip().upper() == b"DATA":
                    return head, header_end, s2
                raise StepFileError("no DATA section after the header")
            raise StepFileError("no DATA section after the header")
    raise StepFileError("no HEADER section" if head is None else "the header is not closed by ENDSEC")


def data_sha256(data):
    """SHA-256 of the bytes from the `DATA` keyword to the end of the file."""
    return sha256_bytes(data[sections(data)[2]:])


# ------------------------------------------------------------------ header

def _unquote(raw):
    """The text of a Part 21 string token, line wraps removed."""
    body = raw[1:-1].replace(b"\r", b"").replace(b"\n", b"")
    return body.replace(b"''", b"'").decode("utf-8", errors="replace")


def _parse_params(data, i):
    """Parse a parenthesised parameter list starting at data[i] == b'('.
    Returns (list, index past the closing parenthesis)."""
    assert data[i:i + 1] == b"("
    i += 1
    out = []
    token = b""
    while i < len(data):
        j = _skip(data, i)
        if j != i:
            if data[i:i + 1] == b"'":
                out.append(_unquote(data[i:j]))
            i = j
            continue
        c = data[i:i + 1]
        if c == b"(":
            sub, i = _parse_params(data, i)
            out.append(sub)
            continue
        if c == b")":
            if token.strip():
                out.append(token.strip().decode("ascii", errors="replace"))
            return out, i + 1
        if c == b",":
            if token.strip():
                out.append(token.strip().decode("ascii", errors="replace"))
            token = b""
        elif not c.isspace():
            token += c
        i += 1
    raise StepFileError("unterminated parameter list")


def _header_entities(data):
    """{NAME: (params, start, end)} for the statements of the header section."""
    head, end, _ = sections(data)
    out = {}
    for s, e in _statements(data, head, end):
        m = re.match(rb"\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:/\*.*?\*/\s*)*", data[s:e], re.S)
        if not m:
            continue
        name = m.group(1).decode("ascii").upper()
        p = data.find(b"(", s, e)
        if p < 0:
            continue
        params, _ = _parse_params(data, p)
        out[name] = (params, s, e)
    return out


def _first(v):
    return v[0] if isinstance(v, list) and v else (v if isinstance(v, str) else "")


def header(data):
    """The header's fields as a dict. Missing fields are None."""
    ents = _header_entities(data)
    out = {"name": None, "time_stamp": None, "author": None, "organization": None, "preprocessor_version": None,
           "originating_system": None, "authorisation": None, "schema": None, "protocol": None}
    if "FILE_NAME" in ents:
        p = ents["FILE_NAME"][0] + [None] * 7
        out.update({"name": p[0], "time_stamp": p[1],
                    "author": p[2] if isinstance(p[2], list) else [p[2]],
                    "organization": p[3] if isinstance(p[3], list) else [p[3]],
                    "preprocessor_version": p[4], "originating_system": p[5], "authorisation": p[6]})
    if "FILE_SCHEMA" in ents:
        schema = _first(_first(ents["FILE_SCHEMA"][0]))
        out["schema"] = schema
        for needle, name in PROTOCOLS:
            if needle in schema.upper():
                out["protocol"] = name
                break
    return out


def _quote(text):
    return "'" + (text or "").replace("'", "''") + "'"


def normalise_header(data, name="part.step"):
    """The same file with FILE_NAME rewritten to fixed values.

    The name becomes `name`, the timestamp NORMALISED_TIMESTAMP, and author,
    organization and authorisation become empty. The preprocessor and
    originating-system strings are kept: they say which software wrote the
    file. No byte outside the FILE_NAME statement changes, so the data
    section, and its hash, are untouched. Applying it twice gives the same
    bytes as applying it once.
    """
    ents = _header_entities(data)
    if "FILE_NAME" not in ents:
        raise StepFileError("the header has no FILE_NAME")
    _, s, e = ents["FILE_NAME"]
    h = header(data)
    new = ("FILE_NAME(" + ",".join([
        _quote(name), _quote(NORMALISED_TIMESTAMP), "('')", "('')",
        _quote(h["preprocessor_version"]), _quote(h["originating_system"]), "''"]) + ");").encode("utf-8")
    out = data[:s] + new + data[e:]
    if data_sha256(out) != data_sha256(data):       # cannot happen; the cheapest possible proof that it did not
        raise StepFileError("normalising the header changed the data section")
    return out


_PRODUCT = re.compile(rb"(#\d+\s*=\s*PRODUCT\s*\(\s*)'(?:[^']|'')*'(\s*,\s*)'(?:[^']|'')*'")


def set_product_name(data, name):
    """The same file with its one PRODUCT entity's id and name set to `name`.

    OpenCASCADE names the product of a bare shape after itself and a counter of
    the exports the process has made, so the same shape exports to different
    bytes depending on what was exported before it. A CAD system that imports
    the file also shows this name to the user. The build command therefore
    names the product after the part. A file with several products (an
    assembly) is refused.
    """
    _, _, start = sections(data)
    found = _PRODUCT.findall(data, start)
    if len(found) != 1:
        raise StepFileError(f"expected one PRODUCT entity, found {len(found)}")
    quoted = _quote(name).encode("utf-8")
    return data[:start] + _PRODUCT.sub(lambda m: m.group(1) + quoted + m.group(2) + quoted, data[start:], count=1)


def is_normalised(data, name="part.step"):
    h = header(data)
    return (h["name"] == name and h["time_stamp"] == NORMALISED_TIMESTAMP and h["author"] == [""]
            and h["organization"] == [""] and h["authorisation"] == "")


# ------------------------------------------------------------------ units

_GUAC = re.compile(r"GLOBAL_UNIT_ASSIGNED_CONTEXT\s*\(\s*\(([^)]*)\)\s*\)", re.S)
_ENTITY = re.compile(r"^\s*#(\d+)\s*=\s*(.*)$", re.S)
_SI = re.compile(r"SI_UNIT\s*\(\s*(\$|\.[A-Z]+\.)\s*,\s*\.METRE\.\s*\)")
_CONV = re.compile(r"CONVERSION_BASED_UNIT\s*\(\s*'([^']*)'", re.I)
SI_PREFIX = {"$": "m", ".MILLI.": "mm", ".CENTI.": "cm", ".KILO.": "km", ".MICRO.": "um"}
CONVERSION_NAMES = {"inch": "in", "inches": "in", "in": "in", "foot": "ft", "feet": "ft", "ft": "ft"}


def length_unit(data):
    """The declared geometry length unit: 'mm', 'cm', 'm', 'in', ...

    Raises StepFileError when there is no unit context, no LENGTH_UNIT among
    its referenced units, or several contexts disagree. Other LENGTH_UNIT
    entities may exist (an inch file carries the millimetre its inch is defined
    from); only the ones the context references count.
    """
    text = data.decode("utf-8", errors="replace")
    start = text.find("DATA;")
    body = text[start + 5:] if start >= 0 else text
    end = body.find("ENDSEC;")
    if end >= 0:
        body = body[:end]
    ents = {}
    for chunk in body.split(";"):
        m = _ENTITY.match(chunk)
        if m:
            ents[int(m.group(1))] = " ".join(m.group(2).split())
    contexts = _GUAC.findall(text)
    if not contexts:
        raise StepFileError("no GLOBAL_UNIT_ASSIGNED_CONTEXT")
    found = set()
    for refs in contexts:
        for ref in refs.split(","):
            ref = ref.strip()
            if not ref.startswith("#"):
                continue
            ent = ents.get(int(ref[1:]), "")
            if "LENGTH_UNIT" not in ent:
                continue
            cm = _CONV.search(ent)
            if cm:
                unit = cm.group(1).strip().lower()
                if unit not in CONVERSION_NAMES:
                    raise StepFileError(f"unknown conversion-based length unit {unit!r}")
                found.add(CONVERSION_NAMES[unit])
                continue
            sm = _SI.search(ent)
            if sm:
                found.add(SI_PREFIX.get(sm.group(1), sm.group(1)))
    if not found:
        raise StepFileError("the unit context references no LENGTH_UNIT")
    if len(found) > 1:
        raise StepFileError(f"unit contexts disagree: {sorted(found)}")
    return found.pop()


# ------------------------------------------------------------------ visibility

_INSTANCE = re.compile(rb"#(\d+)\s*=\s*([A-Za-z_][A-Za-z0-9_]*)?\s*\(")
_REF = re.compile(rb"#(\d+)")
_ONE_REF = re.compile(rb"\s*#(\d+)\s*\Z")
_STYLED = ("STYLED_ITEM", "OVER_RIDING_STYLED_ITEM")


def _elements(data, i):
    """The spans (start, end) of the comma-separated elements of the list that
    opens with the parenthesis at data[i], and the index past its closing one."""
    assert data[i:i + 1] == b"("
    spans, depth, begin, j = [], 0, i + 1, i
    while j < len(data):
        k = _skip(data, j)
        if k != j:
            j = k
            continue
        c = data[j:j + 1]
        if c == b"(":
            depth += 1
        elif c == b")":
            depth -= 1
            if depth == 0:
                if data[begin:j].strip():
                    spans.append((begin, j))
                return spans, j + 1
        elif c == b"," and depth == 1:
            spans.append((begin, j))
            begin = j + 1
        j += 1
    raise StepFileError("unterminated parameter list")


def _ref_list(data, span, what):
    """The entity ids of a parameter that must be a list of references."""
    s, e = span
    p = data.find(b"(", s, e)
    if p < 0 or data[s:p].strip():
        raise StepFileError(f"{what} is not a list")
    out = []
    for a, b in _elements(data, p)[0]:
        m = _ONE_REF.match(data, a, b)
        if not m:
            raise StepFileError(f"{what} holds something that is not a reference")
        out.append((int(m.group(1)), a, b))
    return out, p


def _visibility_edits(data):
    """What `visible_only` has to change: (ids of the invisible items, edits).

    An edit is (start, end, replacement) on the bytes of `data`.
    """
    if b"INVISIBILITY" not in data:
        return [], []
    start = sections(data)[2]
    instances = []
    for s, e in _statements(data, start, len(data)):
        m = _INSTANCE.match(data, s, e)
        if m:
            instances.append((int(m.group(1)), (m.group(2) or b"").decode("ascii").upper(), s, e, m.end() - 1))
    by_id = {i[0]: i for i in instances}
    hidden = {}                                   # item id -> the INVISIBILITY that hides it
    edits = []
    for ident, kind, s, e, paren in instances:
        if kind != "INVISIBILITY":
            continue
        params = _elements(data, paren)[0]
        if len(params) != 1:
            raise StepFileError(f"#{ident} INVISIBILITY does not have one parameter")
        for ref, _, _ in _ref_list(data, params[0], f"#{ident} INVISIBILITY")[0]:
            styled = by_id.get(ref)
            if styled is None or styled[1] not in _STYLED:
                raise StepFileError(f"#{ident} INVISIBILITY hides #{ref}, which is not a STYLED_ITEM; "
                                    "only hidden styled items are understood")
            fields = _elements(data, styled[4])[0]
            item = _ONE_REF.match(data, *fields[2]) if len(fields) >= 3 else None
            if not item:
                raise StepFileError(f"#{ref} STYLED_ITEM does not name the item it styles")
            hidden[int(item.group(1))] = ident
        end = e + (2 if data[e:e + 2] == b"\r\n" else 1 if data[e:e + 1] == b"\n" else 0)
        edits.append((s, end, b""))
    if not hidden:
        return [], []
    placed = set()
    for ident, kind, s, e, paren in instances:
        if kind == "INVISIBILITY" or kind in _STYLED:
            continue
        used = {int(r) for r in _REF.findall(data, paren, e)} & set(hidden)
        if not used:
            continue
        name = kind or "a complex instance"
        fields = _elements(data, paren)[0] if kind.endswith("REPRESENTATION") else []
        if len(fields) < 2:
            raise StepFileError(f"#{min(used)} is marked invisible and is used by #{ident} ({name}); only items "
                                "listed directly in a representation can be left out")
        refs, p = _ref_list(data, fields[1], f"the items of #{ident} {name}")
        outside = _REF.findall(data, paren, fields[1][0]) + _REF.findall(data, fields[1][1], e)
        if {int(r) for r in outside} & set(hidden):
            raise StepFileError(f"#{ident} {name} uses an invisible item outside its list of items")
        keep = [data[a:b].strip() for r, a, b in refs if r not in hidden]
        if not keep:
            raise StepFileError(f"every item of #{ident} {name} is marked invisible")
        edits.append((p, fields[1][1], b"(" + b",".join(keep) + b")"))
        placed |= used
    missing = sorted(set(hidden) - placed)
    if missing:
        raise StepFileError(f"#{missing[0]} is marked invisible but is not an item of any representation")
    return sorted(hidden), edits


def invisible_items(data):
    """The entity ids of the representation items the file marks invisible.

    Inventor's AP242 translator writes the bodies that are hidden in the native
    part as well as the visible ones, and lists the STYLED_ITEM of each hidden
    one in an INVISIBILITY entity. A reader that does not honour that entity
    (OpenCASCADE, and with it FreeCAD) takes them for ordinary solids. Only this
    form is understood: an INVISIBILITY that hides anything but styled items,
    or an invisible item that is not listed directly in a representation,
    raises StepFileError.
    """
    return _visibility_edits(data)[0]


def visible_only(data):
    """The same file without the items it marks invisible.

    Each invisible item is taken out of the item list of every representation
    that holds it, and the INVISIBILITY entities are removed; the items' own
    entities stay in the file, referenced by no shape. No other byte changes.
    A file that marks nothing invisible is returned as it is, and applying
    this twice gives the same bytes as applying it once.
    """
    _, edits = _visibility_edits(data)
    for s, e, new in sorted(edits, reverse=True):
        data = data[:s] + new + data[e:]
    return data


def describe(path):
    """Everything this module reads from one file, as a dict."""
    data = Path(path).read_bytes()
    out = {"bytes": len(data), "sha256": sha256_bytes(data), "data_sha256": data_sha256(data), "header": header(data)}
    try:
        out["length_unit"] = length_unit(data)
    except StepFileError as exc:
        out["length_unit"] = None
        out["length_unit_error"] = str(exc)
    try:
        out["invisible_items"] = len(invisible_items(data))
    except StepFileError as exc:
        out["invisible_items"] = None
        out["invisible_items_error"] = str(exc)
    return out
