"""The rules that make non-overlap mechanical rather than a matter of care.

Every test here is a negative one: it asserts that something is rejected. A suite
that only checks the good cases cannot tell a working rule from one that has
quietly stopped firing, and a rule that has stopped firing looks exactly like a
repository with no problems.
"""

import json
import re
import unittest

from pentest_navgrid.validate import validate
from tests.support import REPO_ROOT, Sandbox, messages


class SandboxCase(unittest.TestCase):
    def setUp(self):
        self.box = Sandbox()
        self.addCleanup(self.box.close)

    def assertRejected(self, fragment):
        problems = validate(self.box.root)
        self.assertTrue(problems, "expected a rejection, got a clean repository")
        self.assertIn(fragment, messages(problems))

    def assertAccepted(self):
        problems = validate(self.box.root)
        self.assertFalse(problems, messages(problems))


class TheTaxonomyDocumentAgreesWithTheSchemaThatEnforcesIt(unittest.TestCase):
    """`docs/TAXONOMY.md` is where an author looks up how to name a thing, and
    `unit.schema.json` is what rejects a name that is wrong. Nothing connected
    them.

    That let the rename leave the document naming the old prefix three lines
    under a grammar block showing the new one: an author reading the
    authoritative file would have chosen the obsolete one, and every test stayed
    green because the document is prose and prose was not checked.

    The grammar block is not parsed. It is read for the one token both files
    have to agree on, which is the whole of what went wrong.
    """

    @classmethod
    def setUpClass(cls):
        cls.doc = (REPO_ROOT / "docs" / "TAXONOMY.md").read_text(encoding="utf-8")
        cls.schema = json.loads(
            (REPO_ROOT / "pentest_navgrid" / "schema" / "unit.schema.json")
            .read_text(encoding="utf-8")
        )

    def prefix_from_schema(self):
        pattern = self.schema["$defs"]["unit_id"]["pattern"]
        found = re.match(r"\^([A-Z]+)-", pattern)
        self.assertIsNotNone(found, f"cannot read a prefix out of {pattern!r}")
        return found.group(1)

    def test_the_document_names_the_prefix_the_schema_requires(self):
        prefix = self.prefix_from_schema()
        self.assertIn(f"- `{prefix}` — the project prefix.", self.doc)

    def test_the_document_shows_the_grammar_the_schema_requires(self):
        prefix = self.prefix_from_schema()
        for shape in (f"{prefix}-<DOM>-<NN>", f"{prefix}-<DOM>-<NN>-<SLUG>"):
            with self.subTest(shape=shape):
                self.assertIn(shape, self.doc)

    def test_no_other_prefix_is_left_being_explained(self):
        """A second prefix presented as this project's is the failure itself,
        whatever it happens to be. Historical mentions elsewhere are fine; this
        line is the one an author acts on."""
        explained = re.findall(r"- `([A-Z]{3})` — the project prefix", self.doc)
        self.assertEqual(explained, [self.prefix_from_schema()])


class UnitSlugsComeFromTheDeclaredAxis(SandboxCase):
    """The rule the whole axis vocabulary exists to enforce."""

    def test_a_slug_from_the_declared_axis_is_accepted(self):
        self.box.add_topic(axis="technique")
        self.box.add_unit(id="PTN-AUT-01-UNION")
        self.assertAccepted()

    def test_a_universal_phase_slug_is_accepted_alongside_an_axis_slug(self):
        # PROBE belongs to no topic's own vocabulary and is available to all of
        # them; UNION is what makes the declared axis do its work.
        self.box.add_topic(axis="technique", order=["PTN-AUT-01-PROBE", "PTN-AUT-01-UNION"])
        self.box.add_unit(id="PTN-AUT-01-PROBE")
        self.box.add_unit(id="PTN-AUT-01-UNION")
        self.assertAccepted()

    def test_a_slug_from_another_axis_is_rejected(self):
        self.box.add_topic(axis="technique")
        self.box.add_unit(id="PTN-AUT-01-HTMLBODY")
        self.assertRejected("is not in the technique vocabulary")

    def test_an_invented_slug_is_rejected(self):
        self.box.add_topic(axis="technique")
        self.box.add_unit(id="PTN-AUT-01-CLEVER")
        self.assertRejected("is not in the technique vocabulary")

    def test_an_unknown_axis_on_the_topic_is_rejected(self):
        self.box.add_topic(axis="vibes")
        self.assertRejected("unknown axis vibes")


class IdentifiersAreWellFormedAndPlaced(SandboxCase):
    def test_the_domain_segment_must_match_the_declared_domain(self):
        self.box.add_topic(id="PTN-CLT-01", domain="INJ")
        self.assertRejected("id domain segment does not match domain")

    def test_a_topic_filed_in_the_wrong_directory_is_rejected(self):
        topic = {
            "id": "PTN-INJ-01", "title": "SQL injection", "domain": "INJ",
            "axis": "technique", "surfaces": {"any_of": ["sql-backed-param"]},
        }
        self.box.write("knowledge/clt/PTN-INJ-01.topic.yaml", topic)
        self.assertRejected("filed under knowledge/clt/ but declares domain INJ")

    def test_a_file_name_that_disagrees_with_its_id_is_rejected(self):
        topic = {
            "id": "PTN-INJ-01", "title": "SQL injection", "domain": "INJ",
            "axis": "technique", "surfaces": {"any_of": ["sql-backed-param"]},
        }
        self.box.write("knowledge/inj/PTN-INJ-02.topic.yaml", topic)
        self.assertRejected("file name must be PTN-INJ-01.topic.yaml")

    def test_an_undefined_domain_is_rejected(self):
        self.box.add_topic(id="PTN-ZZZ-01", domain="ZZZ")
        self.assertRejected("unknown domain ZZZ")

    def test_a_unit_whose_topic_does_not_exist_is_rejected(self):
        self.box.add_unit(topic="PTN-INJ-99", id="PTN-INJ-99-UNION")
        self.assertRejected("topic PTN-INJ-99 does not exist")


class OrderingReachesEveryUnit(SandboxCase):
    """A unit no ordering reaches is a silent coverage hole."""

    def test_a_complete_order_is_accepted(self):
        self.box.add_topic(order=["PTN-AUT-01-PROBE", "PTN-AUT-01-UNION"])
        self.box.add_unit(id="PTN-AUT-01-PROBE")
        self.box.add_unit(id="PTN-AUT-01-UNION")
        self.assertAccepted()

    def test_a_unit_missing_from_order_is_rejected(self):
        self.box.add_topic(order=["PTN-AUT-01-PROBE"])
        self.box.add_unit(id="PTN-AUT-01-PROBE")
        self.box.add_unit(id="PTN-AUT-01-UNION")
        self.assertRejected("PTN-AUT-01-UNION is missing from order")

    def test_order_naming_a_unit_of_another_topic_is_rejected(self):
        self.box.add_topic(order=["PTN-AUT-01-PROBE", "PTN-CLT-01-HTMLBODY"])
        self.box.add_unit(id="PTN-AUT-01-PROBE")
        self.assertRejected("which is not a unit of this topic")


if __name__ == "__main__":
    unittest.main()


class CrossReferencesRunBothWays(SandboxCase):
    """A see_also is a peer relationship. A boundary is the directional one."""

    def test_an_unreturned_cross_reference_is_rejected(self):
        # A reader arriving at the other topic would never learn this one exists,
        # which is the whole value the link was supposed to add.
        self.box.add_topic(self.box.UNLINKED_TOPIC, see_also=["PTN-CLT-01"])
        self.assertRejected("is not returned")

    def test_a_returned_cross_reference_is_accepted(self):
        self.box.add_topic(self.box.UNLINKED_TOPIC, see_also=["PTN-AUT-02"])
        other = self.box.read("knowledge/aut/PTN-AUT-02.topic.yaml")
        other["see_also"] = sorted(set(other.get("see_also", [])) | {"PTN-AUT-01"})
        self.box.write("knowledge/aut/PTN-AUT-02.topic.yaml", other)
        self.assertAccepted()

    def test_a_boundary_needs_no_return(self):
        # Boundaries are directional by design: "the thing I am not covering
        # lives over there" does not oblige the other topic to say anything.
        self.box.add_topic(
            self.box.UNLINKED_TOPIC,
            boundaries=[{
                "subject": "Something filed elsewhere",
                "home": "PTN-CLT-01",
                "note": "Recorded so the boundary is visible rather than assumed.",
            }],
        )
        self.assertAccepted()


class SurfaceEmissionsMustHoldForEverySurface(SandboxCase):
    """An emitted tag is a claim about every surface carrying the emitting one."""

    def test_cross_window_does_not_imply_a_dom_sink(self):
        # A postMessage handler that logs the user out or updates state writes
        # into no sink at all. Emitting dom-sink would make surface-first
        # navigation offer DOM-XSS for a surface where nothing writes anywhere.
        surfaces = self.box.read("vocab/surfaces.yaml")["surfaces"]
        cross_window = next(s for s in surfaces if s["tag"] == "cross-window")
        self.assertNotIn("dom-sink", cross_window.get("emits") or [])

    def test_reverse_tabnabbing_selects_cross_window(self):
        # An ordinary application-authored target=_blank link is the common case
        # of this vulnerability, and cross-window is the tag that describes it.
        topic = self.box.read("knowledge/clt/PTN-CLT-12.topic.yaml")
        self.assertIn("cross-window", topic["surfaces"]["any_of"])


class ADeclaredAxisMustDoWork(SandboxCase):
    """Declaring an axis no unit draws from states a constraint that constrains
    nothing, and misdescribes how the topic is decomposed."""

    def test_an_axis_no_unit_draws_from_is_rejected(self):
        self.box.add_topic(axis="context")
        self.box.add_unit(id="PTN-AUT-01-PROBE")
        self.assertRejected("declares axis context but no unit draws a slug from it")

    def test_a_topic_may_omit_the_axis_when_every_unit_is_universal(self):
        self.box.clear_units(self.box.BASE_TOPIC_ID)
        topic = self.box.read(self.box.BASE_TOPIC)
        topic.pop("axis", None)
        topic["order"] = ["PTN-AUT-01-PROBE", "PTN-AUT-01-READ"]
        self.box.write(self.box.BASE_TOPIC, topic)
        for slug in ("PROBE", "READ"):
            self.box.add_unit(id=f"PTN-AUT-01-{slug}")
        self.assertAccepted()

    def test_an_invented_slug_is_still_rejected_without_an_axis(self):
        self.box.clear_units(self.box.BASE_TOPIC_ID)
        topic = self.box.read(self.box.BASE_TOPIC)
        topic.pop("axis", None)
        topic["order"] = ["PTN-AUT-01-CLEVER"]
        self.box.write(self.box.BASE_TOPIC, topic)
        self.box.add_unit(id="PTN-AUT-01-CLEVER")
        self.assertRejected("is not in any universal vocabulary")

    def test_an_axis_that_does_work_is_accepted(self):
        self.box.add_topic(axis="technique", order=["PTN-AUT-01-UNION"])
        self.box.add_unit(id="PTN-AUT-01-UNION")
        self.assertAccepted()
