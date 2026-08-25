# Chaining

How one test leads to the next, and why the links are not written down.

A tester works three questions in a loop: *what do I know*, *what can I do with
it*, *what does the result make possible*. A catalogue that answers only the
middle one is a checklist. This is the layer that answers the other two.

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

**Why not name the next test directly.** With 365 units and an average of three
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

Credentials are **not** among them. An engagement that hands over no account
leaves one to be earned by registering, and a root that assumed otherwise would
open the catalogue with tests the tester cannot run. What is actually in hand is
stated at read time instead:

```
harrier chain --held access.user,access.peer
```

## 5. What the validator enforces

- Every fact named by a unit exists in the vocabulary.
- No unit both requires and yields the same fact.
- Nothing requires an `impact.*` fact: an impact is where a chain ends.
- `closes` never names a fact `yields` does not.
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
harrier chain                          summary
harrier chain HRR-INJ-01-UNION         one unit: what it needs, gives, and opens
harrier chain --fact primitive.db.read one fact: who establishes it, who needs it
```

`unlocks` and `motivates` are reported separately, because they mean different
things to somebody deciding what to do next: one was impossible before and is
possible now; the other was always possible and has just become worth doing.
