# mechanical-cad agent guidance

Read README.md, docs/direction.md, docs/layout-proposal.md,
docs/layout-specification.md and .agents/PLANS.md, in that order. Read
.agents/handoff.local.md when present: it holds the paths of the sibling
checkouts and of the shared exchange directory on this machine and is ignored
by Git.

## Role

An agent started here works across four repositories: this one,
`vault-cad-tools`, `mechanical-docs` and the project repository
(`free-standing-tank-enclosure` first). It holds the Linux role described in the
shared exchange directory's `coordination/README.md`: it maintains the
coordination plan and operator prompts there and writes the messages for the
Windows agent.

Before editing a sibling repository, read that repository's `.agents/AGENTS.md`
and `.agents/PLANS.md` and follow them. Update its plan when you change it.

## What belongs here

- `docs/direction.md`: the one statement of where this work is going. Change
  its "Decided" section only for something Peter has actually decided, with the
  date. Mark everything else as proposed.
- The repository layout: specification, validator, fixtures, the step that
  flattens assembly manifests into a scene.
- Tools that build parts from code and check geometry.
- The Guix channel for mechanical CAD packages.

What does not: anything specific to Vault or Inventor (`vault-cad-tools`),
rendering and manuals (`mechanical-docs`), project geometry and records (the
project repository).

## Working practices

- Use the managed Guix environment: `manifest.scm` for everything in
  `mechanical_cad/`, `.guix/manifest-cad.scm` for the FreeCAD-run scripts under
  `tools/`. Add a package to a manifest instead of reaching for host tools.
- Commits, pushes, remotes and publication are Peter's. Leave work uncommitted
  and give one commit command per repository, ending with the attribution line
  Peter's session supplies.
- Nothing writes to Vault without Peter's explicit request. Windows work is
  requested through the shared directory's mailbox; a message never wakes an
  agent, Peter starts it.
- After Peter pushes, bring the clones on the shared directory up to date with
  `tools/update_shared_clone.py`. Never run a git command that writes in a
  clone on that mount.
- This repository is public. Keep server names, Vault paths, host and account
  names, credentials and project data out of it. Fixtures are synthetic. Do not
  copy files from the shared evidence area into any generic repository.
- Keep `mechanical_cad/` standard-library Python so the validator runs
  without a CAD kernel. Kernel-backed steps are separate scripts under
  `tools/`, run by FreeCADCmd, as in `mechanical-docs`.
- The layout has three descriptions that must agree: docs/layout-proposal.md
  (why), docs/layout-specification.md (what) and `mechanical_cad/layout.py`
  (the check). Change them together, with a test.
- A derived file carries no timestamp. Measuring or building something that
  has not changed must change no file.
- Machine-written files are JSON; hand-edited ones are TOML. Each file has one
  writer.
- State what was observed and how, and what was not run. A proposal is not a
  decision and a measurement on one part is not a rule.

## Licensing

3-clause BSD, copyright Howard Hughes Medical Institute. A Guix package
definition adapted from Guix's own is GPL-3.0-or-later: keep such files in the
channel directory with that notice.

## Verification

Run the suite before and after a change:
`guix shell --pure -m manifest.scm -- python3 -B -m pytest -q tests`, and with
`-m .guix/manifest-cad.scm` added when a script under `tools/` or the fixture
changes (four tests need FreeCADCmd and are skipped without it). Add tests with
the code they cover. After regenerating `examples/layout-fixture/`, `git
status` must show no change unless one was intended.

The layout's acceptance test is in docs/layout-proposal.md and is run by
`tools/conversion_acceptance.py`; do not call a conversion done on anything
less.

## The living plan

.agents/PLANS.md holds the current state, the next work and the open decisions,
and nothing else. When a checkpoint is finished, move its record to
.agents/HISTORY.md. Do not write commit ids or "uncommitted" into tracked files:
Git knows, and the text is wrong as soon as Peter commits. A checkbox is a task;
a measurement or a decision is a sentence.

## Finish a session

Update .agents/PLANS.md here and in every repository you changed, refresh the
shared directory's coordination plan and your status file, and list the commit
commands for Peter.
