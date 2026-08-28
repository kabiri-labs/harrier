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

    def test_a_case_the_map_resolved_to_nothing_is_not_a_coverage_gap(self):
        """`WSTG-INPV-14` maps to no domain on purpose -- "incubated" describes
        second-order delivery, which this model carries as a dimension rather
        than a topic. The validator forbids a topic claiming it. Reporting it
        beside a genuine gap would turn a decision somebody made and wrote down
        into a task nobody can close."""
        deliberate = [c.id for c in self.cases.values() if not c.resolvable]
        self.assertEqual(deliberate, ["WSTG-INPV-14"])
        case = self.cases["WSTG-INPV-14"]
        self.assertFalse(case.covered)
        self.assertIn("second-order delivery", case.note)

    def test_no_resolvable_case_is_left_without_a_topic(self):
        gaps = [c.id for c in self.cases.values() if c.resolvable and not c.covered]
        self.assertEqual(gaps, [])

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
            self.assertEqual(
                case.authored + case.sketched + case.outline, len(case.units), case.id
            )


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

    def test_the_depth_of_a_case_is_reported_by_tier(self):
        """The line a tester pastes into an engagement tracker. Collapsing the
        middle tier into "authored" here would overstate what is written for the
        one case it is quoted about."""
        case = cases(Repository.load(REPO_ROOT))["WSTG-INFO-04"]
        self.assertTrue(case.sketched, "this case no longer has a sketch to report")
        out = self.run_cli("checklist", "WSTG-INFO-04")
        self.assertIn(
            f"{case.authored} authored, {case.sketched} sketched, {case.outline} outline",
            out,
        )
        self.assertIn("(sketched)", out)

    def test_the_uncovered_view_holds_only_real_gaps(self):
        """It held one entry, and that entry was a decision rather than a gap.
        Nothing is outstanding today, so the honest answer is nothing."""
        self.assertEqual(self.run_cli("checklist", "--uncovered").strip(), "")

    def test_a_deliberately_unresolved_case_explains_itself_when_asked_for(self):
        """Still reachable by name, and it says which of the two it is rather
        than leaving a reader to assume the worse one."""
        out = self.run_cli("checklist", "WSTG-INPV-14")
        self.assertIn("resolved to no domain on purpose", out)
        self.assertIn("second-order delivery", out)
        self.assertNotIn("no topic claims this test case", out)

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


class AUnitsOwnReferenceWinsOverItsTopics(unittest.TestCase):
    """`build.py` files a unit under its own `refs.wstg` where it has one, and
    under its topic's otherwise. The index has to agree: two derivations of one
    relation that disagree are worse than one, because a reader cannot tell
    which of them they are looking at."""

    def index_of(self, root):
        return {c.id: c for c in cases(Repository.load(root)).values()}

    def test_no_unit_in_the_catalogue_overrides_today(self):
        """Recorded so the case below is understood as latent rather than live."""
        repo = Repository.load(REPO_ROOT)
        overriding = [
            d.data["id"] for d in repo.units if (d.data.get("refs") or {}).get("wstg")
        ]
        self.assertEqual(overriding, [])

    def test_a_unit_naming_its_own_case_is_filed_there_and_not_by_its_topic(self):
        box = Sandbox()
        self.addCleanup(box.close)
        box.edit(
            "knowledge/inj/HRR-INJ-01-UNION.unit.yaml",
            lambda unit: unit.update(refs={"wstg": ["WSTG-INPV-06"]}) or unit,
        )
        built = self.index_of(box.root)
        self.assertIn("HRR-INJ-01-UNION", built["WSTG-INPV-06"].units)
        self.assertNotIn("HRR-INJ-01-UNION", built["WSTG-INPV-05"].units)
        # and its siblings, which name nothing, stay where their topic puts them
        self.assertIn("HRR-INJ-01-BOOL", built["WSTG-INPV-05"].units)


class TheIndexResolvesLikeEveryOtherReference(unittest.TestCase):
    """The file earns its place by being reviewable, and one nobody resolves is
    not reviewable -- it is a second copy of the catalogue free to disagree with
    the first while passing every check. The schema constrains the shape of an
    identifier, which a renamed topic satisfies perfectly on its way to pointing
    at nothing."""

    def setUp(self):
        self.box = Sandbox()
        self.addCleanup(self.box.close)

    def mutate(self, change):
        target = self.box.path(INDEX_PATH.as_posix())
        document = yaml.safe_load(target.read_text(encoding="utf-8"))
        change(document)
        target.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        return validate(self.box.root)

    def test_a_unit_identifier_that_resolves_to_nothing_is_rejected(self):
        problems = self.mutate(
            lambda d: d["cases"][0].update(units=["HRR-INJ-99-NOSUCH"], authored=0, outline=1)
        )
        self.assertIn("does not exist", messages(problems))

    def test_a_topic_identifier_that_resolves_to_nothing_is_rejected(self):
        problems = self.mutate(lambda d: d["cases"][0].update(topics=["HRR-ZZZ-01"]))
        self.assertIn("does not exist", messages(problems))

    def test_a_pinned_case_with_no_row_is_rejected(self):
        """A row that vanished with its coverage would leave the file shorter
        and still looking complete."""
        problems = self.mutate(lambda d: d.update(cases=d["cases"][1:]))
        self.assertIn("has no row in the index", messages(problems))

    def test_a_row_the_schema_rejects_does_not_crash_the_run(self):
        """Pass 1 has already recorded what is wrong with such a row. Reading it
        here would raise instead of adding a problem, which loses every finding
        collected so far and hands a reader a traceback in place of the error
        that was already waiting for them."""
        for label, change in (
            ("no id", lambda d: d["cases"][0].pop("id")),
            ("a string where a row belongs", lambda d: d.update(cases=["not-a-row"])),
            ("cases is not a list", lambda d: d.update(cases="nope")),
            ("units is not a list", lambda d: d["cases"][0].update(units="HRR-INJ-01-PROBE")),
            ("a depth count that is text", lambda d: d["cases"][0].update(authored="two")),
        ):
            with self.subTest(shape=label):
                box = Sandbox()
                self.addCleanup(box.close)
                target = box.path(INDEX_PATH.as_posix())
                document = yaml.safe_load(target.read_text(encoding="utf-8"))
                change(document)
                target.write_text(
                    yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
                )
                problems = validate(box.root)   # must return, not raise
                self.assertTrue(problems)
                self.assertIn("schema (wstg-index)", messages(problems))

    def test_an_unreadable_row_does_not_bury_the_fault_that_caused_it(self):
        """Those rows name identifiers nobody could read, so reporting each
        pinned case as missing would be a hundred lines hiding the one line that
        matters."""
        box = Sandbox()
        self.addCleanup(box.close)
        target = box.path(INDEX_PATH.as_posix())
        document = yaml.safe_load(target.read_text(encoding="utf-8"))
        document["cases"] = ["not-a-row"]
        target.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        problems = validate(box.root)
        self.assertNotIn("has no row in the index", messages(problems))
        self.assertLess(len(problems), 5)

    def test_depth_counts_that_disagree_with_the_units_are_rejected(self):
        problems = self.mutate(lambda d: d["cases"][0].update(authored=99))
        self.assertIn("by depth but lists", messages(problems))
