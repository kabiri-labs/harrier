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
                    self.assertEqual(job, "publish")

    def test_every_job_that_builds_or_tests_says_read_explicitly(self):
        """Inheriting the workflow default is not the same as declaring it. A
        job that never states its permissions is one nobody notices when the
        default above it changes."""
        for path in WORKFLOWS:
            for job, body in (load(path).get("jobs") or {}).items():
                if body.get("uses") or job == "publish":
                    continue
                with self.subTest(workflow=path.name, job=job):
                    self.assertEqual(body.get("permissions"), {"contents": "read"})


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

    def test_the_step_that_touches_a_release_lives_only_in_the_guarded_job(self):
        touching = [
            (job, step) for job, step in self.steps
            if "gh release upload" in (step.get("run") or "")
        ]
        self.assertEqual(len(touching), 1, "exactly one step may touch a release")
        job, _ = touching[0]
        self.assertEqual(job, "publish")
        # Guarded on the job, not on the step: a step-level guard still creates
        # a runner holding a write credential on every dispatch.
        self.assertEqual(self.workflow["jobs"][job]["if"], "github.event_name == 'release'")

    def test_a_dispatch_cannot_reach_the_publishing_job_at_all(self):
        """Not "declines to publish" -- cannot. The guard is on the job, so on a
        dispatch nothing with a write credential is ever created."""
        publish = self.workflow["jobs"]["publish"]
        self.assertEqual(publish["if"], "github.event_name == 'release'")
        self.assertEqual(publish["permissions"], {"contents": "write"})

    def test_the_file_leaves_the_build_by_the_same_route_on_both_paths(self):
        kept = [
            step for _, step in self.steps
            if (step.get("uses") or "").startswith("actions/upload-artifact")
        ]
        self.assertEqual(len(kept), 1)
        self.assertIsNone(kept[0].get("if"), "the build must always produce the artefact")

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
        self.assertIn("checks", jobs["build"]["needs"])
        self.assertIn("build", jobs["publish"]["needs"])

    def test_the_release_runs_the_same_checks_a_pull_request_runs(self):
        """Not a copy of them. A release that could pass a weaker set than a
        pull request is a release nobody has actually checked."""
        validate = load(REPO_ROOT / ".github" / "workflows" / "validate.yml")
        self.assertIn("workflow_call", triggers(validate))
        # The reusable workflow is the only place the checks are written down.
        release_runs = " ".join(step.get("run") or "" for _, step in self.steps)
        self.assertNotIn("unittest discover", release_runs)
        self.assertNotIn("harrier validate", release_runs)

    def test_the_job_that_can_write_runs_none_of_this_project_s_code(self):
        """The finding this workflow was rewritten for.

        Building means installing dependencies and executing the repository at
        the released ref. A job holding a write credential while doing either is
        a job where a compromised dependency can push to the repository -- and
        `actions/checkout` persists the token in `.git/config` by default, so
        the credential is reachable by anything that runs there. The build now
        holds `contents: read` and no persisted credential; the job that can
        write checks nothing out, installs nothing, and runs no Python at all.
        """
        publish = self.workflow["jobs"]["publish"]
        for step in publish["steps"]:
            uses, run = step.get("uses") or "", step.get("run") or ""
            with self.subTest(step=step.get("name") or uses):
                self.assertNotIn("actions/checkout", uses, "no checkout in a write-enabled job")
                self.assertNotIn("actions/setup-python", uses)
                for phrase in ("pip install", "python -m", "python "):
                    self.assertNotIn(phrase, run, f"{phrase} runs with a write credential")

    def test_the_building_job_leaves_no_credential_behind_for_it_to_find(self):
        build = self.workflow["jobs"]["build"]
        checkouts = [
            step for step in build["steps"]
            if (step.get("uses") or "").startswith("actions/checkout")
        ]
        self.assertEqual(len(checkouts), 1)
        self.assertIs(
            (checkouts[0].get("with") or {}).get("persist-credentials"), False,
            "actions/checkout leaves the token in .git/config unless told not to",
        )

    def test_the_digest_is_published_beside_the_file_and_proved_reproducible(self):
        runs = " ".join(step.get("run") or "" for _, step in self.steps)
        self.assertIn("sha256sum", runs)
        self.assertIn("not reproducible", runs.lower())
