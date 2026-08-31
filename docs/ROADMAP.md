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

At **0.4.0**: the first two clauses are met and the artefact exists. One topic is
written to full depth, not two. The version tracks the artefact because that is
the only thing anybody consumes -- and 0.4.0 changed what the artefact is, which
is why the jump is a breaking one taken deliberately while it still can be.

Explicitly **not** in 1.0: a full card for every unit. At the granularity this
model produces, that is a 300-hour writing project — and it is not what makes the
taxonomy useful. Cards are written on demand, indefinitely.

## Phases

| # | Phase | Status | Note |
|---|---|---|---|
| 0 | Foundation | `done` | Documents, 14 domain codes, 6 axis vocabularies, 36 surface tags, 5 dimensions, WSTG pinned and fully mapped. No content. |
| 1 | Schema and validator | `done` | Seven schemas, six validation passes, offline suite, CI. Identifiers, axis slugs, every cross-reference and the three depth tiers are machine-checked. Cheap now, impossible to retrofit across 350 files. |
| 1.5 | Pin the reference standards | `done` | ASVS 5.0.0 at its release commit, CWE 4.20 by versioned archive and content hash. `refs.asvs` and `refs.cwe` both resolve. CVE stays out: it names one bug in one product, not a class. |
| 2 | Topic map | `done` | 99 topics across 13 domains. Every resolvable WSTG identifier is claimed by a topic, and the validator now rejects one that is not. |
| 3 | Unit outline pass | `done` | Every topic decomposed to units carrying an identifier, a title and a falsifiable objective. **This is where the artefact becomes genuinely useful.** Done in six batches of two or three domains, because a review of 350 files at once is not a review. |
| 4 | Chain model spike | `done` | Five units authored across five domains and five shapes, plus the fact layer they needed. The point was to break the model while it was cheap to change, not to add coverage. |
| 4.5 | One topic at depth | `done` | `HRR-RES-01` written all the way down: five authored units, four payload files, a shared card, the first mitigation. A calibration pass, not a coverage one -- it settles how concrete a written unit is before three hundred more are written to match it. |
| 5 | Chain pass | `done` | `requires` and `yields` for all 366 units, in six domain batches, `RCN` first because recon produces most of the base facts. 177 capabilities, and the gate at the end -- every non-given fact has a producer -- is enforced from here on. |
| 6 | Published artefact | `done` | `harrier build` writes one self-contained HTML file with every card, payload and mitigation embedded. Versioning starts here, at 0.1.0. Its first navigation model -- a surface-anchored board driven by the facts a tester ticked -- was replaced in phase 6.5. |
| 6.5 | Product pivot | `done` | Harrier becomes an execution companion to a standard rather than a workspace about a target. Standard-first navigation, atomic decomposition per WSTG test case, a derived local chain per unit, a progressively disclosed general graph, and the removal of every piece of engagement state. **Breaking, and deliberate.** See [`PIVOT.md`](PIVOT.md). |
| 6.6 | Second entry point | `done` | The catalogue could be entered from a standard or from a capability, and a tester mid-engagement holds neither: they are looking at an upload, a sort parameter, a token. 0.19.0 makes the attack-surface tags navigable — they had been on every topic since phase 0 and reached the page as inert text — so a context selects the tests filed under it, says which tag matched, and separates the tests nothing has to precede from the ones waiting on a capability. It selects; it establishes nothing. The tag vocabulary and the fact vocabulary do not meet, so no context can be read as a capability in hand, and the file still holds no target. |
| 7 | Beyond WSTG | `not started` | The topics WSTG does not cover: JWT, OAuth/OIDC, GraphQL, WebSocket, request smuggling, cache poisoning and deception, prototype pollution, race conditions, dependency confusion, cloud metadata, LLM-integrated surfaces. Harrier Extensions exists to receive them. This is the clearest differentiation from restating WSTG. |
| 8 | Depth on demand | `ongoing` | Cards written when a real engagement makes one worth writing. Never speculatively. Since 0.10.0 a unit can be sketched rather than only outlined or written in full, so the step from breadth to usable depth is twenty minutes rather than two hours. 0.11.0 sketched the seventeen reconnaissance and configuration topics an engagement opens with. 0.14.0 authored the terminal outcome layer first, because a chain whose last step is an outline stops at a capability rather than at an outcome; 0.15.0 wrote the supporting layer for SQL injection before its units, because the validator rejects a unit referencing a card or a mitigation that does not exist yet; 0.16.0 took the nine remaining `HRR-INJ-01` units to full depth, which makes SQL injection the first chain readable end to end from the standard's own test case to a stated business outcome; 0.17.0 did the same for object-level access control, a chain with no payload axis at all, where the whole difficulty is in the oracle and the evidence; 0.18.0 completed the third with cross-site scripting, whose eight context units are eight different answers to what has already been escaped by the time the value arrives. Three chains now run end to end rather than one. |

Phases 2–5 are 1.0. Phase 6 is what makes it usable; phase 7 is what makes it
better than the standard it is built on.

Surface tags are carried by the topic rather than by the unit, so a context
selects whole topics and lists every test in them. Where a topic spans contexts
a single tag cannot separate — the ten `HRR-CLT-01` units are ten output
contexts, not one — the selection is coarser than the catalogue could be. The
unit schema already permits `surfaces`, so refining it needs content rather than
a schema change, and it is not worth doing speculatively: the tags that would
benefit are the ones a real engagement finds too broad.

The order changed after phase 3: the artefact's main view is driven by the chain,
so the chain has to exist first, and depth waits until real use says which units
deserve it.

Phase 6.5 changed what the artefact is for. The board it removed was coherent,
and it asserted things about a target the file has never seen. What replaced it
answers a narrower question honestly: what is inside this test case, how is each
piece performed, and where can a success lead. The decision, the trade-offs and
the full list of non-goals are in [`PIVOT.md`](PIVOT.md) rather than here,
because a roadmap records what is being built and that document records why one
thing stopped being built.

## Public alpha

0.4.0 is the first version published for anyone outside the project to look at,
and it is an alpha in the honest sense: the decomposition is broad and the depth
behind it is not. Every resolvable WSTG identifier is claimed and 374 Test Units
exist; 36 are written to full procedural depth, 40 are sketched, and the far half
of the chain is barely charted.

Both figures are in the README rather than at the bottom of it, and the suite
reads them from the catalogue so neither can go stale in prose. The label is not
a disclaimer to be dropped once the project feels more finished -- it comes off
when the numbers say so.

## The standing rule

**Never let depth block coverage.**

A unit that exists as an outline — correct identifier, correct objective,
correct surface tags — already appears in the artefact, already counts, and
already stops a test being skipped silently. A unit that does not exist because
nobody has written its two thousand words does none of those things, and its
absence is invisible to the reader.

Depth is therefore written in tiers rather than in one step. An outline is five
minutes and a unit written in full is a couple of hours, which left nothing in
between and made the gap read as wider than it is: a **sketch** is twenty
minutes and carries the steps, the reading of a result, the mistake that most
often imitates a positive, and what finishing means. That is most of what a
tester uses in the field. What each tier requires is in the schema, so a status
cannot claim more than the file carries.

## Coverage

Two different numbers, kept apart because conflating them would let phase 0's
work read as phase 2's:

| | Count |
|---|---|
| **WSTG identifiers mapped to a domain** | **109 of 109** |
| **WSTG identifiers covered by a topic** | **108 of 108** |
| Topics | 106 |
| Units — outlined | 298 |
| Units — sketched | 40 |
| Units — authored | 36 |
| Units — charted | 374 |

*Mapped* means the ordered procedure resolved the identifier, which phase 0
finished. *Covered* means a topic exists that claims it, which phase 2 finished.
The denominators differ by one: `WSTG-INPV-14` is mapped to no domain because it
describes second-order delivery rather than a test, so nothing can cover it and
the validator does not ask anything to.

Every topic now carries units, which was phase 3's job. The number to watch from
here is charted units — those carrying `requires` and `yields` — which is phase
5's, and the one every local chain in the artefact is derived from.

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
185 facts, 374 units, and no condition in the graph without a route to it.

The gate is one-directional, and the asymmetry is worth stating plainly. Every
capability has a producer; many have no *consumer*. 78 of 177 are declared as a
use by nothing at all -- impacts excluded, because those are terminal by
construction and counting them here would describe arriving as failing to
arrive. So the chain runs from reconnaissance to a primitive and then stops.
That is the shape of what phase 5 set out to do -- place every unit in the graph
-- and not the shape of a complete attack model. Charting the far half is listed
under **Considered, not scheduled** rather than left to be noticed one dead end
at a time.

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
| `RCN` 8 | `OUT` 7 | `PRT` 5 | `CRY` 5 | `ERR` 4 | `IDN` 4 | `RES` 3 |
| `SUP` 0 | | | | | | |

`OUT` is where a confirmed capability arrives. Its topics claim no WSTG test
case, because the standard enumerates what to test rather than what a result is
worth, and they appear under Harrier Extensions for that reason.

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
| `payloads/sqli/` | 105 SQL injection payloads across 10 files, covering probe, fingerprint, seven techniques and evasion. |
| `payloads/traversal/` | 4 files: survival probes, encodings and what each distinguishes, read targets with fingerprints, and the read-versus-interpret pair. |
| `payloads/xss/` | 48 payloads across 10 files, one per context plus the probe and the evasion set, each executable entry run in a browser rather than recalled. |
| `toolbox/registry.yaml` | 8 tools with per-flag rationale. |
| `cards/sqli/union-extraction.md` | One card in the recall-first layout, as the worked example of the format. |
| `cards/traversal/path-resolution.md` | The second card, shared by all five units of `HRR-RES-01`. |
| `cards/outcome/proportionate-demonstration.md` | The third card, shared by the three terminal outcome units: how much is enough to answer what a capability was worth. |
| `cards/sqli/injection-points.md` | Shared by the five `HRR-INJ-01` units that reason about where a value lands in the statement rather than what to do once it is there. |
| `cards/sqli/inference.md` | Shared by the four `HRR-INJ-01` channels that read a database, and the basis for choosing between the two shapes they divide into. |
| `mitigations/path-resolution.md` | The first mitigation, written because a unit referenced it. |
| `cards/access-control/object-ownership.md` | Shared by all five `HRR-ACL-02` units: the two-account method, the empty-record trap, and the ceiling that keeps enumeration a sample. |
| `payloads/access-control/identifiers.yaml` | Identifier shapes and adjacency -- transformations of an identifier the engagement holds, never a guess into real records. |
| `mitigations/parameterised-query.md` | CWE-89, for `HRR-INJ-01`: binding rather than escaping, what cannot be bound, and what least privilege changes about each capability the topic charts. |
| `cards/xss/contexts.md` | Shared by the probe and all eight `HRR-CLT-01` context units: the context table, and why an encoder written for one context leaves another live. |
| `cards/xss/evasion.md` | The four mechanisms that produce one clean result, and the single observation that separates each. |
| `mitigations/output-encoding.md` | CWE-79 and CWE-80, for `HRR-CLT-01`: encode at output for the context, and why a content policy is a second layer rather than the fix. |
| `mitigations/object-authorization.md` | CWE-639 and CWE-566, for `HRR-ACL-02`: authorize the object rather than the route, enforce at the data-access layer, and why an unguessable identifier is exposure surface rather than a control. |
| `standards/asvs.yaml` | ASVS 5.0.0: 17 chapters, 80 sections, 345 requirement identifiers. Identifiers and structural names only — the text is CC BY-SA. |
| `standards/cwe.yaml` | CWE 4.20: 969 weaknesses, 422 categories, 59 views, with abstraction and status. |
| `knowledge/` | 106 topics across 14 domains, and 374 units across all fourteen domains. |
| `vocab/surfaces.yaml` | 52 attack-surface tags, describing where a topic applies. |
| `vocab/facts.yaml` | 185 capabilities in seven families — the join keys the chain is derived from. |
| `harrier/` | Nine schemas, seven validation passes, the derived chain, and the builder plus the artefact's own template, stylesheet and script. See [`VALIDATION.md`](VALIDATION.md). |
| `tests/` | An offline suite, almost all of it negative — asserting what must be rejected. Two further runners, `node` and a browser, are used when present and skipped when not. |

The payload files and the tool registry are volatile content and carry a
`reviewed` date that predates phase 0. Treat them as unreviewed until a depth pass
re-verifies them against current engine and tool behaviour.

## Considered, not scheduled

Recorded so they are decisions rather than omissions. None is being built.

| Item | Note |
|---|---|
| **Chart what a defeated control permits** | The largest remaining gap. 49 of 185 capabilities are established by a test and used by none, and 36 of 59 of them are `control.*`; `primitive.*` is down to 1 of 32 since the outcome layer landed. The three phase-1 chains gave three control facts their first consumer, and those are `motivated_by` hints rather than escalations — nothing yet says what a defeated control *permits*, which is what this item is for. A control is the state of a defence rather than a result, so the step that turns one into something — what a weak cookie, a permissive cache or an absent binding actually lets somebody do — has to be written before an edge can honestly be drawn from it. Until it is, 81 of 374 tests still end at the capability they established. |
| **`HRR-CLT-02` — DOM cross-site scripting** | The sibling of the chain 0.18.0 wrote, and the natural next one. A second instance of a shape already proven, which is why it waited. |
| **`HRR-RES-03` — server-side request forgery** | A fourth chain shape: `primitive.fetch.internal` to `impact.network.reached`, through `HRR-OUT-03`. The first candidate once the three phase-1 chains have been used in anger. |
| A second execution standard | The navigation is standard-first and the artefact's structure allows one. Nothing is added until there is a standard whose decomposition Harrier improves as much as it improves WSTG's. |
| OWASP Top 10 as a risk lens | A classification of risk, not an execution methodology. If it arrives it is a lens over the existing catalogue and never a second way to navigate to a test. |
| ASVS as a remediation lens | The mapping already exists in `refs.asvs`; a view that reads a finding's controls from it does not. |
| Better graph exploration | Saved focus, comparison of two routes, filtering a path by domain. The current general graph is deliberately the smallest thing that is honest. |
| More units at full depth | Thirty-six of 374, with 40 sketched. Governed by the standing rule above: written when an engagement makes one worth writing. |
| Optional external integrations | Export to a report template, or a checklist import. Anything of the kind must not become a route by which target data enters the artefact. |

## Governance and distribution

Inbound contribution terms are in [`CONTRIBUTING.md`](../CONTRIBUTING.md), and
were written before the project accepted its first outside contribution rather
than after: a licence decision that has to be renegotiated with past
contributors is one that cannot be made.

Three settled questions -- the repository stays public, a hosted site is a later
second build target, and any commercial layer lives outside this repository --
are recorded with their reasoning in
[`DISTRIBUTION.md`](DISTRIBUTION.md). They are decisions rather than omissions,
and the record says what would have to change for each to be revisited.

## Releasing

`release.yml` attaches the built artefact to a release published from the GitHub
UI. It runs the same checks a pull request runs -- by calling `validate.yml`,
not by restating them -- refuses to continue if the tag and `__version__`
disagree, and publishes the SHA-256 beside the file after rebuilding from
scratch to prove the digest is reproducible.

The trigger is `release: published` rather than a tag push, so the workflow can
only ever add a file to a publication a person made; it has no path by which it
publishes anything of its own. `workflow_dispatch` exercises the whole thing and
publishes nothing.

Building and publishing are separate jobs on purpose. The build installs
dependencies and runs this repository's code, so it holds `contents: read` and
checks out without persisting a credential; the job that can write runs neither,
and is guarded on the job rather than the step so a dispatch never creates a
runner holding a write credential at all.
