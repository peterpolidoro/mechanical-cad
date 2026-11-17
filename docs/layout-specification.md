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
    build.py                   people and agents      } the part's source: a program with its
    parameters.json            people and agents      } parameters, or
    part.FCStd                 people                   a document drawn in FreeCAD, or
    origin.json                supply command           a file from outside; one of the three
    checks.json                people and agents (optional)
    interface.json             people and agents, or a command (optional)
    README.md                  people and agents (optional)
    part.step                  build command; the supply command for a supplied part
    receipt.json               build command; a supplied part has none
    facts.json                 build command; the facts command for a supplied part
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
| facts | `facts.json` of every mirrored part and of every supplied part | `tools/step_facts.py`, run by FreeCADCmd with the OCP bindings |
| supply | `part.step` and `origin.json` of a supplied part | `python3 -m mechanical_cad add-supplied` |
| board interface | `interface.json` of a supplied circuit board | `tools/board_interface.py`, run by FreeCADCmd |
| build | `part.step`, `receipt.json`, `facts.json` of an authored part | `tools/build_part.py`, run by FreeCADCmd with the OCP bindings |
| publication record | `vault.json` of an authored part, and the `publications` of `vault-lock.json` | `vault-cad-tools` (`vault-cad import-publish-result`) |
| validate, check, flatten, assemblies | nothing in the repository | `python3 -m mechanical_cad` |
| whole-assembly STEP | `.cache/assemblies/`, which the project ignores | `tools/assembly_step.py`, run by FreeCADCmd |
| pictures | `.cache/pictures/`, which the project ignores | `tools/picture.py`, run with the `f3d` viewer |
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
measured), `tool` (`name`, `version`, `kernel`, `kernel_version`,
`integration`), `valid`, `length_unit_declared`, `solids`, `shells`, `faces`,
`volume_mm3`, `area_mm2`, `center_of_mass_mm`, `bounding_box_mm` (`min`,
`max`), `invisible_items` when the file marks items invisible, `notes`
when the tool has something to say, and, for an authored part whose checks
name points, `points`: what the kernel found at each ("An authored part").

**Volume, area and centre of mass are by the kernel's adaptive integration**,
asked for a relative tolerance of 1e-7; `tool.integration` says so (`method`,
`relative_tolerance`, `bindings`, `bindings_version`), and a note says when a
solid did not reach the tolerance. FreeCAD reads the file and counts, and
hands the shape to the OCP bindings of the same kernel for the integration,
because its own `Volume` is the kernel's plain integration over the faces.
That one was 0.8 % low in volume, and 4 mm off in the centre of mass, for a
spring whose surface is a B-spline spiral (the first project, 2026-11-13,
against Inventor and a fine mesh); for its other 36 parts the two agree
within 5e-5. Facts without `tool.integration` were measured the plain way;
the validator points them out, and the facts command measures them again.

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
export on one kernel version, and nothing else has been tried. One part of
the first project reaches a relative error of 2e-5 in the integration, not
the 1e-7 asked; two exports of such a part may differ by more than 1e-6.

## An authored part

- `build.py` defines `build(parameters)`, a pure function that returns the
  shape and reads and writes no file. The shape is a FreeCAD `Part.Shape`, or
  a shape of build123d (anything whose `wrapped` is a `TopoDS_Shape` of the
  OCP bindings, or such a shape itself). The build command hands the second
  kind to FreeCAD as BREP, so one kernel writes and measures every part.
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

  A check may instead name a point of the part, in the part's own frame and
  in millimetres, and say what is there (2026-11-16):

  ```json
    {"id": "hole-upper-right", "point": [50.0, 55.475, -56.5], "is": "empty"},
    {"id": "pad-at-61-5", "point": [55.0, 60.475, -61.4], "is": "material"}
  ```

  `is` is `material` or `empty`. That is how a part states an interface: a
  hole where a pattern has one, a face at a given depth (material just under
  it, empty just above), an opening of a given width. The build command asks
  the kernel what the file read back has at every point its checks name and
  records the answers in `facts.json` as `points`, each `{"point", "is"}`
  with `is` one of `material`, `empty` and `surface`. A point within 1e-6 mm
  of a face is `surface`, which satisfies neither: a check names a point
  clear of the surface. The checks are then read without a kernel. A point
  added to `checks.json` after the build is not known, and its check fails
  until the part is built again.
- The build command calls `build`, writes the shape as `part.step` with a
  normalised header and with the STEP product named after the key, reads the
  file back, and writes `receipt.json` and `facts.json`. Neither carries a
  timestamp, so building an unchanged part again changes no file.
- `receipt.json`: `schema_version`, `key`, `name`, `step` (as above, without
  `protocol` and `received_sha256`), `program` and `parameters` (`file` and
  `sha256`), `tool`, `reimport` (whether the file read back agrees with the
  shape that was built). When the program built its shape with a library
  other than the tool, `tool.library` names it: `name`, `version`,
  `bindings` and `bindings_version`. A receipt whose program or parameters
  hash no longer matches the file is an error: build the part again.
- **A drawn part** (Peter, 2026-11-16) has `part.FCStd`, a FreeCAD document,
  where a programmed part has `build.py` and `parameters.json`. A part has
  one source; a directory with a document and either of the two files is an
  error. Everything else is the same for both: `checks.json`, the three
  files the build command writes, `vault.json`, how an assembly places the
  part and how it is published.
  - The build command opens the document, computes every object in it
    again and closes it without saving: it never writes the document. The
    part is the one object that has a solid and that nothing else in the
    document uses, a body, a part container or the last of a chain of
    features. Sketches, planes and sheets that are left over have no solid
    and do not count. An object that does not compute, no such object, and
    more than one are refused: a part is one thing, and the document does
    not say which.
  - `receipt.json` has `document` in place of `program` and `parameters`:
    `file`, `sha256`, and the object exported (`object`, `label`, `type`).
    `name` is that object's label.
  - A FreeCAD document is a compressed archive: Git cannot compare two
    versions of it, and saving it again gives another file even when
    nothing in it changed. So the receipt goes stale with every save and
    the part is built again, which gives the same `part.step` when the
    solid is the same; a review reads the STEP file's facts and a picture,
    not the document.
- `vault.json`, once a publication is verified: `schema_version` and
  `publications`, each with `request_id`, `master_id`, `version_id`,
  `git_commit` and `step_sha256`. When `part.step` differs from the last
  publication, that is reported.

## A supplied part

A third source of a part (Peter, 2026-11-17): a STEP file that came from
outside, a supplier's model or a circuit board's, kept as it came. It lives in
`designs/parts/<key>/` like the other two, and nothing builds it.

- `python3 -m mechanical_cad add-supplied PROJECT KEY FILE` with the origin
  puts it there. `part.step` is the file with its header normalised; its data
  section is byte for byte what was received, so names, colours and the
  structure inside the file are kept. Such a part may be many solids. The
  command fetches nothing: the file is a path on the machine, and what is
  recorded of its origin is what the caller says.
- `origin.json`: `schema_version`, `key`, `name`, `step` (as in
  `source.json`, with `received_sha256`, the hash of the file as it came) and
  `origin`:

  ```json
  {"kind": "supplier", "supplier": "McMaster-Carr", "part_number": "5537T879", "url": null,
   "retrieved": "2026-11-16", "licence": null, "publishable": true}
  {"kind": "repository", "repository": "https://github.com/OWNER/board", "commit": "b58cd3f",
   "path": "docs/generated/3d/board-assembled.step",
   "retrieved": "2026-11-17", "licence": "CC-BY-SA-4.0", "publishable": true}
  {"kind": "other", "description": "measured and drawn by the workshop", ...}
  ```

  `retrieved` is the day the file was taken. `publishable` says whether the
  file may be in a public repository: `true`, `false`, or `null` when nobody
  has said; the validator reports the last two. A `note` may say more.
- A supplied part has no `receipt.json`, no program and no document; a
  directory with `origin.json` and any of those is an error. The facts
  command measures it. `checks.json`, `interface.json`, `vault.json` and how
  an assembly places the part are as for any other part.
- A newer file of the same part is added over the old one with `--replace`.
  The key stays, and every part built against it is then stale.

## The interface of a part

`interface.json`, optional for a part under `designs/`, states the named
features that other parts are designed to, in the part's own frame and in
millimetres: where a board's mounting holes are, where a connector sits and
from which side something enters it, how high its parts reach.

```json
{"schema_version": 1, "key": "the-board", "length_unit": "mm",
 "frames": {"board": {"transform": [[1,0,0,137.425],[0,1,0,-95.0],[0,0,1,1.51],[0,0,0,1]],
                      "note": "origin at the middle of the outline, on the top face"}},
 "features": [
   {"id": "h101", "kind": "hole", "center": [92.425, -60.0, 1.51], "axis": [0, 0, 1], "diameter": 3.2, "through": true},
   {"id": "top", "kind": "plane", "point": [137.425, -95.0, 1.51], "normal": [0, 0, 1]},
   {"id": "j201", "kind": "port", "box": {"min": [90.1, -111.0, 1.51], "max": [94.7, -100.9, 8.0]},
    "direction": [0, 0, 1], "accepts": "USB-C plug", "reference": "J201"},
   {"id": "parts-above", "kind": "keep_out", "box": {"min": [87.4, -135.0, 1.51], "max": [187.4, -55.0, 18.1]}}]}
```

- A feature has an `id`, unique in the file (lower-case letters and digits
  joined by `-`, `_` or `.`), and a `kind`:

  | Kind | Fields | Meaning |
  | --- | --- | --- |
  | `hole` | `center`, `axis`, `diameter`; `depth`, `through` | `center` is where the axis meets the face the hole is drilled from, and `axis` points out of the material there |
  | `plane` | `point`, `normal` | a face to mate with or to measure from; `normal` points out of the material |
  | `outline` | `point`, `normal`, `x`, `polygon`; `corner_radius` | a closed outline in the plane through `point`, its points given along `x` and `normal` x `x` |
  | `port` | `box`, `direction`; `accepts` | where something plugs in; `direction` points the way out, so what plugs in comes against it |
  | `keep_out` | `box` | a volume nothing else may enter |
  | `point` | `point` | a datum |
  | `axis` | `point`, `direction` | a datum line |

  Vectors named `axis`, `normal`, `direction` and `x` are unit vectors. A
  `box` has `min` and `max`. Any feature may carry `note`, `reference` (the
  name the part's own documents use, a connector's J201) and `expect`.
- `frames` names frames other than the part's own. A frame's `transform` is a
  4 x 4 matrix, rigid, that takes a point given in the named frame to the
  part's frame. Features are always given in the part's own frame.
- **The interface is held to the solid.** A hole must be empty on its axis,
  at half its depth or 0.01 mm inside the face when no depth is given; and
  `expect` lists points of a feature that must be `material` or `empty`.
  These are point checks like those of `checks.json`, with ids that begin
  `interface:`: the build command, or the facts command for a supplied part,
  looks at the points and records them in `facts.json`, and `check` reads
  them. A malformed interface is an error.
- It is written by hand, or by a command: `tools/board_interface.py` writes
  a circuit board's from the files its repository generates.
- Not yet for a part under `references/`, where nothing is added by hand.

## Inputs: a part built against other parts

A programmed part may be built against other parts of the project, an
enclosure against the board it holds (Peter, 2026-11-17).

- `parameters.json` names them: `"inputs": {"board": "the-board"}`, the name
  the program uses and the key of a part, mirrored, authored or supplied.
- The program is then `build(parameters, inputs)`. `inputs["board"]` has
  `key`, `name`, `facts` (the part's `facts.json`), `interface` (its
  `interface.json`, or nothing), and the solid: `shape()` for FreeCAD's Part
  module, `build123d()` for build123d, read without the items the file marks
  invisible. The program still opens no file itself.
- `receipt.json` gets `inputs`: for each, `name`, `key`, `step_sha256` and
  `interface_sha256` (null when the input has no interface). When either file
  of an input has changed since, the validator says the part is to be built
  again.
- An input has to validate before a part is built against it, so parts are
  built in the order of their inputs: `python3 -m mechanical_cad build-order
  PROJECT [KEY ...]` prints it. Inputs that go in a circle are an error.

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
is exported again. A file names one schema in `FILE_SCHEMA`: one that names
more is an error, and has no protocol (Inventor's translator has been seen to
put a second, unrelated name in front of the AP242 one; the exporter does not
deliver such a file).

**Saved view.** An AP242 file exported from Inventor carries a camera
(`CAMERA_MODEL_D3` and what it reaches). From a document that has no view it
is a fixed default camera, and the file is the same in every session; from a
document that has a view it is that view's camera. A file exported for a
repository comes from a document without a view, which the exporter checks
([exporter-package.md](exporter-package.md)). Normalising does not touch the
camera, and nothing here reads it.

**Invisible items.** `part.step` is kept as the exporter wrote it, hidden
bodies included. `mechanical_cad/stepfile.py` is the reference for finding
them (`invisible_items`) and for the file without them (`visible_only`): each
marked item is taken out of the item list of the representations that hold
it, the `INVISIBILITY` entities are removed, and no other byte changes.
`python3 -m mechanical_cad visible-only IN OUT` writes that file, for someone
who wants to open a part in a CAD program that ignores the mark, as FreeCAD
does.

## Line endings

The layout records the SHA-256 of files: `part.step`, and for an authored
part `build.py` and `parameters.json`, or `part.FCStd`. So a checkout has to give the same
bytes on every platform, and Git for Windows does not do that by itself: as
installed it writes CRLF into every file it takes for text, and a STEP file is
text. A project repository therefore has these lines in its `.gitattributes`:

    * text=auto eol=lf
    *.step -text -diff -merge
    *.stp -text -diff -merge
    *.STEP -text -diff -merge
    *.STP -text -diff -merge
    *.FCStd -text -diff -merge
    /references/receipts/** -text

The first line stores text with LF and checks it out with LF whatever the
workstation's Git is set to. The STEP lines keep geometry byte for byte. The
last keeps the exporter's records as it wrote them, CRLF and byte-order mark
included. A setting on one workstation is no substitute: `core.autocrlf=false`
with `text=auto` alone still gives CRLF on Windows, and the next person's
checkout would be wrong again.

When a file differs from its record only in line endings, the validator says
so in its first error and names the files; the other errors about them follow
from it, and nothing is to be built or measured again. After `.gitattributes`
is corrected, files that are already checked out stay as they are. In a
checkout without uncommitted changes, `git rm --cached -r -q .` followed by
`git reset --hard` writes every tracked file again and leaves untracked and
ignored files alone; a fresh clone does the same.

Found on 2026-11-12, when the enclosure was first validated on Windows: 29
text files came out with CRLF, `build.py` of its authored part among them,
and the fixture of this repository, which then had no `.gitattributes`, gave
16 errors. Reproduced on Linux in clones with `core.autocrlf=true`, and gone
there with the lines above.

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
scene's size. A STEP file that differs is a difference. With `--other-export`
it is listed and not counted: the new scene is then another export of the
same Vault versions, whose files differ in every byte, and their geometry is
compared with `tools/compare_step_exports.py`.

## A STEP file of a whole assembly

An assembly is stored as its parts' STEP files and its manifest, never as a
STEP file of its own: such a file repeats the geometry of every part below
it, and would be a second source that can disagree with the first. When one
is wanted, to look at the assembly in FreeCAD or to hand it to someone, it is
derived:

    FreeCADCmd tools/assembly_step.py --pass PROJECT [KEY] [-- --out DIR] [-- --frame own] [-- --force]

writes `KEY.step`, `KEY.FCStd` and `KEY.json` for the assembly KEY (any
assembly of the project; by default the one the scene would be flattened
from). They go to `PROJECT/.cache/assemblies/` unless `--out` names another
directory. That default is a proposal (2026-11-11): beside what they derive
from and kept between sessions, in a directory the project's `.gitignore`
lists and the validator does not look into. They are never committed.

- The file is the flattened scene of KEY: each part file read once, without
  the items it marks invisible; one instance per visible occurrence. Geometry
  is shared between the instances of a part.
- A sub-assembly is one product, named after its file, and every instance of
  it that holds the same parts in the same places is a usage of that product,
  as the mirrored CAD system has one document for them. An instance that
  differs, because a flexible assembly places something in it differently,
  has a product of its own, named after the file with a number. That is the
  STEP file. In `KEY.FCStd` every instance is a container of its own: in
  FreeCAD what is hidden inside a container is hidden in every link to it,
  and one instance could not be hidden or looked into without the others.
- `--frame z-up`, the default, applies the scene's turn to `+Z` up; `--frame
  own` keeps the assembly's own frame.
- The STEP header is normalised. Building the same scene again with the same
  tool gives the same bytes, and nothing is built when `KEY.json` describes
  the scene, the frame, the tool and the STEP file that is there.
- Before the files are kept the STEP file is read back and every solid in it
  is matched with where the scene puts it: the same volume within one part in
  a thousand and the centre of mass within 0.01 mm
  (`mechanical_cad/solids.py`). `KEY.json` holds that check.
- Every usage of a component in the STEP file
  (`NEXT_ASSEMBLY_USAGE_OCCURRENCE`) has its occurrence's name as its name
  and as its id. Inventor shows the id as the occurrence's name, where
  OpenCASCADE writes a running number; and FreeCAD numbers a label anew when
  its document has it already, where an occurrence's name need only be its
  own among its parent's children. The build puts both right in the file's
  text (`mechanical_cad/stepfile.py`, `name_usages`). A part's product is
  named after the part; a CAD system names its documents after the products.
- The files hold positions and shapes. They hold no constraints or joints, no
  features, and no colour.
- Inventor 2025 opens such a file as an assembly in millimetres with every
  occurrence where the manifests put it (2026-11-13, the first project: 171
  occurrences within 7e-10 mm, 479 solid bodies). It shows the names of the
  usages (a second read that day: all 171 paths are the exporter's). It
  makes one document of each product and places it once for every usage (a
  third read that day, of the file with shared products: 8 assembly
  documents, as many as the native design has plus the added level, where a
  product per instance gave 18; the same occurrences, names and placements).
  The root document is named after the STEP file, not after the root
  product.
- `KEY.FCStd` opens in the FreeCAD window with the assembly shown, upright
  and in view, the first level of its tree open, and the part files the
  occurrences link to hidden in a group of their own. FreeCADCmd has no
  window and saves no view data, and a document without them opens with
  every object hidden, so the build appends them (`mechanical_cad/fcstd.py`;
  observed with FreeCAD 1.1.3).
- `python3 -m mechanical_cad built PROJECT [KEY] [--step] [--dir DIR]` prints
  the path of the document (or of the STEP file) when it is current, and
  fails when it is not.

`FreeCADCmd tools/compare_assembly_step.py --pass PROJECT KEY OTHER.step
OUT.json` runs the same match on a file something else wrote, in the
assembly's own frame: the mirrored CAD system's export of its assembly
document is an independent check of the recorded placements.

Which assemblies there are to build is read from the project, not kept in a
list: `python3 -m mechanical_cad assemblies PROJECT [--dir DIR] [--json FILE]`
prints every assembly under `references/assemblies/` and
`designs/assemblies/`, the ones no other assembly places first, each with its
key, the name of its file, how many different parts and how many visible
occurrences it holds, which assemblies place it, and the state of its built
files in DIR (default `PROJECT/.cache/assemblies/`): `not built`, `current`
(built from the records as they stand, and the STEP file is the one the
report names) or `out of date`. Every assembly listed can be built; a key
that is not one is refused with the list of those that are.

## Short commands in a project

A project may have a Makefile so that nobody has to compose the commands
above. This repository's own Makefile runs them for a project named as
`PROJECT=DIR` (`make` alone lists its targets), and a project hands its
targets to it:

```make
# Where the mechanical-cad checkout is: beside this repository, or what local.mk (ignored) or the environment says.
-include local.mk
MECHANICAL_CAD ?= ../mechanical-cad
MECHANICAL_CAD_MAKE = $(MAKE) --no-print-directory -C "$(MECHANICAL_CAD)" PROJECT="$(CURDIR)"

.PHONY: validate check assemblies assembly open picture part fit
validate check assemblies:
	@$(MECHANICAL_CAD_MAKE) $@

part:
	@$(MECHANICAL_CAD_MAKE) $@ KEY="$(KEY)"

fit:
	@$(MECHANICAL_CAD_MAKE) $@ KEY="$(KEY)" SUBJECT="$(SUBJECT)" CLEARANCE="$(CLEARANCE)"

assembly open:
	@$(MECHANICAL_CAD_MAKE) $@ KEY="$(KEY)"

picture:
	@$(MECHANICAL_CAD_MAKE) $@ KEY="$(KEY)" VIEWS="$(VIEWS)" UP="$(UP)"
```

Inside the project, `make part KEY=<key>` builds an authored part,
`make check` evaluates every part's checks and `make fit KEY=<assembly>
SUBJECT='NAME[,NAME]'` says whether those children of an assembly fit among
the rest ([adding-a-part.md](adding-a-part.md) walks through them).
`make assemblies` lists what can be built,
`make assembly` builds the top-level assembly and `make assembly KEY=<key>`
any other. `make open`, with or without a key, builds the assembly if its
files are not current and opens the FreeCAD document in the FreeCAD window
that `guix shell` provides; FreeCAD stays in the foreground and the command
returns when the window is closed, so it is a command for a person at the
machine, not for an agent. `make picture KEY=<key>` is the one for an agent,
and for a person in a hurry: it draws a part, or an assembly that is built,
to images in the project's ignored `.cache/pictures/` without a window
(`tools/picture.py`; `VIEWS=iso,below,+x` says where the camera stands and
`UP=+Y` which axis points up). `local.mk` holds what differs between machines (one line,
`MECHANICAL_CAD = /path/to/mechanical-cad`) and is listed in the project's
`.gitignore`. The Makefile is a convenience and not part of the layout: the
validator does not look at it, and where there is no `make` the commands
above do the same.

## What is not specified yet

- **The exporter's package.** What the Windows exporter delivers to the import
  command has a draft of its own, [exporter-package.md](exporter-package.md):
  files named by master id and model state, a child list per assembly, no
  workstation paths. It is not reviewed by Peter and no exporter writes it
  yet; the import command reads it and the package the exporter wrote on
  2026-10-21.
- **Hand-edited JSON.** `parameters.json`, `checks.json` and an authored
  `assembly.json` are edited by hand, and this repository's rule is TOML for
  hand-edited files. The names follow the proposal; the rule has not been
  applied to them.
- **Drawings**, and anything else a Vault file carries besides its geometry.
- **Purchased parts shared between projects.** Each project holds its own copy.
- **A supplied assembly.** A supplied part is one file and one component,
  however many solids it holds. Taking a STEP file of an assembly apart into
  parts and placements is not built.
- **A display model beside a supplied part**, the glTF file a board's
  repository generates, for pictures with real finishes.
- **A key for an occurrence that survives a refresh.** Occurrence names are
  what Inventor shows; nothing ties an instruction step to an occurrence
  across a rename.
- **Suppressed and mirrored children** beyond the two rules above.
