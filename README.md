# mechanical-cad

Open-source tools for writing mechanical parts as code and checking their
geometry, the layout that project repositories use for STEP files and their
metadata, and a Guix channel for the mechanical CAD packages those tools need.

**Status (2026-11-19): the layout has a draft specification and working
tools, used on real projects; the direction is the plan the work follows.**
Peter has decided the layout's main choices (two top-level roots, readable
directory keys, AP242 for files exported from Inventor, a place for files
from outside, one file for a project's finishes) and found the goals and
the order of work reasonable; the direction document as a whole is not yet
accepted, and the specification is still a draft. What exists:

- a validator and a flatten step for the layout, standard-library Python;
- parts from a program (FreeCAD's `Part` module or build123d), from a
  document drawn in FreeCAD, or from a file that came from outside, each
  measured and held to its checks; parts built against other parts, and
  interfaces that say what a neighbour is designed to;
- enclosures for circuit boards, a library of polyhedra, and the files to
  make a part from: a mesh to print, a drawing to cut, a screen for whether
  a part prints as it lies;
- one STEP file and one FreeCAD document of a whole assembly, fit checks,
  pictures without a window, sections as drawings, and a project's
  finishes;
- a project made of one STEP file of an assembly;
- as a draft that the layout does not know yet, joints and poses: how the
  things of an assembly move, the fit check walked over a joint's range,
  and pictures with the joints moved
  ([docs/joints-and-poses-draft.md](docs/joints-and-poses-draft.md));
- a synthetic fixture and a test suite.

It has been used on the first project, an enclosure mirrored from Vault,
converted to the layout and merged on 2026-11-12; on an enclosure for an
instrument, reproduced from a reference model and extended; and on a
mechanical assembly that exists only as one STEP file. Nothing designed
with it has been made yet. `.agents/PLANS.md` has the state and
[docs/direction.md](docs/direction.md) where each goal stands.

The repository is also a Guix channel, with packages of the OCP bindings of
OpenCASCADE and of build123d, so that a part's program can be written with
build123d as well as with FreeCAD's `Part` module ("Guix packages" below).
CadQuery is not packaged.

## Start here

1. [Direction](docs/direction.md): the goal, what is decided, which repository
   owns what, the order of work and what is out of scope.
2. [Layout proposal](docs/layout-proposal.md): the proposed structure for STEP
   files and metadata, the evidence behind it and what is still unknown.
3. [Layout specification](docs/layout-specification.md): the draft that the
   tools implement.
4. Agents: [AGENTS.md](AGENTS.md), then [the living plan](.agents/PLANS.md).

## Commands

[docs/adding-a-part.md](docs/adding-a-part.md) walks through adding a part to
a project, programmed or drawn, with the short `make` forms of what follows.

`make` alone lists short forms of the commonest ones:

```sh
make test                              # the tests that need no FreeCAD; make test-cad runs all of them
make validate PROJECT=DIR              # check a project repository against the layout
make assemblies PROJECT=DIR            # the project's assemblies, and which are built
make assembly PROJECT=DIR [KEY=K]      # build one as a STEP file and a FreeCAD document
make open PROJECT=DIR [KEY=K]          # build it if need be, then open it in the FreeCAD window
```

A project repository's own Makefile can hand these to this one, so that inside
the project they need no parameter (`make assemblies`, `make assembly`); the
lines are in [the specification](docs/layout-specification.md#short-commands-in-a-project).
The commands in full follow.

Nothing below needs a CAD kernel:

```sh
guix shell --pure -m manifest.scm -- python3 -B -m mechanical_cad validate PROJECT
guix shell --pure -m manifest.scm -- python3 -B -m mechanical_cad assemblies PROJECT
guix shell --pure -m manifest.scm -- python3 -B -m mechanical_cad built PROJECT [KEY]
guix shell --pure -m manifest.scm -- python3 -B -m mechanical_cad flatten PROJECT --out NEW_DIR [--root KEY]
guix shell --pure -m manifest.scm -- python3 -B -m mechanical_cad check PROJECT
guix shell --pure -m manifest.scm -- python3 -B -m mechanical_cad add-supplied PROJECT KEY FILE.step --supplier S --part-number N --retrieved DAY --publishable yes
guix shell --pure -m manifest.scm -- python3 -B -m mechanical_cad build-order PROJECT [KEY ...]
guix shell --pure -m manifest.scm -- python3 -B -m mechanical_cad compare-scenes OLD/scene.json NEW/scene.json
guix shell --pure -m manifest.scm -- python3 -B -m mechanical_cad step-info FILE.step
guix shell --pure -m manifest.scm -- python3 -B -m mechanical_cad normalise-header IN.step OUT.step
guix shell --pure -m manifest.scm -- python3 -B -m mechanical_cad visible-only IN.step OUT.step
guix shell --pure -m manifest.scm -- python3 -B -m pytest -q tests
```

- `validate` checks a project repository against the layout and prints errors
  and findings.
- `assemblies` lists every assembly of a project, the top-level one and the
  sub-assemblies, with its key, its parts and occurrences, what it is part of
  and whether its built files are current. Any of them can be built by
  `assembly_step.py` below; this is how a person or an agent finds out which
  there are. `--json FILE` writes the list for a program.
- `built` prints the path of an assembly's built FreeCAD document (`--step`:
  of its STEP file) when it is current, and fails when it is not; `make open`
  uses it.
- `flatten` composes the per-assembly manifests into the `scene.json` that
  `mechanical-docs` reads, with a copy of the STEP files it names, and
  writes `finishes.json` beside it when the project has a `finishes.toml`:
  the one hand-edited file of a project that says what a picture draws each
  part with ([the specification](docs/layout-specification.md#finishes)).
- `check` evaluates each authored part's `checks.json` against its measured
  facts, and holds what its `interface.json` says to the solid: a hole is
  empty.
- `tools/print_file.py PROJECT KEY` writes the mesh to print a part from
  (`.cache/print/KEY.stl`) with a record beside it: that the mesh is closed,
  how its volume compares with the solid's, and, with
  `.guix/manifest-print.scm` in the environment, what PrusaSlicer says of
  the file. It does not slice: that needs a printer and a material.
- `tools/cut_file.py PROJECT KEY` writes the drawing to cut a part from
  sheet (`.cache/cut/KEY.dxf`, in millimetres) with a record beside it: for
  a part that is a plate cut square through, the outline of one face with
  its holes; that the drawing's lines, arcs and circles join into closed
  loops, and that the area inside them is the face's. A round corner or
  the round end of a slot is an arc in the file; a plate with an ellipse
  or a spline in its outline is refused, and so is a part with a pocket, a
  chamfer or a leaning wall. It needs build123d
  (`make cut PROJECT=DIR KEY=K`). `--kerf 0.2` (`KERF=0.2`) allows for a
  cut that wide: the outline is moved outward and every hole inward by
  half of it, the drawing is held to the solid's face moved by as much,
  and the record says the allowance; one that closes a hole or a slot is
  refused. With `--pattern` (`PATTERN=1`) it writes
  the flat pattern of a part that is a convex solid with flat faces, a
  polyhedron of `mechanical_cad/shapes/`, a box or a prism:
  `.cache/cut/KEY.pattern.dxf` with the outline on the layer `cut` and the
  fold lines on the layer `fold`, and a record with every fold's angle.
  Read back, the outline has to close, enclose the area of the solid's
  faces and be as long as the cut edges twice over, and every fold has to
  run from the outline to the outline inside it. It allows nothing for the
  sheet's thickness or a bend's radius and adds no tabs; `--root +x`
  (`ROOT=+x`) names the face laid first. `--open +z` (`OPEN=+z`, several
  as `+z,-y`) leaves out the face that faces that way: the pattern of a
  shell open there, a tray from a box or half of an enclosure from the
  solid it fills, with the edges round the opening cut once. The part
  stays the closed solid, and thickness and bends are allowed for no more
  than before.
- `mechanical_cad/enclosures.py` is not a command: a part's program calls it
  to make a plain box around a circuit board from the board's interface, a
  base with standoffs and a lid with posts and openings, or the same inside
  a polyhedron of `mechanical_cad/shapes/`, a prism on a regular polygon,
  or a prism that follows the board's rectangle with its corners cut
  (`octagon_halves`: as long, as wide and as high as the box, with flat
  walls all round).
  Ports that face up get a window in the lid, ports that face sideways one
  through the wall, and the halves meet in a step that locates the lid
  (docs/direction.md, the plan of 2026-11-17). Two settings add to any of
  them. `vents` is a list of fields of slots or round holes, each cut
  square through one wall, the lid's plate, the floor or a named side; a
  field keeps a margin from the edge of the wall's plain part and a web
  between its openings, and is refused, with the reason, when it does not
  fit or comes too near a standoff, a post, the lip or a port's opening.
  `"stagger": true` sets every second row of a field between the openings
  of the row before it, and a direction halfway between two walls of the
  box, `[1, 1, 0]`, names the round corner there, which is cut along its
  middle.
  `feet` puts round bosses under the base, one towards each corner or
  where `at` says, never under a vent or a port's window; the base has to
  rest on them alone with its centre of mass between them, which
  `enclosures.standing` says of any solid. A base with feet no longer lies
  on its floor, so it prints with support, and the print check says so.
  With `"kind": "recess"` the feet are pockets in the underside for feet
  that are stuck on, placed the same way and kept clear of the holes for
  the inserts, the vents and too thin a floor: such a base lies on its
  floor, and the print check reports the roofs of its pockets, four
  bridges of 8.4 mm for feet of 8 mm, and nothing else.
  What is cut and what is added is held to a volume worked out without the
  kernel.
- `mechanical_cad/shapes/` is a library of polyhedra for a part's program:
  the Platonic and Archimedean solids, prisms, antiprisms and boxes by their
  vertices, sized by an edge or to hold a box, as solid, shell, frame,
  mitred panels and flat pattern.
- `add-supplied` puts a STEP file from outside into a project as a part: a
  supplier's model, or a circuit board's from its own repository (`--repository
  URL --commit HASH --path PATH` in place of the supplier). The file is kept
  as it came, with its header normalised, and `origin.json` records where it
  came from and whether it may be published.
- `tools/take_apart.py ASSEMBLY.step NEW_PROJECT` makes a project of one
  STEP file of a whole assembly, for a design that exists only as such a
  file: every product with geometry of its own becomes a supplied part
  (its shape written out in millimetres, with `origin.json` saying which
  product of which file it is), and every product made of others an
  assembly with its children under their usages' names, where the file has
  them. A product used several times is one part placed several times. Keys
  come from the products' names; a single part, and a placement that
  mirrors or scales, are refused. It needs the OCP bindings (`make
  take-apart FILE=... PROJECT=... ORIGIN='...'`). Measure the result with
  `step_facts.py`, build its root with `assembly_step.py -- --frame own` and
  hold it against the file with `compare_assembly_step.py`: every solid has
  to be where the file has it. The file's colours become the project's
  finishes: every part gets the colour most of its surface has, in a
  `finishes.toml` that is written once and is a person's to edit from then
  on. No colour goes into a part's own file.
- `build-order` prints the authored parts so that each comes after the parts
  it is built against: a part's `parameters.json` may name other parts as
  `inputs`, and its program then receives their solids and interfaces.
- `compare-scenes` says whether two flattened scenes are the same assembly.
  With `--other-export`, STEP files that differ are listed, not counted: use
  it with `compare_step_exports.py` when a project was exported again in
  another protocol.

These run in FreeCAD. The three that record a measurement need the OCP
bindings beside it (`.guix/manifest-build123d.scm`, "Guix packages" below);
the two about whole assemblies need FreeCAD alone (`.guix/manifest-cad.scm`):

```sh
B3D="guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm --"
$B3D FreeCADCmd tools/step_facts.py --pass PROJECT
$B3D FreeCADCmd tools/build_part.py --pass PROJECT/designs/parts/KEY
$B3D FreeCADCmd tools/board_interface.py --pass PROJECT/designs/parts/KEY BOARD-GEOMETRY.json [DATUMS.json]
$B3D FreeCADCmd tools/compare_step_exports.py --pass PROJECT MAP.json NEW_REPORT.json
$B3D python3 -B tools/take_apart.py ASSEMBLY.step NEW_PROJECT --retrieved DAY --publishable yes --description TEXT
$B3D python3 -B -m pytest -q tests
guix shell --pure -m .guix/manifest-cad.scm -- FreeCADCmd tools/assembly_step.py --pass PROJECT [KEY]
guix shell --pure -m .guix/manifest-cad.scm -- FreeCADCmd tools/compare_assembly_step.py --pass PROJECT KEY OTHER.step NEW_REPORT.json
guix shell --pure -m .guix/manifest-cad.scm -- FreeCADCmd tools/print_check.py --pass PROJECT KEY [-- --up +Z] [-- --angle 45] [-- --step 0.5]
guix shell --pure -m manifest.scm -m .guix/manifest-cad.scm -- python3 -B -m pytest -q tests
```

Volumes, areas and centres of mass that are recorded are measured with
OpenCASCADE's adaptive integration, through the bindings. FreeCAD's own
`Volume` is the kernel's plain integration, which was 0.8 % low for one part
of the first project. Without the bindings the measuring tools say so and
write nothing, and the tests of them are skipped.

- `compare_step_exports.py` measures other exports of a project's parts (an
  AP242 export of a part tracked as AP214, an export from another session) and
  says whether each is the same geometry as the tracked file.
- `picture.py` makes pictures of a part or of a built assembly without a
  window, with the `f3d` viewer (`.guix/manifest-view.scm`; `make picture
  PROJECT=DIR KEY=K`): something to look at for a person or an agent, into
  the project's ignored `.cache/pictures/`. A view says where the camera
  stands (`iso`, `iso-back`, `below`, `+x` and so on), `--up` which axis
  points up. A check passes on a shape that is wrong in a way only a picture
  shows, so look at what was built.
  `--cut +y` takes away what lies beyond the middle towards +Y (`--cut
  -x=12.5` what is below X = 12.5) so that the inside shows, and `--colour`
  gives every part of an assembly a colour of its own. Both need build123d
  beside the viewer and put an assembly together from the project's records,
  so it need not be built first (`make picture PROJECT=DIR KEY=K CUT=+y
  COLOUR=1`). `--finish` in place of `--colour` draws every part with the
  finish the project's `finishes.toml` gives it, its colour, how much of a
  metal and how rough it is and how much it lets through, in plain
  surroundings so that a metal looks like one (`FINISH=1`); a part that is
  given no finish is drawn plain and named.
- `section.py` draws what a plane cuts of a part or of an assembly, true to
  scale: an SVG file in millimetres with every part filled in the colour a
  picture gives it, a scale and a legend, and beside it a record of the
  area the plane cuts of each part (`make section PROJECT=DIR KEY=K
  CUT=+y`; `CUT=-x=12.5` names the place). It needs build123d and puts an
  assembly together from the project's records. With `--finish` (`FINISH=1`)
  the parts are filled in the colours of their finishes and the legend names
  them. `--measure "across X,Y,Z X,Y,Z words; up X,Y,Z X,Y,Z"`
  (`MEASURE='...'`) writes dimensions into the drawing between points of the
  model: how far apart two points are across the sheet, up it, or straight,
  each with thin lines to its points and its value in the record.
  `--hatch` (`HATCH=1`) hatches the cut faces over their colour, parts side
  by side differently; `--behind` (`BEHIND=1`) draws in thin lines the edges
  seen behind the plane, by the kernel's hidden-line removal on the exact
  surfaces, which takes minutes or more on an assembly of many parts, and
  with `--quick` (`BEHIND=quick`) on a mesh, which takes seconds; `--arcs`
  (`ARCS=1`) writes circular cut edges as arcs. The record says what each
  added.
- `fit_check.py` says whether some children of an assembly fit among the
  others. For an assembly KEY, usually an authored one that places what is
  mirrored together with what is being designed, and the names of the
  children in question, it compares every solid of those children with every
  other solid of the assembly and reports what interferes (shared volume),
  what touches and what is closer than a clearance, with the smallest
  clearance that is left. It needs FreeCAD alone.
- `sweep_check.py` is the fit check over the range of a joint, and
  `axes.py` lists the lines that round faces turn about, where a joint
  could be. Both belong to a draft that the layout does not know yet,
  joints and poses in a project's `motion.toml`
  ([docs/joints-and-poses-draft.md](docs/joints-and-poses-draft.md)):
  `make sweep PROJECT=DIR KEY=K JOINT=NAME` sets the joint to thirteen
  values across its range, moves what it moves, compares that with
  everything that stands still, and prints the stretch around the assembled
  position that is free and what blocks it at either end; `picture.py
  --pose NAME` (`POSE=NAME`) draws an assembly with its joints where a pose
  puts them; `python3 -m mechanical_cad motion PROJECT` checks the record
  and writes `motion.json` beside a flattened scene, for `mechanical-docs`
  to make a video of a joint from. All need FreeCAD alone but the picture.
- `print_check.py` says whether a part prints as it lies in its own frame,
  growing along +Z from its lowest point, or along the axis `--up` names
  (`make print-check PROJECT=DIR KEY=K`). Three screens: the flat faces that
  lie on the plate; every face that looks down at less than 45 degrees above
  the plate, a curved face measured over the part of it that does; and
  material that starts in mid-air, found by cutting the part into slices
  every 0.5 mm and asking of every piece of a slice whether it lies over
  the slice before. Roofs that all pass the angle can still enclose such a
  piece where they meet from several sides. With `--bridge MM` (`BRIDGE=8`)
  a flat ceiling that is no wider than that where it is narrowest, with a
  wall under both ends, is listed as a bridge and not held against the
  part: the roof of a pocket for a stick-on foot, of a slot. No width is
  assumed without it. The record goes beside the
  print file (`.cache/print/KEY.check.json`). It is a screen of the
  geometry, not a slicer's verdict; it needs FreeCAD alone, and takes a STEP
  file in place of a project and a key.
- `assembly_step.py` builds one STEP file and one FreeCAD document of a whole
  assembly (KEY, one of the keys `assemblies` lists, or the only assembly
  nothing places) from the part files and
  the placements, into the project's ignored `.cache/assemblies/`: the way to
  look at an assembly in FreeCAD or hand it to someone. Instances of a
  sub-assembly that are alike are one product in the STEP file, named after
  the assembly's file, and every usage carries its occurrence's name; in the
  FreeCAD document each instance can be hidden by itself. It reads
  its file back and checks every solid against the flattened scene. The FreeCAD document
  opens with the assembly shown and in view and the part files it links to
  hidden. The files carry positions and shapes, not constraints, features or
  colour; the part files and manifests stay the source.
- `compare_assembly_step.py` says whether another STEP file of a whole
  assembly, such as the mirrored CAD system's own export of its assembly
  document, holds every solid where the project's records put it.
- `step_facts.py` measures every STEP file that nothing here builds, the
  mirrored parts and the supplied ones (validity, solids, volume, area, centre
  of mass, bounding box), and writes `facts.json` beside it. A file measured
  with another tool, or another integration, is measured again.
- `board_interface.py` writes the `interface.json` of a circuit board that is
  a supplied part: the outline, the mounting holes and the connectors from
  the geometry file the board's repository generates, and from the solid
  model how high each connector stands and how far the board's parts reach
  above and below it. It refuses a model that is not that board: every
  mounting hole has to be empty in it.
- `build_part.py` builds an authored part from its source: `build.py` and
  `parameters.json`, or `part.FCStd`, a document drawn in FreeCAD (the one
  object in it that has a solid and that nothing else uses is the part; the
  document is opened and computed again, never saved). It writes the STEP
  file, a receipt and the facts. Building an
  unchanged part again changes no file. `build.py` returns a `Part.Shape` of
  FreeCAD or a shape of build123d; for the second, run the tool in the
  environment of "Guix packages" below. FreeCAD writes and measures the file
  either way, and the receipt names the library that built the shape.

FreeCADCmd reads dashed options itself, even after `--pass`; put a bare `--`
before a script's own options (`--pass PROJECT -- --force`). It also exits 0
after an uncaught exception, so each script prints its own status line.

`tools/conversion_acceptance.py` runs the acceptance test for converting an
exporter's package into the layout.

`tools/update_shared_clone.py LOCAL_CHECKOUT SHARED_CLONE` fast-forwards a
clone that lives on a filesystem where git cannot write safely (the network
share the Windows agent fetches from) to the commit of a clean, pushed local
checkout, by copying a pack, the refs, the changed files and the index.

## Guix packages

`.guix-channel` makes this repository a Guix channel whose package module is
`.guix/modules/orb-weaver/mechanical-cad/packages.scm`. It fits the Guix the
repository is used with: OpenCASCADE 7.9.3 and Python 3.12.

| Package | What it is |
| --- | --- |
| `python-ocp` 7.9.3.1 | The OCP bindings of OpenCASCADE, generated in the build from OCP's repository and the headers of Guix's own OpenCASCADE, then compiled, with the type stubs written from the module. Its check builds a box, measures it and sends it through a STEP file |
| `python-pywrap`, `python-clang-21`, `python-pybind11-stubgen-for-ocp` | What generates them: the generator OCP is made with, the Python bindings of the libclang it needs, and the fork of the stub writer OCP is released with |
| `python-build123d` 0.12.0 | build123d, the last release for OpenCASCADE 7.9. Its own tests run in the build |
| `python-ocpsvg`, `python-ocp-gordon`, `python-svgpathtools`, `python-trianglesolver`, `python-bd-materials`, `python-threejs-materials`, `python-pygltflib`, `python-dataclasses-json`, `python-lib3mf`, `lib3mf-2.5` | What build123d needs and Guix does not have, or has in an older release |

Nothing builds these for you: the first use generates and compiles the
bindings, about thirty-five minutes on sixteen cores (seventeen to
generate, fourteen to compile, two for the stubs), and an update of Guix
that changes Python, OpenCASCADE, VTK, pybind11 or Clang does it again.
Until 2026-11-19 the generated sources were fetched from upstream's
release; generated here they give the same 319 submodules and 10268 names,
and build123d's 2437 tests and bd_warehouse's 1105 pass on them as before.

Without adding the channel:

```sh
guix shell --pure -L .guix/modules python python-build123d -- python3 PROGRAM.py
guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm -- FreeCADCmd tools/build_part.py --pass PROJECT/designs/parts/KEY
guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm -- python3 -B -m pytest -q tests
```

`.guix/manifest-build123d.scm` is the FreeCAD role with build123d added;
`make test-build123d` runs the last line. What each definition changes
against its upstream, and why, is written beside the change. Three of them
stand for changes to Guix's own packages and say so. They have not been
offered to Guix; `.agents/PLANS.md` lists what is left before that.

## Related repositories

- `vault-cad-tools`: exchange with Autodesk Vault and Inventor, and the import
  command that writes the layout.
- `mechanical-docs`: inventories and assembly manuals from a project repository.
- `free-standing-tank-enclosure`: the first project and the test case.

## Licence

Copyright © 2026 Howard Hughes Medical Institute.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version. It is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
A PARTICULAR PURPOSE. See [LICENSE](LICENSE) for the licence.

The repository was under the 3-clause BSD licence until 2026-11-13. GPL-3.0-or-later
is the licence of Guix, so the package definitions here can be offered to it.
The related repositories keep their own licences; they run this one's
programs and copy none of its code.
