# Roadmap

Build state. **Every change updates this file in the same pull request as the
work.** A roadmap updated only when someone remembers is the same failure mode as
a test plan updated only when someone remembers.

Status: `done` · `in progress` · `not started`

---

## Definition of 1.0

> Every WSTG identifier decomposed into units, every unit carrying a falsifiable
> objective, and at least two topics authored to full depth so the model can be
> judged on real content rather than on its own description.

Explicitly **not** in 1.0: a full card for every unit. At the granularity this
model produces, that is a 300-hour writing project — and it is not what makes the
taxonomy useful. Cards are written on demand, indefinitely.

## Phases

| # | Phase | Status | Note |
|---|---|---|---|
| 0 | Foundation | `in progress` | Documents, controlled vocabularies, pinned standards. No content. |
| 1 | Schema and validator | `not started` | Machine-checked identifiers, axis slugs, references, and the outline/authored distinction. Cheap now, impossible to retrofit across 350 files. |
| 2 | Topic map | `not started` | Every topic named, placed in a domain, given its axis and boundaries. `standards/wstg-map.yaml` is the input: every entry must be covered by at least one topic, and every topic must trace back to an entry or be declared beyond-WSTG. |
| 3 | Unit outline pass | `not started` | Every topic decomposed to units. Identifier, title, objective, surfaces, refs. **This is where the artefact becomes genuinely useful.** |
| 4 | Two reference topics at depth | `not started` | SQL injection and cross-site scripting. Chosen because one splits on `technique` with a dimension, the other on `context` with two dimensions — between them they exercise every mechanism in the model. |
| 5 | Published artefact | `not started` | Single self-contained HTML file. Surface-first navigation, full-text search, standard-coverage views. |
| 6 | Beyond WSTG | `not started` | The topics WSTG does not cover: JWT, OAuth/OIDC, GraphQL, WebSocket, request smuggling, cache poisoning and deception, prototype pollution, race conditions, dependency confusion, cloud metadata, LLM-integrated surfaces. This is the clearest differentiation from restating WSTG. |
| 7 | Depth on demand | `ongoing` | Cards written when a real engagement makes one worth writing. Never speculatively. |

Phases 2–4 are 1.0. Phase 5 is what makes it usable; phase 6 is what makes it
better than the standard it is built on.

## The standing rule

**Never let depth block coverage.**

A unit that exists as an outline — correct identifier, correct objective,
correct surface tags — already appears in the artefact, already counts, and
already stops a test being skipped silently. A unit that does not exist because
nobody has written its two thousand words does none of those things, and its
absence is invisible to the reader.

## Coverage

| | Topics | Units | Cards |
|---|---|---|---|
| Authored | 0 | 0 | 0 |
| Outlined | 0 | 0 | — |
| **WSTG identifiers mapped** | **0 of 109** | | |

These figures are meant to be asserted by the validator, not maintained by hand.
A stale coverage number is worse than none, because it is the number this project
asks to be judged on.

## What already exists

Phase 0 leaves the repository with the vocabularies settled and four content
assets in place, so phases 2–4 start against real material rather than an empty
tree:

| Asset | State |
|---|---|
| `standards/wstg.yaml` | 109 identifiers, pinned by commit and SHA-256, every entry verified. |
| `standards/wstg-map.yaml` | All 109 resolved to a domain by the ordered procedure, with the deciding rule and a note on each contested one. |
| `vocab/surfaces.yaml` | 36 attack-surface tags with discovery hints — the primary navigation axis. |
| `payloads/sqli/` | 99 SQL injection payloads across 10 files, covering probe, fingerprint, seven techniques and evasion. |
| `toolbox/registry.yaml` | 6 tools with per-flag rationale. |
| `cards/sqli/union-extraction.md` | One card in the recall-first layout, as the worked example of the format. |

The payload files and the tool registry are volatile content and carry a
`reviewed` date that predates phase 0. Treat them as unreviewed until phase 4
re-verifies them against current engine and tool behaviour.
