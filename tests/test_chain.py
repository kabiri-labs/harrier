"""The rules that keep the derived attack chain honest.

The graph is computed from what units declare, so a wrong declaration does not
produce a visible error -- it produces a route that silently does not exist, or
one that does and should not. Every rule here is checked negatively for that
reason, and the two positive tests exist only to prove the rules can be
satisfied at all.
"""

import unittest

from harrier.chain import Chain, chain_index, family_of, still_required, tier_of
from harrier.validate import validate
from tests.support import REPO_ROOT, Sandbox, messages

REAL_FACT = "surface.sql.injectable"

#: A vocabulary small enough to reason about, covering one fact of each tier.
TIERS = {
    "access.user": "engagement",
    "surface.x": "topic",
    "artifact.token": "chain",
}


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

    def test_a_granted_fact_is_never_treated_as_supplied(self):
        # Host access is supplied by an engagement whose scope includes it, and
        # by no test. It is not a root of the graph, and a continuation that
        # needs it must still say so rather than assuming it away.
        chain = Chain.load(self.box.root)
        self.assertNotIn("access.host", chain.given())
        needs_host = [
            uid
            for uid, unit in chain.units.items()
            if "access.host" in ((unit.get("requires") or {}).get("all_of") or [])
        ]
        self.assertTrue(needs_host, "nothing requires a granted capability any more")
        still = still_required(
            chain.units[needs_host[0]], established=set(), given=chain.given()
        )
        self.assertIn("access.host", still.get("all_of", []))

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
    """Asserted against the real repository: these are the relationships the
    catalogue actually declares, not ones a fixture invented.

    Every claim here is generic. An edge means *if this succeeds, that may
    become relevant* -- it is never a statement that something is now possible,
    and the wording of the assertions has to stay as careful as the product's.
    """

    @classmethod
    def setUpClass(cls):
        cls.chain = Chain.load(Sandbox.REPO_ROOT)
        cls.index = cls.chain.index()

    def onward(self, uid):
        return {link["unit"]: link for link in self.index[uid]["out"]}

    def test_a_probe_leads_to_the_technique_that_needs_what_it_establishes(self):
        link = self.onward("HRR-INJ-01-PROBE").get("HRR-INJ-01-UNION")
        self.assertIsNotNone(link)
        self.assertEqual(link["kind"], "requires")
        self.assertIn("surface.sql.injectable", link["via"])

    def test_a_fingerprint_motivates_rather_than_conditions(self):
        link = self.onward("HRR-INJ-01-FPRINT").get("HRR-INJ-01-UNION")
        self.assertIsNotNone(link)
        self.assertEqual(link["kind"], "motivated_by")
        self.assertEqual(link["via"], [])
        self.assertIn("recon.engine.identified", link["hint"])

    def test_an_account_is_not_a_root_of_the_graph(self):
        # Engagements that supply no credentials exist. Treating an account as a
        # root would present tests whose condition nothing has established.
        self.assertNotIn("access.user", self.chain.given())
        self.assertTrue(self.chain.producers.get("access.user"))

    def test_a_condition_success_does_not_supply_is_reported_as_still_required(self):
        link = self.onward("HRR-ACL-02-MAP").get("HRR-ACL-02-PEER")
        self.assertIsNotNone(link)
        self.assertIn("artifact.objectid.known", link["via"])
        # Reaching it through one capability is not the same as being able to
        # perform it: the second account is still owed, and is named.
        self.assertIn("access.peer", link["also"].get("all_of", []))

    def test_every_edge_names_the_capability_it_travels_through(self):
        for uid, edge in self.index.items():
            for link in edge["out"]:
                self.assertTrue(
                    link["via"] or link.get("hint"), f"{uid} -> {link['unit']}"
                )

    def test_an_alternative_route_is_not_pooled_into_one_condition(self):
        """`any_of` is a choice, and the two branches leave different things
        owed. Treating the group as satisfied because one member is establishes
        a capability nobody has."""
        unit = {"requires": {"any_of": ["access.anon", "access.user"]}}
        self.assertEqual(still_required(unit, set(), set()), {"any_of": ["access.anon", "access.user"]})
        self.assertEqual(still_required(unit, {"access.user"}, set()), {})
        self.assertEqual(still_required(unit, set(), {"access.anon"}), {})


class TheChartsReachIsMeasuredRatherThanAssumed(unittest.TestCase):
    """A capability nothing declares a use for is where some chain stops.

    Not a defect in any one unit, and not something to hide: it is how far the
    chart currently runs, and the artefact says so on the page rather than
    rendering a dead end with no explanation."""

    @classmethod
    def setUpClass(cls):
        cls.chain = Chain.load(Sandbox.REPO_ROOT)

    def test_a_dead_end_is_a_capability_nothing_requires_or_is_motivated_by(self):
        for fid in self.chain.dead_ends():
            self.assertIn(fid, self.chain.facts)
            self.assertFalse(self.chain.consumers.get(fid), fid)
            self.assertFalse(self.chain.motivates.get(fid), fid)

    def test_an_impact_is_never_counted_as_a_dead_end(self):
        """Every impact is unconsumed -- requiring one is rejected -- so a count
        that included them would describe arriving at an outcome as failing to
        continue to one, and would be inflated by exactly the terminal set."""
        impacts = self.chain.impacts()
        self.assertTrue(impacts)
        for fid in impacts:
            self.assertEqual(family_of(fid), "impact")
            self.assertFalse(self.chain.consumers.get(fid), fid)
            self.assertNotIn(fid, self.chain.dead_ends())

    def test_the_four_ways_a_chain_can_go_account_for_every_test(self):
        reach = self.chain.reach()
        self.assertEqual(sum(reach.values()), len(self.chain.nodes))
        self.assertTrue(all(v >= 0 for v in reach.values()))
        self.assertGreater(reach["impact"], 0, "nothing reaches an impact any more")

    def test_a_unit_whose_capabilities_are_all_terminal_is_marked_as_such(self):
        index = self.chain.index()
        stops = 0
        for uid, edge in index.items():
            if edge["yields"] and not edge["out"]:
                self.assertTrue(edge["terminal"], uid)
                stops += 1
        self.assertGreater(stops, 0, "no chain in the catalogue stops any more")


class EveryFactDeclaresWhatKindOfEdgeItMakes(SandboxCase):
    """Three different relations were printed under one heading before `tier`.

    Holding a session, having another technique for the same test, and holding a
    captured token are all "A yields what B requires", and the derivation cannot
    tell them apart from the join alone. The fact says which it is. A fact that
    declares no tier is rejected rather than defaulted, because a default would
    silently refill the heading this field exists to empty.
    """

    def test_a_fact_without_a_tier_is_rejected(self):
        def drop(vocab):
            for fact in vocab["facts"]:
                fact.pop("tier", None)
            return vocab

        self.box.edit("vocab/facts.yaml", drop)
        self.assertRejected("tier")

    def test_a_tier_outside_the_three_is_rejected(self):
        def invent(vocab):
            vocab["facts"][0]["tier"] = "sometimes"
            return vocab

        self.box.edit("vocab/facts.yaml", invent)
        self.assertRejected("tier")


class TheTierOfAnEdgeIsTheMostSpecificItTravelsThrough(unittest.TestCase):
    """An edge reached by two facts is filed under the narrower of them.

    A step that needs both a held session and a captured token is reached by
    capturing the token. Filing it under the session would bury it among the
    ninety-odd other things a session opens, which is the exact failure the tier
    exists to prevent -- so the precedence runs chain, then topic, then
    engagement, and never the other way.
    """

    def test_chain_wins_over_engagement(self):
        self.assertEqual(
            tier_of(["access.user", "artifact.token"], TIERS), "chain"
        )

    def test_topic_wins_over_engagement(self):
        self.assertEqual(tier_of(["access.user", "surface.x"], TIERS), "topic")

    def test_an_edge_through_only_generic_facts_stays_engagement(self):
        self.assertEqual(tier_of(["access.user"], TIERS), "engagement")

    def test_an_unknown_fact_stays_visible_rather_than_being_hidden(self):
        """Failing open is the deliberate direction. Showing a prerequisite among
        the escalations costs a reader one line; hiding an escalation costs them
        the edge they opened the page for."""
        self.assertEqual(tier_of(["nothing.declared"], TIERS), "chain")


class ContinuationsAreOrderedByTier(unittest.TestCase):
    """The escalation must not sort below the prerequisites, whatever else is true
    of it -- that ordering was what made it unfindable."""

    def test_a_chain_edge_precedes_an_engagement_edge_from_the_same_unit(self):
        units = {
            "HRR-A-01-P": {
                "id": "HRR-A-01-P",
                "topic": "HRR-A-01",
                "yields": ["access.user", "artifact.token"],
            },
            "HRR-A-01-GENERIC": {
                "id": "HRR-A-01-GENERIC",
                "topic": "HRR-A-01",
                "requires": {"all_of": ["access.user"]},
            },
            "HRR-B-02-ESCALATION": {
                "id": "HRR-B-02-ESCALATION",
                "topic": "HRR-B-02",
                "requires": {"all_of": ["artifact.token"]},
            },
        }
        index = chain_index(units, given=set(), tiers=TIERS)
        out = index["HRR-A-01-P"]["out"]
        self.assertEqual(
            [e["unit"] for e in out], ["HRR-B-02-ESCALATION", "HRR-A-01-GENERIC"]
        )
        self.assertEqual([e["tier"] for e in out], ["chain", "engagement"])

    def test_a_hinted_fact_counts_toward_the_tier_even_when_a_hard_one_exists(self):
        """`kind` and `tier` answer different questions. Whether a hard
        prerequisite exists decides the first; the most specific fact the edge
        travels through decides the second. A consumer that requires a session
        and is motivated by a captured token travels through both, and reading
        only the hard side would file it under the session -- hiding exactly the
        relation the tier exists to surface."""
        units = {
            "HRR-A-01-P": {
                "id": "HRR-A-01-P",
                "topic": "HRR-A-01",
                "yields": ["access.user", "artifact.token"],
            },
            "HRR-B-02-C": {
                "id": "HRR-B-02-C",
                "topic": "HRR-B-02",
                "requires": {"all_of": ["access.user"]},
                "motivated_by": ["artifact.token"],
            },
        }
        index = chain_index(units, given=set(), tiers=TIERS)
        edge = index["HRR-A-01-P"]["out"][0]
        self.assertEqual(edge["via"], ["access.user"])
        self.assertEqual(edge["hint"], ["artifact.token"])
        self.assertEqual(edge["kind"], "requires")
        self.assertEqual(edge["tier"], "chain")

    def test_the_real_catalogue_files_the_known_escalations_as_chain(self):
        """The five primitive and artifact escalations in the catalogue are the
        ones a tester means by "attack chain". If any of them stops being
        chain-tier, the tier assignment has drifted."""
        chain = Chain.load(REPO_ROOT)
        index = chain.index()
        known = {
            ("HRR-INJ-03-READ", "HRR-RES-01-EXEC"),
            ("HRR-INJ-04-READ", "HRR-RES-01-EXEC"),
            ("HRR-INJ-10-READ", "HRR-RES-01-EXEC"),
            ("HRR-SES-04-READ", "HRR-SES-09-READ"),
            ("HRR-SES-04-READ", "HRR-SES-09-REPLAY"),
        }
        seen = {
            (uid, edge["unit"]): edge["tier"]
            for uid, node in index.items()
            for edge in node["out"]
        }
        for pair in known:
            self.assertEqual(seen.get(pair), "chain", pair)

    def test_no_edge_through_a_held_session_alone_is_called_an_escalation(self):
        """`access.user` on its own opens most of the catalogue. An edge that
        travels only through it is a prerequisite however far apart the two units
        are, and calling it a continuation is what produced ninety-two of them
        from a single unit."""
        chain = Chain.load(REPO_ROOT)
        for uid, node in chain.index().items():
            for edge in node["out"]:
                travelled = edge["via"] or edge.get("hint") or []
                if set(travelled) <= {"access.user"} and travelled:
                    self.assertEqual(edge["tier"], "engagement", (uid, edge["unit"]))
