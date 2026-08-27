# Architecture

The model, and the reasoning behind each part of it. `TAXONOMY.md` fixes the
identifiers and vocabularies; `AUTHORING.md` states the rules for writing.

---

## 1. Entities

```
Domain        navigation grouping            "Server-side injection"
  Topic       a coherent subject             "SQL injection"
    Unit      an atomic performed test       "UNION-based extraction"
      Dimension   a parameterisation of it   engine = mysql | postgresql | ...
```

Three things hang off units rather than living inside them:

```
Card          recall-first prose, shared by every unit that needs it
Payload set   the only place a payload is written
Mitigation    attached to the weakness class, not to the test
```

A **topic** is roughly what a published standard calls one test. A **unit** is
what a person actually performs and records a separate result for. The gap
between those two is the whole point of this project — see §2.

## 2. The unit boundary rule

> One published test identifier is never assumed to be one test.

A candidate is a **unit** when all three hold:

1. **Separately recordable.** It can come out clean while a sibling comes out
   vulnerable.
2. **Non-substitutable.** Performing a sibling does not perform it.
3. **One oracle.** A single sentence states what proves it, with no "or".

Fails (3) → it is two units. Fails (2) → it is a *dimension* of its sibling.
Fails (1) → it is a step inside a unit, not a unit.

## 3. The axis rule — what to split on

Most topics can be cut several ways. The cut is not a matter of taste:

> **Split on the axis that changes the payload and the oracle.**
> **Keep as a dimension the axis that only changes delivery.**

Worked, because it is the case that motivated the whole model:

**Cross-site scripting** has two candidate axes at once — where the input comes
from (reflected / stored / DOM) and where it lands (HTML body, attribute, script
string, URI, CSS, markup-only). Six sinks × three sources is eighteen cells,
which is unusable as eighteen units and useless as one.

The sink decides what you must escape and what proves execution — payload *and*
oracle. The source only decides where you paste it. So **the sink is the unit,
the source is a dimension**: six units, nothing lost.

**SQL injection** cuts the other way. The technique (error / boolean / time /
union / out-of-band) changes the oracle completely; the engine (MySQL,
PostgreSQL, ...) changes only payload syntax. So **technique is the unit, engine
is a dimension**: seven units instead of thirty-five.

## 4. Overlap: canonical home, not zero overlap

Overlap in web testing is inherent, not a symptom of bad taxonomy. Reflected XSS
into an attribute and DOM XSS into the same attribute share a payload. CSRF,
state-changing `GET`, and a permissive `SameSite` are three names for one
reality. Finding injectable JSON fields is shared work across SQL, NoSQL, OS
command, template and XML injection.

A taxonomy that promises **zero overlap** will spend its life in boundary
arguments and produce nothing. So the rule is weaker and achievable:

> Every unit has exactly **one canonical home**. Every other place that touches
> it carries a `see_also` reference and a one-line boundary statement.

The target is **zero duplicated content**, not zero conceptual overlap. Boundary
statements are recorded even when they point at something not yet written — that
keeps a gap visible instead of letting it read as covered.

## 5. Two shapes that do not fit the unit model

Forcing everything into "perform a test, reach a verdict" produces category
errors that a practitioner spots immediately. Two kinds are declared explicitly:

**`kind: recon`** — establishes a fact rather than judging the target.
Fingerprinting a server, mapping a workflow, enumerating a GraphQL schema. Its
output is a *discovered fact* that other units consume. It has no oracle, and
declaring one is rejected.

**`kind: inquiry`** — target-specific by nature; no generic procedure exists.
Business logic is the whole of this category. "Can the steps be reordered?" "Is
the price trusted from the client?" "Can the counter go negative?" A unit here
carries a **list of questions to ask of the workflow in front of you**, not a
procedure. Pretending otherwise produces a card that is either trivially generic
or secretly about someone else's application.

Everything else is `kind: test` and carries an oracle.

### `role`: a step beside the others, or one of them

`kind` says what a unit is. `role` says how it stands to the rest of its topic,
and every unit declares one:

**`role: stage`** — performed alongside the topic's other stages. Probing that
the condition exists, fingerprinting the engine, defeating the filter that masks
a result: you do each of them, in the order the topic sets.

**`role: variant`** — one of the alternatives the topic's primary axis
enumerates. Boolean inference, UNION extraction and time-based inference are
three routes to one finding, and a tester picks among them on the evidence in
front of them rather than working through all seven.

Which one a unit gets follows from what its axis says about its own slugs.
`technique` is the axis that describes alternatives: "chosen from observed
evidence rather than all executed". Every other axis describes a list to work
through — `property` says each of its properties is "separately recordable",
`principal` says a clean result for one caller "says nothing about the others".
So the techniques of a topic are its variants and the rest of it is stages.

The distinction was therefore always derivable and nowhere in what a reader was
shown. Ten units under one heading, with "perform all of these" and "pick one of
these" indistinguishable, is a list that has to be opened ten times to be read
once.

It is required rather than derived at render time. Deriving it would tie the
reading of a unit to the slug someone happened to give it, and leave no way to
record that a particular unit is an exception to the pattern its slug implies.

## 5b. The standard is linked in both directions

A topic names the test cases it claims, in `refs.wstg`. That is the direction an
author writes in, and it is the only direction the repository held: answering
"which units cover `WSTG-INPV-05`" meant walking every topic, and nothing but the
built HTML file did it.

`standards/wstg-index.yaml` is that walk, generated by `harrier index` and
**committed**. Both halves are the point. Generated, so it cannot drift from the
catalogue it describes -- `harrier index --check` fails when it has, and the
suite asserts the committed bytes are what the catalogue derives. Committed, so a
change in coverage appears in a pull request diff rather than inside a build
output nobody reviews. A relation that only a build can see is a relation nobody
reviews.

Every pinned test case gets a row, including the one no topic claims. A row that
disappeared when coverage was lost would hide the change worth seeing: the file
would simply be shorter and still look complete.

The relation is many-to-many in both directions, and the file represents it as
such. Thirteen topics claim more than one test case; five test cases are spread
across more than one topic. `WSTG-APIT-99` is claimed by four, in four domains,
because it really is reconnaissance and authorization and business logic and
injection at once -- and a representation forced to pick one would be wrong five
times over.

## 6. Durable and volatile content are separated

Security content rots in roughly eighteen months, and three hundred stale cards
are worse than none — they teach superseded technique under the project's name.
The only structure a small team can keep alive is one that separates what rots
from what does not:

| Durable — lives in the unit and the card | Volatile — lives in dated side files |
|---|---|
| The mechanism: why this is possible at all | A specific payload string |
| The oracle: what proves it | A specific WAF or filter bypass |
| Common false positives | Engine and browser quirks |
| The order the steps must go in | Tool flags and versions |

Volatile files carry a `reviewed` date. The durable layer does not need one.

## 7. Card shape — written for recall, not for reading

The reader is an experienced tester mid-engagement. They are not learning what
XSS is; they are recovering a detail they knew six months ago. Every card is
therefore two layers, in this order:

**Recall block** — scannable in about ten seconds:

- **Oracle** — one line: what observation settles it
- **Sequence** — three to six imperative steps, in the order they must happen
- **Payloads** — a pointer, never inline
- **First false positive** — the one that catches people
- **Done when** — one line: what proves the test was actually performed

**Depth block** — collapsed by default:

- Why the sequence is ordered that way
- What to do when a step does not behave
- Edge cases, engine differences, known bypasses

If the recall block does not fit on a laptop screen without scrolling, the unit
is too big and rule §2 was applied too loosely.

## 8. Navigation — the standard, then the tests inside it

A tester arrives with a standard they are working through and a line item that
is too coarse to perform. Everything here follows from treating *what is
actually inside this test case, and where does a success lead* as the product's
job.

The old model is recorded in [`PIVOT.md`](PIVOT.md), along with why it was
rejected. In short: it asked the tester to describe their target, then made
claims about that target from what they had ticked. Harrier has never seen the
target, and a product that talks as though it has will eventually be believed.

### Standard-first

```
Standard → Testing group → WSTG test case → Test Units → Test Unit detail
```

The artefact opens on **Standards**. WSTG is the initial execution standard;
the internal shape allows another to be added, and none is. Groups appear in the
standard's own order, pinned with the identifiers in `standards/wstg.yaml`,
because a navigation order invented from an identifier prefix would silently be
this project's opinion presented as the standard's. That order is the standard's
default coverage structure and is described as that — not as a mandatory
workflow.

A **test case page** is the bridge. It carries the pinned identifier and
official title, the Harrier topic or topics that claim it, and the Test Units
each of those decomposes it into, in the order the topic declares. One
identifier may resolve to several topics in several domains — `WSTG-APIT-99` is
reconnaissance, authorization, business logic and injection at once — and the
page shows all of them rather than forcing a one-to-one relationship. An
identifier the domain map deliberately does not resolve says so instead of
rendering as an empty page.

Content with no WSTG identifier appears under **Harrier Extensions**. It is the
home for beyond-WSTG material, and it exists before that material does so the
material never has to be filed somewhere it does not belong.

### The Test Unit detail

The most important page in the product, and ordered by what a person needs in
the order they need it: title, what it is for, why it is a separate test at all,
what has to be in place, what settles it, how to perform it, what will fool you,
what counts as finished, where to stop, then payloads, tools, depth, mitigation,
mappings, and the local chain. The objective, the oracle, the first false
positive and the safety boundary are never behind an identifier or a taxonomy
label.

"Test Unit" is the term in this document and in the schemas. The page says
*test* or *atomic test*, which reads better and cannot be confused with a unit
test in the software sense.

An outline unit stays useful: its objective and its position in the chain are
real, and the page says the procedure has not been written rather than filling
the gap with something plausible.

### The local chain

Every Test Unit carries a graph derived from the four chain fields — never a
stored edge list. Five ranks:

```
tests that establish a prerequisite → prerequisites → this test
    → what success establishes → tests that capability may make relevant
```

Capabilities are the intermediate nodes, so the reason for every edge is on the
screen. Hard prerequisites and `motivated_by` are drawn differently, because a
hint that looks like a gate is the failure the two fields exist to prevent. A
unit may have several routes in and several out, and the drawing does not
flatten that into a line. Three per side initially, with *Show more* when there
is more; the whole catalogue is never drawn around one unit.

Each continuation states **what succeeding here does not supply**. Being reached
through one capability is not the same as being possible: the page names the
other conditions and does not claim they hold. The continuations are
deliberately *not* ordered by how few of those remain — that ordering sorts
every conditional continuation below the three a reader sees, and the conditions
are the honest half.

Where a capability is an impact, or where nothing in the catalogue consumes it,
the page says the result is terminal or reportable. An empty graph with no
explanation reads as missing data; an impact is not missing data.

Beneath it, **if this test is unsuccessful** — read from `closes`, from the
other producers of the same capability, and from the sibling tests in the topic.
A clean UNION result does not mean there is no SQL injection while boolean and
timing routes remain untried, and the page is the thing that has to say so. No
result is offered, recorded or stored: this is interpretation, not bookkeeping.

### The general graph

`Attack Chains` is for understanding the model, not for working. Three hundred
and sixty-six units and a hundred and seventy-seven capabilities drawn at once
is a picture of nothing, so the entry point is the seven fact families and how
often a test spans one to another. From there: a family, a capability, the tests
that establish and consume it, and the shortest routes from it to an impact.
Progressive disclosure throughout — useful omission beats completeness in one
image on a laptop screen.

### Search

Everything the file carries: test cases, tests, topics, capabilities, payloads,
cards, mitigations and tools. Every result says what kind of thing it is and
where it goes. Search is retrieval; the tests inside a test case are reached by
navigating to the test case, never by having to search for them.

### Naming what is shown

Titles lead and identifiers follow. An identifier is how two people refer to the
same test and how a finding is written down — it is not what a tester reads. The
same holds for capabilities: a unit needs *"the session identifier is known"*,
not `recon.session.identified`. The word *fact* is internal; the page says
capability or condition.

### Wording is part of the model

The chain is generic. It says a test requires conditions, that success
establishes capabilities, and that those capabilities may make other tests
relevant. It never says *you hold this*, *unlocked*, *available now*, *ruled out
for this target*, or *completed*. The vocabulary is prerequisite, previous
possibility, resulting capability, potential continuation, becomes relevant
when, additional condition, alternative route, may lead to.

This is not house style. Target-state wording is how the rejected model comes
back — as a phrase first, then as the feature that phrase implies — so the suite
asserts on its absence in the rendered page.

### The command line describes the same model

`harrier chain` reads the derivation in `chain.py`, which is the same one the
artefact reads. That is not a tidiness argument: a command line that still asked
what the tester held and answered with what was *available* would leave the
product carrying two contradictory models one step apart, and whichever a reader
met first is the one they would believe. So `--held`, `available` and `unlocks`
went with the board, and the tool prints prerequisites, established capabilities,
potential continuations and what each still owes — in the page's words.

### One file, and it reaches for nothing

The published artefact is a **single self-contained HTML file**: no external
stylesheet, script, font or image, and no network call of any kind. It is opened
from disk on an engagement network, and a request to a third party would tell
that party which target is being tested and when. A `Content-Security-Policy`
names the three inline blocks by content hash and denies everything else,
`connect-src` included, so the guarantee is enforced by the browser rather than
only by review.

## 9. Repository layout

```
docs/
  ARCHITECTURE.md   this document: the model and why it is shaped this way
  TAXONOMY.md       identifiers, domains, axis vocabularies
  AUTHORING.md      the rules for writing a unit or a card
  CHAINING.md       how one test leads to the next, and why no unit names another
  VALIDATION.md     what the validator checks, and why each rule is mechanical
  ROADMAP.md        build state; updated in the same change as the work
  PIVOT.md          why the engagement board was removed, and what replaced it

harrier/            the validator and the builder -- the only executable code
  chain.py          the derived attack graph; nothing about it is stored
  build.py          catalogue, derived indexes, and safe embedding into one file
  artefact/         the page itself: template.html, app.css, app.js
  schema/           nine JSON Schemas, selected by a document's location
tests/              offline suite; mutation tests copy the repository itself

standards/          published standards this project cross-references
  wstg.yaml         pinned identifiers and titles; generated, never hand-edited
  wstg-map.yaml     every WSTG identifier resolved to a domain, with the rule
  cwe.yaml          weakness classes                         (phase 1)
  asvs.yaml         requirements, for mitigation cross-reference  (phase 1)

vocab/              controlled vocabularies
  domains.yaml      the frozen domain codes
  axes.yaml         the axis slug vocabularies
  surfaces.yaml     attack-surface tags, with discovery hints
  dimensions.yaml   engines, browsers, delivery, platforms

knowledge/          the taxonomy and the units
  <domain>/
    HRR-INJ-01.topic.yaml
    HRR-INJ-01-UNION.unit.yaml

cards/              recall-first prose, organised by technique
payloads/           the only place a payload is written
toolbox/            tool invocations and per-flag rationale
mitigations/        remediation text, per weakness class
```

Domain directories are named by their frozen code so a grep for an identifier
lands in the right place.
