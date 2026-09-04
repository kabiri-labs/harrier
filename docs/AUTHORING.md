# Authoring

The rules, and what each one is protecting. Most are enforced by
`python -m pentest_navgrid validate` rather than by review — see
[`VALIDATION.md`](VALIDATION.md) — because every one of them reads perfectly
well in a diff.

The governing rule, from which most of the others follow:

> **Breadth before depth.** A unit exists as soon as it has an identifier and a
> falsifiable objective. It does not wait for its card.

A taxonomy that requires each entry to be deeply written before it may exist
never reaches usable coverage: the entries that exist are excellent and the ones
that do not exist are invisible, which is the worse of the two failures. A unit
with nothing but a good objective is already useful — it tells a tester the test
exists, what it is for, and that they have not done it.

And a second one, which nothing below enforces because nothing could:

> **Check a claim against the mechanism behind it, not against today's data.**

A description is not a specification. Reading a capability's description and
finding it consistent with the edge you want to draw is not the check — the check
is whether the description is narrow enough to carry that edge.
`control.content.internal` says "host names, paths, identifiers **or**
credentials", and a unit consuming it to establish another user's session derived
account takeover from a disclosed file path. Every word of the description was
satisfied. The claim was still wrong.

The same failure has a second form, in prose rather than in YAML: a sentence in a
document, a pull request or a page that is wider than the code, the derivation or
the vocabulary underneath it. "Twelve walks, grouped, four shown" described an
ordering the code did not perform. "48 capabilities reach it" borrowed the one
word [`PIVOT.md`](PIVOT.md) forbids, in a product whose earlier version was
removed for speaking that way. Both sentences were true of the catalogue on the
day they were written, which is exactly why running anything caught neither.

So the question is not "is this consistent with what I see today". It is "what
would have to change for this to become false, and would anything notice". Where
the answer is nothing, the claim is narrowed, or it is bound to something that
fails when it goes stale — a figure read from the repository, a property asserted
rather than a number pinned, a validator pass — before it is written down.

---

## 1. A topic file

```yaml
id: PTN-INJ-01
title: SQL injection
domain: INJ
axis: technique              # the primary axis; units are named from its vocabulary
surfaces:                    # attack-surface tags this topic attaches to
  any_of: [sql-backed-param]
dimensions:
  engine: [mysql, postgresql, mssql, oracle, sqlite]
order:                       # the sequence a tester works these units in
  - PTN-INJ-01-PROBE
  - PTN-INJ-01-FPRINT
  - PTN-INJ-01-UNION
boundaries:                  # canonical-home statements; see ARCHITECTURE.md §4
  - subject: "LDAP injection"
    home: PTN-INJ-04
    note: "A different interpreter: no SQL grammar, different metacharacters."
  - subject: "NoSQL operator injection"
    home: null
    note: "Not yet written. Recorded so the gap stays visible rather than reading as covered."
see_also: [PTN-API-02]
refs:
  wstg: [WSTG-INPV-05]
  cwe: [89]
```

`boundaries[].home: null` is legitimate and useful. A boundary against something
nobody has written yet is still worth recording — it is the difference between a
known gap and an invisible one.

**`see_also` runs both ways; `boundaries` does not.** A cross-reference is a peer
relationship: if a topic is worth knowing about from here, this one is worth
knowing about from there, and a reader arriving from the other direction would
otherwise never learn it exists. The validator rejects a link that is not
returned. A boundary is directional by design — *the thing I am not covering
lives over there* obliges the other topic to say nothing — so if a relationship
genuinely runs one way, it is a boundary, not a `see_also`.

## 2. A unit file

```yaml
id: PTN-INJ-01-UNION
topic: PTN-INJ-01
kind: test                   # test | recon | inquiry
status: outline              # outline | sketched | authored -- see below
role: variant                # stage | variant -- required; see below
title: UNION-based extraction
objective: >
  Determine whether a UNION arm can be appended to the query so that
  attacker-chosen, SQL-computed values appear in the response body.

hypotheses:                  # optional at every tier -- why this may work
  - "Normalisation happens after the root and the parameter are joined."
  - "The link is hidden rather than the file protected."
triage:                      # optional at every tier -- where to start looking
  - "Parameters named file, path, page, tpl, view, download."
sink: >                      # forbidden on recon and inquiry
  The path the application hands to the platform's file resolver.

oracle:                      # required on kind: test; forbidden on recon and inquiry
  positive: "A value the database computed, not one the request contained, appears in the response."
  negative: "Every arity and every reflected position exhausted with no computed value returned."
  inconclusive: "Responses are non-deterministic, or rate limiting stopped the sweep."

done_when: >
  Column count resolved, the reflected column index identified, and at least one
  SQL-computed value extracted -- or the reason the column count could not be
  resolved is written down.

sequence:                    # three to six steps; see ARCHITECTURE.md §7
  - "Resolve column count with ORDER BY N until the error boundary."
  - "If ORDER BY is filtered, NULL-pad the UNION arm until the query succeeds."
  - "Identify which column index reaches the response."
  - "Extract one computed value to prove it is the database talking."

first_false_positive: >
  Template echo of the input rather than query output. Prove it with a computed
  value such as 1337*7, never a static marker.

requires:                    # what makes this possible; see CHAINING.md
  all_of: [surface.sql.injectable]
  any_of: [access.anon, access.user]
motivated_by: [recon.engine.identified]   # worth doing sooner, not a condition
yields: [primitive.db.read]  # what a positive result establishes
# closes:                    # what a negative one rules out; a subset of yields.
#   - surface.sql.injectable # Omitted here rather than left empty: the schema
#                            # rejects an empty list, so that absent and "rules
#                            # nothing out" are one state instead of two.

payloads: payloads/sqli/union.yaml
tools: [burp-repeater, sqlmap]
card: cards/sqli/union-extraction.md
surfaces: { any_of: [sql-backed-param] }
dimensions: { engine: [mysql, postgresql, mssql, oracle, sqlite] }
refs: { wstg: [WSTG-INPV-05], cwe: [89] }
```

### Depth: `outline`, `sketched`, `authored`

Three tiers, each a strict superset of the one before it. What each requires is
in `unit.schema.json` and checked on every run, so the status cannot claim more
than the file carries.

| | `outline` | `sketched` adds | `authored` adds |
|---|---|---|---|
| `kind: test` | id, title, `objective`, `role` | `oracle` (positive and negative), `sequence`, `first_false_positive`, `done_when` | `enter_when`, `preconditions`, `evidence`, `false_positives`, `safety` |
| `kind: recon` | the same | `sequence`, `first_false_positive`, `done_when` | `enter_when`, `preconditions`, `evidence` |
| `kind: inquiry` | the same | `questions`, `done_when` | `enter_when`, `preconditions`, `evidence`, `first_false_positive` |

A **sketch** is the twenty-minute tier: enough to perform the test and to
recognise an answer that is wrong. It is deliberately not the full page — what
to record, when the test is worth entering and how far to take it are what
`authored` adds, and those are the parts that take the other two hours.

Recon carries no `safety` or `false_positives` at any tier because an
enumeration that touches nothing has no limit to state, and a required field
with nothing to say gets filled with "not applicable".

An outline unit carries its identifier, title, `objective`, `surfaces` and
`refs`, and nothing else. Everything below `oracle` is relaxed.

`requires` and `yields` are the exception: they are structure, not depth, and an
outline unit should carry them. They are what places it in the chain, and a unit
nobody can reach is not usefully outlined.

This is the mechanism that decouples coverage from depth. An outline unit already
appears in the published artefact, already answers "does this test exist and what
is it for", and already makes the gap countable. What it does not give is *how* —
the reader supplies that from their own knowledge, which for the intended reader
is usually enough.

`status` moves up when the fields of the next tier are filled in. A unit still
marked at a tier below the one it has grown into is rejected: a stale status
makes the depth figures lie, and those figures are the number this project asks
to be judged on.

### Orientation: `triage`, `hypotheses`, `sink`

Three fields that describe the **target** rather than the test. Every other
field answers what the test is for, how to run it, or how to read the answer;
these answer *where to start* and *why this may work at all*.

- **`triage`** — what in the target makes this test worth reaching for sooner:
  parameter naming, endpoint shapes, a signal in a response. Write the literal
  token a tester will see and type — `tpl`, not "a template parameter". The
  artefact searches this field, and a name written out as prose is a name
  nobody can search for.
- **`hypotheses`** — the mechanisms that, if they hold, are why this succeeds.
  Two or more: one is the objective restated, and the value of the field is
  that a reader can rule them out one at a time.
- **`sink`** — where an input the tester controls comes to rest, and what
  interprets it there. Forbidden on `recon` and `inquiry`, which send nothing.
  Omit it on a `test` unit that reads rather than submits; six do.

All three are allowed at **every** tier, including `outline`. None depends on
procedural depth, and a `triage` line is the cheapest thing that turns an
outline from a title into a lead.

`triage` meets the same vague-language gate as `objective`, because it is an
instruction and "review the parameters" is the thing it exists to replace.
`hypotheses` does not: a hypothesis is a claim about the target, and "the
non-standard ports are the ones nobody reviews" is exactly what the field is
for.

## 3. Content rules

These are not style preferences. `python -m pentest_navgrid validate` fails on them, and
the suite asserts that it still does.

**`objective` is one falsifiable sentence.** It must be possible to be wrong
about it. "Investigate the parameter", "review the configuration" and "check
whether things are secure" are not objectives — nothing could contradict them.

**`oracle` and `done_when` are separate and never merged.** The oracle says what
makes the *target* vulnerable. `done_when` says what proves *you performed the
test*, including when you found nothing. A unit with only the first cannot answer
"did I finish", which is the question a tester asks at the end of a long day.

**A declared `axis` must do work.** It states which vocabulary this topic's
units may draw from *beyond* the universal ones, so declaring one no unit draws
from constrains nothing and misdescribes the decomposition. Omit it instead: a
small topic whose units are all phases and reaches genuinely has no primary axis,
and inventing a unit to justify a declaration is the worse of the two errors.

**An objective states one outcome, not a menu of them.** This is the boundary
rule applied to the sentence that carries it, and it is the mistake that recurs:

> ~~Determine which of local file read, internal network access and parser
> resource exhaustion the entity resolution permits.~~

Those are three tests. A deployment can return a file and cap expansion, so they
are separately recordable; reading a file does not attempt expansion, so they are
non-substitutable; and no single sentence states what proves all three. Bundled,
finishing the easy one marks the other two complete, which is the coverage lie
the whole instrument exists to prevent.

Enumerating several *manifestations of one observation* is fine — "an error, a
truncated response, or a terminated process" are three ways the same read past
the argument list shows itself. The test is whether a sibling could come out
clean while this one comes out vulnerable.

**`done_when` must be countable or enumerable.** "Tested thoroughly" is not a
criterion. "All eight encoding variants sent, status and length recorded for
each" is.

**A unit that cannot state an oracle is not a test.** It is `kind: recon` (it
establishes a fact) or `kind: inquiry` (it is target-specific by nature). Both
forbid `oracle` outright. Writing `"not applicable"` into an oracle field is
rejected. A rule with a socially acceptable escape hatch stops being a rule: the
first unit that cannot state an oracle writes `"not applicable"`, the second
copies it, and the field stops meaning anything.

**A yielded capability must be specific enough to justify what consumes it.**
`yields` is what the artefact draws the next arrow from, so a fact that is
vaguer than the thing it enables produces an edge nobody can act on.
`primitive.db.read` earns the extraction units; a hypothetical
`surface.something.interesting` earns nothing and connects everything. If two
units yield the same fact and mean materially different capabilities, the fact
is too coarse and belongs split.

**A prerequisite states possibility, never likelihood.** `requires` is what makes
the test performable at all. Anything that merely makes it more promising is
`motivated_by`, and the two must not be traded: over-declaring `requires` hides
the unit from a reader who has not yet met the condition, which is worse than
offering a test slightly early. One is invisible; the other is merely premature.

**`motivated_by` must never become a hard gate.** It is drawn differently and
read differently — *worth reaching for sooner*, not *now possible*. If a unit
genuinely cannot be performed without the fact, it is a `requires`, and saying so
is not a downgrade.

**A downstream path must not overstate what success proves.** The artefact
renders every continuation with the conditions this unit's `yields` do not
supply, so an over-broad `yields` turns into an edge that claims more than the
test showed. The same applies in reverse to `closes`: it is a subset of `yields`,
it may name only a fact this unit is the sole producer of, and a negative result
on one route says nothing about the others.

**A terminal impact is never a prerequisite.** `impact.*` is where a chain ends;
the validator rejects anything requiring one. A unit that seems to need an impact
needs the primitive behind it instead.

**The recall block must fit one screen.** If it does not, the unit is too large
and the boundary rule was applied too loosely. Prose beyond that belongs in the
card's depth block.

**Never write a standard's identifier from memory.** The authorization prefix in
WSTG is `ATHZ`, not `AUTHZ`. Every `refs.wstg` and `refs.asvs` value is resolved
against the pinned files under `standards/`. If the source cannot be reached,
mark the entry unverified and say so, rather than guessing.

Numbering is renumbered between major releases of a standard, so an identifier
remembered from an earlier one resolves to nothing or, worse, to something else.
`V5.3.4` was a real ASVS 4.x requirement and does not exist in 5.0 — an
identifier like that reads as evidence while being none, which is why the check
is mechanical.

`refs.cwe` resolves the same way, and must name a **weakness**. Citing `CWE-699`
or `CWE-1000` is rejected by name: those are a category and a view, which group
weaknesses rather than being one. A deprecated weakness is rejected in favour of
its replacement.

## 4. Where things go

| You are adding | It goes in |
|---|---|
| A payload | `payloads/` — never inline in a unit |
| A tool invocation, and why each flag is there | `toolbox/registry.yaml` — written once |
| Long-form explanation | `cards/`, organised **by technique**, not by identifier |
| Remediation text | `mitigations/`, keyed by weakness class |
| A new surface tag, dimension value or axis slug | `vocab/` |

**If a payload would appear in two units, it belongs in one file referenced
twice. No exceptions.** Cards are organised by technique for the same reason: two
units that share a technique share one card rather than each carrying a copy that
will drift.

**Mitigation attaches to the weakness, not to the test.** Six XSS units and four
DOM XSS units share one remediation text about contextual output encoding. Copied
per unit, it would be ten copies diverging from the moment the second was
written.

## 5. A new surface tag

Every tag declares a `dimension`, and the seven are not interchangeable:

| Dimension | What it names | Example |
|---|---|---|
| `channel` | The interface the interaction happens over | `rest-api` |
| `entry_point` | Where a controlled value enters or selects something | `object-id-param` |
| `business_function` | What the operation is for | `payment` |
| `security_context` | The identity, privilege, tenancy or browsing context it runs in | `multi-tenant` |
| `environment` | A deployment or platform property | `cache-fronted` |
| `processor` | The component that interprets a controlled value — a hypothesis until observed | `sql-backed-param` |
| `observed_behavior` | Something the tester has actually seen | `stored-then-rendered` |

Choose it from what the tag's **description** says, not from what its name
suggests. `rest-api` is labelled "Structured machine-facing API" and its
description is about programmatic interfaces rather than about REST, which is
why GraphQL is one of them and why the tag is a `channel` rather than a
protocol. A tag whose description spans two dimensions is two tags.

### Which relation a new edge is

Two relations exist and they claim different things. Getting this wrong is not a
style question: the page prints one of them as fact.

> **`parents` must be true of every surface carrying the tag, and stay inside
> one dimension. Everything else is `often`.**

A parent is a coarser way of saying the same kind of thing. Every GraphQL
endpoint is a machine-facing API — not usually, always — so a topic filed under
the parent is an answer for the child and the page says so plainly. The relation
is closed transitively, so it must also be true through every step.

`often` records what such a surface commonly carries as well. It may cross
dimensions, which is most of what it is for, and it is reported as association
wherever it appears. A search box often reaches a relational store; `/search`
may query no database at all.

The test is not "is this usually true". It is **what would have to be the case
for this to be false, and does that thing exist**. If you can name one — a
write-only upload with no download, a login form that returns a bearer token and
sets no cookie, a SOAP endpoint that parses XML and accepts no file — it is
`often`. Every one of those was once written as an implication here, and the
selection page printed each as something true of every surface carrying the
first.

Two relations that both cross a boundary are rejected rather than reconciled: a
deployment property does not imply an input location, and an edge that wants to
say so is describing two different observations that belong on the surface
separately. Apply both tags when both were seen.

## 6. Volatile content carries a date

Payload files, tool entries and engine- or browser-specific notes carry a
`reviewed:` date. Durable content — mechanism, oracle, ordering, false positives
— does not need one, because it does not rot on that timescale.

An undated volatile file is treated as unreviewed, not as current.

## 7. Licensing

Contributions are licensed under [Apache-2.0](../LICENSE).

**Do not copy or paraphrase WSTG or ASVS prose.** Both are share-alike licensed;
copying would force share-alike onto this repository. Reference identifiers and
official titles only. Everything under `knowledge/`, `cards/`, `payloads/` and
`mitigations/` is originally written.

Where published research informed a payload file, credit it in that file's
`credits` field.

## 8. Content safety

This is material for authorised testing, and the repository's own correctness is
part of its threat model.

- Payloads stay at proof-of-concept level: markers, benign metadata reads,
  non-destructive probes.
- No destructive operations — no `DROP`/`DELETE` payloads, no mass-exploitation
  drivers, no ready-made webshells.
- Where a technique is inherently dangerous, record that in the unit's or payload
  file's `safety` field rather than shipping the weaponised form. Time-based
  inference holds a backend connection open per request, which is a
  denial-of-service primitive on a pooled backend at low request rates;
  out-of-band extraction sends target-derived data past every resolver on the
  path. Both are said out loud rather than left for the reader to notice.
- **Never commit anything from a real target** — no hostnames, tokens,
  credentials, or captured traffic. Examples are invented.
