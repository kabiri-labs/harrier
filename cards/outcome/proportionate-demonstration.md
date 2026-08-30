# Proportionate demonstration

Shared by `HRR-OUT-01-IMPACT`, `HRR-OUT-04-IMPACT` and `HRR-OUT-06-IMPACT`: the
three outcome units ask different questions of different capabilities, and the
reasoning about *how much* to do to answer them is one argument written once.

## Recall

**The rule** — the smallest observation that answers the question is the whole
of the demonstration. Anything beyond it is no longer evidence; it is the harm
the engagement was hired to find, performed by the tester.

**Before the first observation, not after** — how much may be retrieved, where
it is held, who sees it, and when it is destroyed. A read cannot be un-taken,
and agreement obtained afterwards is consent to a decision already made.

**A schema is not data.** Table and column names establish that the store is
reachable. What is in it comes from a bounded sample or from nothing at all.

**Reversibility differs by outcome** — a read has none, a write may have one if
a restoration path was established first, and a stored client-side payload has
one only if its location was recorded when it was placed.

**The third party never agreed to anything.** For a client-side outcome, reach
is established from how the application stores and serves the payload, never by
delivering it to a real person.

---

## Depth

### Why proportionality is a rule rather than an instinct

Every one of these three units sits at the end of a chain that has already
succeeded. The capability is confirmed; nothing further is being tested. What
remains is a question about *worth* — what the read returns, what depends on the
written record, who receives what runs — and questions about worth have a
property the tests behind them do not: they are answerable at a wide range of
sizes, and the larger answers are not better ones.

A tester who dumps a customer table has not established more than one bounded
sample established. They have established the same fact and created a second
copy of the client's data, on a laptop, outside every control the client
operates. The finding did not improve. The engagement acquired a breach.

This is why the limit is written into the units as `safety` and `preconditions`
rather than left to judgement in the moment. In the moment, one more query
always looks free.

### What a schema establishes, and what it does not

Reading table and column names is the cheapest observation in `HRR-OUT-01-IMPACT`
and it is routinely over-read. A schema establishes:

- that the store is reachable through the confirmed route,
- roughly how the application models its data,
- which tables are worth a bounded sample and which are not.

It establishes nothing whatever about content. A column named `ssn` may be empty
in every row of a staging database restored into production hardware. A column
named `notes` may hold free text into which support agents have pasted card
numbers for four years. Naming is a developer's intention; content is a fact,
and only a sample distinguishes them.

The practical consequence: the category answers in the report cite the sample,
not the schema. A report that says "personal data is exposed" on the strength of
a column name has made a claim the tester cannot support, and the client's own
staff will be the ones to discover that — usually in the meeting where the
remediation budget is decided.

### Handling what was retrieved

Four questions, settled in writing before the first read:

| | |
|---|---|
| **How much** | A stated ceiling — a row count, a field count, a single record — rather than "as little as possible", which is not a limit |
| **Where** | One named location under the tester's control, not a working directory that gets synchronised somewhere |
| **Who** | The named people who write and review the report, and nobody else |
| **When destroyed** | A date, tied to the report's acceptance rather than to the engagement's end |

The reason these are agreed first is not procedural neatness. A tester who has
already retrieved more than the client expected is negotiating from a position
where the only honest options are an awkward disclosure or a quiet omission, and
the second one is how a security engagement becomes the incident.

Record what was retrieved precisely enough that the client's own logs and the
tester's account of the work agree line for line. A discrepancy discovered later
is indistinguishable from a concealed one.

### Reversibility, by outcome

**A read is irreversible.** Nothing undoes it. This is the entire reason the
limit sits before the observation rather than after it.

**A write is reversible only if arranged.** `HRR-OUT-04-IMPACT` requires a
restoration path established before the change, on a record the engagement
created where one exists. Restoring a field is not the same as restoring a
record: an application that stamps a modification time, fires a webhook on
change, or appends to an audit trail has produced state the restoration does not
reach, and the report says so rather than implying the target was left as found.

**A stored client-side payload is reversible only if located.** A payload placed
and not recorded is one the client cannot find and the tester cannot remove. The
location goes into the evidence at the moment of placement, not reconstructed
from memory at the end of the week.

### The third-party problem

`HRR-OUT-06-IMPACT` is the only one of the three whose subject is a person who
never agreed to anything. The client consented to the engagement. A visitor who
loads a poisoned page did not, and cannot, because they do not know it happened.

So the reach questions are answered from the application's own behaviour:

- **Who receives it** is read from where the payload is stored and which
  responses serve it — a per-request reflection, a record rendered to one other
  account, a page every visitor loads.
- **What the receiving context holds** is read from what the application grants
  a session of that kind, established with the tester's own accounts.
- **Whether it needs interaction** is read from the payload's own trigger, not
  from whether anybody triggered it.
- **Whether it persists** is read from whether it survives a fresh session and a
  cache the tester does not control.

Three of the six capabilities that reach this unit leave nothing in the
application at all, and the same questions still have answers. A chosen redirect
is read from the response that issues it — which destinations the parameter
accepts, and whether the browser follows without a prompt. A framed or
foreign-origin action is read from what the application does *not* send: a
missing frame ancestry directive, an origin the message handler never checks, a
state change that needs no token. An effect on a request in flight is read from
how the front end and the origin disagree about where one request ends. In each
case the artefact is in the attacker's page or on the wire, not in the client's
store, so there is nothing to remove — and the reach question is answered from
the response rather than from a delivery.

Every one of those is answerable without a single real user receiving anything.
A tester who cannot answer one of them without delivery records it as
unestablished and says why. That is a smaller finding than the alternative and a
truthful one.

The marker in a stored payload is silent for the same reason — a console entry
or a distinctive node rather than a dialog. A dialog raised in a stranger's
browser is not evidence anybody will ever see; it is an interruption in
somebody's afternoon, caused deliberately, by a person they never engaged.

## Related units

- `HRR-OUT-01-IMPACT` — what the readable data is worth, reached from eleven
  read capabilities across the catalogue.
- `HRR-OUT-04-IMPACT` — whether the altered records are read back.
- `HRR-OUT-06-IMPACT` — what is done through the other party, and the one unit
  here whose subject never consented.
