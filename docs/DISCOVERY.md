# Discovery — what a surface tag names, and what it cannot

A decision record. It exists because the model it replaces was one flat list,
and one flat list is what a future change will drift back into unless the
reason not to is written down.

---

## 1. What was wrong

`vocab/surfaces.yaml` declared 52 tags as a single navigation axis. Picked from
that one list, in the order the file happens to write them:

```
rest-api          an interface
payment           what the operation is for
multi-tenant      how principals are separated
sql-backed-param  a guess about what interprets a value
stored-then-rendered   something the tester saw happen
tls-endpoint      a property of the deployment
```

Every line there is a different kind of statement, and the list gave a reader no
way to tell. Three consequences followed, and all three were visible on the page
rather than hidden in the model.

**Selecting more could not narrow.** Each tag contributed its own topics and the
result was their union, which the page said outright: *"Choosing more than one
narrows nothing and adds."* Describing a surface more precisely returned more
tests, not fewer. With nothing to say that `rest-api` and `multi-tenant` are
different kinds of claim, there was nothing to intersect on.

**Implication crossed kinds, and the claims were false.** The file's own header
stated the rule — *"An emitted tag must state something true of every surface
carrying the emitting tag"* — and of the 20 edges, 19 broke it. `search` implied
a parameter reaching SQL, which the same file warns against two paragraphs
earlier: *"/search may not query a database and /profile may."* `multi-tenant`
implied an object identifier in a request, deriving an input location from a
deployment property. `login-form` implied a session cookie while its own
description said it covers *"SSO initiation and API token exchange"*, neither of
which sets one.

**The page printed those as fact.** Under a heading reading *"Also counted as
chosen, because the tags above imply them"*, with the explanation *"A tag
implies another where the second is true of every surface carrying the first."*
That sentence was true of one edge in the file.

## 2. What a dimension is

Seven, and a tag declares exactly one:

| Dimension | What it names | Not |
|---|---|---|
| `channel` | The interface the interaction happens over | What the interface is used for |
| `entry_point` | Where a controlled value enters or selects something | What consumes it afterwards |
| `business_function` | What the operation is for | Who is allowed to perform it |
| `security_context` | The identity, privilege, tenancy or browsing context it runs in | Where the deployment puts it |
| `environment` | A deployment or platform property | Anything about one request |
| `processor` | The component that interprets a controlled value | Anything confirmed — this is a hypothesis until observed |
| `observed_behavior` | Something the tester has actually seen | Anything the catalogue asserts |

The classification is made from each tag's **description**, not its name, and
the distinction earns its place immediately. `rest-api` is labelled *"Structured
machine-facing API"* and described as *"a programmatic interface consumed by
clients other than the rendered web application"*. Read that way it is a
`channel` that includes GraphQL — so the tag is misnamed rather than wrong, and
the one relation in the file that survives is `graphql → rest-api`.

### Three that sit on a boundary

Recorded because the next reader will want to re-litigate them, and because a
classification whose hard cases are undocumented is a classification nobody can
apply.

**`privileged-function` → `business_function`.** Its description is about *"a
function whose availability is meant to depend on the caller's role"*, which is
a function and a context at once. It is filed as the function, because that is
what a tester is looking at; the role gate is a `security_context` tag applied
alongside when it is known.

**`server-fetch` → `observed_behavior`.** Genuinely compound. The description
says *"a function where the server retrieves a resource"* and the discovery hint
lists features — URL preview, webhook registration, import-from-URL. The
security-relevant half is the observation that an outbound request happened, and
that is what a tester selects it for. Splitting the feature from the evidence
means retagging topics and is content work, not this change.

**`admin-panel` → `business_function`.** Its description leads with audience —
*"a surface whose intended audience is operators"* — and follows with the
privilege boundary. The audience is the function.

## 3. Two relations, and why one was not enough

| | `parents` | `often` |
|---|---|---|
| Claims | True of **every** surface carrying the tag | Commonly carried as well |
| Crosses dimensions | No | Yes — that is most of its use |
| Closed transitively | Yes | No |
| On the page | Reported with the tags the reader chose | Reported separately, as association |

The defect was never the edges. It was that one relation carried two meanings
and the page printed the stronger one. Deleting the 19 that failed as
implications would have cost real navigation — selecting `search` would have
dropped from 44 tests to 16 — while fixing nothing that a truthful label does
not fix.

So 16 became associations, 1 stayed an implication, and 3 were deleted outright
because relabelling them would not have made them coherent:

- `login-form → session-cookie` — contradicted by `login-form`'s own description.
- `multi-tenant → object-id-param` — a deployment property producing an input location.
- `search → stored-then-rendered` — a search box is not itself a surface where
  input is stored and later rendered in another user's context. Its results may
  display stored content; the tag is about the storing surface.

Both are reported per topic as well as per selection, and that is where the
first attempt at this got it wrong. Correcting the paragraph above the results
and leaving the reason line on each card alone left the page still saying
*"Matched because the context is: Parameter reaching a SQL data store"* over a
topic a search box had only been associated with -- the disclaimer two inches
above it, saying the opposite. Every tag that reaches a topic now carries which
of the three relations did it, and the card writes a separate sentence for each,
because one sentence cannot be true of all three.

`often` is not closed transitively, and the reason is worth stating: a search
box is often backed by SQL, a SQL parameter is often an object identifier, and
chaining those arrives at a claim nobody wrote. It **is** inherited down
`parents`, which is a different operation and is sound — whatever is often true
of machine-facing APIs is often true of the GraphQL endpoints that are ones.

## 4. What a selection still cannot do

Unchanged by this, and load-bearing:

**A selection establishes no capability.** The surface vocabulary and the fact
vocabulary do not meet. There is no mapping from a tag to a fact, and inventing
one would be the file asserting something about a target it has never seen. A
selection says what the catalogue files under the kind of surface described,
which is a statement about the catalogue.

**An association is not evidence.** `search → sql-backed-param` says these are
often seen together in applications generally. It does not say the search box in
front of you reaches a database, and the page's wording carries that on every
screen where the relation surfaces.

**A processor is a hypothesis.** Every tag in that dimension names something
believed to interpret a value. Confirming it is what a test is for; selecting it
is how the catalogue is asked which tests would.

## 5. What this change deliberately did not do

**Intersecting selection.** The selector is grouped by dimension as of 0.28.0,
and the selection is still a union. Narrowing across dimensions was measured
before it was built and cannot work at topic level: 82 topics carry a tag at
all, they declare 2.17 of them on average, and 53 of those 82 speak about a
single dimension, so the number of topics speaking about both `channel` and
`entry_point` -- the ceiling
on what such an intersection could ever exclude -- is 1, and for `channel` with
`processor` it is 0. On `rest-api` + `object-id-param` + `multi-tenant` a strict
intersection returns 1 topic against the union's 11.

The rule is not what is wrong; the object is. A topic is a subject and usually
describes one aspect of it, while a test is specific enough to be several kinds
of thing at once. The intersection waits on unit-level mapping, below.

**Unit-level mapping** began in 0.29.0, and the intersection above is what it
unblocks. A test declares its own surface where its applicability differs from
its subject's and then answers for itself; a test that declares none is still
answered for by its subject and inherits the whole list. Selecting
`multi-tenant` reached all five object-level access-control tests and now
reaches the one that is about tenancy, with the other four folded under it
rather than dropped.

19 tests across 5 topics carry a clause; the rest of the catalogue is still
answered for by its topics. What makes mapping a topic a few tests at a time
safe is that a clause is written only where it differs — the tests without one
keep inheriting, so nothing is lost half way through. See
[`AUTHORING.md`](AUTHORING.md) section 5.

**Renaming `rest-api`.** It means "machine-facing API" and says so in its label.
Renaming a tag changes every URL carrying it, and the classification above is
what makes the mismatch legible in the meantime.

**Splitting `server-fetch`.** See section 2.
