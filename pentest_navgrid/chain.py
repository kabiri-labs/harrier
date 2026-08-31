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
from typing import Any, Dict, Iterable, List, Set

from . import Repository


def family_of(fact: str) -> str:
    """The family a fact belongs to. It is the first segment of its identifier."""
    return fact.split(".", 1)[0]


#: Tiers, most specific first. An edge travelling through several facts takes the
#: most specific one any of them carries: a step that needs both a held session
#: and a captured token is reached by capturing the token, and filing it under
#: the session would hide it among the hundreds of other things a session opens.
TIER_ORDER = ("chain", "topic", "engagement")


def tier_of(facts: Iterable[str], tiers: Dict[str, str]) -> str:
    """The tier an edge through `facts` belongs to.

    A fact the caller knows nothing about counts as `chain`, which is the tier
    that stays visible. The schema makes `tier` required, so a gap here means a
    caller assembled the vocabulary itself rather than that data is missing --
    and of the two ways to be wrong, showing a generic prerequisite among the
    escalations costs a reader one line, while hiding a real escalation costs
    them the edge they came for.
    """
    seen = {tiers.get(fact, "chain") for fact in facts}
    for tier in TIER_ORDER:
        if tier in seen:
            return tier
    return "chain"


@dataclass
class Node:
    """One unit, with the facts it consumes and produces."""

    id: str
    title: str
    kind: str
    status: str
    #: Whether the topic's other units are steps beside this one or alternatives
    #: to it. Empty only for a unit assembled by a caller rather than loaded.
    role: str = ""
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


def chain_index(
    units: Dict[str, Any], given: Set[str], tiers: Dict[str, str] | None = None
) -> Dict[str, Dict[str, Any]]:
    """Per unit: what it needs, what success establishes, and what may follow.

    One implementation, read by both consumers. The edges are never unit-to-unit
    in the data: each one carries the capability it travels through, because the
    reason an edge exists is the only part of it a reader can act on.

    Each edge also carries the `tier` of the relation it represents, so the three
    different things this list has always held can be told apart by a reader
    instead of being printed under one heading.
    """
    tiers = tiers or {}
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
            # Both, not whichever came first. `kind` is decided by whether a hard
            # prerequisite exists; the tier is decided by the most specific fact
            # the edge travels through, and a consumer that requires a session
            # but is motivated by a captured token travels through both. Reading
            # only `via` there would file it under the session and hide exactly
            # the relation this field exists to surface.
            edge["tier"] = tier_of(edge["via"] + edge["hint"], tiers)
            edge["also"] = still_required(consumer, established, given)
            if not edge["hint"]:
                del edge["hint"]

        # Escalations first, then same-topic alternatives, then the generic
        # prerequisites -- and within a tier, hard continuations before hinted
        # ones and same-topic before the rest. Tier leads because it is the
        # question a reader is actually asking: of the ninety-odd things a held
        # session unlocks, the two that are escalations must not sort below the
        # ninety that are not.
        #
        # Deliberately *not* ranked by how little each still needs: that reads as
        # helpful and is not, because it sorts every continuation with unmet
        # conditions below the initial three and hides exactly the honesty this
        # view exists for.
        topic = unit.get("topic")
        outgoing = sorted(
            onward.values(),
            key=lambda e: (
                TIER_ORDER.index(e["tier"]),
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
                role=data.get("role", ""),
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

    def tiers(self) -> Dict[str, str]:
        """Each fact's tier, keyed by identifier."""
        return {fid: fact["tier"] for fid, fact in self.facts.items() if "tier" in fact}

    def index(self) -> Dict[str, Dict[str, Any]]:
        """The derivation, over this checkout's units."""
        return chain_index(self.units, self.given(), self.tiers())

    def charted(self) -> int:
        """How many units carry chain declarations at all."""
        return sum(1 for n in self.nodes.values() if n.requires or n.yields)

    def impacts(self) -> List[str]:
        """The terminal capabilities. Nothing may require one; the validator says so."""
        return sorted(fid for fid in self.facts if family_of(fid) == "impact")

    def dead_ends(self) -> List[str]:
        """Capabilities no unit declares a use for, **excluding impacts**.

        The exclusion is the whole point. Every impact is unconsumed by
        construction -- requiring one is rejected -- so counting impacts here
        would describe reaching an outcome as failing to continue to one, and
        would inflate the number by exactly the set already reported as where
        chains are *meant* to end.

        What is left is the honest measure: a capability some test establishes
        and nothing goes on to use. Not a defect in any one unit -- it is how far
        the chart reaches.
        """
        return sorted(
            fid
            for fid in self.facts
            if family_of(fid) != "impact"
            and not self.consumers.get(fid)
            and not self.motivates.get(fid)
        )

    def reach(self) -> Dict[str, int]:
        """How the tests divide by where their chain goes. A partition, and the
        four counts sum to the whole catalogue -- which is what stops any one of
        them from quietly meaning something else."""
        index = self.index()
        counts = {"continuation": 0, "impact": 0, "short": 0, "uncharted": 0}
        for edge in index.values():
            if not edge["yields"]:
                counts["uncharted"] += 1
            elif edge["out"]:
                counts["continuation"] += 1
            elif any(family_of(f) == "impact" for f in edge["yields"]):
                counts["impact"] += 1
            else:
                counts["short"] += 1
        return counts
