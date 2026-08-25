"""The attack chain, derived from the facts units declare.

Nothing here is stored in the repository. A unit says what must already be true
for it to be possible and what becomes true when it succeeds; the edges follow.
Writing the edges down instead would mean maintaining several hundred of them by
hand, and a stale edge is worse than a missing one -- it reads as a route that
was checked.

The graph is deliberately bipartite: units and facts alternate. Projecting it
down to unit-to-unit edges loses the reason an edge exists, which is the one
thing the tester needs to see.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set

from . import Repository


@dataclass
class Node:
    """One unit, with the facts it consumes and produces."""

    id: str
    title: str
    kind: str
    status: str
    all_of: List[str] = field(default_factory=list)
    any_of: List[str] = field(default_factory=list)
    motivated_by: List[str] = field(default_factory=list)
    yields: List[str] = field(default_factory=list)

    @property
    def requires(self) -> List[str]:
        return [*self.all_of, *self.any_of]

    def reachable_with(self, held: Set[str]) -> bool:
        """True when every hard condition is met by the facts in hand.

        `any_of` is satisfied by one member, `all_of` by every member. A unit
        declaring neither is reachable from the start, which is the correct
        reading: it needs nothing.
        """
        if any(fact not in held for fact in self.all_of):
            return False
        if self.any_of and not any(fact in held for fact in self.any_of):
            return False
        return True


@dataclass
class Chain:
    """Every unit and fact in one checkout, indexed both ways."""

    nodes: Dict[str, Node] = field(default_factory=dict)
    facts: Dict[str, dict] = field(default_factory=dict)
    #: fact id -> units that produce it
    producers: Dict[str, List[str]] = field(default_factory=dict)
    #: fact id -> units that need it
    consumers: Dict[str, List[str]] = field(default_factory=dict)

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
                all_of=list(requires.get("all_of") or []),
                any_of=list(requires.get("any_of") or []),
                motivated_by=list(data.get("motivated_by") or []),
                yields=list(data.get("yields") or []),
            )
            chain.nodes[node.id] = node
            for fact in node.yields:
                chain.producers.setdefault(fact, []).append(node.id)
            for fact in node.requires:
                chain.consumers.setdefault(fact, []).append(node.id)
        return chain

    def given(self) -> Set[str]:
        """The facts an engagement supplies rather than a test earning them."""
        return {fid for fid, fact in self.facts.items() if fact.get("given")}

    def available(self, held: Set[str]) -> List[Node]:
        """Units the held facts put within reach, minus those with nothing left to give.

        A unit that declares no chain data is reachable: it states no condition,
        so there is none to fail. That is the honest reading while the catalogue
        is only partly charted -- treating an undeclared unit as unreachable
        would hide most of the taxonomy behind a field it has not been given yet.
        """
        return sorted(
            (
                node
                for node in self.nodes.values()
                if node.reachable_with(held)
                and not (node.yields and set(node.yields) <= held)
            ),
            key=lambda n: n.id,
        )

    def next_after(self, unit_id: str) -> Dict[str, List[Node]]:
        """What a positive result here opens up.

        Two answers, kept apart because they mean different things to whoever is
        deciding what to do next: `unlocks` was impossible before and is possible
        now, `motivates` was always possible and has just become worth doing.
        """
        node = self.nodes[unit_id]
        opened = set(node.yields)
        unlocked: Dict[str, Node] = {}
        # Each alternative in `any_of` is a different way to have reached this
        # unit, and they leave the tester holding different facts. Pooling them
        # into one `before` set would assume every alternative was held at once,
        # which suppresses exactly the units that the alternative not taken would
        # have reached anyway. So each is evaluated on its own and the results
        # are unioned.
        for choice in node.any_of or [None]:
            before = self.given() | set(node.all_of) | ({choice} if choice else set())
            after = before | opened
            for candidate in self.available(after):
                if candidate.id == unit_id or candidate.reachable_with(before):
                    continue
                unlocked[candidate.id] = candidate
        unlocks = sorted(unlocked.values(), key=lambda n: n.id)
        motivates = [
            n
            for n in self.nodes.values()
            if n.id != unit_id
            and opened & set(n.motivated_by)
            and n.id not in unlocked
        ]
        return {"unlocks": unlocks, "motivates": sorted(motivates, key=lambda n: n.id)}

    def charted(self) -> int:
        """How many units carry chain declarations at all."""
        return sum(1 for n in self.nodes.values() if n.requires or n.yields)
