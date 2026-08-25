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

## Seven passes

Every pass collects problems rather than stopping at the first. A contributor
fixing a batch wants the whole list, and a first-failure validator quietly
trains people to fix one thing and re-run — which is how the second and third
problems in a file go unnoticed. Every message names the file that caused it.

**1 — Schema conformance.** Nine schemas under `harrier/schema/`, selected by
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
  hatch stops being a rule
- a unit still marked `outline` while carrying everything an authored unit needs
  is rejected, because a stale status makes the coverage figures lie
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

## What the suite adds

125 tests, offline, no network and no fixtures of their own: every mutation test
copies the real repository and breaks exactly one thing in it. A hand-built
miniature drifts from what it stands in for, and then the suite passes while the
repository is broken.

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

Three properties are asserted about the repository rather than the code:

- the roadmap's coverage figures match what the validator counts, so the number
  this project asks to be judged on cannot go stale
- no code path loads YAML without `safe_load` — the catalogue is
  contributor-submitted, and full loading would make it a code-execution channel
  into every contributor's machine and into CI
- no payload carries a destructive operation, and no payload or command template
  carries a literal host where a placeholder belongs
