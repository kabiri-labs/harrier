"""The repository itself passes, and the counts it publishes are true."""

import unittest

from harrier.chain import Chain
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
            ("Units — charted", counts["units_charted"]),
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
            declared = topics[parent].get("axis")
            allowed = (axes[declared] if declared else set()) | universal
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


class ThePublishedFiguresComeFromTheData(unittest.TestCase):
    """Every number this project prints about itself, checked against what it
    actually holds.

    Learned the hard way: "189 of 366 tests lead nowhere" appeared in three
    documents and was wrong in all three, because it conflated tests that
    establish nothing with tests that stop short and counted the ones reaching
    an impact among them. A figure repeated by hand is a figure that is wrong
    somewhere, and this is the number the project asks to be judged on.
    """

    @classmethod
    def setUpClass(cls):
        cls.chain = Chain.load(REPO_ROOT)
        cls.counts = coverage(REPO_ROOT)
        # Whitespace-collapsed: the assertion is about the figure, not about
        # where a paragraph happened to wrap.
        cls.docs = {
            name: " ".join((REPO_ROOT / name).read_text(encoding="utf-8").split())
            for name in ("README.md", "docs/ROADMAP.md", "docs/CHAINING.md")
        }

    def assertPublished(self, phrase, where=None):
        for name, text in self.docs.items():
            if where and name not in where:
                continue
            if phrase in text:
                return
        self.fail(f"no document publishes {phrase!r}")

    def assertNotPublished(self, phrase):
        for name, text in self.docs.items():
            self.assertNotIn(phrase, text, f"{name} publishes a stale figure")

    def test_the_reach_of_the_chain_is_reported_correctly(self):
        reach = self.chain.reach()
        self.assertEqual(sum(reach.values()), len(self.chain.nodes),
                         "the four counts must partition the catalogue")
        self.assertPublished(
            f"{reach['continuation']} have a potential continuation, "
            f"{reach['impact']} establish an impact, {reach['short']} stop short, and "
            f"{reach['uncharted']} declare no capability"
        )

    def test_the_dead_end_count_excludes_impacts(self):
        dead = len(self.chain.dead_ends())
        total = len(self.chain.facts)
        self.assertPublished(f"{dead} of {total} capabilities")
        # The inflated figure -- dead ends plus the impacts, which are terminal
        # by construction -- must not appear anywhere.
        self.assertNotPublished(f"{dead + len(self.chain.impacts())} of {total} capabilities")

    def test_the_per_family_dead_end_figures_are_real(self):
        from harrier.chain import family_of

        dead = self.chain.dead_ends()
        for family in ("primitive", "control"):
            in_family = [f for f in self.chain.facts if family_of(f) == family]
            stopped = [f for f in dead if family_of(f) == family]
            self.assertPublished(
                f"{len(stopped)} of {len(in_family)} `{family}.*`"
            )

    def test_the_derived_edge_count_is_real(self):
        edges = sum(len(e["out"]) for e in self.chain.index().values())
        self.assertPublished(f"{edges} unit-to-unit edges across {len(self.chain.nodes)} units")

    def test_the_headline_counts_are_real(self):
        self.assertPublished(f"{self.counts['units']} Test Units", where=("README.md",))
        self.assertPublished(f"{len(self.chain.facts)} capabilities")
        self.assertPublished(f"{self.counts['topics']} topics")
