"""The link from a test case of the standard to the units that cover it.

The catalogue stores this relation one way round -- a topic names the test cases
it claims -- which answers the author's question. The tester's question is the
other one: the scope sheet says `WSTG-INPV-05`, so what is opened. It was always
derivable, and derivable is not available: it existed only inside the built HTML
file, where it cannot be read in a diff, checked in CI, or reached from a
terminal.
"""

import subprocess
import sys
import unittest
from pathlib import Path

import yaml

from harrier import Repository, find_root
from harrier.standard import INDEX_PATH, cases, index_document
from tests.support import REPO_ROOT, Sandbox, messages
from harrier.validate import validate


class TheIndexIsDerivedFromTheCatalogue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Repository.load(REPO_ROOT)
        cls.cases = cases(cls.repo)

    def test_every_pinned_test_case_appears_even_with_nothing_covering_it(self):
        """A row that vanished when coverage was lost would hide exactly the
        change worth seeing: the file would shrink and still look complete."""
        pinned = {e["id"] for e in self.repo.standards["wstg"].data["wstg"]}
        self.assertEqual(set(self.cases), pinned)

    def test_a_test_case_no_topic_claims_says_so_rather_than_being_absent(self):
        uncovered = [c.id for c in self.cases.values() if not c.covered]
        self.assertEqual(uncovered, ["WSTG-INPV-14"])

    def test_a_case_claimed_by_several_topics_keeps_all_of_them(self):
        """Five test cases are spread across more than one topic. An index that
        had to pick one would be wrong five times, and `WSTG-APIT-99` is the
        reason: it really is reconnaissance and authorization and business logic
        and injection at once."""
        spread = {c.id: c.topics for c in self.cases.values() if len(c.topics) > 1}
        self.assertEqual(len(spread), 5)
        self.assertEqual(
            sorted(spread["WSTG-APIT-99"]),
            ["HRR-ACL-07", "HRR-BIZ-09", "HRR-INJ-12", "HRR-RCN-07"],
        )

    def test_the_units_of_a_case_are_the_units_of_the_topics_claiming_it(self):
        topics = {d.data["id"]: d.data for d in self.repo.topics}
        for case in self.cases.values():
            expected = set()
            for tid in case.topics:
                expected |= {
                    d.data["id"] for d in self.repo.units
                    if d.data["topic"] == tid
                }
            self.assertEqual(set(case.units), expected, case.id)

    def test_the_declared_order_of_a_topic_survives_into_the_index(self):
        """The order is the sequence a tester works, so it is carried rather
        than sorted."""
        topic = next(d.data for d in self.repo.topics if d.data["id"] == "HRR-INJ-01")
        self.assertEqual(self.cases["WSTG-INPV-05"].units, topic["order"])

    def test_the_depth_counts_add_up_to_the_units(self):
        for case in self.cases.values():
            self.assertEqual(case.authored + case.outline, len(case.units), case.id)


class TheCommittedIndexIsCurrent(unittest.TestCase):
    """The file is generated and committed. Both halves matter: generated, so it
    cannot drift from what it describes; committed, so a change in coverage shows
    up in a diff instead of inside a build output nobody reviews."""

    def test_the_file_on_disk_is_what_the_catalogue_derives(self):
        expected = index_document(Repository.load(REPO_ROOT))
        actual = yaml.safe_load((REPO_ROOT / INDEX_PATH).read_text(encoding="utf-8"))
        self.assertEqual(actual, expected, "run `harrier index`")

    def test_the_check_flag_agrees(self):
        done = subprocess.run(
            [sys.executable, "-m", "harrier", "index", "--check"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_stale_file_is_rejected_rather_than_quietly_regenerated(self):
        """The failure mode this guards is a reviewer reading a coverage claim
        the catalogue no longer supports."""
        box = Sandbox()
        self.addCleanup(box.close)
        target = box.path(INDEX_PATH.as_posix())
        document = yaml.safe_load(target.read_text(encoding="utf-8"))
        document["cases"][0]["units"].append("HRR-INJ-01-INVENTED")
        target.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        done = subprocess.run(
            [sys.executable, "-m", "harrier", "index", "--check"],
            cwd=box.root, capture_output=True, text=True,
        )
        self.assertEqual(done.returncode, 1)
        self.assertIn("stale", done.stderr)


class TheIndexIsCheckedLikeEveryOtherStandard(unittest.TestCase):
    """A file under `standards/` with no schema is refused rather than trusted,
    and this one is no exception for being generated."""

    def setUp(self):
        self.box = Sandbox()
        self.addCleanup(self.box.close)

    def assertRejected(self, fragment):
        problems = validate(self.box.root)
        self.assertTrue(problems, "expected a rejection, got a clean repository")
        self.assertIn(fragment, messages(problems))

    def test_an_index_naming_a_topic_that_does_not_exist_is_rejected(self):
        target = self.box.path(INDEX_PATH.as_posix())
        document = yaml.safe_load(target.read_text(encoding="utf-8"))
        document["cases"][0]["topics"] = ["not-a-topic-id"]
        target.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        self.assertRejected("schema (wstg-index)")

    def test_an_index_with_an_unknown_generator_is_rejected(self):
        target = self.box.path(INDEX_PATH.as_posix())
        document = yaml.safe_load(target.read_text(encoding="utf-8"))
        document["generated_by"] = "somebody's editor"
        target.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        self.assertRejected("schema (wstg-index)")


class TheChecklistAnswersTheTestersQuestion(unittest.TestCase):
    def run_cli(self, *args):
        done = subprocess.run(
            [sys.executable, "-m", "harrier", *args],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def test_one_case_lists_the_units_a_tester_would_work(self):
        out = self.run_cli("checklist", "WSTG-INPV-05")
        self.assertIn("Testing for SQL Injection", out)
        self.assertIn("HRR-INJ-01-UNION", out)
        self.assertIn("10 unit(s)", out)

    def test_an_uncovered_case_says_so_rather_than_printing_an_empty_list(self):
        out = self.run_cli("checklist", "--uncovered")
        self.assertIn("WSTG-INPV-14", out)
        self.assertIn("no topic claims this test case", out)

    def test_an_unknown_case_is_an_error_rather_than_an_empty_result(self):
        done = subprocess.run(
            [sys.executable, "-m", "harrier", "checklist", "WSTG-NOPE-01"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        self.assertEqual(done.returncode, 1)
        self.assertIn("no such test case", done.stderr)

    def test_the_chain_view_names_the_test_case_that_leads_to_a_unit(self):
        """`harrier chain HRR-INJ-01-BOOL` never said WSTG-INPV-05, so a reader
        had no route back to the line item that sent them there."""
        out = self.run_cli("chain", "HRR-INJ-01-BOOL")
        self.assertIn("covers: WSTG-INPV-05", out)
