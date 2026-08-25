# Harrier

> A complete, non-overlapping decomposition of web application security testing
> into named, addressable test units — each with the one thing that proves it,
> and the notes a practitioner needs to perform it without re-reading a textbook.

[![licence](https://img.shields.io/badge/licence-Apache--2.0-green)](LICENSE)
[![WSTG](https://img.shields.io/badge/WSTG-109%20pinned-informational)](standards/wstg.yaml)
[![ASVS](https://img.shields.io/badge/ASVS-5.0.0%20pinned-informational)](standards/asvs.yaml)
[![CWE](https://img.shields.io/badge/CWE-4.20%20pinned-informational)](standards/cwe.yaml)
[![phase](https://img.shields.io/badge/phase-2%20of%207-lightgrey)](docs/ROADMAP.md)

## What this is

Published testing standards are exhaustive at the wrong granularity. One WSTG
identifier is a chapter, not a task: `WSTG-INPV-01` covers six materially
different tests with different payloads, different oracles and different
outcomes. So a practitioner reads it once, then works from personal notes —
which is where coverage quietly goes.

Harrier is the missing layer between the standard and the work: the complete set
of distinct tests, at the granularity a person actually performs them, each with
a stable name, an explicit boundary against its neighbours, and a one-sentence
statement of what settles it.

## What this is not

- **Not a tutorial.** The reader already knows what cross-site scripting is.
  PortSwigger's Academy teaches it better than this ever will, and has labs.
- **Not an automation tool.** Nothing here scans, exploits, or talks to a target.
- **Not another vulnerability encyclopedia.** The content is the second layer.
  The taxonomy is the product.

## Who it is for

An experienced tester who is not learning the technique but recovering a detail
they knew six months ago. Cards are written for **recall**, not for reading:
oracle, sequence, payload pointer, the first false positive, and what counts as
finished — on one screen, with the explanation collapsed underneath.

## Scope

Web application testing, not the WSTG table of contents. WSTG is used as a
coverage skeleton — proof that nothing standard is missing — but a large part of
current practice has no WSTG identifier at all: JWT, OAuth and OIDC, GraphQL,
WebSocket, HTTP request smuggling, cache poisoning and deception, prototype
pollution, race conditions, dependency confusion, cloud metadata, and
LLM-integrated surfaces. Those are in scope and carry Harrier identifiers of
their own.

## Structure

| Directory | Holds |
|---|---|
| `docs/` | The model, the naming methodology, the authoring rules, the roadmap |
| `harrier/` | The validator and its schemas — the only executable code here |
| `standards/` | Pinned WSTG, ASVS and CWE references — generated, never hand-edited |
| `vocab/` | Controlled vocabularies: domains, axes, surface tags, dimensions |
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

python -m unittest discover -s tests -t .   # 137 tests, offline
python -m harrier validate                  # the repository
python -m harrier coverage                  # the counts the roadmap publishes
python -m harrier chain HRR-INJ-01-UNION    # what a unit needs, gives and opens
python -m harrier build -o harrier.html     # the artefact
```

Both of the first two must pass; CI runs exactly them.
[`docs/VALIDATION.md`](docs/VALIDATION.md) explains what is checked and why each
rule is mechanical rather than a review comment.

## Status

**0.1.0.** The taxonomy is complete and the artefact exists.

- **99 topics across 13 domains**, every resolvable WSTG identifier claimed by one, with the boundaries between neighbouring topics written down.
- **366 units**, each with an identifier and a falsifiable objective; 10 of them written to full depth.
- **177 facts** and the chain they derive: every unit declares what makes it possible and what it establishes, and every condition in the graph has a route to it.
- **One self-contained HTML file** carrying all of it, including every card, payload and mitigation. It fetches nothing, which is the point: it is opened on an engagement network.

What is not done: depth. Ten units of 366 are written in full, and the rest
carry an objective and nothing more. That is deliberate -- see the standing rule
in [`docs/ROADMAP.md`](docs/ROADMAP.md) -- but it is what the next release is
for.

The level below — the units a person actually performs — is being written now, in
batches of two or three domains. **223 units exist across six domains**; the remaining eleven domains are outstanding.
[`docs/ROADMAP.md`](docs/ROADMAP.md) carries the plan and the definition of 1.0.

## Licence and attribution

Apache-2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

Harrier is not affiliated with, endorsed by, or sponsored by OWASP. WSTG and
ASVS identifiers are referenced for cross-mapping only; no prose from either is
reproduced here. Both are share-alike licensed, and everything in this
repository is originally written.

CWE is used under the [CWE Terms of Use](https://cwe.mitre.org/about/termsofuse.html).
Copyright (c) 2006-2026, The MITRE Corporation. CWE is a trademark of The MITRE
Corporation. See [`NOTICE`](NOTICE).
