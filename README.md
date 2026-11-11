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
- tools that measure a STEP file and build a part from a program, run by
  FreeCAD;
- a synthetic fixture and a test suite;
- a dry-run conversion of the first project, which passes the proposal's
  acceptance test (see `.agents/PLANS.md`).

There is no Guix channel yet, and no package of OCP, build123d or CadQuery.

## Start here

1. [Direction](docs/direction.md): the goal, what is decided, which repository
   owns what, the order of work and what is out of scope.
2. [Layout proposal](docs/layout-proposal.md): the proposed structure for STEP
   files and metadata, the evidence behind it and what is still unknown.
3. [Layout specification](docs/layout-specification.md): the draft that the
   tools implement.
4. Agents: [AGENTS.md](AGENTS.md), then [the living plan](.agents/PLANS.md).

## Commands

Nothing below needs a CAD kernel:

```sh
guix shell --pure -m manifest.scm -- python3 -B -m mechanical_cad validate PROJECT
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
- `flatten` composes the per-assembly manifests into the `scene.json` that
  `mechanical-docs` reads, with a copy of the STEP files it names.
- `check` evaluates each authored part's `checks.json` against its measured
  facts.
- `compare-scenes` says whether two flattened scenes are the same assembly.
  With `--other-export`, STEP files that differ are listed, not counted: use
  it with `compare_step_exports.py` when a project was exported again in
  another protocol.

These run in FreeCAD (`.guix/manifest-cad.scm`):

```sh
guix shell --pure -m .guix/manifest-cad.scm -- FreeCADCmd tools/step_facts.py --pass PROJECT
guix shell --pure -m .guix/manifest-cad.scm -- FreeCADCmd tools/build_part.py --pass PROJECT/designs/parts/KEY
guix shell --pure -m .guix/manifest-cad.scm -- FreeCADCmd tools/compare_step_exports.py --pass PROJECT MAP.json NEW_REPORT.json
guix shell --pure -m manifest.scm -m .guix/manifest-cad.scm -- python3 -B -m pytest -q tests
```

- `compare_step_exports.py` measures other exports of a project's parts (an
  AP242 export of a part tracked as AP214, an export from another session) and
  says whether each is the same geometry as the tracked file.
- `step_facts.py` measures every imported STEP file (validity, solids, volume,
  area, centre of mass, bounding box) and writes `facts.json` beside it.
- `build_part.py` builds an authored part from its `build.py` and
  `parameters.json`: the STEP file, a receipt and the facts. Building an
  unchanged part again changes no file.

FreeCADCmd reads dashed options itself, even after `--pass`; put a bare `--`
before a script's own options (`--pass PROJECT -- --force`). It also exits 0
after an uncaught exception, so each script prints its own status line.

`tools/conversion_acceptance.py` runs the acceptance test for converting an
exporter's package into the layout.

`tools/update_shared_clone.py LOCAL_CHECKOUT SHARED_CLONE` fast-forwards a
clone that lives on a filesystem where git cannot write safely (the network
share the Windows agent fetches from) to the commit of a clean, pushed local
checkout, by copying a pack, the refs, the changed files and the index.

## Related repositories

- `vault-cad-tools`: exchange with Autodesk Vault and Inventor, and the import
  command that writes the layout.
- `mechanical-docs`: inventories and assembly manuals from a project repository.
- `free-standing-tank-enclosure`: the first project and the test case.

## Licence

3-clause BSD, copyright Howard Hughes Medical Institute; see [LICENSE](LICENSE).
Guix package definitions adapted from Guix's own will carry Guix's licence,
GPL-3.0-or-later, and be marked as such.
