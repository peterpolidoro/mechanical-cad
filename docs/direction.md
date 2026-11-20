# Direction

**Status: proposal, drafted 2026-11-10 from Peter's statements. Not yet accepted.**
Sections marked *decided* record what Peter has already settled, with the date.
Sections marked *proposed* are waiting for a decision. The goals and the order
of work were written on 2026-11-16, when Peter asked for a plan of the whole
project, and he accepted them that day; the two sections after them are
proposals. On 2026-11-17 he accepted further additions and asked for a plan
of them: it is the last section before "Not settled".

This is the one place that says where the open mechanical CAD work is going.
Each repository's `.agents/PLANS.md` records that repository's own work and
links here; none of them restates the direction.

## Goal

Work with collaborators who use only Windows, Autodesk Inventor and Vault, while
doing as much as possible on a Linux desktop with free and open-source tools.

Keep an open representation, in Git, of the Inventor parts and assemblies that
live in Vault: STEP geometry plus metadata that people and agents can read,
check, render and build on without proprietary software. Scripts or agents on a
Windows machine handle the Vault and Inventor interactions and nothing else.

Why: designs should not be readable only through a paid, proprietary tool;
collaborators without Inventor or Vault should be able to use them; and open
files let agents and deterministic tools take part in mechanical design.

## The loop this has to support

The free-standing tank enclosure is the test project for every stage.

1. **Mirror.** A Vault project is exported at exact versions into a project
   repository as STEP plus metadata.
2. **Document.** A parts inventory and assembly manual are generated from the
   repository.
3. **Build.** The hardware is assembled from that manual; notes from the bench
   improve the manual.
4. **Design.** Agents write new parts as parametric programs that produce STEP
   in the project repository, with checks that state what the geometry must
   satisfy.
5. **Make and verify.** The parts are manufactured and checked against the STEP.
6. **Publish.** The verified STEP files are placed in Vault so collaborators can
   use them from Inventor.

## Goals, and where each stands (2026-11-16)

Peter on 2026-11-16: import and export to and from Inventor and Vault, so
that open-source tools on Linux can view and document mechanical CAD
projects and create parts, with agents, with programs and in a graphical
editor. As capabilities, each with what shows it done:

| | Capability | State on 2026-11-16 |
| --- | --- | --- |
| | **Import** | |
| 1 | An assembly in Vault is mirrored at exact versions as STEP and metadata that validate | **Done** on the first project; the mirror is Inventor's own export of the assembly, solid for solid |
| 2 | A mirror is refreshed after Vault changed: what changed is found, only that is exported again, what is gone is removed | **Partly** (2026-11-16). A refresh from an earlier version of the first project's root to the one it holds gives the repository's files byte for byte: one file updated, four new, the rest untouched. `vault-cad sync-status` says file by file what a refresh would change, from a discovery of the Vault folder. and the import removes what is gone when asked. Not built: exporting only what changed. Nothing has changed in Vault since the mirror was made, so no refresh has yet followed a real change there |
| 3 | A second assembly or project goes through the same commands | **Done once** (2026-11-16), as a test: a second root assembly was acquired, exported, imported, measured, validated and built, with no change to a command. A second project was acquired on 2026-11-17 and its export stopped at a guard, the first to fire on real data: a sub-assembly used in two model states ("Built so far") |
| | **View** | |
| 4 | Any part or assembly opens on Linux | **Done**: a FreeCAD document and a STEP file of any assembly, built from the records. No colour |
| | **Document** | |
| 5 | An inventory and an assembly manual are generated from the repository, good enough to build from | **Partly.** The pipeline runs end to end and a draft manual is published; it is being corrected at the bench, and has not been rendered at full quality since the re-export |
| | **Create** | |
| 6 | A part is written as a program, built and checked | **Partly.** The tools are there (build123d and its bindings packaged here, `tools/build_part.py`), shown on one simple solid |
| 7 | A part is designed to fit: its checks say how it meets the parts around it, and whoever writes it, person or agent, can see it | **Done for a part** (2026-11-16). A check may name a point of the part and say whether it is material or empty, which states a hole, a face or an opening; `tools/fit_check.py` tests what is being designed against the rest of an assembly for interference, contact and clearance; `tools/picture.py` draws a part or a built assembly without a window. Not built: a place for a supplier's file, so that a bought part can be a component |
| 8 | A part drawn in a graphical editor is kept like a programmed one | **Built** (2026-11-16), after Peter decided it that day: `part.FCStd` as a part's source, built and validated like a program. Shown on documents made by a script; no part of a project has been drawn by hand yet |
| 9 | A part is made and verified: a file to make it from, and a record of the made part against the STEP | **Not started** |
| | **Export** | |
| 10 | A new STEP file is added to Vault and verified | **Done** (2026-11-17) for a part authored in the new layout: planned, run dry, added once to a test folder Peter made, and verified by downloading it again. First done on 2026-10-22, before the layout changed |
| 11 | A published part is revised: a new version of the same Vault file | **Not built** |
| 12 | A collaborator uses the part from Inventor: the STEP referenced in a native assembly, following its revisions | **Partly**: tried in a disposable copy only. Shown besides: Inventor opens a STEP file of a whole assembly built here with every name and placement right |
| | **Packaging** | |
| 13 | The tools are Guix packages | **Done here** for the OCP bindings and build123d, in this repository's channel. Not offered to Guix |

Six done, five partly, two not begun (four, three and six when the table
was first written, earlier the same day). Of the loop above, mirror and
document have run on the first project and its build is under way. Design,
make and publish have not run for one real part, and a mirror has never been
refreshed.

### Where the goals stand on 2026-11-18

An agent's reading of "Built so far" below, for Peter to correct; goals 14 to
20 are those of the plan of 2026-11-17. Nothing in it is a decision.

| | Goal | State on 2026-11-18 |
| --- | --- | --- |
| 1 | Mirror an assembly from Vault | Done on the first project |
| 2 | Refresh a mirror | Partly, as on 2026-11-16: no refresh has followed a real change in Vault |
| 3 | A second assembly or project | A second assembly done once. The second project is mirrored and its export stopped at a sub-assembly in two model states; the exporter's change is in the Windows task that waits to be started |
| 4 | Any part or assembly opens on Linux | Done; since 2026-11-18 also drawn in colour, cut open, and as a section to scale |
| 5 | Inventory and manual | Partly, as on 2026-11-16: waits for the notes from the bench |
| 6 | A part written as a program, built and checked | Done on real parts: the monitor, the bowl with its plug and frame (concepts), the twenty parts of the Farseer Eye model |
| 7 | A part designed to fit, and seen | Done, and used on both projects of 2026-11-18: point checks, interfaces, fit checks, pictures |
| 8 | A drawn part kept like a programmed one | Built; no part of a project has been drawn by hand |
| 9 | A part made and verified | **Nothing has been made.** What comes before making exists: the mesh to print, the check that a part prints as it lies, the drawing to cut a plate from. No slicer has run with a printer's profile and no made part has been measured |
| 10 | A new STEP file in Vault | Done, twice |
| 11 | A published part revised | Designed, not built; Windows reads the design in the task that waits |
| 12 | A collaborator uses the part from Inventor | Partly: the route is made ready up to the write, by a dry run; its rehearsal is in the Windows task that waits, and the live run waits for Peter's word for one request |
| 13 | The tools as Guix packages | Done in this repository's channel; not offered to Guix |
| 14 | A file from outside is a component | Done: a board, and the first placement of the Farseer board |
| 15 | A part built against other components | Done: enclosure halves, the forming plug, the bowl frame, the Farseer carrier |
| 16 | A component states its interface | Done for boards and for authored parts; a circle and a swept clearance cannot be stated |
| 17 | An enclosure generated for a board | Done on the example board as box, polyhedron and prism; the Farseer enclosure reproduced from its reference and extended |
| 18 | Printed, measured; flat stock cut | As goal 9: the files and the checks, nothing made |
| 19 | A project that begins as one STEP file | Done on the mechanical example (stage 6) |
| 20 | Pictured and animated from records | Begun: colour by part, cuts, sections. No finishes kept by a project, no joints, no motion |

What has never run is the stretch from a file to a made part and back to a
measurement (goals 9 and 18), and that needs a printer, a former or a cutter
and Peter's choice of one.

Since 2026-11-19, goal 20: a project keeps its finishes, both picture
tools draw with them, and `mechanical-docs` writes a turntable and an
exploded sequence as video ("Built so far", stage 7). No joints and no
poses, so no joint in motion.

## Decided

- Inventor natives in Vault stay intact and authoritative while they match their
  STEP exports. A native that has not changed is never overwritten. (2026-10-23)
- Every part has one authority: Vault for parts designed in Inventor, the
  repository for parts written as code.
- A STEP file pushed to Vault is stored as STEP and referenced from Inventor; it
  is never converted into a non-parametric native body. (2026-10-23)
- New parts are parametric Python programs that produce B-rep STEP: FreeCAD
  scripting today, build123d or CadQuery once packaged. The program, its
  parameters, the STEP and a receipt are committed together. Inventor is not an
  authoring tool unless a collaborator insists. (2026-10-23) build123d is
  packaged first, with the OCP bindings, in a Guix channel in this
  repository; CadQuery may follow once build123d works, to give agents and
  people more options. (2026-11-13)
- An assembly is per-part STEP files plus a placement manifest, never a single
  assembly STEP as the source. (2026-10-23) A STEP file of a whole assembly,
  for viewing and for documentation, is generated from them and not stored in
  the repository. (2026-11-11)
- Linux controls the workflow. Windows performs only the Vault and Inventor
  operations, through validated request and result files in a shared directory.
  Nothing writes to Vault without Peter's explicit request. (2026-10-23)
- What CAD says about quantities and materials is recorded as a claim and
  curated by the project; it is never silently trusted. (2026-10-22, 2026-10-23)
- Licence: 3-clause BSD, copyright Howard Hughes Medical Institute.
  (2026-11-10) This repository alone is GPL-3.0-or-later since 2026-11-13,
  the licence of Guix, so that its package definitions can be offered there.
- Hosting: GitHub. (2026-11-10)
- `mechanical-cad` holds the tools for writing and checking parts and doubles as
  the Guix channel for the mechanical CAD packages. (2026-11-10)
- Work that spans the repositories is run from an agent session rooted in
  `mechanical-cad`. (2026-11-10)
- A project repository has two top-level roots: `references/` for what mirrors
  Vault and `designs/` for what is authored in the repository. (2026-11-11)
- Directories are keyed by a readable name tied to the Vault master id, not by
  a mirror of Vault's folder tree. (2026-11-11)
- Files exported from Inventor are AP242. (2026-11-11)
- The goals and the order of work below are the plan: Peter found them
  reasonable when they were put to him. (2026-11-16)
- Reading from Vault is authorized for tests. Writing to it stays as above:
  at Peter's explicit request, each time. (2026-11-16)
- A part drawn in FreeCAD may sit beside a programmed one: the same
  directory, with the document as its source in place of the program and
  its parameters. (2026-11-16)
- The Windows agent may read and write files in the test folder Peter made
  in Vault for this work. Anywhere else in Vault, writing stays as above: at
  his explicit request, each time. (2026-11-17)
- The additions put to Peter on 2026-11-17 are wanted, all of them: a place
  for files that come from outside, parts built against other components,
  `bd_warehouse` packaged, the library of enclosure shapes, helpers for
  circuit boards, a path to a printed part, flat patterns, a preview that
  follows a part while it is written; and three more tasks for the Windows
  agent: the published file referenced from an Inventor assembly in the test
  folder, a revision as a new version of the same file, and the properties
  of the file published in October. The plan below orders them.
  (2026-11-17)
- A file from outside lives in `designs/parts/<key>/` as a third source of a
  part, beside the program and the drawn document. The two roots stay.
  (2026-11-17)
- A supplier's file may be in a public repository. (2026-11-17)
- The generator of a board's geometry files in `kicad-libs` may be used as
  it is, or changed to be of more use here. (2026-11-17)
- The second project, the one `mouse-joysticks-mech` holds a STEP export of,
  is not being worked on at the moment. It may serve as an example of a
  project exported from Vault and worked on with open tools. A mirror of it
  for testing may be made in the shared directory, where the Linux and the
  Windows agents both reach it. `mouse-joysticks-mech` itself is left alone
  unless Peter works on that project again. (2026-11-17)
- What a picture draws each part with, its finish, is one hand-edited file
  for the whole project, not a file in each part's directory. (2026-11-19)

## Repositories

| Repository | Owns |
| --- | --- |
| `mechanical-cad` | This document; the repository layout and its validator; tools for building parts from code and checking geometry; the Guix channel |
| `vault-cad-tools` | Everything specific to Vault and Inventor: the Windows scripts and the Linux side of the exchange |
| `mechanical-docs` | Inventories, assembly manuals, renders and viewer data generated from a project repository |
| One repository per project (`free-standing-tank-enclosure` first) | The project's geometry, metadata, curated records and published documents |

The shared directory used by the Linux and Windows agents is an unversioned
mailbox and evidence store. Decisions that last are written into a repository.
Its location is machine-specific and recorded in each checkout's ignored
`.agents/handoff.local.md`.

## Proposed: repository layout

One directory per Vault file, for parts and for assemblies, so the repository
maps one-to-one onto Vault.

- A part directory holds the STEP file, the facts recorded on Windows (Vault
  identity, version, lifecycle state, properties, material claim, parameters,
  holes and threads) and the facts computed on Linux (validity, extents, volume,
  a geometry fingerprint). Each file is written by exactly one command.
- An assembly directory holds a manifest of its direct children with their
  local placements. The flattened scene that the documentation reads is derived
  from these manifests, not stored.
- A part written as code has the same shape, with its program, parameters,
  checks and build receipt beside the STEP.
- Directories are keyed by a readable name tied to the Vault master id, so a
  rename or move in Vault does not rename anything here. The exporter on
  Windows identifies files by master id; the import command on Linux assigns
  the keys.
- STEP headers are normalised at export so an unchanged part exports to the same
  bytes. Geometry is compared by fingerprint, never by bytes alone.
- The lock file is an index derived from the directories, never a second copy
  of their facts.

The three choices this layout left open were decided on 2026-11-11 and are
under "Decided": two top-level roots, readable keys, and AP242 for the files
exported from Inventor. An AP242 file also holds the bodies that are hidden in
the native part, marked invisible; they are left out when a part is measured
and when it is drawn. The files tracked today are AP214 and stay so until the
re-export.

The detail, the evidence and the acceptance test are in
[layout-proposal.md](layout-proposal.md). A draft specification that implements
the two decided choices, with its validator, is in
[layout-specification.md](layout-specification.md); it stays a draft until the
enclosure has been converted and re-exported under it.

## Order of work (2026-11-16)

Of the order proposed on 2026-11-10, the layout, its validator, the
conversion of the enclosure, the Windows tests, the exporter and the
re-export are finished (2026-11-12), and the packages of OCP and build123d
are built (2026-11-13). Accepting this document and the first part written
as code are left. The numbers in brackets are the goals above.

1. **One real part through the whole loop** (6, 7, 9). A part the first
   project needs, not a box: written with build123d, with checks for how it
   meets the parts around it, seen while it is written, made, and measured
   against its STEP. What this needs and lacks is built for that part and no
   further: a check of fit against the mirrored assembly, a command that
   renders a part to an image, the file to make it from. It is the stretch
   of the loop that has never run, and it shows whether agents can design
   with these tools.
2. **Publishing as collaborators will meet it** (10, 11, 12), with that
   part: the publish commands on the new layout, the STEP referenced from a
   native assembly in a test folder, then a revision published as a new
   version of the same file. Every write to Vault is at Peter's request.
   Before it: the file's name in Vault, the wrapper part, and the Inventor
   requirement under "Not settled". The first of the three ran on
   2026-11-17: the monitor's reference model was added to the test folder
   and verified. The revision and the reference from an assembly are left;
   the revision has to be designed first, because nothing built so far
   checks a file out or in.
3. **Keeping a mirror current** (2, 3): change detection against Vault,
   read-only; a refresh tried on a real change; a second assembly imported,
   to meet what the exporter refuses. It needs Peter's word for reading
   from Vault and his decision on which files a project mirrors, and can run
   on Windows while step 1 runs on Linux.
4. **The manual finished from the bench** (5): Peter's notes and corrected
   instructions, one render at full quality, and the manual packages out of
   the project's tracked tree.
5. **A drawn part** (8): a FreeCAD document as the source of an authored
   part, with the STEP exported from it by a command. Decided and built on
   2026-11-16; what is left is a part of a project drawn that way.
6. **The packages offered to Guix** (13), once step 1 has shown they are the
   right ones and the licence question raised on OCP is clearer. CadQuery
   after that, when someone wants to write in it.

## Proposed: what else to package (2026-11-16)

- **Nothing more before a real part exists.** Guix has what the other goals
  need: FreeCAD (viewing, drawing, meshing), Blender and Typst (the manual),
  `ezdxf`, and `f3d` built with OpenCASCADE, a small viewer that reads STEP.
  `f3d` is to be tried in step 1, for a preview that follows the file while a
  part is written and for images an agent can look at; it has not been run
  here.
- **CadQuery later, on demand.** It makes the same OCP shape as build123d,
  so it adds a way of writing a part and no capability. It costs `casadi`
  and `runtype`, which Guix lacks, a newer `multimethod`, and VTK's Python
  modules.
- **For Guix itself**, what step 6 needs is in `.agents/PLANS.md`: the
  bindings generated in the build, lib3mf 2.4.1, fewer inputs. (Done on
  2026-11-19 but for the offering: "Built so far" below.)

## Proposed: tests with Inventor and Vault (2026-11-16)

The export from Inventor has been reviewed and run until two runs agree in
every file, and Inventor has read the files built here. More runs of either
on the same assembly would show little. What the goals rest on and nothing
has tested:

- a refresh after something changed in Vault (step 3), which is the
  operation of every working day once a project is mirrored;
- a published part revised and followed from an Inventor assembly (step 2),
  which is what a collaborator sees of all this;
- a second assembly (step 3), because every rule so far rests on one.

The first and third read from Vault, which Peter authorized for tests on
2026-11-16; they were asked of the Windows agent that day. The second writes
to Vault. Its first part, a dry run of adding an authored part to a test
folder Peter made, passed on 2026-11-16; on 2026-11-17 he allowed files to
be read and written in that folder, and the add itself ran and was verified
that day.

## Proposed: a library of enclosure shapes (2026-11-17)

Peter on 2026-11-17: a common problem of his is an enclosure around a circuit
board he has designed, of which he has a STEP file. Besides plain boxes he
likes polyhedra for enclosures, Platonic and Archimedean solids, a truncated
octahedron for one. He wants a library of such shapes as solids, shells and
frames with volume, to be machined, printed or folded from flat stock, and
parameterized so that a person or an agent sizes one to a board or to
another use. He was thinking about it then; later that day he said he
wanted it, and it is stage 3 of the plan below. Nothing is in the repository
yet.

A trial that day, in a scratch directory, with build123d as packaged here
and a truncated octahedron given by its 24 vertices and nothing else:

- the solid, with the volume of the closed form to twelve digits;
- a shell with the same wall at every face, made by moving every face in,
  not by scaling;
- a frame of 36 struts and 24 nodes as one solid;
- a flat pattern of the 14 faces that does not overlap itself;
- the smallest size that holds a box of given size with a clearance and a
  wall, which is a formula over the faces and needs no search.

So the geometry is not the hard part. What a first version could be:

- a table of polyhedra by vertex coordinates, the faces found as the convex
  hull: the five Platonic and thirteen Archimedean solids, prisms and
  antiprisms, a box being a prism. Each is tested against what is known of
  it: counts of vertices, edges and faces, equal edges, the volume;
- sized by an edge, by the distance across two opposite faces, by the
  sphere around it, or by what it has to hold: a box, or a STEP file with a
  clearance;
- forms: solid; shell, with faces left open or made lids; panels, one plate
  per face with mitred edges, for sheet stock; frame; flat pattern with its
  fold lines;
- used from a part's `build.py` like any other code, so that the part is
  checked, pictured and tested for fit like every authored part.

Not looked at yet, and where the work is: how the board is held and on which
face; openings for connectors, found from the board's STEP file; how the
enclosure opens and closes; the allowance for bends when folding; an export
for cutting (DXF or SVG). A search that day found no polyhedra library for
build123d or CadQuery; coordinates of these solids are published with the
`coxeter` Python package, to be read before a table is written here; the
enclosure generators found take dimensions, not a board's STEP file. None
of these was examined.

Peter pointed to FreeCAD's polyhedra add-on, which is installed on his
workstation: "Polyhedra", formerly "Pyramids-and-Polyhedrons", version
0.2.1, Python, GPL-3.0-or-later, so its code may be used here. Read and run
without a window the same day, in FreeCAD 1.1.3:

- it makes solids only, as objects of a FreeCAD document: the five Platonic
  solids, pyramids, a geodesic sphere, and a "Regular Solid" that truncates
  a Platonic solid by two numbers, with presets named for the thirteen
  Archimedean solids and their duals. Size is set by the inner, middle or
  outer radius or by an edge. No shell, frame, panels or flat pattern, and
  nothing that sizes a shape to what it holds;
- of the thirteen presets, five are exact to machine precision, the
  truncated octahedron among them (edges equal, the volume of the closed
  form). Six are close but not exact, their numbers being rounded: edges
  differ by 0.005 % to 0.24 %. Two are not the solid they name: "Truncated
  Dodecahedron" has edges of two lengths in the golden ratio, and
  "Truncated Cube" gives no shape at all ("Failed to create face from
  wire");
- so it serves two ways. Drawn by hand: a Regular Solid in FreeCAD, made a
  shell with Part's thickness tool, kept as a part's `part.FCStd`, which the
  layout takes already; not tried, and whether such a document rebuilds
  where the add-on is absent is not known. And as a second opinion: each
  solid of a table here can be compared with the add-on's where the add-on
  is exact. The tests named above (equal edges, the known volume) are what
  told its exact presets from the others.

## Plan: parts around other parts, enclosures for boards, pictures and motion (2026-11-17)

Peter on 2026-11-17 wanted all the additions put to him that day and asked
for a plan of them. He designs circuit boards in KiCad. He named two of his
repositories as examples: `mouse-joystick-pcb`, a board, and
`mouse-joysticks-mech`, a mechanical project of the kind he may later keep
in this layout. He renders such projects in Blender and would like animated
videos of them. He asked whether a board should have an interface file.

### What the two examples hold

Read that day; nothing in either was changed.

- **The board's files already say what an enclosure needs in the plane of
  the board.** The repository generates and tracks `board-geometry.json`
  (the outline, 100 x 80 mm with 5 mm corners; the thickness; four mounting
  holes of 3.2 mm; thirteen connectors and switches with their courtyards;
  a frame at the centre of the outline), `mechanical-datums.json` (the
  direction in which six connectors mate) and a STEP file of the assembled
  board. That is an interface file in all but name. **It lacks height**:
  nothing says how tall a connector is, or how far the board's parts reach
  above and below it.
- **The STEP file has the heights.** Read here with build123d: 703 solids in
  361 components, 16.6 mm above the board's top face and 2.4 mm below its
  bottom face. Its frame is not the geometry file's: it is KiCad's page with
  y reversed, and the geometry file records the offset between the two. Its
  components carry the names of footprints, not references such as J201.
- **The mechanical repository** is one STEP file of an assembly, exported
  from Inventor by a collaborator, with a registry that maps its parts to
  the nodes of a glTF model and gives each a finish, a scene file, and
  renders made from them in Blender. `mechanical-docs` has the same kind of
  pipeline for the manuals: a mesh of each part, Blender for the pictures, a
  viewer model assembled and exploded. Neither moves anything.

So the answer to the interface file is yes, and most of it exists: the
board's side keeps writing the facts it knows, and a command here adds what
only the solid model shows.

### Goals added

| | Capability | Shown by |
| --- | --- | --- |
| 14 | A file from outside is a component: a supplier's part, a circuit board | The example board and one supplier's part in a project, each with a record of where it came from, validating |
| 15 | A part is built against other components | A part that takes a board's shape as an input and is reported stale when the board changes |
| 16 | A component states its interface: the holes, faces, ports and keep-outs that other parts are designed to | The board's interface written from its files and agreeing with its STEP file |
| 17 | An enclosure for a board is generated: a shape from a library, sized to the board, with standoffs and openings where the interface says | The example board's enclosure as a box and as a polyhedron, each passing a fit check against the board |
| 18 | Goal 9 begun: a part is printed from a file a slicer has accepted, measured, and the record kept; flat stock is cut from a pattern | One enclosure printed and measured against its STEP |
| 19 | A project that begins as one STEP file of an assembly is kept in the layout | A copy of the mechanical example imported and validating, its scene equal to the file solid for solid |
| 20 | A project is pictured and animated from its records: finishes, views, joints and poses | A turntable, an exploded sequence and a moving joint of one project, as video |

### Stages

Each stage is built on the example board and no further than it needs. S, M
and L say how large a stage is beside the others.

**1. Components from outside, and parts built against them** (14, 15, 16;
here; M).

- 1.1 A third source of a part beside the program and the drawn document:
  the file itself as received, never edited, with `origin.json` saying where
  it came from (a supplier and a part number, or a repository, a commit and
  a path), its hash, the day, and whether it may be published. Such a part
  may be many solids. It may bring a display model from the same origin, for
  pictures. (As built, the file is the part's `part.step`: "Built so far"
  below.)
- 1.2 Inputs. A part names the components it is built against, and its
  program becomes `build(parameters, inputs)`, receiving their shapes and
  interfaces. The program still reads no file. The receipt records each
  input's hash, the validator reports a part whose input has changed, parts
  are built in the order of their inputs, and a circle is refused.
- 1.3 `interface.json`, optional for any part: named features in the part's
  own frame. A hole (centre, axis, diameter, depth), a face, an outline, a
  port (its extent, the direction something enters it, what that is), a
  volume to keep clear. Written by hand for an authored part, by a command
  for a board. The validator checks its form, and a check may hold it to the
  solid, a hole where a hole is stated.
- Done when each is shown on a fixture with tests, and the specification and
  the guide to adding a part say how.

**2. The board as a component** (14, 16; here; M).

- 2.1 A command that writes a board's `interface.json` from the board
  repository's geometry and datum files and its assembled STEP file: the
  outline, the thickness, the mounting holes, every connector with its
  extent in the plane, its height measured from the solids over its
  courtyard, its mating direction where the board's files give one, the
  highest and the lowest point of the board, and the board's solid model
  moved into the frame of the geometry file.
- 2.2 The interface held to the STEP file: the outline, a hole at every
  stated hole, the heights.
- 2.3 Put to the board's side, which is `kicad-libs` and Peter's to decide:
  that its generator write a height and a mating direction for every
  connector and name the STEP file's components by their references. Until
  then they are measured here.
- Which connectors must be reached from outside, and how much room a plug
  needs, are not facts about the board. They are parameters of the
  enclosure.
- Done when the example board at a named commit is a component with an
  interface in a project.

**3. What an enclosure is made of** (17; here; L).

- 3.1 `bd_warehouse` packaged in the channel: screws, threads, holes for
  heat-set inserts. It can be done at any time.
- 3.2 The library of shapes, as proposed above: a table of solids by their
  vertices; the forms solid, shell with faces left open or made lids,
  panels, frame and flat pattern; sized by an edge, a radius, a box to hold,
  or a board's interface with a clearance and a wall. Every solid tested
  against what is known of it, and against FreeCAD's add-on where that is
  exact.
- 3.3 The features of an enclosure as functions a part's program calls:
  standoffs under the mounting holes with holes for screws or inserts; an
  opening for a port, cut along its direction through whatever wall or lid
  is in the way; a body divided into two halves with a lip and screws.
- Done when each has tests and a picture.

**4. The first enclosure** (6, 7, 17; a project repository; M).

- 4.1 For the example board, as a plain box first: a base, a lid, and an
  assembly with the board in place. Its checks: no interference with the
  board, a stated clearance, a point in every opening that is empty and one
  in every standoff that is material. Pictures.
- 4.2 The same board in a polyhedron, a truncated octahedron for one.
- Done when both build, validate and pass their fit checks.

**5. Made and verified** (9, 18; here and at the printer; M).

- 5.1 A command that writes the file to print, checks the mesh against the
  solid, and has a slicer slice it (PrusaSlicer is in Guix), keeping what
  the slicer said. It needs the printer and the material.
- 5.2 The part printed and measured, the measurements kept beside the STEP,
  and the clearances that printing needs made parameters.
- 5.3 Flat patterns as DXF or SVG for panels cut from sheet, with fold lines
  for folded stock. The allowance for a bend is looked at then, starting
  with what FreeCAD's sheet-metal add-on does.

**6. A project that begins as one STEP file** (19; here; M).

- 6.1 A command that takes a STEP file of an assembly apart into the
  layout: a part for every distinct solid model, the assemblies with their
  placements, keys from the names in the file, one record of where the file
  came from. Nothing in it comes from Vault.
- 6.2 Tried on a copy of the mechanical example, and the scene built from
  the result compared with the file, solid for solid.
- 6.3 What that repository's registry holds (vendor numbers, datasheets,
  finishes, which board connector a part meets) set against the records of
  the layout. The repository itself is converted only when Peter says so.
- If the native files of such a project are in Vault, the mirror through
  Inventor is the better way in: it knows the identity of every file.

**7. Pictures and motion** (20; `mechanical-docs`, with records defined
here; L).

- 7.1 Records in the layout that a picture needs and CAD does not give
  reliably: the finish of each component, curated like quantities and
  materials; joints between components, an axis and its limits, and named
  poses; views. (The finish is built, as one file for the project; joints
  and poses are built as a draft outside the layout, for Peter to decide:
  "Built so far" below, and [joints-and-poses-draft.md](joints-and-poses-draft.md).)
- 7.2 In `mechanical-docs`, which has the meshes, the Blender stage and the
  exploded view already: a still of any view outside a manual, a turntable,
  an exploded sequence that follows the manual's steps, a joint moved
  through its range, each written as video. (All are built, the joint
  against the draft: "Built so far" below.)
- 7.3 The fit check run over the range of a joint, which the monitor arm
  needs. (Built against the draft, `tools/sweep_check.py`, and run on the
  mechanical example; not yet on the arm, which is not in the first
  project.)
- What this asks of the earlier stages is small: a supplied component may
  bring its display model (1.1), every solid keeps its name into the scene,
  which the layout does already, and colour is not put into STEP files,
  since a picture takes its finishes from a record.

**8. A preview that follows the file** (here; S): a short command that
opens the viewer on a part or a built assembly and reloads it when it is
built again. With stage 1 or 4.

**The Windows agent** (10, 11, 12; `vault-cad-tools`), beside all of the
above and independent of it:

- W1 The published STEP file referenced from an Inventor assembly in the
  test folder, and what Vault records of that relation.
- W2 A revision as a new version of the same file: designed first, the SDK
  members looked up without touching Vault, then built, run dry, run once,
  and the assembly of W1 seen to follow it.
- W3 The properties of the file published in October, to see whether the
  server fills in a lab the same way every time.
- Each begins with the offline rehearsal of the line corrected on
  2026-11-17.

### Order

Stage 1 first: it is small, and the board, the monitor arm and every
enclosure wait on it. Then 2, 3 and 4 in that order, with 3.1 whenever it
fits. Stage 5 when there is an enclosure to print. Stages 6 and 7 after the
first enclosure, or earlier if Peter wants pictures or the mechanical
repository sooner; neither depends on 2 to 5. The Windows tasks run beside
the rest, W1 and W3 first.

### For Peter to decide

Answered on 2026-11-17 and now under "Decided": where a supplied file lives,
that a supplier's file may be public, and that the board's generator in
`kicad-libs` may be used or changed. He also said that the native files of
`mouse-joysticks-mech` are in Vault, so that project can be mirrored through
Inventor as the first one was (stage 6, last line); the folder is in the
ignored notes of this checkout, not here. Still his to decide:

1. Where the first enclosure lives. Recommended: a new, small project
   repository with authored parts only, the board pinned by commit; the
   board's own repository and the mechanical one are left as they are.
2. How the first enclosure is made. Assumed: printed. Then which printer
   and which material.

   Peter on 2026-11-18, on 1 and 2: he may have an enclosure project that
   can be used for testing. Later that day he named it: the enclosure of
   the Farseer Eye in his repository `farseer-mech` "may be a good test
   project". That repository holds a brief written for this (its
   `enclosures/truncated-octahedron/cad-agent-handoff.md`): reproduce a
   reference model made with FreeCAD and its checks, then design a carrier
   for the board and the optics. The first two of its three sections were
   done that day in an ignored project of this checkout ("Built so far").
   He then said to move the model into `farseer-mech`, and it is there as
   `enclosures/eye/`, a project in this layout inside that repository,
   with targets in that repository's Makefile that hand its commands to
   this checkout. The third section was begun there the same day. Still
   his to say: the printer and the material.
3. Whether a published file should carry the lab of its project. Both
   published files carry the same lab, which is the lab of neither folder.
   Read on 2026-11-17: it is the property's default, the first entry of a
   list of 131, given to a file that has no value. A file gets its
   project's lab only if the property is written, which is a write to
   Vault of another kind than adding a file. Recommended: leave it, and
   decide when a file is published for a project and not for a test.
4. The live run of W1. Windows has reported what it adds to the test
   folder: two new files, `aw2725q-monitor-reference.ipt` (342 528 bytes)
   and `reference-pilot-01.iam` (113 152 bytes), each with a comment that
   names the pilot, the first declared to depend on the published STEP
   file and the second on the first. Nothing else is written; the STEP
   file gets no new version. Recommended: his word after the next Windows
   task, which rehearses the two adds offline and reads what Inventor's
   own add-in records for such a relation. If the run stops between the
   two, the wrapper part is in the folder and the assembly is not.
   Both are done (2026-11-20), and the read changes the recommendation:
   the add-in's relations carry three texts and the pilot's would carry
   none, one of the three being a number inside the parent file that
   nothing we have can read. Recommended now: before the live run, Peter
   checks one such pair into the test folder from Inventor himself, under
   other names than the pilot's, and one more read shows what the add-in
   records for exactly these two relations. The alternative is to run the
   pilot as it stands and see what Inventor and the Vault client make of
   two files whose relations say less than the add-in's.

Answered on 2026-11-17 and now under "Decided": the second project may be
mirrored for testing, in the shared directory. The mirror asked for is the
one assembly the mechanical repository holds as a STEP file, by its version
id, with what it uses; not the folder's three roots.

### Built so far

- **Stage 1** (2026-11-17): a supplied part (`add-supplied`, `origin.json`),
  inputs (`build(parameters, inputs)`, the receipt's `inputs`, the stale
  part reported, `build-order`), and `interface.json` held to the solid. One
  thing is not as first written above: the file is not kept twice. The
  part's `part.step` is the file as it came with its header normalised, its
  data section byte for byte what was received, and `origin.json` holds the
  hash of the file as received; there is no `supplied.step` beside it. A
  board's file is 12.8 MB, and a second copy would only repeat it.
- **Stage 2** (2026-11-17), 2.1 and 2.2: `tools/board_interface.py`. Run on
  the example board in a scratch project: the board found in the file with
  its frame at (137.425, -95.0), the four mounting holes empty in it, a
  solid over every one of the thirteen connectors and switches, their
  heights from 1.74 mm (the switches) to 16.58 mm (the RJ45), parts 16.585
  mm above the top face and 2.405 mm below the bottom. Found on the way: two
  of the file's 703 solids, the USB-C connector's, are not valid to the
  kernel; for a supplied part that is reported and not refused. The board's
  solid is 1.51 mm thick where its files say 1.6 mm. Six of the thirteen
  have a mating direction from the board's files; for the rest it is taken
  as away from the board, and the interface says so. 2.3, asking more of the
  board's generator, is not begun.
- **Stage 3.1** (2026-11-17): `bd_warehouse` 0.4.0 is in the channel and in
  the build123d manifest. Its own 1105 tests run in the build, about six
  minutes; three tests here make a screw, a clearance hole and a hole for a
  heat-set insert.
- **Stage 3.2** (2026-11-17): `mechanical_cad/shapes/`, written by a second
  agent from the trial above and reviewed here. `polyhedra` has the five
  Platonic and thirteen Archimedean solids, prisms, antiprisms and boxes by
  their vertices, with the faces found as the convex hull, and sizes one to
  hold a box behind a wall; `unfold` lays a solid out flat with its fold
  lines; `forms` makes the solid, the shell with faces opened, the frame,
  mitred panels and the flat pattern with build123d. The first two need no
  kernel.
  - Every named solid is held to what is known of it: its counts, equal
    edges, flat and convex faces, the closed-form volume to 1e-9, the
    rotations of its family, and a second derivation of its radius and
    volume from the faces around one vertex, without coordinates. That
    second derivation matters because the coordinates were written from
    memory, with no network to look them up.
  - Every solid the kernel makes is held to the volume worked out without
    it, and refused when they differ. That came from a finding: **the
    kernel's union of plain cylinders and balls is silently wrong in some
    positions**. A frame of the truncated octahedron resting on a hexagon
    came out as one valid solid with 0.06 % to 2.6 % of its volume missing,
    a dodecahedron's as four solids. So a frame is made of pieces that meet
    only in flat faces, and sizes at which the kernel cannot join them are
    refused with the reason. The frame of the trial above, which was one
    valid solid, was never checked for its volume.
  - Not there: an allowance for sheet thickness and bends in the flat
    pattern; sizing by the distance across two faces; and a flat pattern or
    a set of panels as a part, since the build command takes one shape with
    a solid.
- **Stage 3.3 and 4.1, a first cut** (2026-11-17): `mechanical_cad/
  enclosures.py` makes a plain box from a board's interface: a base with a
  standoff and an insert hole under each mounting hole, and a lid with a
  post and a counterbored screw hole over each and an opening above each
  port that is asked for. Four screws through the lid and the board into
  the standoffs hold the board and close the box, and the halves meet in a
  step that locates the lid. Tried on the example board
  in a scratch project, as two parts built against the board and an
  assembly: both build and pass their checks (a point in every standoff,
  hole, post and opening), and the fit check finds no interference with any
  of the board's 703 solids, three contacts (the halves, the board on its
  standoffs, the posts on the board) and 0.75 mm as the smallest gap that
  does not touch. A screw and an insert can be named, and their holes then
  come from `bd_warehouse`'s tables. That showed at once what typed-in
  numbers had hidden: the standard M3 insert is 5.7 mm long and needs 6.8
  mm of material, and the box's standoff and floor were 5.4 mm together; the
  generator now refuses that and says what to change, and the example has
  1.5 mm more room under the board. Not there yet: a home for the project,
  which is Peter's to say; until then it is kept in this checkout's ignored
  `tmp/mouse-joystick-box/`. Nothing has been printed.
- **Stage 4.2, a first cut** (2026-11-17): the same board in a truncated
  octahedron, with the library of stage 3.2: `polyhedron_halves` sizes the
  solid to hold the board with its parts, a clearance and a wall, divides
  the shell at the board's top face, and gives the halves the standoffs,
  posts, screw holes and openings of the box, each reaching to whatever
  wall is there. Two parts and an assembly in the kept project: they build,
  pass their checks, and do not interfere with the board. What it shows: a
  solid that is as high as it is wide is large around a flat board. For
  this board of 100 x 80 mm it has an edge of 52.5 mm, is 149 mm high and
  166 mm across its corners, and the standoffs are 66 mm long; the plain
  box is 107 x 87 x 28 mm. A cuboctahedron would be 111 mm high. A prism,
  which the library also has, would follow the board more closely. The
  halves meet flat, without a step.
- **Stage 4.1 and 4.2, three additions** (2026-11-17, later that day):
  - *Openings in walls.* A port that faces sideways or down gets a window
    through the wall on that side: the port's extent across its direction
    and the margin, from the port outwards, cut from both halves, in the
    box and in any other enclosure. Tested on a board with such a port,
    the volumes removed to the cubic millimetre. The example board has no
    such port: every connector on it faces up, so it does not show this.
  - *A step between the halves of any enclosure.* `halves` gives the base
    the box's lip: a ring half a wall thick that stands straight up from
    the cavity's outline at the board's top face, with the lid cut back
    over it. It is upright whatever the walls do there, so the lid lifts
    straight off; that is tested by lifting it. Where the walls lean
    inwards so much that less than a quarter of the wall would be left
    outside the cut, the lip is refused. The octahedron's halves in the
    kept project now have it.
  - *A prism.* `prism_halves(board, sides)` is a right prism on a regular
    polygon, with the box's heights and the smallest polygon of that many
    sides that holds the board with its clearance, turned whichever of two
    ways is smaller. The example board in a hexagon, two parts and an
    assembly in the kept project: 127 x 146 mm across and 28 mm high, no
    interference with the board, both meshes closed and manifold to the
    slicer. What it shows: a prism is as low as the box, and a regular
    polygon around a board of 100 x 80 mm is wider than the box, which is
    107 x 87 mm. A polygon that follows a rectangle, with unequal sides,
    is not built. (It is since 2026-11-19: below.)
- **Stage 5.1, the first half** (2026-11-17): `tools/print_file.py` and
  `make print` write the mesh to print a part from and check it: every edge
  shared by two triangles, the volume within 0.5 % of the solid's, the same
  extent; and PrusaSlicer, from Guix, is asked what it makes of the file.
  The two halves of the box: closed, 0.005 % and 0.002 % from their
  solids, and manifold to the slicer. It is not sliced: that needs the
  printer and the material, which Peter has not named. The part measured
  after printing, the other half of goal 9, is not begun.
- **Stage 5.3, the first half** (2026-11-18): `tools/cut_file.py` and
  `make cut` write the drawing to cut a plate from sheet and check it
  against the solid. The part has to be a plate cut square through: its
  volume is the area of its largest flat face times the distance to the
  face opposite, and its outline is straight lines and circles; anything
  else is refused, since it is not made in one pass. The outline is written
  as DXF in millimetres, in the part's own X and Y where the plate lies in
  them, then read back: its lines, arcs and circles have to join into
  closed loops, and the area inside the outer loop less the holes has to be
  the face's. Run on the first project's bowl frame: seven loops, 4.88 m of
  cut, the same area to sixteen digits. The same part gives the same file,
  which took two things: the DXF library's fixed metadata, and its class
  records added in order, because it writes them from a set and their order
  changed from one run of Python to the next. Not there: ellipses and
  splines, an allowance for the width of the cut, several parts on one
  sheet, fold lines, and so the flat patterns of `mechanical_cad/shapes/`.
  (Fold lines and flat patterns are there since 2026-11-19: below.)
- **A formed part, its tool and its frame, in the first project**
  (2026-11-18). Peter took up the bowls of the first project's brief,
  vacuum formed and clear, about 16 cm across and 2 cm deep, six to a
  monitor in a frame, and asked how such parts are made with these tools.
  As concepts in that project, every number of the bowl beyond those two
  assumed and marked so:
  - *The bowl* is a section turned about an axis, with its corners rounded
    about two centres so that the wall has one thickness. Its volume is held
    to the section's first moment, worked out without the kernel.
  - *The plug it is formed over is a part built against the bowl* (goal 15,
    for the first time in a project that is in a repository): the space
    inside the bowl's solid, enlarged by a shrinkage allowance, turned over
    and set on a base with vents. No dimension of the bowl is typed into it.
    Each step is held to a volume worked out another way, and that stopped
    the first build: the plug stood 0.105 mm into its base, because
    build123d's `scale` enlarges a shape about the origin it had before it
    was moved. A check of the finished part's size would not have shown it.
  - *The frame is built against three parts*: the monitor's lit area, from
    an `interface.json` the monitor's model was given (an outline, the first
    interface of a part that is not a board), the bowl's solid for the
    width of the holes, and the sheet under it for its outline. Its program
    refuses a layout that does not fit and says by how much; that is how
    the project learned that six such bowls fit one display with half a
    millimetre to spare.
  - An authored assembly of the monitor, the sheet, the frame and six
    bowls, checked for fit.
  - What it showed missing. **A project with two assemblies that nothing
    places has no default**: `assembly`, `open`, `built` and `flatten`
    without a key then ask for one, so adding an authored assembly broke
    the first project's `make assembly` and the script that flattens the
    scene of its manual, until the project named its mirrored root in its
    own Makefile and script. Proposed, not built: the layout lets a project
    name its main assembly. **A circle cannot be stated in an interface**:
    an outline is a polygon, so the bowl gives its opening as a point at its
    edge. And a picture of a section, which was made by hand in a scratch
    directory: `tools/picture.py` has no cut.
- **The Farseer Eye enclosure reproduced** (2026-11-18; sections 1 and 2 of
  its brief, by a second agent session and checked here; made in this
  checkout's ignored `tmp/` and moved that day, at Peter's word, into
  `farseer-mech` as `enclosures/eye/`, with a README of its commands). The reference is a truncated octahedron of 80 mm in two
  halves that print seam-down, with walls of 2 mm, roofs that lean at 45°
  towards a guide opening and four connector passages, a rib, and a board
  on the seam, generated with FreeCAD's Python interface.
  - Eight parts written with build123d and four assemblies. **The two
    halves and the two boards are the reference's solids**: no volume in
    one and not in the other, either way, for all four; the surfaces within
    1.2e-8 mm; the two assemblies match the reference's STEP files solid
    for solid. The rear half differs in volume by 7 parts in 10⁸, which is
    the integration's tolerance: its roofs are cut one at a time and come
    out as planes where the reference has splines.
  - The reference's own checks, repeated: one valid solid per half, the
    seam on the plate, 40 mm high; the large board 0.5 mm from the walls;
    no passage blocked; no face flatter than 45°; no material that starts
    in mid-air in 80 slices per half. **With the rib taken out both find
    the same island**, at 36.25 mm, 0.0664 mm² in area, while every face
    still passes the angle. The variant the brief asks for (90 mm, walls of
    1.5 mm, one passage fewer) gives the reference generator's solids and
    numbers.
  - A half's own frame is its print orientation, and the assembly turns it
    into place: the part's STEP file is then the file to print, and it
    compares directly with the reference's.
  - What it showed missing, each a proposal and none built: **numbers
    shared by several parts** (one study has one set of numbers and eight
    parts; a project script writes every part's parameters, checks and
    placements from one file, and a variant is a copy of the project);
    **code shared by parts** (only `build.py` is hashed, so a change in a
    module a program imports does not make the part stale); **no place for
    how a part is printed** (which way up, the process, the layer); **space
    that is kept clear** (an interface has boxes only, so the passages are
    parts placed as reference children and drawn like material); **what a
    fit check should find** (it lists contacts and gaps and cannot be told
    which are wanted); **comparing an authored part with a file from
    outside**; and pictures of a section and in colour.
  - **The third section, as a concept for joint review** (the same day, in
    `farseer-mech/enclosures/eye/`): a carrier built against the board's
    interface and seated on corbels added to the front half, an optics
    cartridge with the guide and a filter, the electrical side's first
    placement as a supplied part, and stand-ins named as assumed for what
    is not known. Twenty parts and eleven assemblies, 179 checks. The
    tools found two things a person would want to know before a board is
    laid out: the gap asked for between the guide and the detector leaves
    1.7 mm and less above the board where the placement has parts, and the
    rear half for the placement's ports has a piece of roof that starts in
    mid-air, which the print check found and a script of the project
    predicts from the numbers. The four things the brief asks to return
    are written by scripts into the project: a section with its
    dimensions as a drawing, a table of clearances and recesses, and
    coordinates for the board's designer.
  - **Options for the two findings** (the same day, while Peter was
    away): the rear half prints with one added vault, a void with no port
    whose ridge the project's script found by flooding the roof's underside
    from the walls, without the kernel, and the print check confirms; and
    the gap was built as six variants, which give the board's designer a
    table of what may stand where if the gap stays. Both are in the
    project's `review/options.md`.
- **Stage 5.1, a second screen before printing** (2026-11-18):
  `tools/print_check.py` and `make print-check` say whether a part prints
  as it lies in its own frame: what rests on the plate, every face that
  looks down flatter than an angle (45° unless given), measured by area on
  the trimmed face, and material that begins above the plate with nothing
  under it, found in thin slices every half millimetre. Faces that all pass
  the angle can still enclose such a start, where roofs meet from several
  sides; that is what the Farseer reference's rib is for. It needs FreeCAD
  alone. On the first project's forming plug it found twelve flat roofs of
  3 mm inside the vents; they are cones now and it passes.
- **Stage 5.1, corrected** (2026-11-18): the print file's deflection was
  not millimetres. build123d's `export_stl` hands its tolerance to the
  mesher as a fraction of each edge's size, so on a disc of 200 mm a "0.01"
  left the triangles 0.03 mm from the surface and the tool's own check of
  the mesh's extent failed. `tools/print_file.py` now calls the mesher with
  an absolute deflection. The enclosure halves of 2026-11-17 were small
  enough not to show it.
- **Two projects, each with one file of numbers** (2026-11-18). Peter asked
  that the bowls be quickly adjusted when the researcher answers. The first
  project now has `studies/bowls/study.json` and a script, Python alone,
  that writes the four parts' parameters, checks and interfaces, the
  assembly and a summary from it, refuses a layout that does not fit before
  anything is built, answers a what-if at once, lists which sizes fit, and
  writes a variant as a project of its own; one `make` command then builds,
  checks and fits everything. A variant with ten numbers changed went
  through with no other edit. The Farseer model has the same thing
  (`study.json`, `scripts/derive.py`), made independently the same day. So
  the first proposal under open decision 18, numbers shared by parts, has
  two working instances of the same pattern outside the layout: a study
  file, a derive script that is the one writer of the generated files, and
  checks worked out a second way without the kernel. What the layout would
  add is that a receipt knows of the study and that the validator says when
  a generated file is older than it.
- **A fault in `make fit`** (2026-11-18): the Makefile divided the subjects
  at spaces, so a child named "BOWL FRAME:1" or "TANK SUPPORT FRAME:1" was
  two names the assembly does not have. `tools/fit_check.py` now takes
  `--subjects "NAME,NAME"` and the Makefile hands SUBJECT on whole; a test
  uses the fixture's child whose name has a space. Found when the first
  project's `make bowls` was run through `make` for the first time; no
  test runs `make`.
- **Pictures cut open and in colour** (2026-11-18, while Peter was away for
  an hour and asked for as much as could be done). Both projects of that
  day had cut their assemblies open with scripts of their own, and every
  picture until then was one grey. `tools/picture.py` now takes `--cut +y`
  (what lies beyond the middle towards +Y is taken away; `--cut -x=12.5`
  names the place) and `--colour` (every part of an assembly in a colour of
  its own, the same part the same colour wherever it is placed), and `make
  picture` takes `CUT=` and `COLOUR=1`. The solids are placed as the
  project's records say, with build123d, cut, and written as a glTF model
  that the viewer draws, so an assembly need not be built first and the
  model can be opened in any viewer of such files. Colour stays out of the
  STEP files, as the plan has it. Two things had to be found: OpenCASCADE
  writes a material as a colour and nothing else, which a glTF reader takes
  for polished metal and draws nearly black, so the tool says in the file
  that it is not metal; and such a file has Y up, so the camera and the up
  axis are turned with it. The first project's whole enclosure, 155
  occurrences and 479 solids, is drawn in colour in three minutes. Not
  there: finishes curated by a project (stage 7.1), a section as a drawing
  with dimensions (the Farseer project writes one with a script of its
  own), and edges drawn as lines.
- **A section as a drawing** (2026-11-18): `tools/section.py` and `make
  section` draw what a plane cuts of a part or of an assembly, true to
  scale: an SVG file in millimetres, every part filled in the colour a
  picture gives it, with a scale and a legend, and beside it a record of
  the area the plane cuts of each part. It is what one sends to someone who
  has to judge a shape; a drawing program can measure in it and add
  dimensions. The first project's bowl is 196.798 mm2 in its plane of
  symmetry, twice what its program's section has, and the stack of
  monitor, sheet, frame and bowls shows at a glance what sits in what. The
  kernel gives the pieces of a cut in an order that changes from run to
  run; they are written in a settled order, and a test holds the drawing
  to the same bytes. Not there: dimensions written by the tool, hatching,
  and what lies behind the plane.
- **Stage 6** (2026-11-18, by a second agent session and checked here):
  `tools/take_apart.py`, with its rules in `mechanical_cad/takeapart.py`,
  makes a project of one STEP file of an assembly. Every product with
  geometry of its own becomes a supplied part, its shape written out in
  millimetres, with an `origin.json` that names the product and carries the
  hash of the file it was taken from; every product made of others becomes
  an assembly with its children under their usages' names, where the file
  has them. A product used several times is one part. Keys come from the
  products' names, numbered where two give the same; a file that is a
  single part and a placement that mirrors or scales are refused. The
  layout did not change, with two stretches of meaning that are Peter's to
  accept: for such a part `received_sha256` is the hash of the file it was
  taken from, not of a file of its own, and its `part.step` is the kernel's
  writing, not bytes as they came. Tried on a copy of the mechanical
  example (22.6 MB, exported from Inventor, products in inches and in
  millimetres in one file): 43 products became 37 parts and 6 assemblies in
  20 s; the project validates; its root, built again, has the file's 43
  products and 112 usages, and compared with the file all 152 solids are
  where the file has them, within 0.001 mm and 2e-4 of their volume. A
  second run changes no file. Not kept: the file's 24 colours. One part has
  faces and no solid; it is kept and placed. The sub-assembly that the file
  holds in two model states is two products of one name, and the second
  key is numbered. Not there: a record of the file for the project as a
  whole, colours, and telling products apart that are alike in shape. What
  that repository's own registry holds beyond geometry (vendor numbers,
  datasheets, finishes, the order of an exploded view, the mapping to its
  display model) has no place in the layout; it is the material of stage
  7.1. The project is in this checkout's ignored `tmp/`; the repository it
  came from was read and not changed, and is converted only when Peter
  says so.
- **Stage 7, begun: a project's finishes, and a picture outside a manual**
  (2026-11-19, after Peter chose one file for the whole project over a file
  in each part's directory).
  - **The record.** `finishes.toml` at the top of a project, hand-edited
    and TOML, the first file of the layout that follows that rule: named
    finishes, each a colour written as a colour picker gives it, how much
    of a metal the surface is, how rough, and how much it hides of what
    lies behind it; and under `[parts]` a finish for a part by its key,
    with an optional default for the rest. The validator refuses a key
    that is no part, a name that is no finish and an unknown field, and
    points out the parts that have no finish when the file names no
    default. One part has one finish. It is how a part looks in a picture
    and not the record of what it is made of
    (`mechanical_cad/finishes.py`; docs/layout-specification.md,
    "Finishes").
  - **Beside the scene, not in it.** The flatten step writes what the file
    says of a scene's parts as `finishes.json` next to `scene.json`. That
    is not what was put to Peter that morning, which had the finishes
    carried into the scene: `mechanical-docs` gates its meshes and renders
    on the scene's hash, and a changed colour would have asked for new
    meshes. The first project's scene, flattened with its finishes in
    place, has the hash its documentation is pinned to.
  - **`tools/picture.py --finish` and `tools/section.py --finish`** draw a
    part or an assembly with it, where `--colour` gives every part a
    colour of its own: one tells parts apart, the other shows what the
    thing looks like. A part without a finish is drawn plain and named.
    Three things had to be found. build123d takes a colour as sRGB and
    writes it into the model as light adds up. OpenCASCADE writes one
    material for each colour and nothing else of a finish, so every finish
    goes into the model under a colour that only says which it is, and the
    tool writes the finish in its place afterwards, with its name. And a
    metal shows its surroundings: with nothing around it the viewer drew
    aluminium darker than a grey plastic of half its brightness, so a
    model with finishes is drawn inside a plain light sky that the tool
    writes for the viewer. A section through a plane that only touches a
    solid stopped the section tool; it cuts nothing of such a solid now.
  - **In `mechanical-docs`** (by a second agent session, read here): the
    renderer draws a part in the look the project's `render.json` names
    for it, else in its finish, else in the default look; its receipt
    records what every part was drawn with, and a later run renders again
    only the views that show a part whose look changed. And
    `mechanical_docs/still.py` draws a scene alone, or one subassembly,
    from a named side, with no inventory and no instructions: the first
    item of 7.2. Its view names are those of `tools/picture.py`. One thing
    was found there: the studio of that renderer lights a face that looks
    up about seven times as brightly as its colour, which suits a manual's
    outlined pictures and turns a mid-grey finish white, so a still has an
    exposure of its own, and how a manual is exposed when a project has
    finishes is left to Peter.
  - **On the first project**: a draft `finishes.toml` that gives 31 of its
    43 parts a finish, each only where the part's name or the material CAD
    claims for it says what it is; the twelve without one are named by the
    validator, the two panels among them, whose colour no record has. The
    whole enclosure and the enclosure cut open were drawn with it by the
    viewer (the project's ignored `.cache/pictures/`): the framing reads as
    aluminium, the tanks and their platforms are seen through, the panels
    are plain. The renderer of `mechanical-docs` drew the same scene,
    flattened and meshed in a scratch directory (155 occurrences, 37 parts,
    every check passed): the whole enclosure in 10 s without outlines, 2.4
    million triangles being over its budget for them, and one tank support
    frame alone, the tank seen through, with outlines, in under four
    minutes; Cycles at preview quality.
  - **The colours of a file that is taken apart** (the same day, later).
    `tools/take_apart.py` kept no colour. It now reads them and writes the
    new project's `finishes.toml`: a file may colour a product, each of
    its solids and single faces, and a part has one finish, so every part
    gets the colour most of its surface has, named `colour-<rrggbb>`, and
    the report says how much of the surface that is. The file is written
    once and is a person's from then on: a later run leaves one alone that
    says something else. No colour goes into a part's own STEP file. On
    the mechanical example: all 37 parts get a finish, 12 finishes in all;
    three parts have several colours in the file and got the one that
    covers 64 to 76 % of them; the kernel reads back exactly the colours
    the file's text has. Run on the project made of that file on
    2026-11-18, it added the finishes and changed none of its 80 files;
    drawn with them, the motor mount plates are blue and the gears white,
    as in the collaborator's model.
  - **Moving pictures** (the same day, later; stage 7.2, in
    `mechanical-docs`, by a second agent session). `mechanical_docs/motion.py`
    draws three sequences from the directory a still is made from and
    writes each as frames, a video and a receipt: a turntable of the scene
    or of one subassembly; the top-level groups moving apart to where the
    manual's exploded view has them, and back; and, for a project with
    instructions, the steps in the manual's order, what each adds arriving
    at its seat. Blender writes the video itself, on both of its routes,
    and reads it back. On the first project, Cycles at preview quality:
    a turntable of one tank support frame, a turntable of the whole
    enclosure and its subassemblies moving apart and back, 72 to 95 frames
    each in three to five minutes; and its eighteen draft steps in their
    order, 19.5 s of video in two minutes with the faster engine. That is
    two of the three videos goal 20
    asks for; the third, a joint moved through its range, waits for joints
    as a record of the layout.
  - **A manual with finishes, for Peter to look at** (the same day). Six of
    the first project's views as its manual draws them today and with its
    finishes at three exposures, on one sheet in that project's ignored
    `.cache/pictures/`: at the manual's exposure light finishes stay white
    and black plastic comes out grey; a stop and a half darker the colours
    read and the pages stay light.
  - **Joints and poses, as a draft outside the layout** (the same day, a
    third round, at Peter's word to go on with as much of it as was
    recommended; he had said he was not sure what the words meant, and
    [joints-and-poses-draft.md](joints-and-poses-draft.md) is written to
    say it). A hand-edited `motion.toml` at the top of a project says
    which children of an assembly turn about a line or slide along one,
    how far either way from the assembled position, which joint follows
    another at a ratio as meshing gears do, and names positions.
    `mechanical_cad/motion.py` checks it against the project and works
    out, for a flattened scene, every joint as a line in the scene's
    frame and every occurrence that moves with the joints that move it,
    outermost first; `python3 -m mechanical_cad motion` writes that as
    `motion.json` beside `scene.json`. The validator does not read the
    record and the flatten step does not write the derived file: both
    wait for his word. Three tools use it. `tools/axes.py` lists the
    lines that round faces turn about, which is where a joint's numbers
    come from. `tools/sweep_check.py` is the fit check over a joint's
    range (7.3): the joint at thirteen values, what it moves compared
    with what stands still, the assembled position's own overlaps
    measured first and not held against the motion, and the free stretch
    around zero found to a thirty-second of a step. `tools/picture.py
    --pose` and `--at` draw an assembly with its joints moved.
  - **On the mechanical example** (its record written from the geometry
    and the names alone): `make axes` gave one lever unit's three lines
    at once, and walking five joints found what nobody had written down.
    Each unit turns on the base plate through 39° between the ends of
    its arc slot, 11.6° one way and 27.5° the other for the first and
    the mirror of that for the second, so both are assembled about 8°
    off the middle. The lever has a stop 10° one way, where its gear
    meets a post on the motor's plate, and none that the solids show in
    120° the other way. The stage's halves meet at once in one
    direction: the micrometer's tip is one solid with the half that
    carries it. Both gears have 70 teeth, so the motor's gear follows
    the lever's at -1, and walked together they kept their mesh. A walk
    takes one to seven minutes, and sixteen to twenty where the two
    gears are compared at every step.
  - **A part that is faces and no solid** showed there too: the
    example's switch. `tools/fit_check.py` and `tools/sweep_check.py`
    compare solids, and now name such parts as not compared.
    `mechanical-docs`' mesh stage refused the scene for it; it takes
    `--surface-parts KEY` now, which meshes a named part from its faces
    and records that, and is strict as before without it.
  - **A joint as video** (in `mechanical-docs`, by further agent
    sessions): `motion.py joint NAME` takes a joint from one limit to
    the other and back with what follows it, `pose A B` goes from one
    named pose to another, and `still.py --pose` draws one. Of the
    example: the lever with its two gears turning against each other,
    the unit turning through its slot, and a still with both units at
    their slots' ends, in that project's ignored
    `.cache/pictures/poses/`. Looked at here frame by frame: the gears
    mesh, the rod stays on its gear, the slot passes over the knob's
    screw from end to end. That is the third of the three videos goal
    20 asks for.
  - **Outlines on whole assemblies** (in `mechanical-docs`, the same
    day): Grease Pencil Line Art is built into the renderer behind
    `"lines": {"outliner": "freestyle" | "line-art" | "mixed"}`,
    Freestyle as before unless a project says otherwise. The first
    project's overview with outlines takes 14 s with the faster engine,
    where Freestyle took 32 minutes. The broken edges of the thin tank
    were not its wall: strokes were drawn without anti-aliasing, every
    face of a mesh was outlined as a patch of its own, and edges only
    marked sharp were drawn; all three are corrected. Whether the first
    project's manual uses it is Peter's, from
    `line-art-comparison.png` in that project's ignored
    `.cache/pictures/`.
  - **The earlier video code, read line by line**: four defects
    corrected in `mechanical-docs` (a looping sequence showed its first
    frame twice; the lights of a turntable of one subassembly went
    round another axis than the camera; a video from an earlier run
    stayed beside a receipt that did not describe it; the mesh stage's
    bare `--` failed with one argument).
  - Not there: joints and poses as records of the layout, and views at
    all; a finish for one solid of a part or for one occurrence; a
    manual drawn with a project's finishes; a project made of one STEP
    file saying which way is up (the example stands Y up and is taken
    as Z up, so every picture of it is told).
- **Vents, feet, a prism that follows the board, and flat patterns to
  cut** (2026-11-19, the smaller items of the plan, by a second agent
  session and looked at here). All four are settings and functions of
  what was there; the layout did not change.
  - **Vents**: `vents` in an enclosure's settings, fields of slots or round
    holes cut square through one wall of a box, a prism or a polyhedron's
    half, laid out without the kernel, with a margin to the edge of the
    wall's plain part and a web between openings. A field that does not
    fit, or that comes nearer than the web to a standoff, a post, the lip
    or a port's opening, is refused with the reason and the distance.
  - **Feet**: round bosses under the base, towards its corners. Bosses and
    not recesses, because the corners are where the standoffs' insert
    holes leave 0.6 mm of floor. A base with feet has to rest on them
    alone with its centre of mass between them. What it costs was
    measured: such a base no longer lies on its floor, and the print check
    fails it, where the same base without feet passes; it prints with
    support or gets stuck-on feet.
  - **The prism that follows a rectangular board** (`octagon_halves`): the
    board's rectangle grown by the clearance, each corner cut as far as
    the board's round corner allows. What it turned out to be: the box
    with each round corner replaced by its tangent flat. For the example
    board it is 106.8 x 86.8 x 28 mm like the box, with 0.1 % more
    footprint and 0.3 % more material, where the hexagon is 126.8 x 146.4
    mm and 40 % more material. So it saves nothing over the box; it gives
    flat walls all round, to vent, to cut from sheet or to fold.
  - **Flat patterns through the cut file**: `tools/cut_file.py --pattern`
    unfolds a part that is a convex solid with flat faces and writes the
    outline to cut and the fold lines on two layers, checked as the cut
    file checks itself: the outline closes, encloses the area of the
    solid's faces and is as long as the cut edges twice over, every fold
    runs from outline to outline inside it, and the file is the same bytes
    on a second run. Every named solid of the library unfolds to one
    simple outline from every one of its faces, 532 in all. No allowance
    for the sheet's thickness or a bend, no tabs.
  - Shown on the example board in the kept project: the board in the
    octagon, plain and with vents in the lid, the floor and a wall and
    four feet; 165 checks pass, nothing interferes, the four halves give
    closed meshes the slicer calls manifold. The six enclosure parts that
    were there build to the same bytes with the changed module.
  - **A second pass, the same day** (three more agent sessions and this
    one; each began by reading what the first had written, line by line).
    - *What the reading found.* In the enclosures: two vent fields in one
      wall kept only the later one's web; a round vent took a slot's
      sizes and ignored them; a triangular prism was refused its feet; a
      screw too large for its post surfaced as a lid in five solids.
      In the patterns: a fold line drawn along the outline was not
      found; an outline that touched itself was not refused; a solid
      with round edges too small to show in its volume passed as flat.
      Each has a test that failed first. No wrong geometry was found in
      about 2,500 vents compared with the built halves.
    - *Pockets for stick-on feet*: `"feet": {"kind": "recess", ...}`,
      round pockets in the underside of the floor, refused where they
      leave too little floor or come too near an insert, a port or a
      vent. The base then lies on its floor. The print check still
      failed it, on the pockets' roofs, because it knew no bridge:
      `tools/print_check.py --bridge MM` now lists a flat ceiling that
      is no wider than that where it is narrowest, with a wall under
      both ends, as a bridge and does not hold it against the part. On
      the example the base with pockets passes with `--bridge 9` (four
      ceilings 8.4 mm across) and the base with bosses fails as before.
      No width is assumed without the option.
    - *Vents*: `"stagger": true` sets every second row between the
      openings of the row before; and a field can lie on a round corner
      of the box, cut level along the corner's middle.
    - *The cut file*: it wrote arcs as arcs all along, which the plan
      had wrong. `--kerf MM` moves the outline outward and every hole
      inward by half the width of the cut, checks the drawing against
      the solid's face moved by as much, and refuses a cut that closes
      a hole or a slot. Found on the way: OpenCASCADE 7.9.3 misplaces
      the offset of a one-circle wire on a moved face; the allowance's
      own check caught it.
    - *A pattern of something open*: `--pattern --open +z` leaves out
      the faces that look squarely along an axis, and
      `Polyhedron.clipped` cuts a solid at a plane, so the outside of a
      polyhedron enclosure's half unfolds as a tray does. What
      `enclosures.halves` returns is still refused: walls, lip and
      standoffs are not sheet.
    - *A section as a drawing proper* (`tools/section.py`): `--hatch`
      hatches every cut face over its colour, neighbours told apart by
      angle and spacing; `--behind` draws, in thin lines beneath the
      cut, the edges seen behind the plane; `--arcs` writes a circular
      cut edge as an arc. The kernel's exact hidden-line projection
      draws the fixture in a tenth of a second and did not finish the
      mechanical example from one side in 45 minutes, so `--behind
      --quick` finds the edges on a fine mesh, in half a minute there.
      Without the options a drawing is byte for byte what it was. Met on
      the way and corrected: the area a plane cuts of a part in three
      or more pieces moved in its last digit from run to run, the kernel
      handing the pieces over in an order of its own.
  - Not there: louvres; a pocket's place chosen clear of the standoffs
    without being told; openings, a lip or flanges in a pattern, and
    the sheet's thickness; nothing has been printed, cut or folded.
- **Dimensions in a section** (2026-11-19): `tools/section.py --measure`
  writes a dimension into the drawing between two points of the model,
  taken into the plane: how far apart they are across the sheet, up it, or
  straight, with words beside the number and thin lines to the points. The
  ones across stand above the drawing and the ones up at its right; the
  record lists them with their values. Until then a section carried how
  wide and how high all that is cut is, and the Farseer project drew its
  own dimensions with a script.
- **The index, derived twice, compared** (2026-11-19): `vault-cad-tools`
  writes `vault-lock.json` when it imports and this repository derives the
  same index from the directories; they agreed on the first project and no
  test compared them. One does now, in `vault-cad-tools`
  (`tests/test_index_agreement.py`): a first import, a new version with a
  new file, and one file in two model states. They agree.
- **The Guix packages, to where they can be offered** (2026-11-19, by a
  further agent session on a copy, checked here before the module was
  changed). `python-ocp` no longer fetches the sources upstream
  generates for each release: the build generates them, from OCP's
  repository and the headers of Guix's own OpenCASCADE, with OCP's
  generator and the Python bindings of Clang 21, compiles them and
  writes the type stubs from the module. Generated here they have the
  same 319 submodules, 10268 names and 132708 class attributes as the
  fetched ones. It takes about thirty-five minutes on sixteen cores
  where compiling alone took twenty. With it: lib3mf 2.5.0, which
  build123d asks for, so that its patched binding and one deselected
  test go; `python-anytree` giving its version, so that build123d's
  requirement stands as upstream wrote it; the tests of two libraries
  run that were switched off; `python-ocp` compiled without debugging
  symbols and with three inputs fewer. On these packages build123d's
  own 2437 tests and bd_warehouse's 1105 pass, as before, and so do
  this repository's. Not done: offering anything to Guix, which is
  Peter's, and what the plan lists before that.
- **The Makefile is tested** (2026-11-18): `tests/test_makefile.py` looks at
  what each short command would run, with `make -n`, and runs none of it;
  `make` is in the base manifest for that. Written after two faults of the
  Makefile were found by hand that day, it found a third at once: a
  project whose path holds a space reached the tools in pieces, and is now
  refused with a sentence.
- **Stage 8** (2026-11-17): `make view PROJECT=DIR KEY=K` opens the viewer
  on a part or a built assembly and has it follow the file. The command is
  written and the viewer has the option; no window was opened from the
  agent's shell, so it is not tried.
- **The Windows tasks** (2026-11-17): one task of three reads, which wrote
  nothing to Vault and downloaded nothing; reviewed here against the
  server's raw answers.
  - The line corrected on 2026-11-17 counts files: rehearsed offline, nine
    cases of nine. It has not run against Vault.
  - W3 is answered. The server gave the file of October and the test file
    the same lab, and it is the lab of neither folder: the value does not
    follow the folder. Where it comes from was not read. Everything else
    the server chose is the same for both. So a published file does not
    get its project's lab by itself; if it should carry it, that is a
    property written after the add, and a question for Peter (above).
  - The folder of the second project, the one `mouse-joysticks-mech` holds
    a STEP export of: 27 files, three root assemblies. The assembly that
    repository holds is in it and is not a root, because a later assembly
    of the folder uses it. It has 14 versions; its closure is 41 files,
    none checked out, all in that lab's project and the common library, so
    it can be mirrored as the first project was, by its version id. One of
    the three roots is checked out by another user and reaches files of
    three other projects.
  - Which state the STEP file in `mouse-joysticks-mech` is: its header
    time lies 222 seconds after the check-out of version 13 of that
    assembly and 969 seconds before its check-in. It is an export of the
    working copy that became version 13. Version 14 is later, so a mirror
    made today would be newer than the repository's file.
  - For W2, the SDK was read without touching Vault: the connection's file
    manager can check a file out, check it in, and undo a check-out. A
    check-out is a write of its own, and a run that stops after it leaves
    the file checked out; the design has to say what then.
  - W1 is not begun.
- **The next Windows task** (asked on 2026-11-17, for Peter to start;
  nothing in it is written to Vault): the two script changes agreed with
  Windows; the definitions of the two properties the server fills in; the
  mirror of the second project for testing, acquired and exported, in the
  shared directory; and W1 up to the point where it would write: the
  published STEP file downloaded, a wrapper part and an assembly that
  reference it made in a scratch workspace, a dry run, and a report of
  exactly what a live run would add to the test folder. The route is the
  one `vault-cad-tools` designed and probed in October
  (`docs/native-checkin-adapter-design.md`, section 5): a wrapper part
  whose only content is the STEP file as a reference model, placed in an
  assembly, with both relations declared to Vault when the files are added.
- **That task, delivered and reviewed** (2026-11-18; 66 checks on Linux
  against the evidence, the mirror on the share and the raw answers of the
  day before; nothing was written to Vault: 5 sign-ins, 25 GET, 43
  downloads):
  - The two script changes are a patch, applied in `vault-cad-tools`. A
    file that is checked out is listed by a row that is not a version; the
    discovery says so and an acquisition refuses it. On Linux `sync-status`
    calls such a file `checked_out`.
  - The lab on a published file is the property's default (point 3 above).
  - **The second project is mirrored**: the one assembly and the 41 files
    it uses, at the versions read the day before, in the shared directory.
    **Its export stopped**, at the first guard to fire on real data: the
    root places one sub-assembly twice, in its primary model state and in
    a second one, and each state suppresses the parts of the other. One
    part has no body. What the package holds for model states and
    suppressed occurrences is decided in
    [exporter-package.md](exporter-package.md); the layout and the import
    needed no change, and the exporter is changed on Windows next.
  - **W1 is ready and was not run.** The wrapper part holds the STEP file
    by a name relative to itself, and the three files open with the link
    held after they are moved together to another place, which is what a
    Vault workspace needs. A live run adds two files (point 4 above).
- **The Windows task after it** (written on 2026-11-18; nothing in it is
  written to Vault): the two adds of W1 rehearsed against a stand-in; one
  read through the Vault client's library of what Inventor's add-in
  records for a relation between two files; the exporter with model
  states, run on the mirror of the second project; an acquisition that
  takes a file a colleague has checked out at its last version checked
  in; and the design of W2 read and corrected.
- **That task, delivered and reviewed** (2026-11-20, the day Peter's
  Windows laptop was back; 56 checks on Linux against the evidence and the
  mirror, none failed). Nothing was written to Vault and nothing was read:
  the one sign-in the task allowed failed and was not tried again.
  - **The two adds of W1 ran whole against a stand-in** for the Vault
    client's library, which was first held against the installed client by
    reflection. One line was wrong: a live run would have sent three empty
    texts with each relation where the request says nothing is sent.
    Corrected. Also seen: the connection is made with user id 0, which an
    add does not mind and a check-out may.
  - **What Inventor's add-in records for a relation is still not known.**
    The sign-in failed because the token of Autodesk's identity service on
    the workstation had run out and was being refreshed; the Vault client
    was not open. The read is asked for once more, with the client open.
  - **The exporter takes a file in two model states and names suppressed
    occurrences.** The second project passed every guard of that and
    stopped later, at the STEP file of a generated gear: a hidden surface
    that is also a member of a named group. **There is no package of it
    yet.** Decided on Linux that day
    ([exporter-package.md](exporter-package.md)): such a file is taken and
    the group left as it is (`mechanical_cad/stepfile.py`; measured on the
    file that stopped the export, one valid solid); and a part without a
    solid, which that project also has, is kept and says how many work
    surfaces it has. The first project exports as before, 89 of its 90
    files the same bytes.
  - **Found on Linux by reading the first `package.json` of the changed
    exporter**: the import compared its counts with the parts and the
    assemblies alone and would have refused it. Corrected in
    `vault-cad-tools`, with tests.
  - **A file a colleague has checked out** is taken at its last version
    checked in, rehearsed against a stand-in server and not yet run
    against Vault.
  - **The design of W2 was read**: nine remarks, all in the design now. Two
    change it: a check-out that is refused need not raise an error, and
    "checked out to this account" has to be read by the executor itself.
- **That next task, delivered and reviewed the same day (2026-11-20; 43
  checks on Linux, none failed).** Nothing was written to Vault and nothing
  asked of it by the task itself, for which the Vault client was not
  running. **The read was made after the delivery**, at Peter's word in
  the Windows session with his Vault client open: one sign-in through the
  Vault client's library and one read, nothing written. It showed what
  Inventor's add-in records for a relation: for the six files the second project's root uses directly, the add-in
  recorded the text `INVENTOR` as the source, the child's own Vault path as
  the expected path, and as the reference id a whole number that differs
  for each child and rises with the order in which the files came into
  Vault. Where the add-in takes that number from is not known; Inventor's
  programming interface was not found to give it. All six are references
  from an assembly to Inventor files; what the add-in records for a part
  that holds a STEP file was not seen. Delivered
  with the task: the Windows reader
  follows the rule for a named group and says the same as `stepfile.py` of
  every file; a part's work surfaces and the warning for a part without a
  solid; **the second project's package**, which the import takes and the
  kernel and the validator read (38 parts, 5 assemblies); the material and
  appearance of every part of both projects and the constraints, joints and
  degrees of freedom of the second project's assembly, read in Inventor;
  and the user id of the connection read from the session, rehearsed. Both
  patches are applied as delivered. The import holds a part's work surfaces
  to the rule of the Windows check. docs/exporter-package.md, "Not met on
  real data", has what the import showed, and what it did not: the assembly
  built from the records is not the STEP file Linux has of that assembly.
- **A third task that day, delivered and reviewed (17 checks on Linux,
  none failed), nothing sent to Vault.** Inventor's own STEP export of the
  second project's root from its mirror is the assembly the package's
  records describe: 153 of 153 solids where the records put them, and
  Inventor's occurrences are the package's, cell for cell. So the package
  of a project with a file in two model states, suppressed occurrences and
  a flexible instance is held against the CAD system's own file, as the
  first project's was on 2026-11-11, and the STEP file the mechanical
  repository holds of that assembly is another version or pose. With it
  came a page for Peter on checking one wrapper part and one assembly into
  his test folder from Inventor by hand (in the evidence on the share, not
  tried), and a line for the read in the Windows history.
- **The Windows task after that** (written on 2026-11-20; one sign-in
  through the Vault client's library and one read, nothing written): the
  Windows reader follows the rule for a hidden item in a group; a part's
  work surfaces; the second project exported; the read of what the add-in
  records, once more; and the user id of the connection corrected, as a
  change of its own.
- **W2, the design** (2026-11-17): written, not built
  (`vault-cad-tools/docs/update-step-file-design.md`). A revision is a new
  version of the same file: the request names the version the repository
  published last, and anything else found in Vault refuses it. It is two
  writes, a check-out that everyone sees and a check-in, so the journal
  gets a state for each place a run can stop, and an undo is sent only
  while nothing has been changed. Windows reads it before anything is
  built. One point is Peter's before the pilot: which changed file the
  pilot publishes over the test copy.

## Not settled

These are Peter's to settle. The direction above depends on each of them, and
none is decided. The working list, with what is known about each, is in
`.agents/PLANS.md`.

- **The Inventor requirement.** The enclosure's brief asks for design work in
  Inventor and finished records in Vault
  (`free-standing-tank-enclosure/README.md`). The decision above that new parts
  are written as code, and reach Inventor as referenced STEP files, has not
  been reconciled with that brief. Stage 6 of the loop depends on the answer.
- **Names in public files.** Whether server, host and account names, Vault
  paths and the names of people in exported files may stay in public
  repositories. Some are already published (layout-proposal.md, "Evidence").
- **Supplier models.** Whether component models that originate from suppliers
  may be redistributed in a public repository.
- **Where on GitHub** the repositories live, and with it the links between
  them.

## Out of scope

- Writing a graphical editor. (Keeping a part drawn in FreeCAD's is proposed
  above, goal 8.)
- A neutral parametric interchange format, or rebuilding Inventor's feature
  history from geometry.
- Two-way synchronisation of features between Inventor and code.
- Replacing Vault as the system of record for release state.
- Metrology-grade claims from scans or photographs.
- Converting drawings beyond PDF and DXF export.

Later, not now: a bridge to the KiCad tools for board and enclosure fit;
comparing scans with STEP; a shared library of purchased parts.

## Where the detail lives

- Synchronisation states, Vault metadata and keeping STEP as the referenced
  source in Inventor: `vault-cad-tools/docs/native-checkin-adapter-design.md`.
- Authoring and materials decisions: `vault-cad-tools/docs/authoring-and-materials.md`.
- What the documentation pipeline reads: `mechanical-docs/docs/input-contract.md`.
