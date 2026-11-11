# Repository layout: draft specification

**Status: draft 1, written 2026-11-10, provisional.** It implements
[layout-proposal.md](layout-proposal.md) with the three choices Peter decided
on 2026-11-11: two roots, readable keys, and AP242 for files exported from
Inventor. It has been run on the fixture and on a dry-run conversion of the
enclosure, not yet on a re-exported project. The
proposal holds the reasons and the evidence; this document says exactly what a
conforming repository contains.

The validator is `python3 -m mechanical_cad validate PROJECT`. Where this text
and the validator disagree, that is a defect in one of them; say so and fix it.
`examples/layout-fixture/` is a small conforming project.

## The tree

```
references/                    Vault is the authority
  parts/<key>/
    part.step                  import command
    source.json                import command
    facts.json                 facts command
  assemblies/<key>/
    assembly.json              import command
    source.json                import command
  receipts/<run>/              import command; the exporter's records, unchanged
designs/                       the repository is the authority
  parts/<key>/
    build.py                   people and agents
    parameters.json            people and agents
    checks.json                people and agents (optional)
    README.md                  people and agents (optional)
    part.step                  build command
    receipt.json               build command
    facts.json                 build command
    vault.json                 publication record command, when a publication is verified
  assemblies/<key>/
    assembly.json              people and agents
    README.md                  people and agents (optional)
vault-lock.json                import and publication record commands; a derived index
```

Each file has one writer. Nothing under `references/` is edited by hand, and a
file there that the layout does not name is an error. Under `designs/` such a
file is reported, not refused (a FreeCAD document kept beside a program, for
example). Anything else at the top of `references/` or `designs/` is reported
as not part of the layout, so an old tree can stand beside the new one while a
project is being converted.

The commands, and where they live:

| Command | Writes | Where |
| --- | --- | --- |
| import | `references/`, `vault-lock.json` | `vault-cad-tools` (`vault-cad import-snapshot`, provisional) |
| facts | `references/parts/*/facts.json` | `tools/step_facts.py`, run by FreeCADCmd |
| build | `part.step`, `receipt.json`, `facts.json` of an authored part | `tools/build_part.py`, run by FreeCADCmd |
| publication record | `vault.json` of an authored part, and the `publications` of `vault-lock.json` | `vault-cad-tools` (`vault-cad import-publish-result`) |
| validate, check, flatten | nothing in the repository | `python3 -m mechanical_cad` |
| step-info, normalise-header, visible-only | nothing in the repository | `python3 -m mechanical_cad` |

## Keys

A key names one component directory. It is lower-case letters and digits in
groups joined by single hyphens, at most 80 characters, and unique across the
whole repository: no part and assembly, imported or authored, share one.

A part exported in a model state other than its primary one has the key
`<key>@<state>`, with the state written the same way. The primary state has no
suffix.

The import command assigns the key of an imported file once, from the file's
name when it is first imported, and records it against the Vault master id.
The key does not change when the file is renamed or moved in Vault. The
exporter never sees a key.

## JSON conventions

UTF-8 without a byte-order mark, LF line endings, a trailing newline. A value
that is not known is written as `null`; it is never left out and never guessed.
Unknown fields are errors, except inside the blocks this document calls free.
Transforms are 4 by 4, row-major, applied to column vectors, with the
translation in the last column:

```
p_parent = T_parent_from_child * [x, y, z, 1]^T
```

Only rigid transforms are accepted: an orthonormal rotation with determinant +1
and a translation. The length unit of a file's transforms is stated in that
file.

## `source.json` (imported part or assembly)

What the exporter recorded for one Vault file.

| Field | Meaning |
| --- | --- |
| `schema_version` | `1` |
| `kind` | `"part"` or `"assembly"` |
| `key` | the directory name |
| `name` | the document's name without its extension |
| `model_state` | the exported model state, or null |
| `vault` | `vault_id`, `master_id`, `version_id`, `version_number`, `revision`, `lifecycle_state`, `checkin_date`, `path`, `native_sha256`: all nine present, null where unknown. An unknown master or version id is reported |
| `step` | parts only; see below |
| `export` | `run` (required: the directory under `references/receipts/` holding the records of the export this file came from), then free: `exporter`, `exported_at`, `translator_options`, `package_id` and `package_path` (what the exporter called this file and where its STEP lay in the exporter's package) |
| `properties` | an object of scalar values (part number, description, material, ...), or null |
| `bom_structure_default` | parts only; a string or null |
| `native` | free: what the CAD system reported. `extent_mm` (three numbers), `volume_mm3` and `bodies` are used by the flattened scene when present |
| `materials` | the material and appearance claim (`vault-cad-tools/docs/authoring-and-materials.md`, 4.1), or null |

The `step` block, all seven fields present:

| Field | Meaning |
| --- | --- |
| `sha256` | of `part.step` |
| `data_sha256` | of `part.step` from its `DATA` keyword to the end of the file |
| `bytes` | its size |
| `protocol` | `AP203`, `AP214`, `AP203E2`, `AP242` or null; must agree with the file's schema |
| `length_unit` | `mm`, `cm`, `m` or `in`; must be the unit the file declares |
| `header_normalised` | whether the file's header is the normalised one; must be true of the file |
| `received_sha256` | when a file was normalised after it was received, the hash of what was received; otherwise null |

## `assembly.json`

The direct children of one assembly.

| Field | Meaning |
| --- | --- |
| `schema_version` | `1` |
| `key`, `name` | the directory name; the display name |
| `length_unit` | the unit of every translation in this file: `mm`, `cm`, `m` or `in` |
| `frame` | optional: `handedness` (`"right"`), `up_axis` (`"+Z"` or `"+Y"`), `origin` (text). The frame of the root assembly becomes the scene's |
| `children` | a list |

Each child:

| Field | Meaning |
| --- | --- |
| `name` | the occurrence name, unique in this assembly, without `/` |
| `component` | the key of a part or an assembly |
| `kind` | `"part"` or `"assembly"`; must be what the component is |
| `transform` | the child's placement in this assembly |
| `bom_structure` | `Normal`, `Phantom`, `Reference`, `Purchased`, `Inseparable` or `Default` |
| `visible`, `suppressed`, `grounded`, `flexible`, `mirrored` | true or false |
| `master_id`, `model_state` | optional; when given they must be those of the component |
| `overrides` | optional; only on a flexible assembly child |

An imported assembly states every flag and the BOM structure of every child.
An authored assembly may leave them out: visible, not suppressed, not
grounded, not flexible, not mirrored, `Normal`. An imported assembly places
imported components only; an authored assembly may place either. An assembly
cannot contain itself. A mirrored child is an error (a mirrored part is its
own geometry). A suppressed child is reported and left out of the flattened
scene.

**Overrides.** A flexible instance of a sub-assembly may hold its descendants
somewhere other than the sub-assembly's own definition says. Such a placement
is written on the instance's child entry, in the manifest of the assembly that
contains the instance:

```json
"overrides": [{"path": ["PIN:2"], "transform": [[1, 0, 0, 35], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]}]
```

`path` is the chain of occurrence names from the instance down to the node; it
must exist in the instance's definition. `transform` replaces that node's
placement in its own parent, in the length unit of the manifest the override
is written in. When two levels state a placement for the same node, the outer
one holds.

## `facts.json`

What a geometry kernel measured of `part.step`, in millimetres.

`schema_version`, `key`, `step` (`sha256` and `data_sha256` of the file
measured), `tool` (`name`, `version`, `kernel`, `kernel_version`), `valid`,
`length_unit_declared`, `solids`, `shells`, `faces`, `volume_mm3`, `area_mm2`,
`center_of_mass_mm`, `bounding_box_mm` (`min`, `max`), `invisible_items` when
the file marks items invisible, and `notes` when the tool has something to
say.

**Invisible items are not measured.** An AP242 file exported from Inventor
holds the bodies that are hidden in the native part and lists them in an
`INVISIBILITY` entity. The facts describe the file without them, which is the
geometry a designer sees and the geometry an AP214 export of the same part
holds; `invisible_items` is how many were left out and is absent when there
are none. The validator counts the marked items in `part.step` itself and
refuses facts whose count differs. One form of the mark is understood (styled
items listed directly in a representation); a file that hides anything else is
an error until someone has looked at it.

Facts that describe a different `part.step`, or geometry the kernel does not
find valid, are errors. A part without facts is reported. The file carries no
timestamp: measuring an unchanged file with the same tool writes nothing.

**The fingerprint** is `solids`, `volume_mm3`, `area_mm2`, `center_of_mass_mm`
and `bounding_box_mm`. Two fingerprints are the same geometry when the solid
counts are equal, volume and area agree within a relative 1e-6, and centre of
mass and box corners agree within 1e-6 mm plus 1e-6 of the part's size. These
tolerances are provisional: they have held between a shape and its own STEP
export on one kernel version, and nothing else has been tried.

## An authored part

- `build.py` defines `build(parameters)`, a pure function that returns the
  shape and reads and writes no file. Today the shape is a FreeCAD `Part.Shape`.
- `parameters.json` is the object passed to `build`. A `name` in it is the
  part's display name.
- `checks.json` states what the geometry must satisfy:

  ```json
  {"schema_version": 1, "checks": [
    {"id": "one-solid", "fact": "solids", "equals": 1},
    {"id": "outer-size", "fact": "extent_mm", "equals": [20.0, 20.0, 5.0], "tolerance": 0.001},
    {"id": "volume", "fact": "volume_mm3", "min": 1137.5, "max": 1138.5}
  ]}
  ```

  A check names a fact (`solids`, `volume_mm3`, `area_mm2`,
  `center_of_mass_mm`, `extent_mm`, `bounding_box_min_mm`,
  `bounding_box_max_mm`) and gives `equals` with an optional absolute
  `tolerance`, or `min`, or `max`, or both bounds. A malformed check is an
  error, not a failed check.
- The build command calls `build`, writes the shape as `part.step` with a
  normalised header and with the STEP product named after the key, reads the
  file back, and writes `receipt.json` and `facts.json`. Neither carries a
  timestamp, so building an unchanged part again changes no file.
- `receipt.json`: `schema_version`, `key`, `name`, `step` (as above, without
  `protocol` and `received_sha256`), `program` and `parameters` (`file` and
  `sha256`), `tool`, `reimport` (whether the file read back agrees with the
  shape that was built). A receipt whose program or parameters hash no longer
  matches the file is an error: build the part again.
- `vault.json`, once a publication is verified: `schema_version` and
  `publications`, each with `request_id`, `master_id`, `version_id`,
  `git_commit` and `step_sha256`. When `part.step` differs from the last
  publication, that is reported.

## `vault-lock.json`

An index of what the directories say, so that one file shows what an import
changed. It is derived, never a second source:

```json
{"schema_version": 2,
 "components": [{"key": "...", "path": "references/parts/...", "kind": "part", "model_state": "...",
                 "master_id": "...", "version_id": "...", "native_sha256": "...",
                 "step_sha256": "...", "step_data_sha256": "..."}],
 "publications": [{"key": "...", "path": "designs/parts/...", "request_id": "...", "master_id": "...",
                   "version_id": "...", "step_sha256": "...", "git_commit": "..."}]}
```

`components` lists every imported component, sorted by key; an assembly has
null STEP hashes. `publications` repeats the `vault.json` files.
`python3 -m mechanical_cad lock PROJECT` prints the index; the validator
requires the file to equal it.

## STEP files

Three identities, each answering one question:

- the file's SHA-256: did any byte change;
- the data-section SHA-256: did the geometry text change, whatever the header
  says;
- the fingerprint: did the geometry change, as a kernel measures it.

**The normalised header.** `FILE_NAME` has the name `part.step`, the timestamp
`1970-01-01T00:00:00`, and empty author, organization and authorisation. Its
preprocessor and originating-system strings are kept: they say which software
wrote the file. No other byte of the file is touched.
`python3 -m mechanical_cad normalise-header IN OUT` does this. The build
command always normalises. An imported file is normalised by the exporter, or
it is left as received and its `source.json` says so; the validator reports
how many headers are not normalised and how many distinct author names they
carry.

`mechanical_cad/stepfile.py` is the reference for the normalised header and
for the data-section hash. `vault-cad-tools/windows/Step-Header.ps1` is a port
for the exporter; the two were compared on 49 exported files on 2026-11-10 and
gave the same hashes and the same normalised bytes. An exporter leaves the
translator's description option empty, because that text goes into
`FILE_DESCRIPTION`, which normalising does not touch.

**Protocol.** Any of the four protocols is valid here, and `source.json`
records which one a file is. Files exported from Inventor are AP242 (Peter,
2026-11-11; the reasons on both sides are in layout-proposal.md, "Open
choices"). The files of a project exported earlier stay what they are until it
is exported again.

**Invisible items.** `part.step` is kept as the exporter wrote it, hidden
bodies included. `mechanical_cad/stepfile.py` is the reference for finding
them (`invisible_items`) and for the file without them (`visible_only`): each
marked item is taken out of the item list of the representations that hold
it, the `INVISIBILITY` entities are removed, and no other byte changes.
`python3 -m mechanical_cad visible-only IN OUT` writes that file, for someone
who wants to open a part in a CAD program that ignores the mark, as FreeCAD
does.

## The flattened scene

`python3 -m mechanical_cad flatten PROJECT --out DIR [--root KEY]` writes
`DIR/scene.json` and `DIR/assets/<key>.step`, a copy of every STEP file the
scene uses. The asset of a part whose file marks items invisible is the file
without them, and the scene records that asset's hash, so what is drawn is
what the designer sees. The scene is the `draft-1` scene of
`mechanical-docs/docs/input-contract.md`. It is derived and never committed.

- The root is the named assembly, or the only assembly no other assembly
  places.
- The root group's id is `root`. Every other id is the chain of occurrence
  names from the root, joined by `/`. These are the ids the Inventor exporter
  writes.
- A part's id is its key. Translations are in millimetres.
- Each occurrence carries its placement in its parent and in the root, whether
  that placement came from an override, and whether its parent instance is
  flexible.
- The scene's frame is the root assembly's. A `+Y` frame carries the matrix
  that takes it to `+Z` up.

`python3 -m mechanical_cad compare-scenes OLD NEW [--part-map FILE]` says
whether two scenes are the same assembly: the same parts, groups and
occurrences, with rotation cells within 1e-9 and lengths within 1e-6 of the
scene's size.

## What is not specified yet

- **The exporter's package.** What the Windows exporter delivers to the import
  command (files named by master id and model state, a child list per
  assembly) is described in the proposal and not specified here. The import
  command today reads the package the exporter wrote on 2026-10-21.
- **Hand-edited JSON.** `parameters.json`, `checks.json` and an authored
  `assembly.json` are edited by hand, and this repository's rule is TOML for
  hand-edited files. The names follow the proposal; the rule has not been
  applied to them.
- **Drawings**, and anything else a Vault file carries besides its geometry.
- **Purchased parts shared between projects.** Each project holds its own copy.
- **A key for an occurrence that survives a refresh.** Occurrence names are
  what Inventor shows; nothing ties an instruction step to an occurrence
  across a rename.
- **Suppressed and mirrored children** beyond the two rules above.
