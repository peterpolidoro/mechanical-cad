# mechanical-cad living plan

## Objective

Give Peter's Inventor and Vault projects an open representation in Git and the
open-source tools to check it, document it and add to it, with the
free-standing tank enclosure as the test project. The full statement is
docs/direction.md. Finished checkpoints are in .agents/HISTORY.md.

## Current state (2026-11-13)

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
- Tests: 143 pass in the base role, 152 with FreeCAD and 153 with FreeCAD and
  build123d (run 2026-11-13, after the usage names, the shared sub-assembly
  products and the build123d path of `build_part.py`; Python 3.12.12, pytest
  9.0.2, FreeCAD 1.1.3, OpenCASCADE 7.9.3).

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

1. The exporter's package, docs/exporter-package.md (draft 3). Its choices:
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
5. Names in public files. Before the re-export: all 37 STEP headers carried
   an account-like author name (four people, none of them Peter); the
   exporter's records and the lock carried Peter's Windows account in
   absolute paths and a host name. Counted on the enclosure's `main` after
   the re-export (8d15145, 347 tracked files, 2026-11-12): no STEP file of
   the 38 has an author or an organisation in its header, and the 44
   directories and the index hold no account, host or workstation path.
   What is left in the tree: the earlier snapshot's records, kept byte for
   byte under `references/receipts/legacy-snapshot-991056/` (four files with
   the account in absolute paths, one of them with the host name); the
   published `docs/manual/manual.json` (the account in paths) and
   `docs/manual/SOURCE.json` (the share path); the server name in
   `vault-project.toml` and one more file of the enclosure and in seven
   tracked files of `vault-cad-tools`; none of these names in this
   repository or in `mechanical-docs`; and the Vault folder path with the
   lab's name in 116 tracked files of the enclosure
   (the 44 `source.json`, 63 files under `docs/manual/`, five receipts and
   four others). So the question is now about those receipts (keep, cut down
   or leave out), the published manual, the folder path, and history, which
   holds everything the earlier files did.
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
12. Settled by Peter on 2026-11-13: instances of a sub-assembly that are
    alike share one product in the STEP file of a whole assembly, if the
    Linux role recommends it. It did, and built it that day (item 4).
13. Settled by Peter on 2026-11-13: this repository is GPL-3.0-or-later
    (`LICENSE`, README, `.agents/AGENTS.md`), so the package definitions can
    be offered to Guix. He said "GPL-3.0"; "or later" is what Guix asks for
    and what was written. The other repositories stay 3-clause BSD.
14. Settled by Peter on 2026-11-13: the eight Windows scripts that served
    only the earlier export formats are removed, and with them the reading
    of the earlier package (`vault-cad-tools/.agents/PLANS.md`).

## Next work, in order

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
       Two things not seen: Inventor reading that file, and the FreeCAD
       window showing the document, whose repeated sub-assemblies are links
       now (no window can be opened from the agent's shell; `make open`).
     - One part's volume differs in Inventor by 11 % between its two
       accuracies (`MCMASTER 5537T429`, 11 bodies). `facts.json` is right
       about the file: a fine mesh of each solid gives the B-rep volume (29
       035 against 29 037 mm3), and the solid with a void is the difference
       of its two shells. Inventor's lower number is short by the volume of
       one body. Nothing changes in the project.
     - The Windows patch (the six remarks on the exporter, each with an
       offline case; a new probe that reads a STEP file in Inventor) is
       applied in `vault-cad-tools`, uncommitted, with its README and plan.
       Windows listed eight scripts that serve only the earlier formats;
       the list is in that plan for Peter, and nothing is removed.
   A full-quality render of the manual waits for Peter's corrected
   instructions.
5. The first new part for the enclosure written as code, built and checked
   here, manufactured, then published to Vault.
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
   Next, in order: a first real part written with build123d (item 5); then,
   if wanted, CadQuery 2.8.0 (it needs `casadi` and `runtype`, which Guix
   lacks, a newer `multimethod`, and VTK's Python modules), and a kernel
   module on OCP that measures and writes without FreeCADCmd.

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

## Known limits of what was built

- The validator has been run on two projects: the fixture and the converted
  enclosure. The tolerances for comparing geometry facts are provisional (one
  kernel version).
- `import-snapshot` reads the package `Export-Package.ps1` writes
  (`package.json`, `occurrences.json`, `files/`; draft 3), into a new
  directory or an existing project. The reading of the earlier exporter's
  package went on 2026-11-13 with that exporter (`vault-cad-tools`, at
  Peter's word). It
  refuses what the layout cannot record: suppressed or mirrored occurrences,
  an instance whose definition disagrees with another instance's, and nested
  flexible instances that would need an override on an outer level. One real
  package has been imported, from one root assembly.
- `build_part.py` takes a FreeCAD `Part.Shape` or a build123d shape, with one
  product. One part has been built from a build123d program, the fixture's
  spacer in a test; none in a project. There is no CadQuery path.
- The scene written by `flatten` copies every STEP file into its output
  directory, because the documentation loader resolves assets below the scene.
- A whole-assembly STEP file is for reading. FreeCAD's writer does not give
  back exactly what it read: over the enclosure's 102 solids the volume of a
  solid moves by up to 2.5e-4 of itself and its centre of mass by up to
  0.0018 mm (FreeCAD 1.1.3). It has no colour. The FreeCAD document beside
  it gets its view data written by this repository, not by FreeCAD: two
  properties per object and a camera, in the form FreeCAD 1.1.3 reads.
  Another FreeCAD version may read them differently; the document then opens
  with its objects hidden, as it did before, and nothing else is lost.
- On Windows `mechanical_cad/stepfile.py` has been run, read-only, to check
  the PowerShell port against it, and `validate` and `assemblies` once, on a
  checkout whose line endings Git had changed (2026-11-12) and on scratch
  clones without that fault, where both give what Linux gets. The flatten
  step, the tests and the tools under `tools/` have not been run there.

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
