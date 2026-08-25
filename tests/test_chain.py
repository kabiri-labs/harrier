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
from tests.support import REPO_ROOT, Sandbox, messages

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


class OnlyASoleProducerMayCloseAFact(SandboxCase):
    """A clean result rules out the route the unit took, not the fact itself.
    Where several units establish one fact, closing it from any of them hides
    the routes that are still open -- which reads, in a coverage view, exactly
    like having tried them."""

    def test_closing_a_fact_another_unit_also_yields_is_rejected(self):
        # primitive.exec.client is established by ten units across two topics.
        self.box.edit(
            "knowledge/clt/HRR-CLT-01-HTMLBODY.unit.yaml",
            lambda u: u.update(closes=["primitive.exec.client"]),
        )
        self.assertRejected("other unit(s) also establish")

    def test_a_sole_producer_may_close_what_it_yields(self):
        self.assertAccepted()


class EveryConditionHasAProducer(SandboxCase):
    """The gate the chain pass ends on. A fact something requires and nothing
    establishes is a hole, and from the outside it reads exactly like a route
    nobody has taken yet -- which is the one failure a coverage claim must not
    be able to make."""

    def test_a_required_fact_nothing_yields_is_rejected(self):
        # RCN-03-MAP is the only unit that produces the entry-point inventory,
        # which most of the catalogue is conditioned on.
        self.box.edit(
            "knowledge/rcn/HRR-RCN-03-MAP.unit.yaml",
            lambda u: u.update(yields=["recon.hosts.enumerated"]),
        )
        self.assertRejected("recon.entrypoints.mapped is required but no unit establishes it")

    def test_a_granted_fact_is_exempt_but_not_held_at_the_start(self):
        # Host access is supplied by an engagement whose scope includes it and
        # by no test. It must not be assumed before the tester says they have it.
        chain = Chain.load(self.box.root)
        self.assertNotIn("access.host", chain.given())
        self.assertNotIn(
            "HRR-CFG-07-POLICY", {n.id for n in chain.available(chain.given())}
        )
        self.assertIn(
            "HRR-CFG-07-POLICY",
            {n.id for n in chain.available(chain.given() | {"access.host"})},
        )

    def test_a_given_fact_needs_no_producer(self):
        # access.anon is a root: the engagement supplies it and no test earns it.
        self.assertAccepted()


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

    def test_an_account_is_not_assumed_to_have_been_handed_over(self):
        # Engagements that supply no credentials exist. Treating an account as a
        # root would open the catalogue with tests the tester cannot run.
        self.assertNotIn("access.user", self.chain.given())
        opening = {n.id for n in self.chain.available(self.chain.given())}
        self.assertNotIn("HRR-ACL-02-MAP", opening)
        self.assertIn("HRR-ACL-02-MAP", {
            n.id for n in self.chain.available(self.chain.given() | {"access.user", "access.peer"})
        })

    def test_one_account_does_not_reach_the_two_account_test(self):
        held = self.chain.given() | {"access.user", "artifact.objectid.known"}
        self.assertNotIn("HRR-ACL-02-PEER", {n.id for n in self.chain.available(held)})


class AnAlternativeNotTakenIsNotAssumedHeld(unittest.TestCase):
    """`any_of` is a choice, and the choice leaves the tester holding different
    facts. Pooling the alternatives would hide the units the other route reaches."""

    def setUp(self):
        self.box = Sandbox()
        self.addCleanup(self.box.close)

    def test_a_unit_reachable_by_the_alternative_still_appears(self):
        # UNION may be reached as an anonymous or an authenticated caller. A unit
        # needing the authenticated route must still be reported as unlocked when
        # UNION's own result is what makes it possible.
        self.box.edit(
            "knowledge/inj/HRR-INJ-01-ERROR.unit.yaml",
            lambda u: u.update(
                requires={"all_of": ["access.user", "primitive.db.read"]},
                yields=["recon.engine.identified"],
            ),
        )
        chain = Chain.load(self.box.root)
        unlocked = {n.id for n in chain.next_after("HRR-INJ-01-UNION")["unlocks"]}
        self.assertIn("HRR-INJ-01-ERROR", unlocked)


class TheReadingOrderIsAnOpinionWithReasons(unittest.TestCase):
    """The order units are met in is the product's answer to "what next", so it
    is pinned rather than left to whatever order a directory listing gives."""

    @classmethod
    def setUpClass(cls):
        cls.chain = Chain.load(REPO_ROOT)
        cls.order = cls.chain.reading_order()

    def test_every_unit_gets_exactly_one_position(self):
        self.assertEqual(len(self.order), len(self.chain.nodes))
        self.assertEqual(len(set(self.order.values())), len(self.order))

    def test_a_unit_written_in_full_comes_before_one_that_is_not(self):
        """An outline hands the tester an objective and leaves them where they
        started. Burying the written ones under several hundred of those is how
        a reader concludes the catalogue is empty."""
        authored = [n.id for n in self.chain.nodes.values() if n.status == "authored"]
        outline = [n.id for n in self.chain.nodes.values() if n.status != "authored"]
        self.assertTrue(authored and outline, "the fixture no longer has both")
        self.assertLess(max(self.order[i] for i in authored),
                        min(self.order[i] for i in outline))

    def test_a_topic_declared_order_is_followed_within_that_topic(self):
        checked = 0
        for tid, declared in self.chain.topic_order.items():
            known = [u for u in declared if u in self.order]
            if len(known) < 2:
                continue
            positions = [self.order[u] for u in known]
            same_depth = len({self.chain.nodes[u].status for u in known}) == 1
            if same_depth:
                self.assertEqual(positions, sorted(positions), tid)
                checked += 1
        self.assertGreater(checked, 0, "no topic exercises the rule any more")

    def test_units_of_one_topic_are_not_scattered(self):
        """A run that jumps between unrelated topics is a run that loses its
        place. Within one depth, a topic's units are contiguous."""
        seen = {}
        for uid, position in sorted(self.order.items(), key=lambda kv: kv[1]):
            node = self.chain.nodes[uid]
            seen.setdefault((node.status == "authored", node.topic), []).append(position)
        for key, positions in seen.items():
            self.assertEqual(
                positions, list(range(min(positions), min(positions) + len(positions))),
                f"{key} is split across the order",
            )


class ReachabilityStaysDenyByDefault(unittest.TestCase):
    """The board offers a unit only when its conditions are met. A unit offered
    early is worse than one offered late: it sends a tester at a test that
    cannot work and costs them the time to find out."""

    @classmethod
    def setUpClass(cls):
        cls.chain = Chain.load(REPO_ROOT)

    def test_the_opening_position_is_not_empty(self):
        opening = self.chain.available(self.chain.given())
        self.assertTrue(opening, "a tester opening the artefact must have somewhere to start")

    def test_every_opening_unit_is_reachable_on_the_given_facts_alone(self):
        given = self.chain.given()
        for node in self.chain.available(given):
            self.assertTrue(node.reachable_with(given), node.id)

    def test_a_unit_needing_an_unheld_fact_is_never_offered(self):
        given = self.chain.given()
        offered = {n.id for n in self.chain.available(given)}
        withheld = 0
        for node in self.chain.nodes.values():
            if any(f not in given for f in node.all_of):
                self.assertNotIn(node.id, offered, node.id)
                withheld += 1
        self.assertGreater(withheld, 0, "nothing in the catalogue is gated any more")

    def test_an_any_of_group_is_not_satisfied_by_holding_none_of_it(self):
        gated = [n for n in self.chain.nodes.values() if n.any_of and not n.all_of]
        self.assertTrue(gated, "no unit exercises the rule any more")
        for node in gated:
            self.assertFalse(node.reachable_with(set()), node.id)
