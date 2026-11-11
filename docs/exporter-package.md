# The exporter's package: draft specification

**Status: draft 2, 2026-11-11, not reviewed by Peter or by the Windows agent.
No exporter writes it yet.** It specifies what the Windows exporter delivers
for one export of one root assembly, and what the import command does with
it. The exporter in `vault-cad-tools` (`windows/Export-PartAssets.ps1`) writes
an earlier package today. `vault-cad import-snapshot` reads both: the earlier
one into a new directory, and since 2026-11-11 this one into a new directory
or into a project (provisional, tested on packages written on Linux).

Draft 2 has the results of the Windows AP242 tests of 2026-11-11
([layout-proposal.md](layout-proposal.md), "Windows tests of 2026-11-11"): the
two statements that draft 1 marked as waiting for that report are confirmed,
and the rule about views under "The STEP files" is new. The section on the
import command was rewritten later that day, when the command was built;
what the exporter delivers is as the Windows agent was given it.

The layout the package feeds is in
[layout-specification.md](layout-specification.md). Where this document says
"as in the layout", the field is defined there.

## What the package is for

- The exporter identifies every file by its Vault master id and its model
  state. It never sees a key and never writes one. The import command on Linux
  assigns keys and keeps them.
- Exporting the same Vault versions twice gives the same bytes in every file
  of the package except `package.json`. Nothing but `package.json` carries a
  time.
- No record carries a path on the workstation, a host name or an account
  name. The earlier package carried all three. The files as the translator
  wrote them, whose headers carry the native file's author, and the
  exporter's own logs stay on the workstation; the package holds the hash of
  each translator output and nothing else of it.
- Every native document the exporter opens is bound to the hash it was
  acquired with, and nothing is saved, as today.

## The tree

```
<package>/
  package.json                    what was exported, and the hash of every other file
  files/
    <master id>_<state>/          one directory per exported Vault file and model state
      source.json                 every file
      part.step                   a part
      assembly.json               an assembly
```

`<state>` is the model state in lower case, with every run of characters other
than `a` to `z` and `0` to `9` replaced by one hyphen and no hyphen at either
end: `[Primary]` gives `953898_primary`. The exporter stops if two states of
one file give the same name. The directory name is a convenience; the identity
is in `source.json`.

## `package.json`

| Field | Meaning |
| --- | --- |
| `schema_version` | `2` |
| `kind` | `"vault-cad-export-package"` |
| `exported_at` | UTC time the export finished |
| `exporter` | `name`, `version` (the commit of `vault-cad-tools` it ran from), `inventor` (the product version string) |
| `translator_options` | the STEP translator's options as they were set, by name |
| `vault_id` | the vault the files came from |
| `root` | `master_id`, `version_id`, `model_state` of the root assembly |
| `acquisition` | `captured_at` and `method`: when and how the exact versions were frozen and downloaded |
| `counts` | `parts`, `assemblies` |
| `not_exported` | a list of `master_id`, `model_state`, `reason` for every dependency the exporter left out; empty when there is none |
| `files` | an object: the path of every other file in the package, with `sha256` and `bytes` |

The package is complete only when `package.json` exists; the exporter writes
it last.

## `source.json`

The layout's `source.json` without `key` and without `export.run`, which the
import command adds. In particular:

- `vault`: all nine fields. Version number, revision, lifecycle state and
  check-in date reach the REST interface for every file (measured on
  2026-11-10) and are written here, not in a separate record. `path` is the
  Vault path. The exporter takes them from the records made at or after the
  acquisition (`acquisition.json`, the dependency inventory, the output of
  `Get-VaultFileFacts.ps1`); it makes no Vault request of its own.
- `step` (parts): all seven fields, with `header_normalised` true and
  `received_sha256` null, because the exporter normalises before it delivers.
- `export`: `translator_output_sha256`, the hash of the file as the translator
  wrote it, before the header was normalised.
- `properties`: category, description, manufacturer, material, part number,
  stock number, title and vendor, as today. The exporter does not write the
  properties that name people (author, designer, engineer, checked by,
  creator). Whether such names may be in a public repository is not settled
  ([direction.md](direction.md)); leaving them out can be reversed by one
  export.
- `native`: the document's length unit, `extent_mm`, `volume_mm3` and
  `bodies` (`solid_bodies`, `visible_solid_bodies`, `surface_bodies`) as
  today. For a part also its parameters and its hole features, in the form
  `Get-PartFeatureDump.ps1` wrote on 2026-11-10, under `parameters` and
  `holes`, with what that test showed made explicit: a tapped hole has no hole
  diameter and its size is in the thread data; a thread value states the unit
  of its thread standard; and each hole feature names the mirror and pattern
  features that repeat it, so that a hole count can be multiplied out.
- `materials`: the claim per part and body of
  `vault-cad-tools/docs/authoring-and-materials.md`, 4.1, or null until the
  exporter records it.

## `assembly.json`

The layout's `assembly.json` without `key`, with each child naming its
component by identity:

- `master_id` and `model_state` are required, and `component` is absent. The
  import command writes `component` from them.
- `name`, `kind`, `transform`, `bom_structure` and the five flags are as in
  the layout, every one stated. `length_unit` is the unit the transforms are
  written in; the exporter may keep Inventor's centimetres.
- A number is written so that reading it back gives the same double.
- An assembly document is written once, whatever the number of its instances.
  The exporter stops if two instances of one document and model state do not
  have the same children.
- The placements a flexible instance gives its descendants are written as
  `overrides` on that instance's child entry, as in the layout. An override
  more than one level below the instance, and a flexible instance inside a
  flexible instance, are written the same way; neither has been met on real
  data. Open, and put to the Windows agent on 2026-11-11: today the exporter
  writes the occurrences in context and the import command derives the
  overrides. If that split is sounder with the Inventor API, the package
  holds each assembly's children as defined plus the occurrences in context,
  and this paragraph changes.
- A suppressed child is written with `suppressed` true, and its component is
  exported like any other.
- A child whose placement is not a rotation and a translation (a mirrored
  occurrence) stops the export.

## The STEP files

- AP242 (`ApplicationProtocolType` 5), sketches not included, every other
  translator option at its default, and the translator's description, author,
  organization and authorisation options empty. The translator reports eight
  options; `translator_options` in `package.json` records all eight.
- Exported from documents that have no view. The exporter opens the root
  invisibly in its own Inventor instance, and then neither the root nor any
  document it refers to has a view (measured on 2026-11-11: none of 44). It
  checks this for every document it exports from and stops if one has a view.
  Why: without a view the translator writes a fixed default camera, and ten
  exports of a part from six Inventor instances on two days had one data
  section; with a view it writes that view's camera, and the data section
  changes whenever the camera does. The camera is not rewritten afterwards:
  the data section stays the translator's.
- The header is normalised with `Set-StepFileHeader` of
  `windows/Step-Header.ps1` under the name `part.step`. (It gives the bytes
  `stepfile.py` gives, on all 37 AP242 files as on the AP214 ones. The
  exporter does not call it yet.) An AP242 header has a second, constant
  `FILE_DESCRIPTION` string naming a recommended practice for PMI; it stays.
- Bodies hidden in the native part are in the file, marked invisible. None of
  the translator's options leaves them out. Linux leaves them out when it
  measures and draws (`stepfile.py`, `visible_only`), and understands one form
  of the mark; the exporter stops if a file has an `INVISIBILITY` in another
  form (`Get-StepInvisibility` in `Step-Header.ps1` is the text-level check).
- A solid with an internal void is a `BREP_WITH_VOIDS`, not a
  `MANIFOLD_SOLID_BREP`. Whatever counts solids in the text of a file to
  compare them with `native.bodies` counts both.

## What the import command does with it

`vault-cad import-snapshot PACKAGE --into PROJECT --run RUN`
(`vault-cad-tools/src/vault_cad_tools/package_import.py`), built on 2026-11-11
against this draft. It checks the whole package and the project before it
writes anything:

1. Every file is verified against `package.json`, and nothing may be in the
   package that `package.json` does not list. The vault and the root assembly
   are compared with the project's `vault-project.toml`. The project's
   directories must be what its index says they are.
2. Each file's key is found by master id and model state in the project's
   index. A file the project does not have yet gets a key from its name, as
   today, one that no imported or authored component has.
3. The package is refused when the project holds a later version of one of
   its files (by version number), and when the order of two versions cannot
   be told because a version number is unknown.
4. A component's directory is left untouched when its version id, its native
   hash, its STEP bytes and the exporter's record of it are what the project
   has. The record is `source.json` without its `export` block, and for an
   assembly its children. An unchanged file therefore keeps pointing at the
   export it first came from, and a refresh changes only what changed. What
   is not unchanged is reported as updated (a new Vault version) or rewritten
   (the same version, exported differently) and replaced.
5. The components of the project that the package does not have are
   reported. Nothing is removed; removal on request is not built.
6. `package.json` is kept under `references/receipts/<run>/`, and the index
   is derived again. `facts.json` is left alone: the result names the parts
   whose `part.step` changed, for `tools/step_facts.py` to measure.

After it: `tools/step_facts.py`, `validate`, and `compare-scenes` between the
scene flattened before and after. When the STEP files are another export of
the same versions, as in the change from AP214 to AP242, every one differs:
`compare-scenes --other-export` then lists them and compares everything else,
and `tools/compare_step_exports.py` compares their geometry.

Tried on 2026-11-11 on copies of the converted enclosure, with packages
written on Linux from what the project holds:

- The package of exactly what the project holds: 44 files unchanged, and no
  file of the project changes but the new receipt.
- The same with the 37 AP242 files of the Windows tests in place of the
  tracked AP214 files: 37 parts rewritten, the 7 assemblies untouched, all
  keys kept. After `step_facts.py` the project validates without an error,
  and its flattened scene equals the branch's (37 parts, 17 assembly nodes,
  155 occurrences, no placement differs) apart from the 37 STEP files.

## Not in the package

- The BOM views of the assemblies and virtual components. They stay with the
  audit (`Audit-NativeBom.ps1`).
- Drawings.
- A key for an occurrence that survives a rename. If Inventor's reference key
  of an occurrence can be read without saving, the exporter could add it to
  each child; the layout has no field for it yet.
- The files of the Vault folder that the root assembly does not use. Which
  files a project mirrors is not settled.
