"""The workflows, checked the way everything else here is checked.

This project's own supply chain is part of its threat model -- it says so in the
authoring rules -- and a workflow is the one place in the repository that runs
somebody else's code with a token in the environment. So the properties that
keep that safe are asserted rather than reviewed: nothing runs but this
project's own steps and GitHub's own actions, nothing has more permission than
its job needs, and the release path cannot publish on a trigger a person did
not deliberately pull.

Offline and structural: the files are parsed, never executed.
"""

import unittest

import yaml

from tests.support import REPO_ROOT

WORKFLOWS = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))


def load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def triggers(workflow):
    """The `on:` block.

    YAML 1.1 reads a bare `on` as the boolean true, so the key is whichever of
    the two the parser produced. Asking for the string alone silently returns
    nothing, which would make every assertion below pass over an empty dict.
    """
    return workflow.get("on", workflow.get(True)) or {}


def steps(workflow):
    for name, job in (workflow.get("jobs") or {}).items():
        for step in job.get("steps") or []:
            yield name, step


class ThereAreWorkflowsToCheck(unittest.TestCase):
    def test_the_files_are_found_and_parse(self):
        self.assertTrue(WORKFLOWS, "no workflow was found to check")
        for path in WORKFLOWS:
            with self.subTest(workflow=path.name):
                self.assertTrue(triggers(load(path)), "no trigger")


class NothingRunsThatIsNotOursOrGitHubs(unittest.TestCase):
    """A third-party action is code from a repository this project does not
    control, running in a job that holds a token. The convenience is never worth
    it here: `gh` is already on the runner."""

    def test_every_action_is_githubs_own_or_a_local_workflow(self):
        for path in WORKFLOWS:
            for job, step in steps(load(path)):
                uses = step.get("uses")
                if not uses:
                    continue
                with self.subTest(workflow=path.name, job=job, uses=uses):
                    self.assertTrue(
                        uses.startswith("./") or uses.startswith("actions/"),
                        "third-party action in a job that holds a token",
                    )

    def test_every_action_names_a_version(self):
        for path in WORKFLOWS:
            for job, step in steps(load(path)):
                uses = step.get("uses")
                if not uses or uses.startswith("./"):
                    continue
                with self.subTest(workflow=path.name, uses=uses):
                    self.assertIn("@", uses, "an unpinned action is whatever it is today")

    def test_a_reused_workflow_is_one_of_ours(self):
        for path in WORKFLOWS:
            for job, body in (load(path).get("jobs") or {}).items():
                uses = body.get("uses")
                if not uses:
                    continue
                with self.subTest(workflow=path.name, job=job):
                    self.assertTrue(uses.startswith("./.github/workflows/"), uses)
                    # removeprefix, not lstrip: lstrip strips characters, so it
                    # would eat the leading dot of `.github` as well.
                    self.assertTrue((REPO_ROOT / uses.removeprefix("./")).is_file(), uses)


class PermissionIsTakenWhereItIsNeededAndNowhereElse(unittest.TestCase):
    def test_every_workflow_starts_from_read(self):
        for path in WORKFLOWS:
            with self.subTest(workflow=path.name):
                self.assertEqual(load(path).get("permissions"), {"contents": "read"})

    def test_only_the_job_that_publishes_may_write(self):
        for path in WORKFLOWS:
            for job, body in (load(path).get("jobs") or {}).items():
                granted = (body.get("permissions") or {}).get("contents")
                if granted != "write":
                    continue
                with self.subTest(workflow=path.name, job=job):
                    self.assertEqual(path.name, "release.yml")
                    self.assertEqual(job, "artefact")


class TheReleasePathCannotPublishOnItsOwn(unittest.TestCase):
    """The workflow attaches a file to a release that already exists. It has no
    path by which it creates a publication, which is the whole reason the
    trigger is `release: published` rather than a tag push."""

    @classmethod
    def setUpClass(cls):
        cls.workflow = load(REPO_ROOT / ".github" / "workflows" / "release.yml")
        cls.steps = list(steps(cls.workflow))

    def test_it_runs_only_on_a_published_release_or_a_deliberate_dispatch(self):
        on = triggers(self.workflow)
        self.assertEqual(sorted(on), ["release", "workflow_dispatch"])
        self.assertEqual(on["release"]["types"], ["published"])

    def test_it_never_creates_a_tag_or_a_release(self):
        forbidden = ("gh release create", "gh release delete", "git tag", "git push")
        for job, step in self.steps:
            body = step.get("run") or ""
            for phrase in forbidden:
                with self.subTest(job=job, phrase=phrase):
                    self.assertNotIn(phrase, body)

    def test_the_step_that_touches_a_release_runs_only_on_a_release(self):
        uploads = [
            step for _, step in self.steps if "gh release upload" in (step.get("run") or "")
        ]
        self.assertEqual(len(uploads), 1, "exactly one step may touch a release")
        self.assertEqual(uploads[0].get("if"), "github.event_name == 'release'")

    def test_a_dispatch_keeps_the_file_on_the_run_rather_than_publishing_it(self):
        kept = [
            step for _, step in self.steps
            if (step.get("uses") or "").startswith("actions/upload-artifact")
        ]
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0].get("if"), "github.event_name == 'workflow_dispatch'")

    def test_the_tag_and_the_version_are_checked_against_each_other(self):
        """A release tagged v0.4.1 carrying a file that says 0.4.0 is worse than
        no release: those are the two things anybody quotes."""
        checks = [
            step for _, step in self.steps
            if "the artefact states" in (step.get("run") or "")
        ]
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0].get("if"), "github.event_name == 'release'")
        self.assertIn("exit 1", checks[0]["run"])

    def test_nothing_is_attached_until_the_checks_have_passed(self):
        jobs = self.workflow["jobs"]
        self.assertEqual(jobs["checks"]["uses"], "./.github/workflows/validate.yml")
        self.assertIn("checks", jobs["artefact"]["needs"])

    def test_the_release_runs_the_same_checks_a_pull_request_runs(self):
        """Not a copy of them. A release that could pass a weaker set than a
        pull request is a release nobody has actually checked."""
        validate = load(REPO_ROOT / ".github" / "workflows" / "validate.yml")
        self.assertIn("workflow_call", triggers(validate))
        # The reusable workflow is the only place the checks are written down.
        release_runs = " ".join(step.get("run") or "" for _, step in self.steps)
        self.assertNotIn("unittest discover", release_runs)
        self.assertNotIn("harrier validate", release_runs)

    def test_the_digest_is_published_beside_the_file_and_proved_reproducible(self):
        runs = " ".join(step.get("run") or "" for _, step in self.steps)
        self.assertIn("sha256sum", runs)
        self.assertIn("not reproducible", runs.lower())
