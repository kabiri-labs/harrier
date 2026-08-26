"""The published artefact.

The one property worth testing above all others is that the file reaches for
nothing: it is opened from a laptop on an engagement network, and a stylesheet
fetched from a content delivery network would tell that network's operator which
target somebody is testing and when.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

import yaml

from harrier import __version__
from harrier.build import catalogue, render, surface_closure
from harrier.validate import coverage
from tests.support import REPO_ROOT

EXTERNAL = re.compile(r"""(?:src|href)\s*=\s*["'](?!#)((?:https?:)?//|https?:)""", re.I)
NETWORK_CALLS = re.compile(r"\b(fetch\(|XMLHttpRequest|WebSocket\(|importScripts|navigator\.sendBeacon)")


class TheArtefactIsSelfContained(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)
        cls.page = render(cls.data)

    def test_it_references_no_external_resource(self):
        self.assertIsNone(
            EXTERNAL.search(self.page),
            "the artefact must not fetch a stylesheet, script, font or image",
        )

    def test_it_makes_no_network_call(self):
        found = NETWORK_CALLS.search(self.page)
        self.assertIsNone(found, f"the artefact must not call out: {found}")

    def test_it_carries_no_link_or_frame_element(self):
        for tag in ("<link", "<iframe", "<img", "<object", "<embed"):
            self.assertNotIn(tag, self.page.lower())


class TheArtefactRendersWhatItCarries(unittest.TestCase):
    """Embedding something and showing it are different, and the difference is
    invisible from the data alone."""

    @classmethod
    def setUpClass(cls):
        cls.page = render(catalogue(REPO_ROOT))

    def test_the_tools_a_unit_names_are_rendered(self):
        # Nine units name a tool whose commands and flag rationale are embedded.
        self.assertIn("D.toolbox[id]", self.page)

    def test_a_payload_cell_keeps_its_whitespace_when_displayed(self):
        # The browser collapses whitespace inside an inline element, so the
        # trailing space would be lost on copy even though the data is right.
        self.assertIn("td code, .payload { white-space: pre; }", self.page)


class TheArtefactCarriesTheCatalogue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)
        cls.page = render(cls.data)
        blob = cls.page.split('type="application/json">', 1)[1].split("</script>", 1)[0]
        cls.embedded = json.loads(blob.replace("<\\/", "</"))

    def test_the_embedded_json_survives_the_script_tag(self):
        # A "</script>" inside a string would end the block early and leave the
        # rest of the catalogue rendering as markup.
        self.assertEqual(len(self.embedded["units"]), len(self.data["units"]))

    def test_every_unit_and_topic_travels_with_it(self):
        counts = coverage(REPO_ROOT)
        self.assertEqual(len(self.embedded["units"]), counts["units"])
        self.assertEqual(len(self.embedded["topics"]), counts["topics"])

    def test_every_card_a_unit_names_is_embedded(self):
        # A card behind a link the reader cannot follow is a card they do not have.
        for unit in self.embedded["units"].values():
            if unit.get("card"):
                self.assertIn(unit["card"], self.embedded["cards"], unit["id"])
            if unit.get("mitigation"):
                self.assertIn(unit["mitigation"], self.embedded["mitigations"], unit["id"])

    def test_every_payload_file_a_unit_names_is_embedded(self):
        ids = set(self.embedded["payloads"])
        for unit in self.embedded["units"].values():
            rel = unit.get("payloads")
            if rel:
                self.assertIn(rel[len("payloads/"):-len(".yaml")], ids, unit["id"])

    def test_payload_whitespace_survives_the_journey(self):
        """Whitespace in a payload is syntax, not formatting.

        A MySQL comment is "-- " and stops being one without the trailing
        space; a numeric-context probe begins with one because it is appended
        to a bare number. The folding that tidies prose would silently take
        both, and the reader would copy something that does not work.
        """
        import yaml

        significant = 0
        for path in sorted((REPO_ROOT / "payloads").rglob("*.yaml")):
            source = yaml.safe_load(path.read_text(encoding="utf-8"))
            embedded = self.embedded["payloads"][source["id"]]["entries"]
            for original, carried in zip(source["entries"], embedded):
                self.assertEqual(original["payload"], carried["payload"], source["id"])
                if original["payload"] != original["payload"].strip():
                    significant += 1
        self.assertGreater(significant, 0, "no payload exercises the rule any more")

    def test_it_states_the_version_it_was_built_from(self):
        self.assertEqual(self.embedded["version"], __version__)
        self.assertIn(__version__, self.page)


class TheBoardIsWhatTheTesterMeetsFirst(unittest.TestCase):
    """The catalogue already computes where to start. The failure worth testing
    for is the one this replaced: computing it and then opening on something
    else, so the tester is asked the question the file could have answered."""

    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)
        cls.page = render(cls.data)

    def test_the_board_is_the_view_the_page_opens_on(self):
        self.assertIn('let view = "board"', self.page)
        self.assertIn('data-view="board" class="on"', self.page)

    def test_every_unit_carries_the_position_the_board_ranks_it_by(self):
        for unit in self.data["units"].values():
            self.assertIn("order_hint", unit, unit["id"])

    def test_all_four_result_states_are_offered(self):
        # Three results and "not yet". Without the negative one, a test nobody
        # ran and a test that came back clean look identical, which is the whole
        # thing a tester needs the file to keep straight.
        for state in ("found", "clean", "unclear", "undo"):
            self.assertIn(state, self.page)

    def test_a_clean_result_closes_what_the_unit_says_it_closes(self):
        self.assertIn('if (outcome === "clean") (u.closes || []).forEach', self.page)
        closing = [u for u in self.data["units"].values() if u.get("closes")]
        self.assertTrue(closing, "no unit declares what a clean result closes")


class TheRunNeverTravelsInsideTheArtefact(unittest.TestCase):
    """A run holds a client's target name and what was found on it. The file is
    published; the run is not, and the two must not be able to become one."""

    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)
        cls.page = render(cls.data)

    def test_the_catalogue_carries_no_run(self):
        for key in ("run", "results", "held", "target", "anchor"):
            self.assertNotIn(key, self.data, f"the catalogue must not carry {key}")

    def test_the_embedded_data_is_the_catalogue_and_nothing_else(self):
        blob = self.page.split('type="application/json">', 1)[1].split("</script>", 1)[0]
        embedded = json.loads(blob.replace("<\\/", "</"))
        self.assertEqual(set(embedded), set(self.data))

    def test_it_still_makes_no_network_call(self):
        # Storing a run must not have become a way to send one.
        self.assertIsNone(NETWORK_CALLS.search(self.page))

    def test_storage_failure_is_reported_rather_than_swallowed(self):
        # Opening a file from disk blocks storage in some browsers. Losing four
        # hours of a run silently is worse than saying so up front.
        self.assertIn("storageBroken", self.page)
        self.assertIn("Export before you finish", self.page)


class SurfacesCloseOverWhatTheyImply(unittest.TestCase):
    """A tester names the thing in front of them, not the set of things it drags
    in with it. A login form is a session cookie whether or not they said so."""

    @classmethod
    def setUpClass(cls):
        cls.surfaces = [
            s for s in yaml.safe_load(
                (REPO_ROOT / "vocab" / "surfaces.yaml").read_text(encoding="utf-8")
            )["surfaces"]
        ]
        cls.closed = surface_closure(cls.surfaces)

    def test_a_tag_always_implies_itself(self):
        for tag in self.closed:
            self.assertIn(tag, self.closed[tag])

    def test_what_a_tag_emits_is_included(self):
        exercised = 0
        for surface in self.surfaces:
            for emitted in surface.get("emits") or []:
                self.assertIn(emitted, self.closed[surface["tag"]])
                exercised += 1
        self.assertGreater(exercised, 0, "no surface emits anything any more")

    def test_it_follows_a_chain_more_than_one_step_long(self):
        deep = [t for t, implied in self.closed.items()
                if len(implied) > 1 + len(
                    dict((s["tag"], s.get("emits") or []) for s in self.surfaces)[t])]
        self.assertTrue(deep, "no surface implies anything transitively any more")

    def test_a_cycle_in_the_vocabulary_does_not_hang_the_page(self):
        # Closure runs in a browser on an engagement. A cycle must come back
        # wrong rather than not come back.
        cyclic = [{"tag": "a", "emits": ["b"]}, {"tag": "b", "emits": ["a"]}]
        self.assertEqual(surface_closure(cyclic), {"a": ["a", "b"], "b": ["a", "b"]})

    def test_a_scope_names_only_topics_that_exist(self):
        data = catalogue(REPO_ROOT)
        for tag, topics in data["scope"].items():
            for tid in topics:
                self.assertIn(tid, data["topics"], f"{tag} claims a topic that is not there")


class ACleanResultRulesOutRatherThanEstablishes(unittest.TestCase):
    """The failure this guards against inverted a finding.

    `closes` is a subset of `yields` -- enforced -- and for every unit that
    declares it, the two sets are identical. So folding a clean result into the
    held facts records the test as its own opposite: a probe that found no SQL
    injection would establish that the parameter is injectable and offer the
    extraction units that need it. Found and Clean would be the same button.
    """

    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)
        cls.page = render(cls.data)
        body = cls.page.split("function record(id, outcome) {", 1)[1]
        cls.record = body.split("\n}", 1)[0]

    def test_only_a_positive_result_establishes_a_fact(self):
        adding = [l for l in self.record.splitlines() if "held.add" in l]
        self.assertTrue(adding, "nothing establishes a fact any more")
        for line in adding:
            self.assertIn("yields", line)
            self.assertNotIn("closes", line)

    def test_a_clean_result_goes_to_the_ruled_out_set(self):
        self.assertIn('if (outcome === "clean") (u.closes || []).forEach(f => ruled.add(f));',
                      self.record)

    def test_reachability_reads_the_held_set_and_not_the_ruled_out_one(self):
        missing = self.page.split("function missing(u) {", 1)[1].split("\n}", 1)[0]
        self.assertNotIn("ruled", missing)

    def test_the_data_is_what_makes_the_mistake_possible(self):
        """If this stops holding, the guard above stops being about anything."""
        overlapping = 0
        for unit in self.data["units"].values():
            closes, yields = set(unit.get("closes") or []), set(unit.get("yields") or [])
            if closes:
                self.assertLessEqual(closes, yields, unit["id"])
                overlapping += 1
        self.assertGreater(overlapping, 0, "no unit declares closes any more")

    def test_a_ruled_out_requirement_is_not_shown_as_merely_pending(self):
        self.assertIn("function ruledOut(u) {", self.page)
        self.assertIn("Ruled out", self.page)


class ARecordedResultStaysCorrectable(unittest.TestCase):
    """A settled unit leaves the lanes that render the result controls, so an
    Undo built only there is a button nobody can reach: a mistaken result would
    cost the whole run to correct."""

    @classmethod
    def setUpClass(cls):
        cls.page = render(catalogue(REPO_ROOT))

    def test_the_settled_row_carries_an_undo_control(self):
        block = self.page.split('<div class="done-row"', 1)[1].split("join", 1)[0]
        self.assertIn("esc(u.id)", block, "the settled row is no longer rendered")
        self.assertIn('data-out="undo"', block)

    def test_undoing_a_clean_result_withdraws_what_it_ruled_out(self):
        # Safe only because a unit may close a fact it is the sole producer of.
        record = self.page.split("function record(id, outcome) {", 1)[1].split("\n}", 1)[0]
        self.assertIn("ruled.delete(f)", record)


class ImportedRunsAreCheckedAgainstThisCatalogue(unittest.TestCase):
    """`D.facts`, `D.units` and `D.scope` are plain objects, so "constructor"
    and "__proto__" index truthy on all of them. A bare truthiness check lets an
    imported run name one; the board then calls a list method on a function and
    goes down -- permanently, because the run is saved before it is drawn."""

    @classmethod
    def setUpClass(cls):
        cls.page = render(catalogue(REPO_ROOT))
        cls.runin = cls.page.split("function runIn(raw) {", 1)[1].split("\n}", 1)[0]

    def test_membership_is_asked_rather_than_assumed(self):
        self.assertIn("Object.prototype.hasOwnProperty.call", self.page)
        for lookup in ("D.scope[raw.anchor]", "D.facts[f]", "D.units[id]"):
            self.assertNotIn(
                lookup + ")", self.runin,
                f"{lookup} is truthy for inherited names; ask own() instead",
            )

    def test_every_gate_in_the_importer_uses_it(self):
        for guard in ("own(D.scope, raw.anchor)", "own(D.facts, f)", "own(D.units, id)",
                      "own(OUTCOMES, r.outcome)"):
            self.assertIn(guard, self.runin)

    def test_the_scope_lookup_that_draws_the_board_is_guarded_too(self):
        self.assertIn("own(D.scope, anchor) ? D.scope[anchor] : []", self.page)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class TheGeneratedScriptIsValidJavaScript(unittest.TestCase):
    """Every other test here asserts on substrings of the page, which a broken
    page satisfies just as well as a working one: an unterminated string literal
    left the whole script dead and the suite green. Offline, local, no network."""

    def test_it_parses(self):
        page = render(catalogue(REPO_ROOT))
        script = page.rsplit("<script>", 1)[1].rsplit("</script>", 1)[0]
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as handle:
            handle.write(script)
            path = handle.name
        try:
            done = subprocess.run(["node", "--check", path],
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
        finally:
            os.unlink(path)
