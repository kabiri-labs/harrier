# Pivot — from engagement board to WSTG companion

A decision record. It exists because the model it replaces was plausible, and a
future change that has not read this will rebuild it.

---

## 1. What was here before

Version 0.3.0 published an artefact whose default view was a **board**. The
tester named a target, named the surface in front of them, and ticked the facts
they held. The board then sorted every unit into lanes — *Start here*, *Waiting
on something*, *Settled*, *Ruled out* — and recorded a result per unit as
Found, Clean or Unclear. The result mutated the held and ruled-out fact sets,
which re-sorted the lanes. All of it lived in `localStorage` and could be
exported to and imported from a run file.

It was a coherent design. It answered "what do I do next" with a specific
answer, which is more than a catalogue does.

## 2. Why it was rejected

**It claimed to know things it could not know.** "Available now" and "unlocked"
are statements about a real target. The artefact has never seen the target. It
knew only what the tester had ticked, and it presented that as reachability —
so a missed tick read as *this test is not possible* and a careless one read as
*this test is ready*. Both are the file asserting something about someone's
client that it has no basis for.

**The state was the least valuable thing in the file and the most expensive.**
Run persistence, run import, run validation, undo semantics, and the
asymmetry between establishing and ruling out were most of the JavaScript and
most of the test suite. None of it is what a tester opens the file for. A
tester already has somewhere to record results — a report, a checklist, a
notebook — and that place is authoritative. A second, weaker record in a
browser tab competes with it and loses.

**It buried the content.** The board's entry point was a lane, so reaching a
test meant agreeing with the board's ranking first. The two things Harrier
actually has that WSTG does not — atomic decomposition and chain continuity —
were reachable only through a stateful view that had to be configured before it
said anything.

**It put a target's name and findings in a browser.** Even stored locally and
never transmitted, that is client data in an artefact whose entire security
argument is that it holds none.

## 3. What Harrier is now

An interactive execution companion for web security testing standards. It
decomposes large standard test cases into atomic, independently understandable
Test Units, and shows what attack-chain paths may become relevant when each Test
Unit succeeds.

> WSTG tells you what to cover. Harrier shows you the real tests inside it and
> where each successful test can lead.

The initial supported execution standard is OWASP WSTG, which provides the
primary coverage and navigation structure:

```
Standard → Testing group → WSTG test case → Harrier Test Units → Test Unit detail
```

Harrier adds two things at a granularity the standard does not reach:

1. **Atomic decomposition.** A WSTG test case is often several independently
   performable tests with different payloads, oracles and outcomes. Harrier
   makes those Test Units explicit and separately addressable.
2. **Attack-chain continuity.** A successful Test Unit establishes a capability
   that can make other tests or impacts relevant. Harrier exposes those possible
   continuations so a test is not read as an isolated checklist item.

## 4. Retained

- The whole content catalogue: 99 topics, 366 units, cards, payloads,
  mitigations, toolbox, and every boundary note.
- The schemas, the pinned standards, and every validation rule.
- The fact vocabulary and the four chain fields — `requires`, `motivated_by`,
  `yields`, `closes` — plus `given` and `granted`. They describe generic
  relationships between tests and they are what the derived graph is built from.
- One self-contained offline HTML artefact that fetches nothing.
- Titles lead, identifiers follow.

## 5. Removed

- The board and every lane in it.
- Target input, surface anchors as a working context, and the `scope`/`always`
  indexes that powered them.
- Held and ruled-out fact sets, fact checkboxes, and "what you hold".
- Per-unit result recording: Found, Clean, Unclear, Undo.
- `localStorage` run state, run restore, run clear, and run export/import with
  its validation.
- Build-time reading-order ranking (`order_hint`), which existed to sort a board
  that no longer exists.
- Every phrase asserting reachability, availability or completion for a target.
- `harrier chain --held`, `Chain.available` and `Chain.reachable_with`, and the
  `unlocks` wording in the command line. The pivot is the product's, not the
  artefact's: a tool one step away that still computed what was *possible now*
  would carry the rejected model in a place nothing on the page could correct.

## 5b. Reconsidered in 0.13.0, and where the line is

The chain map lets a reader open any capability and see the tests that declare
it a prerequisite. That is close enough to `Chain.reachable_with` — removed
above — to need saying why it is not the same thing, because the next change
that has not read this will either rebuild the board or refuse a navigation
link out of caution.

What made the board dishonest was three things together: a **set** of facts the
tester ticked, **persisted**, and presented as a **claim** about a target —
"available now", "unlocked". The map has none of them. It carries one
capability at a time, stores nothing, ranks nothing, and the page it opens
states a fact about the catalogue: *these tests declare it a condition of being
possible at all*. Whether any of it applies to a target is the reader's, and the
wording says so on every screen.

The line, stated so it can be checked: a view here may answer "what does the
catalogue say follows from X". It may not accumulate several X, remember them,
order the answer by what the tool thinks matters, or describe any of it as
reachable, available or unlocked. The first is a query. The rest is the board.

## 6. Non-goals

Deliberately outside this product, not merely unbuilt: target or engagement
creation; target names, URLs, endpoints, parameters, assets, roles, tenants or
accounts; surface and principal instances; target-specific results; evidence
collection; finding management; engagement reporting; dynamic coverage of a real
target; deciding what is currently reachable on a target; claiming a chain
branch has been unlocked; persisting results; run state or run files; target-aware
scoring.

OWASP Top 10 is not added here. If it is added later it is a **risk-classification
lens**, not a second execution methodology. ASVS remains a control and
remediation mapping; CWE remains a weakness classification; WSTG is the
execution-navigation standard.

Harrier is not a scanner, an exploit framework, a reporting platform, an
engagement tracker, or an automatic decision-maker.

## 7. Consequences and trade-offs

**This is a breaking change to the artefact's user experience**, taken during
the pre-1.0 period precisely so it can be taken at all. Run files written by
0.3.0 cannot be read by 0.4.0 and no migration is offered: the data they hold is
target state, which the product no longer has a place for.

**Harrier now answers a narrower question.** It will not tell a tester what to do
next on their engagement. It tells them what a standard test case actually
contains, how to perform each piece, and where a success can lead. Deciding which
of those applies today stays with the person, which is where the knowledge is.

**Chain language becomes conditional and stays that way.** "Potential
continuation", "becomes relevant when", "still required" — never "unlocked".
The graph is a statement about tests, not about a target, and the wording has to
carry that on every screen or the old model returns by accident.

**The general graph is now a real design problem.** 366 units and 177 facts
rendered at once is an unreadable hairball, and the board's ranking used to hide
that. Progressive disclosure — families first, then drill-down, then a focused
path — replaces it.
