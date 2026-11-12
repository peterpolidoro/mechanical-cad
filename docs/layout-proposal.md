# Repository layout: proposal and evidence

**Status: proposal of 2026-11-10. On 2026-11-11 Peter decided its three open
choices: two roots, readable keys, AP242.** [direction.md](direction.md)
says why this matters; this file holds the reasoning, what was measured, and
what is still unknown. A draft specification with a validator, a fixture and a
flatten step implements them
([layout-specification.md](layout-specification.md)). This file is retired
when the enclosure has been converted and re-exported under the layout.

The proposal was amended on 2026-11-10 after a review of all four
repositories; what changed is listed at the end. The same day the enclosure's
snapshot was converted in a dry run, outside the tracked tree, and passed the
acceptance test below. The results are in "Dry run of 2026-11-10". The
read-only tests asked of Windows were run that day as well; they are in
"Windows tests of 2026-11-10", with what Linux measured on their files. The
three tests that the choice of AP242 asked for were run on 2026-11-11 and are
in "Windows tests of 2026-11-11".

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
| Normalised STEP header | Kept, done by whoever writes the file as a declared step (evidence below) |
| `assembly.step` as a source | Dropped: contradicts the 2026-10-23 directive; at most a derived export |
| YAML sidecars | Dropped: JSON for machine-written files, TOML for hand-edited ones. The tools are standard-library only, and YAML retypes strings such as part numbers and revision labels |
| AP242 | Undecided: test it, do not assume it |
| Geometry hash including a canonical tessellation | Changed: mass properties compared within a stated tolerance. Whether they survive a kernel upgrade is not verified (see "Not verified") |
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
references/                 Vault is the authority; two commands write here
  parts/<key>/
    part.step               bytes as the exporter wrote them
    source.json             import command: the exporter's record of this file
    facts.json              facts command: what the kernel measures
  assemblies/<key>/
    assembly.json           import command: direct children and placements
    source.json             import command
  receipts/<export id>/     import command: the exporter's run-level records,
                            byte for byte
designs/                    the repository is the authority
  parts/<key>/
    build.py  parameters.json  checks.json     people and agents
    part.step  receipt.json  facts.json        build command
    vault.json              written when a publication to Vault is verified
  assemblies/<key>/
    assembly.json           people and agents; may place components from
                            references/
assembly/                   curated project files as today, re-keyed
vault-lock.json             derived index: Vault master id, key, version, hashes
build/                      derived and ignored: flattened scene.json, meshes,
                            renders, manual
```

Rules:

- **One directory per Vault file.** The enclosure is 44 Vault files: 37 parts
  and 7 assemblies. Per-file synchronisation states
  (`vault-cad-tools/docs/native-checkin-adapter-design.md`, section 2) then
  attach to a directory.
- **One writing command per file.** Each file is written by exactly one
  command, named in the tree above, so a re-import cannot overwrite curation
  and a stage never rewrites another stage's record. Nothing under
  `references/` is edited by hand. Two commands write there: the import command
  (`vault-cad-tools`) and the facts command (`mechanical-cad`, kernel-backed).
- **The exporter never sees a key.** On Windows the exporter identifies every
  file by its Vault master id and model state, and lists an assembly's children
  the same way. The import command on Linux assigns a key to each master id it
  has not seen, records it in the lock, and writes the directories. In
  `assembly.json` it writes the child's key and keeps the master id beside it.
- **Keys.** `<key>` is a readable lower-case name assigned once, unique across
  the repository, and recorded against the Vault master id in the lock. A
  rename or move in Vault changes `source.json`, not the directory or anything
  that refers to it. A part's primary model state uses `<key>`; any other
  exported state uses `<key>@<state>`, so a second state never renames the
  first.
- **Assembly manifests list direct children only**: occurrence name, component
  key, local transform, BOM structure and the flags the exporter records today.
  An instance of a flexible sub-assembly whose children sit somewhere other
  than in the definition carries an override list on that child entry of the
  parent's manifest: a path of occurrence names below the instance, and the
  local transform that replaces the definition's.
- **The flattened scene is derived.** A flatten step composes the manifests
  into the `scene.json` that `mechanical-docs` reads today and writes it under
  `build/`. Occurrence ids stay the paths of occurrence names they are now.
- **Authored parts** use the same directory shape. The STEP in the directory is
  the deliverable; a separate `step/` copy is no longer needed. A verified
  publication is recorded in the part's `vault.json` against a commit and hash.
- **The lock is derived.** `vault-lock.json` is an index of what the
  directories say (master id, key, version id, hashes). The import command
  rewrites it and the validator recomputes it and requires agreement, so the
  two cannot drift. The synchronisation facts of the design document map onto
  it: F1 is the discovered version id against `source.json`; F2 is the native
  hash in `source.json`; F3 is the STEP hash in `source.json`; F4 is the hash
  of `part.step` at HEAD.
- **Three identities for a STEP file**, each answering a different question:
  the file's SHA-256 (did any byte change), the SHA-256 of its data section,
  from the `DATA;` line to the end of the file (did the exporter's geometry
  text change, whatever the header says), and the geometry fingerprint (did
  the geometry change, as a kernel measures it).
- **STEP headers** are normalised by whoever writes the file (the exporter, the
  build command): fixed file name, fixed timestamp, empty author. The record
  beside the file says that it was done, and keeps the hash of the file as
  received when a file is normalised after the fact.
- **Geometry fingerprint**: solid count, volume, surface area, centre of mass
  and bounding box, with the kernel and its version. Two fingerprints are
  compared within a stated tolerance, never by equality of a hash.
- **The exporter's run-level records are kept.** Each import stores the
  exporter's receipt and raw run records under `references/receipts/`,
  unchanged, so the hashes they contain can still be checked against the files
  they name.

Starting point for the file contents (the draft specification makes these
exact):

- `source.json` (part): Vault id, master id, version id, version number,
  revision, lifecycle state, check-in date, Vault path, native SHA-256; exporter
  name and version, translator options, STEP protocol and length unit, export
  time; the STEP's file hash and data-section hash, whether the header was
  normalised, and the export run it came from; model state; the properties
  recorded today (part number, description, material, stock number, vendor,
  manufacturer, title, category); default BOM structure; body counts, volume
  and range box as Inventor reports them; the material and appearance claim per
  part and body (`vault-cad-tools/docs/authoring-and-materials.md`, 4.1);
  later, parameters with expressions and units, hole and thread
  specifications, sheet-metal data.
- `facts.json`: tool and kernel versions, validity, solid count, bounding box,
  volume, declared STEP unit, the fingerprint, the hashes of the STEP it
  describes.
- `assembly.json`: units, frame, and per child: occurrence name, component key
  (with the master id and model state for imported children), local transform,
  BOM structure, visible, suppressed, grounded, flexible, mirrored; overrides.
- `receipt.json` (authored): program and parameter hashes, tool and kernel
  versions, output hashes, the re-import check.

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
  everything from `DATA;` on has the same SHA-256. (Repeated since on three
  parts across nine Inventor sessions; see "Windows tests of 2026-11-10".)
- **Asset names follow the Vault path.** The `<hash8>` suffix is the first eight
  hex digits of the SHA-256 of `<workspace-relative path>|<model state>`
  (`windows/Export-PartAssets.ps1`), so a rename or move in Vault renames the
  repository file.
- **Exported files carry names of people and machines.** Every one of the 37
  STEP headers has an account-like name in its `author` field: four distinct
  names, one of them on 33 files, none of them the account that ran the export.
  The exporter passed an empty `Author` translator option, so the name comes
  from somewhere else: the native file's own "Author" property, as the Windows
  tests confirmed. `scene.json` holds absolute
  Windows paths with an account name 17 times and `native-snapshot.json` 54
  times; the receipt and lock hold a host name. (Corrected on 2026-11-10: the
  first draft said 33 of 37 headers.)
- **The exporter already supports AP242.** Its protocol map is 2 = AP203,
  3 = AP214, 4 = AP203E2, 5 = AP242; the enclosure used 3.
- **Geometry checks are implemented four times**: three FreeCAD scripts in the
  enclosure and `cad_mesh.py` in `mechanical-docs`. `vault-cad-tools` has none
  in its Python sources.
- **Render reuse is gated on file hashes.** `mechanical-docs` copies a view from
  an earlier receipt only when the scene file and every asset file have the
  same SHA-256 (`render.py`, `--reuse`; `manifest.py`,
  `geometry_input_hashes`). A converted project has a different `scene.json`
  whatever else stays the same, so no render carries across the conversion.
- **Guix** (commit `64d4de2`): `freecad` 1.1.3, `opencascade-occt` 7.9.3,
  `cloudcompare`, `python-trimesh`, `python-olefile`, `python-ezdxf` and
  `python-setuptools` 80.9.0 are packaged; CadQuery, build123d, the OCP bindings
  and Open3D are not.

## Dry run of 2026-11-10

Run on Linux against the enclosure repository's tracked snapshot, into an
ignored directory of that repository (`.cache/layout-dry-run-01/`). Nothing
tracked in the enclosure changed, no branch was made, and no image was
rendered. Tools: `vault-cad import-snapshot` (`vault-cad-tools`, provisional),
then `validate`, `flatten`, `tools/step_facts.py` and
`tools/conversion_acceptance.py` from here. Python 3.12.12, FreeCAD 1.1.3,
OpenCASCADE 7.9.3.

- **Conversion.** 37 part directories and 7 assembly directories, with 44
  overrides: 32 on the camera frame's entry and 12 on the free-standing
  frame's, both in the root assembly's manifest. With the acquisition's
  dependency inventory given to the converter, every one of the 44 files has
  its master id, version id, version number, revision, lifecycle state and
  check-in date; that inventory was written on Windows on 2026-10-21 and had
  not been brought into the repository.
- **Acceptance test: all four checks pass.**
  1. The converted project validates with no error.
  2. All 37 STEP files are byte-identical to the exporter's and its receipt,
     kept under `references/receipts/`, still verifies them.
  3. The flattened scene equals the exporter's `scene.json`: 37 parts, 17
     assembly nodes, 155 occurrences. The largest difference in any rotation
     cell is 6.3e-14 and in any translation 6.5e-11 mm, for placements in their
     parent and in the root alike. The only difference in fields is that the
     new scene also says which assembly nodes are flexible.
  4. The documentation project the published manual was built from (37
     inventory rows, 20 supplement rows, 18 steps, the build scope and the
     render settings), with its part ids re-keyed by the script, loads in
     `mechanical_docs inspect` with the same counts, the same finding (the two
     coincident tanks), the same inventory and build-scope quantities, the same
     steps and the same world placements.
- **Overrides round-trip.** Check 3 is the test of the hard part: the 44
  placements that differ from their definitions come back where the exporter
  had them. The enclosure only has overrides one level below a flexible
  instance; deeper paths and an outer override taking precedence are covered by
  the fixture's tests, not by real data.
- **Geometry facts.** FreeCAD reads all 37 parts as valid in 39 s. Counted
  over the 155 occurrences they hold 479 solids, the number known from the full
  assembly export.
- **Inventor's recorded volume is not a fingerprint.** Against OpenCASCADE's,
  the volume the exporter recorded agrees within a relative 1e-4 for 30 of the
  37 parts and within 1e-3 for 33; three purchased parts differ by 7.8 %, 8.2 %
  and 10.9 %. Two of the three are Inventor's default-accuracy measurements,
  already known. The third, `MCMASTER 47065T245`, is something else: Inventor's
  volume counts the part's four solid bodies and the AP214 file holds only the
  visible one (see the Windows tests below). Inventor's range boxes agree with
  OpenCASCADE's extents within 0.01 mm for 29 parts and within 1.445 mm for
  all. The fingerprint therefore comes from one kernel, on Linux; what Inventor
  reports stays a claim in `source.json`.
- **Header normalisation on the real files.** Normalising each of the 37
  headers in memory leaves every data-section hash unchanged, and the two
  exports of the top panel normalise to the same bytes. Nothing was written.
- **A part built from code is reproducible.** The fixture's authored part
  builds to the same bytes on a second build and in another directory. That
  needed one correction: OpenCASCADE names the STEP product of a bare shape
  after a counter of the exports the process has made, so the build command
  names the product after the part's key.

Not done by the dry run: the enclosure's own curated files that carry part ids
(`assembly/materials.json`, the two procurement sheets, `joint-audit.json`) and
its eight scripts that read `references/enclosure/` are not converted; the
authored monitor envelope is not moved; no manual was built.

## Windows tests of 2026-11-10

The five read-only tests below were run by the Windows agent on the acquired
mirror of the same Vault versions (Inventor 2025.3; REST requests GET only;
nothing saved, nothing written to Vault). Its report and files are in the
shared evidence run `2026-11-10-windows-layout-tests-01`. Linux checked the
run's 395 files against their checksums, reviewed and applied its patch to
`vault-cad-tools`, and repeated what it could on the files themselves; where a
line says "measured on Linux", that is this repository's `stepfile.py` or
FreeCAD 1.1.3 with OpenCASCADE 7.9.3.

1. **AP214 against AP242, three parts.** For the top panel and for a threaded
   shoulder screw the two protocols give the same geometry: same solid and
   face counts, volume, area, centre of mass and bounding box (measured on
   Linux). For `MCMASTER 47065T245` they do not. Its native file has four solid
   bodies of which one is visible. AP214 writes the visible one; AP242 writes
   all four and marks three invisible. FreeCAD does not honour that mark: it
   reads the AP242 file as four valid solids, 37 306.4 mm³ in place of
   34 485.9 mm³, with a bounding box 1 mm larger (measured on Linux). The
   three extra solids are 940.2 mm³ each, and the total is the volume Inventor
   itself reports for the part. Every AP242 file also carries a saved-view
   block (a camera and draughting model) that AP214 does not.
2. **Stability between sessions.** For each of the three parts, nine AP214
   exports from nine Inventor instances between 2026-10-21 and 2026-11-10 have
   the same data-section hash and normalise to the same bytes. Measured on
   Linux: the three exports made on 2026-11-10 have the data sections of the
   files tracked in the enclosure repository since October, and normalise to
   the same bytes as those files. One workstation; no restart between that
   day's sessions; AP242 was not tested for stability.
3. **Vault facts.** Nothing has changed in Vault for the 44 files since
   2026-10-21: every acquired version is still the latest. Revision, lifecycle
   definition and state, check-in date and check-out state reach REST for
   every file. All 44 are revision 0, in state Work in Progress, none checked
   out.
4. **Parameters, holes and threads.** Seven plates were dumped without saving.
   Parameters come with their expressions and units; hole features with tap
   data (designation, class, pitch, tap drill), clearance data, extent and
   centres in model coordinates. Fifteen of 3232 reads fail, all on a property
   that does not apply to that hole. Three things matter for `source.json`: a
   tapped hole has no hole diameter (it is in the thread data); thread table
   values are in the thread standard's own unit, not the API's centimetres;
   and holes repeated by a mirror or a pattern are not in the hole feature's
   list of centres, so a hole count has to multiply through those features.
   Not exercised, because none of the seven parts has them: thread features,
   counterbores, sheet metal.
5. **The header's author** is the native file's Summary Information "Author".
   A non-empty translator option overrides it, the header's name is the output
   file name, and no option controls the timestamp. The exporter therefore
   has to rewrite `FILE_NAME` after the translator has run.
   `vault-cad-tools/windows/Step-Header.ps1` does that as a port of
   `stepfile.py`. Windows compared the two on 49 files (hashes, header fields,
   normalised bytes) without a disagreement; measured on Linux, the six files
   it rewrote from the test-1 exports are byte-identical to what `stepfile.py`
   writes from the same inputs, and all 14 rewritten files are normalised by
   the reference's own test. The translator's `Description` option lands in
   `FILE_DESCRIPTION`, which the normaliser leaves alone, so the exporter
   keeps it empty.

Also from that run:

- **The Vault folder holds more than the snapshot.** A read-only discovery of
  the enclosure's folder finds 32 files and two root assemblies: the one that
  was mirrored, and `SLLB Enclosure.iam`, which nothing in the folder uses and
  whose 20 dependencies are, all but one, already in the snapshot. Six files of
  the folder are not in the snapshot: that assembly, one extrusion only it
  uses, three parts nothing in the folder uses, and the published monitor
  envelope. Conversely 18 of the snapshot's 44 files live outside the folder
  (purchased parts and parts of two other projects). "One directory per Vault
  file" holds either way; which files a project mirrors is a separate choice.
- **REST listings on this server must be read as one page.** Following the
  paging cursor repeats and skips rows. One page of up to 1000 rows, accepted
  only when its row count is the server's total, is reliable.

## Windows tests of 2026-11-11

After Peter chose AP242, three read-only tests were asked of Windows and run
the same day (Inventor 2025.3; no Vault access; nothing saved; every opened
file re-hashed and unchanged). The report and files are in the shared evidence
run `2026-11-11-windows-ap242-tests-01`. Linux checked the run's 184 files
against their checksums, reviewed and applied its patch to `vault-cad-tools`
(probes, text-level helpers and their tests; the exporter is untouched), and
made the comparison of test 3 with `tools/compare_step_exports.py` (FreeCAD
1.1.3, OpenCASCADE 7.9.3).

1. **AP242 exports are stable when the document has no view.** Three parts,
   each exported in three separate Inventor instances that day, reached
   through the invisibly opened assembly and opened by itself, and compared
   with the file of 2026-11-10 and with the snapshot exporter's own AP242
   file: one data-section hash per part (ten exports from six instances for
   the top panel and for the corner cube, eight from five for the shoulder
   screw). Only the header's time stamp and name differ. One workstation; no
   restart.
2. **The saved view is the camera of the document's view.** Opened as the
   exporter opens it, the root assembly has no view and none of its 43
   referenced documents has one; the translator then writes a fixed default
   camera (a 20 mm square window looking along -Z, one text per length unit
   over all 37 files). A part opened visibly has a view, and the file carries
   that view's camera: rotating, zooming or setting an orientation changes
   the file each time, for the same camera two instances write the same file,
   and changing the camera does not mark the document as modified. In every
   pair compared the difference is confined to the 12 instances reachable
   from `CAMERA_MODEL_D3`; none of them is referenced from outside. Tried on
   two parts, in the invisible application; an interactive user's window was
   not tried.
3. **No translator option leaves out the hidden bodies or the saved view.**
   The translator reports eight options (`IncludeSketches`,
   `ApplicationProtocolType`, `Author`, `Organization`, `Authorization`,
   `Description`, `export_fit_tolerance`, `ExportUCS`). Changing the three that
   are not header texts leaves the corner cube's data section unchanged. No
   option name the translator does not report was tried.
4. **All 37 parts as AP242 are the same geometry as the tracked AP214
   files.** One strict exporter run (44 of 44 documents bound to the
   acquisition), headers normalised with the PowerShell port, which
   `stepfile.py` confirms on all 37. Measured on Linux against the converted
   enclosure: 37 of 37 have the fingerprint of the tracked part; no data
   section is the same, as expected; one file marks items invisible
   (`MCMASTER 47065T245`, three, in the understood form) and is the same
   geometry once they are left out.
5. **A solid with an internal void is a `BREP_WITH_VOIDS`.** One framing part
   has 11 solid bodies in Inventor and 10 `MANIFOLD_SOLID_BREP` plus one
   `BREP_WITH_VOIDS` in its file, in both protocols. A count of solids from
   the text has to take both. `stepfile.py` does not look at the kind of a
   hidden item, and FreeCAD measures the part as valid.

Also constant in every AP242 header: a second `FILE_DESCRIPTION` string naming
the CAx-IF recommended practice for PMI, which normalising leaves alone.

What follows from tests 1 and 2: the saved view does not have to be
normalised. A file exported for a repository comes from a document without a
view, which is how the exporter runs; the exporter is to check that and stop
otherwise ([exporter-package.md](exporter-package.md)). Rewriting the camera
would be the first change to a data section, and every identity recorded so
far rests on the data section being the translator's.

## Not verified

- That the recorded placements are the assembly Inventor itself would export.
  The placements were read from Inventor's occurrences and the manual drawn
  from them is being built from, but no record shows them compared with a
  STEP file of the whole assembly written by Inventor. Since 2026-11-11
  `tools/assembly_step.py` derives such a file from the layout (the
  enclosure: 479 solids, each read back within 0.002 mm of where the scene
  puts it) and `tools/compare_assembly_step.py` compares another one with the
  records; Inventor's export of the root assembly is asked of Windows, as
  evidence only.
- How the FreeCAD document that `tools/assembly_step.py` writes looks when it
  is opened: it is made without a view, and whether the part definitions the
  instances link to open hidden has not been observed.
- Overrides more than one level below a flexible instance, and nested flexible
  instances, on real data. The enclosure has neither.
- Header and data-section stability on another workstation, after a restart
  or after an Inventor update, in either protocol.
- What the window of an interactive Inventor session does to the saved view
  of an AP242 file. The exporter never has one.
- The invisibility mark in any form but the one in the one part that has it.
- Thread features, counterbores and sheet-metal data through the Inventor API.
- A refresh-stable occurrence key. Occurrence ids are snapshot-scoped today;
  the exporter has not been asked for Inventor reference keys.
- That a fingerprint made of mass properties is stable across kernel versions,
  and at what tolerance. It has been computed with one version only. The record
  says to be careful: FreeCAD's volume integral disagreed with both of its own
  tessellations on one purchased part (`mechanical-docs`, 2026-10-21), and
  Inventor's default-accuracy volumes differ from FreeCAD's by up to 10.9 % on
  three parts (above) until Inventor measures at its highest accuracy, which
  brought two of them to about 0.0022 % (`vault-cad-tools`, pilot 02).
- That a part built from code is reproducible across FreeCAD or OpenCASCADE
  versions. It is on one.

## Open choices (Peter)

1. Two top-level roots as drawn, or one tree with an authority field in every
   directory. **Decided by Peter on 2026-11-11: two roots.** The reason given
   for the recommendation: "never edit `references/`" is a rule a path can
   enforce.
2. Readable keys tied to the master id, or a mirror of Vault's folder tree.
   **Decided by Peter on 2026-11-11: readable keys.**
3. AP214 or AP242. **Decided by Peter on 2026-11-11: AP242**, after he asked
   for the reasons behind the recommendation of AP214 and was given them and
   what speaks for AP242. What the decision asks for is listed after them. The
   reasons for AP214 were practical, not a judgement that it is the better
   standard:
   - **Continuity.** All 37 tracked files are AP214, and every check so far
     was made on them (479 solids, the acceptance test, the published manual).
     An AP214 re-export can be compared with the tracked files by the hash of
     the data section, which was the same for the three parts re-exported on
     2026-11-10. An AP242 re-export differs in every file, so the same
     comparison has to go through the kernel, part by part.
   - **Stability.** Nine AP214 exports per part gave the same data section.
     AP242 was exported once per part. Each AP242 file carries a saved-view
     block (a camera); whether that block is the same from one session to the
     next was not tested.
   - **Hidden bodies.** AP242 writes them and marks them invisible; FreeCAD
     reads them as ordinary solids. In this project that is one part of 37
     (`MCMASTER 47065T245`, three hidden bodies, counted from the `bodies`
     record of the exporter's `scene.json`). With AP242 the Linux side needs a
     filter for the invisibility mark before anything is measured or drawn.
   - **Nothing gained on these parts.** For the two other parts tested the
     geometry is identical in both protocols.

   What speaks for AP242: it is the standard that replaced AP203 and AP214
   and the one that is still developed (stated from general knowledge of
   ISO 10303, not checked against a source in this work); it can carry
   tolerances and annotations as data, should a designer add them to the
   native part (none of these parts has any, and what FreeCAD would do with
   them was not tested); and it keeps the hidden bodies, which is closer to
   the native file.

   The choice is not permanent: `source.json` records the protocol of each
   part, the specification accepts either, and the exporter writes either, so
   changing it later costs one re-export and one comparison through the
   kernel.

   What AP242 asks for, and where each stands:
   - **Hidden bodies are left out on Linux.** Built on 2026-11-11:
     `stepfile.py` finds the items a file marks invisible and writes the file
     without them; the facts command measures that, and the flatten step
     writes it as the scene's asset. Measured with FreeCAD on the three test
     parts: the AP242 file of `MCMASTER 47065T245` without its three invisible
     solids has the fingerprint of the AP214 file (1 solid, 200 faces,
     34 485.858 mm³, 13 072.588 mm², the same extent and centre of mass), and
     the other two parts mark nothing invisible and measure the same in both
     protocols. One form of the mark is understood, the one Inventor wrote for
     that part; anything else is refused, not guessed.
   - **Stability of AP242 exports** between sessions, and what the saved-view
     block depends on: tested on 2026-11-11. Exports made without a view are
     stable, and the exporter has none; the block is the view's camera
     otherwise ("Windows tests of 2026-11-11").
   - **All 37 parts as AP242**, each compared with its tracked AP214 file by
     fingerprint: done on 2026-11-11, 37 of 37 the same geometry.
   - **The exporter's default protocol** is still AP214; it changes with the
     exporter's package.
   - Someone who opens a tracked AP242 `part.step` directly in FreeCAD sees
     the hidden bodies. `python3 -m mechanical_cad visible-only IN OUT`
     writes the file without them.

## Acceptance test for the conversion

Convert the existing snapshot into the layout on a branch of the enclosure,
flatten it, and require:

- the same 37 parts, 17 assembly nodes and 155 occurrences as today's
  `scene.json`, compared field by field under their recorded original ids, with
  each local and world transform equal within the tolerance the loader already
  uses for the exporter's matrices;
- every STEP file byte-identical to the one it came from, so the exporter's
  receipt still verifies, and the same FreeCAD volume and extents per part;
- the converted project, with its curated files re-keyed, loading in
  `mechanical-docs inspect` with the same counts and the same findings;
- every curated file (`inventory`, `instructions`, `build-scope`, `materials`,
  `supplement`, `render`) re-keyed by script, with no row lost.

The manual is not rebuilt as part of this test. Because render reuse is gated
on the hashes of the scene and asset files, a rebuild from the converted
project renders every view again, and the re-export that follows changes every
asset hash once more (normalised headers). One full render is therefore
planned, after the re-export, and its manual is compared with today's by its
parts, quantities, steps and checks. Carrying renders across such a change
would need reuse keyed on mesh content in `mechanical-docs`; that is possible,
not planned.

`main` of the enclosure is left alone until this passes: it feeds the published
manual that Peter is assembling from.

## Read-only tests to request from Windows

All five were run on 2026-11-10; the results are in "Windows tests of
2026-11-10". The requests as they were made:

1. Export three parts as AP214 and as AP242; compare in FreeCAD.
2. Export the same parts twice in separate sessions; compare data sections.
3. Record lifecycle state, revision and check-in date for the 44 files, and
   say whether anything has changed in Vault since 2026-10-21. (The values as
   of that day are in the acquisition's dependency inventory.)
4. Dump parameters, hole features and thread data for one drilled or tapped
   plate.
5. Find where the header's `author` name comes from, and whether the exporter
   can write a fixed header itself (file name, timestamp, empty author) or the
   header has to be rewritten after the translator has run.

## What changes where, if accepted

- `vault-cad-tools`: the exporter's output (files identified by master id and
  model state, per-assembly child lists, header normalisation), the import
  command that assigns keys and writes `references/`, the lock reduced to a
  derived index (design document 2.3), a `source.json` per directory in place of
  the planned `metadata.json` (4.2, 4.3), the publication record moved into the
  authored part's directory.
- `mechanical-docs`: nothing for the conversion; it reads the derived scene.
  One full render after the re-export.
- The enclosure: the conversion on a branch, re-keyed curated files, the
  authored monitor envelope moved to the new shape.
- Here: the specification and validator, the flatten step, then the geometry
  facts, build and check commands.

## Changes since the first draft (2026-11-10)

- Writers are named as commands, not machines; the exporter identifies files by
  master id and the import command assigns keys.
- A place for the exporter's run-level records (`references/receipts/`), and
  the data-section hash as a recorded identity.
- The lock is derived from the directories and checked against them; the
  publication record moves to the authored part's directory.
- The fingerprint is compared within a tolerance; its stability across kernels
  moved to "Not verified".
- The rule for a second model state is fixed now.
- The acceptance test compares the flattened scene with today's instead of
  reusing renders, which the renderer's hash gating does not allow.
- A fifth Windows test, and the correction to the header-author count.
- The results of the dry run, and with them the first evidence on overrides,
  on the fingerprint and on reproducible builds.
- The results of the five Windows tests, with a recommendation for the
  protocol, and the correction that one part's volume difference comes from
  hidden bodies, not from measurement accuracy.
- Peter's three decisions of 2026-11-11, and the results of the three Windows
  tests that AP242 asked for.
