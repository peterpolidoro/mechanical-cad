# mechanical-cad living plan

## Objective

Give Peter's Inventor and Vault projects an open representation in Git and the
open-source tools to check it, document it and add to it, with the
free-standing tank enclosure as the test project. The full statement is
docs/direction.md. Finished checkpoints are in .agents/HISTORY.md.

## Current state (2026-11-10)

Peter has not accepted the direction document or the layout. On 2026-11-10 he
asked for as much as possible to be done without his input while he assembles
the enclosure, so the layout was built and tested against the recommended
options (two roots, readable keys). All of it is provisional.

What exists here:

- `mechanical_cad/` (standard library): `layout.py` validates a project
  repository; `flatten.py` composes the per-assembly manifests into the
  `scene.json` that `mechanical-docs` reads; `compare.py` says whether two
  scenes are the same assembly; `facts.py` compares measured geometry and
  evaluates a part's `checks.json`; `stepfile.py` reads a STEP file's
  identities, header and unit and normalises the header; `cli.py` has
  `validate`, `flatten`, `check`, `lock`, `compare-scenes`, `step-info` and
  `normalise-header`.
- `tools/` (run by FreeCADCmd): `step_facts.py` writes `facts.json` for
  imported parts; `build_part.py` builds an authored part from `build.py` and
  `parameters.json`. `tools/conversion_acceptance.py` (plain Python) runs the
  acceptance test of docs/layout-proposal.md.
- `examples/layout-fixture/`: a synthetic project with imported and authored
  parts, a flexible instance with an override, and its generator.
- docs/layout-specification.md: the draft the code implements.
- Tests: 100 pass in the base role and 4 more with FreeCAD (run 2026-11-10,
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

Also done that day, in all four repositories: stale status text corrected,
plans cut down to the current state with their past moved to history files,
and the review findings and open questions that existed only on the shared
directory written into the repositories. The Windows agent's queued work was
replaced by one message asking for five read-only tests, and the operator
prompts were rewritten.

## Open decisions to put to Peter

Layout:

1. Two roots (`references/`, `designs/`) or one tree with an authority field.
   Recommended and built: two roots.
2. Readable directory keys tied to the Vault master id, or a mirror of Vault's
   folder tree. Recommended and built: readable keys.
3. AP214 or AP242, after the Windows test.
4. Acceptance of docs/direction.md as a whole. Its "one authority per part"
   entry under "Decided" has no date; confirm it and date it.

The four questions under "Not settled" in docs/direction.md:

5. The Inventor requirement: the enclosure's brief asks for design work in
   Inventor and records in Vault; the decision of 2026-10-23 is parts as code,
   referenced from Inventor as STEP. Not reconciled.
6. Names in public files. Known places: all 37 STEP headers carry an
   account-like author name (four people, none of them Peter); the exporter's
   records and the lock carry Peter's Windows account in absolute paths and a
   host name; the enclosure's published `docs/manual/manual.json` and
   `SOURCE.json` carry the account and the share path; `vault-project.toml` and
   eight tracked files of `vault-cad-tools` carry the server name and vault
   name; the Vault folder path with the lab's name is in 57 tracked files of
   the enclosure. Removing them from new files is possible at the re-export;
   history and the published site are a separate matter.
7. Whether supplier-originated models may be redistributed publicly, and the
   wording of the enclosure README's scope statement.
8. Where on GitHub the repositories live. `origin` here is still Codeberg.

Smaller ones:

9. Whether the generated manual packages move out of the enclosure's tracked
   `docs/` (141 MB there).
10. Whether hand-edited `parameters.json`, `checks.json` and authored
    `assembly.json` become TOML, as this repository's rule for hand-edited
    files would have it.
11. The ten questions on the Vault side
    (`vault-cad-tools/docs/native-checkin-adapter-design.md`, section 10) and
    the enclosure's own (its plan, "Open items").

## Next work, in order

1. Peter's answers to decisions 1, 2 and 4. If he takes the recommendations,
   nothing built here changes; if not, the specification, validator and
   converter change together.
2. The enclosure's conversion on a branch. The dry run covers `references/`
   and the lock. Still to do there: re-key the curated files that carry part
   ids (`assembly/materials.json`, the two procurement sheets,
   `joint-audit.json`) by script; point the eight project scripts that read
   `references/enclosure/` at the flattened scene; decide what stays of the old
   tree; move the monitor envelope to `designs/parts/` with `build_part.py`,
   and its publication record into `vault.json`. Then run the acceptance test
   on the branch. `main` stays as it is until that passes.
3. The Windows tests, whenever Peter starts that agent. The request is in the
   shared mailbox. Then decision 3.
4. Specify the exporter's package (files named by master id and model state, a
   child list per assembly, no absolute paths, normalised header), have the
   Windows exporter write it, and make `import-snapshot` read it. Re-export the
   enclosure and compare it with step 2 using `compare-scenes`.
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
- Nothing here has been run on Windows.

## Hazards

- **The enclosure's `main` feeds the published manual**, which Peter is
  assembling from. Its Pages workflow now runs only when a push changes
  `docs/`, `mkdocs.yml` or the workflow. Conversion work belongs on a branch.
- **The shared directory has no history.** Decisions that last go into a
  repository. Its `PLAN.md` is a dated log; where it differs from
  docs/direction.md, the direction wins.
- **The shared clones the Windows agent syncs from lag behind** until someone
  fast-forwards them after Peter pushes. The Windows request assumes he has
  pushed the changes of 2026-11-10.
- **Remotes.** `origin` here and in `mechanical-docs` still points at Codeberg;
  the GitHub remote is `peterpolidoro`. Remotes are Peter's to change.
