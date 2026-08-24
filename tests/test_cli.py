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
        self.assertIn("HRR-INJ-01.topic.yaml", err)
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
