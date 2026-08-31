# Contributing

Contributions are welcome to the catalogue, the tooling and the documentation.
This file covers the terms a contribution arrives under. What the work itself
has to satisfy is in four documents, and is not repeated here:

| | |
|---|---|
| What a Test Unit must contain, and at which depth | [`docs/AUTHORING.md`](docs/AUTHORING.md) |
| What a chain edge asserts, and what it does not | [`docs/CHAINING.md`](docs/CHAINING.md) |
| The model, and how the artefact is built from it | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| What the validator checks, and why each rule exists | [`docs/VALIDATION.md`](docs/VALIDATION.md) |

---

## Inbound licensing

Pentest NavGrid is published under Apache-2.0 and that is not changing. The terms below
exist so that the project can *also* license the same material differently in
future -- a hosted build, or a commercial layer -- without having to find and
ask every past contributor. A project that cannot answer that question ends up
unable to answer it later either, which is why it is answered now rather than
after the first outside contribution arrives.

Two things this does **not** do, because both are the usual reasons to distrust
an agreement like this one:

- **It does not take your copyright.** You keep it. What you grant is a licence
  alongside it, not instead of it.
- **It does not let anything already published be taken back.** Apache-2.0 grants
  every recipient a perpetual, irrevocable licence to what they received. No
  agreement here can withdraw that, and none of this is retroactive against a
  release that has already happened.

### Contribution Licence

By submitting a contribution you agree to the following.

**1. Definitions.** *"Owner"* means Ahmad Kabiri, the copyright holder named in
[`NOTICE`](NOTICE). *"You"* means the individual or legal entity submitting.
*"Contribution"* means any work of authorship you submit to this repository by
any means -- pull request, patch, issue attachment or otherwise -- **in any
directory**. It is not limited to source code: catalogue content under
`knowledge/`, `vocab/`, `cards/`, `payloads/`, `mitigations/`, `toolbox/` and
`standards/`, and documentation under `docs/` and the repository root, are
contributions on the same terms as code.

**2. Copyright licence.** You grant the Owner a perpetual, worldwide,
non-exclusive, no-charge, royalty-free, irrevocable copyright licence to
reproduce, prepare derivative works of, publicly display, publicly perform,
sublicense and distribute your Contribution and such derivative works, **under
Apache-2.0 and under any other licence terms the Owner chooses**, including
proprietary terms.

**3. Patent licence.** You grant the Owner and every recipient of software
distributed by the Owner a perpetual, worldwide, non-exclusive, no-charge,
royalty-free, irrevocable patent licence to make, have made, use, offer to sell,
sell, import and otherwise transfer your Contribution, limited to those patent
claims licensable by you that are necessarily infringed by your Contribution
alone or by its combination with the project. If any entity brings patent
litigation alleging that the project or a contribution within it constitutes
direct or contributory patent infringement, any patent licence granted under
this section to that entity terminates as of the date the litigation is filed.

**4. Publication under Apache-2.0.** Your Contribution is published in this
public repository under Apache-2.0 like the rest of it. Section 2 is in addition
to that, not instead of it.

**5. What you are representing.** That each Contribution is your original work,
or that you have the right to submit it under these terms; that if you are
employed and the work was created within the scope of that employment, you have
your employer's permission or your employer has waived its rights; and that any
third-party material included is identified as such, with its source and licence
named in the pull request.

**6. No obligation.** The Owner is under no obligation to accept, merge or use
any Contribution.

**7. No warranty.** Except for the representations in section 5, a Contribution
is provided as-is, without warranty of any kind.

**8. Correction.** If any representation in section 5 becomes inaccurate, tell
the Owner.

### How to accept it

There is no signing portal. Two things per pull request:

1. In the pull request description, one line:

   > I have read `CONTRIBUTING.md` and I agree to the Contribution Licence.

2. Sign off each commit, which records the same agreement in the history:

   ```bash
   git commit -s
   ```

   `-s` appends `Signed-off-by: Your Name <your@email>`. Use a name and address
   you can be identified by; a pseudonym is fine, an unreachable one is not.

If your contribution includes work by somebody else, name them and their licence
in the pull request rather than in a commit message, where it is easy to miss.

---

## What a contribution must not contain

Three things are rejected on sight, and two of them are checked mechanically.

**Prose from a referenced standard.** WSTG and ASVS are share-alike licensed.
This repository references their identifiers, official test titles and group
headings for navigation and cross-mapping, and reproduces none of their text.
Everything written here is original. A contribution that pastes standard prose
puts the project's licensing in question, so write the thing in your own words
or do not write it.

**Anything from a real target.** No hostname, address, credential, token,
account identifier, session, or captured request from an actual engagement --
in content, tests, fixtures, examples or commit history. `tests/test_safety.py`
checks for concrete hosts where a placeholder belongs, and for command templates
that hard-code a target instead of parameterising it.

**Speculative chain edges.** A chain edge is a security claim. Declaring a
capability a prerequisite asserts the test is not performable without it;
declaring that a success establishes a capability asserts the result proves that
much and no more. Both are judgements a reader will rely on. An edge nobody
thought about is indistinguishable from one that was checked, and the second is
the only reason the first is worth reading -- so bulk or generated edges are not
acceptable here, however plausible they look.

---

## Before opening a pull request

```bash
python -m unittest discover -s tests -t .
python -m pentest_navgrid validate
```

Both must pass, and CI runs exactly them -- no CI-only extras, because a check
nobody can reproduce before pushing gets worked around rather than fixed.

Two runners inside the suite are optional locally and installed in CI: `node`
executes the artefact's own graph, layout, path-walk and search functions
against the real catalogue, and a browser driven through Playwright uses the
built file. A suite that silently skipped them would look exactly like one that
ran them, so CI fails if either is missing. Install them with:

```bash
python -m pip install playwright && python -m playwright install chromium
```

If your change alters what the catalogue holds, `python -m pentest_navgrid index`
regenerates `standards/wstg-index.yaml`; CI fails if the committed file has
drifted from what the catalogue derives.

[`docs/ROADMAP.md`](docs/ROADMAP.md) is build state and is updated in the same
pull request as the work, for the reason stated at the top of it.
