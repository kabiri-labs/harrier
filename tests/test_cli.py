"""The command line. Exit statuses are the contract CI depends on."""

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout

from harrier.cli import EXIT_FAILED, EXIT_OK, EXIT_USAGE, main
from tests.support import REPO_ROOT, Sandbox


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        status = main(argv)
    return status, out.getvalue(), err.getvalue()


class CommandLine(unittest.TestCase):
    def test_validate_exits_zero_on_the_real_repository(self):
        status, out, _ = run(["--root", str(REPO_ROOT), "validate"])
        self.assertEqual(status, EXIT_OK)
        self.assertIn("is valid", out)

    def test_quiet_prints_nothing_on_success(self):
        status, out, _ = run(["--root", str(REPO_ROOT), "validate", "--quiet"])
        self.assertEqual(status, EXIT_OK)
        self.assertEqual(out, "")

    def test_no_command_is_a_usage_error(self):
        status, _, _ = run([])
        self.assertEqual(status, EXIT_USAGE)

    def test_a_directory_that_is_not_a_repository_is_reported(self):
        status, _, err = run(["--root", "/", "validate"])
        self.assertEqual(status, EXIT_FAILED)
        self.assertIn("no Harrier repository found", err)

    def test_coverage_prints_the_counts(self):
        status, out, _ = run(["--root", str(REPO_ROOT), "coverage"])
        self.assertEqual(status, EXIT_OK)
        self.assertIn("wstg_pinned", out)


class FailureOutput(unittest.TestCase):
    def setUp(self):
        self.box = Sandbox()
        self.addCleanup(self.box.close)

    def test_a_broken_repository_exits_one_and_names_the_file(self):
        self.box.add_topic(axis="vibes")
        status, _, err = run(["--root", str(self.box.root), "validate"])
        self.assertEqual(status, EXIT_FAILED)
        self.assertIn("HRR-AUT-01.topic.yaml", err)
        self.assertIn("unknown axis vibes", err)

    def test_every_problem_is_reported_in_one_pass(self):
        # A first-failure validator trains people to fix one thing and re-run,
        # which is how the second and third problems in a file go unnoticed.
        self.box.add_topic(
            axis="vibes",
            surfaces={"any_of": ["not-a-surface"]},
            dimensions={"engine": ["mariadb"]},
        )
        status, _, err = run(["--root", str(self.box.root), "validate"])
        self.assertEqual(status, EXIT_FAILED)
        for fragment in ("unknown axis vibes", "not-a-surface", "mariadb"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, err)

    def test_malformed_yaml_names_the_file(self):
        self.box.path("vocab/domains.yaml").write_text("version: 1\ndomains: [\n")
        status, _, err = run(["--root", str(self.box.root), "validate"])
        self.assertEqual(status, EXIT_FAILED)
        self.assertIn("domains.yaml", err)
        self.assertIn("not valid YAML", err)

    def test_a_misnamed_file_under_knowledge_is_reported(self):
        self.box.path("knowledge/inj/notes.yaml").write_text("id: whatever\n")
        status, _, err = run(["--root", str(self.box.root), "validate"])
        self.assertEqual(status, EXIT_FAILED)
        self.assertIn(".topic.yaml or <id>.unit.yaml", err)


if __name__ == "__main__":
    unittest.main()


class OneStructuralErrorDoesNotHideTheRest(unittest.TestCase):
    """A misnamed file used to abort the load, which is the behaviour the
    collect-everything design exists to avoid."""

    def setUp(self):
        self.box = Sandbox()
        self.addCleanup(self.box.close)

    def test_other_problems_are_still_reported(self):
        self.box.path("knowledge/inj/notes.yaml").write_text("id: whatever\n")
        self.box.add_topic(axis="vibes")
        status, _, err = run(["--root", str(self.box.root), "validate"])
        self.assertEqual(status, EXIT_FAILED)
        self.assertIn(".topic.yaml or <id>.unit.yaml", err)
        self.assertIn("unknown axis vibes", err)


class TheCommandLineDescribesTheSameModelAsThePage(unittest.TestCase):
    """The pivot is the product's, not the artefact's.

    A command line that still asks what the tester holds and answers with what
    is "available" leaves Harrier carrying two contradictory models: the page
    saying it knows nothing about a target, and the tool a step away claiming to
    compute reachability for one. Whichever a reader meets first is the one they
    believe.
    """

    def chain(self, *args):
        status, out, err = run(["--root", str(REPO_ROOT), "chain", *args])
        self.assertEqual(status, EXIT_OK, err)
        return out

    def test_there_is_no_way_to_state_what_is_held(self):
        # argparse exits rather than returning, which is the right behaviour for
        # an unrecognised option and is what a caller would meet.
        with self.assertRaises(SystemExit) as raised:
            run(["--root", str(REPO_ROOT), "chain", "--held", "access.user"])
        self.assertEqual(raised.exception.code, EXIT_USAGE)

    def test_no_output_claims_a_test_is_now_possible(self):
        text = (
            self.chain()
            + self.chain("HRR-INJ-01-PROBE")
            + self.chain("--fact", "surface.sql.injectable")
        ).lower()
        for phrase in ("unlocks", "available", "you hold", "reachable", "ruled out"):
            self.assertNotIn(phrase, text, f"target-state wording: {phrase}")

    def test_a_continuation_names_the_capability_it_travels_through(self):
        # Every continuation this probe has is another technique for the same
        # test, so it is filed under that heading rather than as an escalation.
        # What the edge travels through is named either way -- that is the part
        # a reader acts on.
        out = self.chain("HRR-INJ-01-PROBE")
        self.assertIn("alternative techniques for this test", out)
        self.assertIn("requires what this establishes:", out)
        self.assertIn("UNION-based extraction", out)

    def test_an_escalation_is_headed_as_a_continuation_rather_than_a_prerequisite(self):
        """The two edges that leave this unit for another topic are the whole
        reason the tiers exist: before them, they sorted below ninety rows that
        every held session produces."""
        out = self.chain("HRR-IDN-01-POLICY")
        self.assertIn("potential continuations:", out)
        self.assertIn("generic prerequisite of", out)
        self.assertIn("-- not an escalation:", out)
        self.assertLess(
            out.index("potential continuations:"),
            out.index("generic prerequisite of"),
        )

    def test_a_continuation_states_what_success_here_does_not_supply(self):
        out = self.chain("HRR-ACL-02-MAP")
        self.assertIn("still required:", out)

    def test_a_continuation_with_nothing_further_owed_says_that_precisely(self):
        out = self.chain("HRR-RES-01-READ")
        self.assertIn("no additional declared hard prerequisite", out)

    def test_a_motivation_is_labelled_as_one(self):
        out = self.chain("HRR-INJ-01-FPRINT")
        self.assertIn("motivated by what this establishes:", out)

    def test_a_capability_nothing_uses_is_reported_as_where_a_chain_stops(self):
        # A blind oracle is the one capability with no outcome written for it,
        # deliberately: it is how a value is extracted rather than something a
        # chain arrives at. The subject moved here when the outcome layer gave
        # the read primitives somewhere to go -- what is asserted did not.
        out = self.chain("--fact", "primitive.blind.oracle")
        self.assertIn("no test declares a use for this", out)

    def test_a_test_whose_result_leads_nowhere_says_so(self):
        out = self.chain("HRR-INJ-11-TIME")
        self.assertIn("terminal:", out)
        self.assertIn("reportable outcome", out)

    def test_the_summary_partitions_the_tests_by_where_their_chain_goes(self):
        from harrier.chain import Chain

        out = self.chain()
        chain = Chain.load(REPO_ROOT)
        reach = chain.reach()
        # Against the catalogue rather than a literal. What this asserts is that
        # the four counts partition it exactly -- a written-down total only
        # asserts that nobody has added a unit since.
        self.assertEqual(sum(reach.values()), len(chain.nodes))
        for label, value in (
            ("with a continuation", reach["continuation"]),
            ("establishing an impact", reach["impact"]),
            ("stopping short", reach["short"]),
            ("declaring nothing", reach["uncharted"]),
        ):
            self.assertRegex(out, label + r"\s+" + str(value))

    def test_the_summary_counts_impacts_apart_from_dead_ends(self):
        from harrier.chain import Chain

        chain = Chain.load(REPO_ROOT)
        out = self.chain()
        self.assertRegex(out, r"impacts\s+" + str(len(chain.impacts())))
        self.assertRegex(out, r"dead ends\s+" + str(len(chain.dead_ends())))
        self.assertNotIn(
            str(len(chain.dead_ends()) + len(chain.impacts())) + " ", out,
            "the inflated figure must not appear",
        )

    def test_an_unknown_identifier_is_reported_rather_than_raised(self):
        for args, word in ((["chain", "NOPE"], "test"), (["chain", "--fact", "no.such"], "capability")):
            status, _, err = run(["--root", str(REPO_ROOT), *args])
            self.assertEqual(status, EXIT_FAILED)
            self.assertIn(word, err)
