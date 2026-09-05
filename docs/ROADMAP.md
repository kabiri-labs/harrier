# Roadmap

Build state. **Every change updates this file in the same pull request as the
work.** A roadmap updated only when someone remembers is the same failure mode as
a test plan updated only when someone remembers.

Status: `done` · `in progress` · `not started`

---

## Definition of 1.0

> Every WSTG identifier decomposed into units, every unit carrying a falsifiable
> objective, and at least two topics authored to full depth so the model can be
> judged on real content rather than on its own description.

At **0.4.0**: the first two clauses are met and the artefact exists. One topic is
written to full depth, not two. The version tracks the artefact because that is
the only thing anybody consumes -- and 0.4.0 changed what the artefact is, which
is why the jump is a breaking one taken deliberately while it still can be.

Explicitly **not** in 1.0: a full card for every unit. At the granularity this
model produces, that is a 300-hour writing project — and it is not what makes the
taxonomy useful. Cards are written on demand, indefinitely.

## Phases

| # | Phase | Status | Note |
|---|---|---|---|
| 0 | Foundation | `done` | Documents, 14 domain codes, 6 axis vocabularies, 36 surface tags, 5 dimensions, WSTG pinned and fully mapped. No content. |
| 1 | Schema and validator | `done` | Seven schemas, six validation passes, offline suite, CI. Identifiers, axis slugs, every cross-reference and the three depth tiers are machine-checked. Cheap now, impossible to retrofit across 350 files. |
| 1.5 | Pin the reference standards | `done` | ASVS 5.0.0 at its release commit, CWE 4.20 by versioned archive and content hash. `refs.asvs` and `refs.cwe` both resolve. CVE stays out: it names one bug in one product, not a class. |
| 2 | Topic map | `done` | 99 topics across 13 domains. Every resolvable WSTG identifier is claimed by a topic, and the validator now rejects one that is not. |
| 3 | Unit outline pass | `done` | Every topic decomposed to units carrying an identifier, a title and a falsifiable objective. **This is where the artefact becomes genuinely useful.** Done in six batches of two or three domains, because a review of 350 files at once is not a review. |
| 4 | Chain model spike | `done` | Five units authored across five domains and five shapes, plus the fact layer they needed. The point was to break the model while it was cheap to change, not to add coverage. |
| 4.5 | One topic at depth | `done` | `PTN-RES-01` written all the way down: five authored units, four payload files, a shared card, the first mitigation. A calibration pass, not a coverage one -- it settles how concrete a written unit is before three hundred more are written to match it. |
| 5 | Chain pass | `done` | `requires` and `yields` for all 366 units, in six domain batches, `RCN` first because recon produces most of the base facts. 177 capabilities, and the gate at the end -- every non-given fact has a producer -- is enforced from here on. |
| 6 | Published artefact | `done` | `pentest-navgrid build` writes one self-contained HTML file with every card, payload and mitigation embedded. Versioning starts here, at 0.1.0. Its first navigation model -- a surface-anchored board driven by the facts a tester ticked -- was replaced in phase 6.5. |
| 6.5 | Product pivot | `done` | Pentest NavGrid becomes an execution companion to a standard rather than a workspace about a target. Standard-first navigation, atomic decomposition per WSTG test case, a derived local chain per unit, a progressively disclosed general graph, and the removal of every piece of engagement state. **Breaking, and deliberate.** See [`PIVOT.md`](PIVOT.md). |
| 6.6 | Second entry point | `done` | The catalogue could be entered from a standard or from a capability, and a tester mid-engagement holds neither: they are looking at an upload, a sort parameter, a token. 0.19.0 makes the attack-surface tags navigable — they had been on every topic since phase 0 and reached the page as inert text — so a context selects the tests filed under it, says which tag matched, and separates the tests nothing has to precede from the ones waiting on a capability. It selects; it establishes nothing. The tag vocabulary and the fact vocabulary do not meet, so no context can be read as a capability in hand, and the file still holds no target. |
| 7 | Beyond WSTG | `not started` | The topics WSTG does not cover: JWT, OAuth/OIDC, GraphQL, WebSocket, request smuggling, cache poisoning and deception, prototype pollution, race conditions, dependency confusion, cloud metadata, LLM-integrated surfaces. Pentest NavGrid Extensions exists to receive them. This is the clearest differentiation from restating WSTG. |
| 8 | Depth on demand | `ongoing` | Cards written when a real engagement makes one worth writing. Never speculatively. Since 0.10.0 a unit can be sketched rather than only outlined or written in full, so the step from breadth to usable depth is twenty minutes rather than two hours. 0.11.0 sketched the seventeen reconnaissance and configuration topics an engagement opens with. 0.14.0 authored the terminal outcome layer first, because a chain whose last step is an outline stops at a capability rather than at an outcome; 0.15.0 wrote the supporting layer for SQL injection before its units, because the validator rejects a unit referencing a card or a mitigation that does not exist yet; 0.16.0 took the nine remaining `PTN-INJ-01` units to full depth, which makes SQL injection the first chain readable end to end from the standard's own test case to a stated business outcome; 0.17.0 did the same for object-level access control, a chain with no payload axis at all, where the whole difficulty is in the oracle and the evidence; 0.18.0 completed the third with cross-site scripting, whose eight context units are eight different answers to what has already been escaped by the time the value arrives. Three chains now run end to end rather than one. |

Phases 2–5 are 1.0. Phase 6 is what makes it usable; phase 7 is what makes it
better than the standard it is built on.

Surface tags are carried by the topic rather than by the unit, so a context
selects whole topics and lists every test in them. Where a topic spans contexts
a single tag cannot separate — the ten `PTN-CLT-01` units are ten output
contexts, not one — the selection is coarser than the catalogue could be. The
unit schema already permits `surfaces`, so refining it needs content rather than
a schema change, and it is not worth doing speculatively: the tags that would
benefit are the ones a real engagement finds too broad.

The order changed after phase 3: the artefact's main view is driven by the chain,
so the chain has to exist first, and depth waits until real use says which units
deserve it.

Phase 6.5 changed what the artefact is for. The board it removed was coherent,
and it asserted things about a target the file has never seen. What replaced it
answers a narrower question honestly: what is inside this test case, how is each
piece performed, and where can a success lead. The decision, the trade-offs and
the full list of non-goals are in [`PIVOT.md`](PIVOT.md) rather than here,
because a roadmap records what is being built and that document records why one
thing stopped being built.

## Public alpha

0.4.0 is the first version published for anyone outside the project to look at,
and it is an alpha in the honest sense: the decomposition is broad and the depth
behind it is not. Every resolvable WSTG identifier is claimed and 393 Test Units
exist; 36 are written to full procedural depth, 40 are sketched, and the far half
of the chain is barely charted.

Both figures are in the README rather than at the bottom of it, and the suite
reads them from the catalogue so neither can go stale in prose. The label is not
a disclaimer to be dropped once the project feels more finished -- it comes off
when the numbers say so.

## The standing rule

**Never let depth block coverage.**

A unit that exists as an outline — correct identifier, correct objective,
correct surface tags — already appears in the artefact, already counts, and
already stops a test being skipped silently. A unit that does not exist because
nobody has written its two thousand words does none of those things, and its
absence is invisible to the reader.

Depth is therefore written in tiers rather than in one step. An outline is five
minutes and a unit written in full is a couple of hours, which left nothing in
between and made the gap read as wider than it is: a **sketch** is twenty
minutes and carries the steps, the reading of a result, the mistake that most
often imitates a positive, and what finishing means. That is most of what a
tester uses in the field. What each tier requires is in the schema, so a status
cannot claim more than the file carries.

## Coverage

Two different numbers, kept apart because conflating them would let phase 0's
work read as phase 2's:

| | Count |
|---|---|
| **WSTG identifiers mapped to a domain** | **109 of 109** |
| **WSTG identifiers covered by a topic** | **108 of 108** |
| Topics | 106 |
| Units — outlined | 299 |
| Units — sketched | 40 |
| Units — authored | 54 |
| Units — charted | 393 |

*Mapped* means the ordered procedure resolved the identifier, which phase 0
finished. *Covered* means a topic exists that claims it, which phase 2 finished.
The denominators differ by one: `WSTG-INPV-14` is mapped to no domain because it
describes second-order delivery rather than a test, so nothing can cover it and
the validator does not ask anything to.

0.21.0 closes the half of the chain gate that was missing. The producer gate has
asked where a capability comes from since phase 5; nothing asked where it goes,
so a chain-tier capability no test declares a use for passed every check while
being exactly the place the chart stops earlier than the mechanism does. Those
are now registered in `vocab/facts.yaml` under the cause they belong to -- 12
open, in 2 causes -- and the validator rejects an unlisted dead end as well as
an entry for a gap that has since closed. It fills nothing; it makes the gap a
number that can only move by being worked on.

0.22.0 starts closing what that register records, and starts at the end rather
than the middle. Three topics established a capability and stopped: `PTN-CRY-05`
recovered a signing key and never minted a token, `PTN-ACL-04` obtained a role
above the granted one and never used it, and five `*-REVOCATION` units proved an
identifier outlives sign-out with nothing acting through it. Three outline units
-- `PTN-CRY-05-WRITE`, `PTN-ACL-04-IMPACT`, `PTN-SES-06-IMPACT` -- close 4 of the
register's entries between them and route each topic into the outcome layer that
already existed. The register is the measure: 41 open before, 37 after, and the
gate refused the fourth entry until it was removed, which is the ratchet working
rather than a courtesy.

0.23.0 finishes what 0.22.0 started, and finishes it by finding that most of the
register was not a backlog. 14 units close 23 of the 37 open entries, almost all
of them one shape: a test that requires the defeated control and establishes
what it permits. Seven end at a session belonging to somebody else -- a
credential the policy allows, a guessable recovery answer, a skippable second
factor, a reset token that outlives its use -- which the catalogue already had a
route from. The chart runs deeper than it did, and 29 tests stop short where 81 did.

Four of the units in that pass were wrong and an automated review caught all
four, each the same mistake: a fact was read against its description without
asking whether the description was narrow enough to carry the claim.
`control.content.internal` says "host names, paths, identifiers or
credentials", and a unit consuming it to establish another user's session
derived account takeover from a disclosed path. That one is now two results --
whether the detail is authentication material, and whether the material
authenticates -- joined by `artifact.credential.found`, the one capability this
work added. An audience test that repeated the test that produced its own
condition was removed; a key that a disclosure *would* hand over is no longer
read as a key in hand; and an unchecked handshake origin is required rather
than merely one of two sufficient conditions.

The other 14 were the finding. Ten permit nothing on their own and never will;
one is a carrier rather than a destination; and three were blocked on a
vocabulary that could not say "one stored object is readable". 0.24.0 closed
that third group by saying it -- `primitive.stored.read`, with the three tests
that establish it -- which emptied its cause entirely and left 12 entries in 2.
That a cause could be closed by naming a capability rather than by writing
around it is the argument for having separated the three reasons at all.

0.24.1 fixes a place where the picture and the list disagreed about the same
derivation. The tier vocabulary exists so that three different relations stop
printing under one heading, and the list beside the graph has grouped them by
tier since it landed -- but the graph headed its last column "Potential
continuation" whatever it held. For `PTN-INJ-01-PROBE`, whose nine outgoing
edges are nine contexts to try the same test in, that called nine alternatives
an escalation. The column is now headed by the relation it holds, in the
wording the list already uses, so the two views cannot drift into two
vocabularies.

Nothing about the derivation changed, and the count is unaffected: edges have
always been sorted with escalations first, so no escalation was ever hidden
behind an alternative. What was wrong was the word above them.

0.24.2 stops the routes view counting one route as several. `pathsToImpact` is
right to enumerate walks that differ anywhere as different walks -- its
signature is the whole shape -- but a reader given four cards that differ only
in which technique carries a step reads four ways in where there is one way
with four techniques. Cards are now grouped on the capability sequence together
with what each step still owes, and the alternatives sit at the step they are
alternatives for. Walks that leave different conditions outstanding stay
separate, because they are not interchangeable.

The search runs wider than it displays, since grouping a truncated search would
be the wrong order. A fixed multiple of the display count does not settle that
either -- it only makes it less likely -- so the search widens until it holds
four shapes or comes back short of the limit it was given, which is the signal
that it ran out of walks rather than out of allowance. That is not a nicety:
`surface.sql.injectable` filled all four old slots with one shape, so the route
through a stacked statement to a database write and on to lost integrity was
never drawn. Two capabilities now show an outcome the view had been hiding.

180 cards where there were 205, over the same 123 capabilities.

0.25.0 makes the page named for chains show them. It carried a picture of every
capability in the file, shaded by how far the chart reached from each -- a
glossary and a coverage measure, both worth having and neither a chain -- and
told a reader to open an impact "to see the routes charted to it". Opening one
said a chain ends here and stopped, because the only search the artefact had ran
forwards, and forwards from an outcome there is nothing. The claim was the wider
of the two.

`routesToImpact` walks the same relation backwards, and only backwards: finding
four routes to `impact.account.denied` by forward search and filtering on the
destination would mean enumerating nearly every walk in the graph, since about
one in two hundred arrives there. A walk is reported when it reaches a
capability nothing establishes -- what an engagement supplies rather than what a
test earns -- so what is drawn is a chain rather than the one-step restatement
of the tests listed above it. Both directions return the same step shape, so the
widening, the grouping from 0.24.2 and the drawing are one piece of code; a test
asserts that every route the backward search reports is a walk the forward
search reports from the same start.

Two things cannot be carried backwards and are settled in one pass over the
finished walk: what a step still owes, which depends on everything established
before it, and the forward rule that a walk may not arrive on a capability an
earlier unit already established. A walk breaking the second is dropped rather
than drawn, because the two directions describe one graph.

Beside the drawings, every capability from which a route to that outcome begins,
nearest first -- a reachability sweep of the graph rather than an enumeration of
its walks, which is a set and a distance in one pass where the routes to
`impact.data.disclosed` are several hundred walks to answer a question about 48
capabilities. The distance is a
lower bound and says so: a route travels through one of a test's conditions and
leaves the rest outstanding. The list is not cut off at five steps; the drawings
are, and the page says which is which.

The destinations now stand above the map on the chains page rather than below
it, each row carrying how many capabilities begin a charted route to it. The
wording is deliberate and is checked against the line in `PIVOT.md` that this
product exists on the right side of: a route is charted from a capability, never
available to a tester.

0.26.0 makes the search box answer the words this field actually uses. Titles in
this catalogue name mechanisms, which is the rule that stops two topics
inventing two names for one idea and is not up for revision -- but it means the
tests for what everyone calls IDOR are filed under `Object-level access
control`, and the four letters a tester types reached nothing at all. Neither
did `bola`, `lfi`, `ssti`, `ssrf`, `xxe`, `csrf`, `jwt`, `2fa` or `sqli`, and
`xss` reached one capability whose identifier happens to contain it. The aliases
in `vocab/search_aliases.yaml` close that: an alias is a spelling, not a
synonym, and each expansion is searched as if the reader had typed it instead.
The hits are reported as expansions and never merged into the ones the typed
term found -- the same split the context page makes between a tag chosen and a
tag implied.

The validator holds every entry to both directions. An expansion reaching
nothing is dead weight; an alias reaching nothing the bare term does not is
noise, which is what an alias becomes the day a title is reworded to carry the
shorthand itself. Neither would surface any other way: an alias that has stopped
resolving simply answers nothing, silently, which is the failure the file was
added to fix.

Order changed with it, and every rule in it is lexical. A term standing as a
word ranks above the same letters buried in a longer one, so `rce` no longer
opens on the tests carrying `force` and `resource`; a kind whose best
match stands as a word is listed before one where every match is buried, and a
heading where they all are says so rather than presenting a count of
coincidences. Within that, an identifier or a whole title outranks a match
further down the page. None of it is a judgement about which test is worth more.
A search box ordering by the catalogue's opinion of its own content would be
making one, and that judgement is the reader's.

Results past the fortieth in a kind are now folded rather than withheld. Saying
how many were not shown is not the same as being able to read them, and a reader
looking for one entry has no way to make a substring narrower.

0.27.0 makes the surface vocabulary say what kind of thing each tag names, and
stops the selection page printing an association as a fact.

52 tags sat in one flat list. `rest-api` is an interface, `payment` is what an
operation is for, `multi-tenant` is how principals are separated,
`sql-backed-param` is a guess about what interprets a value, and
`stored-then-rendered` is something a tester saw happen -- every one a
different kind of statement, with nothing to tell a reader which was which. Both
consequences of that showed on the page in its own words. Selecting more
could not narrow, because there was nothing to intersect on: *"Choosing more than
one narrows nothing and adds."* And implication crossed from one kind to
another, which is how a deployment property came to imply an input location.

Every tag now declares a `dimension` -- channel, entry point, business function,
security context, environment, processor, or observed behaviour -- chosen from
the tag's description rather than its name. That distinction pays immediately:
`rest-api` is described as *"a programmatic interface consumed by clients other
than the rendered web application"*, so it is a channel that includes GraphQL,
and the tag is misnamed rather than wrong.

`emits` carried two meanings and the page printed the stronger one. The file's
own header stated the rule -- *"An emitted tag must state something true of every
surface carrying the emitting tag"* -- and of the 20 edges, 19 broke it. `search`
implied a parameter reaching SQL, which the same file warns against two
paragraphs earlier. `login-form` implied a session cookie while its own
description covers *"SSO initiation and API token exchange"*, neither of which
sets one. The page presented all of them under *"Also counted as chosen, because
the tags above imply them"*.

So the relation split rather than shrank. `parents` is true of every surface
carrying the tag and stays inside one dimension; `graphql -> rest-api` is the
only edge in the file that qualifies, and topics reached through it are reported
as the answers they are. `often` records what such a surface commonly carries as
well, may cross dimensions, and is reported as association wherever it appears.
3 edges were deleted rather than relabelled, because relabelling would not have
made them coherent. Deleting all 19 was the other option and was rejected:
it would have taken `search` from 44 tests to 16 while fixing nothing that a
truthful label does not fix.

`often` is not closed transitively -- a search box is often backed by SQL, a SQL
parameter is often an object identifier, and chaining those arrives at a claim
nobody wrote. It is inherited down `parents`, which is a different operation and
is sound.

The reasoning is recorded in [`DISCOVERY.md`](DISCOVERY.md) rather than left to
be re-derived, and the rule the vocabulary had always cited but never carried --
`surfaces.yaml` pointed at `AUTHORING.md` for it, and `AUTHORING.md` said
nothing about relations at all -- is now written in the file the pointer names.

Nothing about the selection semantics changed: tags still union, the selector
still lists all 52, and a selection still establishes no capability. Narrowing
across dimensions is what the dimensions are for and is a change to what a
selection means, which is worth making on its own.

0.28.0 puts the vocabulary in the seven groups 0.27.0 gave it names for. 52 tags
in one grid asked a reader to hold the whole list to discover that `payment` and
`sql-backed-param` are not the same kind of answer. Each group now carries what
it names, and the two that need a caveat carry it where it is read rather than
in a document: a processor is a hypothesis until a test confirms it, and an
observed behaviour is something the tester saw rather than something this file
asserts.

Grouping is presentation, and the page says so under the groups. Seven labelled
rows look like a filter where you pick one from each and get the intersection,
which this page does not do -- every tag adds its own tests, as it always has.
A layout that implies a semantics the code does not have is the same defect as
prose that does, and it is worth as much care.

This was meant to be that intersection, and the intersection was measured before
it was built. It cannot work on this catalogue, and the reason is in the data
rather than in the rule. 82 topics carry a surface tag at all, they declare 2.17
of them on average, and 53 of those 82 speak about a single dimension; 22 speak
about two, 6 about three, 1 about four. So the ceiling on what an intersection
can ever exclude at topic
level is set by how many topics speak about both dimensions at once, and that
number is 1 for channel with entry point, 1 for channel with security context,
and 0 for channel with processor. Measured on the flagship case -- `rest-api`
and `object-id-param` and `multi-tenant` -- a strict intersection returns 1
topic and 5 tests where the union returns 11 and 39, and a lenient one that
declines to exclude a topic silent on a dimension returns 10 and 34. Unusable,
or indistinguishable from what it replaced.

The finer object is the unit, not the topic. A topic is a subject and usually
describes one aspect of it; a test is specific, and `PTN-ACL-02-TENANT` is an
object identifier and a tenancy boundary and a channel at once. `unit.schema.json`
has permitted `surfaces` since it was written and no unit uses it, so the
intersection waits for the mapping that gives it something to bite on rather
than shipping as a control that moves 11 to 10.

0.29.0 lets a test answer for itself. A tag was carried by the topic, so
selecting `multi-tenant` returned all five object-level access-control tests
when one of them is about tenancy -- the page said so under every result, and
saying so is not the same as fixing it.

A test now declares its own surface where its applicability differs from its
subject's, and the clause replaces the subject's for that test rather than
adding to it. That is why four of `PTN-ACL-02`'s tests repeat the channels they
share: the one thing they are saying is that they are not about tenancy, and
dropping the channels to say it would take away the answer their subject was
giving them. The fifth carries exactly the subject's list and declares nothing,
because the subject already says it. `multi-tenant` now reaches that one, and
the other four are folded under it rather than dropped -- a test hidden because
a tag missed is a test the reader cannot discover was there.

The rule is enforced rather than reviewed for. A clause identical to its
topic's is rejected: it changes no answer, and it would let a script write what
looks like consideration. `always` on a unit is rejected, because whether a
subject applies regardless of surface is decided once. And once every test in a
topic carries a clause, a tag the topic declares and none of them do is
rejected -- the subject would be claiming a surface each of its own tests has
just said it does not have.

A test may name a tag its subject does not, and that is the case the mapping
exists for rather than an exception to it. `PTN-CRY-02` is about assets in
transit and carries no `export-report`; the test in it about a bulk export
does. Reaching that needed the index to be built from the tests upward rather
than from the topics down -- asked from the topic's clause alone, the mapping
would have been written, validated, and unreachable, which is the failure this
release is about repeated one level up.

It also made three labels false, and the labels were the last thing to catch up
with the mechanism rather than the first. A heading read "N topics declare a
tag you chose" over topics that declare nothing of the sort; a card said "the
context is" about a surface only one of the topic's tests claims; and the
selector's per-tag count became a union in this same change while the sentence
beside it went on calling it a count of declarations, which three tags now
contradict on the page. Six topic-and-tag pairs are reached this way today. The
heading says what it means, the card says which route reached it, and a test
sweeps every tag rather than the one that showed the fault.

19 tests across 5 topics carry a clause. The rest of the catalogue is still
answered for by its topics, and what makes mapping a topic a few tests at a
time safe is that a clause is written only where it differs: the tests without
one keep inheriting, so nothing is lost half way through.

0.30.0 puts the procedure above the orientation on a unit page, which reverses
what stood there. The reason it stood the other way was real and is written in
the code it replaces: a reader who cannot say where a controlled input comes to
rest has nothing to point the sequence at. That is true of a first read, and it
is not the read this page mostly gets.

Measured across the 76 written units at 900px before the change: the oracle sat
below the fold on 39 of the 47 that have one, the sequence on 54 of 72, the
first false positive on 74 of 76, and `done when` on all 76. A tester who came
back mid-test to check what counts as a positive found the assumptions instead,
every time. After: 0 of 47 and 0 of 72, with the first false positive under on
16. The measurement is the test, so a block quietly added above them fails
rather than being noticed later.

Orientation is one screen down rather than folded away. A first reader is
reading the whole unit and a returning one is not, and neither is served by
material that has to be opened before it can be read. Both groups now carry a
heading that says which they are.

Focus follows the route. Replacing the document and scrolling to the top left
focus wherever the last click put it -- on a link that no longer exists, which
browsers reset to the body -- so a reader on a keyboard tabbed through the whole
header to reach what they had just opened, on every navigation. The
destination's own heading takes it instead, which is what a page load would have
done. It is focusable and not tabbable: a stop in the tab order that is not a
control is its own defect.

Ctrl/Cmd+K reaches the search box. One shortcut, and modified rather than bare,
because a bare key fires while the reader is typing into the box it focuses.

0.31.0 lets the vocabulary be written ahead of the tests. A fact no unit named
was rejected -- an unreachable fact is vocabulary nobody can use -- and that one
sentence refused two different things: a fact nobody noticed, and the only
honest way to say where the catalogue is going. A concept therefore existed
exactly when a test happened to reach it, which makes the vocabulary a
description of today's coverage rather than of the domain.

An `uncovered` register replaces the refusal, with the same two-sided ratchet
the `unconsumed` register carries: a fact nothing names and nothing registers
is still rejected, so a gap cannot arrive silently, and an entry for a fact
something has since started naming is rejected too, so the register shrinks by
a test arriving rather than by an entry being forgotten. What did not move is
the producer gate. A fact a unit *requires* that nothing establishes stays a
broken chain, because from outside it reads exactly like a route nobody has
taken yet -- and that confusion is the one this file exists to prevent.

The first entry is `impact.persistence.retained`, an outcome: access that
outlives the remediation. The catalogue's tests around registration, recovery
binding and second-factor enrolment establish that a control is absent or
defeated and stop there -- two of them are in the `unconsumed` register for
exactly that reason. What those defeats leave behind is a way back in that the
fix does not close, and that is an outcome an engagement reports rather than a
control it records. Naming it says where the work goes; registering it says the
work is not done.

Every surface carries the distinction rather than leaving it to be inferred.
The capability's own page says no test in this catalogue establishes it and
prints the reason it was written anyway; the chain map gives it a fifth shade,
read against `unused` rather than against `impact`, because "nothing goes on
from here" and "nothing arrives here yet" are different facts about the chart;
the status page counts it beside the dead ends rather than inside them; and
`pentest-navgrid chain --fact` says the same thing, because the two states have
the same three empty lists and the sentence written for the second one --
*a chain reaching it stops here* -- asserts a chain reaches it. Every one of
those reads the register rather than inferring from what is empty, which is the
only thing that tells the two apart. The published totals are labelled the same
way, so a denominator that now includes a concept no test reaches cannot be read
as coverage.

0.32.0 separates running a test from inspecting the model, which was the
alternative to renaming the navigation and is why the navigation is unchanged.

`#/chains` carried three things: the surface selector, the outcomes a chain is
meant to end at, and a picture of every capability in the file shaded by how
much of the catalogue is written. The third is not a chain, and the comment
that put it there said so without acting on it. The first two are the two ways
into a route -- what is in front of you, and what you are heading for -- and
they stay. The picture moves to `#/status`, whose subject already was what this
file does and does not contain, and which already carried the family matrix
ordered the same way.

The objection to moving it was written down as a test: burying the honesty
behind a friendlier view is the one way this could make the product worse. It
is answered rather than dropped. The page it moved to now reports strictly more
than the map did -- both gap registers, each cause with the reason it is open,
in the words the repository records -- none of it is folded away, and the
chains page links straight to it. The test asserts those properties instead of
the location that used to stand for them.

Publishing the registers is the substance of the release. A count of where the
model stops is a figure a reader cannot interrogate: 20 capabilities nothing
uses reads as 20 things left undone, and 11 of them are dead ends for good --
absent misuse detection removes a cost rather than granting a capability, and
writing a consumer for it would draw an edge the evidence does not support.
That distinction has been written down per cause since the register existed,
and it was the one part of the model that never left the repository.

What the page says about its own coverage is narrower than the first draft of
it. The `unconsumed` gate ratchets chain-tier facts, because the tier is what
says an edge through a capability is an escalation -- so 8 of the 20 dead ends
are topic-tier and outside it. Printing the figure of 20 above a section that
explained 12 and claimed to explain every gap was the same uninterrogable
number one level up. The remainder is now derived on the page and carries the
smaller claim its tier already makes: a topic-tier fact is consumed inside the
topic that produces it, so one nothing consumes is a technique whose result no
sibling declares rather than a chain that stopped. That it is not ratcheted is
stated where it is listed, and the suite asserts the two groups partition the
published figure exactly.

0.33.0 is content rather than machinery, and it is the first of it since the
retrieval work started. `PTN-AUT-01`, credential strength policy, goes from four
outlines to four authored units -- the first executable tests in `AUT`, a domain
holding 42 units of which none could be performed.

The topic was chosen for what its `safety` fields have to say. Three of its four
units *set* a credential on a running application and the fourth *guesses* one,
so the real costs are locking a person out of their account, changing a real
user's access, and turning a policy question into a credential-spraying sweep.
`sketched` has no `safety` field, which would have left exactly the part that
makes this topic dangerous unwritten -- so the tier was never in question.

The mechanism worth having in writing is in `-SIZE`: bcrypt hashes the first 72
bytes and discards the rest, so a long passphrase is exactly as strong as its
first 72 bytes and nothing tells the user. The oracle is a sign-in with a strict
prefix, because a maximum stated on the page is a claim and a truncated secret
is a measurement.

`-IMPACT` is ordered so the arithmetic comes before the attempt: the attempt
budget is measured on the tester's own account, the permitted space is stated
from what the policy units found, and where the space is larger than the budget
the answer is already negative and no account is touched. A test that spends a
real person's access to learn something the two numbers already say is not a
test worth running.

`-IMPACT` declares no motivation, and the first draft did. `control.limit.absent`
looked like the right one -- knowing a limit is unenforced is what makes guessing
worth reaching for -- until the edge count moved by twelve and naming the twelve
showed what they were: a per-object upload size limit and an accumulated storage
quota among them. The fact is true of every unenforced limit in the catalogue,
which makes it too coarse to carry this motivation, and the unit measures the
attempt budget itself in its first step rather than inheriting a claim about
upload quotas. A fact narrow enough to say *authentication attempts are not
throttled* would earn the edge; writing one belongs to `PTN-AUT-03`, which would
have to produce it.

One payload file, `payloads/credential/policy-probes.yaml`, and it is probes
rather than guesses: values the tester sets on their own account to find the
boundary. There is deliberately no list of candidate passwords anywhere in this
repository, and `-IMPACT` -- the only unit that guesses -- is the one with no
payload file at all.

What this does not do is finish a chain. The topic is authored end to end within
itself and stops at `access.principal.other`; the unit that consumes that is
`PTN-AUT-02-IMPACT`, still an outline. Three chains reach a stated outcome, not
four.

`PTN-AUT-02`, default and seeded credentials, follows it in the same batch and
takes that step: its impact unit is the only consumer of
`access.principal.other`, so writing it is what continues the chain rather than
starting another one beside it.

It needed one fact. `PTN-AUT-02-MAP` is a recon unit that established nothing,
which meant the topic declared a `phase` axis -- map, then probe, then impact --
that existed in the file and not in the graph: nothing connected the inventory
to the unit that uses it. `recon.vendoraccounts.mapped` is that connection, at
topic tier because it is consumed inside the topic that produces it and nowhere
else.

The safety fields carry most of the judgement again. `-PROBE` is one attempt per
documented pair, stopping at the first acceptance, because the alternative is
credential spraying with a different name -- and where the component
authenticates against the application's own store, a failed attempt spends a
real user's lockout budget rather than a service account's, which is a thing to
establish before attempting rather than after. `-IMPACT` reads rather than
writes: a management interface is where the destructive functions are, and the
account was left in place precisely because somebody believed it was harmless.

`PTN-AUT-03`, anti-automation and lockout, is the third in the batch and the one
`PTN-AUT-01` was waiting on: its rate unit is where the attempt budget that the
credential-policy impact reasons about is actually measured. Nothing in the
graph moved -- its four units already carried their chain fields -- so this is
depth and nothing else.

Its impact unit denies a real person their access on purpose, and it is the one
in this catalogue that most needs the word no: one account the client named in
writing, once, and only when the route to clear the lockout is already known,
because applying a denial without knowing how to lift it is an outage rather
than a test. Where the client will not designate an account, the mechanism is
already established by the scope unit and the finding is recorded as
demonstrated in principle and not performed -- a materially different sentence,
and the honest one.

`PTN-AUT-04`, authentication bypass, is the fourth, and it made a pattern
visible that is worth recording once rather than per topic. Its `-MAP` unit
established nothing, exactly as `PTN-AUT-02`'s did -- and so do 32 of the
catalogue's recon units, across 11 domains. They are most of what the published
figure counts as *tests declaring no capability*. A recon unit that yields
nothing is not merely undeclared: it means the topic's own axis, the phase
sequence its `order` sets out, exists in the file and not in the graph, so
nothing connects the inventory to the units that use it. Authoring one forces
the fact that closes that, which is why writing depth keeps adding capabilities
rather than only filling fields.

Two more of them here: `recon.authstates.mapped` at topic tier, and the same
judgement as before -- the units that use it declare it a motivation rather than
a prerequisite, because a bypass attempt is worth offering slightly early and
never worth hiding from a reader who has not drawn the state map yet.

`PTN-AUT-05`, persistent authentication, is the fifth, and nothing in the graph
moved for it either -- depth only. What its four units share is a single
discipline that the topic makes unavoidable: every one of them is about a secret
that authenticates without a credential, so every one of them is written to be
performed on the tester's own account and on no other. Composing a token for a
real user, changing a real user's credential to see what survives it, shortening
a wait by altering somebody else's value: each is the attack the unit above it
is trying to predict, and each answers a question an owned account answers
identically.

The recurring false positive across the topic is the browser being measured
instead of the server. A cookie the browser drops at sign-out, an expiry the
browser enforces, a value the browser forgets -- all three read as the
application revoking something. Every offer in these units is made from a client
that was never told to forget the secret, which is what turns three tests of
obedience into three tests of a server-side record.

Every topic now carries units, which was phase 3's job. The number to watch from
here is charted units — those carrying `requires` and `yields` — which is phase
5's, and the one every local chain in the artefact is derived from.

### Phase 5 batches

`requires` and `yields` for every unit. Recon goes first because it produces the
facts every other domain consumes: charting anything else first would mean
declaring requirements against facts nothing yet establishes.

| Batch | Domains | Units | Status |
|---|---|---|---|
| 1 | `RCN` | 17 | `done` |

| 2 | `INJ` `RES` | 80 | `done` |
| 3 | `CLT` `PRT` | 80 | `done` |
| 4 | `SES` `CRY` | 64 | `done` |
| 5 | `AUT` `IDN` `ACL` | 67 | `done` |
| 6 | `BIZ` `ERR` `CFG` | 58 | `done` |

The pass ended with a gate rather than a count: every fact that is not `given`
has at least one unit producing it, and the validator enforces it from here on.
187 facts, 393 units, and no condition in the graph without a route to it.

The gate is one-directional, and the asymmetry is worth stating plainly. Every
capability has a producer; many have no *consumer*. 78 of 177 are declared as a
use by nothing at all -- impacts excluded, because those are terminal by
construction and counting them here would describe arriving as failing to
arrive. So the chain runs from reconnaissance to a primitive and then stops.
That is the shape of what phase 5 set out to do -- place every unit in the graph
-- and not the shape of a complete attack model. Charting the far half is listed
under **Considered, not scheduled** rather than left to be noticed one dead end
at a time.

### Phase 3 batches

| Batch | Domains | Topics | Units | Status |
|---|---|---|---|---|
| 1 | `INJ` `RES` | 15 | 80 | `done` |
| 2 | `CLT` `PRT` | 17 | 80 | `done` |
| 3 | `SES` `CRY` | 16 | 64 | `done` |
| 4a | `AUT` `IDN` | 14 | 46 | `done` |
| 4b | `ACL` | 7 | 21 | `done` |
| 5 | `BIZ` `ERR` | 13 | 36 | `done` |
| 6 | `RCN` `CFG` | 17 | 39 | `done` |

Batch 1 went first because SQL injection already carries payloads and a card, so
the unit model could be judged against real depth material before three hundred
more units were written on top of it.

### Topics per domain

| | | | | | | |
|---|---|---|---|---|---|---|
| `INJ` 12 | `CLT` 12 | `SES` 11 | `AUT` 10 | `BIZ` 9 | `CFG` 9 | `ACL` 7 |
| `RCN` 8 | `OUT` 7 | `PRT` 5 | `CRY` 5 | `ERR` 4 | `IDN` 4 | `RES` 3 |
| `SUP` 0 | | | | | | |

`OUT` is where a confirmed capability arrives. Its topics claim no WSTG test
case, because the standard enumerates what to test rather than what a result is
worth, and they appear under Pentest NavGrid Extensions for that reason.

`SUP` carries no topics because no WSTG test covers vulnerable components or
supply chain, and phase 2's input is the WSTG map. It is phase 7's first entry,
and its emptiness is part of why the scope is wider than the standard.

These figures are asserted by the test suite, not maintained by hand. A stale
coverage number is worse than none, because it is the number this project asks
to be judged on.

## What already exists

Phases 0 to 2 leave the repository with the vocabularies settled, the machine
checks in place, and the taxonomy's top level written, so the phases that follow begin
against real material rather than an empty tree:

| Asset | State |
|---|---|
| `standards/wstg.yaml` | 109 identifiers, pinned by commit and SHA-256, every entry verified. |
| `standards/wstg-map.yaml` | All 109 resolved to a domain by the ordered procedure, with the deciding rule and a note on each contested one. |
| `payloads/sqli/` | 105 SQL injection payloads across 10 files, covering probe, fingerprint, seven techniques and evasion. |
| `payloads/traversal/` | 4 files: survival probes, encodings and what each distinguishes, read targets with fingerprints, and the read-versus-interpret pair. |
| `payloads/xss/` | 48 payloads across 10 files, one per context plus the probe and the evasion set, each executable entry run in a browser rather than recalled. |
| `toolbox/registry.yaml` | 8 tools with per-flag rationale. |
| `cards/sqli/union-extraction.md` | One card in the recall-first layout, as the worked example of the format. |
| `cards/traversal/path-resolution.md` | The second card, shared by all five units of `PTN-RES-01`. |
| `cards/outcome/proportionate-demonstration.md` | The third card, shared by the three terminal outcome units: how much is enough to answer what a capability was worth. |
| `cards/sqli/injection-points.md` | Shared by the five `PTN-INJ-01` units that reason about where a value lands in the statement rather than what to do once it is there. |
| `cards/sqli/inference.md` | Shared by the four `PTN-INJ-01` channels that read a database, and the basis for choosing between the two shapes they divide into. |
| `mitigations/path-resolution.md` | The first mitigation, written because a unit referenced it. |
| `cards/access-control/object-ownership.md` | Shared by all five `PTN-ACL-02` units: the two-account method, the empty-record trap, and the ceiling that keeps enumeration a sample. |
| `payloads/access-control/identifiers.yaml` | Identifier shapes and adjacency -- transformations of an identifier the engagement holds, never a guess into real records. |
| `mitigations/parameterised-query.md` | CWE-89, for `PTN-INJ-01`: binding rather than escaping, what cannot be bound, and what least privilege changes about each capability the topic charts. |
| `cards/xss/contexts.md` | Shared by the probe and all eight `PTN-CLT-01` context units: the context table, and why an encoder written for one context leaves another live. |
| `cards/xss/evasion.md` | The four mechanisms that produce one clean result, and the single observation that separates each. |
| `mitigations/output-encoding.md` | CWE-79 and CWE-80, for `PTN-CLT-01`: encode at output for the context, and why a content policy is a second layer rather than the fix. |
| `mitigations/object-authorization.md` | CWE-639 and CWE-566, for `PTN-ACL-02`: authorize the object rather than the route, enforce at the data-access layer, and why an unguessable identifier is exposure surface rather than a control. |
| `standards/asvs.yaml` | ASVS 5.0.0: 17 chapters, 80 sections, 345 requirement identifiers. Identifiers and structural names only — the text is CC BY-SA. |
| `standards/cwe.yaml` | CWE 4.20: 969 weaknesses, 422 categories, 59 views, with abstraction and status. |
| `knowledge/` | 106 topics across 14 domains, and 393 units across all fourteen domains. |
| `vocab/surfaces.yaml` | 52 attack-surface tags, describing where a topic applies. |
| `vocab/facts.yaml` | 185 capabilities in seven families — the join keys the chain is derived from. |
| `pentest_navgrid/` | Nine schemas, seven validation passes, the derived chain, and the builder plus the artefact's own template, stylesheet and script. See [`VALIDATION.md`](VALIDATION.md). |
| `tests/` | An offline suite, almost all of it negative — asserting what must be rejected. Two further runners, `node` and a browser, are used when present and skipped when not. |

The payload files and the tool registry are volatile content and carry a
`reviewed` date that predates phase 0. Treat them as unreviewed until a depth pass
re-verifies them against current engine and tool behaviour.

## Considered, not scheduled

Recorded so they are decisions rather than omissions. None is being built.

| Item | Note |
|---|---|
| **Chart what a defeated control permits** | Done in 0.23.0 and 0.24.0, and what is left is not the same work. 20 of 187 capabilities are established by a test and used by none, 11 of 59 of them `control.*`, and `primitive.*` is at 1 of 33. The shape that closed it was written 15 times: a test that requires the defeated control and establishes what it permits. Of the 12 remaining, 11 permit nothing on their own and are dead ends for good and 1 is the blind oracle, which carries a value rather than being one — recorded under two causes so the register stops reading as a to-do list. 26 of 393 tests now end at the capability they established, down from 81. |
| **`PTN-CLT-02` — DOM cross-site scripting** | The sibling of the chain 0.18.0 wrote, and the natural next one. A second instance of a shape already proven, which is why it waited. |
| **`PTN-RES-03` — server-side request forgery** | A fourth chain shape: `primitive.fetch.internal` to `impact.network.reached`, through `PTN-OUT-03`. The first candidate once the three phase-1 chains have been used in anger. |
| A second execution standard | The navigation is standard-first and the artefact's structure allows one. Nothing is added until there is a standard whose decomposition Pentest NavGrid improves as much as it improves WSTG's. |
| OWASP Top 10 as a risk lens | A classification of risk, not an execution methodology. If it arrives it is a lens over the existing catalogue and never a second way to navigate to a test. |
| ASVS as a remediation lens | The mapping already exists in `refs.asvs`; a view that reads a finding's controls from it does not. |
| Better graph exploration | Saved focus, comparison of two routes, filtering a path by domain. The current general graph is deliberately the smallest thing that is honest. |
| More units at full depth | Thirty-six of 393, with 40 sketched. Governed by the standing rule above: written when an engagement makes one worth writing. |
| Optional external integrations | Export to a report template, or a checklist import. Anything of the kind must not become a route by which target data enters the artefact. |

## Governance and distribution

Inbound contribution terms are in [`CONTRIBUTING.md`](../CONTRIBUTING.md), and
were written before the project accepted its first outside contribution rather
than after: a licence decision that has to be renegotiated with past
contributors is one that cannot be made.

Three settled questions -- the repository stays public, a hosted site is a later
second build target, and any commercial layer lives outside this repository --
are recorded with their reasoning in
[`DISTRIBUTION.md`](DISTRIBUTION.md). They are decisions rather than omissions,
and the record says what would have to change for each to be revisited.

## Releasing

`release.yml` attaches the built artefact to a release published from the GitHub
UI. It runs the same checks a pull request runs -- by calling `validate.yml`,
not by restating them -- refuses to continue if the tag and `__version__`
disagree, and publishes the SHA-256 beside the file after rebuilding from
scratch to prove the digest is reproducible.

The trigger is `release: published` rather than a tag push, so the workflow can
only ever add a file to a publication a person made; it has no path by which it
publishes anything of its own. `workflow_dispatch` exercises the whole thing and
publishes nothing.

Building and publishing are separate jobs on purpose. The build installs
dependencies and runs this repository's code, so it holds `contents: read` and
checks out without persisting a credential; the job that can write runs neither,
and is guarded on the job rather than the step so a dispatch never creates a
runner holding a write credential at all.
