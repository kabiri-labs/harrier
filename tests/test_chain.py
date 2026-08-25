"""The rules that keep the derived attack chain honest.

The graph is computed from what units declare, so a wrong declaration does not
produce a visible error -- it produces a route that silently does not exist, or
one that does and should not. Every rule here is checked negatively for that
reason, and the two positive tests exist only to prove the rules can be
satisfied at all.
"""

import unittest

from harrier.chain import Chain
from harrier.validate import validate
from tests.support import Sandbox, messages

REAL_FACT = "surface.sql.injectable"


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


class FactsComeFromTheVocabulary(SandboxCase):
    """A fact nobody declared does not connect two units -- it hides that they
    were never connected."""

    def test_an_invented_required_fact_is_rejected(self):
        self.box.edit(
            "knowledge/inj/HRR-INJ-01-UNION.unit.yaml",
            lambda u: u.update(requires={"all_of": ["surface.invented.here"]}),
        )
        self.assertRejected("requires names unknown fact surface.invented.here")

    def test_an_invented_yielded_fact_is_rejected(self):
        self.box.edit(
            "knowledge/inj/HRR-INJ-01-UNION.unit.yaml",
            lambda u: u.update(yields=["primitive.invented.here"]),
        )
        self.assertRejected("yields names unknown fact primitive.invented.here")

    def test_a_fact_no_unit_uses_is_rejected(self):
        def add_unused(vocab):
            vocab["facts"].append(
                {
                    "id": "control.nobody.uses",
                    "label": "Unused",
                    "description": "Declared and never referenced by any unit at all.",
                }
            )

        self.box.edit("vocab/facts.yaml", add_unused)
        self.assertRejected("control.nobody.uses is declared but no unit")


class AUnitCannotDependOnItself(SandboxCase):
    def test_requiring_what_it_yields_is_rejected(self):
        self.box.edit(
            "knowledge/inj/HRR-INJ-01-UNION.unit.yaml",
            lambda u: u.update(requires={"all_of": [REAL_FACT]}, yields=[REAL_FACT]),
        )
        self.assertRejected("requires and yields both name surface.sql.injectable")


class ImpactsEndChains(SandboxCase):
    """An impact is a business outcome, not a stepping stone. Allowing one to be
    required would let the graph run through a finding and out the other side."""

    def test_requiring_an_impact_is_rejected(self):
        def add_impact(vocab):
            vocab["facts"].append(
                {
                    "id": "impact.data.disclosed",
                    "label": "Data disclosed",
                    "description": "Records left the client's control, which is where a chain ends.",
                }
            )

        self.box.edit("vocab/facts.yaml", add_impact)
        self.box.edit(
            "knowledge/inj/HRR-INJ-01-UNION.unit.yaml",
            lambda u: u.update(requires={"all_of": ["impact.data.disclosed"]}),
        )
        self.assertRejected("an impact is where a chain ends")


class ANegativeResultClosesOnlyWhatItCouldOpen(SandboxCase):
    def test_closing_a_fact_it_does_not_yield_is_rejected(self):
        self.box.edit(
            "knowledge/inj/HRR-INJ-01-UNION.unit.yaml",
            lambda u: u.update(closes=["recon.engine.identified"]),
        )
        self.assertRejected("closes recon.engine.identified without yielding it")


class AnAuthoredUnitEstablishesSomething(SandboxCase):
    def test_an_authored_test_without_yields_is_rejected(self):
        def strip(unit):
            unit.pop("yields", None)

        self.box.edit("knowledge/inj/HRR-INJ-01-UNION.unit.yaml", strip)
        self.assertRejected("authored without yields")


class TheDerivedGraph(unittest.TestCase):
    """Asserted against the real repository: these are the routes the catalogue
    actually offers, not ones a fixture invented."""

    @classmethod
    def setUpClass(cls):
        cls.chain = Chain.load(Sandbox.REPO_ROOT)

    def test_a_probe_unlocks_the_technique_that_needs_it(self):
        onward = self.chain.next_after("HRR-INJ-01-PROBE")
        self.assertIn("HRR-INJ-01-UNION", [n.id for n in onward["unlocks"]])

    def test_a_fingerprint_motivates_rather_than_unlocks(self):
        onward = self.chain.next_after("HRR-INJ-01-FPRINT")
        self.assertIn("HRR-INJ-01-UNION", [n.id for n in onward["motivates"]])
        self.assertNotIn("HRR-INJ-01-UNION", [n.id for n in onward["unlocks"]])

    def test_only_given_facts_are_available_before_anything_is_done(self):
        # A unit that needs an earned fact must not appear in the opening set,
        # or the chain would be telling a tester to do something impossible.
        opening = {n.id for n in self.chain.available(self.chain.given())}
        self.assertNotIn("HRR-INJ-01-UNION", opening)
        self.assertIn("HRR-INJ-01-PROBE", opening)
