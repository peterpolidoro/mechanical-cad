# Direction

**Status: proposal, drafted 2026-11-10 from Peter's statements. Not yet accepted.**
Sections marked *decided* record what Peter has already settled, with the date.
Sections marked *proposed* are waiting for a decision.

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
  authoring tool unless a collaborator insists. (2026-10-23)
- An assembly is per-part STEP files plus a placement manifest, never a single
  assembly STEP as the source. (2026-10-23)
- Linux controls the workflow. Windows performs only the Vault and Inventor
  operations, through validated request and result files in a shared directory.
  Nothing writes to Vault without Peter's explicit request. (2026-10-23)
- What CAD says about quantities and materials is recorded as a claim and
  curated by the project; it is never silently trusted. (2026-10-22, 2026-10-23)
- Licence: 3-clause BSD, copyright Howard Hughes Medical Institute. (2026-11-10)
- Hosting: GitHub. (2026-11-10)
- `mechanical-cad` holds the tools for writing and checking parts and doubles as
  the Guix channel for the mechanical CAD packages. (2026-11-10)
- Work that spans the repositories is run from an agent session rooted in
  `mechanical-cad`. (2026-11-10)

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

Open choices: two top-level roots (`references/` for Vault's authority,
`designs/` for the repository's) or one tree with an authority field; readable
keys or a mirror of Vault's folder tree; AP214 or AP242 (to be tested, not
assumed).

The detail, the evidence and the acceptance test are in
[layout-proposal.md](layout-proposal.md). A draft specification that implements
the recommended choices, with its validator, is in
[layout-specification.md](layout-specification.md); it is provisional until the
choices are made.

## Proposed: order of work

1. Accept or amend this document.
2. Write the layout as a specification with a validator, here.
3. Convert the enclosure's existing snapshot into the layout on a branch, on
   Linux alone, and require the scene flattened from it to equal today's, part
   for part and placement for placement.
4. Run the read-only Windows tests that settle the open choices: AP214 against
   AP242, header stability on more parts, lifecycle state and revision, and what
   Inventor reports for parameters, holes and threads. Run on 2026-11-10; the
   results are in layout-proposal.md.
5. Change the Windows exporter to write the layout, re-export the enclosure and
   compare it with step 3. Render the manual once from the result and compare
   it with today's. Merge the branch.
6. Build the first code-authored part with the tools here and publish it to
   Vault.
7. Package OCP, build123d and CadQuery in the channel.

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

- A graphical editor.
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
