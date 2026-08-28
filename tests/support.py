"""Shared fixtures.

Every mutation test works on a copy of the real repository rather than a
hand-built miniature. A miniature drifts from the thing it stands in for, and
then the suite passes while the repository is broken -- so the fixture is the
repository, with one thing deliberately changed.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


class Sandbox:
    """A throwaway copy of the repository, with helpers to break one thing in it."""

    #: The checkout the copies are made from. Exposed so a test that reads the
    #: real catalogue rather than mutating one names the same path.
    REPO_ROOT = REPO_ROOT

    def __init__(self) -> None:
        self._tmp = tempfile.mkdtemp(prefix="harrier-test-")
        self.root = Path(self._tmp) / "repo"
        shutil.copytree(
            REPO_ROOT,
            self.root,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".venv"),
        )

    def close(self) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)

    def path(self, rel: str) -> Path:
        return self.root / rel

    def read(self, rel: str) -> Any:
        return yaml.safe_load(self.path(rel).read_text(encoding="utf-8"))

    def write(self, rel: str, data: Any) -> None:
        target = self.path(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    def edit(self, rel: str, mutate: Callable[[Any], Any]) -> None:
        """Load, mutate, write back. The mutation may return a value or edit in place."""
        data = self.read(rel)
        result = mutate(data)
        self.write(rel, data if result is None else result)

    #: The topic every mutation test starts from. A real one rather than an
    #: invented one -- a miniature would need its own copy of every field the
    #: validator checks, and would drift from the repository the moment one of
    #: them changed.
    #:
    #: It is deliberately a topic that nothing links to: a test declaring its
    #: own `see_also` on a topic with inbound links would collide with them and
    #: fail on the wrong rule. Units are not a constraint on the choice --
    #: `add_topic` drops the base's own units from the copy.
    BASE_TOPIC = "knowledge/aut/HRR-AUT-01.topic.yaml"
    BASE_TOPIC_ID = "HRR-AUT-01"

    #: Kept as a separate name because the reason differs: some tests need a
    #: topic nothing links to, which is a weaker requirement than the base's.
    UNLINKED_TOPIC = BASE_TOPIC

    def clear_units(self, topic_id: str) -> None:
        """Remove a real topic's own units from the copy.

        The bases these tests start from are real topics, so they carry
        whatever units phase 3 has written for them by now. A test that
        declares its own `order` would collide with those, and the collision
        names the wrong rule. Dropping them here rather than hunting for an
        ever-shrinking set of unit-free topics is what keeps the fixture
        working as coverage grows.
        """
        for unit in self.root.glob(f"knowledge/*/{topic_id}-*.unit.yaml"):
            unit.unlink()
        self._prune_facts()
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        """Regenerate the derived index over whatever the fixture now holds.

        `standards/wstg-index.yaml` names units, and removing units leaves it
        pointing at ones that no longer exist -- which the validator rejects,
        correctly, and as a second broken thing the test never asked for. Same
        reason as `_prune_facts` above: a mutation test must break exactly one
        rule, so the fixture repairs what it disturbed on its way past.

        Regenerated rather than deleted. A missing index is its own finding, and
        substituting one failure for another would leave the tests passing for
        the wrong reason.
        """
        from harrier import Repository
        from harrier.standard import INDEX_PATH, index_document

        target = self.path(INDEX_PATH.as_posix())
        if not target.is_file():
            return
        document = index_document(Repository.load(self.root))
        target.write_text(
            yaml.safe_dump(document, sort_keys=False, allow_unicode=True, width=100),
            encoding="utf-8",
        )

    def _prune_facts(self) -> None:
        """Drop facts nothing references any more.

        Removing units can leave a fact with no producer and no consumer, which
        the validator rejects -- correctly, but as a second broken thing the
        test never asked for. A mutation test must break exactly one rule, so
        the fixture repairs what it disturbed on its way past.
        """
        path = self.path("vocab/facts.yaml")
        if not path.is_file():
            return
        referenced: set[str] = set()
        for unit in self.root.glob("knowledge/*/*.unit.yaml"):
            data = yaml.safe_load(unit.read_text(encoding="utf-8")) or {}
            requires = data.get("requires") or {}
            for names in (
                requires.get("all_of"),
                requires.get("any_of"),
                data.get("motivated_by"),
                data.get("yields"),
                data.get("closes"),
            ):
                referenced.update(names or [])
        vocab = yaml.safe_load(path.read_text(encoding="utf-8"))
        vocab["facts"] = [f for f in vocab["facts"] if f["id"] in referenced]
        path.write_text(yaml.safe_dump(vocab, sort_keys=False), encoding="utf-8")

    def add_topic(self, base: str | None = None, **overrides: Any) -> str:
        """Overwrite the base topic with one field changed, and return its id.

        Reading the real file rather than building a miniature is what keeps the
        fixture honest: a miniature would need its own copy of every field the
        validator checks, and would drift from the repository the moment one of
        them changed. Here, an override is the only difference.
        """
        topic = self.read(base or self.BASE_TOPIC)
        self.clear_units(topic["id"])
        topic.pop("order", None)
        # The fixture's units are named with technique slugs, so the fixture's
        # topic declares that axis unless a test is specifically about the axis
        # rule. The base topic's own axis is irrelevant here -- what is being
        # exercised is the rule, not this topic's content.
        topic.setdefault("axis", "technique")
        if base is None and "axis" not in overrides:
            topic["axis"] = "technique"
        # refs merges key by key rather than replacing the block. A test that
        # sets refs.cwe is not saying the topic has no WSTG reference, and
        # dropping one would trip the coverage gate instead of the rule under
        # test -- a failure that names the wrong thing.
        refs = {**topic.get("refs", {}), **overrides.pop("refs", {})}
        topic.update(overrides)
        topic["refs"] = refs
        self.write(f"knowledge/{topic['domain'].lower()}/{topic['id']}.topic.yaml", topic)
        return topic["id"]

    #: What each depth tier adds on top of the one before it, mirroring the
    #: contract in `unit.schema.json`. A fixture that asks for a tier gets a
    #: document valid at it, so a test that breaks one rule breaks exactly one.
    SKETCH_DEPTH: Dict[str, Any] = {
        "oracle": {
            "positive": "A value the database computed appears in the response.",
            "negative": "Every arity and reflected position exhausted with no computed value.",
        },
        "sequence": [
            "Resolve the column count by extending the arity until the error stops.",
            "Find which of the columns is reflected into the response body.",
            "Place one computed value in that column and read it back.",
        ],
        "first_false_positive": (
            "A page that echoes the submitted arm verbatim, which proves reflection "
            "and not execution."
        ),
        "done_when": (
            "Column count resolved, the reflected index identified, and one computed "
            "value extracted, or the reason it could not be is recorded."
        ),
    }
    AUTHORED_DEPTH: Dict[str, Any] = {
        "enter_when": ["The parameter is already known to reach the query."],
        "preconditions": ["The column count is resolvable within the arity the tool tries."],
        "evidence": ["The request, and the response excerpt carrying the computed value."],
        "false_positives": ["A cached body from an earlier request in the same sweep."],
        "safety": (
            "Read one computed value and stop. Extracting rows is a decision to put "
            "to the client rather than a step in a procedure."
        ),
    }

    def add_unit(self, without: Iterable[str] = (), **overrides: Any) -> str:
        """Write a minimal valid unit under the base topic, at the depth asked for.

        Depth defaults to authored, which is what an absent status means. The
        fixture carries whatever that tier requires: a fixture invalid for a
        reason the test did not ask about fails the wrong rule, and the failure
        names something the test was not written to check.
        """
        unit = {
            "id": f"{self.BASE_TOPIC_ID}-UNION",
            "topic": self.BASE_TOPIC_ID,
            # UNION is a technique: one of the routes a tester picks between,
            # rather than a step every run performs. Overridable, because a
            # fixture that needs a stage says so.
            "role": "variant",
            "title": "UNION-based extraction",
            "objective": (
                "Determine whether a UNION arm can be appended to the query so that "
                "attacker-chosen values appear in the response body."
            ),
        }
        status = overrides.get("status", "authored")
        if status != "outline":
            unit.update(copy.deepcopy(self.SKETCH_DEPTH))
        if status == "authored":
            unit.update(copy.deepcopy(self.AUTHORED_DEPTH))
        unit.update(overrides)
        # Removing a field the tier requires is how a depth rule is put under
        # test, and it has to happen after the tier fills the document in.
        for field in without:
            unit.pop(field, None)
        domain = unit["topic"].split("-")[1].lower()
        self.write(f"knowledge/{domain}/{unit['id']}.unit.yaml", unit)
        return unit["id"]


def messages(problems: Any) -> str:
    return "\n".join(problems.items)


# --- helpers for exercising the artefact itself ------------------------------

def _artefact(name: str) -> Path:
    return REPO_ROOT / "harrier" / "artefact" / name


def node_available() -> bool:
    return bool(shutil.which("node"))


def run_in_node(body: str, data: Any) -> Any:
    """Run one snippet against the artefact's own script and return its result.

    The graph model, its layout and the search index are JavaScript, and every
    assertion about them was previously a substring match on the rendered page
    -- which a script with an unterminated literal satisfies exactly as well as
    a working one. `app.js` exports its pure functions and runs nothing on load
    without a document, so the real implementation can be called directly.

    Offline and local: node is already how the suite checks the script parses.
    """
    tmp = Path(tempfile.mkdtemp(prefix="harrier-node-"))
    try:
        (tmp / "data.json").write_text(json.dumps(data), encoding="utf-8")
        script = (
            "const H = require(%s);\n"
            "const D = JSON.parse(require('fs').readFileSync(%s, 'utf8'));\n"
            "const result = (function () {\n%s\n})();\n"
            "process.stdout.write(JSON.stringify(result === undefined ? null : result));\n"
        ) % (json.dumps(str(_artefact("app.js"))), json.dumps(str(tmp / "data.json")), body)
        (tmp / "run.js").write_text(script, encoding="utf-8")
        done = subprocess.run(
            ["node", str(tmp / "run.js")], capture_output=True, text=True
        )
        if done.returncode != 0:
            raise AssertionError(done.stderr.strip() or "node exited non-zero")
        return json.loads(done.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


#: Where a browser might be. Checked in order; absent is not a failure, because
#: the suite has to run offline on a machine that has never installed one.
_BROWSER_NAMES = ("chromium", "chromium-browser", "google-chrome", "chrome")


def find_browser() -> str | None:
    for name in _BROWSER_NAMES:
        found = shutil.which(name)
        if found:
            return found
    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if root and Path(root).is_dir():
        for pattern in (
            "chromium-*/chrome-linux/chrome",
            "chromium-*/chrome-win/chrome.exe",
            "chromium*/chrome-mac/Chromium.app/Contents/MacOS/Chromium",
        ):
            for candidate in sorted(Path(root).glob(pattern)):
                if candidate.is_file():
                    return str(candidate)
    return None


def playwright_available() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False
    return True


_BROWSER_CHECKED: bool | None = None


def browser_available() -> bool:
    """Whether a browser can actually be launched, rather than merely installed.

    Asked properly because the two ways of having one come apart: a machine may
    carry a browser Playwright did not download (found by `find_browser`), or
    Playwright's own and nothing on PATH. Guessing from either alone turns a
    skip into an error on one kind of machine and an error into a skip on the
    other -- and a silent skip is the failure mode that matters, because a suite
    that skipped a third of itself looks exactly like one that passed it.
    """
    global _BROWSER_CHECKED
    if _BROWSER_CHECKED is None:
        _BROWSER_CHECKED = False
        if playwright_available():
            if find_browser():
                _BROWSER_CHECKED = True
            else:
                try:
                    from playwright.sync_api import sync_playwright

                    with sync_playwright() as pw:
                        _BROWSER_CHECKED = Path(pw.chromium.executable_path).is_file()
                except Exception:
                    _BROWSER_CHECKED = False
    return _BROWSER_CHECKED


class Page:
    """A real browser with the artefact open in it.

    Driving the page rather than dumping its DOM is the difference between
    testing what the script renders and testing what a person can do with it:
    typing in the search box, clicking a node in the graph, pressing Enter on
    one, following a link. None of that is reachable from a static dump, and all
    of it is where a single-page application breaks.

    It is also the only place the two guarantees can be checked as behaviour
    rather than as text: every request the page attempts is recorded, and so is
    every console error -- including the ones a Content-Security-Policy raises
    when it blocks something the page needed.

    Opened over `file://` on purpose. That is how the artefact is used, and it is
    where a browser is strictest about what an inline block may do.
    """

    def __init__(self, path: Path) -> None:
        from playwright.sync_api import sync_playwright

        self._url = "file://" + str(path)
        self._pw = sync_playwright().start()
        launch: dict = {"args": ["--no-sandbox", "--disable-dev-shm-usage"]}
        # Playwright ships with a browser build it expects; where the machine has
        # a different one already, use that rather than reaching for the network.
        found = find_browser()
        if found:
            launch["executable_path"] = found
        self._browser = self._pw.chromium.launch(**launch)
        self.page = self._browser.new_page()
        self.console_errors: list[str] = []
        self.requests: list[str] = []
        self.page.on(
            "console",
            lambda m: self.console_errors.append(m.text) if m.type == "error" else None,
        )
        self.page.on("pageerror", lambda e: self.console_errors.append(str(e)))
        self.page.on("request", lambda r: self.requests.append(r.url))

    def open(self, fragment: str = ""):
        self.page.goto(self._url + fragment)
        self.page.wait_for_selector("main h2")
        return self.page

    def text(self, selector: str = "main") -> str:
        return " ".join(self.page.inner_text(selector).split())

    def hash(self) -> str:
        return self.page.evaluate("location.hash")

    def wait_for_render(self, predicate: "Callable[[], bool]", timeout: float = 5.0) -> None:
        """Wait for the page to have redrawn, not merely for the URL to change.

        `hashchange` is dispatched in a later task than the assignment that
        causes it, so `location.hash` reads as the new route while the document
        is still showing the old one. Asserting in that gap passes or fails on
        timing rather than on behaviour.

        Polled from here rather than with `wait_for_function`, which compiles a
        string inside the page and is refused by the artefact's own
        Content-Security-Policy -- correctly, since `unsafe-eval` is exactly what
        that policy exists to withhold. A test helper must not be the reason a
        security control is loosened.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            self.page.wait_for_timeout(25)
        raise AssertionError("the page did not reach the expected state in time")

    def count(self, selector: str) -> int:
        return self.page.locator(selector).count()

    def heading(self) -> str:
        return self.page.inner_text("main h2")

    def wait_for_view(self, previous: str, timeout: float = 5.0) -> str:
        """Wait until a new view has been drawn, given the one on screen now.

        The reliable signal, and the reason it is not the URL: the hash is
        assigned first and `hashchange` is dispatched in a later task, so a test
        that waits on `location.hash` and then reads the document is asserting
        against whichever the machine got to first. It passes on a fast one and
        fails on a slow one, which is the worst kind of test.
        """
        self.wait_for_render(lambda: self.heading() != previous, timeout)
        self.page.wait_for_selector("main h2")
        return self.heading()

    def offsite(self) -> list:
        return [url for url in self.requests if not url.startswith("file://")]

    def close(self) -> None:
        self._browser.close()
        self._pw.stop()
