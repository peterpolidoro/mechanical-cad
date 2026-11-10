# Layout fixture

A small synthetic project in the layout of
[docs/layout-specification.md](../../docs/layout-specification.md), used by the
tests. Nothing in it is a real part, and its "Vault" identities are invented.

```
references/parts/base-plate     a 100 x 60 x 8 mm plate; normalised STEP header
references/parts/pin            a 10 mm pin, 30 mm long; a header as an exporter
                                that does not normalise leaves it (name, time, author)
references/assemblies/pin-pair  two pins 50 mm apart, written in centimetres
references/assemblies/fixture-root
                                the plate and two instances of pin-pair, in a +Y-up
                                frame; the second instance is flexible and holds its
                                second pin 10 mm further out than the definition
references/receipts/synthetic-export-0001
                                the stand-in for an exporter's receipt
designs/parts/spacer            a ring written as code: build.py, parameters.json,
                                checks.json, and what the build command made of them
designs/assemblies/fixture-with-spacer
                                an authored assembly placing fixture-root and the spacer
vault-lock.json                 the index derived from references/
```

Flattened from `fixture-with-spacer` it has 3 parts, 4 assembly nodes and 6
occurrences. `python3 -m mechanical_cad validate examples/layout-fixture`
reports no error and one finding, the pin's header.

## Regenerating it

The hand-written files are the spacer's `build.py`, `parameters.json` and
`checks.json`, and `designs/assemblies/fixture-with-spacer/assembly.json`.
Everything else is written by `generate_fixture.py`:

```sh
guix shell --pure -m .guix/manifest-cad.scm -- FreeCADCmd examples/layout-fixture/generate_fixture.py
```

Generating it twice gives the same bytes (FreeCAD 1.1.3, OpenCASCADE 7.9.3,
observed 2026-11-10), so `git status` after a regeneration shows whether
anything changed. A different FreeCAD or OpenCASCADE version may write
different STEP text; the receipts record the versions.
