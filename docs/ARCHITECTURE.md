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

## 8. Navigation — the run, not the catalogue

A tester does not arrive wanting to browse. They arrive with something in front
of them and a decision to make: what to test first, and what comes after it.
Everything here follows from treating that as the product's job rather than the
reader's.

### The run

The one piece of state that is about a target rather than about the catalogue:
what is being tested, what is in front of the tester, what they hold, and what
they have settled. It lives in the browser and in a file the tester exports on
purpose. It is never embedded in the artefact — a run carries a client's target
name and what was found on it, and the artefact is published.

### Two filters, applied together

**The anchor** is what is in front of the tester, and it moves with the
granularity of the question. A whole application at the start of an engagement,
one section of it, or one technical thing — a cookie, a redirect parameter, a
web form. Surface tags are how it is expressed, which is why they are a
first-class controlled vocabulary. A tag closes over what it `emits`, so naming
a login form also names the session cookie, and naming a search box also names
the database-backed parameter behind it.

**Reachability** is what the held facts allow, derived from the facts units
declare rather than from any stored ordering. See [`CHAINING.md`](CHAINING.md).

Neither is useful alone. The anchor without the chain is a flat list of
everything that could ever apply; the chain without the anchor answers for the
whole target when the tester asked about one form.

### When nothing is ready

Naming a surface is not the same as holding what testing it needs, so a board
can open with nothing in reach. It does not answer "nothing", and it does not
ask the tester to assert the missing fact either: `recon.entrypoints.mapped` is
not an observation, it is what a unit establishes, and handing it over because
somebody named a surface would record reconnaissance nobody performed. The
vocabulary is explicit that everything outside `given` and `granted` has to be
earned.

So the answer is the unit that earns it, offered with its result controls in
place. That unit is usually outside the surface being looked at — which is
exactly why the tester could not find it. Where the unit is itself blocked, what
it is waiting on is named, and the chain resolves to something that can be done
now. A fact no unit yields is one the engagement supplies, and there the only
honest control is the tester saying so.

### Order

Within what is both in scope and reachable, three things decide what comes
first: whether something held makes a unit more likely to pay (`motivated_by`),
whether the unit is written in full or is still an outline, and the performance
order its topic declares. The first is decided in the page because only the page
knows what is held; the other two are decided at build time and travel as an
integer, so the opinion is one a test can pin down.

### Naming what is shown

Titles lead and identifiers follow. An identifier is how two people refer to the
same test and how a finding is written down — it is not what a tester reads. The
same holds for facts: a unit needs *"the session identifier is known"*, not
`recon.session.identified`.

### Results

Four states, because three of them are results and the fourth is "not yet".
Without the clean state there is no difference between a test nobody ran and a
test that came back empty, and that difference is the only thing that makes
coverage a claim rather than a hope.

What a result does to the graph is asymmetric, and the asymmetry is the point.
A positive result **establishes** what the unit yields, and those facts open
what needs them. A clean result **rules out** what the unit closes, into a set
of its own — never into the held facts. `closes` is a subset of `yields`, so
merging the two would record a finding as its own opposite: a probe that found
no injection would establish that the parameter is injectable and offer the
extraction that needs it.

A ruled-out fact prunes rather than opens. Units that need it are not pending —
they were answered — and they are shown that way, with the fact that answered
them.

Undo withdraws a ruling-out but not an establishing, because a unit may only
close a fact it is the sole producer of, while a yielded fact may have been
established by another route the tester still holds.

### The other views

**Surfaces** is a reference listing of every surface the catalogue knows, and a
way into the board from one. **Search** is three characters to a payload.
**Coverage** is WSTG, CWE and ASVS — real, but its audience is report-writing
and scoping, not testing.

The published artefact is a **single self-contained HTML file**: no external
stylesheet, script or font. It is opened from a laptop on an engagement network
and must not emit a request a monitored target could observe. Storing a run must
not become a way to send one.

## 9. Repository layout

```
docs/
  ARCHITECTURE.md   this document: the model and why it is shaped this way
  TAXONOMY.md       identifiers, domains, axis vocabularies
  AUTHORING.md      the rules for writing a unit or a card
  CHAINING.md       how one test leads to the next, and why no unit names another
  VALIDATION.md     what the validator checks, and why each rule is mechanical
  ROADMAP.md        build state; updated in the same change as the work

harrier/            the validator and the builder -- the only executable code
  chain.py          the derived attack graph; nothing about it is stored
  build.py          the published artefact: one self-contained HTML file
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
