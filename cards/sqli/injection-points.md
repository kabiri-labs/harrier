# Injection points and what they are made of

Shared by `HRR-INJ-01-PROBE`, `HRR-INJ-01-FPRINT`, `HRR-INJ-01-STACK`,
`HRR-INJ-01-SECOND` and `HRR-INJ-01-EVADE`: all five reason about *where the
value lands in the statement* rather than about what to do once it is there, so
that reasoning is written once here.

## Recall

**The three contexts** — string (quoted), numeric (unquoted), identifier (a
column, a table, a sort direction). A quote-based probe answers the first and
says nothing about the other two.

**The pair, not the payload** — a lone quote proves the application dislikes
quotes. A quote that errors *alongside* a balanced form that returns the
baseline proves concatenation into a statement.

**Numeric context needs arithmetic** — `1` and `2-1` are the same record only if
the value is used as a number. A literal marker cannot make that distinction.

**Stacking is the driver's decision, not the engine's** — the same PostgreSQL
server stacks over one client library and refuses over another, so the answer is
a property of the deployment.

**Second order is silent at the store** — the write succeeds, and the statement
that breaks is somewhere else entirely: an export, an admin listing, a nightly
job.

**Four refusal shapes** — engine error, application error page, filter block,
silent normalisation. Each says something different about where the refusal sat.

---

## Depth

### The three contexts

Almost every discussion of SQL injection begins with a quote, which is why the
identifier position is the one most often missed.

**String context.** The value is inside quotes in the statement text:
`WHERE name = '<value>'`. A lone quote ends the literal early and the remainder
no longer parses. This is the context the standard probe was written for.

**Numeric context.** The value is unquoted: `WHERE id = <value>`. No quote is
involved, so sending one produces either a type error or nothing interesting,
and both look like "not injectable". What proves this context is arithmetic: if
the record for `id=1` is also returned for `id=2-1`, the engine evaluated the
expression, which it can only do if the expression reached the statement.

**Identifier context.** The value names a thing rather than being one:
`ORDER BY <column>`, `ORDER BY name <direction>`, occasionally a table name.
This position cannot be parameterised — placeholders bind values, not
identifiers — so it is the position most likely to be concatenated in code that
is otherwise entirely bound. A quote-based probe returns clean from a perfectly
injectable sort column, and that clean result is why the position survives
audits.

Look for it wherever a listing lets the caller choose its order: `sort`, `order`,
`orderby`, `dir`, `direction`, `column`, `by`. The signal is not an error; it is
the *ordering changing* for a value that names no column, or the listing
collapsing for one that does.

### Why the doubled quote goes with the single one

Send `'` and `''` in the same breath, and read them as a pair.

The single quote alone has two explanations that a single response cannot tell
apart: the statement broke, or something upstream refused a request containing a
quote. Both produce "the response changed".

The doubled quote separates them, because the two mechanisms treat it
oppositely. A parser sees an escaped quote inside a string and the statement
parses. A signature filter sees a quote and refuses, twice as much as before.
So: error on the first and a clean parse on the second means the statement
broke; identical refusal for both means the refusal never reached a statement,
and `HRR-INJ-01-EVADE` is the next unit rather than any extraction technique.

Sent afterwards instead of alongside, the same information arrives after the
tester has already decided what they are looking at.

The balanced form that returns the *baseline record* — rather than merely
parsing — is `' AND '1'='1`, which reconstructs the original comparison and adds
a tautology. Adjacent string literals (`' 'a' = 'a`) look like they should do the
same job and do not: only MySQL concatenates literals by juxtaposition, so on
PostgreSQL and SQLite that form is a syntax error indistinguishable from the
lone quote, and it proves nothing on the two engines where it was most likely to
be tried.

### The arithmetic pair

For a numeric position the equivalent pair is a value and an expression that
evaluates to it: `1` against `2-1`, or the appended no-op `-0`.

A literal marker cannot serve here for the same reason it cannot serve in
extraction: a template that echoes input reproduces a literal and cannot perform
arithmetic. If `2-1` returns the record for `1`, something evaluated the
subtraction, and the only thing in the path that evaluates SQL arithmetic is the
engine.

Pick an expression whose two forms have the same length where the response
length is being compared, and watch for a framework that coerces types before
any statement is built — the commonest reason a numeric probe returns a clean
negative from a parameter that is genuinely concatenated further down.

### What decides stacking

A stacked statement — `'; SELECT 1--` — is a second statement sent in one
string. Whether it executes is decided by the **client library**, not by the
engine:

- PostgreSQL executes multiple statements in a simple-query message, and refuses
  them in the extended protocol most drivers use for parameterised calls.
- MySQL stacks only when the connection was opened with multi-statements
  enabled, which is a connection flag and not a server setting.
- SQL Server stacks over most drivers, which is why the technique is associated
  with it.
- Oracle does not stack in an ordinary statement at all; the equivalent is an
  anonymous PL/SQL block.
- SQLite is decided entirely by the binding: Python's `sqlite3` refuses a second
  statement in `execute` and accepts one in `executescript`.

The consequence for a report: "stacked statements are not available" is a
statement about *this deployment*, and a driver upgrade or a connection-string
change can make it false without anybody touching the application. Record the
driver and the connection flags beside the result, or the finding will be
re-tested from scratch in six months.

### Where second-order injection hides

The defining property is that the store is **silent**. The value is written
successfully, no error appears, nothing in the response suggests anything
happened — and the statement that breaks is built later, somewhere the tester
was not looking.

The three places it surfaces, in rough order of how often:

1. **An export or report** — a CSV or PDF generator concatenating stored values
   into a query that filters or joins on them.
2. **An administrative listing** — a back-office screen that no ordinary user
   sees, frequently older than the application's public half and written before
   the ORM was adopted.
3. **A scheduled job** — a nightly aggregation, a billing run, a
   synchronisation. This one is the hardest to observe and the one with the
   widest blast radius, because it runs as a privileged account and its failures
   go to a log nobody reads.

So the carrier payload is chosen to be traceable rather than clever: a unique
marker with the syntax attached to it, written into every field that accepts
one, and then a deliberate search for where the marker comes back out. The
marker is what makes the read-back findable; the syntax is what makes it break
when it is found.

### The four refusal shapes

A refusal is evidence about *where* the refusal happened, and reading it wrongly
costs an afternoon:

| Shape | What it looks like | Where it sat | Next |
|---|---|---|---|
| **Engine error** | Driver or SQL text, a line number, a constraint or column name | The statement — the value reached the parser | `HRR-INJ-01-ERROR`; the channel may carry values |
| **Application error page** | The application's own template, generic wording, HTTP 200 or 500 | The application caught the exception | `HRR-INJ-01-BOOL` or `-TIME`; the injection may be live with no visible channel |
| **Filter block** | A different template entirely, a 403, a themed page, sometimes a reference number | Upstream of the application | `HRR-INJ-01-EVADE` — nothing about the database has been learnt yet |
| **Silent normalisation** | Baseline response, no error, payload gone from any echo | A sanitiser, or a type coercion | Re-probe in another context; the parameter may still be injectable elsewhere |

The inert control payload in `payloads/sqli/probe.yaml` exists for the third
row. It looks hostile and contains no SQL. Blocked identically to the quote, the
block is a signature filter and not a query error — which is the difference
between "this parameter is safe" and "this parameter is behind a WAF", and those
two conclusions lead to opposite reports.

## Related units

- `HRR-INJ-01-PROBE` — establishes the context, and is the sole producer of
  `surface.sql.injectable`.
- `HRR-INJ-01-FPRINT` — the engine, which decides payload syntax for everything
  downstream.
- `HRR-INJ-01-STACK` — a second statement, decided by the driver as above.
- `HRR-INJ-01-SECOND` — the silent-store case.
- `HRR-INJ-01-EVADE` — where a uniform refusal goes before it is read as a
  negative.
