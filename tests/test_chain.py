"""The rules that keep the derived attack chain honest.

The graph is computed from what units declare, so a wrong declaration does not
produce a visible error -- it produces a route that silently does not exist, or
one that does and should not. Every rule here is checked negatively for that
reason, and the two positive tests exist only to prove the rules can be
satisfied at all.
"""

import unittest

from pentest_navgrid.chain import Chain, chain_index, family_of, still_required, tier_of
from pentest_navgrid.validate import validate
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
            "knowledge/inj/PTN-INJ-01-UNION.unit.yaml",
            lambda u: u.update(requires={"all_of": ["surface.invented.here"]}),
        )
        self.assertRejected("requires names unknown fact surface.invented.here")

    def test_an_invented_yielded_fact_is_rejected(self):
        self.box.edit(
            "knowledge/inj/PTN-INJ-01-UNION.unit.yaml",
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
            "knowledge/inj/PTN-INJ-01-UNION.unit.yaml",
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
            "knowledge/inj/PTN-INJ-01-UNION.unit.yaml",
            lambda u: u.update(requires={"all_of": ["impact.data.disclosed"]}),
        )
        self.assertRejected("an impact is where a chain ends")


class SelfMotivationCannotSatisfyTheConsumerGate(SandboxCase):
    """The one way the gate could be quietly defeated.

    `chain_index` drops an edge whose consumer is the producing unit, so a unit
    that declares a use for a capability it establishes itself adds no route.
    Asking only whether *something* names the fact would let that declaration
    clear the gate while the chart still stops there -- and the register would
    lose the entry for exactly the dead end it exists to record."""

    #: One producer, so its own motivation is the only one there could be.
    SOLE = "control.misuse.undetected"
    PRODUCER = "knowledge/biz/PTN-BIZ-07-PROBE.unit.yaml"

    def _self_motivate(self):
        self.box.edit(self.PRODUCER, lambda u: u.update(motivated_by=[self.SOLE]))

    def test_a_sole_producer_naming_its_own_result_does_not_clear_the_gate(self):
        def unregister(vocab):
            for entry in vocab["unconsumed"]:
                if self.SOLE in entry["facts"]:
                    entry["facts"].remove(self.SOLE)

        self._self_motivate()
        self.box.edit("vocab/facts.yaml", unregister)
        self.assertRejected(f"{self.SOLE} is chain-tier and 1 unit(s) establish it")

    def test_the_entry_stays_valid_while_the_only_use_is_the_producer_s_own(self):
        """The other half: the register must not be told its entry is stale for
        a use that establishes no route."""
        self._self_motivate()
        self.assertAccepted()


class ASiblingNamingAnothersResultIsARealEdge(unittest.TestCase):
    """The case the rule above must not catch.

    Five `PTN-CRY-02` units test one property across five surfaces. Each
    establishes `control.transport.plaintext` and each is motivated by it, so
    every one is joined to the other six producers -- 30 edges the derivation
    draws and a naive self-edge rule would delete. The capability is not a dead
    end, and the suite says so against the real catalogue rather than a
    fixture."""

    @classmethod
    def setUpClass(cls):
        cls.chain = Chain.load(REPO_ROOT)

    FACT = "control.transport.plaintext"

    def test_the_capability_has_several_producers_that_motivate_each_other(self):
        producers = set(self.chain.producers.get(self.FACT, []))
        movers = set(self.chain.motivates.get(self.FACT, []))
        self.assertGreater(len(producers), 1)
        self.assertTrue(movers)
        self.assertTrue(movers <= producers, "the case under test is producers motivating each other")

    def test_it_is_not_a_dead_end_and_edges_really_travel_through_it(self):
        self.assertTrue(self.chain.leads_from(self.FACT))
        self.assertNotIn(self.FACT, self.chain.dead_ends())
        index = self.chain.index()
        travelled = [
            (uid, edge["unit"])
            for uid, entry in index.items()
            for edge in entry["out"]
            if self.FACT in edge.get("via", []) + edge.get("hint", [])
        ]
        self.assertTrue(travelled, "no derived edge travels through it")
        for producer, consumer in travelled:
            self.assertNotEqual(producer, consumer, "a self-edge was counted as a route")

    def test_a_root_the_engagement_supplies_is_never_a_dead_end(self):
        """`access.anon` has no producer, so nothing established it and there is
        no continuation to be missing. Counting a root would inflate the figure
        the README publishes by the size of the given set."""
        for fid in sorted(self.chain.given()):
            self.assertNotIn(fid, self.chain.dead_ends())


class AMalformedRegisterEntryIsReportedRatherThanRaised(SandboxCase):
    """Every pass collects problems rather than raising on the first one, and a
    contributor fixing a batch wants the whole list. Reading a key the schema
    pass has just reported as missing would hand them a traceback instead --
    and a traceback about `cause` says nothing about the field they omitted."""

    @staticmethod
    def _drop(field):
        def mutate(vocab):
            vocab["unconsumed"][0].pop(field)

        return mutate

    def test_an_entry_without_a_cause_still_returns_the_schema_problem(self):
        self.box.edit("vocab/facts.yaml", self._drop("cause"))
        problems = validate(self.box.root)
        self.assertIn("'cause' is a required property", messages(problems))

    def test_an_entry_without_facts_still_returns_the_schema_problem(self):
        self.box.edit("vocab/facts.yaml", self._drop("facts"))
        problems = validate(self.box.root)
        self.assertIn("'facts' is a required property", messages(problems))

    def test_a_facts_field_of_the_wrong_type_does_not_raise(self):
        self.box.edit("vocab/facts.yaml", lambda v: v["unconsumed"][0].update(facts="all of them"))
        problems = validate(self.box.root)
        self.assertTrue(problems, "a string where a list belongs must be reported")


class ANegativeResultClosesOnlyWhatItCouldOpen(SandboxCase):
    def test_closing_a_fact_it_does_not_yield_is_rejected(self):
        self.box.edit(
            "knowledge/inj/PTN-INJ-01-UNION.unit.yaml",
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
            "knowledge/clt/PTN-CLT-01-HTMLBODY.unit.yaml",
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
            "knowledge/rcn/PTN-RCN-03-MAP.unit.yaml",
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

        self.box.edit("knowledge/inj/PTN-INJ-01-UNION.unit.yaml", strip)
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
        link = self.onward("PTN-INJ-01-PROBE").get("PTN-INJ-01-UNION")
        self.assertIsNotNone(link)
        self.assertEqual(link["kind"], "requires")
        self.assertIn("surface.sql.injectable", link["via"])

    def test_a_fingerprint_motivates_rather_than_conditions(self):
        link = self.onward("PTN-INJ-01-FPRINT").get("PTN-INJ-01-UNION")
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
        link = self.onward("PTN-ACL-02-MAP").get("PTN-ACL-02-PEER")
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
            "PTN-A-01-P": {
                "id": "PTN-A-01-P",
                "topic": "PTN-A-01",
                "yields": ["access.user", "artifact.token"],
            },
            "PTN-A-01-GENERIC": {
                "id": "PTN-A-01-GENERIC",
                "topic": "PTN-A-01",
                "requires": {"all_of": ["access.user"]},
            },
            "PTN-B-02-ESCALATION": {
                "id": "PTN-B-02-ESCALATION",
                "topic": "PTN-B-02",
                "requires": {"all_of": ["artifact.token"]},
            },
        }
        index = chain_index(units, given=set(), tiers=TIERS)
        out = index["PTN-A-01-P"]["out"]
        self.assertEqual(
            [e["unit"] for e in out], ["PTN-B-02-ESCALATION", "PTN-A-01-GENERIC"]
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
            "PTN-A-01-P": {
                "id": "PTN-A-01-P",
                "topic": "PTN-A-01",
                "yields": ["access.user", "artifact.token"],
            },
            "PTN-B-02-C": {
                "id": "PTN-B-02-C",
                "topic": "PTN-B-02",
                "requires": {"all_of": ["access.user"]},
                "motivated_by": ["artifact.token"],
            },
        }
        index = chain_index(units, given=set(), tiers=TIERS)
        edge = index["PTN-A-01-P"]["out"][0]
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
            ("PTN-INJ-03-READ", "PTN-RES-01-EXEC"),
            ("PTN-INJ-04-READ", "PTN-RES-01-EXEC"),
            ("PTN-INJ-10-READ", "PTN-RES-01-EXEC"),
            ("PTN-SES-04-READ", "PTN-SES-09-READ"),
            ("PTN-SES-04-READ", "PTN-SES-09-REPLAY"),
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


class EveryUnitSaysHowItStandsToItsSiblings(SandboxCase):
    """"Perform all of these" and "pick one of these" are opposite instructions.

    A topic listed its units flat, so the two were rendered identically and the
    list had to be opened unit by unit to be read. `role` records which, and is
    required rather than derived: deriving it from the identifier's slug would
    tie the reading of a unit to a naming convention and leave no way to record
    that one is an exception to the pattern its slug implies.
    """

    def test_a_unit_without_a_role_is_rejected(self):
        def drop(unit):
            unit.pop("role", None)
            return unit

        self.box.edit("knowledge/inj/PTN-INJ-01-UNION.unit.yaml", drop)
        self.assertRejected("role")

    def test_a_role_outside_the_two_is_rejected(self):
        self.box.edit(
            "knowledge/inj/PTN-INJ-01-UNION.unit.yaml",
            lambda u: u.update(role="sometimes") or u,
        )
        self.assertRejected("role")


class TheRolesReadTheWayTheCatalogueIsWritten(unittest.TestCase):
    """Spot checks against topics whose shape is not in dispute, so a drift in
    the assignment fails here rather than being noticed by a reader."""

    @classmethod
    def setUpClass(cls):
        cls.chain = Chain.load(REPO_ROOT)

    def role(self, uid):
        return self.chain.nodes[uid].role

    def test_a_probe_and_a_fingerprint_are_stages(self):
        for uid in ("PTN-INJ-01-PROBE", "PTN-INJ-01-FPRINT", "PTN-INJ-01-EVADE"):
            self.assertEqual(self.role(uid), "stage", uid)

    def test_the_seven_sql_techniques_are_alternatives(self):
        for slug in ("ERROR", "BOOL", "TIME", "UNION", "OOB", "STACK", "SECOND"):
            uid = f"PTN-INJ-01-{slug}"
            self.assertEqual(self.role(uid), "variant", uid)

    def test_every_unit_declares_one_of_the_two(self):
        for uid, node in self.chain.nodes.items():
            self.assertIn(node.role, ("stage", "variant"), uid)

    def test_no_topic_asks_for_a_choice_before_offering_a_way_in(self):
        """A topic of nothing but alternatives has no entry: the tester is asked
        to pick a route before anything has established there is a surface to
        pick one for. `PTN-ACL-04` was the last of them and now opens with the
        stage that records where privilege is decided, which is the thing all
        three of its routes attack."""
        by_topic = {}
        for node in self.chain.nodes.values():
            by_topic.setdefault(node.topic, []).append(node.role)
        stageless = sorted(t for t, roles in by_topic.items() if "stage" not in roles)
        self.assertEqual(stageless, [])


class TheChainArrivesSomewhere(unittest.TestCase):
    """A capability nothing declares a use for is where a chain stops.

    That was the common case: twenty-six of thirty-two primitives were
    established by a test and consumed by nothing, so most chains ended at the
    capability that reached them rather than at anything a report can carry. The
    outcome layer is what they end at now.
    """

    @classmethod
    def setUpClass(cls):
        cls.chain = Chain.load(REPO_ROOT)

    #: The one capability deliberately left without an outcome. A reproducible
    #: conditional signal is not something a chain arrives at -- it is how a
    #: value is extracted, and what the extraction obtains reaches an outcome
    #: through the capability that carries it. Pinned so that a new orphan, or a
    #: use written for this one, both fail here.
    WITHOUT_AN_OUTCOME = ["primitive.blind.oracle"]

    def test_every_primitive_but_one_is_declared_as_a_use_somewhere(self):
        orphans = sorted(
            f for f in self.chain.dead_ends() if family_of(f) == "primitive"
        )
        self.assertEqual(orphans, self.WITHOUT_AN_OUTCOME)

    def test_every_outcome_is_reachable_from_a_test_or_registered_as_not_yet(self):
        """An impact nothing establishes would sit in the matrix looking like
        coverage, and that is still what this refuses. What changed is that it
        may now be written down instead: the `uncovered` register is the only
        thing that excuses one, it names the reason, and the artefact prints it.

        Asserted in both directions on purpose. An unreachable outcome outside
        the register fails, and a registered outcome that something does
        establish fails too -- an entry that outlives its gap is how a register
        of what is unwritten turns into a place to park vocabulary.
        """
        import yaml

        registered = {
            f
            for entry in yaml.safe_load(
                (REPO_ROOT / "vocab" / "facts.yaml").read_text(encoding="utf-8")
            )["uncovered"]
            for f in entry["facts"]
        }
        for impact in self.chain.impacts():
            with self.subTest(impact=impact):
                if impact in registered:
                    self.assertFalse(self.chain.producers.get(impact), impact)
                else:
                    self.assertTrue(self.chain.producers.get(impact), impact)

    def test_an_outcome_topic_declares_no_surface(self):
        """It is not reached by going somewhere. It is reached by holding
        something, from wherever that was established."""
        import yaml

        for path in (REPO_ROOT / "knowledge" / "out").glob("*.topic.yaml"):
            topic = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertEqual(topic["domain"], "OUT", path.name)
            self.assertNotIn("surfaces", topic, path.name)

    def test_an_outcome_is_asked_rather_than_asserted(self):
        """Pentest NavGrid has not seen the target. Every outcome unit is an inquiry --
        it carries the question the capability makes worth asking, and claims
        nothing about what the answer is."""
        for uid, node in self.chain.nodes.items():
            if uid.startswith("PTN-OUT-"):
                self.assertEqual(node.kind, "inquiry", uid)

    def test_the_worked_example_in_the_readme_runs_to_its_end(self):
        """The README walks path traversal from the standard down to an outcome.
        If any link in it breaks, the document is telling a reader something the
        catalogue no longer does."""
        walk = [
            ("PTN-RES-01-PROBE", "surface.path.traversable"),
            ("PTN-RES-01-READ", "primitive.fs.read"),
            ("PTN-RES-01-EXEC", "primitive.exec.server"),
        ]
        index = self.chain.index()
        for uid, established in walk:
            self.assertIn(established, self.chain.nodes[uid].yields, uid)
        onward = [e["unit"] for e in index["PTN-RES-01-EXEC"]["out"]]
        self.assertIn("PTN-OUT-02-IMPACT", onward)
        self.assertIn(
            "impact.code.executed", self.chain.nodes["PTN-OUT-02-IMPACT"].yields
        )


class AnOutcomeTopicIsHeldToTheSameRules(SandboxCase):
    def test_an_outcome_topic_declaring_a_surface_is_rejected(self):
        """The exemption is for outcomes and cannot be borrowed. A topic that
        named a surface would be claiming something the model has no way to
        honour -- an outcome is reached from wherever its capability was
        established, not from a place."""
        self.box.edit(
            "knowledge/out/PTN-OUT-02.topic.yaml",
            lambda topic: topic.update(surfaces={"any_of": ["login-form"]}) or topic,
        )
        self.assertRejected("schema (topic)")

    def test_an_ordinary_topic_still_has_to_declare_one(self):
        def drop(topic):
            topic.pop("surfaces", None)
            return topic

        self.box.edit("knowledge/inj/PTN-INJ-01.topic.yaml", drop)
        self.assertRejected("surfaces")

    def test_requiring_an_outcome_is_still_rejected(self):
        """Unchanged by the outcome layer, and the rule that keeps it terminal:
        a chain that could continue past an impact would be describing something
        after the end of itself."""
        self.box.edit(
            "knowledge/out/PTN-OUT-02-IMPACT.unit.yaml",
            lambda unit: unit.update(requires={"all_of": ["impact.code.executed"]}) or unit,
        )
        self.assertRejected("impact")


class EveryEscalationGoesSomewhereOrSaysWhyNot(SandboxCase):
    """The mirror of the producer gate.

    A chain-tier fact is currency, so one nothing requires is where the chart
    stops earlier than the mechanism does. Before the register that state passed
    every check: the producer gate asks where a capability comes from, and
    nothing asked where it goes. The register does not forbid a dead end -- a
    growing catalogue honestly has them -- it forbids an unrecorded one, and it
    forbids an entry outliving the gap it describes."""

    REGISTERED = "control.misuse.undetected"

    def _register(self, box):
        return box.read("vocab/facts.yaml")["unconsumed"]

    def test_an_unregistered_dead_end_is_rejected(self):
        def drop(vocab):
            for entry in vocab["unconsumed"]:
                if self.REGISTERED in entry["facts"]:
                    entry["facts"].remove(self.REGISTERED)

        self.box.edit("vocab/facts.yaml", drop)
        self.assertRejected(f"{self.REGISTERED} is chain-tier and 1 unit(s) establish it")

    def test_an_entry_for_a_gap_that_has_closed_is_rejected(self):
        # The half that keeps the register a list of open gaps rather than of
        # suppressions. PTN-ERR-02-PROBE establishes it, so the use is declared
        # from somewhere else -- a unit requiring its own result is rejected
        # several rules earlier.
        self.box.edit(
            "knowledge/err/PTN-ERR-03-PROBE.unit.yaml",
            lambda u: u.update(motivated_by=[self.REGISTERED]),
        )
        self.assertRejected(f"the unconsumed register still lists {self.REGISTERED}")

    def test_registering_a_fact_outside_the_vocabulary_is_rejected(self):
        def invent(vocab):
            vocab["unconsumed"][0]["facts"].append("control.invented.here")

        self.box.edit("vocab/facts.yaml", invent)
        self.assertRejected("the unconsumed register names unknown fact control.invented.here")

    def test_registering_a_fact_of_another_tier_is_rejected(self):
        def wrong_tier(vocab):
            vocab["unconsumed"][0]["facts"].append("surface.sql.injectable")

        self.box.edit("vocab/facts.yaml", wrong_tier)
        self.assertRejected("which is topic-tier")

    def test_one_dead_end_under_two_causes_is_rejected(self):
        def twice(vocab):
            vocab["unconsumed"][1]["facts"].append(self.REGISTERED)

        self.box.edit("vocab/facts.yaml", twice)
        self.assertRejected(f"{self.REGISTERED} appears in the unconsumed register under both")

    def test_two_entries_may_not_share_a_cause(self):
        def clash(vocab):
            vocab["unconsumed"][1]["cause"] = vocab["unconsumed"][0]["cause"]

        self.box.edit("vocab/facts.yaml", clash)
        self.assertRejected("duplicate cause")


class TheRegisterDescribesThisCatalogue(unittest.TestCase):
    """Read against the real files rather than a mutation, because the claim is
    about what is actually recorded: the register is the count of open gaps that
    the roadmap and the artefact report, so it has to equal them."""

    @classmethod
    def setUpClass(cls):
        cls.chain = Chain.load(REPO_ROOT)
        import yaml

        cls.register = yaml.safe_load(
            (REPO_ROOT / "vocab" / "facts.yaml").read_text(encoding="utf-8")
        )["unconsumed"]

    def _listed(self):
        return {f for entry in self.register for f in entry["facts"]}

    def test_it_names_exactly_the_chain_tier_dead_ends(self):
        dead = {
            fid
            for fid in self.chain.dead_ends()
            if self.chain.facts[fid]["tier"] == "chain"
        }
        self.assertEqual(self._listed(), dead)

    def test_no_impact_is_registered(self):
        """An impact is unconsumed by construction. Registering one would record
        a chain reaching its outcome as a chain that failed to continue."""
        self.assertFalse(self._listed() & set(self.chain.impacts()))

    def test_every_registered_fact_is_established_by_something(self):
        for fid in sorted(self._listed()):
            self.assertTrue(self.chain.producers.get(fid), fid)


class ConceptsMayBeWrittenAheadOfTheTests(SandboxCase):
    """The reference gate, which used to be a flat refusal.

    A fact no unit named was rejected outright -- an unreachable fact is
    vocabulary nobody can use -- and that one sentence refused two different
    things: a fact nobody noticed, and the only honest way to write down where
    the catalogue is going. The register separates them, with the same two
    halves the `unconsumed` register has: an unrecorded gap is still rejected,
    and an entry whose gap has closed is rejected too.
    """

    REGISTERED = "impact.persistence.retained"

    def test_a_fact_nothing_names_and_nothing_registers_is_rejected(self):
        def drop(vocab):
            for entry in vocab["uncovered"]:
                if self.REGISTERED in entry["facts"]:
                    entry["facts"].remove(self.REGISTERED)
            vocab["uncovered"] = [e for e in vocab["uncovered"] if e["facts"]]
            if not vocab["uncovered"]:
                vocab.pop("uncovered")

        self.box.edit("vocab/facts.yaml", drop)
        self.assertRejected(
            f"{self.REGISTERED} is declared but no unit requires, yields or is "
            f"motivated by it, and it is not in the uncovered register"
        )

    def test_an_entry_for_a_gap_that_has_closed_is_rejected(self):
        """The half that stops the register becoming a place to park vocabulary.
        A test arriving is the only thing that may remove an entry."""
        self.box.edit(
            "knowledge/biz/PTN-BIZ-08-IMPACT.unit.yaml",
            lambda u: u.update(yields=["impact.money.lost", self.REGISTERED]),
        )
        self.assertRejected(f"the uncovered register still lists {self.REGISTERED}")

    def test_a_motivation_alone_closes_the_gap(self):
        """Naming, not establishing. The gate asks whether the catalogue has
        arrived at the concept at all, and a unit that names it as a motivation
        has -- so the entry has to go even though nothing yields it yet."""
        self.box.edit(
            "knowledge/biz/PTN-BIZ-08-IMPACT.unit.yaml",
            lambda u: u.update(motivated_by=[self.REGISTERED]),
        )
        self.assertRejected(f"the uncovered register still lists {self.REGISTERED}")

    def test_registering_a_fact_outside_the_vocabulary_is_rejected(self):
        self.box.edit(
            "vocab/facts.yaml",
            lambda v: v["uncovered"][0]["facts"].append("impact.invented.here"),
        )
        self.assertRejected("the uncovered register names unknown fact impact.invented.here")

    def test_one_gap_under_two_causes_is_rejected(self):
        def twice(vocab):
            vocab["uncovered"].append({
                "cause": "a-second-reason-for-the-same-thing",
                "reason": "A second entry naming a fact the first already names, which is "
                          "the shape that splits one gap across two reasons nobody reads.",
                "facts": [self.REGISTERED],
            })

        self.box.edit("vocab/facts.yaml", twice)
        self.assertRejected(f"{self.REGISTERED} appears in the uncovered register under both")

    def test_two_entries_may_not_share_a_cause(self):
        def clash(vocab):
            vocab["uncovered"].append({
                "cause": vocab["uncovered"][0]["cause"],
                "reason": "The same cause stated twice, which splits the facts that share "
                          "it and leaves the second reason where nobody reads it.",
                "facts": ["impact.money.lost"],
            })

        self.box.edit("vocab/facts.yaml", clash)
        self.assertRejected("duplicate cause")


class TheRegisterDoesNotExcuseABrokenChain(SandboxCase):
    """The boundary the register must not move, tested from both sides.

    A fact a unit requires that nothing establishes is a hole, and it reads from
    the outside exactly like a route nobody has taken yet -- which is precisely
    what the uncovered register is for. So the one way this change could go
    wrong is the register being usable to silence that. It cannot: a required
    fact is a named fact, so the entry is rejected as a gap that has closed
    while the producer gate goes on rejecting the hole.
    """

    ORPHAN = "recon.entrypoints.mapped"

    def _break_the_producer(self):
        # The only unit establishing the entry-point inventory, which most of
        # the catalogue is conditioned on.
        self.box.edit(
            "knowledge/rcn/PTN-RCN-03-MAP.unit.yaml",
            lambda u: u.update(yields=["recon.hosts.enumerated"]),
        )

    def test_the_producer_gate_still_rejects_it(self):
        self._break_the_producer()
        self.assertRejected(f"{self.ORPHAN} is required but no unit establishes it")

    def test_registering_it_does_not_silence_the_producer_gate(self):
        self._break_the_producer()
        self.box.edit(
            "vocab/facts.yaml",
            lambda v: v["uncovered"][0]["facts"].append(self.ORPHAN),
        )
        problems = validate(self.box.root)
        text = messages(problems)
        self.assertIn(f"{self.ORPHAN} is required but no unit establishes it", text)
        # And the attempt is itself reported, rather than passing quietly.
        self.assertIn(f"the uncovered register still lists {self.ORPHAN}", text)


class TheUncoveredRegisterDescribesThisCatalogue(unittest.TestCase):
    """Against the real files, for the reason its sibling above is: the register
    is the figure the README, the roadmap and the artefact all publish, so it
    has to equal what the catalogue actually holds."""

    @classmethod
    def setUpClass(cls):
        import yaml

        cls.chain = Chain.load(REPO_ROOT)
        cls.register = yaml.safe_load(
            (REPO_ROOT / "vocab" / "facts.yaml").read_text(encoding="utf-8")
        )["uncovered"]

    def _listed(self):
        return {f for entry in self.register for f in entry["facts"]}

    def _named_by_a_unit(self):
        named = set()
        for unit in self.chain.units.values():
            requires = unit.get("requires") or {}
            named |= set(requires.get("all_of") or [])
            named |= set(requires.get("any_of") or [])
            named |= set(unit.get("yields") or [])
            named |= set(unit.get("motivated_by") or [])
        return named

    def test_it_names_exactly_the_facts_no_unit_names(self):
        self.assertEqual(self._listed(), set(self.chain.facts) - self._named_by_a_unit())

    def test_nothing_is_in_both_registers(self):
        """The two registers answer opposite questions -- nothing consumes it,
        and nothing names it -- so a fact in both would mean one of them is
        wrong about the same fact."""
        import yaml

        unconsumed = yaml.safe_load(
            (REPO_ROOT / "vocab" / "facts.yaml").read_text(encoding="utf-8")
        )["unconsumed"]
        self.assertFalse(
            self._listed() & {f for entry in unconsumed for f in entry["facts"]}
        )

    def test_every_entry_carries_a_reason_that_is_written_rather_than_a_label(self):
        for entry in self.register:
            with self.subTest(cause=entry["cause"]):
                self.assertGreater(len(entry["reason"].split()), 40, entry["cause"])
