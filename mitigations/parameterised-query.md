# Parameterised queries

Applies to `HRR-INJ-01`. Cross-references: ASVS V1.2, CWE-89.

## The fix that works

**Bind the value; do not build the statement around it.** A prepared statement
sends the SQL text and the parameter values to the engine as separate things.
The engine parses the text once, with placeholders where the values go, and the
values never reach the parser. A quote inside a bound value is a quote inside a
string, because by the time the value arrives there is no longer a grammar for
it to break.

This is the whole of the fix, and the reason it holds where escaping does not:
escaping tries to make a hostile value safe inside a statement, and binding
means the value was never inside the statement in the first place.

Two things follow that are easy to get wrong:

- **A prepared statement built by concatenation is not a prepared statement.**
  `prepare("SELECT * FROM t WHERE id = " + id)` prepares an injected statement
  perfectly. The placeholder has to be in the SQL text the code wrote.
- **Binding is per value, not per statement.** One bound parameter beside three
  concatenated ones is three injection points, and the presence of the first
  is what usually stops anybody looking for the other three.

## What cannot be bound

Placeholders stand in for **values**. They do not stand in for identifiers or
for syntax, so these four cannot be bound and need a different control:

| | The control |
|---|---|
| Table and column names | An allow-list mapping a request token to an identifier the code contains. Never the request value itself, quoted or otherwise. |
| `ORDER BY` column and direction | The same allow-list. The sort column is the identifier position `HRR-INJ-01-PROBE` exists to find, precisely because no quote is involved and a quote-based probe comes back clean. |
| `LIMIT` and `OFFSET` | Bindable on most engines; where the driver refuses, cast to an integer in code and range-check it. Do not concatenate the string. |
| A dynamic `IN` list | Generate one placeholder per element and bind each. Joining the elements into one string re-introduces exactly what binding removed. |

An allow-list here means a fixed map in the source, checked with equality. A
regular expression that "looks like a column name" is a blacklist wearing an
allow-list's clothes: it admits every identifier the developer did not think of,
including the ones the schema does not have.

## What least privilege changes

Binding stops the injection. Privilege decides what an injection that got
through anyway is worth, and the two are not alternatives — the second is what
makes the difference between a finding and an incident.

Against each capability the topic charts:

- **Read** — an account granted `SELECT` on the tables the feature uses reads
  those tables and no others. It is the difference between one feature's rows
  and the whole store, which is precisely the question `HRR-OUT-01-IMPACT` asks.
- **Write** — an account with no `INSERT`, `UPDATE` or `DELETE` on tables the
  feature only reads cannot reach `primitive.db.write` at all, and the
  integrity outcome behind it disappears with it.
- **Stacked statements** — usually decided by the driver rather than by
  privilege, but an account without DDL rights cannot use a second statement to
  change the schema even where stacking is available.
- **Out-of-band** — the functions that make the database open a network
  connection are grants, not features. Revoking them removes the channel that
  survives when nothing is rendered and nothing is timed.
- **Reading files from the database account** — a separate grant again, and the
  route by which a database read becomes a filesystem read.

Separate accounts per application, no shared administrative account, and no
application connecting as the schema owner.

## What does not work

**An escaping helper.** It is correct only for the context it was written for.
A helper written for a quoted string does nothing for a numeric position, where
no quote is needed, and nothing for an identifier position, where a quote is
wrong. The value that defeats it is not an exotic one; it is an ordinary integer
in a place the helper never expected.

**A blacklist of keywords or characters.** `HRR-INJ-01-EVADE` exists because
every such list has a case variation, a comment interruption, an encoding layer,
a whitespace substitute or an operator synonym that passes it. A control whose
failure mode is "somebody wrote it differently" is not a control.

**A stored procedure that concatenates internally.** The procedure boundary
moves the concatenation out of sight and changes nothing about it. Procedures
help only when they too use parameters.

**An ORM used in a way that concatenates.** Every mainstream ORM binds by
default and every one offers a raw-fragment escape hatch — a raw SQL call, a
`where` taking a string, an ordering taken from user input. The ORM is not the
control; the absence of string building is. Grep for the escape hatches by name
rather than trusting the library's reputation.

**Input validation as the fix.** Rejecting a quote is worth doing and is not a
remediation: it narrows the payload space without removing the defect, and it
sends a maintainer looking at the wrong layer for years afterwards.
