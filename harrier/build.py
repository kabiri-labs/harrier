"""The published artefact: one self-contained HTML file.

Everything the reader needs is embedded, because the file is opened from a
laptop on an engagement network and must not emit a request a monitored target
could observe. No stylesheet, no script, no font, no image is fetched. The data
travels as one JSON blob and the page renders from it.

This module does three things and nothing else: assemble the catalogue and the
indexes the page navigates by, read the template, stylesheet and script from
`artefact/`, and embed them safely into one file. The page itself is no longer
written here -- a UI defect in a string literal is invisible to review, and the
suite could only ever assert on substrings of it.

Every index below is derived from the source documents. None of it is stored,
because a stored edge that was never updated reads exactly like an edge that was
checked and found to hold.
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple

from . import Repository, __version__
from .chain import Chain
from .validate import coverage

ARTEFACT_DIR = Path(__file__).resolve().parent / "artefact"

#: Keys whose value is a literal to be copied and sent, not prose to be read.
#: Whitespace in them is syntax: a MySQL comment is "-- " and stops being one
#: without the trailing space, and a numeric-context probe starts with a space
#: because it is appended to a bare number.
VERBATIM = frozenset({"payload"})

#: The seven fact families, in the order a chain runs through them, with the
#: word the page uses for each. The order is not alphabetical and is not an
#: accident: recon precedes surface precedes access, and impact is where a chain
#: stops. Fixed here rather than read from the vocabulary for the same reason the
#: schema fixes them -- a file that could add a family could file an impact as a
#: primitive.
FAMILIES: Tuple[Tuple[str, str, str], ...] = (
    ("recon", "Reconnaissance", "Something is now known about the target."),
    ("surface", "Surface", "An interactable thing has been shown to exist."),
    ("access", "Access", "A principal or session is held."),
    ("artifact", "Artefact", "A value is in hand."),
    ("primitive", "Primitive", "A capability is controlled -- what an exploit is built from."),
    ("control", "Control", "The state of a defence."),
    ("impact", "Impact", "A business outcome. A chain ends here."),
)


def _text(value: Any) -> str:
    """Collapse the whitespace a folded YAML scalar leaves behind."""
    if not isinstance(value, str):
        return value
    return " ".join(value.split())


def _clean(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: (v if k in VERBATIM else _clean(v)) for k, v in data.items()}
    if isinstance(data, list):
        return [_clean(v) for v in data]
    return _text(data)


def family_of(fact: str) -> str:
    """The family a fact belongs to. It is the first segment of its identifier."""
    return fact.split(".", 1)[0]


def wstg_groups(standard: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The standard's groups, in the standard's order, each with its identifiers.

    The group a test case belongs to is already in its identifier, so the
    membership is read rather than declared twice. What cannot be read is the
    order the groups are presented in: that is the standard's decision, it is
    pinned with the rest, and inventing it from a prefix would silently make it
    this project's decision instead.
    """
    entries = standard["wstg"]
    ordered = [dict(group) for group in standard.get("groups") or []]
    by_code: Dict[str, List[str]] = {}
    for entry in entries:
        by_code.setdefault(entry["id"].split("-")[1], []).append(entry["id"])
    for group in ordered:
        group["ids"] = sorted(by_code.get(group["code"], []))
    return ordered


def unit_order(topic: Dict[str, Any], units: Dict[str, Any]) -> List[str]:
    """A topic's units in its declared order, with anything undeclared after it.

    The declared order is a deliberate performance sequence -- probe before
    verify, verify before evade -- and it is the one piece of sequencing a human
    wrote down. A unit missing from it is a gap in the topic file, not a reason
    to hide the unit, so it follows in identifier order rather than vanishing.
    """
    declared = [uid for uid in (topic.get("order") or []) if uid in units]
    rest = sorted(
        uid for uid, unit in units.items()
        if unit.get("topic") == topic["id"] and uid not in declared
    )
    return declared + rest


def _still_required(
    consumer: Dict[str, Any], established: Set[str], given: Set[str]
) -> Dict[str, List[str]]:
    """What a downstream unit needs that succeeding here does not supply.

    The honest half of a continuation. A unit reached because it consumes a fact
    this one establishes may need three other things as well, and showing the
    edge without them reads as *do this next* when the truth is *this is one of
    the conditions*. `given` facts are the roots of the graph and are not listed:
    naming them would bury the conditions that matter under the ones that always
    hold.

    `granted` facts are deliberately *not* treated as satisfied. An engagement
    may supply host access and usually does not, so a unit needing it is still
    waiting on something the reader has to recognise.
    """
    have = established | given
    requires = consumer.get("requires") or {}
    all_of = [f for f in requires.get("all_of") or [] if f not in have]
    any_of = list(requires.get("any_of") or [])
    if not any_of or any(f in have for f in any_of):
        any_of = []
    out: Dict[str, List[str]] = {}
    if all_of:
        out["all_of"] = all_of
    if any_of:
        out["any_of"] = any_of
    return out


def chain_index(units: Dict[str, Any], given: Set[str]) -> Dict[str, Dict[str, Any]]:
    """Per unit: what it needs, what success establishes, and what may follow.

    Derived from the same four fields the CLI reads, in the same direction. The
    edges are never unit-to-unit in the data: each one carries the capability it
    travels through, because the reason an edge exists is the only part of it a
    reader can act on.
    """
    hard: Dict[str, List[str]] = {}
    hinted: Dict[str, List[str]] = {}
    for uid in sorted(units):
        unit = units[uid]
        requires = unit.get("requires") or {}
        for fact in (requires.get("all_of") or []) + (requires.get("any_of") or []):
            hard.setdefault(fact, []).append(uid)
        for fact in unit.get("motivated_by") or []:
            hinted.setdefault(fact, []).append(uid)

    index: Dict[str, Dict[str, Any]] = {}
    for uid in sorted(units):
        unit = units[uid]
        requires = unit.get("requires") or {}
        incoming = [
            {"fact": fact, "kind": kind}
            for kind, names in (
                ("all_of", requires.get("all_of") or []),
                ("any_of", requires.get("any_of") or []),
                ("motivated_by", unit.get("motivated_by") or []),
            )
            for fact in names
        ]

        established = set(unit.get("yields") or [])
        onward: Dict[str, Dict[str, Any]] = {}
        for fact in sorted(established):
            for other, key in ((hard.get(fact, []), "via"), (hinted.get(fact, []), "hint")):
                for consumer_id in other:
                    if consumer_id == uid:
                        continue
                    edge = onward.setdefault(
                        consumer_id, {"unit": consumer_id, "via": [], "hint": []}
                    )
                    if fact not in edge[key]:
                        edge[key].append(fact)
        for edge in onward.values():
            consumer = units[edge["unit"]]
            edge["kind"] = "requires" if edge["via"] else "motivated_by"
            edge["also"] = _still_required(consumer, established, given)
            if not edge["hint"]:
                del edge["hint"]

        # Hard continuations first, then the ones in the same topic, then by
        # identifier. Deliberately *not* ranked by how little each still needs:
        # that reads as helpful and is not, because it sorts every continuation
        # with unmet conditions below the initial three and hides exactly the
        # honesty this view exists for. A reader taking the first three should
        # meet the conditional ones as readily as the direct ones.
        topic = unit.get("topic")
        outgoing = sorted(
            onward.values(),
            key=lambda e: (
                0 if e["kind"] == "requires" else 1,
                0 if units[e["unit"]].get("topic") == topic else 1,
                e["unit"],
            ),
        )

        # A yielded capability nothing consumes is where a chain stops. Saying so
        # is the point: an empty continuation list with no explanation reads as
        # missing data, and an impact is not missing data -- it is the outcome.
        terminal = [
            {
                "fact": fact,
                "why": "impact" if family_of(fact) == "impact" else "unconsumed",
            }
            for fact in sorted(established)
            if family_of(fact) == "impact" or not (hard.get(fact) or hinted.get(fact))
        ]

        index[uid] = {
            "in": incoming,
            "yields": sorted(established),
            "out": outgoing,
            "terminal": terminal,
        }
    return index


def family_edges(units: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Family-to-family counts: the whole graph at the only scale that reads.

    Three hundred and sixty-six units and a hundred and seventy-seven facts
    drawn at once is a hairball, and a hairball is a picture of nothing. At
    family scale the same data is seven nodes and the shape is legible: recon
    feeds surface, surface feeds primitive, primitive ends in impact.
    """
    tally: Dict[Tuple[str, str], int] = {}
    for uid in sorted(units):
        unit = units[uid]
        requires = unit.get("requires") or {}
        sources = {
            family_of(f)
            for f in (requires.get("all_of") or []) + (requires.get("any_of") or [])
        }
        targets = {family_of(f) for f in unit.get("yields") or []}
        for source in sources:
            for target in targets:
                tally[(source, target)] = tally.get((source, target), 0) + 1
    order = {name: i for i, (name, _, _) in enumerate(FAMILIES)}
    return [
        {"from": source, "to": target, "units": count}
        for (source, target), count in sorted(
            tally.items(), key=lambda kv: (order.get(kv[0][0], 9), order.get(kv[0][1], 9))
        )
    ]


def _index_by_fact(units: Dict[str, Any], pick) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for uid in sorted(units):
        for fact in pick(units[uid]) or []:
            out.setdefault(fact, []).append(uid)
    return out


def _embedded_files(unit_values: Iterable[Dict[str, Any]], root: Path) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Cards and mitigations travel with the units that name them.

    A card behind a link the reader cannot follow is a card they do not have.
    """
    cards: Dict[str, str] = {}
    mitigations: Dict[str, str] = {}
    for unit in unit_values:
        for key, store in (("card", cards), ("mitigation", mitigations)):
            rel = unit.get(key)
            if rel and rel not in store:
                path = root / rel
                if path.is_file():
                    store[rel] = path.read_text(encoding="utf-8")
    return cards, mitigations


def catalogue(root: Path) -> Dict[str, Any]:
    """Everything the page renders, in the shape the page reads it.

    Assembled here rather than in the template so that what the artefact
    contains is reviewable as data, so the derivations are testable without a
    browser, and so a second consumer can read the same structure.
    """
    repo = Repository.load(root)
    chain = Chain.load(root)

    topics = {d.data["id"]: _clean(d.data) for d in repo.topics}
    units = {d.data["id"]: _clean(d.data) for d in repo.units}
    facts = {f["id"]: _clean(f) for f in repo.vocab["facts"].data["facts"]}
    given = set(chain.given())

    cards, mitigations = _embedded_files(units.values(), root)
    payloads = {doc.data["id"]: _clean(doc.data) for doc in repo.payloads}

    standard = repo.standards["wstg"].data
    wstg = {e["id"]: e["title"] for e in standard["wstg"]}
    groups = wstg_groups(standard)

    # Which topics claim a test case, and which test cases a topic claims. One
    # identifier may be claimed by four topics in four domains, and the page has
    # to say so rather than pick one: WSTG-APIT-99 really is reconnaissance and
    # authorization and business logic and injection at once.
    claims: Dict[str, List[str]] = {}
    for tid in sorted(topics):
        for wid in (topics[tid].get("refs") or {}).get("wstg") or []:
            claims.setdefault(wid, []).append(tid)

    for tid, topic in topics.items():
        topic["units"] = unit_order(topic, units)
        topic["wstg"] = list((topic.get("refs") or {}).get("wstg") or [])
    for unit in units.values():
        parent = topics.get(unit.get("topic")) or {}
        # A unit's own refs win where it has them; otherwise it is filed under
        # the test case its topic claims, which is how it is reached.
        own = list((unit.get("refs") or {}).get("wstg") or [])
        unit["wstg"] = own or list(parent.get("wstg") or [])

    axes = {
        axis["name"]: {"universal": bool(axis.get("universal")), "slugs": _clean(axis["slugs"])}
        for axis in repo.vocab["axes"].data["axes"]
    }

    return {
        "version": __version__,
        "counts": coverage(root),
        "standard": {
            "id": "wstg",
            "name": "OWASP Web Security Testing Guide",
            "short": "WSTG",
            "source": standard["source"],
            "commit": standard["source_commit"],
            "retrieved": standard["retrieved"],
        },
        "groups": groups,
        "wstg": wstg,
        "claims": claims,
        # Test cases the domain map deliberately did not resolve to a domain:
        # not one test, or not a test at all. Shown as that rather than as a hole.
        "unresolved": sorted(
            e["id"] for e in repo.standards["wstg-map"].data["map"] if not e["domains"]
        ),
        # Topics with no test case in the standard. Empty while the catalogue
        # tracks WSTG exactly; the section exists so beyond-WSTG content has a
        # home the moment it is written, rather than being forced into one.
        "extensions": sorted(tid for tid, t in topics.items() if not t["wstg"]),
        "topics": topics,
        "units": units,
        "facts": facts,
        "axes": axes,
        "families": [
            {
                "name": name,
                "label": label,
                "note": note,
                "facts": sorted(f for f in facts if family_of(f) == name),
            }
            for name, label, note in FAMILIES
        ],
        "familyEdges": family_edges(units),
        "producers": _index_by_fact(units, lambda u: u.get("yields")),
        "requiredBy": _index_by_fact(
            units,
            lambda u: (u.get("requires") or {}).get("all_of", [])
            + (u.get("requires") or {}).get("any_of", []),
        ),
        "motivates": _index_by_fact(units, lambda u: u.get("motivated_by")),
        "chain": chain_index(units, given),
        "impacts": sorted(f for f in facts if family_of(f) == "impact"),
        "given": sorted(given),
        "granted": sorted(f for f, body in facts.items() if body.get("granted")),
        "cards": cards,
        "mitigations": mitigations,
        "payloads": payloads,
        "toolbox": {t["id"]: _clean(t) for doc in repo.toolbox for t in doc.data},
    }


def _sha256_source(text: str) -> str:
    """The CSP source expression naming one inline block by its content hash."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return "'sha256-" + base64.b64encode(digest).decode("ascii") + "'"


def content_security_policy(css: str, script: str, blob: str) -> str:
    """Deny everything, then name the three blocks this file actually contains.

    Hashes rather than `unsafe-inline`: the artefact is deterministic, so the
    exact bytes of each block are known at build time, and a policy that names
    them permits those three and nothing else -- including nothing a future
    change adds without rebuilding. `connect-src 'none'` is the one that carries
    the promise the file is published on: no request leaves it, whatever ends up
    embedded in the catalogue.

    The JSON block is data and no browser executes it, but `script-src` applies
    to `<script>` elements and enforcement of non-executable types has varied.
    Naming it costs one hash and removes the question.
    """
    inline = " ".join(
        sorted({_sha256_source(script), _sha256_source(blob)})
    )
    return "; ".join(
        (
            "default-src 'none'",
            "connect-src 'none'",
            f"script-src {inline}",
            f"style-src {_sha256_source(css)}",
            "img-src 'none'",
            "font-src 'none'",
            "media-src 'none'",
            "object-src 'none'",
            "frame-src 'none'",
            "worker-src 'none'",
            "manifest-src 'none'",
            "form-action 'none'",
            "base-uri 'none'",
            "frame-ancestors 'none'",
        )
    )


def _attribute(value: str) -> str:
    """Place a generated value in a double-quoted attribute, verbatim.

    The policy is assembled from fixed directives and base64 digests, so it can
    contain nothing that needs escaping -- and escaping it anyway would turn
    every `\'none\'` into an entity and make the one security control in the file
    unreadable to the person auditing it. Checked rather than trusted: if a
    future directive ever carries one of these, this raises instead of emitting
    a broken attribute.
    """
    if any(c in value for c in '<>&"'):
        raise ValueError(f"policy needs escaping and must not: {value!r}")
    return value


def render(data: Dict[str, Any]) -> str:
    """One file: the template, with the stylesheet, the script and the data in it."""
    template = (ARTEFACT_DIR / "template.html").read_text(encoding="utf-8")
    css = (ARTEFACT_DIR / "app.css").read_text(encoding="utf-8")
    script = (ARTEFACT_DIR / "app.js").read_text(encoding="utf-8")

    blob = json.dumps(data, separators=(",", ":"), sort_keys=True)
    # "</script>" inside a string would end the block early and leave the rest of
    # the catalogue rendering as markup. Escaping the slash keeps the JSON valid
    # and the parser inside the tag.
    blob = blob.replace("</", "<\\/")

    # The stylesheet and the script are this project's own files, not catalogue
    # content, and neither may contain a closing tag for the element it sits in.
    # Checked rather than assumed: a stylesheet that grew a `</style>` inside a
    # string would break the page open in exactly the way the escaping above
    # exists to prevent -- and would silently invalidate its own hash.
    if "</style" in css.lower():
        raise ValueError("app.css contains a closing style tag")
    if "</script" in script.lower():
        raise ValueError("app.js contains a closing script tag")

    # Order matters. The catalogue is content and goes in last, so a placeholder
    # appearing inside a unit's prose is text rather than an instruction.
    page = (
        template.replace("{{VERSION}}", html.escape(data["version"]))
        .replace("{{CSP}}", _attribute(content_security_policy(css, script, blob)))
        .replace("/*{{CSS}}*/", css)
        .replace("//{{JS}}", script)
        .replace("{{DATA}}", blob)
    )
    return page


def build(root: Path, target: Path) -> Path:
    target.write_text(render(catalogue(root)), encoding="utf-8")
    return target
