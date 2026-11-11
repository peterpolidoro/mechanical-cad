# The exporter's package: draft specification

**Status: draft 1, written 2026-11-11, not reviewed by Peter or by the Windows
agent, not implemented.** It specifies what the Windows exporter delivers for
one export of one root assembly, and what the import command does with it. The
exporter in `vault-cad-tools` (`windows/Export-PartAssets.ps1`) writes an
earlier package today, and `vault-cad import-snapshot` reads only that one.

Two statements below rest on the Windows AP242 tests of 2026-11-11, whose
report was not finished when this was written. They are marked *(pending the
report)* and were read from the run's files as they stood.

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
  name. The earlier package carried all three.
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
  Vault path.
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
  data.
- A suppressed child is written with `suppressed` true, and its component is
  exported like any other.
- A child whose placement is not a rotation and a translation (a mirrored
  occurrence) stops the export.

## The STEP files

- AP242 (`ApplicationProtocolType` 5), sketches not included, every other
  translator option at its default, and the translator's description, author,
  organization and authorisation options empty.
- Exported with no view open, as the exporter runs today. A file exported
  while a view is open carries that view's camera, so its data section
  changes with the view; exported without one, ten exports of a part from six
  Inventor instances on two days had one data section *(pending the report)*.
- The header is normalised with `windows/Step-Header.ps1` under the name
  `part.step`.
- Bodies hidden in the native part are in the file, marked invisible. The
  translator reports eight options and none leaves them out *(pending the
  report)*. Linux leaves them out when it measures and draws
  (`stepfile.py`, `visible_only`).

## What the import command does with it

Not built. `vault-cad import-snapshot` is to read this package beside the
earlier one, into an existing project:

1. Verify every file against `package.json`, and the vault and root against
   the project.
2. Find each file's key by master id and model state in the project's index.
   A file the project does not have yet gets a key from its name, as today.
3. Refuse the package when the project holds a later version of one of its
   files (by version number).
4. Leave a component's directory untouched when its version id, native hash
   and STEP bytes are what the project has. Replace it when they are not. An
   unchanged file therefore keeps pointing at the export it first came from,
   and a refresh changes only what changed in Vault.
5. Report the components of the project that the package no longer has, and
   remove nothing unless asked to.
6. Keep `package.json` under `references/receipts/<run>/` and derive the
   index again.

After it: `tools/step_facts.py` for the parts that changed, `validate`, and
`compare-scenes` between the scene flattened before and after.

## Not in the package

- The BOM views of the assemblies and virtual components. They stay with the
  audit (`Audit-NativeBom.ps1`).
- Drawings.
- A key for an occurrence that survives a rename. If Inventor's reference key
  of an occurrence can be read without saving, the exporter could add it to
  each child; the layout has no field for it yet.
- The files of the Vault folder that the root assembly does not use. Which
  files a project mirrors is not settled.
