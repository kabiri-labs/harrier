# Context decides everything

Shared by `HRR-CLT-01-PROBE` and all eight context units. The topic's whole
argument is that these are not eight payload lists — they are eight different
answers to *what has already been escaped by the time the value arrives*, and
each has a different negative result.

## Recall

**Read the context from the raw body, never from developer tools.** The browser
has already repaired the markup and re-serialised what it built, so the element
tree is the browser's repair rather than what the application sent.

**An encoder is written for one context.** A value correctly encoded for element
content is frequently live inside a script string on the same page, where the
angle brackets are ordinary characters and the quote is the only delimiter.

**Choose an event that fires without interaction**, so a negative is a negative
rather than a handler nobody triggered.

**Three results, not two** — markup encoded, markup parsed, markup parsed *and
executed*. The middle one is a real finding with its own unit.

**Delivery is a dimension.** Reflected and stored change who receives the
payload, not what proves it fired — and a stored proof fires in strangers'
browsers, so it is silent and its location is recorded.

---

## Depth

### The table this card exists for

| Context | Delimiters that matter | What proves execution | What a clean result does **not** rule out |
|---|---|---|---|
| **Element content** | `<` `>` | An element the tester introduced runs script | Anything in an attribute, a script block, or a style — the element-content encoder covers none of them |
| **Attribute value** | `"` `'` and the space | A handler the tester added fires without interaction | The angle brackets may still be live for a value elsewhere on the page; and an unfired handler looks identical to an encoded one |
| **URL attribute** | the scheme, not the path | Activating the element runs script in this origin | Nothing about the other attributes of the same element; a rewritten scheme says the URL was filtered, not that the value was encoded |
| **Script string** | the quote that opened the literal, and `\` | The page's own block evaluates a computed expression | HTML encoding is irrelevant here — this is the context most often recorded clean because the wrong encoder was checked |
| **Script code** | none; the value is already an operand | A computed marker the page's block produced | That a serialiser is present today: the same parameter may be an operand on another page |
| **Style** | `"` `<` and the block terminator | Script runs from markup introduced past the boundary | Control of the style value itself, which is a real finding for another topic |
| **Inline SVG** | `<` `>` under SVG rules | An element or event inside the subtree runs | Nothing from the HTML forms: the subtree parses under different rules, so a refusal of an HTML payload says nothing here |
| **Markup, no script** | `<` `>` | *Not* execution — an element that reaches a destination, a request, or a rendered instruction | That script is impossible; only that it did not run under the policy in force |

The right-hand column is the reason the topic decomposes at all. A checklist
that ticks cross-site scripting once records the left-hand side and loses the
right.

### An encoder is written for one context

This is the central claim, and the script-string case is the worked example.

A template that HTML-encodes its output turns `<` into `&lt;`, `>` into `&gt;`
and the quotes into entities. Inside element content that is complete: nothing
the value contains can open an element.

Now the same value is written into a script block:

```html
<script>var greeting = "VALUE";</script>
```

HTML entities have no meaning inside a script block. `&lt;` is five ordinary
characters. The angle brackets the encoder so carefully removed were never the
delimiter here — the quote is, and if the encoder covered it as `&quot;` the
browser hands the script block `&quot;` and the literal is untouched.

So a page can be correctly encoded, demonstrably safe under the test everybody
runs, and fully injectable in the block three lines further down. That is not an
exotic case; it is the ordinary consequence of one encoder and several contexts,
and it is why `HRR-CLT-01-JSSTR` names it as the first false positive.

The same asymmetry runs the other way. A JavaScript-escaping helper that
backslash-escapes quotes leaves `<` and `>` untouched, which is exactly what
`</script>` needs — and the HTML parser ends the script element on that literal
text regardless of the JavaScript around it.

### Read the raw body, not the element tree

Every context unit's `preconditions` says the context was read from the raw
body. This is not fastidiousness.

The browser's parser is a repair mechanism. Given broken markup it closes
unclosed elements, moves content out of positions where it is not allowed,
reparents nodes into `<body>`, and drops attributes it cannot make sense of.
Then developer tools show you a *re-serialisation of the repaired tree*.

Two consequences:

- The context you read there may not be the context the application wrote. A
  value the server put inside a `<title>` can appear in the element tree in the
  body, because the parser moved it.
- Markup that was present in the response can be absent from the tree, and
  markup absent from the response can be present in it.

So: read the response bytes to decide the context and to decide whether the
payload survived encoding. Read the running page only to decide whether it
*executed*. Those are two different questions asked of two different artefacts,
and the units keep them apart deliberately.

### Choose an event that fires on its own

A handler that needs a click has three explanations for a silent page: it was
encoded, it was not fired, or the element is not clickable. Only the first is a
negative result.

So the payload files prefer `onerror` on a broken image, `onbegin` on an SVG
animation, and `onfocus` paired with `autofocus` — each fires from the page's
own load. When such a payload is silent, the payload is the thing that failed,
and the unit's negative means what it says.

Two practical notes from running these:

- `onfocus` with `autofocus` needs the parameter's **existing value in front of
  it** when the attribute is unquoted. Sent into an empty unquoted attribute the
  parser takes the whole payload as the value, and the element gets one
  attribute and no handler at all — which reads as a clean negative.
- A value written into script as an operand cannot use a bare comma in a `var`,
  `let` or `const` declaration: there the comma separates declarations rather
  than acting as the comma operator, so `1,console.log(m)` is a syntax error
  that runs nothing — including the page's own block. Parenthesised, it
  evaluates everywhere.

### Three results, not two

The distinction the topic depends on:

1. **Markup encoded.** The value arrives as entities. Nothing the tester wrote
   becomes part of the document. This is the control working.
2. **Markup parsed.** The element the tester wrote is in the document tree, and
   no script of theirs runs — a policy blocked it, a sanitiser stripped the
   handler, or the element never carried one. `HRR-CLT-01-MARKUP` exists for
   this, because what injected markup reaches without script is its own finding:
   a form whose destination the tester chose, a request the browser makes
   unprompted, a `<base>` that redirects every relative URL in the page.
3. **Markup parsed and executed.** Script runs in the page's origin.

Reporting (2) as (1) understates a real finding. Reporting (2) as (3) overstates
one, and is the mistake a reviewer will catch. The discriminator is mechanical:
look in the parsed document for the element, and in the console for the marker.
Both, separately, every time.

And `HRR-CLT-01-MARKUP`'s own first false positive is worth repeating here: it
is not the consolation prize for a failed script payload. A unit that records
only that a bracket survived has established nothing the probe did not.

### Delivery, and what it costs somebody else

`delivery: [reflected, stored]` is a dimension rather than two units, because
the oracle does not change: the marker either arrived or it did not.

What changes is who the payload fires for, and that is a safety consequence
rather than a procedural one:

- **Reflected** — the payload is in the tester's own request and fires in the
  tester's own browser. A dialog is acceptable proof.
- **Stored** — the payload is in the application, and fires for whoever loads
  the page. That may be one other account, every visitor to a record, or every
  visitor to the application.

So a stored proof is **silent**: a console entry or a distinctive node, never a
dialog. A dialog raised in a stranger's browser is not evidence anybody will see
— it is an interruption in somebody's afternoon, caused deliberately, by a
person they never engaged. And the location of every stored payload is recorded
when it is placed, because a payload nobody can find is one the client cannot
remove.

`HRR-OUT-06-IMPACT` is where the reach of that is established, and it is
answered from how the application stores and serves the payload rather than by
delivering anything to a real person.

## Related units

- `HRR-CLT-01-PROBE` — which context, and which delimiters survived into it.
  Sole producer of `surface.reflection.unencoded`.
- The eight context units — one per row of the table above.
- `HRR-CLT-01-EVADE` — where a negative goes before it is believed.
- `HRR-CLT-02` — the sibling topic for output the browser itself wrote, where
  nothing the server returned was ever unsafe.
