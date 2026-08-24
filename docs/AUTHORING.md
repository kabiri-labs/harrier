# Authoring

The rules, and what each one is protecting. Most are enforced by
`python -m harrier validate` rather than by review — see
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

---

## 1. A topic file

```yaml
id: HRR-INJ-01
title: SQL injection
domain: INJ
axis: technique              # the primary axis; units are named from its vocabulary
kind: test                   # test | recon | inquiry
surfaces:                    # attack-surface tags this topic attaches to
  any_of: [sql-backed-param]
dimensions:
  engine: [mysql, postgresql, mssql, oracle, sqlite]
order:                       # the sequence a tester works these units in
  - HRR-INJ-01-PROBE
  - HRR-INJ-01-FPRINT
  - HRR-INJ-01-UNION
boundaries:                  # canonical-home statements; see ARCHITECTURE.md §4
  - subject: "LDAP injection"
    home: HRR-INJ-04
    note: "A different interpreter: no SQL grammar, different metacharacters."
  - subject: "NoSQL operator injection"
    home: null
    note: "Not yet written. Recorded so the gap stays visible rather than reading as covered."
see_also: [HRR-API-02]
refs:
  wstg: [WSTG-INPV-05]
  cwe: [89]
```

`boundaries[].home: null` is legitimate and useful. A boundary against something
nobody has written yet is still worth recording — it is the difference between a
known gap and an invisible one.

## 2. A unit file

```yaml
id: HRR-INJ-01-UNION
topic: HRR-INJ-01
kind: test
status: outline              # outline | authored
title: UNION-based extraction
objective: >
  Determine whether a UNION arm can be appended to the query so that
  attacker-chosen, SQL-computed values appear in the response body.

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

payloads: payloads/sqli/union.yaml
tools: [burp-repeater, sqlmap]
card: cards/sqli/union-extraction.md
surfaces: { any_of: [sql-backed-param] }
dimensions: { engine: [mysql, postgresql, mssql, oracle, sqlite] }
refs: { wstg: [WSTG-INPV-05], cwe: [89] }
```

### `status: outline`

An outline unit carries its identifier, title, `objective`, `surfaces` and
`refs`, and nothing else. Everything below `oracle` is relaxed.

This is the mechanism that decouples coverage from depth. An outline unit already
appears in the published artefact, already answers "does this test exist and what
is it for", and already makes the gap countable. What it does not give is *how* —
the reader supplies that from their own knowledge, which for the intended reader
is usually enough.

`status` flips to `authored` when the depth fields are filled in. A unit still
marked `outline` while carrying everything an authored unit needs is rejected: a
stale status makes the coverage figures lie, and those figures are the number
this project asks to be judged on.

## 3. Content rules

These are not style preferences. `python -m harrier validate` fails on them, and
the suite asserts that it still does.

**`objective` is one falsifiable sentence.** It must be possible to be wrong
about it. "Investigate the parameter", "review the configuration" and "check
whether things are secure" are not objectives — nothing could contradict them.

**`oracle` and `done_when` are separate and never merged.** The oracle says what
makes the *target* vulnerable. `done_when` says what proves *you performed the
test*, including when you found nothing. A unit with only the first cannot answer
"did I finish", which is the question a tester asks at the end of a long day.

**`done_when` must be countable or enumerable.** "Tested thoroughly" is not a
criterion. "All eight encoding variants sent, status and length recorded for
each" is.

**A unit that cannot state an oracle is not a test.** It is `kind: recon` (it
establishes a fact) or `kind: inquiry` (it is target-specific by nature). Both
forbid `oracle` outright. Writing `"not applicable"` into an oracle field is
rejected. A rule with a socially acceptable escape hatch stops being a rule: the
first unit that cannot state an oracle writes `"not applicable"`, the second
copies it, and the field stops meaning anything.

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

`refs.cwe` is still checked only for plausibility: no CWE catalogue is pinned
yet, so keep to identifiers you can state with confidence.

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

## 5. Volatile content carries a date

Payload files, tool entries and engine- or browser-specific notes carry a
`reviewed:` date. Durable content — mechanism, oracle, ordering, false positives
— does not need one, because it does not rot on that timescale.

An undated volatile file is treated as unreviewed, not as current.

## 6. Licensing

Contributions are licensed under [Apache-2.0](../LICENSE).

**Do not copy or paraphrase WSTG or ASVS prose.** Both are share-alike licensed;
copying would force share-alike onto this repository. Reference identifiers and
official titles only. Everything under `knowledge/`, `cards/`, `payloads/` and
`mitigations/` is originally written.

Where published research informed a payload file, credit it in that file's
`credits` field.

## 7. Content safety

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
