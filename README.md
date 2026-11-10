# mechanical-cad

Open-source tools for writing mechanical parts as code and checking their
geometry, the layout that project repositories use for STEP files and their
metadata, and a Guix channel for the mechanical CAD packages those tools need.

**Status (2026-11-10): direction and layout proposed, nothing implemented.**
This repository holds documents only. No specification, tool or package exists
yet.

## Start here

1. [Direction](docs/direction.md): the goal, what is decided, which repository
   owns what, the order of work and what is out of scope.
2. [Layout proposal](docs/layout-proposal.md): the proposed structure for STEP
   files and metadata, the measurements behind it and what is still unknown.
3. Agents: [AGENTS.md](AGENTS.md), then [the living plan](.agents/PLANS.md).

## Related repositories

- `vault-cad-tools`: exchange with Autodesk Vault and Inventor.
- `mechanical-docs`: inventories and assembly manuals from a project repository.
- `free-standing-tank-enclosure`: the first project and the test case.

## Licence

3-clause BSD, copyright Howard Hughes Medical Institute; see [LICENSE](LICENSE).
Guix package definitions adapted from Guix's own will carry Guix's licence,
GPL-3.0-or-later, and be marked as such.
