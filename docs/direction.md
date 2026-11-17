# Direction

**Status: proposal, drafted 2026-11-10 from Peter's statements. Not yet accepted.**
Sections marked *decided* record what Peter has already settled, with the date.
Sections marked *proposed* are waiting for a decision. The goals and the order
of work were written on 2026-11-16, when Peter asked for a plan of the whole
project, and he accepted them that day; the two sections after them are
proposals.

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
another use. He is thinking about it; nothing is decided and nothing is in
the repository.

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
