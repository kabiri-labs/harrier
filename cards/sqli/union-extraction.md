# UNION-based extraction

Shared by `PTN-INJ-01-UNION` and `PTN-INJ-01-ERROR`: the arity and reflection
reasoning is identical, so it is written once here rather than copied into both.

## Recall

**Oracle** — a value the *database* computed, not one the request contained,
appears in the response. Prove it with `1337*7`, never a static marker.

**Sequence**

1. `ORDER BY N`, incrementing, until the error boundary gives the column count.
2. If `ORDER BY` is filtered, NULL-pad a `UNION SELECT` until the query succeeds.
3. Find which column index actually reaches the response.
4. Extract one computed metadata value. Stop there.

**Payloads** — [`payloads/sqli/union.yaml`](../../payloads/sqli/union.yaml)

**First false positive** — the template echoing your input rather than the query
returning it. A static marker cannot tell those apart; a computed value can.

**Done when** — column count resolved, reflected index identified, one computed
value extracted — or the reason the arity could not be resolved is written down.

---

## Depth

### What the technique actually requires

A UNION arm succeeds only when four conditions hold at once. Most failed
attempts are one of these four being false, not the absence of an injection:

1. The injection sits in a `SELECT` whose result set reaches the response. An
   injectable `INSERT` value list or an `UPDATE` predicate is still injectable —
   it just cannot take a `UNION` arm, which is why the check's `prune_when`
   names the statement type explicitly.
2. The arity of the injected arm matches the original query's column count
   exactly. Engines reject a mismatch outright.
3. On strictly-typed engines the column types must be compatible position by
   position. PostgreSQL and Oracle enforce this; MySQL and SQLite coerce freely.
4. At least one column position is rendered somewhere in the response. A query
   can be perfectly injectable and still show you nothing.

Resolve them in that order. Testing reflection before resolving arity produces
a stream of identical error responses that tell you nothing about either.

### Resolving arity

Two routes, and the second is not merely a fallback.

`ORDER BY N`, incremented until the response changes, is cheapest: one request
per candidate, and the boundary is unambiguous. It fails when `ORDER BY` is
filtered, or when the endpoint sorts its own results and swallows the error.

`UNION SELECT NULL, NULL, ...` — adding one `NULL` per attempt — costs the same
number of requests but tolerates a filtered `ORDER BY`. `NULL` is the right
padding value precisely because it is type-agnostic: it satisfies condition 3
above on every engine, which no literal does.

Both routes are read as a *discontinuity*, not as a specific response. Sort the
result table by response length and look for where it jumps. Reading each
response individually is slower and less reliable.

Two engine notes that cost real time when forgotten:

- **Oracle** requires a `FROM` clause on every `SELECT`. `UNION SELECT NULL`
  never works; `UNION SELECT NULL FROM dual` does. An arity search that omits
  this returns a uniform error at every arity and reads exactly like "not
  injectable".
- **MySQL** requires a trailing space after a `--` comment. The space is
  invisible in a diff, survives poorly through copy-paste, and its absence
  produces a syntax error that looks like a rejected payload.

### Finding the reflected position

Once the arity is known, move a marker across the positions, padding the rest
with `NULL`. The order matters: pad first, then move the marker — changing both
at once means a failure has two possible causes.

**Use a computed marker, not a literal one.** `1337*7` returning `9359` is the
whole argument: a template echoing your input can reproduce a literal string but
cannot perform arithmetic. This single substitution eliminates the most common
false positive in the entire family, which is why the check's
`false_positives` names it and the pack lists the computed form ahead of the
literal one.

More than one position may render. Prefer the one that appears in a stable part
of the page — a table cell rather than a page title that gets truncated, or a
field that HTML-escapes its content and mangles what you extract.

### When it does not work

| Symptom | Likely cause | Next move |
|---|---|---|
| Uniform error at every arity | Oracle without `FROM dual`, or a filtered keyword | Re-run with `FROM dual`; then go to `PTN-INJ-01-EVADE` |
| Correct arity, no marker anywhere | Result set not rendered, or rendered from a second query | Fall through to `PTN-INJ-01-BOOL` |
| Marker appears, computed value does not | Template reflection, not injection | Not a finding. Record it and re-probe |
| Themed 200 page instead of an error | WAF interception | Compare content length and body markers; go to `PTN-INJ-01-EVADE` |
| Works at one arity, fails at another | Type mismatch on a strict engine | Replace `NULL` with type-appropriate placeholders |

The middle row is worth dwelling on. A marker that reflects while `1337*7` does
not is the application echoing your input, and reporting it as SQL injection is
the single most common false positive in this family.

### Where extraction stops

The check is satisfied by one SQL-computed metadata value — a version string or
the current database name. That is deliberate.

Proving the vulnerability and enumerating the data behind it are different
activities with different authorisation requirements. A version string proves
arbitrary read access to whoever reads the report; a dump of a customer table
proves the same thing while creating a copy of client data on the tester's
machine. Extract the metadata value, capture the request/response pair, and stop
there unless the engagement explicitly says otherwise.

## Related units

- `PTN-INJ-01-PROBE` — establishes that a signal exists at all, and which kind.
- `PTN-INJ-01-FPRINT` — supplies the `engine` dimension value this technique needs.
- `PTN-INJ-01-ERROR` — the alternative in-band channel when nothing renders but
  errors do; it shares this card because the arity and reflection reasoning is
  the same.
- `PTN-INJ-01-EVADE` — run this before concluding that a uniform negative means
  the parameter is safe.
