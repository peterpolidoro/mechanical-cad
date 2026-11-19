# mechanical-cad living plan

## Objective

Give Peter's Inventor and Vault projects an open representation in Git and the
open-source tools to check it, document it and add to it, with the
free-standing tank enclosure as the test project. The full statement is
docs/direction.md. Finished checkpoints are in .agents/HISTORY.md.

## Start here (state of 2026-11-19)

This section is the short version. Where the work is going, what is decided
and what is built are in docs/direction.md ("Goals, and where each stands",
"Decided", "Plan: parts around other parts, enclosures for boards, pictures
and motion" with its "Built so far"). The record of how each piece came
about, up to 2026-11-18, is in .agents/HISTORY.md. Paths on this machine,
ids, and the state of the shared clones are in the ignored
`.agents/handoff.local.md` and on the share in `coordination/NEXT-AGENT.md`
and `coordination/status/`. A session that begins after this one reads "For
the next session" at the end of that handoff file first.

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
  halves, and since 2026-11-19 vents through any flat wall and feet under
  the base; fit checks. Shown on the example board in an ignored project
  of this checkout.
- Files to make a part from, each checked against the solid: a mesh to
  print (`tools/print_file.py`, with an absolute deflection since
  2026-11-18), a drawing to cut a plate from sheet (`tools/cut_file.py`,
  2026-11-18), the flat pattern of a solid with flat faces, with its fold
  lines (`tools/cut_file.py --pattern`, 2026-11-19), and whether a part
  prints as it lies, by overhangs and by material that starts in mid-air
  (`tools/print_check.py`, 2026-11-18).
- Pictures without a window, of a part or an assembly, since 2026-11-18
  also cut open and with every part in a colour of its own
  (`tools/picture.py --cut +y --colour`).
- A section as a drawing to scale, every part in its colour
  (`tools/section.py`, 2026-11-18), with dimensions between named points
  of the model (`--measure`, 2026-11-19).
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
- Moving pictures, stage 7.2 but for a joint (2026-11-19, in
  `mechanical-docs`): a turntable, the subassemblies moving apart and
  back, and a project's steps in the manual's order, each as video. Four
  videos of the first project are in its ignored `.cache/pictures/`.
- A STEP file published to Vault and verified, twice (`vault-cad-tools`).

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

**Waiting for the Windows agent**, which Peter starts. The shared clones
were brought level on his word twice on 2026-11-18, the second time when
the session ended, with everything he had pushed until then; the gate of
the task on the share passes. The task has five parts and writes nothing to
Vault: the two adds of the reference route (W1) rehearsed; one read of
what Inventor's add-in records for a relation between two files; the
exporter with model states, run on the mirror of the second project; an
acquisition that takes a checked-out file at its last version checked in;
and the design of a revision (W2) read and corrected. When Windows
delivers, the delivery is checked and answered as
`coordination/NEXT-AGENT.md` on the share describes. The shared clone of
this repository lacks the last commit of 2026-11-18, which changes
documents, and the work of 2026-11-19; it is brought level on Peter's word,
and the Windows task needs neither. On 2026-11-19 the share was not mounted
in the agent's session: whether Windows has delivered was not looked at,
and the share's coordination plan and status file were not refreshed.

**Waiting for Peter**:

- The finishes of the first project (`free-standing-tank-enclosure`,
  `finishes.toml`): a draft that gives 31 of its 43 parts a finish, each
  from the part's name or from the material CAD claims for it. The twelve
  without one, the panels among them, and every colour are his to correct;
  and whether its manual is drawn with them (open decision 20).
- The joint review of the Farseer model with the board's designer, which
  its brief asks for, and the printer and the material for it.
- The researcher's answers on the bowls, and who forms them
  (`free-standing-tank-enclosure`, plan, next work 7).
- His word for the live run of W1, which adds two files to his test folder
  (docs/direction.md, "For Peter to decide", 4). Recommended after the
  Windows task above.
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
3. After stage 6, which is built: a rule for a part without a solid;
   comparing the project made from the mechanical example's file with the
   Vault mirror of the same assembly once Windows exports it; and, if Peter
   says so, the conversion of `mouse-joysticks-mech` itself.
4. Stage 7 goes on. Finishes, stills, a turntable, an exploded sequence
   and a steps sequence are built (above). What is left of it touches the
   layout and waits for Peter's word: joints between components with an
   axis and its limits, named poses, views (7.1); then a joint moved
   through its range as video (7.2) and the fit check over that range,
   which the monitor arm needs (7.3).
5. Smaller, none needing a word: recesses for stick-on feet, since a base
   with bosses under it no longer prints lying on its floor; vents on
   round corners or staggered; a flat pattern of a shell with open faces
   or of an enclosure half; hatching in a section and what lies behind its
   plane; outlines on whole assemblies in `mechanical-docs` with Line Art
   (its plan, next work 5).
6. The Linux half of a revision as a new version (request, plan, journal,
   record, import), after Windows has read the design.

Done on 2026-11-19 at Peter's word to go on without him, and so no longer
on this list: the colours of a file that is taken apart, vents and feet,
the prism that follows a rectangular board, flat patterns through the cut
file, dimensions in a section, a test of the index derived in two places,
and the housekeeping (the plan's record moved to .agents/HISTORY.md, the
README's status).

Tests at the end of 2026-11-19: 557 pass without a kernel (95 skipped), 650
with FreeCAD, the bindings, build123d and bd_warehouse (4 skipped), and the
12 of `tests/test_picture.py` with the viewer and build123d together. In
`mechanical-docs`, 168 (4 skipped) and 172 with FreeCAD; in
`vault-cad-tools`, 113 when run from this checkout.

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
    is that has faces and no solid (one of the 37 in the trial).

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
    - **Feet under an enclosure are bosses**, which a printer has to
      support; recesses for stick-on feet are not built.

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
- **Before the packages can be offered to Guix itself**: the OCP bindings
  generated in the build, from OCP's repository and the headers of
  `opencascade-occt`, with pywrap and libclang 20 or 21 (Guix defines the
  Python bindings of clang for version 13 only); lib3mf 2.4.1 in Guix,
  which build123d asks for; `python-anytree` in Guix giving its version as
  0.0.0; the tests of `python-dataclasses-json` and `python-pygltflib`; the
  inputs of `python-ocp` pruned to what the build uses, and a build type
  without debugging symbols. To watch before anything is submitted: the
  issue Open Cascade SAS opened on 2026-11-12 about OCP's licence
  compliance.
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
  for anyone: about twenty minutes after each update of Guix that changes
  what they depend on. The fingerprint's tolerances (1e-6) are tighter than
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

- `tools/cut_file.py` writes straight lines and circles only, one part per
  drawing, with no allowance for the width of the cut. It has been run on
  one real part, the first project's bowl frame, and nothing has been cut
  from its drawing. It reaches into the DXF library for the order of its
  class records, which another version of that library may arrange
  differently; the test that runs the tool under two hash seeds would then
  fail.
- `tools/print_check.py` samples: slices every half millimetre, and curved
  faces over a mesh. It has been run on the Farseer halves, where it gives
  the reference's results, and on one part of the first project. Nothing
  it passed has been printed.
- build123d's `scale` enlarges a shape about the origin it had before it
  was moved, and its `export_stl` takes its tolerance as a fraction of an
  edge's size. Both were met on 2026-11-18, the first by a volume held in
  a part's program, the second by the print file's own check.

- `tools/take_apart.py` has been run on one real file. It reads every
  product in millimetres, keeps no colour, and tells products apart by
  their identity in the file, not by their shape. A part's `origin.json`
  then carries the hash of the assembly file as `received_sha256`, which
  the layout says of a file as it came.
- `tools/picture.py --cut` and `--colour` and `tools/section.py` put an
  assembly together with build123d, every occurrence with geometry of its
  own, so a model of the first project's whole enclosure is 33 MB and
  takes three minutes. A section's curves are short straight pieces.

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
