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

Asked of Windows that day (three read-only tests): whether AP242 exports are
stable between sessions and what the saved-view block depends on; which
translator options exist; and all 37 parts as AP242 for Linux to compare with
the tracked AP214 files by fingerprint. The agent was still running when this
was written and had not reported. Read from its unfinished run, so not yet
evidence: `compare_step_exports.py` finds all 37 AP242 files to be the same
geometry as the tracked AP214 parts (one with three invisible items left
out); exports made without a view have one data section across sessions,
exports made with a view open change with the camera; the translator reports
eight options and none concerns hidden bodies or the view. The check is
repeated on the sealed run.

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
  scenes are the same assembly; `facts.py` compares measured geometry and
  evaluates a part's `checks.json`; `stepfile.py` reads a STEP file's
  identities, header, unit and invisible items, normalises the header and
  writes the file without its invisible items; `cli.py` has `validate`,
  `flatten`, `check`, `lock`, `compare-scenes`, `step-info`,
  `normalise-header` and `visible-only`.
- `tools/` (run by FreeCADCmd): `step_facts.py` writes `facts.json` for
  imported parts; `build_part.py` builds an authored part from `build.py` and
  `parameters.json`. `tools/conversion_acceptance.py` (plain Python) runs the
  acceptance test of docs/layout-proposal.md. `tools/compare_step_exports.py`
  (FreeCADCmd) compares other exports of a project's parts with the tracked
  files by fingerprint. `tools/update_shared_clone.py`
  (plain Python) fast-forwards a clone on the network share by file copies,
  because git cannot write safely on that mount.
- The enclosure on its branch is the second project in the layout, after the
  fixture, and the first with an authored part published to Vault.
- `examples/layout-fixture/`: a synthetic project with imported and authored
  parts, a flexible instance with an override, and its generator.
- docs/layout-specification.md: the draft the code implements.
- Tests: 118 pass in the base role and 6 more with FreeCAD (run 2026-11-11,
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

1. Whether the saved-view block of AP242 files has to be normalised like the
   header. It depends on the Windows stability test; nothing to decide until
   that has run.
2. Acceptance of docs/direction.md as a whole. Its "one authority per part"
   entry under "Decided" has no date; confirm it and date it.

The four questions under "Not settled" in docs/direction.md:

3. The Inventor requirement: the enclosure's brief asks for design work in
   Inventor and records in Vault; the decision of 2026-10-23 is parts as code,
   referenced from Inventor as STEP. Not reconciled.
4. Names in public files. Known places: all 37 STEP headers carry an
   account-like author name (four people, none of them Peter); the exporter's
   records and the lock carry Peter's Windows account in absolute paths and a
   host name; the enclosure's published `docs/manual/manual.json` and
   `SOURCE.json` carry the account and the share path; `vault-project.toml` and
   eight tracked files of `vault-cad-tools` carry the server name and vault
   name; the Vault folder path with the lab's name is in 57 tracked files of
   the enclosure. Removing them from new files is possible at the re-export;
   history and the published site are a separate matter.
5. Whether supplier-originated models may be redistributed publicly, and the
   wording of the enclosure README's scope statement.
6. Where on GitHub the repositories live. `origin` here is still Codeberg.

Smaller ones:

7. Whether the generated manual packages move out of the enclosure's tracked
   `docs/` (141 MB there).
8. Whether hand-edited `parameters.json`, `checks.json` and authored
   `assembly.json` become TOML, as this repository's rule for hand-edited
   files would have it.
9. Which Vault files the enclosure project mirrors. Its folder holds a second
   root assembly, `SLLB Enclosure.iam`, and four other native files that the
   snapshot does not hold; the snapshot holds 18 files from outside the
   folder. The snapshot follows one root assembly; the target workflow of
   2026-10-23 speaks of mirroring "every file of that project". Peter on
   2026-11-10: he does not know that assembly and wants to look at it in
   Inventor before giving an opinion. What the discovery recorded about it is
   in the enclosure's plan.
10. The ten questions on the Vault side
    (`vault-cad-tools/docs/native-checkin-adapter-design.md`, section 10) and
    the enclosure's own (its plan, "Open items").

## Next work, in order

1. Peter's review of the enclosure's branch `layout-conversion` (done on
   2026-11-11 in a worktree beside the project checkout, at Peter's word; the
   project's plan on that branch has the state and what was checked). When he
   starts the Windows agent: review its three AP242 tests, and compare the 37
   AP242 exports with the tracked AP214 files (`step_facts.py` on both, then
   the fingerprints).
2. The merge of that branch, which is Peter's. `vault-cad-tools` reads the new
   lock since 2026-11-11 (`status`, `prepare-publish` from
   `designs/parts/<key>/part.step`, `import-publish-result` into the part's
   `vault.json`), so nothing in the tools holds it back. The index is derived
   in two places, here and there; they agree on the enclosure, and no test
   compares them.
3. The exporter's package. A draft is in docs/exporter-package.md (2026-11-11):
   one directory per Vault file and model state, identities and no keys, no
   workstation paths or names of people, AP242 exported without a view, the
   header normalised, and what the import command does with it. It is not
   reviewed. Next: confirm its two statements that wait for the Windows AP242
   report; Peter's and the Windows agent's review; the Windows exporter
   writes it; `import-snapshot` reads it into an existing project, keeping
   keys. Then re-export the enclosure and compare it with the branch
   (`compare-scenes`, and `compare_step_exports.py` for the parts).
4. One full render of the manual from the re-exported project, in
   `mechanical-docs`, compared with today's by parts, quantities, steps and
   checks. Merge the branch.
5. The first new part for the enclosure written as code, built and checked
   here, manufactured, then published to Vault.
6. The Guix channel (`.guix-channel` pointing at `.guix/modules`, as
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
