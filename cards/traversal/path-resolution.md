# Path resolution

Shared by every unit of `PTN-RES-01`. The reasoning about where a filter sits
and what a negative result means is the same in all of them, so it is written
once here.

## Recall

**The one question** — does the parameter *resolve* a path, or *name* one? A
value that reaches a resolver behaves differently from one that indexes a
lookup table, and almost every wasted hour on this topic comes from testing the
second as though it were the first.

**Sequence**

1. Baseline the unmodified request. Status, length, content type.
2. `./FILE` — identical response means a resolver is in the path.
3. `DIR/../FILE`, `DIR` being a directory that exists — identical response means
   sequences are *resolved*, not matched.
4. Only then leave the root: overshoot the depth, and let the clamp do the
   arithmetic.
5. Match on a file fingerprint, never on status or length.

**Payloads** — [`probe`](../../payloads/traversal/probe.yaml) ·
[`encoding`](../../payloads/traversal/encoding.yaml) ·
[`targets`](../../payloads/traversal/targets.yaml) ·
[`inclusion`](../../payloads/traversal/inclusion.yaml)

**First false positive** — a 404 read as a refusal. A parameter that reaches no
filesystem answers a traversal payload exactly the way a well-defended one does.

**Done when** — the parameter is recorded as resolving a path, not resolving
one, or indistinguishable, with the no-op probe that decided it.

---

## Depth

### Where the parameter came from

Four shapes, and they fail differently enough that recognising which one is in
front of you is worth more than any payload list.

| Shape | Looks like | What decides the result |
|---|---|---|
| Download or preview | `?file=report.pdf` | Whether the name is joined to a base directory before or after normalising |
| Template or page loader | `?page=about` | Whether the sink appends an extension, and whether it includes or reads |
| Static middleware | `/assets/../../x` | The web server's own normalisation, usually before the application sees anything |
| Rewritten path | `X-Original-URL: /../x` | Which of the proxy and the origin normalises, and whether they agree |

The fourth is the one that surprises people: the application may be flawless and
the deployment still traversable, because the component that resolved the path
was never the one that checked it.

### Why the no-op probe comes first

A traversal payload has two ways to fail and they produce the same response.
Either the value never reaches a resolver — it is a key into a table, and `../`
is just an unusual key — or it reaches one that refuses. From a 404 the two are
indistinguishable.

`./FILE` and `DIR/../FILE` separate them. Both resolve back to exactly the
resource the baseline asked for, so a resolver returns the baseline response and
a lookup table returns not-found. Neither leaves the intended directory, which
means the question is answered before anything is read, and answered without the
request that would raise an alert.

`DIR` has to be a directory that **exists**. A POSIX resolver walks the path one
component at a time and fails on a missing directory before it ever reaches the
`..`, so an invented name returns not-found from a perfectly vulnerable sink —
and reads as a clean result. Take the name from a path the application already
serves. Where nothing is known to exist, `./FILE` is the whole of the available
answer, and the result is the weaker one it is.

This ordering costs two requests and routinely saves an afternoon.

### Where the filter sits

Once a negative result is in hand, the encodings are not a list to work through —
each one distinguishes a different architecture:

- **Plain fails, single-encoded works.** The filter inspected the request before
  the server decoded it. It is looking at bytes the application never sees.
- **Single fails, double-encoded works.** Two decodes and one filter, with the
  filter between them. Almost always a proxy in front of an application, each
  decoding once.
- **`....//` works.** The filter *strips* rather than rejects, and does not
  re-examine its own output. Stripping `../` from `....//` leaves `../`.
- **Nothing works, and the connection drops.** Not a filter at all — a signature
  match upstream. The application's own behaviour is still unknown, and the
  result belongs against the intermediary rather than against this parameter.

The last case is why identifying the tiers motivates the evasion unit. A refusal
you cannot attribute to a layer is not a finding about the application.

### Reading versus interpreting

The severity of this topic lives in one distinction that the response body hides.

A sink that *reads* returns the file. A sink that *includes* returns the result
of interpreting it — which for a configuration file is frequently nothing at
all. An empty response therefore means either "no such file", "no permission",
or "the interpreter consumed it", and those are a non-finding, a non-finding,
and a critical finding respectively.

Two obvious tests do **not** separate them, and both are worth knowing as
non-tests:

- **A system file returned intact.** `include()` of a file containing no code
  emits it unchanged, exactly as a read does. `/etc/passwd` coming back whole
  proves the read and says nothing about interpretation.
- **A source-reading wrapper.** It transforms the stream before either sink sees
  it, so a read sink and an include sink return identical encoded bytes. It is
  the best way to *obtain* source and a useless way to classify a sink.

What separates them is a file whose interpretation visibly differs from its
text — which means the application's own source. Request it through the
parameter: source text back, and the sink reads; rendered output or an empty
body, and it interpreted. The wrapper then *confirms* the second case by
returning the source the plain request would not give. That is what the wrapper
is for here: confirmation after the discriminator, not the discriminator.

### Depth arithmetic, and why to skip it

Resolvers clamp at the filesystem root: `../` from `/` is `/`. So an overshoot
of eight or ten levels resolves to the same place a precisely counted one does,
and counting costs a request per guess to learn something the clamp already
knows. Overshoot, and spend the saved requests on encodings instead.

The exception is a target relative to the *application* root rather than the
filesystem root — a Java deployment descriptor, an environment file beside the
entry point. Those need less depth, not more, and overshooting misses them. That
is what the disclosed application root is for, and why the error unit is cheap
enough to run before the read.

### Where this stops

A confirmed read of a system file is the finding. Reading application
configuration is a different act: it takes the client's credentials onto the
tester's disk, and it is a decision to put to the client rather than the next
step of a procedure. Turning a read into execution by poisoning a file the
server will later interpret changes the target in a way nothing outside it can
undo.

Both are within the technique. Neither is within a default engagement.
