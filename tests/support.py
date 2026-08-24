"""Shared fixtures.

Every mutation test works on a copy of the real repository rather than a
hand-built miniature. A miniature drifts from the thing it stands in for, and
then the suite passes while the repository is broken -- so the fixture is the
repository, with one thing deliberately changed.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


class Sandbox:
    """A throwaway copy of the repository, with helpers to break one thing in it."""

    def __init__(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="harrier-test-")
        self.root = Path(self._tmp) / "repo"
        shutil.copytree(
            REPO_ROOT,
            self.root,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".venv"),
        )

    def close(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def path(self, rel: str) -> Path:
        return self.root / rel

    def read(self, rel: str) -> Any:
        return yaml.safe_load(self.path(rel).read_text(encoding="utf-8"))

    def write(self, rel: str, data: Any) -> None:
        target = self.path(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    def edit(self, rel: str, mutate: Callable[[Any], Any]) -> None:
        """Load, mutate, write back. The mutation may return a value or edit in place."""
        data = self.read(rel)
        result = mutate(data)
        self.write(rel, data if result is None else result)

    #: The topic every mutation test starts from. A real one rather than an
    #: invented one -- a miniature would need its own copy of every field the
    #: validator checks, and would drift from the repository the moment one of
    #: them changed.
    #:
    #: It is deliberately a topic that nothing links to: a test declaring its
    #: own `see_also` on a topic with inbound links would collide with them and
    #: fail on the wrong rule. Units are not a constraint on the choice --
    #: `add_topic` drops the base's own units from the copy.
    BASE_TOPIC = "knowledge/aut/HRR-AUT-01.topic.yaml"
    BASE_TOPIC_ID = "HRR-AUT-01"

    #: Kept as a separate name because the reason differs: some tests need a
    #: topic nothing links to, which is a weaker requirement than the base's.
    UNLINKED_TOPIC = BASE_TOPIC

    def clear_units(self, topic_id: str) -> None:
        """Remove a real topic's own units from the copy.

        The bases these tests start from are real topics, so they carry
        whatever units phase 3 has written for them by now. A test that
        declares its own `order` would collide with those, and the collision
        names the wrong rule. Dropping them here rather than hunting for an
        ever-shrinking set of unit-free topics is what keeps the fixture
        working as coverage grows.
        """
        for unit in self.root.glob(f"knowledge/*/{topic_id}-*.unit.yaml"):
            unit.unlink()

    def add_topic(self, base: str | None = None, **overrides: Any) -> str:
        """Overwrite the base topic with one field changed, and return its id.

        Reading the real file rather than building a miniature is what keeps the
        fixture honest: a miniature would need its own copy of every field the
        validator checks, and would drift from the repository the moment one of
        them changed. Here, an override is the only difference.
        """
        topic = self.read(base or self.BASE_TOPIC)
        self.clear_units(topic["id"])
        topic.pop("order", None)
        # The fixture's units are named with technique slugs, so the fixture's
        # topic declares that axis unless a test is specifically about the axis
        # rule. The base topic's own axis is irrelevant here -- what is being
        # exercised is the rule, not this topic's content.
        topic.setdefault("axis", "technique")
        if base is None and "axis" not in overrides:
            topic["axis"] = "technique"
        # refs merges key by key rather than replacing the block. A test that
        # sets refs.cwe is not saying the topic has no WSTG reference, and
        # dropping one would trip the coverage gate instead of the rule under
        # test -- a failure that names the wrong thing.
        refs = {**topic.get("refs", {}), **overrides.pop("refs", {})}
        topic.update(overrides)
        topic["refs"] = refs
        self.write(f"knowledge/{topic['domain'].lower()}/{topic['id']}.topic.yaml", topic)
        return topic["id"]

    def add_unit(self, **overrides: Any) -> str:
        """Write a minimal valid authored unit under the base topic."""
        unit = {
            "id": f"{self.BASE_TOPIC_ID}-UNION",
            "topic": self.BASE_TOPIC_ID,
            "title": "UNION-based extraction",
            "objective": (
                "Determine whether a UNION arm can be appended to the query so that "
                "attacker-chosen values appear in the response body."
            ),
            "oracle": {
                "positive": "A value the database computed appears in the response.",
                "negative": "Every arity and reflected position exhausted with no computed value.",
            },
            "done_when": (
                "Column count resolved, the reflected index identified, and one computed "
                "value extracted, or the reason it could not be is recorded."
            ),
        }
        unit.update(overrides)
        domain = unit["topic"].split("-")[1].lower()
        self.write(f"knowledge/{domain}/{unit['id']}.unit.yaml", unit)
        return unit["id"]


def messages(problems: Any) -> str:
    return "\n".join(problems.items)
