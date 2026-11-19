# mechanical-cad history

Finished checkpoints, oldest last. Commit ids and "uncommitted" notes describe
the day they were written. The current plan is .agents/PLANS.md.

---

## The three rounds of 2026-11-19

What was built is in docs/direction.md, "Built so far" (stage 7 and the two entries after it, and the
Guix packages); this is how the day went, and the paragraph the plan carried while it lasted.

- **First round**, at Peter's word "one project file, go ahead and build it": a project's finishes
  (`finishes.toml`, `finishes.json` beside the scene, pictures and sections drawn with them), read by
  `mechanical-docs`, with a still outside a manual; a draft for the first project.
- **Second round**, at his word to do as much as could be done without him: videos in `mechanical-docs`,
  the exposure sheet for a manual with finishes, the colours of a file that is taken apart kept as
  finishes, dimensions in a section, vents, feet, a prism that follows a rectangular board and flat
  patterns, the index compared between two repositories, and the plan cut down.
- **Third round**, at his word to complete as much as could be of six things that were put to him; he said
  then that his Windows laptop was down, that no full-quality render of the first project's manual was
  needed yet, and that he was not sure what joints, poses and views meant. It was run as four agents in
  this checkout, each with files of its own, three sessions one after another in `mechanical-docs`, and
  the main thread on the joints draft, the print check's bridge, the plans and the direction. The Guix
  packages were changed on a copy outside the checkout, so that nobody's environment was rebuilt under
  them, and brought in when everything else had finished and they had been built and tested.

The plan's paragraph, as it stood:

> Done on 2026-11-19 at Peter's word to go on without him, and so no longer
> on this list: the colours of a file that is taken apart, vents and feet,
> the prism that follows a rectangular board, flat patterns through the cut
> file, dimensions in a section, a test of the index derived in two places,
> and the housekeeping (the plan's record moved to .agents/HISTORY.md, the
> README's status). And in a third round that day, at his word to complete
> as much as could be of six things: the day's code read line by line and
> eleven defects corrected, each with a test (docs/direction.md, "Built so
> far", has them); pockets for stick-on feet and the bridge the print check
> needed to pass them; staggered vents and vents on round corners; the
> width of the cut and a pattern of something open in the cut file;
> hatching, the edges behind the plane and arcs in a section; Line Art in
> `mechanical-docs`; the joints and poses draft with its tools, and a joint
> as video; a part that is faces and no solid named by the fit checks and
> allowed by name in `mechanical-docs`' mesh stage. And the Guix packages
> brought to where they can be offered ("Next work" has what is left).

Tests when the day ended: 639 without a kernel (121 skipped), 757 with FreeCAD, the bindings, build123d
and bd_warehouse (5 skipped), the 14 of `tests/test_picture.py` with the viewer; in `mechanical-docs` 221
(6 skipped) and 227 with FreeCAD; in `vault-cad-tools` 113.

## The record of 2026-11-10 to 2026-11-18, moved here on 2026-11-19

Two sections of the plan as they stood when they were moved, unchanged but for their headings: what
existed and what had been run by 2026-11-13, and the work list with the record of each item as it was
done, up to stage 6 on 2026-11-18. The plan had grown to hold both beside its current state. What was
still to do in them is carried in the plan's "Next work". What has been built since, and where the
goals stand, is in docs/direction.md, "Built so far".

## Current state, as it stood on 2026-11-13

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
a second build gives the same bytes; 83 s. The FreeCAD document was first
opened in the FreeCAD window on 2026-11-12 (below).
Asked of Windows the same day: Inventor's own STEP export of the root
assembly, as evidence only, to compare with the records.

That comparison was made on 2026-11-12. Windows exported the root assembly
as one AP242 file, read-only (no Vault access, nothing saved, the 44
documents bound to the acquisition by hash). `compare_assembly_step.py` on
the converted enclosure and that file: 479 of 479 solids where the records
put them, within 6.4e-11 mm, none unexpected; read in the wrong frame, as a
control, none of the 479 matches. So the recorded placements, the 44 derived
overrides of the two flexible instances among them, are the assembly
Inventor exports. Found on the way: such a file keeps
each document's length unit (inches, millimetres and centimetres in one
file), which the kernel reads correctly; its one `INVISIBILITY` lists each
styled item twice, which `stepfile.visible_only` handles; and Inventor
writes a flexible sub-assembly's product with the positions it has in the
assembly, which can hold only while that document has one instance. The
detail is in docs/layout-proposal.md. Windows went on to the package task.

On 2026-11-12 Peter asked that people and agents can find out which
assemblies a project can build, and suggested short `make` commands in
place of the long ones. Built: `python3 -m mechanical_cad assemblies PROJECT`
lists every assembly with its key, its size, what it is part of and whether
its built files are current (`mechanical_cad/assemblies.py`); an unknown key
is refused with the list of keys; a `Makefile` here runs the commonest
commands for a project given as `PROJECT=DIR`; and the enclosure's Makefile,
on its branch, hands `validate`, `assemblies` and `assembly` to it, finding
this checkout beside it or through an ignored `local.mk`. Run on the
enclosure through `make`: the list (7 assemblies), `validate`, the camera
frame built (16 parts, 36 occurrences, 124 solids, 25 s), an unknown key
refused. docs/layout-specification.md, "Short commands in a project", has
the lines a project's Makefile needs.

The same day Peter asked for a `make` command that opens an assembly in
FreeCAD through `guix shell`. Opening a built document in the FreeCAD window
for the first time showed that it opened empty: FreeCAD hides every object
while it restores a document and shows again only what the document's view
data say, and a document saved by FreeCADCmd has none. This held for every
document built until then. Fixed in the build: `mechanical_cad/fcstd.py`
appends the view data to the document (the occurrences and their containers
shown, the part files hidden, the top of the tree open, and an isometric
camera that has the assembly in view), and the build version went to 2, so
earlier built files are listed as out of date and rebuilt. Seen in the
FreeCAD window (1.1.3, X11, a session with its own empty FreeCAD settings):
the whole enclosure upright and in view as the document opens, 155 links
and 18 containers shown, the 37 part files hidden, the document not marked
as changed; the same for the caster assembly. `make open [KEY=K]` builds if
need be and opens the document (`python3 -m mechanical_cad built PROJECT
[KEY]` gives its path); run for the caster assembly, FreeCAD came up on the
document and stayed until the test's time limit ended it. Peter ran
`make open` on the whole enclosure the same day, with his own FreeCAD
settings: the assembly opens, he sees all the parts and can hide them. Not
tried: the window on Wayland.

The Windows agent delivered the exporter's package that day
(`windows/Export-Package.ps1`, read-only, two runs that agree in every file
but `package.json`). Its review of draft 2 changed the draft: the package
states every occurrence in context (`occurrences.json`) and no override.
Done on Linux: the run's 357 files verified against its checksums; the
patch read by a second agent (nothing in it reaches Vault or a network or
saves a document; findings on failure paths went back to Windows) and
applied, uncommitted, in `vault-cad-tools`; the reader there derives the
overrides and refuses what the layout cannot record (115 tests);
`stepfile.header` gives every schema name and no protocol to a file that
names two, and the validator refuses such a file; draft 3 written; the
package imported into a copy of the enclosure's branch and checked (next
work, item 3). Not done: the import into the branch itself.

Later that day Windows corrected the six findings and ran the exporter
again: its package is the first one in every file but `package.json`. On
Linux the corrections were read by a second agent and applied, uncommitted,
in `vault-cad-tools` (115 tests). Agreed with Windows: a run in which a
dialog of Inventor was dismissed delivers no package (now in the draft), and
the seven older Windows scripts that start Inventor before their `try` stay
as they are until each is next changed. Six smaller remarks went back for
the next change of the script. The Windows agent has no task.

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
  of a whole-assembly file with a scene; `assemblies.py` lists a project's
  assemblies and the state of their built files; `fcstd.py` writes into a
  FreeCAD document what its window shows; `cli.py` has `validate`,
  `flatten`, `assemblies`, `built`, `check`, `lock`, `compare-scenes`,
  `step-info`, `normalise-header` and `visible-only`.
- `Makefile`: short forms of the tests and of `validate`, `assemblies`,
  `assembly` and `open` for a project given as `PROJECT=DIR`. It needs GNU make on the
  host; the Guix manifests do not provide it, so no test runs it.
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
- The enclosure, on its `main` since 2026-11-12, is the second project in
  the layout, after the fixture, and the first with an authored part
  published to Vault.
- `examples/layout-fixture/`: a synthetic project with imported and authored
  parts, a flexible instance with an override, and its generator.
- docs/layout-specification.md: the draft the code implements.
- Tests: 144 pass in the base role, 148 with FreeCAD alone (what measures is
  skipped there) and 154 with FreeCAD, the OCP bindings and build123d (run
  2026-11-13, after the adaptive integration; Python 3.12.12, pytest 9.0.2,
  FreeCAD 1.1.3, OpenCASCADE 7.9.3).

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

## Next work, in order, with the record of each item up to 2026-11-18

Items 1 to 3 below are done, item 4 but for the manual's render at full
quality, and item 6 as far as build123d; they stand here as their record. A
new order for what is left was proposed on 2026-11-16 in docs/direction.md,
"Proposed: order of work": one real part through the whole loop (item 5
here), publishing it as collaborators will meet it, keeping a mirror
current, the manual finished from the bench, a drawn part if wanted, and the
packages offered to Guix. Peter accepted it that day (open decision 15),
and two things began: the monitor as the first real part (item 5), and three
read-only tests against Vault asked of the Windows agent.

1. Peter's review of the enclosure's branch `layout-conversion` (done on
   2026-11-11 in a worktree beside the project checkout, at Peter's word; the
   project's plan on that branch has the state and what was checked).
2. The merge of that branch: done by Peter on 2026-11-12 (item 4). The
   index is derived in two places, here and in `vault-cad-tools`; they agree
   on the enclosure, and no test compares them.
3. The exporter's package. Draft 3 is in docs/exporter-package.md
   (2026-11-12): Windows reviewed draft 2 against Inventor and wrote the
   package for the enclosure with a new script, read-only, twice; Linux
   reviewed it the same day, taught `import-snapshot` in `vault-cad-tools` to
   read it (the exporter writes every occurrence in context and the import
   derives the overrides), and imported it into a copy of the branch: it
   validates, its scene equals the branch's with no placement differing, and
   it matches Inventor's own export of the root assembly. The details are in
   the draft, "What the import command does with it". On Peter's word the
   package was imported into the enclosure's branch itself on 2026-11-12
   (the one the corrected exporter wrote; the same files but `package.json`):
   the branch validates, its scene equals the one before with no placement
   differing, and it matches Inventor's own export of the root assembly, 479
   of 479 solids. One thing broke and was repaired in the project: its site
   pages found the earlier exporter's part ids in each `source.json`, which
   an import replaces; they are now read from the earlier export's own
   record under `references/receipts/`. Left: Peter's review of the draft.
   `mechanical-docs` was run on the imported branch the same day, the whole
   pipeline at preview quality (staging, inspect, meshes, 88 renders, manual,
   check: all passed), and its manual has the steps, joints, quantities and
   groups of the published one. It printed the line about quantities being
   CAD instance counts only for the exporter's own scene, not for a
   flattened one; corrected in `mechanical-docs` (uncommitted there, 127
   tests). Its mesh script cannot be given `--max-triangles` under FreeCADCmd
   1.1.3, which takes a dashed option after `--pass` for its own; the default
   is the value the recipe asked for. Not done: a full-quality render.
4. Merged: Peter fast-forwarded the enclosure's `main` to the branch on
   2026-11-12 (7a1af68), and the shared clones of this repository and of the
   enclosure were brought level. Done on Linux that day, after the merge:
   - What `main` gives is recorded for the Windows side in the shared
     evidence `2026-11-12-linux-main-baseline-01`: `vault-cad status`,
     `validate`, `assemblies`, and a repeat import of the same Vault versions
     into a clone of `main`, which leaves all 44 directories untouched.
   - The Windows task is written (`to-windows/20261112T181749Z-...`): check
     out and read the new layout on Windows (`mechanical_cad` has not run
     there), the six remarks on the exporter, `Export-Package.ps1` described
     as the exporter, a list of what serves only the earlier package, one
     run of the changed exporter, and Inventor reading the STEP file of the
     whole enclosure that `tools/assembly_step.py` built here (AP214, +Z up,
     479 solids, 19.8 MB). Peter starts the Windows agent.
   - `vault-cad-tools` no longer reads the earlier layout: `import-step`,
     the schema 1 lock and publishing from `step/` are removed with their
     tests (102 pass). Peter committed and pushed it the same day (e85c85e,
     with the enclosure's 8d15145 and d9dd527 here); the tests and `status`
     on the enclosure were run again on the pushed commits and give the same.
   - Peter ran `make open` in the enclosure's main checkout after the merge:
     the whole enclosure builds and opens.
   - Windows ran the first task that evening and stopped in it, as the
     task says it must (shared evidence `2026-11-12-windows-new-layout-01`,
     40 files checked against their checksums here). Passed: the 115 Python
     tests and ten PowerShell suites, `status` equal to the baseline, and a
     repeat import that leaves all 44 directories untouched. Failed:
     `validate`, with one error, because Git for Windows had written CRLF
     into `build.py` of the enclosure's authored part, whose hash the
     receipt records. Nothing of the scripts and nothing in Inventor was
     started. The fault is in the repositories, not on Windows: the
     enclosure's `.gitattributes` gave LF to three file types only, and this
     repository had none, so its fixture gave 16 errors there (STEP files
     are text to Git).
   - Corrected on 2026-11-13, uncommitted until Peter commits: `* text=auto
     eol=lf` in the enclosure and a `.gitattributes` here with the same and
     the STEP lines. No tracked file changes on Linux. Reproduced in scratch
     clones with `core.autocrlf=true`: 29 files of the enclosure and 70 here
     come out with CRLF and `validate` fails as on Windows; with the change,
     none and both validate. An existing checkout is put right with `git rm
     --cached -r -q .` and `git reset --hard` (tried: a fast-forward alone
     leaves 28 of the 29). The validator now says first when files differ
     from their records only in line endings, and that nothing is to be
     built or measured again; docs/layout-specification.md has a section
     "Line endings" with the lines a project needs. `vault-cad-tools` and
     `mechanical-docs` have attributes of their own and were left alone:
     nothing there hashes a file that Git converts.
   - The reply to Windows and its next prompt are written
     (`to-windows/20261113T144207Z-...`): the checkout first if the change has
     reached the shared clones, then Inventor reading the STEP file built
     here, then the scripts. Peter committed the correction (a18ad6a here,
     d4e5ef3 in the enclosure) and the shared clones were brought level on
     2026-11-13.
   - Windows delivered all of it on 2026-11-13 (shared evidence
     `2026-11-13-windows-new-layout-02`, 178 files checked against their
     checksums here; the review is `2026-11-13-linux-windows-new-layout-02-
     review-01/REVIEW.md`):
     - The checkout is right on Windows once every tracked file is written
       again: no file stored with LF and written with CRLF, and `validate`,
       `assemblies`, the fixture, `status` and the tests give what Linux
       gets. `mechanical_cad` has now run on Windows.
     - **Inventor 2025 opens the STEP file of the whole enclosure that
       `tools/assembly_step.py` built**: an assembly in mm, in 47 s, the
       translator says `Successful`, no dialog. 155 part occurrences, 479
       solid bodies, 37 part documents. All 171 occurrences are where the
       package's `occurrences.json` puts them, within 7e-10 mm, the 44 that
       a flexible instance places differently among them. The volume is
       FreeCAD's within 6e-5. Inventor also writes it out as native
       documents (18 `.iam`, 37 `.ipt`, 74 s). No colour, constraint or
       feature arrives, as the tool says.
     - What an Inventor user saw that was ours to correct: the occurrences
       were named with numbers, because Inventor shows the id of a usage and
       OpenCASCADE writes a running number there; and 47 of the 171 names
       were numbered anew by FreeCAD, which keeps the labels of a document
       distinct. Both corrected here on 2026-11-13 (`stepfile.name_usages`,
       used by `tools/assembly_step.py`; the build report is schema 3, so
       built files are built again): every usage has its occurrence's name
       as name and as id, and the 47 are the occurrences' own. On the
       enclosure: 172 usages, no id twice under one parent, and the file is
       the earlier one in every other byte. Inventor has not read it yet;
       that is the next Windows task (`to-windows/20261113T165633Z-...`).
     - Inventor made 18 assembly documents where the native design has 7
       files, because the file had one product per sub-assembly instance.
       Changed on 2026-11-13 at Peter's word (open decision 12): instances
       that hold the same parts in the same places are one container in the
       FreeCAD document and links to it, so one product in the file, named
       after the assembly's file (`stepfile.name_products`); an instance that
       differs keeps a product of its own. The build report is schema 4. On
       the enclosure all 16 sub-assembly instances are of 6 kinds, one per
       native file: 45 products where there were 55, 126 usages where there
       were 172, and all 479 solids read back where the scene puts them.
       Peter opened the document that day and found that hiding one panel
       assembly hid all four: in FreeCAD what is hidden inside a container
       is hidden in every link to it. So the sharing is in the STEP file
       only (report schema 5): the tool builds two documents from the part
       files read once, one with shared containers, from which the STEP file
       is written, and one with a container for every instance, which is
       kept. The STEP file is the same bytes as before that change. Not
       seen: the window with the document as it is now (no window can be
       opened from the agent's shell).
     - **Inventor read the file with shared products on 2026-11-13** (shared
       evidence `2026-11-13-windows-shared-products-01`, 146 files checked
       here on 2026-11-16, and the comparison made again here from the two
       receipts): it makes one document of each product and places it once
       for every usage. 45 documents in memory where the earlier file gave
       55: 37 parts and 8 assemblies, which are the root, the added level
       and the six sub-assemblies under their files' names (three of them
       with four occurrences each, one with two, two with one). The
       172 occurrences are those of the earlier read, in the same order,
       with no placement and no part volume differing; all 171 paths below
       the added level are the package's, and the 90 occurrences in or below
       a shared document are where the package puts them within 4.5e-10 mm.
       `Successful` in 44 s, no dialog. Written out as native documents it
       gives 8 `.iam` and 37 `.ipt` where it gave 18 and 37. The root
       document is named after the STEP file; the root product's name shows
       nowhere in Inventor. Not done there: the native documents written
       were not opened again.
     - Windows read the file with the names on 2026-11-13 (shared evidence
       `2026-11-13-windows-step-names-01`, 144 files checked): none of
       Inventor's 172 occurrence names is a number, it changed none, and all
       171 paths below the added level are paths of the package's
       `occurrences.json`; placements and volumes as in the read before.
     - Volumes, settled between the two sides on 2026-11-13. Inventor
       cannot compute one body of `MCMASTER 5537T429` at its finer
       accuracies and then leaves it out of the document's volume without
       saying so; its default accuracy has all eleven and agrees with
       `facts.json`. The package's `native.volume_mm3` is the native
       document's volume at whatever accuracy the document has, and is short
       for two parts of the enclosure for that reason (docs/exporter-
       package.md says so now). **And `facts.json` is 0.8 % low for one
       part, the spring `MCMASTER 9293K121`**: FreeCAD's `Volume` is
       OpenCASCADE's plain integration, 18 270.7 mm3, where its adaptive
       integration gives 18 422.2 (through `python-ocp`), a fine mesh 18
       420.3, Inventor 18 418 to 18 426 and the native document 18 422.5.
       For the two framing parts the two integrations agree within 1e-5.
       Changed the same day at Peter's word: what is recorded of a shape is
       measured with the adaptive integration (below).
     - The measure, since 2026-11-13. `tools/kernel.py` `measure` hands the
       shape FreeCAD read to the OCP bindings as BREP and integrates volume,
       area and centre of mass adaptively (relative tolerance 1e-7);
       FreeCAD's interface has no such option. `facts.json` and a receipt
       name it in `tool.integration`, a note says when a solid did not reach
       the tolerance, the validator points out facts measured the plain
       way, and `step_facts.py` measures those again. So `step_facts.py`,
       `build_part.py` and `compare_step_exports.py` need the environment
       of `.guix/manifest-build123d.scm`; without the bindings they say so
       and write nothing. `assembly_step.py` and `compare_assembly_step.py`
       compare what one run reads with what it reads back, keep FreeCAD's
       plain integration and need FreeCAD alone, so `make open` is as it
       was. The enclosure's 38 parts were measured again in 40 s: the
       spring's volume is 18 422.2 mm3 (+0.83 %) and its centre of mass 4.0
       mm from where it was recorded; no other volume changes by more than
       5e-5; counts, boxes and validity are the same for all 38. One part,
       the toggle clamp, carries the note (2.3e-5 reached). The enclosure
       validates as before, and its built assembly is still current.
     - One part's volume differs in Inventor by 11 % between its two
       accuracies (`MCMASTER 5537T429`, 11 bodies). `facts.json` is right
       about the file: a fine mesh of each solid gives the B-rep volume (29
       035 against 29 037 mm3), and the solid with a void is the difference
       of its two shells. Inventor's lower number is short by the volume of
       one body. Nothing changes in the project.
     - The Windows patch (the six remarks on the exporter, each with an
       offline case; a new probe that reads a STEP file in Inventor) is
       applied in `vault-cad-tools`, with its README and plan.
       Windows listed eight scripts that served only the earlier formats,
       and Peter had them removed that day. Its last patch of that day (the
       suites after the removal, a `Dirty` flag that is nothing stopping the
       exporter) is applied there too, on 2026-11-16; the Windows agent has
       no assignment.
   A full-quality render of the manual waits for Peter's corrected
   instructions.
5. The first new part for the enclosure written as code, built and checked
   here, manufactured, then published to Vault.
   Begun on 2026-11-16 with a reference model of the enclosure's monitor,
   which Peter named as the part to try: the first authored part that is not
   a box (two lofts, an extrusion, a pocket, pads, holes; 59 faces), written
   with build123d and built with `tools/build_part.py`. What it showed of the
   tools:
   - **A picture is needed, and one can be had without a window.** The first
     build passed its four checks and was wrong: a loft through rounded
     rectangles had paired their corners one edge apart and the surface was
     twisted. Only a picture showed it. `f3d` 3.0.0 of Guix, built with
     OpenCASCADE, renders a STEP file to a PNG with `--rendering-backend=egl`
     and no display; an agent can read that image. On this workstation it
     writes the image and then ends with `free(): invalid pointer` (exit
     134). Not built: a command of this repository that makes the pictures.
   - **The checks cannot state an interface.** A check names a fact of the
     whole part. That four holes are where a mounting pattern has them, and
     that a face is at a given depth, was checked by hand on the file read
     back: the cylindrical faces listed, and sixteen points asked whether
     they are material or empty. Proposed for the layout: a check that names
     a point and says "material" or "empty", evaluated by the build command
     and recorded with the facts, so the validator needs no kernel. It would
     serve fit between parts as well. Not built, and Peter has not been
     asked.
   - **The plain volume integration is wrong again**, by 0.9 % on this model
     (build123d's own `volume`). The adaptive integration that `facts.json`
     records agrees with a fine mesh within 0.04 %.
   - Writing it took the outline drawing and no other information. Numbers
     read off the drawing's pictures are kept apart from printed ones in
     `parameters.json` and are to be measured on the monitor.
   Peter on 2026-11-16, after the model: the two monitors are to lie
   face-up, screens horizontal, under the fish tanks, as displays and
   backlights; McMaster sells monitor arms with STEP files; could one be
   aligned with the monitor's mounting holes as a sub-assembly and placed in
   the enclosure to see whether it fits, and are tools missing for that.
   Answered and built that day:
   - **Nothing has to be packaged for it.** The kernel in the channel finds
     holes in a STEP file, places shapes, and measures common volume and
     distance; build123d has joints (rigid, revolute and others) for
     attaching one pattern to another and for posing an arm; the layout
     already has authored assemblies that place mirrored and authored
     components. FreeCAD of Guix has its Assembly workbench for doing the
     same by hand (the module is there; not tried). CadQuery would add a
     constraint solver for assemblies, which this does not need.
   - **`tools/fit_check.py`** (FreeCAD alone, three tests): for an assembly
     and the names of some of its children, every solid of those against
     every other solid: interference by common volume, contact, and what is
     closer than a clearance. Tried on a scratch copy of the enclosure with
     an authored assembly that places the mirrored root and two monitor
     models face-up, side by side, 5 mm under the lower tank's platform: the
     project validates, 2 solids against 479 in 17 s, nothing interferes,
     and the three distances it reports are the ones the placement gives. A
     second authored assembly of the lower tank support frame and the two
     monitors was built with `assembly_step.py` and drawn with `f3d`. That
     position is a guess; Peter has not said where the monitors sit.
   - The enclosure's frame is 1193.8 mm square outside and 1117.6 mm clear
     between its posts and rails, which are 38.1 mm square. Two monitors
     with their long edges side by side need about 610 by 712 mm; end to end
     they need 1219 mm and do not fit.
   Not built: bringing a supplier's STEP file into a project (the layout has
   mirrored and authored components and no third kind; whether supplier
   models may be public is open decision 6, so a study stays in the
   project's ignored `.cache/` until an arm is chosen); finding matching
   hole patterns in two parts and writing the placement that aligns them;
   posing an arm about its joints, which a STEP file does not describe.
   Asked of Peter: the arms' STEP files in one directory, a drawing or
   catalogue page for each with its tilt and swivel ranges, where the
   monitors sit and what an arm bolts to.
   Peter saved the STEP files of two arms that day and the study was made
   (the enclosure's plan, next work 6, has the results; its ignored
   `tmp/monitor-mounts/study-2026-11-16/` the pictures, files and scripts).
   What it showed of the tools, with build123d alone and three scripts of
   about a hundred lines each:
   - A supplier's file is read as it is: its solids, the two flat plates by
     their sizes, the holes of a pattern by radius and spacing, the joints by
     the cylinders and spheres around their axes. Neither file has a tree or
     names, so which solids turn with a joint was decided by looking at
     their boxes; that is the part an agent cannot take from the file.
   - The mate is a placement worked out from the two patterns, and checked
     by pairing the holes (0 mm) and by asking the kernel what touches.
   - Turning a joint is a placement of some solids about an axis. The files
     overlap themselves slightly at a joint turned by a right angle, which
     says something about the joint's range and is worth reporting.
   - Placing two sub-assemblies in the enclosure and checking them against
     its 479 solids took a minute, most of it reading the 20 MB file.
   To make of this what can be kept in a project: a place in the layout for
   a supplier's file (open decision 6 bears on it), and the three scripts as
   one tool that writes an authored assembly. Not begun.
   Peter on 2026-11-16, later: he prefers the arm 5537T879 and holds the
   mount until he has spoken with the researcher; the other steps of the
   plan go on. Built that day, which closes what the monitor showed missing:
   - **Checks that name a point** (`mechanical_cad/facts.py`,
     `tools/kernel.py` `at_points`, the build command, the validator, the
     specification; ten tests): `{"point": [x, y, z], "is": "material" |
     "empty"}`. The build asks the kernel what the file read back has at
     each point and records it in `facts.json`; the checks are then read
     without a kernel; a point on a surface satisfies neither; a point added
     after the build fails until the part is built again. The monitor's
     mount is stated so, in fourteen points, and its build fails when one is
     wrong.
   - **`tools/picture.py`** with `.guix/manifest-view.scm` and `make picture
     PROJECT=DIR KEY=K [VIEWS=...] [UP=...]`: a part from its `part.step`,
     an assembly from its built file, into the project's ignored
     `.cache/pictures/`, through `f3d` and EGL in a pure Guix environment.
     Three tests; `make test-view` runs them with the viewer. f3d ends with
     a fault after it has written each image on this workstation; the tool
     counts the image and says so.
   - **Short commands and a guide** (the same day): `make part KEY=K`,
     `make check` and `make fit KEY=K SUBJECT='NAME[,NAME]'` here and handed
     on by the enclosure's Makefile, beside `make picture`; and
     docs/adding-a-part.md, which walks a person or an agent through adding
     a part, programmed or drawn: source, checks, build, pictures, placing
     it, fit. Tried through `make` on the enclosure and the fixture. No test
     runs `make`.
   Next for this item, when Peter takes the mount up again: a place for a
   supplier's file (open decision 6), his measurements of the monitor, the
   arm's tilt range and rating. A part that is made, and measured against
   its STEP, is still to come (goal 9).
6. The Guix channel and the packages for writing parts as programs. Peter
   recorded this packaging as his own deferred work on 2026-10-23 and took it
   up on 2026-11-13: build123d first, the channel and the OCP package to go
   ahead, and CadQuery possibly later, once build123d works, to give agents
   and people more options. Built that day with Guix 64d4de2, all in
   `.guix/modules/orb-weaver/mechanical-cad/packages.scm` (`.guix-channel`
   points at `.guix/modules`, as `orb-weaver-context` does):
   - `python-ocp` 7.9.3.1, the release for Guix's OpenCASCADE 7.9.3, from the
     release's `OCP_src_stubs_Linux.zip` (the bindings as upstream's pywrap
     generated them, 639 `.cpp`, and the type stubs). It compiles in 22
     minutes on 16 cores and its check passes: a box, its volume, a STEP file
     written and read back. The generated sources fit Guix's OpenCASCADE as
     they are. Beyond the release's build file it needed MPI found before VTK
     (Guix's VTK is built with MPI), the libraries VTK's CMake files look
     for, and rapidjson for OpenCASCADE's glTF headers. Built with VTK, as
     Guix's OpenCASCADE is, so the one package serves CadQuery too. The
     module is 148 MB.
   - `python-build123d` 0.12.0, the last release for OpenCASCADE 7.9. In the
     build 2436 of its tests pass and 10 are deselected: nine whose set-up
     downloads a model, one that wants lib3mf 2.3.1. Changed against
     upstream, each with its reason in the file: the names and bounds of four
     requirements, `Sentinel` of typing_extensions 4.15 where 4.16 has
     `sentinel`, and the font and script it ships named as package data.
   - Nine packages build123d needs and Guix lacks: `python-ocpsvg` 0.6.0 (232
     tests pass) and `python-ocp-gordon` 0.2.2 (97), both the last for OCP
     7.9; `python-svgpathtools` 1.8.0; `python-trianglesolver` 1.2;
     `python-bd-materials` 0.2.6 (786); `python-threejs-materials` 1.2.5
     (294; one file left out, it needs MaterialX); `python-pygltflib` 1.16.5
     and `python-dataclasses-json` 0.6.7 (tests not run); `python-lib3mf`,
     the binding generated with Guix's lib3mf 2.2.0, laid out as PyPI's
     package is, with one name Python 3 refuses corrected as later releases
     have it.
   - Here: `tools/build_part.py` takes a build123d shape as well as a
     `Part.Shape` (`kernel.as_shape` hands it to FreeCAD as BREP; FreeCAD
     still writes and measures, and the receipt's `tool.library` names
     build123d and the bindings). A test builds the fixture's spacer from a
     build123d program: the same volume and box as FreeCAD's, the project
     validates, a second build changes no file. `.guix/manifest-
     build123d.scm` and `make test-build123d` give the environment. 153
     tests pass there, 152 with FreeCAD alone, 143 without it.
   What was found on the way, 2026-11-13 (the web pages were read by a
   second agent):
   - Guix has no OCP, CadQuery, build123d or pythonocc, and no patch or
     channel for them was found. Peter's Guix checkout `~/guix` (master,
     built; cff8eaaf48c of 2026-11-13) has the same OpenCASCADE 7.9.3 and the
     same typing_extensions 4.15.0 and lib3mf 2.2.0.
   - The newest releases that fit OpenCASCADE 7.9 are these and CadQuery
     2.8.0. build123d 0.13.0 and OCP 8.0.x need OpenCASCADE 8.0. They move
     together when Guix moves its OpenCASCADE.
   - Open Cascade SAS opened an issue on OCP's licence compliance on
     2026-11-12 (the kernel's headers and comments copied into generated
     sources). To watch before anything is submitted to Guix.
   - On this workstation the first build that has the daemon download a new
     source ends with a permission error after the download; the same
     command again goes on (`.agents/handoff.local.md`).
   Not done, and needed before these can go to Guix itself:
   - The bindings generated in the build, from OCP's repository and the
     headers of `opencascade-occt`, with pywrap and libclang 20 or 21. Guix
     has those compilers but defines the Python bindings of clang for
     version 13 only (`clang-python-bindings`). Debian and Arch do this and
     both report trouble with the clang version.
   - lib3mf 2.4.1 in Guix, which build123d asks for; `python-anytree` in
     Guix gives its version as 0.0.0; the tests of `python-dataclasses-json`
     and `python-pygltflib`.
   - The inputs of `python-ocp` pruned to what the build uses (`glew`,
     `libx11` and `zlib` were added with `freetype` and `mesa` and not tried
     without), and a build type without debugging symbols.
   The first part of a project written with build123d is the enclosure's
   monitor envelope, rewritten on 2026-11-13 at Peter's word and built with
   `tools/build_part.py`: every measured fact is the same to the last digit
   as from FreeCAD's `Part` module, its four checks pass, and `part.step`
   differs in 14 of 187 lines, each only in the sign of a zero. The project
   validates as before.
   Next, in order: a part that is not a box (item 5); then, if wanted,
   CadQuery 2.8.0 (it needs `casadi` and `runtype`, which Guix lacks, a newer
   `multimethod`, and VTK's Python modules), and a kernel module on OCP that
   measures and writes without FreeCADCmd.

   Which library, packaging aside (Peter asked on 2026-11-13; build123d's
   source was read at v0.12.0 and CadQuery's documentation, change log and
   `setup.py` at master, by a second agent, before either was built here).
   Peter decided on 2026-11-13: build123d first. What weighed:
   - Both wrap the same OCP shape, so a tool that takes the wrapped
     `TopoDS_Shape` serves both, and a part written in one converts to the
     other in a line. The choice is a convention for `build.py`, not a
     format.
   - For build123d: shapes are plain Python values with no hidden state, so
     `build(parameters)` returns one and every intermediate can be measured;
     selection is Python (`filter_by`, `sort_by`, `group_by`) instead of
     CadQuery's selector strings; `export_step` writes labels, colours and
     the tree, sets no author or organisation, and takes a `timestamp`;
     SVG and DXF export, and (from memory, not read that day) projection and
     dimension lines, for the manual.
   - For CadQuery: a stable interface, with no breaking change listed in its
     releases 2.6.0 to 2.8.0 (build123d is 0.x and renames things between
     releases, which also makes an agent's memory of it less reliable;
     mitigated by a pinned version and by running every build); more public
     code and, from memory, most published work on language models writing
     CAD; a constraint solver for assemblies and sketches; more STEP metadata
     (layers, materials since 2.7.0, names of sub-shapes since 2.8.0); OCP is
     maintained in CadQuery's organisation. Its free-function interface (no
     hidden state, no longer experimental in 2.8.0) answers the main
     objection to its fluent one, but most of its examples are fluent.
   - Not deciding here: the layout owns assemblies (`assembly.json`,
     placements), so neither library's assembly model is in the contract.
     build123d's `import_step` rewrites spaces, dots and parentheses in names
     to underscores; a kernel tool on OCP should read names itself.

7. The plan of 2026-11-17 (docs/direction.md; open decision 17). Nothing of
   it is built. What was read and tried that day, all in scratch
   directories and in no repository:
   - a truncated octahedron from its vertices as solid, shell, frame and
     flat pattern, and the size that holds a box (docs/direction.md,
     "Proposed: a library of enclosure shapes");
   - FreeCAD's polyhedra add-on on Peter's workstation, read and run
     without a window: five of its thirteen Archimedean presets exact, six
     close, two not the solid they name;
   - solids read from STEP files subtracted, intersected and merged with
     build123d, the volumes agreeing to 2e-6 mm3 when measured with the
     kernel's fine integration (the plain `volume` of a solid with spline
     faces is 0.9 % off, as found before); moved, turned and mirrored
     exactly; scaled evenly with planes and cylinders kept; scaled unevenly
     with every face made a spline;
   - the example board's assembled STEP file: read in six seconds, 703
     solids in 361 components, 16.6 mm above the board and 2.4 mm below it,
     in KiCad's page frame with y reversed, components named after
     footprints.
   Where to begin: stage 1.1 and 1.2, once Peter has said where a supplied
   file lives. Stage 3.1 (`bd_warehouse` in the channel) waits on nothing.

   **Built on 2026-11-17, after he said it** (he was away for some hours
   and asked what could be done without him; uncommitted when this was
   written):
   - Stage 1: `mechanical_cad/supplied.py` and `add-supplied` (a supplied
     part is `part.step`, the file as it came with its header normalised,
     and `origin.json`; no second copy of the file, which the plan had
     first written); `interface.json` (`mechanical_cad/interfaces.py`:
     holes, planes, outlines, ports, volumes to keep clear, points, axes,
     named frames; a hole is held to the solid as a point check); inputs
     (`"inputs"` in `parameters.json`, `build(parameters, inputs)`,
     `kernel.Input`, the receipt's `inputs`, a part reported stale when an
     input's STEP file or interface has changed, `build-order`). The facts
     command measures supplied parts and looks at the points their
     interfaces name. A supplied part whose geometry the kernel does not
     find valid is a finding, not an error. The validator, the
     specification and the guide to adding a part say all of it.
   - Stage 2.1 and 2.2: `tools/board_interface.py`, run on the example
     board in a scratch project (the numbers are in docs/direction.md,
     "Built so far").
   - Stage 3.1: `python-bd-warehouse` 0.4.0 in the channel, by a second
     agent; reviewed here.
   - Stage 3.3 and 4.1, a first cut: `mechanical_cad/enclosures.py`, a plain
     box (base and lid) from a board's interface; the example board boxed
     in the scratch project, no interference.
   - Stage 5.1, the first half: `tools/print_file.py`, `make print`,
     `.guix/manifest-print.scm` with PrusaSlicer; both halves of the box
     give closed meshes the slicer calls manifold. Not sliced.
   - Stage 8: `make view` (not tried in a window), and `make parts` and
     `make facts`.
   - Stage 3.2, the library of polyhedra (`mechanical_cad/shapes/`), given
     to a third agent with the trial as its start, and reviewed here: 18
     named solids, prisms, antiprisms, boxes; sizing to hold a box; unfold;
     solid, shell, frame, panels and flat pattern. What it found and what is
     left are in docs/direction.md, "Built so far". Its coordinates are
     from memory (no network), cross-checked by a second derivation.
   - A hazard it found, for every tool here that joins solids: the
     kernel's union of cylinders and balls that are tangent or nearly so
     can return one valid solid with volume missing. The library holds what
     the kernel returns to a volume worked out without it.
     `enclosures.py` joins cylinders to flat floors and walls and is tested
     by volume for the box only.
   - Tests: `tests/test_supplied.py` (29, no kernel), `test_enclosures.py`
     (3 without a kernel, 4 with build123d), `test_parts_from_outside.py`
     (5), `test_board_interface.py` (2), `test_print_file.py` (3 and 1),
     `test_bd_warehouse.py` (3), one more in `test_picture.py`, and the
     library's own `test_polyhedra.py` and `test_shape_forms.py`. All of the
     repository's tests on 2026-11-17: 467 pass without a kernel (67
     skipped), 534 with FreeCAD, the bindings, build123d and bd_warehouse (2
     skipped), 4 with the viewer.
   - The scratch project with the board and its box is under the session's
     scratch directory and in no repository. Making it a project needs
     Peter's word on where it lives.
   - The box takes a named screw and insert (`screw`, `insert`) and cuts
     the holes of `bd_warehouse`'s tables; an insert that the standoff and
     floor are too short for is refused. The halves meet in a step.
   - Stage 4.2, a first cut: `enclosures.halves` and `polyhedron_halves`;
     the board in a truncated octahedron in the kept project (large: 149 mm
     high for a board of 100 x 80 mm).
   - Added later that day to `enclosures.py`: windows through a wall for
     ports that face sideways or down (`_opening`, cut from both halves);
     the lip in `halves` for any outer solid and cavity, upright from the
     cavity's outline at the board's top face, refused where the walls
     lean in too much; `prism_size` and `prism_halves`. The example board
     in a hexagonal prism in the kept project (`prism-base`, `prism-lid`,
     `board-in-prism`); the octahedron's halves rebuilt with the lip. A
     typed-in insert hole in `halves` now stops 0.6 mm short of the
     outside, as the box's does. Tests on 2026-11-17 after it: 468 without
     a kernel (70 skipped), 538 with it (2 skipped).
   - Next here: a polygon with unequal sides that follows a rectangle;
     vents and feet; slicing with a printer's profile once Peter names the
     printer; the part measured after printing.
   **The Windows reads of 2026-11-17** (W3, the rehearsal, a discovery of
   the second project's folder; reviewed here, 57 checks against the raw
   answers; the review is on the share under
   `evidence/2026-11-17-linux-windows-vault-reads-02-review-01/`): nothing
   written, nothing downloaded. The results are in docs/direction.md,
   "Built so far", and in `vault-cad-tools` (`windows/HISTORY.md`,
   `.agents/PLANS.md`); the ids and the folder are in the ignored
   `.agents/handoff.local.md`.

   **Asked of Windows later that day**, for Peter to start, nothing
   written to Vault (the message is on the share,
   `coordination/to-windows/20261117T191339Z-...`): the two script changes
   agreed with it; the definitions of the two properties the server fills
   in; the mirror of the second project for testing, by the version id of
   the one assembly, acquired and exported, in a directory of its own
   under `mirrors/` on the share; and W1 up to the point where it would write. When it
   reports: check the evidence, import the package into a scratch project
   outside every repository (the paths in it name a lab), and put to Peter
   exactly what the live run of W1 adds to the test folder.

   **Delivered on 2026-11-17 and reviewed on 2026-11-18** (66 checks on
   Linux, none failed; the review is on the share under
   `evidence/2026-11-18-linux-windows-mirror-and-reference-route-01-review-01/`).
   Nothing was written to Vault. The results are in docs/direction.md,
   "Built so far". For this repository:
   - There is no package to import: the exporter stopped at a sub-assembly
     used in two model states. What the package holds for that is decided
     in docs/exporter-package.md, "Model states and suppressed
     occurrences"; the layout and the import needed no change (a key
     `<key>@<state>`; a test in `vault-cad-tools`). The exporter is changed
     on Windows, in the next task. One part of that project has no body;
     no rule for it yet.
   - Peter is told what the live run of W1 adds: two files. His word waits
     for two checks Windows proposed (a rehearsal of the live branch, and
     one read of what Inventor's add-in writes into an association).
   - The next Windows task is on the share
     (`coordination/to-windows/20261118T140617Z-...`). Its first step stops
     unless the shared clones hold the Windows patch and the decision on
     model states. Peter pushed both on 2026-11-18; the shared clones are
     brought level when he says so, and then he starts the agent. The
     Windows machine was off on 2026-11-18.

   In Guix that day: KiCad 10.0.5, PrusaSlicer 2.9.5, `python-ezdxf`,
   `python-trimesh`, lib3mf; not `bd_warehouse`. The packaged build123d
   0.12.0 has the exporters for STL, 3MF, DXF and SVG.

---

## The plan as first written, 2026-11-10 (morning)

Written by the session that ran in `mechanical-docs` as a handoff to the first
agent started here, before any code existed. Moved here unchanged.

## Objective

Give Peter's Inventor and Vault projects an open representation in Git and the
open-source tools to check it, document it and add to it, with the
free-standing tank enclosure as the test project. The full statement is
docs/direction.md.

## Current checkpoint — 2026-11-10 (repository started, direction and layout proposed)

Written by the agent session that ran in `mechanical-docs` on 2026-11-10, as a
handoff to the first agent started here. Nothing is implemented. Peter committed
the licence here (`1a9235f`) and in `mechanical-docs` (`1772669`) during that
session; the rest is uncommitted.

- [x] Licence file, README, agent guidance, base Guix manifest
  (`python`, `python-pytest`, `git`; observed to resolve: Python 3.12.12,
  pytest 9.0.2).
- [x] docs/direction.md: goal, the six-stage loop, decisions with dates,
  repository roles, proposed layout and order of work, out of scope.
- [x] docs/layout-proposal.md: the proposed layout, what was measured on the
  enclosure, what is unverified, the acceptance test, the Windows tests.
- [ ] Peter's acceptance of the direction document (drafted from his
  statements; he has not said "accepted").
- [ ] Peter's answers to the three open layout choices (below).

## What Peter decided on 2026-11-10

- Licence: 3-clause BSD, copyright HHMI, in all four repositories.
- Hosting: GitHub. The Codeberg repositories will move there; where is not
  settled.
- This repository holds the tools and doubles as the Guix channel.
- Cross-repository work runs from an agent session rooted here.
- He wants the proper structure for STEP files and metadata worked out, then
  the enclosure re-imported from Vault into it. He is willing to move the
  current enclosure files to a branch.
- While agents work, he assembles the enclosure from the published manual and
  takes notes on the documentation. Afterwards agents design new parts for the
  enclosure with the tools packaged here; he manufactures and checks them; then
  `vault-cad-tools` places them in Vault.

Not decided, although recommended to him: that the direction lives here rather
than in `orb-weaver-context` (he answered by choosing to start the agent here);
the layout itself.

## Open decisions to put to Peter

1. Two roots (`references/`, `designs/`) or one tree with an authority field.
   Recommended: two roots.
2. Readable directory keys tied to the Vault master id, or a mirror of Vault's
   folder tree. Recommended: readable keys.
3. AP214 or AP242, after the Windows test.
4. Whether supplier-originated models may stay in a public repository, and the
   wording of the enclosure README's scope statement (an agent's draft).
5. Whether account, host and server names stay in public files.

## Next work, in order

1. Get Peter's answers to decisions 1 and 2 and his acceptance of the direction.
2. Write the layout as a specification with a standard-library validator and a
   small synthetic fixture, here. Add the flatten step that produces the
   `scene.json` shape `mechanical-docs` reads (`mechanical-docs/docs/input-contract.md`).
3. Write the converter from the enclosure's existing snapshot to the layout and
   run it on a branch of the enclosure. Pass the acceptance test in
   docs/layout-proposal.md. `main` of the enclosure stays untouched until then.
4. Replace the Windows agent's queued work with one message asking for the four
   read-only tests in docs/layout-proposal.md, and rewrite the operator prompt.
5. Have the Windows exporter write the layout; re-export; compare with step 3.
6. Geometry facts, build and check commands; move the enclosure's monitor
   envelope to the new shape as the first authored part.
7. Channel skeleton (`.guix-channel` pointing at `.guix/modules`, as
   `orb-weaver-context` does), then OCP against Guix's `opencascade-occt`,
   build123d, CadQuery. Peter recorded this packaging as his own deferred work
   on 2026-10-23; confirm before starting it.

## Hazards

- **The Windows operator prompt points at superseded work.** In the shared
  directory, `coordination/PROMPT-WINDOWS.txt` still sends the Windows agent to
  two unread messages of 2026-10-23 (`151357Z`, `153207Z`): a `metadata.json`
  sample and an incremental export dry run, both on the old layout. Folder
  discovery in the first message is unaffected. Rewrite the prompt before Peter
  starts that agent.
- **The shared coordination plan is stale.** `coordination/PLAN.md` and
  `NEXT-AGENT.md` describe 2026-10-23. Where they differ from
  docs/direction.md, the direction wins; update them as the Linux role.
- **The enclosure's `main` feeds the published manual.** Its Pages workflow
  builds on every push to `main`, and Peter is assembling from that manual.
- **Remotes.** `origin` here still points at Codeberg; the GitHub remote is
  `peterpolidoro`. Remotes are Peter's to change.
- **The handoff files in the sibling repositories were written on 2026-10-22/23**
  and name commits and patches that are long since committed. Each now starts
  with a 2026-11-10 note; trust that note and the tracked plans over the rest.

## State of the four repositories when this was written

| Repository | HEAD | Uncommitted |
| --- | --- | --- |
| `mechanical-cad` | `1a9235f` (licence only) | README, guidance, plan, manifest, ignore rules, `docs/` |
| `mechanical-docs` | `1772669` (licence, first plan update) | README, guidance, plan, `docs/next-agent.md` |
| `vault-cad-tools` | `7807e8f` | licence, README, guidance, plan |
| `free-standing-tank-enclosure` | `0eeb1af` | licence, README, guidance, plan |

The shared clones matched `7807e8f` and `0eeb1af`. No tests were run in any
repository on 2026-11-10: every change is documentation or licence text.

## Not run, not known

- No code exists here, so nothing was tested beyond the manifest resolving.
- The measurements in docs/layout-proposal.md were made on Linux from tracked
  files; none involved Vault, Inventor or the Windows machine.
- The claim in the external discussion that the package names are free on PyPI
  was not checked.
