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
| 3 | A second assembly or project goes through the same commands | **Done once** (2026-11-16), as a test: a second root assembly was acquired, exported, imported, measured, validated and built, with no change to a command. No guard of the exporter has yet stopped a run on real data |
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
  bindings generated in the build, lib3mf 2.4.1, fewer inputs.

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
  poses; views.
- 7.2 In `mechanical-docs`, which has the meshes, the Blender stage and the
  exploded view already: a still of any view outside a manual, a turntable,
  an exploded sequence that follows the manual's steps, a joint moved
  through its range, each written as video.
- 7.3 The fit check run over the range of a joint, which the monitor arm
  needs.
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
  1.5 mm more room under the board. Not there yet: openings in a wall for
  ports that face sideways, and a home for the project, which is Peter's to
  say; until then it is kept in this checkout's ignored
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
- **Stage 5.1, the first half** (2026-11-17): `tools/print_file.py` and
  `make print` write the mesh to print a part from and check it: every edge
  shared by two triangles, the volume within 0.5 % of the solid's, the same
  extent; and PrusaSlicer, from Guix, is asked what it makes of the file.
  The two halves of the box: closed, 0.005 % and 0.002 % from their
  solids, and manifold to the slicer. It is not sliced: that needs the
  printer and the material, which Peter has not named. The part measured
  after printing, the other half of goal 9, is not begun.
- **Stage 8** (2026-11-17): `make view PROJECT=DIR KEY=K` opens the viewer
  on a part or a built assembly and has it follow the file. The command is
  written and the viewer has the option; no window was opened from the
  agent's shell, so it is not tried.

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
