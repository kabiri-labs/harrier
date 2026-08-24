"""The rules that make non-overlap mechanical rather than a matter of care.

Every test here is a negative one: it asserts that something is rejected. A suite
that only checks the good cases cannot tell a working rule from one that has
quietly stopped firing, and a rule that has stopped firing looks exactly like a
repository with no problems.
"""

import unittest

from harrier.validate import validate
from tests.support import Sandbox, messages


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


class UnitSlugsComeFromTheDeclaredAxis(SandboxCase):
    """The rule the whole axis vocabulary exists to enforce."""

    def test_a_slug_from_the_declared_axis_is_accepted(self):
        self.box.add_topic(axis="technique")
        self.box.add_unit(id="HRR-AUT-01-UNION")
        self.assertAccepted()

    def test_a_universal_phase_slug_is_accepted_alongside_an_axis_slug(self):
        # PROBE belongs to no topic's own vocabulary and is available to all of
        # them; UNION is what makes the declared axis do its work.
        self.box.add_topic(axis="technique", order=["HRR-AUT-01-PROBE", "HRR-AUT-01-UNION"])
        self.box.add_unit(id="HRR-AUT-01-PROBE")
        self.box.add_unit(id="HRR-AUT-01-UNION")
        self.assertAccepted()

    def test_a_slug_from_another_axis_is_rejected(self):
        self.box.add_topic(axis="technique")
        self.box.add_unit(id="HRR-AUT-01-HTMLBODY")
        self.assertRejected("is not in the technique vocabulary")

    def test_an_invented_slug_is_rejected(self):
        self.box.add_topic(axis="technique")
        self.box.add_unit(id="HRR-AUT-01-CLEVER")
        self.assertRejected("is not in the technique vocabulary")

    def test_an_unknown_axis_on_the_topic_is_rejected(self):
        self.box.add_topic(axis="vibes")
        self.assertRejected("unknown axis vibes")


class IdentifiersAreWellFormedAndPlaced(SandboxCase):
    def test_the_domain_segment_must_match_the_declared_domain(self):
        self.box.add_topic(id="HRR-CLT-01", domain="INJ")
        self.assertRejected("id domain segment does not match domain")

    def test_a_topic_filed_in_the_wrong_directory_is_rejected(self):
        topic = {
            "id": "HRR-INJ-01", "title": "SQL injection", "domain": "INJ",
            "axis": "technique", "surfaces": {"any_of": ["sql-backed-param"]},
        }
        self.box.write("knowledge/clt/HRR-INJ-01.topic.yaml", topic)
        self.assertRejected("filed under knowledge/clt/ but declares domain INJ")

    def test_a_file_name_that_disagrees_with_its_id_is_rejected(self):
        topic = {
            "id": "HRR-INJ-01", "title": "SQL injection", "domain": "INJ",
            "axis": "technique", "surfaces": {"any_of": ["sql-backed-param"]},
        }
        self.box.write("knowledge/inj/HRR-INJ-02.topic.yaml", topic)
        self.assertRejected("file name must be HRR-INJ-01.topic.yaml")

    def test_an_undefined_domain_is_rejected(self):
        self.box.add_topic(id="HRR-ZZZ-01", domain="ZZZ")
        self.assertRejected("unknown domain ZZZ")

    def test_a_unit_whose_topic_does_not_exist_is_rejected(self):
        self.box.add_unit(topic="HRR-INJ-99", id="HRR-INJ-99-UNION")
        self.assertRejected("topic HRR-INJ-99 does not exist")


class OrderingReachesEveryUnit(SandboxCase):
    """A unit no ordering reaches is a silent coverage hole."""

    def test_a_complete_order_is_accepted(self):
        self.box.add_topic(order=["HRR-AUT-01-PROBE", "HRR-AUT-01-UNION"])
        self.box.add_unit(id="HRR-AUT-01-PROBE")
        self.box.add_unit(id="HRR-AUT-01-UNION")
        self.assertAccepted()

    def test_a_unit_missing_from_order_is_rejected(self):
        self.box.add_topic(order=["HRR-AUT-01-PROBE"])
        self.box.add_unit(id="HRR-AUT-01-PROBE")
        self.box.add_unit(id="HRR-AUT-01-UNION")
        self.assertRejected("HRR-AUT-01-UNION is missing from order")

    def test_order_naming_a_unit_of_another_topic_is_rejected(self):
        self.box.add_topic(order=["HRR-AUT-01-PROBE", "HRR-CLT-01-HTMLBODY"])
        self.box.add_unit(id="HRR-AUT-01-PROBE")
        self.assertRejected("which is not a unit of this topic")


if __name__ == "__main__":
    unittest.main()


class CrossReferencesRunBothWays(SandboxCase):
    """A see_also is a peer relationship. A boundary is the directional one."""

    def test_an_unreturned_cross_reference_is_rejected(self):
        # A reader arriving at the other topic would never learn this one exists,
        # which is the whole value the link was supposed to add.
        self.box.add_topic(self.box.UNLINKED_TOPIC, see_also=["HRR-CLT-01"])
        self.assertRejected("is not returned")

    def test_a_returned_cross_reference_is_accepted(self):
        self.box.add_topic(self.box.UNLINKED_TOPIC, see_also=["HRR-AUT-02"])
        other = self.box.read("knowledge/aut/HRR-AUT-02.topic.yaml")
        other["see_also"] = sorted(set(other.get("see_also", [])) | {"HRR-AUT-01"})
        self.box.write("knowledge/aut/HRR-AUT-02.topic.yaml", other)
        self.assertAccepted()

    def test_a_boundary_needs_no_return(self):
        # Boundaries are directional by design: "the thing I am not covering
        # lives over there" does not oblige the other topic to say anything.
        self.box.add_topic(
            self.box.UNLINKED_TOPIC,
            boundaries=[{
                "subject": "Something filed elsewhere",
                "home": "HRR-CLT-01",
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
        topic = self.box.read("knowledge/clt/HRR-CLT-12.topic.yaml")
        self.assertIn("cross-window", topic["surfaces"]["any_of"])


class ADeclaredAxisMustDoWork(SandboxCase):
    """Declaring an axis no unit draws from states a constraint that constrains
    nothing, and misdescribes how the topic is decomposed."""

    def test_an_axis_no_unit_draws_from_is_rejected(self):
        self.box.add_topic(axis="context")
        self.box.add_unit(id="HRR-AUT-01-PROBE")
        self.assertRejected("declares axis context but no unit draws a slug from it")

    def test_a_topic_may_omit_the_axis_when_every_unit_is_universal(self):
        self.box.clear_units(self.box.BASE_TOPIC_ID)
        topic = self.box.read(self.box.BASE_TOPIC)
        topic.pop("axis", None)
        topic["order"] = ["HRR-AUT-01-PROBE", "HRR-AUT-01-READ"]
        self.box.write(self.box.BASE_TOPIC, topic)
        for slug in ("PROBE", "READ"):
            self.box.add_unit(id=f"HRR-AUT-01-{slug}")
        self.assertAccepted()

    def test_an_invented_slug_is_still_rejected_without_an_axis(self):
        self.box.clear_units(self.box.BASE_TOPIC_ID)
        topic = self.box.read(self.box.BASE_TOPIC)
        topic.pop("axis", None)
        topic["order"] = ["HRR-AUT-01-CLEVER"]
        self.box.write(self.box.BASE_TOPIC, topic)
        self.box.add_unit(id="HRR-AUT-01-CLEVER")
        self.assertRejected("is not in any universal vocabulary")

    def test_an_axis_that_does_work_is_accepted(self):
        self.box.add_topic(axis="technique", order=["HRR-AUT-01-UNION"])
        self.box.add_unit(id="HRR-AUT-01-UNION")
        self.assertAccepted()
