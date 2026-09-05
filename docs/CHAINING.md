# Chaining

How one test may lead to the next, and why the links are not written down.

A catalogue that says only *what to perform* is a checklist. This is the layer
that says what a test needs in order to be possible at all, and what a success
makes relevant afterwards.

**The graph is generic.** It is a statement about the relationships between
tests, not about anybody's application. Pentest NavGrid is context-free: it has never
seen your target, holds nothing about it, and cannot know which of these
relationships is live today. So the chain says *requires*, *establishes*,
*may become relevant* — and never *you hold*, *unlocked*, or *available now*.
That distinction is load bearing rather than cosmetic; [`PIVOT.md`](PIVOT.md)
records what happened when the product blurred it.

---

## 1. Facts are the nodes, not tests

Each unit declares what must already be true for it to be possible, and what
becomes true when its result is positive:

```yaml
requires:
  all_of: [surface.sql.injectable]
  any_of: [access.anon, access.user]
motivated_by: [recon.engine.identified]
yields:  [primitive.db.read]
closes:  []
```

An edge from unit A to unit B exists exactly when A yields a fact B requires.
Nothing else defines the graph, and no unit names another unit anywhere.

The edge means: *if A succeeds, B may become relevant.* It does not mean B is
now possible. B may need three other things as well, and one of them may be
something no test can supply.

**Why not name the next test directly.** The derivation currently yields 776
unit-to-unit edges across 393 units, and that is with the far half of the chain
barely charted. Written down they would be 776 hand-maintained links, each
needing to be inserted into the `next` list of every unit that could precede it
— so the cost of adding a unit grows with the size of the catalogue, and the
edges nobody updated look exactly like edges that were checked and found not to
exist. Facts are the join key instead: a unit declares what it needs and what it
gives, and the graph reconnects itself.

The graph is derived at read time and never stored. There is no file to fall out
of date.

## 2. The four fields

| Field | Means | Failure it prevents |
|---|---|---|
| `requires` | What makes this test **possible** | — |
| `motivated_by` | What makes it **worth doing sooner** | A hint silently becoming a gate |
| `yields` | What a positive result establishes | — |
| `closes` | What a negative result rules out | A clean result claiming more than it showed |

`requires` takes `all_of`, `any_of`, or both. `all_of` is conjunction, `any_of`
is disjunction, and a unit that declares neither needs nothing — which is the
correct reading, not an omission.

**`closes` is a subset of `yields`,** enforced. A unit can only rule out a claim
it was capable of establishing. A negative UNION result does not close
`primitive.db.read`, because a boolean or timing route could still read the same
database — so `PTN-INJ-01-UNION` closes nothing, and says so by leaving the
field out.

**`requires` is about possibility, never likelihood.** A WAF being absent makes
extraction easier; it is not a condition of trying. Anything of that kind goes in
`motivated_by`. Over-declaring `requires` hides units from the reader who has not
yet earned the fact, which is a worse failure than offering a test slightly early:
one is invisible, the other is merely premature.

## 3. Chain data is structure, not depth

`requires` and `yields` are not depth fields. An `outline` unit may carry them,
and should: they are what places it in the graph, and a unit nobody can reach is
not usefully outlined. This is why the roadmap charts the chain across the whole
catalogue before authoring more than a handful of units.

## 4. The fact vocabulary

Facts live in `vocab/facts.yaml` and nowhere else. A fact outside it is rejected,
for the reason a slug outside `axes.yaml` is: two units inventing two names for
one condition split the graph into halves that each look complete.

Seven families, and the family is part of the identifier:

| Family | Holds |
|---|---|
| `recon.*` | Something is now known about the target |
| `surface.*` | An interactable thing has been shown to exist |
| `access.*` | A principal or session is held |
| `artifact.*` | A value is in hand |
| `primitive.*` | A capability is controlled — what an exploit is built from |
| `control.*` | The state of a defence |
| `impact.*` | A business outcome; terminal |

The families are fixed in the schema rather than declared in the file. A family
is a decision about what kind of thing a fact is, and a file that could add one
could quietly file an impact as a primitive.

`given: true` marks a fact the engagement supplies unconditionally — the target
being reachable, requests being possible without a session. Those are the roots.

`granted: true` marks one an engagement *may* supply and often does not: access
to the host itself is the first of them. Both are exempt from the producer gate,
because neither is earned by a test. Only `given` facts are treated as holding at
the start: a `granted` capability stays visible as an unmet condition, so a
continuation that needs one names it rather than assuming an engagement supplied
it.

Credentials are **not** among them. An engagement that hands over no account
leaves one to be earned by registering, and a root that assumed otherwise would
present tests whose condition nothing has established. `access.user` has a
producer like anything else, and a test that needs it says so.

### Tiers

Every fact also declares a `tier`, and it decides what an edge *through* that
fact is called:

| Tier | The edge is |
|---|---|
| `engagement` | A general precondition rather than a step. Holding a session, having enumerated the entrypoints. |
| `topic` | A join inside one topic: another technique for the same test, not a step past it. |
| `chain` | Currency — a capability, an artifact, a defeated control, an outcome, a finding that picks the next technique. The escalation a tester means by "attack chain". |

The derivation cannot tell these apart from the join alone: "A yields what B
requires" is the same sentence for all three. Without the tier they printed under
one heading, and the arithmetic of that is unforgiving — `PTN-IDN-01-POLICY`
yields `access.user`, which 90 tests require, and the two genuine escalations
leaving that unit sorted somewhere among the ninety.

An edge travelling through several facts takes the **most specific** tier any of
them carries: a step needing both a held session and a captured token is reached
by capturing the token. The other precedence would file it under the session and
bury it again.

A tier says what kind of thing a fact is, not how many topics consume it today.
That distinction is deliberate: a label that shifted as the catalogue grew would
be worse than none, because a reader would have learnt a heading that later means
something else.

`tier` is required. A fact that declared none would have to be defaulted into one
of the three, and any default silently refills the heading the field exists to
empty.

## 5. What the validator enforces

- Every fact named by a unit exists in the vocabulary.
- No unit both requires and yields the same fact.
- Nothing requires an `impact.*` fact: an impact is where a chain ends.
- `closes` never names a fact `yields` does not.
- `closes` names only facts this unit is the sole producer of.
- An authored `test` or `recon` unit yields something. A unit that establishes
  nothing cannot be reached from anywhere and leads nowhere.
- **The reference gate.** Every declared fact is named by at least one unit, or
  is registered under `uncovered` in `vocab/facts.yaml` with the cause it
  belongs to. It used to be a flat refusal — vocabulary must not outrun use —
  and that refused two different things with one sentence: a fact nobody
  noticed, and the only honest way to write down where the catalogue is going.
  A registered fact says on its own page that no test in this catalogue
  establishes it, and is counted apart from the ones tests do reach.
- A fact in the `uncovered` register that a unit has since started naming is
  rejected, the same ratchet the `unconsumed` register carries: it can shrink
  by a test arriving, never by the entry being forgotten.
- No fact id is declared twice.
- Every fact declares a `tier`, and it is one of the three.
- **The producer gate.** Every fact something requires has at least one unit
  establishing it, unless it is `given` or `granted` — neither is earned by a
  test. It became a gate when the chain pass finished, as phase 5 said it would.
- **The consumer gate.** Every chain-tier fact something establishes has a
  derived edge travelling through it, or is registered under `unconsumed` in
  `vocab/facts.yaml` with the cause it belongs to. Impacts are excluded: one is
  terminal by construction.
- The gate counts edges, not mentions. A unit naming a capability it establishes
  itself adds no route -- the derivation drops that edge as self-referential --
  so a sole producer motivated by its own result does not clear the gate. A
  sibling naming another unit's result does: several units testing one property
  across several surfaces, each motivated by whichever found it first, are
  joined to each other even though every one of them also establishes it.
- A registered fact that a unit has since started declaring a use for is
  rejected. The register names the gaps that are open, and an entry outliving
  its gap turns it into a list of suppressions.

The three gates are deliberately not symmetrical in what they permit. A fact with
no producer is a hole and is refused outright, because from the outside it reads
exactly like a route nobody has taken yet. A fact with no consumer is where the
chart honestly stops, and a fact nothing mentions at all is where the catalogue
has not arrived yet; both are recorded rather than refused — what is refused is
recording nothing. The asymmetry is the point: a broken chain and an unwritten
one look identical from outside and mean opposite things, so only one of them
may be written down.

## 6. Reading the graph

```
pentest-navgrid chain                          summary, and how far the chart reaches
pentest-navgrid chain PTN-INJ-01-UNION         one test: what it needs, establishes, and may lead to
pentest-navgrid chain --fact primitive.db.read one capability: who establishes it, who declares a use
pentest-navgrid checklist                      one line per test case of the standard
pentest-navgrid checklist WSTG-INPV-05         one test case, and the units that cover it
pentest-navgrid checklist --uncovered          the test cases no topic claims
pentest-navgrid index                          regenerate standards/wstg-index.yaml
```

`pentest-navgrid chain <unit>` names the test cases that lead to the unit, because the
identifier on a tester's scope sheet is the standard's and not Pentest NavGrid's. That
relation lives on the topic rather than the unit, so a reader of this output
previously had no route back to the line item that sent them there.

The command line reads **the same derivation the artefact does** — one
implementation in `chain.py`, two consumers — so the two cannot drift into
describing different models. It prints the same things and says them the same
way: prerequisites, what success establishes, potential continuations with the
capability each travels through, and what each continuation still declares that
succeeding here does not supply.

There is no way to tell it what you hold, and it computes nothing about a
target. `--held`, `available` and `unlocks` were removed in 0.4.0: a tool that
answers *what is possible now* is making a claim about somebody's application,
and it made that claim one command away from a page that says it cannot.

## 7. Reading a continuation honestly

This is what the artefact renders around every unit, and the rules it follows.

**A prerequisite describes possibility, never likelihood.** It is a condition of
the test being performable at all. Anything that merely makes it more promising
is `motivated_by`.

**Continuations are grouped by tier, not listed flat.** The escalations come
first under their own heading, then the alternative techniques for the same test,
then the general prerequisites — the last with a count and without the per-edge
detail, because ninety rows each saying "this test also needs a session" is what
made the two rows above them impossible to find. Nothing is hidden: every
continuation is still listed under one of the three headings.

**Success here is rarely sufficient for what follows.** A continuation reached
through one capability may declare several others. Those are shown as *still
required*, and they are exactly the declared conditions that this unit's
`yields` and the `given` roots do not cover:

```
Potential continuation: UNION-based extraction

Established here:
  - A parameter reaches a SQL statement

Still required:
  - An ordinary account, or an unauthenticated caller
```

`granted` facts are deliberately **not** treated as supplied. An engagement may
give host access and usually does not, so a unit needing it is still waiting on
something the reader has to recognise as theirs to have or not.

**Continuations are not ranked by how little they still need.** That ordering
looks helpful and is not: it sorts every conditional continuation below the
first few a reader sees, which hides precisely the part that keeps the view
honest.

**A capability nothing consumes is an outcome, not a gap** — and the two kinds
of outcome are counted apart. An `impact.*` fact is terminal by construction, the
validator rejects anything requiring one, and it is shown as where a chain is
*meant* to end. A non-impact capability with no consumer is a **dead end**: a
reportable result where the chart simply does not go on. Folding impacts into
that count would inflate it and would describe arriving as failing to arrive.

It is no longer the common case. 20 of 188
capabilities are established by a test and used by none, including 1 of 33
`primitive.*` and 11 of 59 `control.*`. The chain-tier ones among them are
registered under `unconsumed` with the cause they belong to, so the count moves
only when a gap is worked on. A third state is counted apart from both: 1 of 188
is named by no test at all, registered under `uncovered`, and is where the
catalogue has not arrived rather than where the chart stops. Of 393 tests, 314 have a potential
continuation, 14 establish an impact, 26 stop short, and 39 declare no
capability at all — a partition, and the four sum to the catalogue. Phase 5
charted reconnaissance through to primitives and stopped there; primitive to
impact is largely unwritten. `pentest-navgrid chain` reports the split and the artefact
reports it on the catalogue status and model page -- with the register entry
that says why each one is open -- because a reader meeting a dozen dead ends
should be told it is the chart's reach rather than inferring the catalogue is
broken.

**A negative result excludes less than it appears to.** `closes` is a subset of
`yields` and may name only a fact this unit is the *sole* producer of, so
anything yielded and not closed has another route to it. Those routes are named:
a clean UNION result does not mean there is no SQL injection while boolean,
timing, error and out-of-band routes are untried. Nothing is recorded — this is
how to read a result, not a place to store one.
