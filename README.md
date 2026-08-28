# Harrier

**WSTG tells you what to cover. Harrier shows you the real tests inside each
test case, and where a successful one may lead.**

An offline execution companion for web application security testing standards.
It breaks broad standard test cases into atomic, separately addressable **Test
Units**, and derives the attack-chain continuations each success may open.

> **Harrier 0.10.0 is an early public alpha.** The WSTG decomposition is broad —
> every resolvable identifier is claimed, and 374 Test Units exist. The depth
> behind them is not: 10 units are written to full procedural depth and 2 are
> sketched, and what a defeated control permits is largely unwritten. [What that
> means in numbers](#what-exists-today-and-what-does-not) is below, not buried at
> the end.

[![licence](https://img.shields.io/badge/licence-Apache--2.0-green)](LICENSE)
[![version](https://img.shields.io/badge/version-0.10.0-blue)](docs/ROADMAP.md)
[![WSTG](https://img.shields.io/badge/WSTG-109%20pinned-informational)](standards/wstg.yaml)
[![ASVS](https://img.shields.io/badge/ASVS-5.0.0%20pinned-informational)](standards/asvs.yaml)
[![CWE](https://img.shields.io/badge/CWE-4.20%20pinned-informational)](standards/cwe.yaml)

---

## The problem

A testing standard is a coverage structure. It is very good at that, and WSTG in
particular is the reason nothing standard goes missing from a scope. But two
things a working tester needs sit outside what a coverage structure is for, and
Harrier exists for exactly those two.

**A test case is not a test.** `WSTG-INPV-05` is one line on a checklist and ten
materially different tests in practice — a probe, an engine fingerprint, five
inference and extraction techniques, a stacked-statement variant, a second-order
variant, and a filter-evasion pass. Each has its own payloads, its own oracle,
and its own separately recordable result. A checklist that ticks once for all ten can be complete while most of
the work was never done, and nothing in it will say so. Harrier makes those
tests explicit, individually named, and bounded against each other.

**A result is not the end of the test.** Establishing that a parameter reaches a
SQL statement is not a finding on its own; it is a capability that makes several
other tests worth performing. Standards enumerate test cases as independent line
items, so that relationship lives only in the tester's head and leaves with them
when they move to the next line. Harrier writes each test's prerequisites and
established capabilities down, and derives the connections between them.

Neither is a criticism of the standard. A coverage structure that also tried to
be a decomposition and an attack graph would be worse at the thing it is for.
Harrier is the layer that sits on top of one.

## Standard-first, by construction

Navigation starts at the standard, not at Harrier's own taxonomy:

```
Standard → Testing group → Test case → Harrier Test Units → Potential continuations
```

WSTG is the first standard supported, and the structure is deliberately not
specific to it. A newer WSTG revision, or another execution standard, enters at
the top of that path and reuses everything below it: identifiers are pinned per
standard, and a Test Unit is filed under whichever test case claims it. A Harrier
topic with no test case in the current standard is not lost — it appears under
**Harrier Extensions**, which is where beyond-WSTG material goes as it is
written.

OWASP Top 10 is a different shape and would enter differently. It classifies
risk rather than prescribing execution, so it belongs as a **lens over the same
catalogue** — a way of reading tests you already have — rather than a second way
to navigate to one. That distinction is recorded in
[`docs/PIVOT.md`](docs/PIVOT.md) rather than left to be re-litigated.

## The vocabulary

Five words carry the model, and they are worth two minutes.

| | |
|---|---|
| **Test case** | The standard's unit of coverage. `WSTG-INPV-05`, "Testing for SQL Injection". Identifier and title come from a pinned copy of the standard. |
| **Topic** | Harrier's subject boundary inside a test case — "SQL injection" — declaring the axis its tests are split on and notes marking what belongs to a neighbouring topic instead. One test case may be claimed by several topics; `WSTG-APIT-99` is claimed by four. |
| **Test Unit** | The atomic thing a person performs and records one result for. `HRR-INJ-01-UNION`, "UNION-based extraction". It has an objective that can be wrong, a boundary against its siblings, and — where written to depth — an oracle, a sequence, payloads, false positives and a safety limit. |
| **Capability** | What a success establishes, or what a test needs before it is possible at all. "A parameter reaches a SQL statement." Capabilities are the join keys: no Test Unit ever names another Test Unit. |
| **Impact** | A business outcome. Terminal by construction — nothing may require one, and the validator enforces it. |

Two kinds of relationship, kept apart because conflating them is the failure the
distinction exists to prevent: a **declared prerequisite** is a condition of the
test being performable at all, and a **motivation** makes it worth reaching for
sooner without ever being a gate.

**Harrier has no view of your target.** It has never seen it and does not ask
about it. Every chain statement is about the relationship between two tests —
*potential continuation*, *may become relevant*, *no additional declared hard
prerequisite* — never a claim that something is true of an application. A
continuation always names what succeeding here does **not** supply, because
being reached through one capability is not the same as being possible.

## What it looks like

A test case, decomposed into the tests inside it, in the order the topic
declares — and separated into the ones you perform in sequence and the ones you
choose between, because those are opposite instructions:

![A WSTG test case decomposed into its Test Units, split into stages and alternatives](docs/assets/decomposition.png)

A Test Unit. The chain strip under the objective answers *where can this lead*
before the procedure begins, rather than several screens after it:

![A Test Unit page showing its objective and chain strip](docs/assets/test-unit.png)

The Attack Chains view. A row is a capability a test requires, a column is one
its success establishes, and the number is how many tests span the two — a map
of what the catalogue declares, not a route anyone should follow:

![The capability-family transition matrix](docs/assets/attack-chains.png)

## Try it

There is no downloadable release yet. Build it from source:

```bash
git clone https://github.com/kabiri-labs/harrier.git
cd harrier
python -m pip install "PyYAML>=6,<7" "jsonschema>=4,<5"

python -m harrier validate          # the catalogue is internally consistent
python -m harrier build             # writes harrier.html
```

Open `harrier.html` from disk. It is one self-contained file: no server, no
install, no network.

The same graph reads from the command line:

```bash
python -m harrier chain HRR-RES-01-READ
```

```
HRR-RES-01-READ  Confirmed read outside the intended root
  prerequisite (all of): A parameter selects a file by path -- 1 test(s) establish it
  worth doing sooner given: The application's absolute path is known -- 2 test(s) establish it
  success establishes: Arbitrary file read
  potential continuations:
    HRR-RES-01-EXEC  Inclusion and execution of the resolved path
      requires what this establishes: Arbitrary file read
      no additional declared hard prerequisite
```

## A real journey

The one topic written to full depth is path traversal, under `WSTG-ATHZ-01`.
From the standard down:

1. **Authorization Testing → `WSTG-ATHZ-01`**, "Testing Directory Traversal File
   Include". Harrier decomposes it into five Test Units.
2. **`HRR-RES-01-PROBE`** — does a traversal sequence in the parameter change
   which file is opened? Success establishes *a parameter selects a file by
   path*.
3. **`HRR-RES-01-READ`** — is content the application never meant to serve
   returned in the response body? It declares the probe's capability as a
   prerequisite, and two other tests as motivations: knowing the application's
   absolute path, and knowing how the path filter behaves. Success establishes
   *arbitrary file read*.
4. **`HRR-RES-01-EXEC`** — is the resolved path included and executed rather than
   returned? Reached through *arbitrary file read*, with no additional declared
   hard prerequisite. Success establishes *server-side code execution*.
5. **`HRR-OUT-02-IMPACT`** — what does the executing context actually reach: which
   account, which files, what answers from the network behind it? Reached through
   *server-side code execution*, and where this chain ends.

The last step is a question rather than a claim, and deliberately so. Harrier has
not seen the host and cannot say what the code would reach on it; what it can say
is that reaching this far means the question is now worth asking, and which
capability made it worth asking.

Four of the five capabilities in that chain are still declared by nothing beyond
it — the outcome layer covers what the catalogue's primitives obtain, not every
control it records. Where a chain still stops early, the page says so rather than
drawing an edge nobody wrote.

## What exists today, and what does not

Every figure here is read from the repository by the test suite, so it cannot go
stale in this file without the suite failing.

| Taxonomy | |
|---|---|
| WSTG identifiers pinned | 109, across 12 testing groups |
| Claimed by a Harrier topic | 108 of 108 resolvable |
| Topics | 106, across 14 domains |
| Test Units | 374 |
| Written to full procedural depth | **10** |
| Sketched | 2 |
| Outline only | 362 |

| Chain | |
|---|---|
| Capabilities | 185 |
| Derived unit-to-unit edges | 646 |
| — of them escalations between capabilities | 290 |
| — another technique for the same test | 124 |
| — a general prerequisite, not a step | 232 |
| Tests with a potential continuation | 211 |
| Tests that establish an impact | 14 |
| Tests that stop short | 110 |
| Tests declaring no capability | 39 |
| Capabilities used by no test, impacts excluded | 53 of 185 |
| Capabilities with a charted route to an impact | 90 of 175 |

The four test counts partition the catalogue exactly, which is what stops any one
of them from quietly coming to mean something else.

**Depth runs in three tiers, and every page says which one it is looking at.**
An **outline** Test Unit carries an identifier, a falsifiable objective, its
boundary against neighbouring tests, and its position in the chain — enough to
stop a test being skipped silently, and enough to appear in every count above.
A **sketched** unit adds what it takes to run the test and recognise a wrong
answer: the steps, what a positive and a negative result look like, the mistake
that most often imitates a positive, and what finishing means. An **authored**
unit adds when it is worth entering, what must hold first, what is recorded, and
how far to take it. What each tier requires is checked by the validator rather
than claimed, and nothing is invented to fill the gap.

**The largest known gap is now the controls.** `primitive → impact` is written:
one capability of thirty-two is still declared as a use by nothing, and 90 of
175 capabilities have a charted route to an impact. `control → impact` is not,
and 39 of 59 `control.*` facts are established by a test and consumed by
nothing. A control is the state of a defence rather than a result, so the step
that turns one into an outcome has to be written before an edge can be drawn
from it.

This is recorded rather than filled in. Generating plausible edges would make the
matrix look complete and every route on it untrustworthy — an edge nobody thought
about is indistinguishable from one that was checked, and the second is the only
reason the first is worth reading. See [`docs/ROADMAP.md`](docs/ROADMAP.md).

## What Harrier is not

- **Not a scanner or an exploit framework.** Nothing here scans, exploits, or
  talks to a target.
- **Not a reporting platform or an engagement tracker.** It holds no target, no
  engagement, no results and no findings.
- **Not a target-aware recommendation engine.** It cannot tell you what to test
  next on your application, because it knows nothing about your application.
- **Not a replacement for judgement.** It tells you what a standard line item
  contains and what a success may open; deciding which of that applies today is
  the tester's, and that is where the knowledge is.
- **Not affiliated with, endorsed by, or sponsored by OWASP.**
- **Not a tutorial.** The reader already knows what cross-site scripting is.

Version 0.3.0 shipped a stateful board that asked for a target and claimed to
know what was reachable on it. It was removed; why is in
[`docs/PIVOT.md`](docs/PIVOT.md).

## Security and privacy properties

The artefact is opened from a laptop on an engagement network, so the property
that matters is that it emits nothing anyone monitoring that network could
observe.

- **One self-contained HTML file.** No external stylesheet, script, font or
  image — everything is embedded.
- **No outbound request of any kind.** A hash-based `Content-Security-Policy`
  names the three inline blocks in the file and denies everything else,
  `connect-src` included. `frame-ancestors` is deliberately absent: it is ignored
  when a policy is delivered in a `meta` element, and a directive that cannot
  take effect reads as a control that is in place.
- **No target or engagement data, ever.** No results are recorded, no run is
  imported or exported, and nothing is written to `localStorage`.
- **Verified as behaviour, not as text.** The suite drives a real browser over
  `file://` through the primary journeys — typing in search, clicking a node in
  the graph, expanding a bounded view — while recording every request the page
  attempts and every console error. Both come back empty.

## Contributing

Read [`docs/AUTHORING.md`](docs/AUTHORING.md) for what a Test Unit must contain,
[`docs/CHAINING.md`](docs/CHAINING.md) for the chain semantics,
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the model, and
[`docs/VALIDATION.md`](docs/VALIDATION.md) for what is checked mechanically.

**A chain edge is a security claim.** Declaring a capability a prerequisite
asserts the test is not performable without it. Declaring that a success
establishes a capability asserts the result proves that much and no more. Both
are judgements a reader will rely on, so bulk or speculative edge generation is
not acceptable here.

Before opening a pull request:

```bash
python -m unittest discover -s tests -t .
python -m harrier validate
```

Both must pass, and CI runs exactly them. Two runners inside the suite are
optional locally and installed in CI: `node` executes the artefact's own graph,
layout, path-walk and search functions against the real catalogue, and a browser
driven through Playwright uses the built file. Install them with:

```bash
python -m pip install playwright && python -m playwright install chromium
```

## Standards, attribution and licence

Apache-2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

Harrier is not affiliated with, endorsed by, or sponsored by OWASP. WSTG
identifiers, official test titles and testing-group headings are referenced for
navigation and cross-mapping only, from a copy pinned by commit and SHA-256. No
prose from WSTG or ASVS is reproduced anywhere in this repository; both are
share-alike licensed, and everything here is originally written.

ASVS is referenced as a control and remediation mapping. CWE is referenced as a
weakness classification, used under the
[CWE Terms of Use](https://cwe.mitre.org/about/termsofuse.html). Copyright (c)
2006-2026, The MITRE Corporation. CWE is a trademark of The MITRE Corporation.
See [`NOTICE`](NOTICE).
