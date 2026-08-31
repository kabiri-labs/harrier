# Object ownership, and how to tell a control from a coincidence

Shared by all five `HRR-ACL-02` units. There is no payload axis here and nothing
is injected: every unit is a comparison between two principals, so the whole
difficulty lives in the oracle and in the evidence. This card is that
difficulty, written once.

## Recall

**Two accounts, always.** One account plus a guessed identifier is a worse test
— it cannot tell a refusal from an absence — and a riskier one, because the
guess lands in a real customer's records.

**A status code cannot tell you what happened.** Authorized-and-found-nothing
and served-somebody-else's-record are the same 200 with a different body. Read
the body.

**Read the write back through the route that consumes it**, never through the
route that wrote it. A 200 on an update whose fields were all discarded is the
commonest outcome.

**Opaque is not unguessable.** Encoded counters, timestamp-bearing identifiers
and hashes of small inputs all look random and all narrow to a walkable space.
Decode two and compare.

**The boundary is enforced once and missed twice.** Exports, reporting, batch
and administrative routes read the same store directly, and were written later.

**A bounded sample is the finding. A sweep is an incident.**

---

## Depth

### The two-account method is the technique

Everything else in this topic is a variation on one move: perform the same
request as two different principals and compare what comes back.

That is worth stating plainly because the alternative — one account and a
guessed identifier — is so much easier to reach for, and it is worse in three
separate ways.

1. **It cannot distinguish a refusal from an absence.** A guessed identifier
   that returns nothing might have been refused, or might not exist. With the
   second account you know the object exists, because you just looked at it.
2. **It cannot establish the baseline.** The question is not "does this endpoint
   return data" but "does it return data *it should not*". Without the owner's
   own response to compare against, there is nothing to say the response is
   wrong.
3. **It puts the tester into real records.** A guess that succeeds has returned
   somebody's data — a real customer's, on the balance of probability, since
   they outnumber the test accounts by whatever the application's user count is.

So the first thing an engagement needs for this topic is not a tool. It is a
second account, and where the application is multi-tenant, a second tenant.
Where the client cannot provide one, that is a scoping conversation rather than
a reason to guess.

### The empty-record trap

This is the false positive that costs an afternoon, and it is the same one in
`-PEER`, `-TENANT` and `-IMPACT`.

An endpoint asked for an object the caller does not own has three plausible
behaviours, and two of them are the control working:

| What happened | What it looks like |
|---|---|
| Refused: the check ran and said no | 403, or 404, or a 200 with an error body |
| Authorized, found nothing: the check ran, scoped the query to the caller, and the query matched no rows | **200 with an empty or skeletal record** |
| Served: no check, or a check that read the wrong thing | 200 with the other principal's data |

Rows two and three are both 200. An application that renders a template around
whatever the query returned will produce a page in both cases — same status,
similar length, and a body that is empty in the way an unfamiliar application's
bodies often are.

The discriminator is the owner's own response. Fetch the object as its rightful
owner first, keep that response, and compare. If the field that carried
`"Acme Ltd"` for the owner is absent for the other caller, the query was scoped
and the control held. If it carries `"Acme Ltd"` again, it did not.

This is why `evidence` on every unit here names *two* requests. One response
proves nothing in this topic.

### Reading a write back through the consumer

A write across an ownership boundary has its own version of the same trap, and
it is worse because the tester has already changed something.

Applications routinely answer 200 to an update whose fields were all discarded:
a serializer with an allow-list drops the unknown ones, an ORM ignores
attributes not in the model, a handler validates and then writes only the fields
it recognises. The response says success because the request was well-formed,
not because anything was stored.

So the write's own response is never the evidence. Read the object back:

- **as its rightful owner**, because reading it back in the writing session can
  be served from a cache or from an optimistic client-side copy of what was
  sent;
- **through the route that consumes the value**, not the one that displays it. A
  field can be echoed on an edit form and ignored by the settlement job that
  actually reads it, and the finding is about the second.

And restore it in the same session. A restoration deferred to "later in the
engagement" is one that gets forgotten when the next finding appears.

### Identifiers that look opaque and are not

The topic's `triage` fields name identifier shapes because the shape decides
whether `-IMPACT` is even worth entering. Three shapes are routinely recorded as
unguessable and are not:

- **An encoded counter.** Base64 of `1043`, hex of a row id, a URL-safe encoding
  of either. It looks like a token. Decode two identifiers issued in sequence
  and the difference is `1`.
- **A timestamp-bearing identifier.** UUIDv1, ULID, Snowflake and most "sortable
  unique id" schemes carry a creation time in their high bits. Two records
  created seconds apart differ in a way that says how the space is ordered, and
  a window of interest narrows it enormously.
- **A hash of a small input.** `md5(user_id)` is unguessable in the way a
  four-digit PIN is unguessable: not at all, once you know the input space.

The method is the same for all three: take **two** identifiers the engagement
was issued, decode them the same way, and compare. One identifier looked at in
isolation tells you nothing — which is why the unit's first false positive is a
random-looking identifier recorded as unguessable on the strength of a single
look.

A genuinely random identifier is a real reduction in exposure. It is not an
authorization control, and the mitigation says so.

### Where the boundary is enforced once and missed twice

The ordinary read route is the one everybody tests, and it is frequently the one
route where the check is present. The same store is read by:

- **Export and report routes** — CSV, PDF, scheduled emails. Written to a
  different brief, often by a different team, often querying directly.
- **Batch and bulk endpoints** — a route taking a list of identifiers where the
  check was written for one, or applied to the first element only.
- **Administrative routes** — older than the public half of the application, and
  guarded by "you have to be an admin to reach this" rather than by an ownership
  check.
- **The API beside the page** — or the page beside the API. Whichever was added
  second usually reimplemented the check rather than sharing it.
- **Method overrides and alternative verbs** — `POST` with `_method=DELETE`,
  `PATCH` where the check was written for `PUT`.

Hence the sequence in every unit here: *one route of each kind* rather than one
route many times. Ten repetitions against the read endpoint establish one fact.
One attempt against each of read, list and export establishes three, and the
third is where the finding usually is.

### The ceiling

`-IMPACT` is the unit that can turn an engagement into the breach it was hired
to prevent, and the distinction that keeps it on the right side is between a
**sample** and a **sweep**.

A sample is a handful of adjacent identifiers, bounded by a number agreed in
writing before the first request, which establishes that the space is walkable
*at that point*. A sweep is the enumeration itself — and it is not a better
finding, it is the same finding plus a copy of the client's records on the
tester's disk.

The honest report says: *the identifier space is sequential; a bounded sample of
n adjacent identifiers was requested and n were served; the reachable proportion
is therefore at least this and the route places no observed limit on it.* That
is a bounded estimate with its sample attached. An estimate that outruns its
sample — "all 400,000 customer records are exposed" from a sample of eight — is
the claim that turns a real finding into a report the client's engineers can
dismiss.

Where a list or export route returns many objects for one request, prefer it
over walking anything — **once you have bounded it**. That qualification is the
whole of the difference between the cheapest observation in the topic and the
most damaging one.

A paginated route with the page size set to five is one request that touches five
records and settles the question. The same route with no enforced limit is one
request that retrieves the entire cross-account dataset, and no ceiling agreed
for the adjacent-identifier series applies to it, because that series was never
sent. The tester has performed the mass disclosure they were hired to find.

So the bound is established *before* the request, not discovered from the
response:

- set the page size to a small number and confirm from the owner's own session
  that the route honours it;
- where the route accepts no bound, or accepts one and ignores it, do not send
  it. It is recorded as unbounded from its parameters and from the owner's own
  result — the request that would prove it is the disclosure.

And where such a route *would* return the whole space, the finding is that it
would. Not the response.

### One gap is not a boundary

The adjacent-identifier series has the opposite failure. Stopping at the first
identifier that is not served produces a false negative, because a sequential
space is full of ordinary holes: deleted records, rolled-back transactions,
identifiers allocated and never used.

One miss is a gap. A run of refusals is a control. So the series is carried to
the agreed ceiling rather than abandoned at the first miss, and every identifier
is recorded as served, refused or absent — three outcomes, not two. Where the
engagement holds identifiers already known to exist, prefer those: they remove
the ambiguity entirely, because an absence is then impossible and only a refusal
can explain a non-response.

## Related units

- `HRR-ACL-02-MAP` — the identifier inventory, and the sole producer of
  `artifact.objectid.known`.
- `HRR-ACL-02-PEER` — another account of the same role; the baseline comparison.
- `HRR-ACL-02-TENANT` — the same move across a tenant boundary, where the
  discriminator is whether the tenant comes from the session or the request.
- `HRR-ACL-02-WRITE` — the read-back rule above is the whole of this unit's
  oracle.
- `HRR-ACL-02-IMPACT` — scale, and the ceiling that keeps it a sample.
