# Chaining

How one test may lead to the next, and why the links are not written down.

A catalogue that says only *what to perform* is a checklist. This is the layer
that says what a test needs in order to be possible at all, and what a success
makes relevant afterwards.

**The graph is generic.** It is a statement about the relationships between
tests, not about anybody's application. Harrier is context-free: it has never
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

**Why not name the next test directly.** With 366 units and an average of three
onward routes each, an explicit edge list is over a thousand hand-maintained
links. Every new unit has to be inserted into the `next` list of every unit that
could precede it — which means the cost of adding a unit grows with the size of
the catalogue, and the edges that were never updated look exactly like edges that
were checked and found not to exist. Facts are the join key instead: a unit
declares what it needs and what it gives, and the graph reconnects itself.

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
database — so `HRR-INJ-01-UNION` closes nothing, and says so by leaving the
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

## 5. What the validator enforces

- Every fact named by a unit exists in the vocabulary.
- No unit both requires and yields the same fact.
- Nothing requires an `impact.*` fact: an impact is where a chain ends.
- `closes` never names a fact `yields` does not.
- `closes` names only facts this unit is the sole producer of.
- An authored `test` or `recon` unit yields something. A unit that establishes
  nothing cannot be reached from anywhere and leads nowhere.
- Every declared fact is referenced by at least one unit. Vocabulary must not
  outrun use.
- No fact id is declared twice.

One rule is deliberately **not** enforced yet: that every non-`given` fact has at
least one unit producing it. While the catalogue is partly charted, that rule
would reject a fact whose producer is simply a unit that has not been charted
yet. It becomes a gate when the chain pass finishes — recorded in `ROADMAP.md`
rather than left to be remembered.

## 6. Reading the graph

```
harrier chain                          summary, and how far the chart reaches
harrier chain HRR-INJ-01-UNION         one test: what it needs, establishes, and may lead to
harrier chain --fact primitive.db.read one capability: who establishes it, who declares a use
```

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

**A capability nothing consumes is an outcome, not a gap.** An `impact.*` fact
is terminal by construction — the validator rejects anything requiring one — and
is shown as where a chain ends. A non-impact capability with no consumer is a
reportable result and is described as one rather than as an empty graph.

**A negative result excludes less than it appears to.** `closes` is a subset of
`yields` and may name only a fact this unit is the *sole* producer of, so
anything yielded and not closed has another route to it. Those routes are named:
a clean UNION result does not mean there is no SQL injection while boolean,
timing, error and out-of-band routes are untried. Nothing is recorded — this is
how to read a result, not a place to store one.
