"""The repository itself passes, and the counts it publishes are true."""

import unittest

from harrier.validate import coverage, validate
from tests.support import REPO_ROOT, messages


class TheRealRepository(unittest.TestCase):
    def test_it_validates(self):
        problems = validate(REPO_ROOT)
        self.assertFalse(problems, messages(problems))

    def test_every_pinned_identifier_is_mapped(self):
        counts = coverage(REPO_ROOT)
        self.assertEqual(
            counts["wstg_pinned"],
            counts["wstg_mapped"],
            "the domain map is the claim that the domains partition the standard; "
            "an unmapped identifier makes that claim false",
        )

    def test_the_roadmap_reports_the_real_counts(self):
        counts = coverage(REPO_ROOT)
        roadmap = (REPO_ROOT / "docs" / "ROADMAP.md").read_text(encoding="utf-8")
        why = (
            "a stale coverage number is worse than none: it is the number this "
            "project asks to be judged on"
        )
        with self.subTest(label="mapped"):
            self.assertIn(
                f"| **WSTG identifiers mapped to a domain** | "
                f"**{counts['wstg_mapped']} of {counts['wstg_pinned']}** |",
                roadmap,
                why,
            )
        with self.subTest(label="covered"):
            self.assertIn(
                f"| **WSTG identifiers covered by a topic** | "
                f"**{counts['wstg_covered']} of {counts['wstg_coverable']}** |",
                roadmap,
                why,
            )
        for label, value in (
            ("Topics", counts["topics"]),
            ("Units — outlined", counts["units"] - counts["units_authored"]),
            ("Units — authored", counts["units_authored"]),
        ):
            with self.subTest(label=label):
                self.assertIn(f"| {label} | {value} |", roadmap, why)


class UnitsBelongToTheAxisTheirTopicDeclares(unittest.TestCase):
    """Asserted over the real content rather than a fixture: the axis rule is
    what makes the taxonomy non-overlapping, and it is worth knowing that the
    written content actually obeys it rather than only that it could be made to."""

    def test_every_unit_slug_is_drawn_from_a_declared_vocabulary(self):
        import yaml

        from harrier import Repository, find_root

        repo = Repository.load(find_root(REPO_ROOT))
        axes = {a["name"]: set(a["slugs"]) for a in repo.vocab["axes"].data["axes"]}
        universal = {
            s
            for a in repo.vocab["axes"].data["axes"]
            if a.get("universal")
            for s in a["slugs"]
        }
        topics = {d.data["id"]: d.data for d in repo.topics}
        self.assertTrue(repo.units, "no units to check")
        for unit in repo.units:
            uid, parent = unit.data["id"], unit.data["topic"]
            slug = uid[len(parent) + 1 :]
            allowed = axes[topics[parent]["axis"]] | universal
            with self.subTest(unit=uid):
                self.assertIn(slug, allowed)

    def test_no_two_units_share_an_objective(self):
        from harrier import Repository, find_root

        repo = Repository.load(find_root(REPO_ROOT))
        seen = {}
        for unit in repo.units:
            objective = " ".join(unit.data["objective"].split())
            with self.subTest(unit=unit.data["id"]):
                self.assertNotIn(
                    objective,
                    seen,
                    f"identical to {seen.get(objective)} -- a copied objective "
                    "means one of the two units was not thought about",
                )
            seen[objective] = unit.data["id"]
