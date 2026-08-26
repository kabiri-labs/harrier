# Harrier

> An interactive execution companion for web security testing standards. It
> decomposes large standard test cases into atomic, independently understandable
> Test Units, and shows what attack-chain paths may become relevant when each
> Test Unit succeeds.

[![licence](https://img.shields.io/badge/licence-Apache--2.0-green)](LICENSE)
[![version](https://img.shields.io/badge/version-0.4.0-blue)](docs/ROADMAP.md)
[![WSTG](https://img.shields.io/badge/WSTG-109%20pinned-informational)](standards/wstg.yaml)
[![ASVS](https://img.shields.io/badge/ASVS-5.0.0%20pinned-informational)](standards/asvs.yaml)
[![CWE](https://img.shields.io/badge/CWE-4.20%20pinned-informational)](standards/cwe.yaml)

**WSTG tells you what to cover. Harrier shows you the real tests inside it and
where each successful test can lead.**

## What this is

Published testing standards are exhaustive at the wrong granularity. One WSTG
identifier is a chapter, not a task: `WSTG-INPV-05` is a single line on a
checklist and ten materially different tests in practice, with different
payloads, different oracles and different outcomes. So a practitioner reads it
once, then works from personal notes — which is where coverage quietly goes.

Harrier is the layer between the standard and the work. It adds two things the
standard does not reach:

1. **Atomic decomposition.** A WSTG test case is made explicit as the set of
   independently performable Test Units inside it, each with a stable
   identifier, a falsifiable objective, an explicit boundary against its
   neighbours, and the one thing that settles it.
2. **Attack-chain continuity.** A successful Test Unit establishes a capability
   that can make other tests — or an impact — relevant. Harrier derives those
   possible continuations so a test is not read as an isolated checklist item.

The initial supported execution standard is OWASP WSTG, which provides the
primary coverage and navigation structure:

```
Standard → Testing group → WSTG test case → Harrier Test Units → Test Unit detail
```

## The journey

```
Choose WSTG
→ choose a group              Authorization Testing
→ choose a test case          WSTG-ATHZ-01, Testing Directory Traversal File Include
→ inspect its atomic tests    five of them, probe through execution
→ open one Test Unit          HRR-RES-01-READ, confirmed read outside the intended root
→ see where success may lead  named under the objective, before the procedure
→ see how to perform it       oracle, sequence, payloads, false positives, safety
→ follow the continuation     HRR-RES-01-EXEC, and what it still requires
```

`WSTG-INPV-05` is the decomposition in its clearest form: one checklist line,
ten materially different tests. `WSTG-ATHZ-01` is the chain in its clearest
form: the one topic written to full depth, running probe → read → execution.

## What this is not

- **Not a scanner or an exploit framework.** Nothing here scans, exploits, or
  talks to a target.
- **Not an engagement tracker.** It holds no target, no engagement, no results
  and no findings, and it stores nothing in your browser.
- **Not an automatic decision-maker.** It is context-free by design: it has
  never seen your target and never claims to know what is true of it. Chain
  statements are about the relationship between two tests — *potential
  continuation*, never *unlocked*.
- **Not a tutorial.** The reader already knows what cross-site scripting is.
  PortSwigger's Academy teaches it better than this ever will, and has labs.

The full list of deliberate exclusions, and why, is in
[`docs/PIVOT.md`](docs/PIVOT.md).

## Who it is for

An experienced tester who is not learning the technique but recovering a detail
they knew six months ago, and who wants to see what a standard line item
actually contains. Content is written for **recall**, not for reading: oracle,
sequence, payload pointer, the first false positive, and what counts as
finished.

## Scope

Web application testing, not the WSTG table of contents. WSTG is the execution
and navigation standard, and it is also the coverage skeleton — proof that
nothing standard is missing. A large part of current practice has no WSTG
identifier at all: JWT, OAuth and OIDC, GraphQL, WebSocket, HTTP request
smuggling, cache poisoning and deception, prototype pollution, race conditions,
dependency confusion, cloud metadata, and LLM-integrated surfaces. Those are in
scope, carry Harrier identifiers of their own, and appear under **Harrier
Extensions** rather than being forced into a group they do not belong to.

ASVS is a control and remediation mapping. CWE is a weakness classification.
Neither is an execution methodology and neither is presented as one.

## Structure

| Directory | Holds |
|---|---|
| `docs/` | The model, the naming methodology, the authoring rules, the roadmap, the pivot record |
| `harrier/` | The validator and the builder — the only executable code here |
| `harrier/artefact/` | The published page: template, stylesheet, script |
| `standards/` | Pinned WSTG, ASVS and CWE references — generated, never hand-edited |
| `vocab/` | Controlled vocabularies: domains, axes, surface tags, dimensions, facts |
| `knowledge/` | The taxonomy: topics and units |
| `cards/` | Recall-first prose, organised by technique |
| `payloads/` | The only place a payload is written |
| `toolbox/` | Tool invocations with per-flag rationale |
| `mitigations/` | Remediation text, keyed by weakness class |
| `tests/` | Offline suite; mutation tests copy the repository and break one thing |

Start with [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), then
[`docs/TAXONOMY.md`](docs/TAXONOMY.md) and
[`docs/CHAINING.md`](docs/CHAINING.md).

## Working on it

```bash
pip install PyYAML jsonschema

python -m unittest discover -s tests -t .   # offline
python -m harrier validate                  # the repository
python -m harrier coverage                  # the counts the roadmap publishes
python -m harrier chain HRR-RES-01-READ     # what a test needs, establishes and may lead to
python -m harrier build -o harrier.html     # the artefact, then open it
```

The first two must pass, and CI runs exactly them. Two runners inside the suite
are optional locally and installed in CI, because a suite that quietly skipped
a third of itself would look identical to one that passed it:

```bash
pip install playwright && playwright install chromium   # plus node, for the rest
```

`node` executes the artefact's own graph, layout, path and search functions
against the real catalogue; a browser opens the built file over `file://` and
uses it — typing in the search box, clicking a node in the graph, pressing Enter
on one — while recording every request it attempts and every console error.
[`docs/VALIDATION.md`](docs/VALIDATION.md) explains what is checked and why each
rule is mechanical rather than a review comment.

## Releases

The artefact is built by CI and attached to a release, never committed. A stale
committed copy is indistinguishable from a current one at a glance, and only one
of those is safe to hand to someone.

The trigger is a release published from the GitHub UI — deliberately, rather
than a tag push — so the workflow can only ever add a file to a publication a
person made. It has no path by which it publishes anything of its own. It then:

1. runs the same checks a pull request runs, by calling `validate.yml` rather
   than restating them;
2. refuses to continue if the release tag and `__version__` disagree, because
   those are the two things anybody quotes and they must not diverge silently;
3. builds the artefact, records its SHA-256 beside it, and rebuilds from scratch
   to prove the two are byte-identical — a digest published next to a file
   nobody can reproduce means nothing;
4. attaches both to the release, from a separate job.

The separation is the security property, not tidiness. Building means
installing dependencies and executing this repository at the released ref, and a
job holding a write credential while doing either is a job where a compromised
dependency can push to the repository — `actions/checkout` persists the token in
`.git/config` unless told not to. So the build runs with `contents: read` and no
persisted credential, and the only job that can write checks nothing out,
installs nothing, and runs no Python: a download and one `gh` call.

`workflow_dispatch` runs all of it and publishes nothing. The publishing job is
guarded on the job rather than the step, so a dispatch never creates a runner
holding a write credential at all — it cannot publish, rather than declining to.
The file is kept on the run for seven days so it can be inspected without a
release existing.

Verify a downloaded artefact with:

```bash
sha256sum -c harrier-<version>.html.sha256
```

## Status

**0.4.0.** The taxonomy is complete and the artefact is a companion to the
standard rather than a workspace about a target.

- **99 topics across 13 domains**, every resolvable WSTG identifier claimed by
  at least one, with the boundaries between neighbouring topics written down.
- **366 Test Units**, each with an identifier and a falsifiable objective; 10
  written to full depth.
- **177 capabilities** and the chain they derive: every unit declares what makes
  it possible and what it establishes, every condition in the graph has a route
  to it, and no unit names another unit anywhere.
- **One self-contained HTML file** carrying all of it, including every card,
  payload and mitigation. It fetches nothing and stores nothing, which is the
  point: it is opened from disk on an engagement network.

**0.4.0 is a breaking change to the artefact.** The stateful board — target
input, held facts, recorded results, run export and import — has been removed,
and run files written by 0.3.0 cannot be read. That is deliberate, it is taken
during the pre-1.0 period so it can be taken at all, and the reasoning is
recorded in [`docs/PIVOT.md`](docs/PIVOT.md).

What is not done, and both are visible in the product rather than only here:

- **Depth.** Ten units of 366 are written in full and the rest carry an
  objective and nothing more. That is deliberate — see the standing rule in
  [`docs/ROADMAP.md`](docs/ROADMAP.md).
- **The far half of the chain.** 78 of 177 capabilities are established by a
  test and used by none — impacts excluded, since those are where a chain is
  meant to end. So of 366 tests, 138 have a potential continuation, 7 establish
  an impact, 182 stop short, and 39 declare no capability at all. Phase 5
  charted reconnaissance through to primitives; primitive-to-impact is largely
  unwritten. Both the Attack Chains page and `harrier chain` report the split,
  rather than letting a reader meet it one dead end at a time.

## Licence and attribution

Apache-2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

Harrier is not affiliated with, endorsed by, or sponsored by OWASP. WSTG and
ASVS identifiers, titles and section headings are referenced for cross-mapping
and navigation only; no prose from either is reproduced here. Both are
share-alike licensed, and everything in this repository is originally written.

CWE is used under the [CWE Terms of Use](https://cwe.mitre.org/about/termsofuse.html).
Copyright (c) 2006-2026, The MITRE Corporation. CWE is a trademark of The MITRE
Corporation. See [`NOTICE`](NOTICE).
