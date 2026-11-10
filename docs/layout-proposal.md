# Repository layout: proposal and evidence

**Status: proposal of 2026-11-10, not accepted. No specification, validator or
converter exists yet.** [direction.md](direction.md) says why this matters; this
file holds the detail an implementer needs, what was measured, and what is still
unknown. When the layout is accepted it becomes a specification with a validator
in this repository and this file is retired.

## Where the proposal comes from

Three inputs, reconciled on 2026-11-10:

1. The enclosure project as it stands (first production snapshot, 2026-10-21).
2. Peter's directives of 2026-10-23 (see direction.md, "Decided").
3. A design discussion Peter had with another agent on 2026-10-27/28. It
   proposed one directory per part (`geometry.step`, `part.yaml`, `build.py`),
   `assembly.step` plus `structure.yaml` for assemblies, AP242 with a normalised
   header, one authority per part, a geometry hash, Vault provenance stamps and
   geometry assertions used as tests.

| From the discussion | Position here |
| --- | --- |
| One directory per part, same shape for imported and authored parts | Kept |
| One authority per part | Kept |
| Vault provenance in the metadata; geometry assertions as tests | Kept |
| Normalised STEP header | Kept, done by the exporter as a declared step (evidence below) |
| `assembly.step` as a source | Dropped: contradicts the 2026-10-23 directive; at most a derived export |
| YAML sidecars | Dropped: JSON for machine-written files, TOML for hand-edited ones. The tools are standard-library only, and YAML retypes strings such as part numbers and revision labels |
| AP242 | Undecided: test it, do not assume it |
| Geometry hash including a canonical tessellation | Changed: mass properties only, so a kernel upgrade does not change it |
| (not addressed) assemblies as files of their own | Added |
| (not addressed) who writes which file | Added |
| (not addressed) names that survive a rename in Vault | Added |

## The enclosure today

```
references/enclosure/
  assets/<name>__[<model state>]__<hash8>.step   37 files, flat
  scene.json                 all parts, 17 assembly nodes, 155 occurrences
  native-snapshot.json       the exporter's raw record
  export-receipt.json        hashes of every file in the export
vault-lock.json              per-file provenance, Linux validation, publications
designs/reference-models/<name>/   one code-authored part: program, parameters,
                             STEP, FreeCAD document, validation records
step/                        copies of authored STEP files to publish
assembly/                    curated manifests and project scripts
docs/                        the published manual and site (served from main)
```

## Proposed layout

```
references/                 Vault is the authority; written only by the import command
  parts/<key>/
    part.step               header normalised by the exporter
    source.json             written on Windows
    facts.json              written on Linux
  assemblies/<key>/
    assembly.json           written on Windows
    source.json             written on Windows
designs/                    the repository is the authority
  parts/<key>/
    build.py  parameters.json  checks.json     written by people and agents
    part.step  receipt.json  facts.json        written by the build command
  assemblies/<key>/
    assembly.json           written by people and agents; may place components
                            from references/
assembly/                   curated project files as today, re-keyed
vault-lock.json             index only: Vault master id, key, version, hashes
build/                      derived and ignored: flattened scene.json, meshes,
                            renders, manual
```

Rules:

- **One directory per Vault file.** The enclosure is 44 Vault files: 37 parts
  and 7 assemblies. Per-file synchronisation states
  (`vault-cad-tools/docs/native-checkin-adapter-design.md`, section 2) then
  attach to a directory.
- **One writer per file.** Windows facts, Linux check results and curated
  values never share a file, so a re-import cannot overwrite curation and a
  stage never rewrites another stage's record.
- **Keys.** `<key>` is a readable name assigned once on Linux and recorded
  against the Vault master id in the lock. A rename or move in Vault changes
  `source.json`, not the directory or anything that refers to it. Model state is
  a field, not part of the directory name, until a part with more than one
  exported state appears.
- **Assembly manifests list direct children only**: occurrence name, component
  key, local transform, BOM structure and the flags the exporter records today.
  An instance of a flexible sub-assembly whose children sit somewhere other
  than in the definition carries an override list in the parent's manifest.
- **The flattened scene is derived.** A flatten step composes the manifests
  into the `scene.json` that `mechanical-docs` reads today and writes it under
  `build/`. Occurrence ids stay the paths of occurrence names they are now.
- **Authored parts** use the same directory shape. The STEP in the directory is
  the deliverable; a separate `step/` copy is no longer needed, and a
  publication is recorded against a commit and hash.
- **STEP headers** are normalised by whoever writes the file (the exporter, the
  build command): fixed file name, fixed timestamp, no account name. The fact
  that it was done is recorded beside the hash.
- **Geometry fingerprint**: solid count, volume, surface area, centre of mass
  and bounding box, rounded to a stated tolerance. Bytes say whether a file
  changed; the fingerprint says whether the geometry did.

Starting point for the file contents (to be turned into schemas, not yet one):

- `source.json` (part): Vault id, master id, version id, version number,
  revision, lifecycle state, check-in date, Vault path, native SHA-256; exporter
  name and version, translator options, STEP protocol and length unit, export
  time; model state; the properties recorded today (part number, description,
  material, stock number, vendor, manufacturer, title, category); default BOM
  structure; body counts, volume and range box as Inventor reports them; the
  material and appearance claim per part and body
  (`vault-cad-tools/docs/authoring-and-materials.md`, 4.1); later, parameters
  with expressions and units, hole and thread specifications, sheet-metal data.
- `facts.json`: tool and kernel versions, validity, solid count, bounding box,
  volume, declared STEP unit, the fingerprint, the hash of the STEP it describes.
- `assembly.json`: units, frame, and per child: occurrence name, component key
  (with the master id and model state for imported children), local transform,
  BOM structure, visible, suppressed, grounded, flexible, mirrored; overrides.
- `receipt.json` (authored): program and parameter hashes, tool and kernel
  versions, output hash, the re-import check.

## Evidence gathered on 2026-11-10

Observed on the enclosure repository at `0eeb1af` and `vault-cad-tools` at
`7807e8f`, on Linux, read-only.

- **File count.** 37 part documents, all in model state `[Primary]`; 7 assembly
  documents: the root and six definitions with 16 instances (caster, panel and
  toggle-clamp assemblies four each, tank support frame two, camera frame and
  free-standing frame one each); 155 leaf occurrences. STEP length units: 21
  inch, 15 millimetre, 1 centimetre. All 37 are AP214.
- **Flattening duplicates definitions.** `scene.json` writes out the children of
  every instance, so a four-instance assembly is listed four times.
- **Overrides are needed.** 44 occurrences have a position that differs from
  their definition, all inside the two flexible assemblies (32 and 12).
- **The existing snapshot is enough to prototype with.** `native-snapshot.json`
  records a definition-local transform for everything that sits inside a
  sub-assembly: all 153 such occurrences and all 4 nested assembly instances.
  The 14 direct children of the root (12 assembly instances and 2 parts) have
  none, because the root has no enclosing instance; their local transform is
  the definition. No new Vault export is needed to build the converter.
- **Header normalisation gives stable bytes, on one part.** The repository holds
  two exports of the same Vault version of the top panel, made about three hours
  apart. Their headers differ in two lines (the file name and the timestamp);
  everything from `DATA;` on has the same SHA-256. Not yet repeated on other
  parts, on assemblies, or across Inventor sessions and machines.
- **Asset names follow the Vault path.** The `<hash8>` suffix is the first eight
  hex digits of the SHA-256 of `<workspace-relative path>|<model state>`
  (`windows/Export-PartAssets.ps1`), so a rename or move in Vault renames the
  repository file.
- **Exported files carry machine-specific text.** 33 of 37 STEP headers hold a
  Windows account name; `scene.json` holds absolute Windows paths 17 times and
  `native-snapshot.json` 54 times; the receipt and lock hold a host name.
- **The exporter already supports AP242.** Its protocol map is 2 = AP203,
  3 = AP214, 4 = AP203E2, 5 = AP242; the enclosure used 3.
- **Geometry checks are implemented four times**: three FreeCAD scripts in the
  enclosure and `cad_mesh.py` in `mechanical-docs`. `vault-cad-tools` has none
  in its Python sources.
- **Guix** (commit `64d4de2`): `freecad` 1.1.3, `opencascade-occt` 7.9.3,
  `cloudcompare`, `python-trimesh`, `python-olefile`, `python-ezdxf` and
  `python-setuptools` 80.9.0 are packaged; CadQuery, build123d, the OCP bindings
  and Open3D are not.

## Not verified

- How overrides should be written so that a flexible instance round-trips. This
  is the hard part of the proposal.
- Header stability beyond the one part above.
- Whether AP242 from Inventor reads identically in FreeCAD and what it adds.
- What the Inventor API returns for parameters, holes and threads on a real
  drilled or tapped part, and whether lifecycle state and revision reach the
  export (the synchronisation design specifies them; the enclosure's files do
  not contain them).
- A refresh-stable occurrence key. Occurrence ids are snapshot-scoped today;
  the exporter has not been asked for Inventor reference keys.

## Open choices (Peter)

1. Two top-level roots as drawn, or one tree with an authority field in every
   directory. Recommended: two roots, because "never edit `references/`" is a
   rule a path can enforce.
2. Readable keys tied to the master id, or a mirror of Vault's folder tree.
   Recommended: readable keys.
3. AP214 or AP242, after the test.

## Acceptance test for the conversion

Convert the existing snapshot into the layout on a branch of the enclosure,
flatten it, and require:

- the same 37 parts and 155 occurrences, each world transform equal to today's
  within the tolerance the loader already uses for the exporter's matrices;
- unchanged STEP data sections and the same FreeCAD volume and extents per part;
- the `mechanical-docs` manual rebuilding from the flattened scene with every
  check passing, reusing the existing renders where meshes are unchanged;
- every curated file (`inventory`, `instructions`, `build-scope`, `materials`,
  `supplement`, `render`) re-keyed by script, with no row lost.

`main` of the enclosure is left alone until this passes: it feeds the published
manual that Peter is assembling from.

## Read-only tests to request from Windows

1. Export three parts as AP214 and as AP242; compare in FreeCAD.
2. Export the same parts twice in separate sessions; compare data sections.
3. Record lifecycle state, revision and check-in date for the 44 files.
4. Dump parameters, hole features and thread data for one drilled or tapped
   plate.

## What changes where, if accepted

- `vault-cad-tools`: the exporter's output layout and file naming, header
  normalisation, per-assembly manifests, the lock reduced to an index (design
  document 2.3), per-directory `source.json` in place of the planned
  `metadata.json` (4.2, 4.3), the import command.
- `mechanical-docs`: none in the loader or renderer; it reads the derived scene.
- The enclosure: the conversion on a branch, re-keyed curated files, the
  authored monitor envelope moved to the new shape.
- Here: the specification and validator, the flatten step, then the geometry
  facts, build and check commands.
