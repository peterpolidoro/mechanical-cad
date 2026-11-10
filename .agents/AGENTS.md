# mechanical-cad agent guidance

Read README.md, docs/direction.md, docs/layout-proposal.md and .agents/PLANS.md,
in that order. Read .agents/handoff.local.md when present: it holds the paths of
the sibling checkouts and of the shared exchange directory on this machine and
is ignored by Git.

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

- Use the managed Guix environment (`manifest.scm`). Add a package to the
  manifest instead of reaching for host tools.
- Commits, pushes, remotes and publication are Peter's. Leave work uncommitted
  and give one commit command per repository, ending with the attribution line
  Peter's session supplies.
- Nothing writes to Vault without Peter's explicit request. Windows work is
  requested through the shared directory's mailbox; a message never wakes an
  agent, Peter starts it.
- This repository is public. Keep server names, Vault paths, host and account
  names, credentials and project data out of it. Fixtures are synthetic. Do not
  copy files from the shared evidence area into any generic repository.
- Keep the core standard-library Python so the validator runs without a CAD
  kernel. Kernel-backed steps are separate scripts, as in `mechanical-docs`.
- Machine-written files are JSON; hand-edited ones are TOML. Each file has one
  writer.
- State what was observed and how, and what was not run. A proposal is not a
  decision and a measurement on one part is not a rule.

## Licensing

3-clause BSD, copyright Howard Hughes Medical Institute. A Guix package
definition adapted from Guix's own is GPL-3.0-or-later: keep such files in the
channel directory with that notice.

## Verification

There is no test suite yet. Add tests with the code they cover. The layout's
acceptance test is in docs/layout-proposal.md; do not call the conversion done
on anything less.

## Finish a session

Update .agents/PLANS.md here and in every repository you changed, refresh the
shared directory's coordination plan and your status file, and list the commit
commands for Peter.
