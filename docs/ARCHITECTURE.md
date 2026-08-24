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

## 8. Navigation — surface-first

A tester mid-test does not browse by standard. Ranked by actual use:

1. **By surface.** *"There is a login form in front of me — what applies?"*
   This is the default entry point, and it is why surface tags are a first-class
   controlled vocabulary rather than a loose set of labels.
2. **By search.** Three characters to a payload.
3. **By signal.** *"I saw this response behaviour — what does it mean, what next?"*
4. **By standard.** WSTG, CWE, ASVS coverage views. Real, but its audience is
   report-writing and scoping, not testing.

The published artefact is a **single self-contained HTML file**: no external
stylesheet, script or font. It is opened from a laptop on an engagement network
and must not emit a request a monitored target could observe.

## 9. Repository layout

```
docs/
  ARCHITECTURE.md   this document: the model and why it is shaped this way
  TAXONOMY.md       identifiers, domains, axis vocabularies
  AUTHORING.md      the rules for writing a unit or a card
  VALIDATION.md     what the validator checks, and why each rule is mechanical
  ROADMAP.md        build state; updated in the same change as the work

harrier/            the validator -- the only executable code in the repository
  schema/           seven JSON Schemas, selected by a document's location
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
