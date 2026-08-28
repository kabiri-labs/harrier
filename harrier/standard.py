"""The link between a standard's test cases and the units that cover them.

The catalogue holds this relation on the topic: `refs.wstg` names the test cases
a topic claims. Read in that direction it answers "what does this topic cover",
which is the question an author has. The question a *tester* has is the other
one -- "my scope sheet says WSTG-INPV-05, what am I opening" -- and nothing in
the repository answered it. It was derivable, and derivable is not the same as
available: it existed only inside the built artefact, so it could not be
inspected in a diff, checked in CI, or reached from a terminal.

The relation is many-to-many in both directions, which is why it needs writing
down rather than assuming. Thirteen topics claim more than one test case, and
five test cases are spread across more than one topic -- WSTG-APIT-99 across
four domains, because it really is reconnaissance and authorization and business
logic and injection at once. A representation that had to pick one would be
wrong five times.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from . import Repository

#: The generated file, relative to the repository root.
INDEX_PATH = Path("standards") / "wstg-index.yaml"

#: Written into the file so a reader who opens it knows it is not hand-kept.
GENERATED_BY = "harrier index"


@dataclass
class Case:
    """One test case of the standard, and everything filed under it."""

    id: str
    title: str
    #: Topics claiming this case, in identifier order.
    topics: List[str] = field(default_factory=list)
    #: Units reached through those topics, in the order each topic declares.
    units: List[str] = field(default_factory=list)
    authored: int = 0
    sketched: int = 0
    outline: int = 0
    #: Whether the domain map resolved this case to a domain at all. A case it
    #: deliberately did not -- rule 0 in `wstg-map.yaml` -- is not a gap in
    #: coverage, and reporting it as one turns a decision somebody made and
    #: wrote down into a task nobody can close.
    resolvable: bool = True
    #: Why, when it is not. Carried from the map so the reason travels with the
    #: row rather than living one file away.
    note: str = ""

    @property
    def covered(self) -> bool:
        return bool(self.topics)


def _units_of(topic: Dict[str, Any], units: Dict[str, Any]) -> List[str]:
    """A topic's units in its declared order, then any it failed to list.

    The order is the tester-facing one and is preserved. A unit missing from
    `order` is a validator failure elsewhere; here it is appended rather than
    dropped, because an index that silently omits a test is worse than one that
    shows the catalogue is inconsistent.
    """
    declared = [uid for uid in (topic.get("order") or []) if uid in units]
    rest = sorted(
        uid for uid, unit in units.items()
        if unit.get("topic") == topic["id"] and uid not in declared
    )
    return declared + rest


def _own_refs(unit: Dict[str, Any]) -> List[str]:
    """The test cases a unit names for itself, if it names any.

    A unit's own `refs.wstg` wins over its topic's, which is what `build.py`
    already does for the artefact. The index has to agree with it: two
    derivations of the same relation that disagree are worse than one, because
    a reader has no way to tell which they are looking at.
    """
    return list((unit.get("refs") or {}).get("wstg") or [])


def cases(repo: Repository) -> Dict[str, Case]:
    """Every pinned test case, with the topics and units that cover it."""
    units = {doc.data["id"]: doc.data for doc in repo.units}
    topics = {doc.data["id"]: doc.data for doc in repo.topics}

    out: Dict[str, Case] = {}
    for entry in repo.standards["wstg"].data["wstg"]:
        out[entry["id"]] = Case(id=entry["id"], title=entry["title"])

    for entry in repo.standards["wstg-map"].data["map"]:
        case = out.get(entry["id"])
        if case is not None and not entry.get("domains"):
            case.resolvable = False
            case.note = entry.get("note", "")

    for tid in sorted(topics):
        topic = topics[tid]
        claimed = (topic.get("refs") or {}).get("wstg") or []
        for wid in claimed:
            case = out.get(wid)
            if case is None:
                # A claim on an identifier the pinned standard does not carry.
                # The validator rejects it; the index does not invent a row for
                # it, because a row here would read as coverage.
                continue
            case.topics.append(tid)
            for uid in _units_of(topic, units):
                own = _own_refs(units[uid])
                if own and wid not in own:
                    # The unit names its own cases and this is not one of them.
                    continue
                if uid not in case.units:
                    case.units.append(uid)

    # A unit may name a case its topic does not claim. Filing it only through
    # the topic would drop it from the one case it explicitly asks for.
    for uid in sorted(units):
        for wid in _own_refs(units[uid]):
            case = out.get(wid)
            if case is not None and uid not in case.units:
                case.units.append(uid)

    for case in out.values():
        for uid in case.units:
            # Absent means authored, as everywhere else. Counted by name rather
            # than by "not outline" so that the middle tier lands in its own
            # column instead of inflating the one a reader trusts most.
            status = units[uid].get("status", "authored")
            if status == "outline":
                case.outline += 1
            elif status == "sketched":
                case.sketched += 1
            else:
                case.authored += 1
    return out


def index_document(repo: Repository) -> Dict[str, Any]:
    """The generated index, as it is written to disk."""
    built = cases(repo)
    return {
        "version": 1,
        "generated_by": GENERATED_BY,
        "standard": {
            "source_ref": repo.standards["wstg"].data["source_ref"],
            "source_commit": repo.standards["wstg"].data["source_commit"],
        },
        "cases": [
            {
                "id": case.id,
                "title": case.title,
                "topics": case.topics,
                "units": case.units,
                "authored": case.authored,
                "sketched": case.sketched,
                "outline": case.outline,
                "resolvable": case.resolvable,
            }
            for case in (built[wid] for wid in sorted(built))
        ],
    }
