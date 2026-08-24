# Taxonomy

Identifiers, domains and axis vocabularies. This is the part of the project that
is hardest to change later and easiest to get wrong, so it is fixed here before
any content is written.

---

## 1. Identifier grammar

```
HRR-<DOM>-<NN>            a topic     HRR-INJ-01
HRR-<DOM>-<NN>-<SLUG>     a unit      HRR-INJ-01-UNION
```

- `HRR` — the project prefix. Deliberately not `WSTG`: the scope is web
  application testing, and a large part of it has no WSTG identifier.
- `<DOM>` — a three-letter domain code from §2. **Frozen at creation.**
- `<NN>` — a two-digit serial within the domain, assigned in creation order and
  never reused or renumbered.
- `<SLUG>` — an uppercase slug from the vocabulary of the topic's declared axis
  (§3), or from the `phase` vocabulary, which is available to every topic.

**Identifiers are addresses, not claims.** A topic's domain code says where it
was filed, not what it is *about*. If a topic later reads better under a
different domain, it is *displayed* there via metadata; the identifier does not
move. The alternative — renumbering — breaks every external reference, every
note a tester has written, and every card cross-reference, in exchange for
tidiness nobody outside the repository can see.

Cross-references to published standards (`wstg`, `cwe`, `asvs`) are optional and
plural. A unit may map to several, or to none.

## 2. Domains

Fourteen codes. A domain names a **mechanism**, never a surface — see §3 for the
procedure that assigns one, and `standards/wstg-map.yaml` for the evidence that
these fourteen resolve all 109 published WSTG identifiers.

| Code | Domain | Scope |
|---|---|---|
| `RCN` | Reconnaissance & mapping | fingerprinting, discovery, surface and workflow enumeration |
| `CFG` | Configuration & deployment | server and platform config, response headers, exposed files, cloud posture |
| `SUP` | Components & supply chain | outdated and vulnerable dependencies, integrity of delivered assets |
| `IDN` | Identity & account lifecycle | registration, provisioning, enumeration, account-recovery surface |
| `AUT` | Authentication | credentials, lockout, multi-factor, reset flows, federated sign-in |
| `ACL` | Authorization & access control | object- and function-level access, privilege escalation, tenancy |
| `SES` | Session management | token issue and lifecycle, cookie attributes, fixation, logout, CSRF |
| `INJ` | Server-side injection | SQL, NoSQL, OS command, LDAP, XPath, template, XML, deserialization |
| `CLT` | Client-side | XSS, DOM sinks, prototype pollution, clickjacking, `postMessage`, CORS |
| `PRT` | Protocol & transport abuse | request smuggling, cache poisoning and deception, TLS terminators, WebSocket |
| `RES` | Server-side resource handling | SSRF, file upload, file inclusion, path handling, archive extraction |
| `CRY` | Cryptography & secrets | signed tokens, encryption use, randomness, exposed secrets |
| `BIZ` | Business logic | workflow circumvention, race conditions, quantity and price handling |
| `ERR` | Errors & information disclosure | stack traces, verbose errors, debug endpoints, metadata leakage |

Note `AUT` and `ACL` rather than the `ATHN`/`ATHZ` pair used by WSTG. Those two
differ by one letter in the middle of a four-letter token — the shape that gets
mistyped and mis-remembered, and that reads perfectly well in a diff once it has
been. Two codes sharing no letters cannot drift into each other. WSTG's own
prefixes are still referenced verbatim under `refs.wstg`, where they are checked
against the pinned file rather than trusted.

### There is deliberately no API domain

Testing an API does not change *what* is being tested, only *where*. Broken
object level authorization is the same mechanism as an insecure direct object
reference; API reconnaissance is reconnaissance. An `API` domain would guarantee
duplication — the same test written twice, diverging from the second copy onward
— and it would be the only domain in the set that named a surface rather than a
mechanism.

Surfaces are handled by the vocabulary built for them: `rest-api`, `graphql` and
`websocket` are tags in `vocab/surfaces.yaml`, and surface-first navigation
(`ARCHITECTURE.md` §8) is how a tester holding a GraphQL endpoint gets everything
that applies to it. The same argument retires the question for mobile backends,
admin panels and any surface named later.

## 3. Assigning a domain — an ordered procedure

Read the list top to bottom and stop at the first rule that fires. It is ordered,
not weighted: where two rules could apply, the earlier one wins, and that is the
whole mechanism by which the assignment is unambiguous rather than a matter of
taste.

| # | If… | Domain |
|---|---|---|
| 1 | the deliverable is a map that other tests consume, not a verdict | `RCN` |
| 2 | the finding exists because two components parse the same bytes differently, or because one trusts a request-controlled value naming the deployment | `PRT` |
| 3 | the server fetches, includes, opens, stores or extracts a resource the attacker named or supplied | `RES` |
| 4 | attacker text is parsed as code or as a query by a **server-side** interpreter | `INJ` |
| 5 | the subject is a session token, its carrier, or its lifecycle | `SES` |
| 6 | exploitation requires a victim's browser, or the subject is browser storage, parsing, origin policy or framing | `CLT` |
| 7 | the subject is the cryptography itself — algorithm, key handling, randomness, protocol version, padding, or its absence | `CRY` |
| 8 | the subject is proving identity | `AUT` |
| 9 | the subject is whether an account exists, or how one is created | `IDN` |
| 10 | the subject is permission to act, or on which object | `ACL` |
| 11 | the subject is third-party code or its delivery into the application | `SUP` |
| 12 | the subject is application-specific workflow, sequencing, timing or value | `BIZ` |
| 13 | the response reveals information it should not | `ERR` |
| 14 | otherwise: it is a declared server or platform setting | `CFG` |

The order carries real decisions, and three are worth stating because they are
the ones a reader will want to argue with:

**Rule 5 before rule 6.** Cross-site request forgery requires a victim's browser,
which would put it in `CLT`. But its mechanism is the ambient authority of the
session carrier, which is what `SES` is about — and the fix is a session-layer
fix. Cookie attributes land in `SES` for the same reason. Meanwhile CORS,
clickjacking and browser storage reach rule 6 untouched.

**Rule 3 before rule 10.** Directory traversal is published under authorization
and is usually *found* while testing access control. Its mechanism is the server
resolving a path the attacker wrote, which is the same mechanism as file
inclusion, upload handling and server-side request forgery. Filing it by where it
was found rather than by what it is would split one family across two domains.

**Rule 7 covers absence.** "Credentials sent over an unprotected channel" is a
cryptography finding, not an authentication one: the mechanism is missing
transport protection, and it is the same test whether the data is a credential, a
session token or a payment detail. Authentication references it; it is written
once.

### Rule 0 — when the procedure does not resolve

Two outcomes are legitimate and are recorded rather than forced:

- **The identifier is not one test.** `WSTG-APIT-99` ("Testing GraphQL") is four
  topics across four domains. Recording all four is the model working.
- **The identifier is not a test.** `WSTG-INPV-14` ("Incubated Vulnerabilities")
  describes second-order delivery, which this model expresses as a dimension on
  injection and client-side topics rather than as a topic of its own.

Both are marked `rule: 0` in `standards/wstg-map.yaml` with the reason, so the
coverage claim stays honest instead of quietly counting them.

## 4. Axes and their slug vocabularies

Every topic declares exactly **one primary axis**. Its units are named from that
axis's vocabulary, plus the `phase` vocabulary, which every topic may use.

A slug outside the declared vocabulary is rejected. This is what makes
non-overlap mechanical rather than a matter of care: two topics cannot invent two
different names for the same idea, because neither may invent a name at all.

**Needing two primary axes is a signal, not a special case.** It means either the
topic should split into two, or the second axis is a dimension. Resolve it with
§3 of `ARCHITECTURE.md`, not with a second axis.

### `phase` — available to every topic

Steps that recur across topics and are not alternatives to each other.

`MAP` · `PROBE` · `FPRINT` · `VERIFY` · `EVADE` · `IMPACT`

### `technique` — alternative routes to the same finding, chosen by evidence

`ERROR` · `BOOL` · `TIME` · `UNION` · `OOB` · `STACK` · `SECOND` · `DIFF` · `BRUTE` · `REPLAY`

### `context` — where the payload lands and is interpreted

`HTMLBODY` · `HTMLATTR` · `HTMLURI` · `JSSTR` · `JSCODE` · `CSS` · `SVG` · `MARKUP`
· `SQLSTR` · `SQLNUM` · `SQLID` · `OSCMD` · `PATH` · `XMLDOC` · `TMPL` · `LDAPFLT` · `JSONDOC`

### `vector` — how attacker-controlled input arrives

`QUERY` · `BODY` · `PATH` · `HEADER` · `COOKIE` · `FILENAME` · `FILEBODY`
· `WSMSG` · `GQLVAR` · `IMPORT` · `REFERER`

### `property` — which security property of one mechanism is under test

`ENTROPY` · `SCOPE` · `EXPIRY` · `ROTATION` · `FLAGS` · `BINDING` · `REVOCATION`
· `TRANSPORT` · `STORAGE` · `POLICY` · `VALIDATION` · `NAMING` · `PARSING`
· `SERVING` · `QUOTA`

### `asset` — the same test against a different kind of surface

`LOGIN` · `LOGOUT` · `REGISTER` · `RESET` · `CHANGE` · `MFA` · `PROFILE`
· `ADMIN` · `EXPORT` · `UPLOAD` · `SEARCH`

## 5. Worked examples

### Reflected and stored XSS — primary axis `context`

```
HRR-CLT-01   Cross-site scripting via server-returned output
  HRR-CLT-01-PROBE       phase    find reflection points and what survives
  HRR-CLT-01-HTMLBODY    context  element content
  HRR-CLT-01-HTMLATTR    context  attribute value, quoted and unquoted
  HRR-CLT-01-JSSTR       context  inside a script string literal
  HRR-CLT-01-HTMLURI     context  href / src / formaction sinks
  HRR-CLT-01-CSS         context  style context
  HRR-CLT-01-MARKUP      context  markup injection with script blocked
  HRR-CLT-01-EVADE       phase    filter, encoder and WAF evasion

dimensions:
  delivery: [reflected, stored]
  engine:   [chromium, firefox, webkit]
```

Eight units instead of eighteen cells, and nothing is lost: `delivery` changes
where you paste the payload, not what the payload is or what proves it fired.

DOM-based XSS is a separate topic (`HRR-CLT-02`) with the same primary axis and
overlapping slugs. That is correct and expected — the slug names the sink, the
topic names who wrote to it. The boundary statement is one line: `CLT-01` is
output the *server* produced; `CLT-02` is output the *browser* produced.

### SQL injection — primary axis `technique`

```
HRR-INJ-01   SQL injection
  HRR-INJ-01-PROBE  · -FPRINT   phase
  HRR-INJ-01-ERROR  · -BOOL · -TIME · -UNION · -OOB · -STACK · -SECOND   technique
  HRR-INJ-01-EVADE              phase

dimensions:
  engine: [mysql, postgresql, mssql, oracle, sqlite]
```

Seven technique units instead of thirty-five technique-by-engine combinations.

### Session token handling — primary axis `property`

```
HRR-SES-01   Session token issue and lifecycle
  HRR-SES-01-ENTROPY · -SCOPE · -EXPIRY · -ROTATION · -FLAGS · -BINDING · -REVOCATION
```

Each is separately recordable — a token can have excellent entropy and no
rotation on privilege change — which is exactly rule §2.1 of `ARCHITECTURE.md`.

## 6. Standards cross-reference policy

Three published standards are pinned under `standards/`. Each pin records the
source, the exact commit or release, and the SHA-256 of the file it was built
from, so anyone can re-fetch the bytes and verify. Pinned files are **generated
and never hand-edited** — a hand-edit would make the verification claim empty.

| Standard | Role here | Rule |
|---|---|---|
| **WSTG** | Coverage skeleton. Confirms the taxonomy is not missing something the profession considers standard. | Identifiers and official titles only. Never write one from memory — verify against the pinned file. |
| **CWE** | The weakness class. This is what "type of vulnerability" means; it is what mitigations attach to. | Referenced by number, resolved against the pin. Must name a **weakness** — a category or a view is rejected by name. |
| **ASVS** | Mitigation cross-reference, for report writing and client conversations. | Identifiers and structural names only — **not requirement text**. Remediation prose is written here, originally. |

ASVS 5.0.0 is pinned at its release tag's commit. Note that the repository also
carries a *branch* named `v5.0.0`, which moves; pinning it would name a moving
target, which is the failure the pin discipline exists to prevent. The two
currently serve identical bytes, and that is not a reason to pin the branch.

The pin records the requirement identifier, the chapter and section names, and
the verification level — and nothing else. Requirement text is what ASVS *is*,
and it is CC BY-SA; reproducing it would force share-alike onto this repository.
A reference here is a pointer for the reader to look up, which is what a
cross-reference is for.

CWE 4.20 is pinned by its versioned archive URL and the SHA-256 of the extracted
XML — not `cwec_latest`, which moves, and not the archive's own hash, since a zip
carries timestamps and two archives of identical content do not hash alike.

The pin records weaknesses, categories and views together, so that citing the
wrong kind can be rejected with a message that says why: `CWE-699` is a category
and `CWE-1000` is a view. Both are real identifiers, so "not found" would be a
misleading thing to say about either. `refs.cwe` names the weakness a unit finds,
never the grouping it sits in, and a deprecated weakness is rejected in favour of
its replacement.

Unlike WSTG and ASVS, CWE is not share-alike: MITRE grants royalty-free use **on
the condition that any copy reproduces its copyright designation and the
licence**. That is a condition, not a courtesy, and `NOTICE` is where this
repository meets it — with a test asserting it still does.

**CVE is not a taxonomy and is not pinned.** A CVE names one bug in one product,
not a class. Where known-vulnerable components are the subject, the unit points
at tooling — OSV, Trivy, the ecosystem's own advisory feed — rather than shipping
a snapshot that is stale the week it lands. A CVE may appear on a card as an
illustrative example of a class; it is never a classification.

WSTG and ASVS are share-alike licensed. Identifiers and official titles only —
no prose from either is copied or paraphrased anywhere in this repository.
