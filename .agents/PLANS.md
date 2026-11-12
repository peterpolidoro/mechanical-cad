# mechanical-cad living plan

## Objective

Give Peter's Inventor and Vault projects an open representation in Git and the
open-source tools to check it, document it and add to it, with the
free-standing tank enclosure as the test project. The full statement is
docs/direction.md. Finished checkpoints are in .agents/HISTORY.md.

## Current state (2026-11-11)

On 2026-11-11 Peter decided the layout's three open choices: two roots and
readable keys, which is what was built on 2026-11-10 while he assembled the
enclosure, and AP242 for files exported from Inventor, against the
recommendation of AP214 and after hearing both sides
(docs/layout-proposal.md, "Open choices"). He has not been asked again about
the direction document as a whole.

What AP242 needed on Linux was built the same day: an AP242 file holds the
bodies hidden in the native part, marked invisible, and FreeCAD ignores the
mark. `stepfile.py` finds the marked items and writes the file without them;
`step_facts.py` measures that and records how many items it left out; the
validator compares that number with the file; `flatten` writes the filtered
file as the scene's asset; `visible-only` is the command for a person.
Measured on the three AP242 files of the Windows tests: the corner cube
without its three invisible solids has the fingerprint of its AP214 file, and
the other two measure the same in both protocols. One part of the 37 has
hidden bodies, so the filter rests on one real file; any other form of the
mark is refused.

Asked of Windows that day and reported the same day (three read-only tests,
shared evidence run `2026-11-11-windows-ap242-tests-01`, 184 files checked
against their checksums on Linux): AP242 exports made from a document without
a view have one data section across sessions, and the exporter runs without a
view; with a view the file carries that view's camera, and the difference is
confined to the 12 instances the camera reaches (recounted on Linux from the
run's files); the translator reports eight options and none concerns hidden
bodies or the view; and `compare_step_exports.py` on the sealed files finds
all 37 AP242 exports to be the same geometry as the tracked AP214 parts, one
with three invisible items left out. One framing part has a solid with a
void, written as `BREP_WITH_VOIDS` in both protocols: counts of solids from
text take both (one test here did not, and does now). The detail is in
docs/layout-proposal.md, "Windows tests of 2026-11-11". The Windows patch
(probes and text-level helpers, the exporter untouched) is reviewed and
applied in `vault-cad-tools`.

What follows for the saved view, written into docs/exporter-package.md
(draft 2) and docs/layout-specification.md: it is not normalised; the
exporter exports only from documents without a view and checks that. Peter
has not confirmed it; it is among the draft's choices under "Open decisions".

The import side of the package was built the same day in `vault-cad-tools`
(`import-snapshot` reads the package into a project, keeps keys, leaves
unchanged files untouched), against packages written on Linux, because no
exporter writes the package yet. Tried on copies of the converted enclosure:
a package of what the project holds changes nothing; the same package with
the 37 AP242 files of the Windows tests rewrites the 37 parts and nothing
else, and after `step_facts.py` the project validates and its flattened scene
equals the branch's apart from the STEP files. For that comparison
`compare-scenes` got `--other-export`, which lists STEP files that differ
without counting them. The detail is in docs/exporter-package.md. The
Windows agent's review of the draft may still change the package (who derives
the overrides of flexible instances is put to it), and the reader with it.

Peter opened the question of assemblies that day: he wants to look at a
whole assembly in FreeCAD, and asked whether the exporter should also write a
STEP file per assembly. Decided by him: no, such files are generated from the
part files and the manifests and not stored (docs/direction.md). Built for
it: `tools/assembly_step.py` writes one STEP file and one FreeCAD document of
any assembly of a project into the project's ignored `.cache/assemblies/`
(that location is a proposal; he asked whether it should be a temporary
directory instead), reads its file back and matches every solid with the
flattened scene; `tools/compare_assembly_step.py` runs the same match on a
file something else wrote. On the converted enclosure: 37 parts, 155
occurrences, 479 solids, 102 solid definitions as in the part files (the
geometry is shared), every solid within 0.0018 mm and 2.5e-4 of its volume;
a second build gives the same bytes; 83 s. Not observed: the FreeCAD
document opened in the GUI (an off-screen session had no graphics context),
so whether the part definitions open hidden is unknown until Peter opens it.
Asked of Windows the same day: Inventor's own STEP export of the root
assembly, as evidence only, to compare with the records. No record shows
that comparison was ever made.

The enclosure was converted that day on its branch `layout-conversion`, and
the acceptance test passed there on the tracked tree (it had passed on a dry
run the day before). The conversion brought two things back here: a
`README.md` is now a file the layout expects beside an authored part or
assembly, and the flattened scene lists parts by key, so a project that
numbers parts in scene order has to state its own order (the enclosure's
recipe uses its procurement sheet).

What exists here:

- `mechanical_cad/` (standard library): `layout.py` validates a project
  repository; `flatten.py` composes the per-assembly manifests into the
  `scene.json` that `mechanical-docs` reads; `compare.py` says whether two
  scenes are the same assembly, and for another export of the same versions
  lists the STEP files that differ; `facts.py` compares measured geometry and
  evaluates a part's `checks.json`; `stepfile.py` reads a STEP file's
  identities, header, unit and invisible items, normalises the header and
  writes the file without its invisible items; `solids.py` matches the solids
  of a whole-assembly file with a scene; `cli.py` has `validate`,
  `flatten`, `check`, `lock`, `compare-scenes`, `step-info`,
  `normalise-header` and `visible-only`.
- `tools/` (run by FreeCADCmd): `step_facts.py` writes `facts.json` for
  imported parts; `build_part.py` builds an authored part from `build.py` and
  `parameters.json`. `tools/conversion_acceptance.py` (plain Python) runs the
  acceptance test of docs/layout-proposal.md. `tools/compare_step_exports.py`
  (FreeCADCmd) compares other exports of a project's parts with the tracked
  files by fingerprint. `tools/assembly_step.py` and
  `tools/compare_assembly_step.py` (FreeCADCmd) build and compare a STEP file
  of a whole assembly. `tools/update_shared_clone.py`
  (plain Python) fast-forwards a clone on the network share by file copies,
  because git cannot write safely on that mount.
- The enclosure on its branch is the second project in the layout, after the
  fixture, and the first with an authored part published to Vault.
- `examples/layout-fixture/`: a synthetic project with imported and authored
  parts, a flexible instance with an override, and its generator.
- docs/layout-specification.md: the draft the code implements.
- Tests: 126 pass in the base role and 8 more with FreeCAD (run 2026-11-11,
  Python 3.12.12, pytest 9.0.2, FreeCAD 1.1.3, OpenCASCADE 7.9.3).

What was run against the enclosure (a dry run into the enclosure's ignored
`.cache/layout-dry-run-01/`; nothing tracked there changed):

- `vault-cad import-snapshot` converted the snapshot: 37 parts, 7 assemblies,
  44 overrides.
- The acceptance test passed all four checks: the layout validates; the STEP
  files are the exporter's bytes; the flattened scene equals the exporter's
  (37 parts, 17 assembly nodes, 155 occurrences, largest translation
  difference 6.5e-11 mm); the documentation project re-keyed to the new part
  ids loads in `mechanical_docs inspect` with the same counts, finding,
  inventory, build scope and steps.
- `step_facts.py` measured all 37 parts as valid (479 solids over the 155
  occurrences).

The measurements and what they mean are in docs/layout-proposal.md, "Dry run of
2026-11-10".

The Windows agent, started by Peter that day, ran the five read-only tests and
a read-only discovery of the Vault folder. Linux verified its evidence,
reviewed and applied its patch to `vault-cad-tools`, repeated the text-level
results with `stepfile.py` and compared the AP214 and AP242 exports in FreeCAD.
The results are in docs/layout-proposal.md, "Windows tests of 2026-11-10". In
short: AP214 exports are stable across sessions and normalise to identical
bytes; the exporter can write the normalised header with a port of
`stepfile.py` that gives the same bytes; AP242 carries hidden bodies that
FreeCAD reads as solids; nothing has changed in Vault since the snapshot; and
the Vault folder has a second root assembly that the snapshot does not hold.

Also done that day, in all four repositories: stale status text corrected,
plans cut down to the current state with their past moved to history files,
and the review findings and open questions that existed only on the shared
directory written into the repositories. The Windows agent's queued work was
replaced by one message asking for five read-only tests, and the operator
prompts were rewritten.

## Open decisions to put to Peter

The layout's three choices were decided on 2026-11-11 and are in
docs/direction.md, "Decided". What is left:

1. The exporter's package, docs/exporter-package.md (draft 2). Its choices:
   no names of people and no workstation paths in any record; files named by
   master id and model state, keys assigned on Linux; a refresh replaces only
   what changed in Vault; the saved view is left as the translator wrote it,
   and the exporter refuses a document that has a view.
2. Acceptance of docs/direction.md as a whole. Its "one authority per part"
   entry under "Decided" has no date; confirm it and date it.
3. Where a generated whole-assembly STEP file goes. Built and proposed: the
   project's ignored `.cache/assemblies/` (kept between sessions, beside what
   it derives from, never committed); `--out` writes anywhere else. Peter
   asked on 2026-11-11 whether a temporary directory is better.

The four questions under "Not settled" in docs/direction.md:

4. The Inventor requirement: the enclosure's brief asks for design work in
   Inventor and records in Vault; the decision of 2026-10-23 is parts as code,
   referenced from Inventor as STEP. Not reconciled.
5. Names in public files. Known places: all 37 STEP headers carry an
   account-like author name (four people, none of them Peter); the exporter's
   records and the lock carry Peter's Windows account in absolute paths and a
   host name; the enclosure's published `docs/manual/manual.json` and
   `SOURCE.json` carry the account and the share path; `vault-project.toml` and
   eight tracked files of `vault-cad-tools` carry the server name and vault
   name; the Vault folder path with the lab's name is in 57 tracked files of
   the enclosure. Removing them from new files is possible at the re-export;
   history and the published site are a separate matter.
6. Whether supplier-originated models may be redistributed publicly, and the
   wording of the enclosure README's scope statement.
7. Where on GitHub the repositories live. `origin` here is still Codeberg.

Smaller ones:

8. Whether the generated manual packages move out of the enclosure's tracked
   `docs/` (141 MB there).
9. Whether hand-edited `parameters.json`, `checks.json` and authored
   `assembly.json` become TOML, as this repository's rule for hand-edited
   files would have it.
10. Which Vault files the enclosure project mirrors. Its folder holds a second
   root assembly, `SLLB Enclosure.iam`, and four other native files that the
   snapshot does not hold; the snapshot holds 18 files from outside the
   folder. The snapshot follows one root assembly; the target workflow of
   2026-10-23 speaks of mirroring "every file of that project". Peter on
   2026-11-10: he does not know that assembly and wants to look at it in
   Inventor before giving an opinion. What the discovery recorded about it is
   in the enclosure's plan.
11. The ten questions on the Vault side
    (`vault-cad-tools/docs/native-checkin-adapter-design.md`, section 10) and
    the enclosure's own (its plan, "Open items").

## Next work, in order

1. Peter's review of the enclosure's branch `layout-conversion` (done on
   2026-11-11 in a worktree beside the project checkout, at Peter's word; the
   project's plan on that branch has the state and what was checked).
2. The merge of that branch, which is Peter's. `vault-cad-tools` reads the new
   lock since 2026-11-11 (`status`, `prepare-publish` from
   `designs/parts/<key>/part.step`, `import-publish-result` into the part's
   `vault.json`), so nothing in the tools holds it back. The index is derived
   in two places, here and there; they agree on the enclosure, and no test
   compares them.
3. The exporter's package. Draft 2 is in docs/exporter-package.md
   (2026-11-11): one directory per Vault file and model state, identities and
   no keys, no workstation paths or names of people, AP242 exported from
   documents without a view, the header normalised, and what the import
   command does with it. Asked of Windows on 2026-11-11, for when Peter
   starts it: review the draft against what Inventor and Vault give, and
   write the package as a new mode of the exporter that leaves today's
   output unchanged, run read-only on the enclosure. On Linux, in
   `vault-cad-tools`, `import-snapshot` reads the package into an existing
   project, keeping keys (built 2026-11-11, tried on packages written on
   Linux). When Windows reports: correct the draft and the reader where
   Inventor disagrees with them, import its package into the branch, measure,
   validate, and compare with the branch as it is (`compare-scenes
   --other-export`, and `compare_step_exports.py` for the parts). The scene's
   part properties will differ where the exporter leaves out the names of
   people; that difference is expected and has to be read, not waved through.
4. The comparison with Inventor's own export of the root assembly, when
   Windows delivers it (asked 2026-11-11): `compare_assembly_step.py` on the
   branch's project and that file, in the assembly's own frame. A part that
   is reported in the wrong place is a finding about the recorded placements
   or about how the overrides of flexible instances are derived, to be
   settled before the package's review is.
5. One full render of the manual from the re-exported project, in
   `mechanical-docs`, compared with today's by parts, quantities, steps and
   checks. Merge the branch.
6. The first new part for the enclosure written as code, built and checked
   here, manufactured, then published to Vault.
7. The Guix channel (`.guix-channel` pointing at `.guix/modules`, as
   `orb-weaver-context` does), then OCP against Guix's `opencascade-occt`,
   build123d, CadQuery. Peter recorded this packaging as his own deferred work
   on 2026-10-23; confirm before starting it.

## Known limits of what was built

- The validator has been run on two projects: the fixture and the converted
  enclosure. The tolerances for comparing geometry facts are provisional (one
  kernel version).
- `import-snapshot` reads only the package the exporter wrote on 2026-10-21
  and refuses suppressed or mirrored occurrences, an instance whose definition
  disagrees with another instance's, and nested flexible instances that would
  need an override on an outer level.
- `build_part.py` takes a FreeCAD `Part.Shape` with one product. There is no
  build123d or CadQuery path.
- The scene written by `flatten` copies every STEP file into its output
  directory, because the documentation loader resolves assets below the scene.
- A whole-assembly STEP file is for reading. FreeCAD's writer does not give
  back exactly what it read: over the enclosure's 102 solids the volume of a
  solid moves by up to 2.5e-4 of itself and its centre of mass by up to
  0.0018 mm (FreeCAD 1.1.3). It has no colour, and the FreeCAD document
  beside it has not been seen in the GUI.
- On Windows only `mechanical_cad/stepfile.py` has been run, read-only, to
  check the PowerShell port against it. The validator, the flatten step and the
  tools under `tools/` have not.

## Hazards

- **The enclosure's `main` feeds the published manual**, which Peter is
  assembling from. Its Pages workflow now runs only when a push changes
  `docs/`, `mkdocs.yml` or the workflow. Conversion work belongs on a branch.
- **The shared directory has no history.** Decisions that last go into a
  repository. Its `PLAN.md` is a dated log; where it differs from
  docs/direction.md, the direction wins.
- **The shared clones the Windows agent syncs from lag behind** until someone
  fast-forwards them after Peter pushes. From Linux this is done with
  `tools/update_shared_clone.py`, never by git commands that write on the
  mount: a `git fetch` there deleted a ref on 2026-11-10.
- **Remotes.** `origin` here and in `mechanical-docs` still points at Codeberg;
  the GitHub remote is `peterpolidoro`. Remotes are Peter's to change.
