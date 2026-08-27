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
    outline: int = 0

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


def cases(repo: Repository) -> Dict[str, Case]:
    """Every pinned test case, with the topics and units that cover it."""
    units = {doc.data["id"]: doc.data for doc in repo.units}
    topics = {doc.data["id"]: doc.data for doc in repo.topics}

    out: Dict[str, Case] = {}
    for entry in repo.standards["wstg"].data["wstg"]:
        out[entry["id"]] = Case(id=entry["id"], title=entry["title"])

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
                if uid not in case.units:
                    case.units.append(uid)

    for case in out.values():
        for uid in case.units:
            if units[uid].get("status") == "outline":
                case.outline += 1
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
                "outline": case.outline,
            }
            for case in (built[wid] for wid in sorted(built))
        ],
    }
