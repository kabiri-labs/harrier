# Contextual output encoding

Applies to `PTN-CLT-01`, and to `PTN-CLT-02` when it is written. Cross-references:
ASVS V1.1, V1.3, CWE-79, CWE-80.

## The fix that works

**Encode at the point of output, for the context the value lands in.**

Not at input. Not once, centrally, on the way in. At the moment the value is
written into a document, by something that knows *where* in the document it is
going — because that is the only place the answer exists.

The contexts and their encoders are not interchangeable:

| The value lands in | It needs |
|---|---|
| Element content | HTML entity encoding of `<` `>` `&` |
| An attribute value | Entity encoding including both quotes, and the attribute quoted |
| A URL attribute | An allow-list of schemes, then URL encoding of the component |
| A script string literal | JavaScript string escaping — and the value must not be able to write `</script>` |
| A style value | CSS escaping, and no `url()` the value controls |
| Inline SVG | The same as element content, under SVG's own content model |

A value correctly encoded for element content is frequently live inside a script
string on the same page, where entities mean nothing and the quote is the only
delimiter. That is the defect this whole topic decomposes around, and it is a
consequence of *one* encoder being applied to several contexts.

## Let the template do it

The practical form of the rule above: use a template system that encodes by
default and knows its context, and treat every escape hatch as a code review
trigger.

Every mainstream engine has one, and they are the thing to grep for by name:
`|safe` and `{% autoescape off %}`, `Html.Raw`, `dangerouslySetInnerHTML`,
`v-html`, `raw`, `{{{ }}}`, `MarkupSafe`'s `Markup()`. Each says *I have decided
this string is already safe*. Sometimes that is true; the review question is who
decided, and against which context.

Where a template cannot be used — a value built into a script block, a header, a
generated stylesheet — encode explicitly with a library function named for the
context, not with a general-purpose one.

## Sanitise only where markup is the feature

A user who is allowed to submit formatting needs their markup parsed, so
encoding is not available. There, and only there:

- Use a maintained sanitiser with an **allow-list** of elements and attributes.
  A list of what to remove is a list somebody has to keep complete forever.
- Sanitise **on output**, or on input *and* on output. A value sanitised on the
  way in is sanitised against the library's rules of that day, and it sits in
  the database long after those rules change.
- Never write your own. The `<scr<script>ipt>` form in
  `payloads/xss/evasion.yaml` exists because filters that remove rather than
  reject do not re-examine their own output, and that is one of a family.

## A content policy is a second layer, not the fix

Worth deploying, and it does not close the defect:

- It is one header away from being weakened by somebody who does not know it is
  load-bearing.
- It is absent on any endpoint that does not set it, which is rarely none.
- It does nothing about the markup-only outcomes: a form whose destination the
  attacker chose, a request the browser makes unprompted, a `<base>` that
  redirects every relative URL in the page. Those need `form-action` and
  `base-uri`, which script directives say nothing about.

Where one is deployed: a nonce generated **per response** rather than reused, no
`unsafe-inline`, and a considered `object-src`, `base-uri` and `form-action`.
And read the allow-list adversarially — a permitted CDN or storage host is a
permitted script source for anyone who can put a file there.

## URL schemes need an allow-list

A value that becomes an `href`, `src`, `action` or `formaction` is not a string
to be encoded; it is a URL whose *scheme* decides what happens. Parse it, and
accept only `https`, `http` and the relative forms the application needs.

A blacklist of `javascript:` is defeated by whitespace and control characters
inside the scheme, which browsers strip before parsing it — the tab-split form
in `payloads/xss/htmluri.yaml` is exactly this, and it identifies the mechanism
as a string comparison rather than a parse.

## What does not work

**One global encoder.** It is correct for whichever context its author had in
mind and wrong for the others, and its presence is the reason nobody looks
again.

**Sanitising on input.** It stores a value that is safe under one set of rules,
in a place that will be rendered by code written later, into contexts nobody has
thought of yet — and it destroys the original, so the application can no longer
tell what the user actually typed.

**Stripping tags.** Removal re-forms matches, as above. Rejection has no such
failure mode, and it also tells an operator that something happened.

**Blocking a list of event names.** There are hundreds, browsers add more, and
the SVG and HTML sets differ. `payloads/xss/evasion.yaml` separates a list of
element names from a list of event names precisely because both exist in the
wild and both are incomplete.

**Relying on the browser's own filter.** The XSS auditors are gone from current
browsers, having been removed as a source of vulnerabilities in their own right.
