# Distribution — what is public, what ships, and what lives elsewhere

A decision record. It exists for the same reason [`PIVOT.md`](PIVOT.md) does:
each of these questions has a plausible answer in both directions, and a project
that has not written down which one it took will re-argue it every time somebody
new looks at it.

Three decisions, and the reasoning behind each.

---

## 1. The repository stays public

Apache-2.0, publicly readable, and not changing to a non-commercial or
source-available licence.

**Repository visibility protects nothing here.** The catalogue is not held back
from the published artefact -- it *is* the published artefact. `build.py` embeds
the whole of it as plain JSON inside `template.html`, because a self-contained
offline file cannot fetch what it needs later. Anyone holding `pentest-navgrid.html`
holds every topic, every Test Unit, every capability and every edge, in a form
that is one `JSON.parse` from a working copy. Closing the repository would
withhold the build tooling and the test suite from readers while withholding the
content from nobody.

**And the security claims require the opposite.** What this project asserts about
the artefact is checkable rather than promised: it makes no outbound request of
any kind, its `Content-Security-Policy` is hash-based and denies everything
including `connect-src`, and no prose from WSTG or ASVS is reproduced anywhere.
A reader on an engagement network is being asked to open a file from disk on the
strength of those three claims. They are verifiable only against a repository
that can be read, a suite that can be run, and a build that can be reproduced
from source. A closed repository turns all three into assurances, which is a
different and much weaker thing.

The commercial reasoning points the same way rather than against it: the value
that is hard to copy is the decomposition being *maintained and correct*, not the
bytes being scarce.

## 2. A hosted site is a later second build target

Planned, not built. When it arrives it is a second target beside the offline
single-file artefact, generated from the same catalogue by the same build --
never a fork of the content, and never the primary one.

The offline artefact is the product's argument: a file a tester opens from disk
on a network where a request to a third party would tell that party which target
is being tested and when. A hosted copy answers a different question -- being
findable by somebody who has not heard of the project -- and must not be allowed
to erode the first. Concretely: the offline build keeps its guarantees whatever
the hosted one does, and anything the hosted build needs that would weaken them
belongs to the hosted build alone.

## 3. Any commercial layer lives outside this repository

Accounts, engagement state, telemetry and analytics are not added to the
artefact. Not as an option, not behind a flag.

This is the same boundary [`PIVOT.md`](PIVOT.md) drew and for the same reason.
Version 0.3.0 held target state in the browser and was removed because the
artefact's entire security argument is that it holds none. A commercial feature
that reintroduced any of it would not be an addition to this product; it would
be the rejected product wearing a price. Whatever is built commercially consumes
this catalogue from outside and leaves the file's guarantees intact.

[`CONTRIBUTING.md`](../CONTRIBUTING.md) is what keeps that option open: it takes
a licence broad enough for the Owner to license contributions under other terms,
so the decision can be made later rather than being foreclosed by the first
outside contribution.

---

## What would change these

Written down so a reversal is a decision rather than a drift.

**Decision 1** would need the catalogue to stop shipping inside the artefact --
a hosted-only build, or one that fetches content. Both contradict the offline
guarantee, so in practice this decision holds as long as the product does.

**Decision 2** would need the hosted build to become the primary target, which
would mean the offline file was no longer what people use. That is a product
change, not a distribution one, and belongs in a record of its own.

**Decision 3** would need the artefact to hold target state, which
[`PIVOT.md`](PIVOT.md) already settled.
