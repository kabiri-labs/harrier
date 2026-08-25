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

At **0.1.0**: the first two clauses are met and the artefact exists. One topic is
written to full depth, not two. The version tracks the artefact because that is
the only thing anybody consumes.

Explicitly **not** in 1.0: a full card for every unit. At the granularity this
model produces, that is a 300-hour writing project — and it is not what makes the
taxonomy useful. Cards are written on demand, indefinitely.

## Phases

| # | Phase | Status | Note |
|---|---|---|---|
| 0 | Foundation | `done` | Documents, 14 domain codes, 6 axis vocabularies, 36 surface tags, 5 dimensions, WSTG pinned and fully mapped. No content. |
| 1 | Schema and validator | `done` | Seven schemas, six validation passes, offline suite, CI. Identifiers, axis slugs, every cross-reference and the outline/authored distinction are machine-checked. Cheap now, impossible to retrofit across 350 files. |
| 1.5 | Pin the reference standards | `done` | ASVS 5.0.0 at its release commit, CWE 4.20 by versioned archive and content hash. `refs.asvs` and `refs.cwe` both resolve. CVE stays out: it names one bug in one product, not a class. |
| 2 | Topic map | `done` | 99 topics across 13 domains. Every resolvable WSTG identifier is claimed by a topic, and the validator now rejects one that is not. |
| 3 | Unit outline pass | `done` | Every topic decomposed to units carrying an identifier, a title and a falsifiable objective. **This is where the artefact becomes genuinely useful.** Done in six batches of two or three domains, because a review of 350 files at once is not a review. |
| 4 | Chain model spike | `done` | Five units authored across five domains and five shapes, plus the fact layer they needed. The point was to break the model while it was cheap to change, not to add coverage. |
| 4.5 | One topic at depth | `done` | `HRR-RES-01` written all the way down: five authored units, four payload files, a shared card, the first mitigation. A calibration pass, not a coverage one -- it settles how concrete a written unit is before three hundred more are written to match it. |
| 5 | Chain pass | `done` | `requires` and `yields` for all 366 units, in six domain batches, `RCN` first because recon produces most of the base facts. 174 facts, and the gate at the end -- every non-given fact has a producer -- is enforced from here on. |
| 6 | Published artefact | `done` | `harrier build` writes one self-contained HTML file: surface-first entry, a now/next view driven by the facts in hand, coverage views, full-text search, and every card, payload and mitigation embedded. Versioning starts here, at 0.1.0. |
| 7 | Beyond WSTG | `not started` | The topics WSTG does not cover: JWT, OAuth/OIDC, GraphQL, WebSocket, request smuggling, cache poisoning and deception, prototype pollution, race conditions, dependency confusion, cloud metadata, LLM-integrated surfaces. This is the clearest differentiation from restating WSTG. |
| 8 | Depth on demand | `ongoing` | Cards written when a real engagement makes one worth writing. Never speculatively. |

Phases 2–5 are 1.0. Phase 6 is what makes it usable; phase 7 is what makes it
better than the standard it is built on.

The order changed after phase 3: the artefact's main view is driven by the chain,
so the chain has to exist first, and depth waits until real use says which units
deserve it.

## The standing rule

**Never let depth block coverage.**

A unit that exists as an outline — correct identifier, correct objective,
correct surface tags — already appears in the artefact, already counts, and
already stops a test being skipped silently. A unit that does not exist because
nobody has written its two thousand words does none of those things, and its
absence is invisible to the reader.

## Coverage

Two different numbers, kept apart because conflating them would let phase 0's
work read as phase 2's:

| | Count |
|---|---|
| **WSTG identifiers mapped to a domain** | **109 of 109** |
| **WSTG identifiers covered by a topic** | **108 of 108** |
| Topics | 99 |
| Units — outlined | 356 |
| Units — authored | 10 |
| Units — charted | 366 |

*Mapped* means the ordered procedure resolved the identifier, which phase 0
finished. *Covered* means a topic exists that claims it, which phase 2 finished.
The denominators differ by one: `WSTG-INPV-14` is mapped to no domain because it
describes second-order delivery rather than a test, so nothing can cover it and
the validator does not ask anything to.

Every topic now carries units, which was phase 3's job. The number to watch from
here is charted units — those carrying `requires` and `yields` — which is phase
5's, and the one the now/next view depends on entirely.

### Phase 5 batches

`requires` and `yields` for every unit. Recon goes first because it produces the
facts every other domain consumes: charting anything else first would mean
declaring requirements against facts nothing yet establishes.

| Batch | Domains | Units | Status |
|---|---|---|---|
| 1 | `RCN` | 17 | `done` |

| 2 | `INJ` `RES` | 80 | `done` |
| 3 | `CLT` `PRT` | 80 | `done` |
| 4 | `SES` `CRY` | 64 | `done` |
| 5 | `AUT` `IDN` `ACL` | 67 | `done` |
| 6 | `BIZ` `ERR` `CFG` | 58 | `done` |

The pass ended with a gate rather than a count: every fact that is not `given`
has at least one unit producing it, and the validator enforces it from here on.
177 facts, 366 units, and no condition in the graph without a route to it.

### Phase 3 batches

| Batch | Domains | Topics | Units | Status |
|---|---|---|---|---|
| 1 | `INJ` `RES` | 15 | 80 | `done` |
| 2 | `CLT` `PRT` | 17 | 80 | `done` |
| 3 | `SES` `CRY` | 16 | 64 | `done` |
| 4a | `AUT` `IDN` | 14 | 46 | `done` |
| 4b | `ACL` | 7 | 21 | `done` |
| 5 | `BIZ` `ERR` | 13 | 36 | `done` |
| 6 | `RCN` `CFG` | 17 | 39 | `done` |

Batch 1 went first because SQL injection already carries payloads and a card, so
the unit model could be judged against real depth material before three hundred
more units were written on top of it.

### Topics per domain

| | | | | | | |
|---|---|---|---|---|---|---|
| `INJ` 12 | `CLT` 12 | `SES` 11 | `AUT` 10 | `BIZ` 9 | `CFG` 9 | `ACL` 7 |
| `RCN` 8 | `PRT` 5 | `CRY` 5 | `ERR` 4 | `IDN` 4 | `RES` 3 | `SUP` 0 |

`SUP` carries no topics because no WSTG test covers vulnerable components or
supply chain, and phase 2's input is the WSTG map. It is phase 7's first entry,
and its emptiness is part of why the scope is wider than the standard.

These figures are asserted by the test suite, not maintained by hand. A stale
coverage number is worse than none, because it is the number this project asks
to be judged on.

## What already exists

Phases 0 to 2 leave the repository with the vocabularies settled, the machine
checks in place, and the taxonomy's top level written, so the phases that follow begin
against real material rather than an empty tree:

| Asset | State |
|---|---|
| `standards/wstg.yaml` | 109 identifiers, pinned by commit and SHA-256, every entry verified. |
| `standards/wstg-map.yaml` | All 109 resolved to a domain by the ordered procedure, with the deciding rule and a note on each contested one. |
| `payloads/sqli/` | 99 SQL injection payloads across 10 files, covering probe, fingerprint, seven techniques and evasion. |
| `payloads/traversal/` | 4 files: survival probes, encodings and what each distinguishes, read targets with fingerprints, and the read-versus-interpret pair. |
| `toolbox/registry.yaml` | 7 tools with per-flag rationale. |
| `cards/sqli/union-extraction.md` | One card in the recall-first layout, as the worked example of the format. |
| `cards/traversal/path-resolution.md` | The second card, shared by all five units of `HRR-RES-01`. |
| `mitigations/path-resolution.md` | The first mitigation, written because a unit referenced it. |
| `standards/asvs.yaml` | ASVS 5.0.0: 17 chapters, 80 sections, 345 requirement identifiers. Identifiers and structural names only — the text is CC BY-SA. |
| `standards/cwe.yaml` | CWE 4.20: 969 weaknesses, 422 categories, 59 views, with abstraction and status. |
| `knowledge/` | 99 topics across 13 domains, and 366 units across all thirteen domains. |
| `vocab/surfaces.yaml` | 52 attack-surface tags — the primary navigation axis. |
| `harrier/` | Nine schemas, seven validation passes, the derived chain and the artefact builder. See [`VALIDATION.md`](VALIDATION.md). |
| `tests/` | 134 offline tests, almost all of them negative — asserting what must be rejected. |

The payload files and the tool registry are volatile content and carry a
`reviewed` date that predates phase 0. Treat them as unreviewed until a depth pass
re-verifies them against current engine and tool behaviour.
