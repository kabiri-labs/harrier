# Harrier

> A complete, non-overlapping decomposition of web application security testing
> into named, addressable test units — each with the one thing that proves it,
> and the notes a practitioner needs to perform it without re-reading a textbook.

[![licence](https://img.shields.io/badge/licence-Apache--2.0-green)](LICENSE)
[![WSTG](https://img.shields.io/badge/WSTG-109%20pinned-informational)](standards/wstg.yaml)
[![ASVS](https://img.shields.io/badge/ASVS-5.0.0%20pinned-informational)](standards/asvs.yaml)
[![phase](https://img.shields.io/badge/phase-1%20of%207-lightgrey)](docs/ROADMAP.md)

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
| `standards/` | Pinned WSTG and ASVS references — generated, never hand-edited |
| `vocab/` | Controlled vocabularies: domains, axes, surface tags, dimensions |
| `knowledge/` | The taxonomy: topics and units |
| `cards/` | Recall-first prose, organised by technique |
| `payloads/` | The only place a payload is written |
| `toolbox/` | Tool invocations with per-flag rationale |
| `mitigations/` | Remediation text, keyed by weakness class |
| `tests/` | Offline suite; mutation tests copy the repository and break one thing |

Start with [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), then
[`docs/TAXONOMY.md`](docs/TAXONOMY.md).

## Working on it

```bash
pip install PyYAML jsonschema

python -m unittest discover -s tests -t .   # 80 tests, offline
python -m harrier validate                  # the repository
python -m harrier coverage                  # the counts the roadmap publishes
```

Both of the first two must pass; CI runs exactly them.
[`docs/VALIDATION.md`](docs/VALIDATION.md) explains what is checked and why each
rule is mechanical rather than a review comment.

## Status

Phases 0 and 1 of seven: the model, the vocabularies and the machine checks are
settled. All 109 WSTG identifiers are pinned and resolved to a domain; no content
has been written yet. [`docs/ROADMAP.md`](docs/ROADMAP.md) carries the plan and
the definition of 1.0.

## Licence and attribution

Apache-2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

Harrier is not affiliated with, endorsed by, or sponsored by OWASP. WSTG and
ASVS identifiers are referenced for cross-mapping only; no prose from either is
reproduced here. Both are share-alike licensed, and everything in this
repository is originally written.
