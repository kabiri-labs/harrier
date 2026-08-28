# Validation

What the validator checks, and why each rule is mechanical rather than a review
comment. The short answer to "why mechanical" is the same every time: these
defects read perfectly well in a diff.

```bash
pip install PyYAML jsonschema

python -m unittest discover -s tests -t .   # the suite
python -m harrier validate                  # the repository
python -m harrier coverage                  # the counts the roadmap publishes
```

CI runs exactly those first two commands, in that order, with nothing extra.

Exit status is the contract: `0` valid, `1` rejected, `2` bad invocation.

## Eight passes

Every pass collects problems rather than stopping at the first. A contributor
fixing a batch wants the whole list, and a first-failure validator quietly
trains people to fix one thing and re-run — which is how the second and third
problems in a file go unnoticed. Every message names the file that caused it.

**1 — Schema conformance.** Ten schemas under `harrier/schema/`, selected by
where the file sits. A document in the wrong directory is itself a finding.

**2 — Vocabularies.** Duplicate domain codes, duplicate axis names, surface tags
that emit something unknown or emit themselves, duplicate dimension values, and
the absence of a universal axis — without one, recurring steps such as `PROBE`
have nowhere to live and every topic invents its own name for them.

**3 — Standards.** The pinned WSTG index and the domain map must agree in both
directions: every pinned identifier mapped, every mapped identifier pinned, no
duplicates, no undefined domains, and no title that has drifted from the pin. An
identifier marked unverified is reported rather than trusted.

A file under `standards/` with no schema registered for it is reported rather
than loaded and trusted — adding a standard has to include deciding how it is
checked.

**4 — Knowledge.** The pass everything else exists to make possible:

- a unit's slug must come from its topic's declared axis, or from the universal
  one. **This is what makes non-overlap mechanical** — a unit may not invent a
  name, so two topics cannot name one idea differently.
- identifiers are well formed, unique, match their file name, and sit in the
  directory their domain names
- `refs.wstg`, `refs.asvs` and `refs.cwe` all resolve against their pinned files.
  An ASVS chapter or section may be cited as well as a single requirement —
  citing a whole section is often the more honest reference. A CWE reference must
  name a weakness: a category or a view is rejected *by name*, because both are
  real identifiers and "not found" would be misleading about them. A deprecated
  weakness is rejected in favour of its replacement
- surface tags, dimension names and dimension values resolve
- `objective` is falsifiable and `done_when` is countable — both are pattern
  checks against the language that makes them neither
- an oracle reading `n/a` is rejected; a rule with a socially acceptable escape
  hatch stops being a rule. The same applies to a `triage` or `hypotheses` entry
- a `triage` entry written as an instruction to look around rather than a place
  to start is rejected. Matched at the head of the entry rather than anywhere in
  it: the field carries the literal token a tester will type, and a target can
  have a parameter named `review` or an endpoint at `/explore`. `hypotheses` is
  deliberately exempt from that gate: it states a claim about the target rather
  than an instruction, and the verb list would reject the plainest true thing
  the field has to say
- `sink` on a `recon` or `inquiry` unit is rejected by the schema, for the
  reason `oracle` is: a unit that sends nothing to be interpreted has no sink,
  and an optional field with nothing to say gets filled with "not applicable"
- a unit still marked with a depth tier below the one it has grown into is
  rejected: the check raises the document's own status by one tier and asks the
  schema whether it would still validate, so the two definitions of a tier
  cannot drift apart. A stale status makes the depth figures lie
- every unit is reached by its topic's `order`, when one is declared
- every `see_also` is returned by the topic it names. A one-way link is a
  boundary written in the wrong field
- every `(identifier, domain)` pair the ordered procedure resolved is claimed by
  a topic **in that domain**. Checking the identifier alone would let a topic in
  one domain mask the absence of the other, which reports full coverage over a
  hole. An identifier resolved to no domain is exempt from being covered — and
  claiming one is rejected, because that would count coverage the taxonomy does
  not have

**5 — Payloads.** Both directions of the variable rule: an undeclared placeholder
leaves an entry nobody can fill in, and a declared-but-unused one is what a
renamed placeholder leaves behind. Dimension selectors resolve against
`vocab/dimensions.yaml`, so a mistyped engine name fails loudly instead of
quietly narrowing an entry to nothing.

**6 — Toolbox.** Unique ids, and every explained flag actually appears in its
command. Only keys that look like flags are checked — interactive tools explain
a technique rather than a command-line token, and forcing those into a command
would push the rationale out of the one place it is written.

**7 — Chain.** The graph is derived rather than stored, so a wrong declaration
produces a route that silently does not exist rather than an error. Every fact a
unit names must be in `vocab/facts.yaml`; no unit may require what it yields; an
`impact.*` fact may never be required, because an impact is where a chain ends;
`closes` may not name a fact `yields` does not, since a negative result can only
rule out what a positive one would have established, nor a fact another unit
also establishes, since a clean result rules out the route and not the fact; an authored test or recon
unit must yield something, or it can be reached from nowhere and leads nowhere;
a fact no unit references at all is rejected, because vocabulary must not outrun
use; and two entries for one fact id are rejected, since a graph node whose
meaning is uncertain is worse than one that is missing. See [`CHAINING.md`](CHAINING.md).

**8 — The generated index resolves.** `standards/wstg-index.yaml` is derived and
committed, and a derived file nobody resolves is a second copy of the catalogue
free to disagree with the first while passing every other check. A topic or unit
identifier that does not exist is rejected, so is a case the pinned standard does
not carry, so is a pinned case with no row at all — a row that vanished with its
coverage would leave the file shorter and still looking complete — and so are
depth counts that disagree with the units beside them. The schema constrains the
*shape* of an identifier, which a renamed topic satisfies perfectly on its way to
pointing at nothing.

Staleness is a separate question and has its own answer: `harrier index --check`
compares the committed bytes against a fresh derivation, and the suite asserts
the same thing.

## What the suite adds

Offline, no network and no fixtures of its own: every mutation test copies the
real repository and breaks exactly one thing in it. A hand-built miniature
drifts from what it stands in for, and then the suite passes while the
repository is broken.

The count is deliberately not written down here. A number maintained by hand in
three documents is a number that is wrong in at least one of them; run the suite
if you want it.

Almost every test is a **negative** one — it asserts that something is rejected.
A suite that only checks good cases cannot tell a working rule from one that has
quietly stopped firing, and a rule that has stopped firing looks exactly like a
repository with no problems.

Each pin carries assertions of its own, and they differ because the licences do:

- **ASVS** is CC BY-SA, so no requirement text appears in the pin. Reproducing it
  would force share-alike onto this repository; the schema has no field for it,
  and a test checks that none arrived anyway.
- **CWE** is not share-alike, but MITRE's grant is *conditional* on reproducing
  its copyright designation and the licence. Both are required fields, the
  copyright must name MITRE, and a test asserts `NOTICE` still carries the
  designation the pin records.
- **Both**, plus WSTG, must pin something immutable. A branch (`v5.0.0`) and a
  moving alias (`cwec_latest`) are rejected by pattern, because each names a
  moving target rather than the evidence — and each currently serves the same
  bytes as the thing it should have been, which is exactly when the mistake looks
  harmless.

Two runners are used when present and skipped when not, so the suite still runs
on a machine that has installed neither:

- **node** executes the artefact's own script. The graph model, the layout, the
  path walk, the search index and the Markdown renderer are called against the
  real catalogue rather than matched as substrings of a rendered page — which a
  script with an unterminated string literal satisfies exactly as well as a
  working one.
- **a browser**, driven through Playwright, opens the built file over `file://`
  and *uses* it: navigates, types in the search box, clicks a node in the graph,
  presses Enter on one, expands a bounded graph. A static DOM dump cannot reach
  any of that, and a single-page application is where it breaks. The same run
  records every request the page attempts and every console error, so the two
  guarantees -- no network, no blocked resource -- are checked as behaviour
  rather than as text. Under a hash-based policy a script whose hash no longer
  matches simply never runs, and nothing would render at all.

Both are installed in CI. Optional locally and absent in CI is a suite that
reports green while never having run a third of itself, so the workflow installs
them and then fails the job if either is missing.

Three properties are asserted about the workflows, because a workflow is the one
place here that runs somebody else's code with a token in the environment:

- every action is GitHub's own or one of this project's -- no third-party action
  enters the supply chain of a project whose own supply chain is part of its
  threat model, and `gh` is already on the runner
- no workflow starts from more than `contents: read`, every job declares its own
  rather than inheriting one, and the only job that may write is the one that
  attaches a file to a release
- that job runs none of this project's code: no checkout, no dependency install,
  no Python. The building job holds `contents: read` and checks out without
  persisting a credential, because a job that installs dependencies while
  holding a write token is a job a compromised dependency can push from
- the release path cannot create a tag or a release, and the job that touches
  one is guarded on the job rather than the step, so a dispatch never creates a
  runner holding a write credential

Three properties are asserted about the repository rather than the code:

- the roadmap's coverage figures match what the validator counts, so the number
  this project asks to be judged on cannot go stale
- no code path loads YAML without `safe_load` — the catalogue is
  contributor-submitted, and full loading would make it a code-execution channel
  into every contributor's machine and into CI
- no payload carries a destructive operation, and no payload or command template
  carries a literal host where a placeholder belongs

The artefact carries three more, asserted on the built file:

- it fetches nothing — no element, no stylesheet rule, no script call, and no
  meta refresh reaches the network, and the policy denies `connect-src` outright
- it holds no engagement state: no browser storage, no target, no recorded
  result, and no wording that claims to know what is true of a reader's target
- catalogue content cannot become executable markup, on any path through the
  Markdown renderer or the JSON block
