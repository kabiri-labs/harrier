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
        self.box.add_unit(id="HRR-INJ-01-UNION")
        self.assertAccepted()

    def test_a_universal_phase_slug_is_accepted_on_any_axis(self):
        self.box.add_topic(axis="technique")
        self.box.add_unit(id="HRR-INJ-01-PROBE")
        self.assertAccepted()

    def test_a_slug_from_another_axis_is_rejected(self):
        self.box.add_topic(axis="technique")
        self.box.add_unit(id="HRR-INJ-01-HTMLBODY")
        self.assertRejected("is not in the technique vocabulary")

    def test_an_invented_slug_is_rejected(self):
        self.box.add_topic(axis="technique")
        self.box.add_unit(id="HRR-INJ-01-CLEVER")
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
        self.box.add_topic(order=["HRR-INJ-01-PROBE", "HRR-INJ-01-UNION"])
        self.box.add_unit(id="HRR-INJ-01-PROBE")
        self.box.add_unit(id="HRR-INJ-01-UNION")
        self.assertAccepted()

    def test_a_unit_missing_from_order_is_rejected(self):
        self.box.add_topic(order=["HRR-INJ-01-PROBE"])
        self.box.add_unit(id="HRR-INJ-01-PROBE")
        self.box.add_unit(id="HRR-INJ-01-UNION")
        self.assertRejected("HRR-INJ-01-UNION is missing from order")

    def test_order_naming_a_unit_of_another_topic_is_rejected(self):
        self.box.add_topic(order=["HRR-INJ-01-PROBE", "HRR-CLT-01-HTMLBODY"])
        self.box.add_unit(id="HRR-INJ-01-PROBE")
        self.assertRejected("which is not a unit of this topic")


if __name__ == "__main__":
    unittest.main()
