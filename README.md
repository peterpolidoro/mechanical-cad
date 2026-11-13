# mechanical-cad

Open-source tools for writing mechanical parts as code and checking their
geometry, the layout that project repositories use for STEP files and their
metadata, and a Guix channel for the mechanical CAD packages those tools need.

**Status (2026-11-11): the direction and the layout are proposals; the layout
has a draft specification and working tools.** Peter has decided the layout's
three open choices (two top-level roots, readable directory keys, AP242 for
files exported from Inventor); the direction document as a whole is not yet
accepted. What exists has been tested on a fixture and on a dry-run conversion
of a real project:

- a validator and a flatten step for the layout, standard-library Python;
- tools that measure a STEP file, build a part from a program and build one
  STEP file of a whole assembly for viewing, run by FreeCAD;
- a synthetic fixture and a test suite;
- a dry-run conversion of the first project, which passes the proposal's
  acceptance test (see `.agents/PLANS.md`).

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
  `mechanical-docs` reads, with a copy of the STEP files it names.
- `check` evaluates each authored part's `checks.json` against its measured
  facts.
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
$B3D FreeCADCmd tools/compare_step_exports.py --pass PROJECT MAP.json NEW_REPORT.json
$B3D python3 -B -m pytest -q tests
guix shell --pure -m .guix/manifest-cad.scm -- FreeCADCmd tools/assembly_step.py --pass PROJECT [KEY]
guix shell --pure -m .guix/manifest-cad.scm -- FreeCADCmd tools/compare_assembly_step.py --pass PROJECT KEY OTHER.step NEW_REPORT.json
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
- `step_facts.py` measures every imported STEP file (validity, solids, volume,
  area, centre of mass, bounding box) and writes `facts.json` beside it. A
  file measured with another tool, or another integration, is measured again.
- `build_part.py` builds an authored part from its `build.py` and
  `parameters.json`: the STEP file, a receipt and the facts. Building an
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
| `python-ocp` 7.9.3.1 | The OCP bindings of OpenCASCADE, compiled from the binding sources upstream generates for each release, with the type stubs. Its check builds a box, measures it and sends it through a STEP file |
| `python-build123d` 0.12.0 | build123d, the last release for OpenCASCADE 7.9. Its own tests run in the build |
| `python-ocpsvg`, `python-ocp-gordon`, `python-svgpathtools`, `python-trianglesolver`, `python-bd-materials`, `python-threejs-materials`, `python-pygltflib`, `python-dataclasses-json`, `python-lib3mf` | What build123d needs and Guix does not have |

Nothing builds these for you: the first use compiles the bindings, about
twenty minutes on sixteen cores, and an update of Guix that changes Python,
OpenCASCADE, VTK or pybind11 compiles them again.

Without adding the channel:

```sh
guix shell --pure -L .guix/modules python python-build123d -- python3 PROGRAM.py
guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm -- FreeCADCmd tools/build_part.py --pass PROJECT/designs/parts/KEY
guix shell --pure -L .guix/modules -m manifest.scm -m .guix/manifest-build123d.scm -- python3 -B -m pytest -q tests
```

`.guix/manifest-build123d.scm` is the FreeCAD role with build123d added;
`make test-build123d` runs the last line. What each definition changes
against its upstream, and why, is written beside the change. They are not
yet fit for Guix itself; `.agents/PLANS.md` lists what is missing.

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
