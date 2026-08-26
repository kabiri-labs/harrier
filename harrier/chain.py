"""The attack chain, derived from the facts units declare.

Nothing here is stored in the repository. A unit says what must already be true
for it to be possible and what becomes true when it succeeds; the edges follow.
Writing the edges down instead would mean maintaining several hundred of them by
hand, and a stale edge is worse than a missing one -- it reads as a route that
was checked.

The graph is deliberately bipartite: units and facts alternate. Projecting it
down to unit-to-unit edges loses the reason an edge exists, which is the one
thing the reader needs to see.

**Everything here is generic.** An edge says *if A succeeds, B may become
relevant* -- never that B is now possible, and never anything about a target.
This module has no notion of what anybody holds, because the product does not:
see docs/PIVOT.md. Both the command line and the published artefact read the
derivation below, so the two cannot drift into describing different models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set

from . import Repository


def family_of(fact: str) -> str:
    """The family a fact belongs to. It is the first segment of its identifier."""
    return fact.split(".", 1)[0]


@dataclass
class Node:
    """One unit, with the facts it consumes and produces."""

    id: str
    title: str
    kind: str
    status: str
    topic: str = ""
    all_of: List[str] = field(default_factory=list)
    any_of: List[str] = field(default_factory=list)
    motivated_by: List[str] = field(default_factory=list)
    yields: List[str] = field(default_factory=list)

    @property
    def requires(self) -> List[str]:
        return [*self.all_of, *self.any_of]


def still_required(
    consumer: Dict[str, Any], established: Set[str], given: Set[str]
) -> Dict[str, List[str]]:
    """What a downstream unit declares that succeeding here does not supply.

    The honest half of a continuation. A unit reached because it consumes a fact
    this one establishes may declare three others as well, and showing the edge
    without them reads as *do this next* when the truth is *this is one of the
    conditions*. `given` facts are the roots of the graph and are not listed:
    naming them would bury the conditions that matter under the ones that always
    hold.

    `granted` facts are deliberately *not* treated as satisfied. An engagement
    may supply host access and usually does not, so a unit needing it is still
    waiting on something the reader has to recognise as theirs to have or not.
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

    One implementation, read by both consumers. The edges are never unit-to-unit
    in the data: each one carries the capability it travels through, because the
    reason an edge exists is the only part of it a reader can act on.
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
            edge["also"] = still_required(consumer, established, given)
            if not edge["hint"]:
                del edge["hint"]

        # Hard continuations first, then the ones in the same topic, then by
        # identifier. Deliberately *not* ranked by how little each still needs:
        # that reads as helpful and is not, because it sorts every continuation
        # with unmet conditions below the initial three and hides exactly the
        # honesty this view exists for.
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


@dataclass
class Chain:
    """Every unit and fact in one checkout, indexed both ways."""

    nodes: Dict[str, Node] = field(default_factory=dict)
    facts: Dict[str, dict] = field(default_factory=dict)
    #: The unit documents as loaded, so the derivation runs on the same shape the
    #: artefact builder passes it and there is only one implementation of it.
    units: Dict[str, dict] = field(default_factory=dict)
    #: fact id -> units that produce it
    producers: Dict[str, List[str]] = field(default_factory=dict)
    #: fact id -> units that declare it a hard condition
    consumers: Dict[str, List[str]] = field(default_factory=dict)
    #: fact id -> units it makes worth reaching for sooner
    motivates: Dict[str, List[str]] = field(default_factory=dict)

    @classmethod
    def load(cls, root: Path) -> "Chain":
        repo = Repository.load(root)
        chain = cls()
        facts_doc = repo.vocab.get("facts")
        for fact in (facts_doc.data.get("facts") if facts_doc else None) or []:
            chain.facts[fact["id"]] = fact
        for doc in repo.units:
            data = doc.data
            requires = data.get("requires") or {}
            node = Node(
                id=data["id"],
                title=data["title"],
                kind=data.get("kind", "test"),
                status=data.get("status", "authored"),
                topic=data.get("topic", ""),
                all_of=list(requires.get("all_of") or []),
                any_of=list(requires.get("any_of") or []),
                motivated_by=list(data.get("motivated_by") or []),
                yields=list(data.get("yields") or []),
            )
            chain.nodes[node.id] = node
            chain.units[node.id] = data
            for fact in node.yields:
                chain.producers.setdefault(fact, []).append(node.id)
            for fact in node.requires:
                chain.consumers.setdefault(fact, []).append(node.id)
            for fact in node.motivated_by:
                chain.motivates.setdefault(fact, []).append(node.id)
        return chain

    def given(self) -> Set[str]:
        """The facts an engagement supplies rather than a test earning them."""
        return {fid for fid, fact in self.facts.items() if fact.get("given")}

    def index(self) -> Dict[str, Dict[str, Any]]:
        """The derivation, over this checkout's units."""
        return chain_index(self.units, self.given())

    def charted(self) -> int:
        """How many units carry chain declarations at all."""
        return sum(1 for n in self.nodes.values() if n.requires or n.yields)

    def unconsumed(self) -> List[str]:
        """Capabilities no unit declares a use for.

        Not a defect in any one unit: it is how far the chart reaches. Each is
        where some chain currently stops, and the count is the honest measure of
        how much of the graph runs all the way through to an impact.
        """
        return sorted(
            fid
            for fid in self.facts
            if not self.consumers.get(fid) and not self.motivates.get(fid)
        )
