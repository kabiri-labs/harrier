"""The repository itself passes, and the counts it publishes are true."""

import collections
import re
import unittest

from pentest_navgrid import Repository
from pentest_navgrid.chain import Chain
from pentest_navgrid.validate import coverage, validate
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
            ("Units — outlined",
             counts["units"] - counts["units_authored"] - counts["units_sketched"]),
            ("Units — sketched", counts["units_sketched"]),
            ("Units — authored", counts["units_authored"]),
            ("Units — charted", counts["units_charted"]),
        ):
            with self.subTest(label=label):
                self.assertIn(f"| {label} | {value} |", roadmap, why)


class EveryDocumentLinkResolves(unittest.TestCase):
    """The documents link each other rather than repeat each other, which is the
    right trade and makes a dead link cost more than a stale paragraph would.

    Checked over every markdown file in the repository rather than the ones
    touched last, because the link that breaks is the one in the file nobody
    opened. That claim was false when it was first written: the scan covered
    the root and `docs/`, which is ten of fifteen and misses precisely the
    files the sentence is about.
    """

    #: `[text](target)` where the target is a path rather than a URL. Anchors
    #: and query strings are stripped: what is under test is that the file a
    #: reader is sent to exists.
    LINK = re.compile(r"\[[^\]]+\]\((?!https?://|mailto:)([^)#?]+)")

    @staticmethod
    def documents():
        """Every markdown file in the repository, not the two directories that
        hold most of them. Cards, mitigations and the directory READMEs are the
        ones a reader reaches by following a link from somewhere else, which
        makes them exactly the documents whose links nobody notices breaking."""
        return sorted(
            path
            for path in REPO_ROOT.rglob("*.md")
            if not any(part.startswith(".") for part in path.parts)
        )

    def test_the_scan_reaches_past_the_root_and_the_docs_directory(self):
        outside = [
            doc for doc in self.documents()
            if doc.parent != REPO_ROOT and doc.parent.name != "docs"
        ]
        self.assertTrue(
            outside,
            "the scan covers only the root and docs/, which is where a dead "
            "link is least likely to survive unnoticed",
        )

    def test_no_relative_link_in_any_document_is_dead(self):
        docs = self.documents()
        self.assertGreater(len(docs), 5, "no documents were found to check")
        for doc in docs:
            # Named by path rather than by filename: three of these are called
            # README.md, and a failure that does not say which one is a failure
            # somebody has to reproduce before they can act on it.
            rel = doc.relative_to(REPO_ROOT)
            text = doc.read_text(encoding="utf-8")
            for target in self.LINK.findall(text):
                with self.subTest(doc=str(rel), target=target):
                    self.assertTrue(
                        (doc.parent / target).resolve().exists(),
                        f"{rel} links {target}, which does not exist",
                    )

    def test_the_readme_sends_a_contributor_to_the_terms(self):
        """The terms are the one thing a contributor has to see before writing
        anything, and the README is where they will be standing."""
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("(CONTRIBUTING.md)", readme)

    def test_the_contributing_terms_name_the_content_directories(self):
        """A licence grant that reads as code-only leaves the catalogue --
        which is most of what this repository is -- outside its own terms."""
        terms = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        for directory in ("knowledge/", "vocab/", "cards/", "payloads/",
                          "mitigations/", "toolbox/", "standards/", "docs/"):
            with self.subTest(directory=directory):
                self.assertIn(f"`{directory}`", terms)


class UnitsBelongToTheAxisTheirTopicDeclares(unittest.TestCase):
    """Asserted over the real content rather than a fixture: the axis rule is
    what makes the taxonomy non-overlapping, and it is worth knowing that the
    written content actually obeys it rather than only that it could be made to."""

    def test_every_unit_slug_is_drawn_from_a_declared_vocabulary(self):
        import yaml

        from pentest_navgrid import Repository, find_root

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
        from pentest_navgrid import Repository, find_root

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
        from pentest_navgrid.chain import family_of

        dead = self.chain.dead_ends()
        for family in ("primitive", "control"):
            in_family = [f for f in self.chain.facts if family_of(f) == family]
            stopped = [f for f in dead if family_of(f) == family]
            self.assertPublished(
                f"{len(stopped)} of {len(in_family)} `{family}.*`"
            )

    def test_the_open_register_figures_are_real(self):
        """The register is a claim about how many gaps are open and how many
        causes account for them. Both are read from the file rather than from
        the sentence, because a count kept by hand is the one that goes stale
        first -- and this one is published as the measure of the largest gap."""
        import yaml

        register = yaml.safe_load(
            (REPO_ROOT / "vocab" / "facts.yaml").read_text(encoding="utf-8")
        )["unconsumed"]
        listed = {f for entry in register for f in entry["facts"]}
        self.assertPublished(
            f"{len(listed)} are open, in {len(register)} causes", where=("README.md",)
        )

    def test_the_derived_edge_count_is_real(self):
        edges = sum(len(e["out"]) for e in self.chain.index().values())
        self.assertPublished(f"{edges} unit-to-unit edges across {len(self.chain.nodes)} units")

    def test_the_headline_counts_are_real(self):
        self.assertPublished(f"{self.counts['units']} Test Units", where=("README.md",))
        self.assertPublished(f"{len(self.chain.facts)} capabilities")
        self.assertPublished(f"{self.counts['topics']} topics")

    def test_every_row_of_the_readme_table_is_read_from_the_data(self):
        """The table is what a first-time reader judges the project on. Each row
        is asserted individually so one going stale fails on its own rather than
        hiding behind the others."""
        reach = self.chain.reach()
        rows = (
            ("WSTG identifiers pinned", f"{self.counts['wstg_pinned']}, across 12 testing groups"),
            ("Claimed by a Pentest NavGrid topic",
             f"{self.counts['wstg_covered']} of {self.counts['wstg_coverable']} resolvable"),
            # Derived, not written down: the sibling test below reads the same
            # figure from the catalogue, and a literal here goes stale the first
            # time a domain is added while that one keeps passing.
            ("Topics", f"{self.counts['topics']}, across "
                       f"{len({d.data['domain'] for d in Repository.load(REPO_ROOT).topics})} domains"),
            ("Test Units", str(self.counts["units"])),
            ("Written to full procedural depth", f"**{self.counts['units_authored']}**"),
            ("Sketched", str(self.counts["units_sketched"])),
            ("Outline only", str(self.counts["units"] - self.counts["units_authored"]
                                 - self.counts["units_sketched"])),
            ("Capabilities", str(len(self.chain.facts))),
            ("Tests with a potential continuation", str(reach["continuation"])),
            ("Tests that establish an impact", str(reach["impact"])),
            ("Tests that stop short", str(reach["short"])),
            ("Tests declaring no capability", str(reach["uncharted"])),
            ("Capabilities used by no test, impacts excluded",
             f"{len(self.chain.dead_ends())} of {len(self.chain.facts)}"),
        )
        readme = self.docs["README.md"]
        for label, value in rows:
            with self.subTest(row=label):
                self.assertIn(f"| {label} | {value} |", readme)

    def test_the_edge_split_in_that_table_is_read_from_the_data(self):
        """The total on its own oversells. Most of those 561 edges say a test
        needs a session, and a reader who takes the headline for a count of
        escalations is being misled by a true number -- so the split is
        published beside it and asserted here."""
        tiers = collections.Counter(
            edge["tier"] for node in self.chain.index().values() for edge in node["out"]
        )
        readme = self.docs["README.md"]
        for label, tier in (
            ("— of them escalations between capabilities", "chain"),
            ("— another technique for the same test", "topic"),
            ("— a general prerequisite, not a step", "engagement"),
        ):
            with self.subTest(row=label):
                self.assertIn(f"| {label} | {tiers[tier]} |", readme)
        # Against the derivation rather than a literal: the three tiers have to
        # partition every edge, and a number written here would go stale on the
        # first content change -- the failure this class exists to prevent.
        total = sum(len(node["out"]) for node in self.chain.index().values())
        self.assertEqual(sum(tiers.values()), total)

    def test_the_per_domain_topic_table_is_read_from_the_data(self):
        """It went stale on the first domain added and nothing caught it: the
        totals beside it were asserted, the breakdown that has to sum to them
        was not. Every domain carrying a topic gets a cell, and the cells add
        up to the published total."""
        counts = collections.Counter(
            doc.data["domain"] for doc in Repository.load(REPO_ROOT).topics
        )
        roadmap = self.docs["docs/ROADMAP.md"]
        for code, n in counts.items():
            with self.subTest(domain=code):
                self.assertIn(f"`{code}` {n} ", roadmap + " ")
        self.assertEqual(sum(counts.values()), self.counts["topics"])

    def test_the_group_and_domain_counts_in_that_table_are_real(self):
        from pentest_navgrid import Repository

        repo = Repository.load(REPO_ROOT)
        groups = len(repo.standards["wstg"].data["groups"])
        domains = len({d.data["domain"] for d in repo.topics})
        self.assertIn(f"{self.counts['wstg_pinned']}, across {groups} testing groups",
                      self.docs["README.md"])
        self.assertIn(f"{self.counts['topics']}, across {domains} domains",
                      self.docs["README.md"])

    def test_the_alpha_notice_states_the_real_depth(self):
        """The one figure a reader will quote back. It sits above the fold and
        must not be the optimistic one."""
        self.assertIn(
            f"{self.counts['units']} Test Units exist", self.docs["README.md"]
        )
        # Read with the block quote's wrapping flattened: the sentence is prose
        # and will be rewrapped, and a test that fails on a line break is a test
        # about the paragraph's shape rather than about the figure in it.
        notice = " ".join(self.docs["README.md"].replace(">", " ").split())
        self.assertIn(
            f"{self.counts['units_authored']} units are written to full procedural depth",
            notice,
        )
        self.assertIn(f"{self.counts['units_sketched']} are sketched", notice)
