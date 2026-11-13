"""The layout of a project repository: loading and validating it.

docs/layout-specification.md is the reference; this module is its validator.
Nothing here needs a CAD kernel. Problems are collected, never raised one at a
time: `load()` returns a Project whose `errors` say what breaks the layout and
whose `findings` say what a reader should know (a missing measurement, a
header that still carries an author).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import jsonio, stepfile
from . import transforms as T

SCHEMA_VERSION = 1
LOCK_SCHEMA_VERSION = 2
ROOTS = ("references", "designs")
KINDS = {"parts": "part", "assemblies": "assembly"}
KEY = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:@[a-z0-9]+(?:-[a-z0-9]+)*)?$")
KEY_MAX = 80
SHA256 = re.compile(r"^[0-9a-f]{64}$")
BOM_STRUCTURES = ("Normal", "Phantom", "Reference", "Purchased", "Inseparable", "Default")
UP_AXES = ("+Z", "+Y")

SOURCE_FIELDS = {"schema_version", "kind", "key", "name", "model_state", "vault", "step", "export", "properties",
                 "bom_structure_default", "native", "materials"}
VAULT_FIELDS = ("vault_id", "master_id", "version_id", "version_number", "revision", "lifecycle_state", "checkin_date",
                "path", "native_sha256")
STEP_FIELDS = ("sha256", "data_sha256", "bytes", "protocol", "length_unit", "header_normalised", "received_sha256")
ASSEMBLY_FIELDS = {"schema_version", "key", "name", "length_unit", "frame", "children"}
FRAME_FIELDS = {"handedness", "up_axis", "origin"}
CHILD_FIELDS = {"name", "component", "kind", "master_id", "model_state", "transform", "bom_structure", "visible",
                "suppressed", "grounded", "flexible", "mirrored", "overrides"}
CHILD_FLAGS = ("visible", "suppressed", "grounded", "flexible", "mirrored")
CHILD_FLAG_DEFAULTS = {"visible": True, "suppressed": False, "grounded": False, "flexible": False, "mirrored": False}
OVERRIDE_FIELDS = {"path", "transform"}
FACTS_FIELDS = {"schema_version", "key", "step", "tool", "valid", "length_unit_declared", "solids",
                "shells", "faces", "volume_mm3", "area_mm2", "center_of_mass_mm", "bounding_box_mm", "invisible_items",
                "notes"}
RECEIPT_FIELDS = {"schema_version", "key", "name", "step", "program", "parameters", "tool", "reimport"}

FILES = {
    ("references", "part"): ({"part.step", "source.json"}, {"facts.json"}),
    ("references", "assembly"): ({"assembly.json", "source.json"}, set()),
    ("designs", "part"): ({"part.step", "build.py", "parameters.json", "receipt.json"},
                          {"checks.json", "facts.json", "vault.json", "README.md"}),
    ("designs", "assembly"): ({"assembly.json"}, {"README.md"}),
}


@dataclass
class Child:
    name: str
    component: str
    kind: str
    transform: list
    bom_structure: str
    flags: dict
    overrides: list            # [(path tuple, 4x4)]
    master_id: str | None = None
    model_state: str | None = None


@dataclass
class Component:
    root: str                  # "references" or "designs"
    kind: str                  # "part" or "assembly"
    key: str
    dir: Path
    source: dict | None = None
    assembly: dict | None = None
    facts: dict | None = None
    receipt: dict | None = None
    vault: dict | None = None
    children: list = field(default_factory=list)
    step_sha256: str | None = None
    step_data_sha256: str | None = None
    step_length_unit: str | None = None
    step_invisible_items: int | None = None

    @property
    def path(self):
        return f"{self.root}/{'parts' if self.kind == 'part' else 'assemblies'}/{self.key}"

    @property
    def name(self):
        for d in (self.source, self.assembly, self.receipt):
            if isinstance(d, dict) and isinstance(d.get("name"), str) and d["name"]:
                return d["name"]
        return self.key

    @property
    def step_path(self):
        return self.dir / "part.step"


@dataclass
class Project:
    dir: Path
    components: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    findings: list = field(default_factory=list)
    lock: dict | None = None
    converted: list = field(default_factory=list)       # files that differ from their record only in line endings

    def error(self, where, message):
        self.errors.append(f"{where}: {message}")

    def finding(self, where, message):
        self.findings.append(f"{where}: {message}")

    @property
    def ok(self):
        return not self.errors

    def of(self, root=None, kind=None):
        return [c for c in self.components.values() if (root is None or c.root == root) and (kind is None or c.kind == kind)]

    def report(self):
        return {
            "project": str(self.dir),
            "ok": self.ok,
            "counts": {f"{r}_{k}": len(self.of(r, k)) for r in ROOTS for k in ("part", "assembly")},
            "errors": list(self.errors),
            "findings": list(self.findings),
        }


# ------------------------------------------------------------------ small checks

def _is_sha(v):
    return isinstance(v, str) and SHA256.match(v) is not None


def _str_or_none(v):
    return v is None or isinstance(v, str)


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _vec3(v):
    return isinstance(v, list) and len(v) == 3 and all(_number(x) for x in v)


def _note_line_endings(project, path, recorded):
    """Remember a file whose bytes are the recorded ones once every CRLF is an LF: a checkout converted it."""
    if not _is_sha(recorded):
        return
    try:
        data = Path(path).read_bytes()
    except OSError:
        return
    if b"\r\n" in data and stepfile.sha256_bytes(data.replace(b"\r\n", b"\n")) == recorded:
        name = Path(path).relative_to(project.dir).as_posix()
        if name not in project.converted:
            project.converted.append(name)


def _only(project, where, data, allowed):
    extra = sorted(set(data) - set(allowed))
    if extra:
        project.error(where, f"unknown field(s) {', '.join(extra)}")


def _load_json(project, path, where):
    try:
        data = jsonio.load(path)
    except (jsonio.JsonError, OSError) as exc:
        project.error(where, str(exc))
        return None
    if not isinstance(data, dict):
        project.error(where, "expected a JSON object")
        return None
    return data


# ------------------------------------------------------------------ loading

def load(project_dir):
    """Read a project repository and validate it against the layout."""
    project = Project(Path(project_dir))
    if not project.dir.is_dir():
        project.error(str(project.dir), "not a directory")
        return project
    if not any((project.dir / r).is_dir() for r in ROOTS):
        project.error(str(project.dir), "neither references/ nor designs/ exists")
        return project
    for root in ROOTS:
        _scan_root(project, root)
    for comp in sorted(project.components.values(), key=lambda c: c.path):
        _check_files(project, comp)
        if comp.kind == "part":
            _check_step(project, comp)
        if comp.root == "references":
            _check_source(project, comp)
        elif comp.kind == "part":
            _check_receipt(project, comp)
            _check_publications(project, comp)
        if comp.kind == "part":
            _check_facts(project, comp)
        if comp.kind == "assembly":
            _check_assembly(project, comp)
    _check_references_between(project)
    _check_headers(project)
    _check_lock(project)
    _check_line_endings(project)
    return project


def _scan_root(project, root):
    base = project.dir / root
    if not base.is_dir():
        return
    allowed = set(KINDS) | ({"receipts"} if root == "references" else set())
    for entry in sorted(base.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.name not in allowed:
            project.finding(f"{root}/{entry.name}", "not part of the layout")
            continue
        if entry.name == "receipts":
            continue
        kind = KINDS[entry.name]
        for d in sorted(entry.iterdir()):
            where = f"{root}/{entry.name}/{d.name}"
            if d.name.startswith("."):
                continue
            if not d.is_dir():
                project.error(where, "expected a component directory")
                continue
            if not KEY.match(d.name) or len(d.name) > KEY_MAX:
                project.error(where, "the directory name is not a valid key (lower-case letters, digits and "
                                     f"single hyphens, optionally @state, at most {KEY_MAX} characters)")
                continue
            if d.name in project.components:
                other = project.components[d.name]
                project.error(where, f"the key is already used by {other.path}; keys are unique across the repository")
                continue
            project.components[d.name] = Component(root, kind, d.name, d)


def _check_files(project, comp):
    required, optional = FILES[(comp.root, comp.kind)]
    present = {p.name for p in comp.dir.iterdir() if not p.name.startswith(".")}
    for name in sorted(required - present):
        project.error(comp.path, f"{name} is missing")
    extra = sorted(present - required - optional)
    if extra:
        if comp.root == "references":
            project.error(comp.path, f"unexpected file(s) {', '.join(extra)}; nothing under references/ is added by hand")
        else:
            project.finding(comp.path, f"file(s) outside the layout: {', '.join(extra)}")


def _check_step(project, comp):
    if not comp.step_path.is_file():
        return
    try:
        data = comp.step_path.read_bytes()
        comp.step_sha256 = stepfile.sha256_bytes(data)
        comp.step_data_sha256 = stepfile.data_sha256(data)
        comp._step_header = stepfile.header(data)
        comp._step_normalised = stepfile.is_normalised(data)
    except (stepfile.StepFileError, OSError) as exc:
        project.error(f"{comp.path}/part.step", f"not readable as a STEP file: {exc}")
        return
    if len(comp._step_header["schemas"]) > 1:
        project.error(f"{comp.path}/part.step", "FILE_SCHEMA names more than one schema: "
                      + ", ".join(s.split()[0] for s in comp._step_header["schemas"]))
    try:
        comp.step_length_unit = stepfile.length_unit(data)
    except stepfile.StepFileError as exc:
        project.error(f"{comp.path}/part.step", f"no usable length unit: {exc}")
    try:
        comp.step_invisible_items = len(stepfile.invisible_items(data))
    except stepfile.StepFileError as exc:
        project.error(f"{comp.path}/part.step", f"marks something invisible in a way that is not understood: {exc}")
    comp._step_bytes = len(data)


def _check_step_record(project, comp, where, step, require_received):
    """The `step` block shared by source.json and receipt.json against the file."""
    if not isinstance(step, dict):
        project.error(where, "step: expected an object")
        return
    fields = STEP_FIELDS if require_received else tuple(f for f in STEP_FIELDS if f not in ("received_sha256", "protocol"))
    for f in fields:
        if f not in step:
            project.error(where, f"step.{f} is missing (write null when unknown)")
    _only(project, where + " step", step, STEP_FIELDS)
    if comp.step_sha256 is None:
        return
    if step.get("sha256") != comp.step_sha256:
        project.error(where, f"step.sha256 does not match part.step ({comp.step_sha256})")
        _note_line_endings(project, comp.step_path, step.get("sha256"))
    if step.get("data_sha256") != comp.step_data_sha256:
        project.error(where, f"step.data_sha256 does not match part.step ({comp.step_data_sha256})")
    if "bytes" in step and step.get("bytes") != getattr(comp, "_step_bytes", None):
        project.error(where, "step.bytes does not match part.step")
    unit = step.get("length_unit")
    if unit not in T.UNIT_TO_MM:
        project.error(where, f"step.length_unit {unit!r} is not one of {sorted(T.UNIT_TO_MM)}")
    elif comp.step_length_unit is not None and unit != comp.step_length_unit:
        project.error(where, f"step.length_unit is {unit!r} but the file declares {comp.step_length_unit!r}")
    normalised = step.get("header_normalised")
    if not isinstance(normalised, bool):
        project.error(where, "step.header_normalised must be true or false")
    elif normalised != getattr(comp, "_step_normalised", normalised):
        project.error(where, f"step.header_normalised is {str(normalised).lower()} but the file's header says otherwise")
    protocol = step.get("protocol")
    detected = getattr(comp, "_step_header", {}).get("protocol")
    if protocol is not None and detected is not None and protocol != detected:
        project.error(where, f"step.protocol is {protocol!r} but the file's schema is {detected!r}")
    if require_received:
        received = step.get("received_sha256")
        if received is not None and not _is_sha(received):
            project.error(where, "step.received_sha256 is not a SHA-256")
        if received is not None and normalised is False:
            project.error(where, "step.received_sha256 is set but the header is not normalised")


def _check_source(project, comp):
    path = comp.dir / "source.json"
    where = f"{comp.path}/source.json"
    if not path.is_file():
        return
    data = _load_json(project, path, where)
    if data is None:
        return
    comp.source = data
    _only(project, where, data, SOURCE_FIELDS)
    if data.get("schema_version") != SCHEMA_VERSION:
        project.error(where, f"schema_version must be {SCHEMA_VERSION}")
    if data.get("kind") != comp.kind:
        project.error(where, f"kind must be {comp.kind!r}")
    if data.get("key") != comp.key:
        project.error(where, "key must equal the directory name")
    if not isinstance(data.get("name"), str) or not data.get("name"):
        project.error(where, "name must be a non-empty string")
    if "model_state" not in data or not _str_or_none(data["model_state"]):
        project.error(where, "model_state must be a string or null")
    elif ("@" in comp.key) != (data["model_state"] not in (None, "[Primary]", "Primary")):
        project.error(where, "a key carries @state exactly when the model state is not the primary one")

    vault = data.get("vault")
    if not isinstance(vault, dict):
        project.error(where, "vault: expected an object")
    else:
        _only(project, where + " vault", vault, VAULT_FIELDS)
        for f in VAULT_FIELDS:
            if f not in vault:
                project.error(where, f"vault.{f} is missing (write null when unknown)")
        for f in ("vault_id", "master_id", "version_id", "revision", "lifecycle_state", "checkin_date", "path"):
            if not _str_or_none(vault.get(f)):
                project.error(where, f"vault.{f} must be a string or null")
        n = vault.get("version_number")
        if n is not None and (isinstance(n, bool) or not isinstance(n, int)):
            project.error(where, "vault.version_number must be an integer or null")
        if vault.get("native_sha256") is not None and not _is_sha(vault.get("native_sha256")):
            project.error(where, "vault.native_sha256 is not a SHA-256")
        for f in ("master_id", "version_id"):
            if vault.get(f) is None and f in vault:
                project.finding(where, f"vault.{f} is unknown")

    export = data.get("export")
    if not isinstance(export, dict) or not isinstance(export.get("run"), str) or not export.get("run"):
        project.error(where, "export.run must name the export run this file came from")
    else:
        run = export["run"]
        if "/" in run or "\\" in run or run in (".", ".."):
            project.error(where, "export.run must be a directory name, not a path")
        elif not (project.dir / "references" / "receipts" / run).is_dir():
            project.error(where, f"export.run {run!r}: references/receipts/{run}/ does not exist")

    props = data.get("properties")
    if props is not None:
        if not isinstance(props, dict) or any(isinstance(v, (dict, list)) for v in props.values()):
            project.error(where, "properties must be an object of scalar values")
    for f in ("native", "materials"):
        if data.get(f) is not None and not isinstance(data.get(f), dict):
            project.error(where, f"{f} must be an object or null")
    if comp.kind == "part":
        if not _str_or_none(data.get("bom_structure_default")):
            project.error(where, "bom_structure_default must be a string or null")
        _check_step_record(project, comp, where, data.get("step"), require_received=True)
        native = data.get("native") or {}
        if "extent_mm" in native and not _vec3(native["extent_mm"]):
            project.error(where, "native.extent_mm must be three numbers")
        if "volume_mm3" in native and native["volume_mm3"] is not None and not _number(native["volume_mm3"]):
            project.error(where, "native.volume_mm3 must be a number or null")
    elif "step" in data:
        project.error(where, "an assembly has no step record")


def _check_receipt(project, comp):
    path = comp.dir / "receipt.json"
    where = f"{comp.path}/receipt.json"
    if not path.is_file():
        return
    data = _load_json(project, path, where)
    if data is None:
        return
    comp.receipt = data
    _only(project, where, data, RECEIPT_FIELDS)
    if data.get("schema_version") != SCHEMA_VERSION:
        project.error(where, f"schema_version must be {SCHEMA_VERSION}")
    if data.get("key") != comp.key:
        project.error(where, "key must equal the directory name")
    _check_step_record(project, comp, where, data.get("step"), require_received=False)
    for block, filename in (("program", "build.py"), ("parameters", "parameters.json")):
        rec = data.get(block)
        target = comp.dir / filename
        if not isinstance(rec, dict) or rec.get("file") != filename or not _is_sha(rec.get("sha256")):
            project.error(where, f"{block} must record the file {filename!r} and its SHA-256")
        elif target.is_file() and stepfile.sha256_file(target) != rec["sha256"]:
            project.error(where, f"{filename} has changed since the part was built; build it again")
            _note_line_endings(project, target, rec["sha256"])
    if not isinstance(data.get("tool"), dict):
        project.error(where, "tool must record the tool and kernel versions")


def _check_publications(project, comp):
    path = comp.dir / "vault.json"
    where = f"{comp.path}/vault.json"
    if not path.is_file():
        return
    data = _load_json(project, path, where)
    if data is None:
        return
    pubs = data.get("publications")
    if data.get("schema_version") != SCHEMA_VERSION or not isinstance(pubs, list) or not pubs:
        project.error(where, f"expected schema_version {SCHEMA_VERSION} and a non-empty publications list")
        return
    for i, p in enumerate(pubs):
        w = f"{where} publications[{i}]"
        if not isinstance(p, dict):
            project.error(w, "expected an object")
            continue
        for f in ("request_id", "master_id", "version_id", "git_commit"):
            if not isinstance(p.get(f), str) or not p.get(f):
                project.error(w, f"{f} must be a non-empty string")
        if not _is_sha(p.get("step_sha256")):
            project.error(w, "step_sha256 is not a SHA-256")
    comp.vault = data
    last = pubs[-1] if isinstance(pubs[-1], dict) else {}
    if comp.step_sha256 and last.get("step_sha256") != comp.step_sha256:
        project.finding(comp.path, "part.step differs from the file last published to Vault")


def _check_facts(project, comp):
    path = comp.dir / "facts.json"
    where = f"{comp.path}/facts.json"
    if not path.is_file():
        project.finding(comp.path, "no facts.json: the geometry has not been measured")
        return
    data = _load_json(project, path, where)
    if data is None:
        return
    comp.facts = data
    _only(project, where, data, FACTS_FIELDS)
    if data.get("schema_version") != SCHEMA_VERSION:
        project.error(where, f"schema_version must be {SCHEMA_VERSION}")
    if data.get("key") != comp.key:
        project.error(where, "key must equal the directory name")
    step = data.get("step")
    if not isinstance(step, dict) or not _is_sha(step.get("sha256")) or not _is_sha(step.get("data_sha256")):
        project.error(where, "step must record the SHA-256 and the data-section SHA-256 of the file measured")
    elif comp.step_sha256 and (step["sha256"] != comp.step_sha256 or step["data_sha256"] != comp.step_data_sha256):
        project.error(where, "the facts describe a different part.step; measure it again")
    tool = data.get("tool")
    if not isinstance(tool, dict) or not all(isinstance(tool.get(f), str) and tool.get(f) for f in ("name", "version", "kernel", "kernel_version")):
        project.error(where, "tool must record name, version, kernel and kernel_version")
    elif not isinstance(tool.get("integration"), dict):
        project.finding(comp.path, "facts.json was measured with the kernel's plain integration, which can be about "
                                   "1 % off in volume for a solid with free-form surfaces; measure it again")
    if data.get("valid") is not True:
        project.error(where, "the kernel did not find the geometry valid")
    solids = data.get("solids")
    if isinstance(solids, bool) or not isinstance(solids, int) or solids < 0:
        project.error(where, "solids must be a non-negative integer")
    for f in ("volume_mm3", "area_mm2"):
        if not _number(data.get(f)):
            project.error(where, f"{f} must be a number")
    if not _vec3(data.get("center_of_mass_mm")):
        project.error(where, "center_of_mass_mm must be three numbers")
    box = data.get("bounding_box_mm")
    if not isinstance(box, dict) or not _vec3(box.get("min")) or not _vec3(box.get("max")):
        project.error(where, "bounding_box_mm must have min and max, three numbers each")
    hidden = data.get("invisible_items", 0)
    if isinstance(hidden, bool) or not isinstance(hidden, int) or hidden < 0 or ("invisible_items" in data and not hidden):
        project.error(where, "invisible_items must be a positive integer, and absent when nothing was left out")
    elif comp.step_invisible_items is not None and hidden != comp.step_invisible_items:
        project.error(where, f"invisible_items is {hidden} but part.step marks {comp.step_invisible_items} item(s) "
                             "invisible; measure it again")
    declared = data.get("length_unit_declared")
    if comp.step_length_unit and declared != comp.step_length_unit:
        project.error(where, f"length_unit_declared is {declared!r} but the file declares {comp.step_length_unit!r}")


def _check_assembly(project, comp):
    path = comp.dir / "assembly.json"
    where = f"{comp.path}/assembly.json"
    if not path.is_file():
        return
    data = _load_json(project, path, where)
    if data is None:
        return
    comp.assembly = data
    _only(project, where, data, ASSEMBLY_FIELDS)
    if data.get("schema_version") != SCHEMA_VERSION:
        project.error(where, f"schema_version must be {SCHEMA_VERSION}")
    if data.get("key") != comp.key:
        project.error(where, "key must equal the directory name")
    if not isinstance(data.get("name"), str) or not data.get("name"):
        project.error(where, "name must be a non-empty string")
    if data.get("length_unit") not in T.UNIT_TO_MM:
        project.error(where, f"length_unit must be one of {sorted(T.UNIT_TO_MM)}")
    frame = data.get("frame")
    if frame is not None:
        if not isinstance(frame, dict):
            project.error(where, "frame must be an object")
        else:
            _only(project, where + " frame", frame, FRAME_FIELDS)
            if frame.get("handedness", "right") != "right":
                project.error(where, "frame.handedness must be 'right'")
            if frame.get("up_axis") not in UP_AXES:
                project.error(where, f"frame.up_axis must be one of {UP_AXES}")
    children = data.get("children")
    if not isinstance(children, list):
        project.error(where, "children must be a list")
        return
    if not children:
        project.finding(comp.path, "the assembly has no children")
    explicit = comp.root == "references"
    seen = set()
    for i, c in enumerate(children):
        w = f"{where} children[{i}]"
        if not isinstance(c, dict):
            project.error(w, "expected an object")
            continue
        _only(project, w, c, CHILD_FIELDS)
        name = c.get("name")
        if not isinstance(name, str) or not name or name != name.strip() or "/" in name:
            project.error(w, "name must be a non-empty string without '/' or surrounding whitespace")
            continue
        w = f"{where} child {name!r}"
        if name in seen:
            project.error(w, "the name is used twice in this assembly")
            continue
        seen.add(name)
        if c.get("kind") not in ("part", "assembly"):
            project.error(w, "kind must be 'part' or 'assembly'")
        if not isinstance(c.get("component"), str):
            project.error(w, "component must be the key of a part or an assembly")
            continue
        try:
            transform = T.check_matrix(c.get("transform"), "transform")
        except T.TransformError as exc:
            project.error(w, str(exc))
            continue
        flags = {}
        for f in CHILD_FLAGS:
            if f in c:
                if not isinstance(c[f], bool):
                    project.error(w, f"{f} must be true or false")
                flags[f] = bool(c[f])
            elif explicit:
                project.error(w, f"{f} is missing; an imported assembly states every flag")
                flags[f] = CHILD_FLAG_DEFAULTS[f]
            else:
                flags[f] = CHILD_FLAG_DEFAULTS[f]
        bom = c.get("bom_structure", None if explicit else "Normal")
        if bom not in BOM_STRUCTURES:
            project.error(w, f"bom_structure must be one of {BOM_STRUCTURES}")
            bom = "Normal"
        if flags["mirrored"]:
            project.error(w, "a mirrored occurrence is not supported; a mirrored part is its own geometry")
        if flags["suppressed"]:
            project.finding(w, "suppressed; it is left out of the flattened scene")
        for f in ("master_id", "model_state"):
            if f in c and not _str_or_none(c[f]):
                project.error(w, f"{f} must be a string or null")
        overrides = []
        raw = c.get("overrides", [])
        if not isinstance(raw, list):
            project.error(w, "overrides must be a list")
            raw = []
        if raw and (c.get("kind") != "assembly" or not flags["flexible"]):
            project.error(w, "only a flexible assembly instance may carry overrides")
        paths = set()
        for j, o in enumerate(raw):
            wo = f"{w} overrides[{j}]"
            if not isinstance(o, dict):
                project.error(wo, "expected an object")
                continue
            _only(project, wo, o, OVERRIDE_FIELDS)
            p = o.get("path")
            if not isinstance(p, list) or not p or any(not isinstance(x, str) or not x for x in p):
                project.error(wo, "path must be a non-empty list of occurrence names")
                continue
            if tuple(p) in paths:
                project.error(wo, f"the path {'/'.join(p)} is overridden twice")
                continue
            paths.add(tuple(p))
            try:
                overrides.append((tuple(p), T.check_matrix(o.get("transform"), "transform")))
            except T.TransformError as exc:
                project.error(wo, str(exc))
        comp.children.append(Child(name, c["component"], c.get("kind"), transform, bom, flags, overrides,
                                   c.get("master_id"), c.get("model_state")))


def _check_references_between(project):
    """Every child names an existing component of the stated kind; no cycles;
    imported assemblies place imported components only; override paths resolve."""
    for comp in project.of(kind="assembly"):
        where = f"{comp.path}/assembly.json"
        for child in comp.children:
            w = f"{where} child {child.name!r}"
            target = project.components.get(child.component)
            if target is None:
                project.error(w, f"component {child.component!r} does not exist")
                continue
            if target.kind != child.kind:
                project.error(w, f"kind is {child.kind!r} but {target.path} is a {target.kind}")
            if comp.root == "references" and target.root != "references":
                project.error(w, f"an imported assembly cannot place {target.path}")
            src = target.source or {}
            vault = src.get("vault") if isinstance(src.get("vault"), dict) else {}
            if child.master_id is not None and vault.get("master_id") is not None and child.master_id != vault.get("master_id"):
                project.error(w, f"master_id {child.master_id!r} is not that of {target.path} ({vault.get('master_id')!r})")
            if child.model_state is not None and src.get("model_state") is not None and child.model_state != src.get("model_state"):
                project.error(w, f"model_state {child.model_state!r} is not that of {target.path} ({src.get('model_state')!r})")

    state = {}

    def visit(key, trail):
        if state.get(key) == "done":
            return
        if state.get(key) == "open":
            project.error(project.components[key].path, "the assembly contains itself: " + " > ".join(trail + [key]))
            return
        state[key] = "open"
        for child in project.components[key].children:
            target = project.components.get(child.component)
            if target is not None and target.kind == "assembly":
                visit(target.key, trail + [key])
        state[key] = "done"

    for comp in project.of(kind="assembly"):
        visit(comp.key, [])
    if any(e for e in project.errors if "contains itself" in e):
        return
    for comp in project.of(kind="assembly"):
        for child in comp.children:
            for path, _ in child.overrides:
                node = project.components.get(child.component)
                for name in path:
                    nxt = None
                    if node is not None and node.kind == "assembly":
                        nxt = next((c for c in node.children if c.name == name), None)
                    if nxt is None:
                        project.error(f"{comp.path}/assembly.json child {child.name!r}",
                                      f"override path {'/'.join(path)} does not exist in {child.component}")
                        node = None
                        break
                    node = project.components.get(nxt.component)


def _check_line_endings(project):
    """One cause for many errors: Git wrote CRLF into files whose hashes are recorded. It goes first."""
    if not project.converted:
        return
    files = sorted(project.converted)
    shown = ", ".join(files[:3]) + (f" and {len(files) - 3} more" if len(files) > 3 else "")
    project.errors.insert(0, f".gitattributes: {len(files)} file(s) differ from their records only in line endings "
                             f"(CRLF here, LF recorded): {shown}. The checkout converted them, and the errors below "
                             "about them have that one cause: build nothing and measure nothing again. Give the "
                             "repository the .gitattributes of docs/layout-specification.md (\"Line endings\") "
                             "and check the files out again")


def _check_headers(project):
    parts = [c for c in project.of(kind="part") if getattr(c, "_step_normalised", None) is not None]
    plain = [c for c in parts if not c._step_normalised]
    if plain:
        authors = sorted({(c._step_header.get("author") or [""])[0] for c in plain} - {""})
        note = f"{len(plain)} of {len(parts)} STEP headers are not normalised"
        if authors:
            note += f"; {len(authors)} distinct author name(s) appear in them"
        project.finding("part.step", note)


# ------------------------------------------------------------------ the lock

def derive_lock(project):
    """The index that vault-lock.json must equal: what the directories say."""
    components = []
    for comp in sorted(project.of(root="references"), key=lambda c: c.key):
        src = comp.source or {}
        vault = src.get("vault") if isinstance(src.get("vault"), dict) else {}
        components.append({
            "key": comp.key, "path": comp.path, "kind": comp.kind, "model_state": src.get("model_state"),
            "master_id": vault.get("master_id"), "version_id": vault.get("version_id"),
            "native_sha256": vault.get("native_sha256"),
            "step_sha256": comp.step_sha256, "step_data_sha256": comp.step_data_sha256,
        })
    publications = []
    for comp in sorted(project.of(root="designs", kind="part"), key=lambda c: c.key):
        for p in (comp.vault or {}).get("publications", []):
            if isinstance(p, dict):
                publications.append({"key": comp.key, "path": comp.path, "request_id": p.get("request_id"),
                                     "master_id": p.get("master_id"), "version_id": p.get("version_id"),
                                     "step_sha256": p.get("step_sha256"), "git_commit": p.get("git_commit")})
    return {"schema_version": LOCK_SCHEMA_VERSION, "components": components, "publications": publications}


def _check_lock(project):
    path = project.dir / "vault-lock.json"
    if not path.is_file():
        if project.of(root="references"):
            project.finding("vault-lock.json", "missing; it is the index of references/")
        return
    data = _load_json(project, path, "vault-lock.json")
    if data is None:
        return
    project.lock = data
    want = derive_lock(project)
    if data == want:
        return
    if data.get("schema_version") != LOCK_SCHEMA_VERSION:
        project.error("vault-lock.json", f"schema_version must be {LOCK_SCHEMA_VERSION} (the index derived from the directories)")
        return
    have = {c.get("key"): c for c in data.get("components", []) if isinstance(c, dict)}
    wanted = {c["key"]: c for c in want["components"]}
    for key in sorted(set(have) | set(wanted)):
        if key not in have:
            project.error("vault-lock.json", f"{key} is in references/ but not in the index")
        elif key not in wanted:
            project.error("vault-lock.json", f"{key} is in the index but not in references/")
        elif have[key] != wanted[key]:
            diff = sorted(f for f in set(have[key]) | set(wanted[key]) if have[key].get(f) != wanted[key].get(f))
            project.error("vault-lock.json", f"{key}: the index disagrees with the directory in {', '.join(diff)}")
    if data.get("publications") != want["publications"]:
        project.error("vault-lock.json", "the publications do not match the vault.json files under designs/")
    if not any(e.startswith("vault-lock.json") for e in project.errors):
        project.error("vault-lock.json", "differs from the index derived from the directories")
