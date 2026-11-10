# mechanical-cad history

Finished checkpoints, oldest last. Commit ids and "uncommitted" notes describe
the day they were written. The current plan is .agents/PLANS.md.

---

## The plan as first written, 2026-11-10 (morning)

Written by the session that ran in `mechanical-docs` as a handoff to the first
agent started here, before any code existed. Moved here unchanged.

## Objective

Give Peter's Inventor and Vault projects an open representation in Git and the
open-source tools to check it, document it and add to it, with the
free-standing tank enclosure as the test project. The full statement is
docs/direction.md.

## Current checkpoint — 2026-11-10 (repository started, direction and layout proposed)

Written by the agent session that ran in `mechanical-docs` on 2026-11-10, as a
handoff to the first agent started here. Nothing is implemented. Peter committed
the licence here (`1a9235f`) and in `mechanical-docs` (`1772669`) during that
session; the rest is uncommitted.

- [x] Licence file, README, agent guidance, base Guix manifest
  (`python`, `python-pytest`, `git`; observed to resolve: Python 3.12.12,
  pytest 9.0.2).
- [x] docs/direction.md: goal, the six-stage loop, decisions with dates,
  repository roles, proposed layout and order of work, out of scope.
- [x] docs/layout-proposal.md: the proposed layout, what was measured on the
  enclosure, what is unverified, the acceptance test, the Windows tests.
- [ ] Peter's acceptance of the direction document (drafted from his
  statements; he has not said "accepted").
- [ ] Peter's answers to the three open layout choices (below).

## What Peter decided on 2026-11-10

- Licence: 3-clause BSD, copyright HHMI, in all four repositories.
- Hosting: GitHub. The Codeberg repositories will move there; where is not
  settled.
- This repository holds the tools and doubles as the Guix channel.
- Cross-repository work runs from an agent session rooted here.
- He wants the proper structure for STEP files and metadata worked out, then
  the enclosure re-imported from Vault into it. He is willing to move the
  current enclosure files to a branch.
- While agents work, he assembles the enclosure from the published manual and
  takes notes on the documentation. Afterwards agents design new parts for the
  enclosure with the tools packaged here; he manufactures and checks them; then
  `vault-cad-tools` places them in Vault.

Not decided, although recommended to him: that the direction lives here rather
than in `orb-weaver-context` (he answered by choosing to start the agent here);
the layout itself.

## Open decisions to put to Peter

1. Two roots (`references/`, `designs/`) or one tree with an authority field.
   Recommended: two roots.
2. Readable directory keys tied to the Vault master id, or a mirror of Vault's
   folder tree. Recommended: readable keys.
3. AP214 or AP242, after the Windows test.
4. Whether supplier-originated models may stay in a public repository, and the
   wording of the enclosure README's scope statement (an agent's draft).
5. Whether account, host and server names stay in public files.

## Next work, in order

1. Get Peter's answers to decisions 1 and 2 and his acceptance of the direction.
2. Write the layout as a specification with a standard-library validator and a
   small synthetic fixture, here. Add the flatten step that produces the
   `scene.json` shape `mechanical-docs` reads (`mechanical-docs/docs/input-contract.md`).
3. Write the converter from the enclosure's existing snapshot to the layout and
   run it on a branch of the enclosure. Pass the acceptance test in
   docs/layout-proposal.md. `main` of the enclosure stays untouched until then.
4. Replace the Windows agent's queued work with one message asking for the four
   read-only tests in docs/layout-proposal.md, and rewrite the operator prompt.
5. Have the Windows exporter write the layout; re-export; compare with step 3.
6. Geometry facts, build and check commands; move the enclosure's monitor
   envelope to the new shape as the first authored part.
7. Channel skeleton (`.guix-channel` pointing at `.guix/modules`, as
   `orb-weaver-context` does), then OCP against Guix's `opencascade-occt`,
   build123d, CadQuery. Peter recorded this packaging as his own deferred work
   on 2026-10-23; confirm before starting it.

## Hazards

- **The Windows operator prompt points at superseded work.** In the shared
  directory, `coordination/PROMPT-WINDOWS.txt` still sends the Windows agent to
  two unread messages of 2026-10-23 (`151357Z`, `153207Z`): a `metadata.json`
  sample and an incremental export dry run, both on the old layout. Folder
  discovery in the first message is unaffected. Rewrite the prompt before Peter
  starts that agent.
- **The shared coordination plan is stale.** `coordination/PLAN.md` and
  `NEXT-AGENT.md` describe 2026-10-23. Where they differ from
  docs/direction.md, the direction wins; update them as the Linux role.
- **The enclosure's `main` feeds the published manual.** Its Pages workflow
  builds on every push to `main`, and Peter is assembling from that manual.
- **Remotes.** `origin` here still points at Codeberg; the GitHub remote is
  `peterpolidoro`. Remotes are Peter's to change.
- **The handoff files in the sibling repositories were written on 2026-10-22/23**
  and name commits and patches that are long since committed. Each now starts
  with a 2026-11-10 note; trust that note and the tracked plans over the rest.

## State of the four repositories when this was written

| Repository | HEAD | Uncommitted |
| --- | --- | --- |
| `mechanical-cad` | `1a9235f` (licence only) | README, guidance, plan, manifest, ignore rules, `docs/` |
| `mechanical-docs` | `1772669` (licence, first plan update) | README, guidance, plan, `docs/next-agent.md` |
| `vault-cad-tools` | `7807e8f` | licence, README, guidance, plan |
| `free-standing-tank-enclosure` | `0eeb1af` | licence, README, guidance, plan |

The shared clones matched `7807e8f` and `0eeb1af`. No tests were run in any
repository on 2026-11-10: every change is documentation or licence text.

## Not run, not known

- No code exists here, so nothing was tested beyond the manifest resolving.
- The measurements in docs/layout-proposal.md were made on Linux from tracked
  files; none involved Vault, Inventor or the Windows machine.
- The claim in the external discussion that the package names are free on PyPI
  was not checked.
