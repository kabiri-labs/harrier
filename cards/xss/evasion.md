# Four mechanisms, one clean result

For `HRR-CLT-01-EVADE`. A context unit came back negative. That negative has
four possible causes, they are defeated differently or not at all, and telling
them apart is worth more than any single bypass.

## Recall

**Four mechanisms** — the template's encoder, a sanitiser rewriting the markup,
a browser policy blocking execution, an appliance refusing the request. One
observation separates each from the others.

**Payload intact in the body with nothing running is a policy finding**, and a
materially different report from *payload encoded in the body*. Read the
headers, not the payload.

**Record what a policy permits**, not how to defeat it: a permitted host, a
missing directive, an inline allowance.

**A stripping filter identifies itself.** A form that becomes valid only after
removal has run on it cannot be produced by a filter that rejects.

---

## Depth

### Separating the four

Do this before attempting any bypass. It is three observations of one response,
and it decides whether a bypass is even the right activity.

| Look at | If | The mechanism is |
|---|---|---|
| The **raw body** | The payload is absent, or present as entities | The application's **encoder** |
| The **raw body** | The payload is present but altered — a tag gone, an attribute dropped, a scheme rewritten | A **sanitiser** |
| The **response headers**, with the payload intact in the body | A content policy is present and nothing executed | A **browser policy** |
| The **status and the page itself** | A block page, a reference number, a connection reset, or a response that is not the application's | An **upstream appliance** |

The order matters. Reading the console first tells you only that nothing ran,
which is true in all four cases and distinguishes none of them.

### Why "intact but not running" is its own finding

This is the distinction the unit's first false positive is about, and it changes
what the report says the client must fix.

**Payload encoded in the body.** The application did its job. There is no
injection. The finding, if any, is elsewhere.

**Payload intact in the body, nothing running.** The application encoded
nothing. The value went into the document exactly as written, an element was
created, and a browser control declined to execute it. That is an injection
vulnerability with a mitigating control in front of it — and the control is:

- one header away from being weakened by somebody who does not know it is
  load-bearing;
- absent on any endpoint where the header is not set, which is rarely all of
  them;
- irrelevant to the markup-only outcomes that need no script at all — a form
  with a chosen destination, an unprompted request, a `<base>` that redirects
  every relative URL in the page.

So the two reports differ in severity, in remediation, and in who owns the fix.
Writing the second as the first is how a real defect gets closed as working as
intended.

### What to record about a policy

The instruction in the unit is to record what a policy permits rather than to
defeat it, and that is a deliberate scoping choice: policy bypass research is a
field of its own, and an engagement's job is to say what this deployment's
policy actually protects.

Three things are worth writing down, in this order:

1. **A permitted host that the tester can write to.** A policy allowing a CDN,
   an analytics host or a storage bucket is a policy that permits script from
   anywhere the tester can place a file on that host.
2. **A missing directive.** Absent `object-src`, `base-uri` or `form-action`
   leave routes open that the script directives say nothing about — and
   `base-uri` in particular is what stands between injected markup and every
   relative URL in the document.
3. **An inline allowance.** `unsafe-inline`, or a nonce that is reused across
   responses rather than generated per response, means the policy is present and
   not doing the thing it is there for.

That list is a finding a client can act on. "The policy was bypassed using a
technique from a blog post" frequently is not, because the fix for it is
one entry rather than the shape of the policy.

### The stripping form, and what it proves

```
<scr<script>ipt>...</scr</script>ipt>
```

This is not primarily a bypass. It is an **identification**.

A filter that *rejects* a payload containing `<script>` refuses this outright:
the string is right there. A filter that *removes* what it matches produces
`<script>...</script>` from it, because after removing the inner `<script>` the
outer fragments close up into exactly the thing that was being removed.

So a positive here says something specific about the mechanism: it removes
rather than refuses, and it does not re-examine its own output. That single fact
predicts a family of further failures — nested forms of every kind, and any
sanitiser rule whose result can re-form a match — and it is worth more in a
report than the one payload that got through.

The same logic runs through the rest of the file:

- **Case variation** accepted → the refusal was a case-sensitive list, not a
  parser.
- **An alternative element with the same event** accepted → the list is of
  element names, not of event names. Refused → the reverse.
- **A call written without parentheses** accepted → the filter matches on a
  call's punctuation rather than on the expression.

Each is a question about the mechanism whose answer holds after this engagement
ends, which is not true of any individual payload.

### Where this unit stops

`EVADE` establishes `control.filter.identified` — which layer refused, and what
survives it. It does not establish execution. A surviving form is recorded so
the **context unit** can be re-run with it, and the finding belongs to that unit
rather than to this one.

That boundary is why this unit is `kind: recon`: it enumerates and attributes,
and there is no target behaviour it can call vulnerable on its own.

## Related units

- The eight context units — each can return a negative this unit explains, and
  each is re-run with whatever survives.
- `HRR-CLT-01-PROBE` — a refusal seen here may mean the value never reached the
  context at all, which the probe settles first.
