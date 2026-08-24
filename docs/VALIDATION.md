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

## Six passes

Every pass collects problems rather than stopping at the first. A contributor
fixing a batch wants the whole list, and a first-failure validator quietly
trains people to fix one thing and re-run — which is how the second and third
problems in a file go unnoticed. Every message names the file that caused it.

**1 — Schema conformance.** Seven schemas under `harrier/schema/`, selected by
where the file sits. A document in the wrong directory is itself a finding.

**2 — Vocabularies.** Duplicate domain codes, duplicate axis names, surface tags
that emit something unknown or emit themselves, duplicate dimension values, and
the absence of a universal axis — without one, recurring steps such as `PROBE`
have nowhere to live and every topic invents its own name for them.

**3 — Standards.** The pinned index and the domain map must agree in both
directions: every pinned identifier mapped, every mapped identifier pinned, no
duplicates, no undefined domains, and no title that has drifted from the pin. An
identifier marked unverified is reported rather than trusted.

**4 — Knowledge.** The pass everything else exists to make possible:

- a unit's slug must come from its topic's declared axis, or from the universal
  one. **This is what makes non-overlap mechanical** — a unit may not invent a
  name, so two topics cannot name one idea differently.
- identifiers are well formed, unique, match their file name, and sit in the
  directory their domain names
- `refs.wstg` resolves against the pin. `refs.asvs` is rejected outright until an
  ASVS release is pinned: a citation nobody can check reads as evidence while
  being none
- surface tags, dimension names and dimension values resolve
- `objective` is falsifiable and `done_when` is countable — both are pattern
  checks against the language that makes them neither
- an oracle reading `n/a` is rejected; a rule with a socially acceptable escape
  hatch stops being a rule
- a unit still marked `outline` while carrying everything an authored unit needs
  is rejected, because a stale status makes the coverage figures lie
- every unit is reached by its topic's `order`, when one is declared

**5 — Payloads.** Both directions of the variable rule: an undeclared placeholder
leaves an entry nobody can fill in, and a declared-but-unused one is what a
renamed placeholder leaves behind. Dimension selectors resolve against
`vocab/dimensions.yaml`, so a mistyped engine name fails loudly instead of
quietly narrowing an entry to nothing.

**6 — Toolbox.** Unique ids, and every explained flag actually appears in its
command. Only keys that look like flags are checked — interactive tools explain
a technique rather than a command-line token, and forcing those into a command
would push the rationale out of the one place it is written.

## What the suite adds

72 tests, offline, no network and no fixtures of their own: every mutation test
copies the real repository and breaks exactly one thing in it. A hand-built
miniature drifts from what it stands in for, and then the suite passes while the
repository is broken.

Almost every test is a **negative** one — it asserts that something is rejected.
A suite that only checks good cases cannot tell a working rule from one that has
quietly stopped firing, and a rule that has stopped firing looks exactly like a
repository with no problems.

Three properties are asserted about the repository rather than the code:

- the roadmap's coverage figures match what the validator counts, so the number
  this project asks to be judged on cannot go stale
- no code path loads YAML without `safe_load` — the catalogue is
  contributor-submitted, and full loading would make it a code-execution channel
  into every contributor's machine and into CI
- no payload carries a destructive operation, and no payload or command template
  carries a literal host where a placeholder belongs
