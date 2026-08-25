"""The published artefact.

The one property worth testing above all others is that the file reaches for
nothing: it is opened from a laptop on an engagement network, and a stylesheet
fetched from a content delivery network would tell that network's operator which
target somebody is testing and when.
"""

import json
import re
import unittest

from harrier import __version__
from harrier.build import catalogue, render
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
