# Inference: reading a database one bit at a time

Shared by `HRR-INJ-01-ERROR`, `HRR-INJ-01-BOOL`, `HRR-INJ-01-TIME` and
`HRR-INJ-01-OOB`: four different channels, one model. The model is written once
here because choosing between the four is the decision the card exists to
support.

## Recall

**One model** — every technique here is a one-bit oracle, repeated. The cost of
the finding is the number of requests times the cost per bit, and that product
is what decides whether a technique is usable on a given target.

**Baseline before differential** — measure the endpoint's own variation, in
content and in latency, before reading any difference. A differential smaller
than the noise is not a differential.

**Pad both forms to the same length** — otherwise the difference being read is
the payload's length rather than its truth.

**The delay holds a connection.** It shows on its own request, synchronously.
What the held connection does is add latency to *other* requests, the control in
your own pair included.

**One label per request, not per engagement** — an out-of-band label that
repeats cannot say which request produced which interaction.

**Order: error, then boolean, then time, then out-of-band** — error returns a
value per request, the two inference channels a bit, and time multiplies each
bit by the delay.

---

## Depth

### Two shapes, not one

The four channels divide into two, and the division is what the choice between
them turns on.

**Direct extraction — error and out-of-band.** The channel carries a value, not
a verdict. An engine error quotes the offending operand, and an out-of-band
lookup carries a computed string in the name it resolves. One request returns as
much of the value as the channel is wide, so the cost is one or two requests
per value and the limit is *width* rather than length: an error message
truncates, a label has a length ceiling, and a long value is read in a few
bounded slices rather than a few hundred requests.

**Inference — boolean and time.** The channel carries one bit. The tester writes
a condition, the statement evaluates it, and true or false comes back. Reading a
value means asking about it until enough bits have arrived:

```
requests = bits × repetitions
cost     = requests × cost-per-request
```

For a character-at-a-time read with a binary search, "bits" is about 7 per
character. A 30-character version string is therefore around 210 requests
without repetition, and around 630 with the three repetitions a noisy endpoint
needs -- against one or two for the same string through an error message. That
two-order-of-magnitude gap is why the ordering below matters, and why every unit
in this family stops at one short metadata value: the technique is proven by the
first value, and everything after it is arithmetic somebody else is paying for.

### Measure the baseline first, in both dimensions

The differential is read against the endpoint's own variation, so the variation
has to be a measured number rather than an assumption.

**For content**, send the unmodified request ten times and record status, body
length and any rendered counter. What you are looking for is not the average but
the *spread*. An endpoint that returns three distinct lengths for identical
requests — a rotating advertisement, a timestamp, a session-dependent greeting —
has a content channel that cannot carry a one-bit signal unless the signal is
larger than that spread.

**For latency**, the same ten requests give a distribution rather than a number.
Record the median and the maximum. The rule that follows: an injected delay has
to clear the observed maximum, not the median, and clear it by enough that a
single slow request cannot be mistaken for a true bit. In practice this means a
delay several times the spread, which on a variable path is why a two-second
delay is unreadable and a ten-second one is merely slow.

An endpoint whose variation exceeds the differential is the `inconclusive`
branch of the oracle, and recording it as a negative is the mistake this whole
section exists to prevent. "No difference observed" and "no difference
observable" are different findings.

### Why both forms are padded

The boolean pair is two requests that differ only in the truth of a condition.
If they also differ in length, then anything in the response that reflects the
request — a query string echoed into a link, a rendered parameter, a byte count
— moves for the wrong reason.

`' AND 1=1 AND 'a'='a` and `' AND 1=2 AND 'a'='a` are the same length by
construction, which is why they are written that way rather than as the shorter
`' AND 1=1--`. It costs nothing and removes an entire class of false positive.

The same discipline applies to the extraction payloads: when the comparison
bound changes from `64` to `100`, the payload's length changes by one character.
On a sensitive endpoint that is enough, and the fix is to zero-pad the bound.

### The connection-pool inversion

This is the property that makes time-based inference different in kind from the
other three, and it is stated as a fact rather than a caution.

A delay function does not idle the request. It holds the database connection for
its duration. On an application with a connection pool — which is nearly all of
them — that connection is unavailable to every other request for the whole
delay. With a pool of ten and a ten-second delay, ten concurrent probes exhaust
the pool, and the eleventh request, belonging to a real user, waits.

Two consequences:

1. **The contention lands on other requests, not on this one.** A synchronous
   query holds its connection until the delay finishes, so the delayed request
   is always the slow one -- the signal never moves off its cause. What moves is
   everything else: the control form sent immediately after a delayed one can be
   slow because the pool is still draining, which makes a false condition look
   true. Alternate the pair, leave the pool time to recover between them, and
   compare medians rather than adjacent readings. (The exception is a genuinely
   asynchronous path -- a query the application fires and does not wait for, or
   one that hits a statement timeout -- where the delay is absorbed rather than
   observed, and the channel has to be read some other way.)
2. **This is a denial-of-service primitive at low request rates.** Not at flood
   rates — at ten requests. That is why `HRR-INJ-01-TIME` is the one unit in the
   topic whose `safety` names an availability limit, and why a timing sweep is
   agreed with the client rather than run because it is next in the list.

Where the endpoint is a write path — an insert, an update, a queue submission —
the pool pressure is worse, because those connections are frequently drawn from
a smaller pool with a longer hold.

### One label per request

Out-of-band extraction sends a lookup to a resolver the tester controls, so the
observable is an interaction record rather than a response.

The label in that lookup must be unique **per request**, not per engagement.
With one label for the whole engagement, an interaction proves only that
something, at some point, reached the resolver — which cannot distinguish the
request that succeeded from a retry, a cached resolution, a second tester, or a
resolver's own probe. With a label per request, each interaction names its
cause.

Two further properties worth writing into the report:

- **The data leaves the client's network by design.** The value being extracted
  travels through every resolver on the path in a name that gets logged at each
  one. That is a disclosure to third parties the client did not choose, which is
  why the technique is agreed rather than assumed and why what is extracted stays
  metadata.
- **A negative is weak.** No interaction may mean the injection failed, or that
  egress is filtered, or that the resolver never saw it. An egress control probe
  — the same request with a known-good lookup — is what turns a silent negative
  into a readable one.

### The ordering, and why it is not arbitrary

Work the channels in this order, and stop at the first that answers:

| | Requests per value | What makes it available |
|---|---|---|
| **Error** | 1–2 | The application returns the driver's exception text, or a distinguishable error class |
| **Boolean** | ~7 per character | Anything in the response depends on the result set |
| **Time** | ~7 per character, each costing the delay | The statement executes at all |
| **Out-of-band** | 1–2 | The engine can open a network connection *and* egress is permitted |

Error and out-of-band are both roughly constant per value, and boolean and time
are both linear in the length of what is read — but time multiplies each request
by the delay, which is why it sits an order of magnitude beyond boolean in wall
clock even at the same request count.

Out-of-band is last despite its low request count because its preconditions are
the least often met and its negative is the least informative. It is the channel
to reach for when the first three returned nothing, not the one to start with.

The practical rule: a technique that would take four hours to read one value has
not established a channel worth reporting as usable. It has established the
capability, which is the finding, and `HRR-OUT-01-IMPACT` is where the question
of what that capability is worth actually gets asked.

## Related units

- `HRR-INJ-01-ERROR` — the cheapest channel, and the only one that also
  discloses the statement's own structure.
- `HRR-INJ-01-BOOL` — the fallback when errors are suppressed and nothing
  renders.
- `HRR-INJ-01-TIME` — the last in-band channel, and the one with an availability
  cost.
- `HRR-INJ-01-OOB` — the channel that works when nothing at all comes back.
- `HRR-INJ-01-UNION` — not an inference technique: it returns chosen values
  directly, which is why it is tried before any of these four.
