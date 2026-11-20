# mechanical-cad living plan

## Objective

Give Peter's Inventor and Vault projects an open representation in Git and the
open-source tools to check it, document it and add to it, with the
free-standing tank enclosure as the test project. The full statement is
docs/direction.md. Finished checkpoints are in .agents/HISTORY.md.

## Start here (state of 2026-11-20)

This section is the short version. Where the work is going, what is decided
and what is built are in docs/direction.md ("Goals, and where each stands",
"Decided", "Plan: parts around other parts, enclosures for boards, pictures
and motion" with its "Built so far"). The record of how each piece came
about is in .agents/HISTORY.md. Paths on this machine,
ids, and the state of the shared clones are in the ignored
`.agents/handoff.local.md` and on the share in `coordination/NEXT-AGENT.md`
and `coordination/status/`. A session that begins after this one reads "For
the next session" at the end of that handoff file first.

**Where a new session begins.** On 2026-11-20 Peter's Windows laptop was
back and the share mounted: the Windows task of 2026-11-18 was run,
delivered and reviewed, and the next one is written ("Waiting for the
Windows agent" below). Before building more:

1. Read "Waiting for the Windows agent" below: three tasks were delivered
   and reviewed on 2026-11-20, and none is written now. The next one
   depends on what Peter says of the reference route ("Waiting for Peter").
2. After Peter's next push, bring the shared clones level on his word (the
   handoff file has the commands). The Windows working tree holds one
   patch until then, a line in `windows/HISTORY.md`.
3. Ask what Peter has decided of what waits for him below: the joints and
   poses draft (open decision 21) and what the finishes left open (20)
   come first, because work is built on them.
4. Otherwise take "Next on Linux" from 5, the smaller things that need no
   word, or whatever he asks for.

**Done and working**, each with tests (commands in docs/adding-a-part.md):

- The first project mirrored from Vault, validated and built; its manual
  is published as a draft.
- Parts as programs (build123d), drawn parts, supplied parts with
  `origin.json`, inputs and `interface.json`; a board's interface written
  from the board's repository (`tools/board_interface.py`).
- Enclosures for a board (`mechanical_cad/enclosures.py`): a box, any solid
  of `mechanical_cad/shapes/`, a prism on a regular polygon, and since
  2026-11-19 a prism that follows the board's rectangle (`octagon_halves`);
  standoffs, openings for ports through lid and walls, a lip between the
  halves, and since 2026-11-19 vents through any flat wall or a round
  corner of the box, in rows or staggered, and feet under the base, as
  bosses or as pockets for stick-on feet; fit checks. Shown on the example
  board in an ignored project of this checkout.
- Files to make a part from, each checked against the solid: a mesh to
  print (`tools/print_file.py`, with an absolute deflection since
  2026-11-18), a drawing to cut a plate from sheet (`tools/cut_file.py`,
  2026-11-18; with an allowance for the width of the cut, `--kerf`,
  2026-11-19), the flat pattern of a solid with flat faces, with its fold
  lines, closed or with faces left open (`tools/cut_file.py --pattern`,
  `--open`, 2026-11-19), and whether a part prints as it lies, by
  overhangs and by material that starts in mid-air
  (`tools/print_check.py`, 2026-11-18; a flat ceiling that a printer
  lays across is a bridge when `--bridge MM` says how far, 2026-11-19).
- Pictures without a window, of a part or an assembly, since 2026-11-18
  also cut open and with every part in a colour of its own
  (`tools/picture.py --cut +y --colour`).
- A section as a drawing to scale, every part in its colour
  (`tools/section.py`, 2026-11-18), with dimensions between named points
  of the model (`--measure`), hatching (`--hatch`), the edges seen behind
  the plane (`--behind`, `--behind --quick` for an assembly) and arcs as
  arcs (`--arcs`), all 2026-11-19.
- A project made of one STEP file of an assembly (`tools/take_apart.py`,
  stage 6, 2026-11-18): the mechanical example as a project in the ignored
  `tmp/dual-lever-from-step/`, 152 of 152 solids where its file has them.
  Since 2026-11-19 the file's colours become the project's finishes, for
  every part the colour most of its surface has; that project has them.
- The Makefile's short commands, looked at by tests that run none of them
  (`tests/test_makefile.py`, 2026-11-18).
- A project's finishes, the first record of stage 7.1 (2026-11-19, after
  Peter chose one file for the whole project over a file in each part's
  directory): a hand-edited `finishes.toml` at the top of a project names
  finishes and gives them to parts by key, and the validator holds it to
  the project (`mechanical_cad/finishes.py`). The flatten step writes what
  it says of a scene's parts as `finishes.json` beside `scene.json`, not
  into it, so that a changed colour changes no hash that stands for
  geometry. `tools/picture.py --finish` and `tools/section.py --finish`
  draw with it. The fixture has one; so has the first project, as a draft.
  `mechanical-docs` reads the derived file: its renderer draws a part in
  its finish unless the project's `render.json` names a look for it, and
  `mechanical_docs/still.py` draws a scene alone from a named side, the
  first item of stage 7.2 (that repository's plan has the state).
- Moving pictures, stage 7.2 (2026-11-19, in `mechanical-docs`): a
  turntable, the subassemblies moving apart and back, and a project's
  steps in the manual's order, each as video. Four videos of the first
  project are in its ignored `.cache/pictures/`. A joint through its
  range is drawn too, against the draft below.
- Outlines on whole assemblies (2026-11-19, in `mechanical-docs`): Line
  Art behind a setting that is off unless a project switches it on.
- A STEP file published to Vault and verified, twice (`vault-cad-tools`).

**Built as a draft, outside the layout, for Peter to decide** (2026-11-19;
open decision 21): joints and poses. A project's hand-edited `motion.toml`
says which children of an assembly turn about a line or slide along one,
how far, which joint follows another, and names positions
(`mechanical_cad/motion.py`, docs/joints-and-poses-draft.md, which is
written for him: he had said he was not sure what the words meant). The
validator does not read it and the flatten step does not write what is
derived from it. `make axes` lists the lines a joint could be, `make sweep`
walks a joint through its range and says where what it moves is blocked
(stage 7.3), `make picture POSE=NAME` draws an assembly with its joints
moved, and `python3 -m mechanical_cad motion` writes `motion.json` beside a
flattened scene, from which `mechanical-docs` draws a joint as video. Tried
on the mechanical example: its record, the walks' records, pictures and
three videos are in the ignored `tmp/dual-lever-from-step/` (`motion.toml`,
`.cache/sweep/`, `.cache/pictures/poses/`).

**Two projects worked on with these tools on 2026-11-18**, at Peter's word
that day:

- **The Farseer Eye enclosure** (`farseer-mech`), which he named as a
  possible test project. Sections 1 and 2 of the brief in that repository
  are done: the reference's two shell halves and two boards reproduced as
  the same solids, its checks repeated with the same results, the island
  without the rib found, the 90 mm variant equal to the reference
  generator's. At his word the model was moved into that repository as
  `enclosures/eye/`, a project in this layout, with `eye-*` targets in its
  Makefile that hand the commands to this checkout and this checkout's
  environment. Section 3 followed there the same day as a concept for
  joint review: a carrier, an optics cartridge, the first board placement
  as a supplied part; twenty parts, eleven assemblies, 179 checks. It found
  that the gap asked for between guide and detector leaves too little room
  over the board where the placement has parts, and that the rear half for
  the placement's ports does not pass the print check. Options for both
  followed while Peter was away (a vault that makes the rear half print;
  the gap as built variants with a keep-out table). That repository's plan
  and `enclosures/eye/README.md` have its state.
- **The bowls of the first project**: a vacuum formed bowl, the plug it is
  formed over (built against the bowl), the frame that holds six over a
  monitor (built against the monitor, the bowl and the sheet) and an
  assembly, as concepts under that project's `designs/`. Its plan has the
  state and the questions for the researcher. All of them follow from one
  file of numbers there (`studies/bowls/`), so that the researcher's
  answers are a change of numbers and one command.

**Waiting for the Windows agent**, which Peter starts. The task of
2026-11-18 was delivered on 2026-11-20 and reviewed that day (56 checks,
none failed; nothing written to Vault and nothing read, because the one
sign-in it allowed failed and was not tried again). What it gave, and what
followed on Linux:

- The two adds of the reference route (W1) ran whole against a stand-in.
  One line was wrong and is corrected: a live run would have sent three
  empty texts with each relation where the request says nothing is sent.
- What Inventor's add-in records for a relation is still not known. The
  read is asked for once more, with Peter's Vault client open.
- The exporter takes model states and suppressed occurrences. The second
  project passed those guards and stopped at a generated gear's STEP file:
  a hidden surface that is also in a named group. There is no package of
  that project yet.
- Decided here that day, in docs/exporter-package.md: an invisible item
  may also be in the item list of an `APPLIED_GROUP_ASSIGNMENT`, and the
  group is left as it is (`mechanical_cad/stepfile.py`, with a test; on
  the file that stopped the export the kernel then reads one valid solid);
  a part without a solid is kept and placed, and `native.bodies` says how
  many work surfaces it has; and the three places where the exporter
  differs from the wording of 2026-11-18 stand.
- Found by reading the first `package.json` of the changed exporter: the
  import in `vault-cad-tools` would have refused it for its new count.
  Corrected there, with tests.
- A file a colleague has checked out is taken at its last version checked
  in (rehearsed, not run against Vault), and the design of a revision (W2)
  is read and corrected.

That next task, of seven parts, was run and delivered the same day and
reviewed (53 checks, none failed). Nothing was written to Vault, and one
sign-in and one read were made:

- **The read was made after the delivery**, at Peter's word in the Windows
  session with his Vault client open: one sign-in and one read, nothing
  written (12 of the 53 checks are of it). What Inventor's add-in records
  is known now: for the six files the second project's root uses directly, the add-in
  recorded the text `INVENTOR` as the source, the child's own Vault path as
  the expected path, and as the reference id a whole number that differs
  for each child and rises with the order in which the files came into
  Vault. Where the add-in takes that number from is not known; Inventor's
  programming interface was not found to give it. All six are references
  from an assembly to Inventor files; what the add-in records for a part
  that holds a STEP file was not seen. So the two relations of W1, which would
  carry nothing in the three fields, are not what the add-in writes, and
  no new request was prepared: the reference id cannot be given.
- The Windows reader follows the rule for a named group; both readers say
  the same of the 38 files, on Windows and again on Linux.
- A part says its work surfaces and the receipt warns of a part without a
  solid; the import holds the key to the same rule as the Windows check.
- **The second project has a package**, and it is imported on Linux into a
  scratch project outside every repository: 38 parts and 5 assemblies,
  measured, valid, no error and no finding. The 37 parts of the project
  made from the assembly's STEP file (`tmp/dual-lever-from-step/`) are all
  among them by solids, faces and volume; the 38th is an encoder that file
  does not have. The assembly built from the records is not that STEP
  file's (11 of 153 solids at their place), and the third task of the day
  showed that this is the file's doing and not the records'.
- Appearances and materials of the 75 parts of both projects are read
  (evidence, `f/`), to seed a `finishes.toml` as a claim. For 25 metal
  parts the colour given is one grey and not what one sees. Not used yet.
- Constraints, joints and degrees of freedom of the second project are
  read (evidence, `g/`). Set beside the draft `motion.toml` by reading the
  summary, not number by number: the two gear shafts are where the draft
  has them and the gears' ratio is 1; the stage's constraint has limits of
  -21 mm and 21 mm where the draft assumes 6.5; and the two lever units,
  which the draft turns in their slots, are held by an angle in the CAD and
  have no freedom there. An occurrence below a sub-assembly answers in its
  own document's coordinates.
- The user id of the connection is read from the session in both publishing
  scripts, and a session without one is refused before anything is asked of
  the folder. Rehearsed, never run against Vault: a live run of W1 would be
  the first with it.

Peter committed and pushed both patches that evening and the shared
clones were brought level on his word. A third task followed at once,
with no contact with Vault at all, and was delivered and reviewed (17
checks, none failed):

- **Inventor's own STEP export of the second project's root, from its
  mirror, is the assembly the package's records describe**: 153 of 153
  solids where the records put them, within 1.6e-12 mm, none unexpected
  (`tools/compare_assembly_step.py` on the scratch project and that file).
  The 115 occurrences Inventor gave that run are those of the package,
  every cell of every placement. So the import of a project with a file
  in two model states, suppressed occurrences and a flexible instance is
  held against the CAD system's own file, and the STEP file the mechanical
  repository holds is another version or pose of the assembly. The
  comparison holds a solid by volume and centre of mass: a gear turned
  about its own axis reads as in place.
- A page for Peter on making one part with the STEP file as a reference
  model and one assembly by hand and checking them into his test folder,
  under other names than the pilot's (evidence
  `2026-11-20-windows-root-assembly-step-and-a-page-for-peter-01/i/`).
  Written offline by the Windows agent and not tried.
- A line for the read in `windows/HISTORY.md`, applied as delivered and
  waiting for Peter's commit.

No Windows task is written now. What comes next there is Peter's choice
below: if he checks that pair in, one sign-in and two reads show what the
add-in records for the pilot's two relations; if not, the live run as it
stands, on his word for one request.

**Waiting for Peter**:

- The finishes of the first project (`free-standing-tank-enclosure`,
  `finishes.toml`): a draft that gives 31 of its 43 parts a finish, each
  from the part's name or from the material CAD claims for it. The twelve
  without one, the panels among them, and every colour are his to correct;
  and whether its manual is drawn with them (open decision 20). On
  2026-11-19 he said there is no need for another full-quality render of
  that manual just yet.
- Joints and poses: whether they become records of the layout (open
  decision 21; docs/joints-and-poses-draft.md ends with what is his to
  decide).
- Whether the first project's manual gets outlines from Line Art where
  Freestyle draws none (`mechanical-docs`, plan, next work 5; the sheet
  `line-art-comparison.png` in that project's ignored `.cache/pictures/`).
- The joint review of the Farseer model with the board's designer, which
  its brief asks for, and the printer and the material for it.
- The researcher's answers on the bowls, and who forms them
  (`free-standing-tank-enclosure`, plan, next work 7).
- How W1 goes on, now that the add-in's relations are read
  (docs/direction.md, "For Peter to decide", 4). Recommended: he checks
  one wrapper part with its assembly into the test folder from Inventor
  himself (he has the page for it since 2026-11-20), one more read shows
  what the add-in records for them, and the pilot is made to send the
  same; then his word for the live run. Or his word for the live run as it
  stands, which adds two files whose relations carry less than the
  add-in's.
- Which changed file the pilot of a revision publishes
  (`vault-cad-tools/docs/update-step-file-design.md`, section 10).
- The monitors' mount in the first project, held until he has spoken with
  the researcher. A picture of the arm he prefers with the monitor on it,
  in colour, is in that project's ignored `tmp/monitor-mounts/`.
- What a part taken out of an assembly file says of where it came from
  (open decision 19), the proposals of 2026-11-18 (open decision 18) and
  the older open decisions, listed under "Open decisions to put to Peter".

**Next on Linux, none of it needing Windows**:

1. Farseer, section 3, in `farseer-mech/enclosures/eye/`: what the joint
   review changes, the real connectors and plugs in place of the assumed
   envelopes when the board's side names them, and the plastic fit mockup
   the brief ends with, once there is a printer.
2. What the two projects showed missing, in the order of use (open
   decision 18): a project's main assembly; numbers shared by parts; space
   kept clear and what a fit check should find; how a part is printed.
   Each touches the layout and waits for Peter's word.
3. After stage 6, which is built: the layout's own word on a part without
   a solid (the tools now name one, and one stage takes it by name: open
   decision 19);
   seeding a project's finishes from the appearances read in Inventor,
   and holding the draft joints against the constraints read there (the
   package of the mechanical example imports and is Inventor's assembly;
   the project made from its older STEP file has the same parts in another
   pose or version); and, if Peter
   says so, the conversion of `mouse-joysticks-mech` itself.
4. Stage 7: everything in it is built, the joints and what uses them as
   a draft. Left: Peter's word on that draft (open decision 21), and then
   the record in the layout, the validator and the flatten step; the fit
   check over a range run on the monitor's arm, once the arm is a part of
   the first project with its links as components; views, when something
   needs a picture by name.
5. Smaller, none needing a word:
   - a project made of one STEP file saying which way is up
     (`tools/take_apart.py` writes no frame, and the mechanical example,
     which stands Y up, is taken as Z up by everything that draws it);
   - the second lever unit's lever and stage in the example's record, and
     the walk of a joint made quicker where two gears are compared at
     every step (sixteen to twenty minutes there);
   - a pocket for a foot placed clear of the standoffs without being
     told; louvres;
   - openings, a lip and flanges in a flat pattern, and the sheet's
     thickness;
   - hidden edges dashed in a section, and its header kept on a narrow
     sheet;
   - in `mechanical-docs` (its plan, next work 5): outlines on parts
     behind ghosted ones; a whole manual built once with Line Art.
6. The Linux half of a revision as a new version (request, plan, journal,
   record, import), after Windows has read the design.

Tests on 2026-11-20: 640 pass without a kernel (121 skipped), 758
with FreeCAD, the bindings, build123d and bd_warehouse (5 skipped); in
`vault-cad-tools`, 116 when run from this checkout. Not run again that
day, nothing in them having changed: the 14 of `tests/test_picture.py`
with the viewer and build123d together, and `mechanical-docs` (221, 6
skipped, and 227 with FreeCAD at the end of 2026-11-19).

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
   This now decides a next step (2026-11-16). Peter prefers the arm McMaster
   5537T879 for the enclosure's monitors, and the study that mated it to the
   monitor lives in an ignored directory. To make it an assembly of the
   project that opens in FreeCAD, is checked for fit and can be published,
   the arm has to be a component, and the layout has no place for a file
   that comes from a supplier. Proposed to him: a third source of a part
   beside the program and the drawn document, the supplier's file itself
   with a record of where it came from (supplier, part number, the file's
   hash, the day), and the arm as two such parts, what turns with the plate
   and the rest, placed by an authored assembly. Not built. It is of use
   only if the supplier's file may be committed: the enclosure's repository
   is public, and it already holds the supplier models that came through
   Vault.
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
    Linux role recommends it. It did, and built it that day (the record in
    .agents/HISTORY.md, item 4).
13. Settled by Peter on 2026-11-13: this repository is GPL-3.0-or-later
    (`LICENSE`, README, `.agents/AGENTS.md`), so the package definitions can
    be offered to Guix. He said "GPL-3.0"; "or later" is what Guix asks for
    and what was written. The other repositories stay 3-clause BSD.
14. Settled by Peter on 2026-11-13: the eight Windows scripts that served
    only the earlier export formats are removed, and with them the reading
    of the earlier package (`vault-cad-tools/.agents/PLANS.md`).
15. The plan of the whole project. Peter asked for one on 2026-11-16 and
    restated the goal (import and export to and from Inventor and Vault;
    viewing, documenting and creating parts on Linux, with agents, programs
    and a graphical editor). Proposed that day in docs/direction.md: thirteen
    capabilities with the state of each (four done, three partly, six not
    begun), an order of work in six steps, what else to package and which
    tests with Inventor and Vault are worth running. Peter the same day:
    - the goals and the order "seem reasonable" (now under "Decided");
    - the first real part: he is not sure which, "we can try modeling the
      monitor". Begun that day in the enclosure (the record in
      .agents/HISTORY.md, item 5);
    - "I authorize vault access for test". Taken as reading only, which is
      what he was asked, and told to him so; no write is authorized. Three
      read-only tests were asked of Windows that day (`vault-cad-tools`
      plan);
    - where a part drawn in FreeCAD should sit, a question back. Recommended
      to him; **he decided it later that day ("FreeCAD-drawn parts may sit
      beside programmed ones") and it was built** (`tools/kernel.py`
      `document_shape`, `tools/build_part.py`, the validator, the
      specification; three tests of the validator and three with FreeCAD: a
      document made by a script is built, validates, builds again to the
      same files, goes stale when it is saved again and gives the same
      STEP file when the solid is the same; a body of Part Design is the
      part, and a sketch and a sheet left over beside it do not count; a
      document with two solids, with none, and a part with both sources are
      refused). Not done: a document drawn by hand in the FreeCAD window.
      As recommended: in `designs/parts/<key>/`
      like a programmed part, with `part.FCStd` as its source where a
      programmed part has `build.py` and `parameters.json`, never both. A
      command opens the document with FreeCADCmd, recomputes it, refuses a
      document that does not recompute or has more than one shape to
      export, and writes `part.step`, `receipt.json` (with the document's
      hash) and `facts.json` as the build command does; `checks.json`, the
      validator, the assembly manifests and the publication are the same
      for both kinds. What it costs: a FreeCAD document is a zip file that
      Git cannot compare and that changes in every byte when it is saved,
      so the STEP file and the facts are what a review reads. The decision
      of 2026-10-23 that new parts are programs would then read "programs,
      or documents of FreeCAD".

16. Which state a mirror holds. Found on 2026-11-16 by the read-only tests
    against Vault (`vault-cad-tools` plan, next work 4): the server answers
    any version of a root assembly with its children at their latest
    versions, so a root version does not name a state. Recommended to Peter:
    a mirror is "get latest", every file at its latest version, which is
    what a collaborator sees who opens the assembly in Inventor today and
    what the first project's mirror is; whether it is current is asked of
    every file in it. The state a root version was checked in with can be
    rebuilt by date, as a rule and not a record, and is not what a project
    is mirrored with.

17. The plan of 2026-11-17 (docs/direction.md, "Plan: parts around other
    parts, enclosures for boards, pictures and motion"). Peter that day
    wanted every addition put to him and the three further Windows tasks
    (under "Decided" there), named `mouse-joystick-pcb` and
    `mouse-joysticks-mech` as examples, said he designs boards in KiCad and
    renders and would animate such projects in Blender, and asked for a
    plan. It adds goals 14 to 20 and eight stages. Later that day he
    answered four of its six questions (now under "Decided" in
    docs/direction.md): a supplied file lives in `designs/parts/<key>/` as
    recommended; a supplier's file may be public, which settles decision 6
    above; the board's generator in `kicad-libs` may be used or changed; and
    the natives of `mouse-joysticks-mech` are in Vault (the folder is in the
    ignored `.agents/handoff.local.md`). Left for him: where the first
    enclosure lives, and how it is made; and, since the Windows reads of
    that day, whether a published file should carry the lab of its project,
    and the live run of W1 once Windows has said what it writes
    (docs/direction.md, "For Peter to decide", 3 and 4). He answered the
    question of the second project that day: it may be mirrored for
    testing, in the shared directory, and `mouse-joysticks-mech` is left
    alone ("Decided"). The six as they were put:
    - where a supplied file lives (recommended: a third source of a part in
      `designs/parts/<key>/`, as proposed under 6 above);
    - where the first enclosure lives (recommended: a new project
      repository, the board pinned by commit);
    - how the first enclosure is made (assumed: printed), and then the
      printer and the material;
    - whether the board's generator in `kicad-libs` is asked for heights,
      mating directions and references in the STEP file;
    - decision 6 above, which holds up the monitor arm only;
    - whether the native files of `mouse-joysticks-mech` are in Vault.

18. What two projects showed missing on 2026-11-18 (docs/direction.md,
    "Built so far": the Farseer Eye enclosure reproduced, and a formed part,
    its tool and its frame). Each is a proposal; none is built, and where
    one touches the layout its three descriptions change together:
    - **A project's main assembly.** With two assemblies that nothing
      places, `assembly`, `open`, `built` and `flatten` ask for a key. The
      first project names its mirrored root in its own Makefile and
      script. Proposed: the layout lets a project say which assembly is
      meant when none is named.
    - **Numbers shared by parts.** A study has one set of numbers and many
      parts; today a project script writes each part's `parameters.json`,
      `checks.json` and the placements from one file, and a variant is a
      copy of the project. Proposed: a project parameter file that parts
      name and receipts hash; or that script as a documented pattern.
    - **Code shared by parts.** A receipt hashes `build.py` alone, so a
      change in `mechanical_cad/shapes`, `enclosures.py` or a module of the
      project does not make a part stale. Proposed: the receipt records the
      modules the program imported, with their hashes.
    - **How a part is printed.** Which way up, the process, the layer and
      the angle have no place; the Farseer halves are written in their
      print orientation. Proposed: an optional hand-edited file beside a
      part, read by `print_check.py` and `print_file.py`.
    - **Space kept clear.** A `port` and a `keep_out` are boxes along the
      axes; a round or swept clearance cannot be stated, a circle neither
      (an outline is a polygon), and nothing holds a keep-out against an
      assembly. Sweeps as parts placed as reference children work and are
      drawn like material.
    - **What a fit check should find.** `fit_check.py` lists interference,
      contact and gaps; it cannot be told that two parts may touch or that
      a pair keeps half a millimetre, so a person reads the list.
      Proposed: expectations stated in the assembly.
    - **The same solid?** Comparing an authored part with a file from
      outside is a script of the Farseer project (volume in one and not
      the other, both ways; distance between the surfaces; a control).
      `compare_step_exports.py` looks under `references/` only.
    - **Pictures.** Built on 2026-11-18, being a tool and no part of the
      layout: `tools/picture.py --cut` and `--colour` (docs/direction.md,
      "Built so far"). Left: a section as a drawing with dimensions, and
      finishes curated by a project.

19. What a part taken out of an assembly file says of where it came from
    (stage 6, 2026-11-18). `tools/take_apart.py` writes such a part as a
    supplied part, without a change to the layout, and stretches two of its
    statements: `received_sha256` in `origin.json` is the hash of the
    assembly file the part was taken from, where the layout means the file
    of the part as it came; and `part.step` is written by the kernel, where
    the layout says a supplied part's data section is what was received.
    The project as a whole has no record of the file. To accept as it is,
    or: a kind of origin of its own for a part taken out of a larger file,
    and a place for the record of that file. Also open there: what a part
    is that has faces and no solid (one of the 37 in the trial). Since
    2026-11-19 the tools say what they do with one, and no rule is
    written: `fit_check.py` and `sweep_check.py` name it as not compared,
    and `mechanical-docs`' mesh stage refuses it unless it is named with
    `--surface-parts`, then meshes its faces and records that. The layout
    still says nothing of it.

20. What the finishes left open (2026-11-19; docs/direction.md, "Built so
    far", stage 7). Peter decided the one thing asked: one file for the
    project. Built on that, and his to accept or change:
    - **Beside the scene, not in it.** He was told the flatten step would
      carry the finishes into `scene.json`. It writes `finishes.json`
      beside it, because `mechanical-docs` gates its meshes and renders on
      the scene's hash.
    - **What a finish is**: an sRGB colour, `metallic`, `roughness`,
      `opacity`, a note; one for a part, by key; an optional default. No
      finish for one solid of a part or one occurrence.
    - **The first project's draft** (`free-standing-tank-enclosure`,
      `finishes.toml`): twelve parts without a finish, the panels first;
      whether zinc is right for the two framing parts CAD claims it for;
      every colour.
    - **A manual with finishes.** The renderer's studio turns a finish
      lighter than a dark grey white on top. Stills are exposed for their
      colours; a manual's views are not, and the first project's recipe
      does not hand its finishes to the manual. Whether it should, and how
      a manual is then lit, is his. To decide by: six of the first
      project's views as its manual draws them today and with its finishes
      at three exposures, on one sheet in that project's ignored
      `.cache/pictures/manual-views-finishes-and-exposure.png`. The
      full-quality render of that manual was not made for the same reason:
      either answer decides what it is a render of.
    - **The colour a part gets when a file is taken apart**: the one most
      of its surface has. Three parts of the mechanical example have
      several colours in their file and are drawn in one.
    - **Feet under an enclosure** are bosses, which a printer has to
      support, or since the third round of 2026-11-19 pockets for
      stick-on feet, with which the base lies on its floor. The print
      check passes such a base only when it is told how far the printer
      bridges (`--bridge 9` for pockets 8.4 mm across); no width is
      assumed, and which width is right for a printer is his.

21. Joints and poses (2026-11-19; docs/joints-and-poses-draft.md, which
    ends with these). Built as a draft outside the layout, at his word to
    go on with as much as was recommended:
    - **Whether they belong in the layout at all.** A yes means a section
      in the specification, `validate` reading `motion.toml`, `flatten`
      writing `motion.json`, a record in the fixture; a no removes one
      module, two tools, two options of the picture tool and three
      Makefile targets here, and a reader and two kinds of video in
      `mechanical-docs`.
    - **One file for the project or one beside each assembly.** Built as
      one, as he chose for finishes.
    - **A joint's line as numbers**, which `make axes` finds, or as a
      named feature of a part.
    - **A joint that follows another** (`follows`, `ratio`) was added
      because the example's lever is gear-driven; it stands for gears, a
      rack, a belt, and nothing else couples two joints.
    - **Views** are not built and not proposed yet.

## Next work

The order is the list under "Start here", "Next on Linux". Carried over from
the record that moved to .agents/HISTORY.md on 2026-11-19, each still open:

- **The first project's manual at full quality.** The project was converted
  and its part ids changed, so every view is rendered once; that render
  waits for Peter's corrected instructions (`mechanical-docs`, plan, next
  work 1).
- **The monitors' mount in the first project**, when Peter takes it up
  again: his measurements of the monitor, the tilt range and the rating of
  the arm he prefers (McMaster 5537T879), and then the arm as a supplied
  part placed by an authored assembly, which the layout has had a place for
  since 2026-11-17. The study of 2026-11-16 is in that project's ignored
  `tmp/monitor-mounts/`.
- **A part that is made, and measured against its STEP file** (goals 9 and
  18): nothing has been made yet.
- **Before the packages can be offered to Guix itself.** Done on
  2026-11-19, and built and tested here: the OCP bindings generated in
  the build from OCP's repository and the headers of `opencascade-occt`,
  with pywrap and the Python bindings of Clang 21; lib3mf 2.5.0 beside
  Guix's 2.2.0; `python-anytree` giving its version; the tests of
  `python-dataclasses-json` and `python-pygltflib` run, but for those
  that need mypy or the Khronos sample models; the inputs of
  `python-ocp` pruned, and compiled without debugging symbols. Left:
  - three definitions stand for changes to Guix's own packages and are
    to be offered as that: `clang-python-bindings` entering
    `clang/bindings/python` for the later releases, with a
    `python-clang-21`; a phase for `python-anytree` that hands
    pdm-backend the version; `lib3mf` updated;
  - lib3mf 2.5.0 is built from the sources its own generator wrote,
    which Guix's release of that generator does not reproduce;
  - a second build of `python-ocp` compared with the first
    (`guix build --check`), other architectures, and Guix's other users
    of lib3mf;
  - the issue Open Cascade SAS opened on 2026-11-12 about OCP's licence
    compliance (CadQuery/OCP, 234): the maintainer agreed and added the
    licence texts on 2026-11-14; the notices in every generated file and
    the wheels' metadata were not released when it was read on
    2026-11-19, and it is open. What is generated here carries what
    upstream's generator writes, so the notices come with a later
    release of it.
  Offering anything to Guix is Peter's.
- **CadQuery 2.8.0**, if wanted: it needs `casadi` and `runtype`, which
  Guix lacks, a newer `multimethod`, and VTK's Python modules. And a kernel
  module on OCP that measures and writes without FreeCADCmd.
- **Peter's review of the exporter's package** (docs/exporter-package.md,
  draft 3; open decision 1).

## Known limits of what was built

- The validator has been run on two projects: the fixture and the converted
  enclosure. The tolerances for comparing geometry facts are provisional (one
  kernel version).
- Measuring needs the OCP bindings since 2026-11-13, which nothing builds
  for anyone: about thirty-five minutes after each update of Guix that
  changes what they depend on, since 2026-11-19, when the build began to
  generate them (twenty before, with upstream's generated sources). The
  fingerprint's tolerances (1e-6) are tighter than
  the integration reaches for one part of the enclosure (2.3e-5), and have
  not been tried between two exports of a part since the change.
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
  product. Two parts have been built from a build123d program, the fixture's
  spacer in a test and the enclosure's monitor envelope, both simple solids.
  There is no CadQuery path.
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

- `tools/cut_file.py` writes lines, arcs and circles, one part per
  drawing; an ellipse or a spline in an outline is refused. `--kerf`
  refuses a slot exactly as wide as the cut, draws sharp inside corners
  sharp and counts them, and adds no relief or lead-in. `--open` names
  only faces square to an axis, of a closed convex solid; a pattern has
  no holes, flanges, tabs, thickness, bend allowance or kerf. It has been
  run on one real part, the first project's bowl frame, and nothing has
  been cut or folded from any drawing. It reaches into the DXF library
  for the order of its
  class records, which another version of that library may arrange
  differently; the test that runs the tool under two hash seeds would then
  fail.
- `tools/print_check.py` samples: slices every half millimetre, and curved
  faces over a mesh. It has been run on the Farseer halves, where it gives
  the reference's results, and on one part of the first project. Nothing
  it passed has been printed. A bridge is judged by a ceiling's width,
  measured every five degrees round, and by what is under its two ends,
  not along its whole edge.
- `tools/sweep_check.py` samples a joint's range: something thinner than
  a step's motion can be passed through unseen. It compares solids, so a
  part that is faces only is not seen (the mechanical example's switch).
  What moves together is said by hand in the draft record; a child
  wrongly put into a joint is not seen at all. It has been run on one
  real assembly, and nothing it found has been compared with the thing
  itself.
- build123d's `scale` enlarges a shape about the origin it had before it
  was moved, and its `export_stl` takes its tolerance as a fraction of an
  edge's size. Both were met on 2026-11-18, the first by a volume held in
  a part's program, the second by the print file's own check.

- `tools/take_apart.py` has been run on one real file. It reads every
  product in millimetres, gives a part the one colour most of its surface
  has, writes no frame (which way is up), and tells products apart by
  their identity in the file, not by their shape. A part's `origin.json`
  then carries the hash of the assembly file as `received_sha256`, which
  the layout says of a file as it came.
- `tools/picture.py --cut` and `--colour` and `tools/section.py` put an
  assembly together with build123d, every occurrence with geometry of its
  own, so a model of the first project's whole enclosure is 33 MB and
  takes three minutes. A section's curves are short straight pieces
  unless `--arcs` is given, and then only circular ones are arcs. The
  edges behind the plane come from the kernel's exact projection, which
  did not finish one side of the mechanical example in 45 minutes, or
  with `--quick` from a mesh, where edges that lie one behind the other
  are both drawn and a ball's outline had gaps in a trial.

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
