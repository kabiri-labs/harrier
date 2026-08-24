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
