"""Validation: schema conformance, then the rules a schema cannot express.

Every pass collects problems rather than raising on the first one. A contributor
fixing a batch of files wants the whole list, not one line at a time -- and a
first-failure validator quietly trains people to fix one thing and re-run, which
is how the second and third problems in a file go unnoticed.

Each message names the file that caused it. A message that says only what is
wrong, without saying where, costs more time than it saves.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from . import SCHEMA_DIR, Document, HarrierError, Repository

#: Phrases that make an objective unfalsifiable. Nothing could contradict
#: "investigate the parameter", so it states no claim and cannot be a test.
VAGUE_OBJECTIVE = re.compile(
    r"\b(investigate|review|check whether things|look (?:at|into)|explore|"
    r"assess the security|ensure security|verify security)\b",
    re.IGNORECASE,
)

#: A completion criterion must be countable or enumerable. "Tested thoroughly"
#: records nothing, so it cannot answer the question the field exists for.
VAGUE_DONE = re.compile(
    r"\b(thoroughly|as (?:needed|appropriate)|properly|adequately|sufficiently|"
    r"where relevant|if necessary)\b",
    re.IGNORECASE,
)

#: An oracle that declines to state one. Forbidding the escape hatch is the
#: point: a rule with an accepted way out stops being a rule.
PLACEHOLDER = re.compile(r"^\s*(n/?a|not applicable|none|tbd|todo|-+)\s*\.?\s*$", re.IGNORECASE)

PLACEHOLDER_TOKEN = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")


class Problems:
    """Collected findings, in discovery order, each naming its source file."""

    def __init__(self) -> None:
        self.items: List[str] = []

    def add(self, where: Any, message: str) -> None:
        self.items.append(f"{where}: {message}")

    def __bool__(self) -> bool:
        return bool(self.items)

    def __len__(self) -> int:
        return len(self.items)


@lru_cache(maxsize=None)
def _load_schema(name: str) -> Dict[str, Any]:
    path = SCHEMA_DIR / f"{name}.schema.json"
    if not path.is_file():
        raise HarrierError(f"missing schema: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _best_error(errors: Iterable[Any]) -> Any:
    """Pick the error most likely to name the real cause.

    jsonschema reports every branch of a failed combinator. The deepest error is
    the one that got furthest into the document, which is almost always the one a
    reader needs; reporting the shallowest instead produces "does not match any
    of the expected shapes" against the whole file, which names nothing.
    """
    return max(errors, key=lambda e: (len(e.absolute_path), -len(str(e.message))))


@lru_cache(maxsize=None)
def _validator(name: str) -> Any:
    """The compiled validator for one schema, with every sibling resolvable.

    Shared rather than built per pass: the depth rule in `check_knowledge` asks
    the schema itself whether a document would be valid one tier up, which keeps
    the two definitions of a tier from drifting apart.
    """
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError as exc:  # pragma: no cover - environment problem, not data
        raise HarrierError(
            "jsonschema is required to validate (pip install jsonschema)"
        ) from exc

    resources = [
        (path.name, Resource.from_contents(json.loads(path.read_text("utf-8"))))
        for path in SCHEMA_DIR.glob("*.schema.json")
    ]
    return Draft202012Validator(
        _load_schema(name), registry=Registry().with_resources(resources)
    )


#: The tier above each one a unit can sit at. Absent from the map means the top:
#: there is nothing above `authored` for a unit to have grown into.
NEXT_TIER = {"outline": "sketched", "sketched": "authored"}


def check_schemas(repo: Repository, problems: Problems) -> None:
    """Pass 1 -- every document conforms to the schema its location selects."""
    for path in repo.unrecognised:
        if path.parent.name == "standards":
            problems.add(
                path,
                "no schema is registered for this standard -- add one to "
                "STANDARD_SCHEMAS rather than letting the file be trusted unchecked",
            )
        else:
            problems.add(
                path,
                "file under knowledge/ must be named <id>.topic.yaml or <id>.unit.yaml",
            )

    for schema_name, doc in repo.documents():
        errors = list(_validator(schema_name).iter_errors(doc.data))
        if not errors:
            continue
        err = _best_error(errors)
        location = "/".join(str(p) for p in err.absolute_path) or "<document>"
        problems.add(doc.rel, f"schema ({schema_name}) at {location}: {err.message}")


def _vocab(repo: Repository, name: str, key: str) -> Any:
    doc = repo.vocab.get(name)
    if doc is None:
        raise HarrierError(f"missing vocabulary: vocab/{name}.yaml")
    return doc.data.get(key)


def check_vocabularies(repo: Repository, problems: Problems) -> None:
    """Pass 2 -- the vocabularies are internally consistent.

    Everything downstream resolves against these, so a duplicate or a dangling
    reference here would be reported later as many failures with no obvious
    common cause.
    """
    domains = _vocab(repo, "domains", "domains")
    seen: Set[str] = set()
    for entry in domains:
        if entry["code"] in seen:
            problems.add("vocab/domains.yaml", f"duplicate domain code {entry['code']}")
        seen.add(entry["code"])

    axes = _vocab(repo, "axes", "axes")
    axis_names: Set[str] = set()
    for axis in axes:
        if axis["name"] in axis_names:
            problems.add("vocab/axes.yaml", f"duplicate axis {axis['name']}")
        axis_names.add(axis["name"])
    if not any(a.get("universal") for a in axes):
        problems.add(
            "vocab/axes.yaml",
            "no axis is marked universal; every topic needs one whose slugs it may "
            "always use, or recurring steps have nowhere to live",
        )

    surfaces = _vocab(repo, "surfaces", "surfaces")
    tags = {s["tag"] for s in surfaces}
    if len(tags) != len(surfaces):
        problems.add("vocab/surfaces.yaml", "duplicate surface tag")
    for surface in surfaces:
        for emitted in surface.get("emits") or []:
            if emitted not in tags:
                problems.add(
                    "vocab/surfaces.yaml",
                    f"{surface['tag']} emits unknown tag {emitted}",
                )
            if emitted == surface["tag"]:
                problems.add("vocab/surfaces.yaml", f"{surface['tag']} emits itself")

    seen_facts: Set[str] = set()
    for fact in _vocab(repo, "facts", "facts") or []:
        if fact["id"] in seen_facts:
            problems.add(
                "vocab/facts.yaml",
                f"duplicate fact {fact['id']} -- a fact is the meaning of a node "
                f"in the graph, and two entries for one id means one of the two "
                f"meanings is silently discarded",
            )
        seen_facts.add(fact["id"])

    for dim, body in (_vocab(repo, "dimensions", "dimensions") or {}).items():
        values = [v["value"] for v in body["values"]]
        if len(set(values)) != len(values):
            problems.add("vocab/dimensions.yaml", f"duplicate value in dimension {dim}")


def check_standards(repo: Repository, problems: Problems) -> None:
    """Pass 3 -- the pinned standard and the domain map agree with each other.

    The map is the project's claim that its domains partition the published
    standard. A map that has drifted from the pin makes that claim about a
    different document than the one it cites.
    """
    wstg = repo.standards.get("wstg")
    wmap = repo.standards.get("wstg-map")
    if wstg is None or wmap is None:
        problems.add("standards/", "both wstg.yaml and wstg-map.yaml are required")
        return

    pinned = {e["id"] for e in wstg.data["wstg"]}
    unverified = [e["id"] for e in wstg.data["wstg"] if not e["verified"]]
    if unverified:
        problems.add(
            "standards/wstg.yaml",
            f"{len(unverified)} identifier(s) marked unverified: {', '.join(sorted(unverified)[:5])}",
        )

    # Every identifier carries its group in its own prefix, so the two can be
    # checked against each other rather than trusted. A group with no
    # identifiers is a heading the standard no longer has; an identifier whose
    # group is undeclared would have no place to appear in the navigation and
    # would be silently unreachable, which is the failure this instrument exists
    # to prevent.
    groups = {g["code"] for g in wstg.data.get("groups") or []}
    if groups:
        seen = {wid.split("-")[1] for wid in pinned}
        for code in sorted(seen - groups):
            problems.add("standards/wstg.yaml", f"identifiers in group {code} but no group declares it")
        for code in sorted(groups - seen):
            problems.add("standards/wstg.yaml", f"group {code} is declared but no identifier belongs to it")
        counted = [g["code"] for g in wstg.data["groups"]]
        for code in sorted({c for c in counted if counted.count(c) > 1}):
            problems.add("standards/wstg.yaml", f"duplicate group {code}")

    domains = {d["code"] for d in _vocab(repo, "domains", "domains")}
    mapped: Set[str] = set()
    for entry in wmap.data["map"]:
        wid = entry["id"]
        if wid in mapped:
            problems.add("standards/wstg-map.yaml", f"duplicate entry for {wid}")
        mapped.add(wid)
        if wid not in pinned:
            problems.add("standards/wstg-map.yaml", f"{wid} is not in the pinned index")
        for code in entry["domains"]:
            if code not in domains:
                problems.add("standards/wstg-map.yaml", f"{wid} names undefined domain {code}")

    # Claims are (identifier, domain) pairs, not identifiers. An identifier that
    # resolved to two domains is two pieces of work, and checking presence alone
    # lets a topic in one domain mask the absence of the other -- which reports
    # full coverage over a hole, the one thing this instrument must never do.
    claimed: Set[tuple] = set()
    for topic in repo.topics:
        domain = topic.data.get("domain")
        for wid in (topic.data.get("refs") or {}).get("wstg") or []:
            claimed.add((wid, domain))

    resolvable = {e["id"] for e in wmap.data["map"] if e["domains"]}
    for entry in wmap.data["map"]:
        # An entry with no domains is one the ordered procedure deliberately did
        # not resolve -- it is not one test, or not a test at all. Requiring a
        # topic for it would force a topic that should not exist, and claiming
        # one is a modelling error rather than coverage.
        for code in entry["domains"]:
            if (entry["id"], code) not in claimed:
                problems.add(
                    "standards/wstg-map.yaml",
                    f"{entry['id']} is mapped to {code} but no {code} topic claims "
                    "it -- a resolved identifier with no topic is a coverage hole, "
                    "not a decision",
                )
    for wid, domain in sorted(claimed):
        if wid in pinned and wid not in resolvable:
            problems.add(
                f"knowledge/{str(domain).lower()}/",
                f"a topic claims {wid}, which the map resolves to no domain -- it "
                "is not one test, or not a test at all, so claiming it would count "
                "coverage the taxonomy does not have",
            )

    for wid in sorted(pinned - mapped):
        problems.add(
            "standards/wstg-map.yaml",
            f"{wid} is pinned but unmapped -- every published identifier must be "
            "resolved or explicitly recorded as unresolvable",
        )

    for entry in wmap.data["map"]:
        title = next((e["title"] for e in wstg.data["wstg"] if e["id"] == entry["id"]), None)
        if title is not None and entry["title"] != title:
            problems.add(
                "standards/wstg-map.yaml",
                f"{entry['id']} title has drifted from the pinned index",
            )


def check_knowledge(repo: Repository, problems: Problems) -> None:
    """Pass 4 -- identifiers, axis slugs and every cross-reference resolve.

    This is the pass the whole schema exists to make possible. A wrong identifier
    or a dangling reference reads perfectly well in a diff, which is exactly why
    it is checked mechanically rather than in review.
    """
    domains = {d["code"] for d in _vocab(repo, "domains", "domains")}
    axes = {a["name"]: set(a["slugs"]) for a in _vocab(repo, "axes", "axes")}
    universal: Set[str] = set()
    for axis in _vocab(repo, "axes", "axes"):
        if axis.get("universal"):
            universal |= set(axis["slugs"])
    surfaces = {s["tag"] for s in _vocab(repo, "surfaces", "surfaces")}
    dimensions = {
        name: {v["value"] for v in body["values"]}
        for name, body in (_vocab(repo, "dimensions", "dimensions") or {}).items()
    }
    pinned = {e["id"] for e in repo.standards["wstg"].data["wstg"]} if "wstg" in repo.standards else set()
    asvs = _asvs_shortcodes(repo)
    cwe = _cwe_index(repo)
    tools = {t["id"] for doc in repo.toolbox for t in doc.data}
    payload_files = {str(d.path.relative_to(repo.root)) for d in repo.payloads}

    topics: Dict[str, Document] = {}
    for doc in repo.topics:
        tid = doc.data.get("id")
        if not tid:
            continue  # the schema pass already reported the missing id
        expected = f"{tid}.topic.yaml"
        if doc.path.name != expected:
            problems.add(doc.rel, f"file name must be {expected} to match its id")
        if tid in topics:
            problems.add(doc.rel, f"duplicate topic id {tid}")
        topics[tid] = doc

        if tid.split("-")[1] != doc.data.get("domain"):
            problems.add(doc.rel, f"id domain segment does not match domain: {doc.data.get('domain')}")
        if doc.data.get("domain") not in domains:
            problems.add(doc.rel, f"unknown domain {doc.data.get('domain')}")
        directory = doc.path.parent.name
        if doc.data.get("domain") and directory != doc.data["domain"].lower():
            problems.add(doc.rel, f"filed under knowledge/{directory}/ but declares domain {doc.data['domain']}")
        if doc.data.get("axis") is not None and doc.data["axis"] not in axes:
            problems.add(doc.rel, f"unknown axis {doc.data['axis']}")
        _check_surface_clause(doc, doc.data.get("surfaces"), surfaces, problems)
        _check_dimensions(doc, doc.data.get("dimensions"), dimensions, problems)
        _check_refs(doc, doc.data.get("refs"), pinned, asvs, cwe, problems)

    units: Dict[str, Document] = {}
    by_topic: Dict[str, List[str]] = {}
    for doc in repo.units:
        uid = doc.data.get("id")
        if not uid:
            continue  # the schema pass already reported the missing id
        expected = f"{uid}.unit.yaml"
        if doc.path.name != expected:
            problems.add(doc.rel, f"file name must be {expected} to match its id")
        if uid in units:
            problems.add(doc.rel, f"duplicate unit id {uid}")
        units[uid] = doc

        parent = doc.data.get("topic")
        if parent not in topics:
            problems.add(doc.rel, f"topic {parent} does not exist")
            continue
        by_topic.setdefault(parent, []).append(uid)
        if not uid.startswith(parent + "-"):
            problems.add(doc.rel, f"id must begin with its topic {parent}")
            continue

        slug = uid[len(parent) + 1 :]
        axis = topics[parent].data.get("axis")
        allowed = (axes.get(axis, set()) if axis else set()) | universal
        if slug not in allowed:
            named = f"the {axis} vocabulary or the universal one" if axis else "any universal vocabulary"
            problems.add(
                doc.rel,
                f"slug {slug} is not in {named} -- a unit may not invent a name, "
                "which is what stops two topics naming one idea differently",
            )

        objective = doc.data.get("objective", "")
        if VAGUE_OBJECTIVE.search(objective):
            problems.add(doc.rel, "objective is not falsifiable: nothing could contradict it")
        done = doc.data.get("done_when")
        if done and VAGUE_DONE.search(done):
            problems.add(doc.rel, "done_when is not countable or enumerable")
        oracle = doc.data.get("oracle") or {}
        for field, text in oracle.items():
            if PLACEHOLDER.match(str(text)):
                problems.add(doc.rel, f"oracle.{field} is a placeholder, not an oracle")

        # Depth is asked of the schema rather than restated here: a unit is
        # stale exactly when it would still validate one tier up. Restating the
        # contract in Python would give two definitions of "sketched" that
        # drift, and the one nobody reads would be the one deciding the figures.
        status = doc.data.get("status", "authored")
        higher = NEXT_TIER.get(status)
        if higher and not list(_validator("unit").iter_errors({**doc.data, "status": higher})):
            problems.add(
                doc.rel,
                f"marked {status} but carries everything the {higher} tier "
                f"requires -- a stale status makes the depth figures wrong",
            )

        payloads = doc.data.get("payloads")
        if payloads and payloads not in payload_files:
            problems.add(doc.rel, f"payload file {payloads} does not exist")
        for tool in doc.data.get("tools") or []:
            if tool not in tools:
                problems.add(doc.rel, f"unknown tool {tool}")
        for target in ("card", "mitigation"):
            rel = doc.data.get(target)
            if rel and not (repo.root / rel).is_file():
                problems.add(doc.rel, f"{target} {rel} does not exist")
        _check_surface_clause(doc, doc.data.get("surfaces"), surfaces, problems)
        _check_dimensions(doc, doc.data.get("dimensions"), dimensions, problems)
        _check_refs(doc, doc.data.get("refs"), pinned, asvs, cwe, problems)

    for tid, doc in topics.items():
        for target in doc.data.get("see_also") or []:
            if target not in topics:
                problems.add(doc.rel, f"see_also names unknown topic {target}")
            elif tid not in (topics[target].data.get("see_also") or []):
                problems.add(
                    doc.rel,
                    f"see_also {target} is not returned -- a cross-reference is a "
                    "peer relationship, and a reader arriving at the other topic "
                    "would never learn this one exists. If the relationship really "
                    "runs one way, it is a boundary, not a see_also",
                )
        for boundary in doc.data.get("boundaries") or []:
            home = boundary.get("home")
            if home is not None and home not in topics:
                problems.add(doc.rel, f"boundary home {home} does not exist")
        # A declared axis must do work. If no unit draws from it, the
        # declaration constrains nothing and misdescribes the topic; the honest
        # form is to omit it, which the schema allows.
        axis = doc.data.get("axis")
        children = by_topic.get(tid, [])
        if axis and children:
            own = axes.get(axis, set()) - universal
            if own and not any(c.rsplit("-", 1)[1] in own for c in children):
                problems.add(
                    doc.rel,
                    f"declares axis {axis} but no unit draws a slug from it -- omit "
                    "the axis rather than declaring one that constrains nothing",
                )

        order = doc.data.get("order")
        if order is not None:
            children = set(by_topic.get(tid, []))
            for uid in order:
                if uid not in children:
                    problems.add(doc.rel, f"order names {uid}, which is not a unit of this topic")
            for uid in sorted(children - set(order)):
                problems.add(
                    doc.rel,
                    f"unit {uid} is missing from order -- a unit no ordering reaches "
                    "is a silent coverage hole, not a harmless leftover",
                )


def _cwe_index(repo: Repository) -> Dict[int, Dict[str, Any]]:
    """Every identifier in the pinned CWE catalogue, keyed by number.

    Categories and views are included alongside weaknesses so that citing one can
    be rejected with a message that says why. CWE-699 is a category and CWE-1000
    is a view; both are real identifiers, so "not found" would be a misleading
    thing to say about either.
    """
    doc = repo.standards.get("cwe")
    if doc is None:
        return {}
    return {entry["id"]: entry for entry in doc.data["cwe"]}


def _asvs_shortcodes(repo: Repository) -> Set[str]:
    """Every requirement identifier in the pinned ASVS release.

    Chapter and section shortcodes are included: a mitigation that cites a whole
    section is a legitimate and often more honest reference than one that cites a
    single requirement it only partly satisfies.
    """
    doc = repo.standards.get("asvs")
    if doc is None:
        return set()
    codes: Set[str] = set()
    for chapter in doc.data["asvs"]:
        codes.add(chapter["shortcode"])
        for section in chapter["sections"]:
            codes.add(section["shortcode"])
            for requirement in section["requirements"]:
                codes.add(requirement["shortcode"])
    return codes


def _check_surface_clause(doc: Document, clause: Any, surfaces: Set[str], problems: Problems) -> None:
    if not clause:
        return
    for key in ("any_of", "all_of", "none_of"):
        for tag in clause.get(key) or []:
            if tag not in surfaces:
                problems.add(doc.rel, f"surfaces.{key} names unknown tag {tag}")


def _check_dimensions(doc: Document, declared: Any, known: Dict[str, Set[str]], problems: Problems) -> None:
    for name, values in (declared or {}).items():
        if name not in known:
            problems.add(doc.rel, f"unknown dimension {name}")
            continue
        for value in values:
            if value not in known[name]:
                problems.add(doc.rel, f"dimension {name} has no value {value}")


def _check_refs(
    doc: Document,
    refs: Any,
    pinned: Set[str],
    asvs: Set[str],
    cwe: Dict[int, Dict[str, Any]],
    problems: Problems,
) -> None:
    for wid in (refs or {}).get("wstg") or []:
        if wid not in pinned:
            problems.add(
                doc.rel,
                f"{wid} is not in the pinned index -- verify it against the source "
                "rather than writing it from memory",
            )
    for shortcode in (refs or {}).get("asvs") or []:
        if shortcode not in asvs:
            problems.add(
                doc.rel,
                f"{shortcode} is not in the pinned ASVS index -- a citation nobody "
                "can check reads as evidence while being none",
            )
    for number in (refs or {}).get("cwe") or []:
        entry = cwe.get(number)
        if entry is None:
            problems.add(doc.rel, f"CWE-{number} is not in the pinned CWE catalogue")
        elif entry["kind"] != "weakness":
            problems.add(
                doc.rel,
                f"CWE-{number} is a {entry['kind']} ({entry['name']}), not a weakness "
                "-- refs.cwe names the weakness a unit finds, not the grouping it sits in",
            )
        elif entry["status"] == "Deprecated":
            problems.add(
                doc.rel,
                f"CWE-{number} is deprecated in the pinned catalogue; cite its replacement",
            )


def check_payloads(repo: Repository, problems: Problems) -> None:
    """Pass 5 -- payload templates are copy-and-run, and their selectors resolve.

    Both directions of the variable rule are checked. An undeclared placeholder
    leaves an entry that cannot be filled in; a declared-but-unused one is what a
    renamed placeholder leaves behind, and it reads as if something still uses it.
    """
    dimensions = {
        name: {v["value"] for v in body["values"]}
        for name, body in (_vocab(repo, "dimensions", "dimensions") or {}).items()
    }
    seen: Dict[str, str] = {}
    for doc in repo.payloads:
        declared = set(doc.data.get("variables") or [])
        used: Set[str] = set()
        pid = doc.data.get("id")
        if pid in seen:
            problems.add(doc.rel, f"payload id {pid} is already used by {seen[pid]}")
        seen[pid] = doc.rel

        for entry in doc.data["entries"]:
            used |= set(PLACEHOLDER_TOKEN.findall(entry["payload"]))
            for key, value in entry.items():
                if key in ("name", "payload", "detect", "note"):
                    continue
                if key not in dimensions:
                    problems.add(doc.rel, f"entry {entry['name']!r} selects on unknown dimension {key}")
                    continue
                for val in value:
                    if val not in dimensions[key]:
                        problems.add(
                            doc.rel,
                            f"entry {entry['name']!r}: dimension {key} has no value {val}",
                        )
        for name in sorted(used - declared):
            problems.add(doc.rel, f"payload uses undeclared variable {{{{{name}}}}}")
        for name in sorted(declared - used):
            problems.add(doc.rel, f"variable {name} is declared but never used")


def check_toolbox(repo: Repository, problems: Problems) -> None:
    """Pass 6 -- tool ids are unique and every explained flag is actually used.

    A rationale for a flag the command does not carry is the residue of an edited
    invocation, and it is indistinguishable from advice.

    Only keys that look like flags are checked. Some tools in this registry are
    interactive, and their entries explain a technique ("paired tabs", "ten
    repetitions") rather than a command-line token; requiring those to appear in
    a command would force the rationale out of the one place it is written.
    """
    seen: Set[str] = set()
    for doc in repo.toolbox:
        for tool in doc.data:
            if tool["id"] in seen:
                problems.add(doc.rel, f"duplicate tool id {tool['id']}")
            seen.add(tool["id"])
            for inv in tool["invocations"]:
                for flag in (inv.get("flags") or {}):
                    if not flag.startswith("-"):
                        continue
                    # A key names the flag and may qualify it -- "-w with
                    # time_total" explains which use of -w is meant. The flag is
                    # the first token; the rest is the explanation continuing
                    # into the key, which is worth keeping.
                    token = re.split(r"[=\s]", flag, maxsplit=1)[0]
                    if token not in inv["cmd"] and flag not in inv["cmd"]:
                        problems.add(
                            doc.rel,
                            f"{tool['id']}: flag {flag!r} is explained but not used in the command",
                        )


def check_chain(repo: Repository, problems: Problems) -> None:
    """Pass 7 -- the attack chain resolves, and its facts mean one thing each.

    The chain is derived, never stored: a unit leads to another exactly when it
    yields a fact that one requires. That makes the fact vocabulary the only
    place the graph can break, so it is the place that is checked.
    """
    facts = {f["id"]: f for f in (_vocab(repo, "facts", "facts") or [])}
    referenced: Set[str] = set()
    producers: Dict[str, List[str]] = {}
    for doc in repo.units:
        for name in doc.data.get("yields") or []:
            producers.setdefault(name, []).append(doc.data["id"])

    for doc in repo.units:
        data = doc.data
        requires = data.get("requires") or {}
        declared = {
            "requires": [*(requires.get("all_of") or []), *(requires.get("any_of") or [])],
            "motivated_by": data.get("motivated_by") or [],
            "yields": data.get("yields") or [],
            "closes": data.get("closes") or [],
        }
        for field, names in declared.items():
            for name in names:
                referenced.add(name)
                if name not in facts:
                    problems.add(
                        doc.rel,
                        f"{field} names unknown fact {name} -- a fact outside "
                        f"vocab/facts.yaml disconnects the graph instead of extending it",
                    )

        required = set(declared["requires"])
        produced = set(declared["yields"])

        for name in sorted(required & produced):
            problems.add(
                doc.rel,
                f"requires and yields both name {name} -- a unit that needs its "
                f"own result cannot be reached",
            )

        for name in sorted(n for n in required if n.startswith("impact.")):
            problems.add(
                doc.rel,
                f"requires {name}: an impact is where a chain ends, so nothing "
                f"may be conditioned on one",
            )

        for name in sorted(set(declared["closes"]) - produced):
            problems.add(
                doc.rel,
                f"closes {name} without yielding it -- a negative result can only "
                f"rule out what a positive one would have established",
            )

        for name in sorted(set(declared["closes"]) & produced):
            others = [u for u in producers.get(name, []) if u != data["id"]]
            if others:
                problems.add(
                    doc.rel,
                    f"closes {name}, which {len(others)} other unit(s) also "
                    f"establish -- a clean result here rules out this route and "
                    f"not the fact, so closing it hides the routes that are left",
                )

        if data.get("status") == "authored" and data.get("kind", "test") != "inquiry" and not produced:
            problems.add(
                doc.rel,
                "authored without yields -- a unit that establishes nothing "
                "cannot be reached from anywhere, and leads nowhere",
            )

    for name, fact in sorted(facts.items()):
        if name not in referenced:
            problems.add(
                "vocab/facts.yaml",
                f"{name} is declared but no unit requires, yields or is motivated by "
                f"it -- an unreachable fact is vocabulary nobody can use",
            )
            continue
        if fact.get("given") or fact.get("granted") or producers.get(name):
            continue
        problems.add(
            "vocab/facts.yaml",
            f"{name} is required but no unit establishes it, and it is neither "
            f"given nor granted -- a condition with no producer is a hole in the "
            f"chain, and it reads from the outside exactly like a route nobody "
            f"has taken yet",
        )


def check_standard_index(repo: Repository, problems: Problems) -> None:
    """Pass 8 -- the generated index resolves, like every other reference.

    The index earns its place by being reviewable, and a file nobody resolves is
    not reviewable -- it is a second copy of the catalogue that can disagree with
    the first while still passing every check. The schema constrains the *shape*
    of an identifier, which a renamed topic satisfies perfectly on its way to
    pointing at nothing.

    Staleness itself is not reported here. `harrier index --check` answers that,
    and it answers it exactly: a byte comparison against a fresh derivation. What
    this pass refuses is the narrower and worse case -- an index naming something
    the catalogue does not contain, which is the state a rename leaves behind and
    the one a reader is least likely to suspect.
    """
    index = repo.standards.get("wstg-index")
    if index is None:
        return

    path = "standards/wstg-index.yaml"
    pinned = {e["id"] for e in repo.standards["wstg"].data["wstg"]} if repo.standards.get("wstg") else set()
    topics = {doc.data["id"] for doc in repo.topics}
    units = {doc.data["id"] for doc in repo.units}

    # A row the schema already rejected is skipped rather than read. Pass 1 has
    # recorded what is wrong with it, and reaching into it here would raise
    # instead of adding a problem -- which loses every finding collected so far
    # and hands a reader a traceback in place of the error that was already
    # waiting for them. Reporting it twice would be the milder version of the
    # same mistake.
    rows = index.data.get("cases")
    seen = set()
    unreadable = not isinstance(rows, list)
    for case in rows if isinstance(rows, list) else []:
        if not isinstance(case, dict):
            unreadable = True
            continue
        wid = case.get("id")
        if not isinstance(wid, str):
            unreadable = True
            continue
        if wid in seen:
            problems.add(path, f"{wid} appears twice")
        seen.add(wid)
        if pinned and wid not in pinned:
            problems.add(path, f"{wid} is not in the pinned standard")
        named_topics = case.get("topics")
        named_units = case.get("units")
        for tid in named_topics if isinstance(named_topics, list) else []:
            if tid not in topics:
                problems.add(path, f"{wid} names topic {tid}, which does not exist")
        for uid in named_units if isinstance(named_units, list) else []:
            if uid not in units:
                problems.add(path, f"{wid} names unit {uid}, which does not exist")
        depths = [case.get("authored"), case.get("sketched"), case.get("outline")]
        if isinstance(named_units, list) and all(isinstance(n, int) for n in depths):
            counted = sum(depths)
            if counted != len(named_units):
                problems.add(
                    path,
                    f"{wid} counts {counted} unit(s) by depth but lists "
                    f"{len(named_units)}",
                )

    # Every pinned identifier gets a row. A row that vanished when coverage was
    # lost would leave the file shorter and still looking complete, which is the
    # one way this document could mislead rather than simply be wrong. Skipped
    # where the file's shape is already in question: a malformed `cases` would
    # otherwise report all 109 identifiers as missing and bury the real fault.
    if not unreadable:
        for wid in sorted(pinned - seen):
            problems.add(path, f"{wid} is pinned but has no row in the index")


PASSES = (
    check_schemas,
    check_vocabularies,
    check_standards,
    check_knowledge,
    check_payloads,
    check_toolbox,
    check_chain,
    check_standard_index,
)


def validate(root: Path) -> Problems:
    """Run every pass over one checkout and return everything found."""
    problems = Problems()
    repo = Repository.load(root)
    for pass_fn in PASSES:
        pass_fn(repo, problems)
    return problems


def coverage(root: Path) -> Dict[str, int]:
    """Counts for the roadmap. Asserted by the suite so they cannot go stale."""
    repo = Repository.load(root)
    wmap = repo.standards["wstg-map"].data["map"]
    covered = {
        wid
        for doc in repo.topics
        for wid in (doc.data.get("refs") or {}).get("wstg") or []
    }
    coverable = {e["id"] for e in wmap if e["domains"]}
    # Intersected rather than counted raw: a topic claiming an unresolvable
    # identifier is rejected by the validator, but the count must not be able to
    # exceed its own denominator even for a moment.
    covered &= coverable
    return {
        "wstg_coverable": len(coverable),
        "topics": len(repo.topics),
        "units": len(repo.units),
        # Compared against the tier by name rather than "not outline": with a
        # third tier in the middle, the negation would have quietly counted
        # every sketch as written to full depth -- and this figure is published
        # in the README, the roadmap and the artefact.
        "units_sketched": sum(1 for d in repo.units if d.data.get("status") == "sketched"),
        "units_authored": sum(
            1 for d in repo.units if d.data.get("status", "authored") == "authored"
        ),
        # The number the chain pass is judged on: a unit with neither field is
        # in the catalogue but not in the graph, which is invisible in every
        # other count here.
        "units_charted": sum(
            1 for d in repo.units if d.data.get("requires") or d.data.get("yields")
        ),
        "wstg_pinned": len(repo.standards["wstg"].data["wstg"]),
        "wstg_mapped": len(wmap),
        "wstg_covered": len(covered),
    }
