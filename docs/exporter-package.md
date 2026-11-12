# The exporter's package: draft specification

**Status: draft 3, 2026-11-12. Reviewed against Inventor by the Windows agent
and written by an exporter for the first project; not reviewed by Peter.** It
specifies what the Windows exporter delivers for one export of one root
assembly, and what the import command does with it. In `vault-cad-tools`,
`windows/Export-Package.ps1` writes it (a script of its own; the earlier
exporter `windows/Export-PartAssets.ps1` and its package are unchanged), and
`vault-cad import-snapshot` reads both packages: the earlier one into a new
directory, this one into a new directory or into a project.

Draft 3 has the Windows review of draft 2 and the first two packages
(2026-11-12, the enclosure: 37 parts, 7 assemblies, 171 occurrences, 90 files;
two runs in two Inventor instances agree in every file but `package.json`).
What changed from draft 2:

- The exporter writes no overrides. It writes each assembly document's own
  children and, in a new file `occurrences.json`, every occurrence in the
  context of the root; the import derives the overrides. This settles the
  question draft 2 left open.
- The hash of the translator's own file is in `package.json`, not in
  `source.json`.
- A STEP file whose `FILE_SCHEMA` names more than one schema is never
  delivered.
- A suppressed occurrence, and a BOM structure the layout does not list, stop
  the export.

The layout the package feeds is in
[layout-specification.md](layout-specification.md). Where this document says
"as in the layout", the field is defined there.

## What the package is for

- The exporter identifies every file by its Vault master id and its model
  state. It never sees a key and never writes one. The import command on Linux
  assigns keys and keeps them.
- Exporting the same Vault versions twice gives the same bytes in every file
  of the package except `package.json`. Nothing but `package.json` carries a
  time, or anything that changes with one.
- No record carries a path on the workstation, a host name or an account
  name. The earlier package carried all three. The files as the translator
  wrote them, whose headers carry the native file's author, and the
  exporter's own logs stay on the workstation. Before `package.json` is
  written, and again after, the exporter searches every file of the package
  for the host name, the account, the profile and mirror paths, any path with
  a drive letter or on a share in a JSON file, and every author, organization
  and authorisation text the translator wrote into a header.
- Every native document the exporter opens is bound to the hash it was
  acquired with, and nothing is saved, as today.
- The exporter states what Inventor states and checks what only it can check
  at the source. It does not apply a rule of the layout: if the layout
  changes how it records something, the import changes and nothing has to be
  exported again.

## The tree

```
<package>/
  package.json                    what was exported, and the hash of every other file
  occurrences.json                every occurrence in the context of the root
  files/
    <master id>_<state>/          one directory per exported Vault file and model state
      source.json                 every file
      part.step                   a part
      assembly.json               an assembly
```

`<state>` is the model state in lower case, with every run of characters other
than `a` to `z` and `0` to `9` replaced by one hyphen and no hyphen at either
end: `[Primary]` gives `953898_primary`. The exporter stops if any two files
would share a directory. The directory name is a convenience; the identity is
in `source.json`.

JSON is written as the layout writes its own: UTF-8 without a byte-order mark,
LF, a list of scalars on one line, and a number so that reading it back gives
the same double. The import also reads a file with a byte-order mark and CRLF.

## `package.json`

| Field | Meaning |
| --- | --- |
| `schema_version` | `2` |
| `kind` | `"vault-cad-export-package"` |
| `exported_at` | UTC time the export finished |
| `exporter` | `name`, `version` (the commit of `vault-cad-tools` it ran from, null when git cannot be asked), `working_tree_modified` (whether what ran differs from that commit), `inventor` (the product version string) |
| `translator_options` | the STEP translator's options as they were set, by name |
| `vault_id` | the vault the files came from |
| `root` | `master_id`, `version_id`, `model_state` of the root assembly |
| `acquisition` | `captured_at` (when the exact versions were frozen), `acquired_at` (when the files were downloaded) and `method` |
| `counts` | `parts`, `assemblies` |
| `not_exported` | a list of `master_id`, `model_state`, `reason`: a referenced document that no occurrence places, and a file of the acquisition that Inventor did not open; empty when there is none |
| `translator_outputs` | for each `part.step`, `sha256` and `bytes` of the file as the translator wrote it, before the header was normalised |
| `files` | an object: the path of every other file in the package, with `sha256` and `bytes` |

The package is complete only when `package.json` exists; the exporter writes
it last, after it has checked the rest of the package against itself, and
checks once more with it. A run that fails leaves no `package.json`, and
neither does a run in which the exporter's watchdog had to dismiss a dialog
of Inventor: what was dismissed is only in the exporter's receipt, which
stays on the workstation, and a package that says it is complete must not
rest on something its reader cannot check.

The translator's file carries the time of the export in its header, so its
hash changes with every run. That is why it is here and not in `source.json`.

## `source.json`

The layout's `source.json` without `key` and without `export.run`, which the
import command adds. In particular:

- `vault`: all nine fields, from the records of the acquisition itself
  (`acquisition.json` for the hash of the downloaded file, the dependency
  inventory for the rest, as Vault returned them when the versions were
  frozen). The exporter makes no Vault request. `path` is the Vault path. It
  is required, and it can run through folders that are named after a lab or
  a person; whether such names may be in a public repository is not settled
  ([direction.md](direction.md)).
- `step` (parts): all seven fields, with `header_normalised` true and
  `received_sha256` null, because the exporter normalises before it delivers.
- `export`: `translator_result`, what the translator reported. Nothing that
  changes from one run to the next.
- `properties`: category, description, manufacturer, material, part number,
  stock number, title and vendor, for parts and assemblies. A property that
  Inventor returns as an empty text is written as an empty text: it exists and
  is empty. The exporter does not write the properties that name people
  (author, designer, engineer, checked by, creator). Whether such names may
  be in a public repository is not settled; leaving them out can be reversed
  by one export.
- `native`, for a part: the document's length unit, `extent_mm`, `volume_mm3`
  and `bodies` (`solid_bodies`, `visible_solid_bodies`, `surface_bodies`), and
  - `parameters`: name, kind (`model`, `reference`, `user`, `other`),
    expression, units, value, value_text, comment, is_key,
    exposed_as_property. `value` is in Inventor's database units (centimetre,
    radian), which `parameter_values` says in the file; `value_text` is the
    same value in the parameter's own unit.
  - `holes`: name, suppressed, hole_type, extent_type, extended_name, tapped,
    diameter, depth_cm, counterbore, countersink, spotface, thread, clearance,
    centres_mm, repeated_by. A tapped hole has `"diameter": null` and its size
    in `thread`; `thread.unit` states the unit of the thread standard (`in`
    or `mm`); `repeated_by` names the mirror and pattern features that repeat
    the hole.
  - `patterns`: each mirror or pattern feature with its type, the features it
    repeats and `instances`, the number of its elements that are not
    suppressed, the original included. A hole count is the hole's centres
    times the instances of each feature in `repeated_by`.
  - A part without features has empty lists. A value the API does not return
    is null, never 0 or an empty text. A failure to list the parameters or
    the features of a part stops the export.
- `native`, for an assembly: its length unit, how often it is placed in this
  export, the number of its children, and its own active design view
  representation, positional representation and level of detail.
- `materials`: the claim per part and body of
  `vault-cad-tools/docs/authoring-and-materials.md`, 4.1, or null until the
  exporter records it. It is null in every file so far.

## `assembly.json`

The layout's `assembly.json` without `key` and without `overrides`, with each
child naming its component by identity. It holds what the assembly document
itself defines, read from the document and not from one of its instances:

- `master_id` and `model_state` are required, and `component` is absent. The
  import command writes `component` from them.
- `name`, `kind`, `transform`, `bom_structure` and the five flags are as in
  the layout, every one stated. `length_unit` is the unit the transforms are
  written in; the exporter keeps Inventor's centimetres.
- An assembly document is written once, whatever the number of its instances.
  The exporter stops if an instance does not have exactly the children its
  document defines, in the same order.
- The root's `assembly.json` states the frame, `handedness` and `up_axis`.
  This is the exporter's declaration of Inventor's convention, not something
  read from the document.
- The exporter stops on a suppressed occurrence. Inventor does not load the
  document of a suppressed occurrence, so nothing can be exported from it in
  the same session and most of its properties cannot be read. No project has
  had one; how a suppressed child is written (most likely with `suppressed`
  true and its component under `not_exported`) waits for a case to try it on.
- The exporter stops on a placement that is not a rotation and a translation
  within 1e-9 (a mirrored occurrence), and on a BOM structure the layout does
  not list (Inventor has a seventh value, `Varies`).

## `occurrences.json`

Every occurrence in the context of the root, as Inventor states it:

```
{"schema_version": 1, "root": {"master_id", "model_state"}, "length_unit": "cm",
 "tolerance": {"rotation_cell": 1e-09, "length": 1e-07},
 "counts": {"occurrences", "parts", "assemblies", "differ_from_definition"},
 "occurrences": [{"path": ["CAMERA FRAME:1", "PIN:2"], "kind", "master_id", "model_state",
                  "transform": 4x4 in its parent occurrence, "transform_root": 4x4 in the root,
                  "differs_from_definition": true or false,
                  "bom_structure", "visible", "suppressed", "grounded", "flexible", "mirrored"}]}
```

in the order Inventor lists them, a parent before its children. The flags are
those of the occurrence in context.

Why this file and not `overrides`: Inventor states two things, each assembly
document's own children and every occurrence in the root's context. An
override is the difference between the two, attached to a flexible instance by
a rule of the layout; Inventor has no object for it. A flexible sub-assembly
is solved in its parent, and the result is visible only as the placements in
context. (Inventor's own STEP export of an assembly shows the same: it writes
a flexible sub-assembly with the placements it has in context.)

What the exporter guarantees, because only it can check these at the source:

1. Every instance of an assembly document has exactly the children its
   document defines.
2. `differs_from_definition` is decided once, with the tolerance the file
   states (a rotation cell 1e-9, a length 1e-7 cm), so the import needs no
   tolerance of its own.
3. An occurrence that differs has a flexible occurrence above it. Nothing
   else can move a child in what the exporter accepts, so it stops otherwise.

## The STEP files

- AP242 (`ApplicationProtocolType` 5), sketches not included, every other
  translator option at its default, and the translator's description, author,
  organization and authorisation options empty. The translator reports eight
  options; `translator_options` in `package.json` records all eight.
- Exported from documents that have no view. The exporter opens the root
  invisibly in its own Inventor instance, and then neither the root nor any
  document it refers to has a view. It asks every opened document for its
  views before anything is read and stops if one has a view. Why: without a
  view the translator writes a fixed default camera, and ten exports of a
  part from six Inventor instances on two days had one data section; with a
  view it writes that view's camera, and the data section changes whenever
  the camera does. The camera is not rewritten afterwards: the data section
  stays the translator's.
- `FILE_SCHEMA` names the AP242 schema and no other. On 2026-11-12 the
  translator wrote, for four of 215 exports and for an unchanged data
  section, a second schema name in front of it (`AUTOMOTIVE_DESIGN`,
  `FEATURE_BASED_PROCESS_PLANNING`, `PROCESS_PLANNING_SCHEMA`). Why is not
  known; it was seen only in runs of the new exporter and in none of 203
  exports by the other scripts. The exporter exports such a part again, three
  times at most, requires the same data section each time, and records every
  attempt in its receipt. It never repairs a header and never delivers such a
  file. On Linux `stepfile.py` gives a file with two schema names no protocol
  and the validator refuses it.
- The header is normalised with `Set-StepFileHeader` of
  `windows/Step-Header.ps1` under the name `part.step`, which gives the bytes
  `stepfile.py` gives. An AP242 header has a second, constant
  `FILE_DESCRIPTION` string naming a recommended practice for PMI; it stays.
- Bodies hidden in the native part are in the file, marked invisible. None of
  the translator's options leaves them out. Linux leaves them out when it
  measures and draws (`stepfile.py`, `visible_only`), and understands one form
  of the mark; the exporter stops if a file has an `INVISIBILITY` in another
  form (`Get-StepInvisibility` in `Step-Header.ps1` is the text-level check).
- A solid with an internal void is a `BREP_WITH_VOIDS`, not a
  `MANIFOLD_SOLID_BREP`. Whatever counts solids in the text of a file to
  compare them with `native.bodies` counts both. A count that differs is a
  warning in the exporter's receipt, not a stop.

## What the import command does with it

`vault-cad import-snapshot PACKAGE --into PROJECT --run RUN`
(`vault-cad-tools/src/vault_cad_tools/package_import.py`). It checks the whole
package and the project before it writes anything:

1. Every file is verified against `package.json`, and nothing may be in the
   package that `package.json` does not list. The vault and the root assembly
   are compared with the project's `vault-project.toml`. The project's
   directories must be what its index says they are.
2. `occurrences.json` is checked against the assembly documents, and the
   overrides are derived from it:
   - every occurrence is the child its parent's document defines under that
     name, a parent comes before its children, and every assembly occurrence
     has all the children its document defines;
   - `differs_from_definition` agrees with the two placements, and
     `transform_root` is the parent's placement in the root times the
     occurrence's own, both within the file's tolerance;
   - each occurrence that differs becomes an override on the nearest flexible
     occurrence above it, in the manifest of the document that places that
     occurrence, with the path from there and the placement in its parent.
   Refused, because the layout cannot record it or this import does not
   write it: a flag or a BOM structure that differs in context from the
   document; a difference with no flexible occurrence above it; instances of
   one document that would need different overrides (an override on an outer
   instance); a child entry that carries `overrides`; placements in another
   unit than the manifests.
3. Each file's key is found by master id and model state in the project's
   index. A file the project does not have yet gets a key from its name, one
   that no imported or authored component has.
4. The package is refused when the project holds a later version of one of
   its files (by version number), and when the order of two versions cannot
   be told because a version number is unknown.
5. A component's directory is left untouched when its version id, its native
   hash, its STEP bytes and the exporter's record of it are what the project
   has. The record is `source.json` without its `export` block, and for an
   assembly its children with their overrides. An unchanged file therefore
   keeps pointing at the export it first came from, and a refresh changes
   only what changed. What is not unchanged is reported as updated (a new
   Vault version) or rewritten (the same version, exported differently) and
   replaced.
6. The components of the project that the package does not have are
   reported. Nothing is removed; removal on request is not built.
7. `package.json` and `occurrences.json` are kept, unchanged, under
   `references/receipts/<run>/`, and the index is derived again. `facts.json`
   is left alone: the result names the parts whose `part.step` changed, for
   `tools/step_facts.py` to measure.

After it: `tools/step_facts.py`, `validate`, and `compare-scenes` between the
scene flattened before and after. When the STEP files are another export of
the same versions, as in the change from AP214 to AP242, every one differs:
`compare-scenes --other-export` then lists them and compares everything else,
and `tools/compare_step_exports.py` compares their geometry.

Tried on 2026-11-12 with the first package the exporter wrote, on Linux:

- Into an empty directory: 37 parts and 7 assemblies new, 44 overrides
  derived (32 on `CAMERA FRAME:1`, 12 on `FREE STANDING FRAME:1`).
- Into a copy of the converted enclosure: all 44 files rewritten, every key
  kept, the vault and the root checked against `vault-project.toml`. After
  `step_facts.py` (37 parts measured, all valid) the copy validates without
  an error, and the finding about headers that are not normalised is gone.
  Its flattened scene equals the branch's: 37 parts, 17 assembly nodes, 155
  occurrences, no placement differing by anything, the 37 STEP files
  different. Those 37 are, byte for byte, the AP242 files whose geometry was
  compared with the tracked AP214 files on 2026-11-11 (37 of 37 the same).
- The copy against Inventor's own STEP export of the root assembly
  (`tools/compare_assembly_step.py`): 479 of 479 solids where the imported
  records put them, within 6.4e-11 mm.
- The package's second run differs from the first in `package.json` only, in
  `exported_at` and `translator_outputs`.

Not done: the import into the enclosure's branch itself.

## Not in the package

- The BOM views of the assemblies and virtual components. They stay with the
  audit (`Audit-NativeBom.ps1`).
- Drawings.
- A key for an occurrence that survives a rename. Inventor's reference key of
  an occurrence can be read without making a document dirty and is the same
  in two sessions, but two occurrences of the enclosure have the same key
  (`TANK SUPPORT FRAME:1` and `:2`; why is not known), so it does not name
  one occurrence.
- The files of the Vault folder that the root assembly does not use. Which
  files a project mirrors is not settled.

## Not met on real data

The exporter's stops for a document with a view, an `INVISIBILITY` in another
form, a suppressed occurrence, a difference without a flexible occurrence
above it, instances with other children than their document, and an unknown
BOM structure have never fired on real data; the ones the package check
repeats are exercised offline. Not met in the enclosure: a model state other
than the primary one, a flexible instance inside a flexible instance, an
override more than one level below its instance, two instances of one
document posed differently, a referenced document that no occurrence places,
thread features, patterns of holes other than a mirror, user parameters and
sheet metal. Both packages come from one workstation on one day.
