"""The artefact's own behaviour.

Every assertion here used to be a substring match on the rendered page, which a
script with an unterminated string literal satisfies exactly as well as a
working one -- the whole application can be dead and the suite green. `app.js`
exports its pure functions and does nothing on load without a document, so the
graph model, its layout, the path walk and the search index are called for real.

Two runners, both optional and both local:

* **node** already checks that the script parses. Here it runs it.
* **a browser**, if one is installed, opens the built file from `file://` and
  reports the DOM its script produced. That is the only way to test the routing,
  the Content-Security-Policy and the rendered wording together, and it is
  skipped rather than required so the suite still runs offline on a machine that
  has never installed one.
"""

import re
import collections
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from harrier.build import build, catalogue
from tests.support import (
    Page,
    REPO_ROOT,
    browser_available,
    node_available,
    run_in_node,
)


@unittest.skipUnless(node_available(), "node is not installed")
class TheLocalGraphModel(unittest.TestCase):
    """What a reader is shown around one test, computed rather than asserted."""

    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)

    def run_js(self, body):
        return run_in_node(body, self.data)

    def test_the_tier_totals_count_every_edge_not_the_bounded_preview(self):
        """The count beside each heading is what makes the engagement list safe
        to skip. Taken from the three-item preview it would read "(1)" where the
        truth is ninety -- and a reader would believe it, which is worse than
        showing no count at all."""
        result = self.run_js("""
            const out = {};
            Object.keys(D.units).forEach(function (id) {
              const g = H.localGraph(D, id, 3);
              const real = {};
              (D.chain[id].out || []).forEach(function (e) {
                real[e.tier] = (real[e.tier] || 0) + 1;
              });
              const got = g.tierTotals || {};
              if (JSON.stringify(real) !== JSON.stringify(got)) out[id] = [real, got];
            });
            return out;
        """)
        self.assertEqual(result, {}, "tierTotals disagrees with the derivation")

    def test_the_totals_survive_the_preview_being_smaller_than_the_tier(self):
        result = self.run_js("""
            const g = H.localGraph(D, "HRR-IDN-01-POLICY", 3);
            return {
              shown: g.outgoing.shown.length,
              engagement: g.tierTotals.engagement,
              chain: g.tierTotals.chain
            };
        """)
        self.assertEqual(result["shown"], 3)
        # Derived, not written down: the point is that the totals exceed the
        # preview, and a literal here would go stale the first time a unit is
        # added -- which is the failure these counts exist to prevent.
        edges = self.data["chain"]["HRR-IDN-01-POLICY"]["out"]
        expected = collections.Counter(e["tier"] for e in edges)
        self.assertEqual(result["chain"], expected["chain"])
        self.assertEqual(result["engagement"], expected["engagement"])
        self.assertGreater(result["engagement"], result["shown"])

    def test_it_is_bounded_before_it_is_expanded(self):
        result = self.run_js("""
            const out = {};
            Object.keys(D.units).forEach(function (id) {
              const g = H.localGraph(D, id, 3);
              out.in = Math.max(out.in || 0, g.incoming.shown.length);
              out.out = Math.max(out.out || 0, g.outgoing.shown.length);
              out.yields = Math.max(out.yields || 0, g.yields.shown.length);
              if (g.outgoing.hidden > 0) out.someHidden = true;
            });
            return out;
        """)
        self.assertLessEqual(result["in"], 3)
        self.assertLessEqual(result["out"], 3)
        self.assertLessEqual(result["yields"], 3)
        self.assertTrue(result["someHidden"], "nothing in the catalogue is ever truncated")

    def test_expanding_shows_more_than_the_initial_view(self):
        result = self.run_js("""
            const id = Object.keys(D.units).filter(function (u) {
              return H.localGraph(D, u, 3).outgoing.hidden > 0;
            }).sort()[0];
            const small = H.localGraph(D, id, 3);
            const big = H.localGraph(D, id, 9999);
            return {
              id: id,
              small: small.outgoing.shown.length,
              big: big.outgoing.shown.length,
              hidden: small.outgoing.hidden
            };
        """)
        self.assertEqual(result["small"], 3)
        self.assertGreater(result["big"], result["small"])
        self.assertEqual(result["hidden"], result["big"] - result["small"])

    def test_a_producer_shown_for_a_prerequisite_actually_yields_it(self):
        bad = self.run_js("""
            const bad = [];
            Object.keys(D.units).forEach(function (id) {
              H.localGraph(D, id, 9999).incoming.shown.forEach(function (link) {
                link.producers.forEach(function (p) {
                  if ((D.units[p].yields || []).indexOf(link.fact) < 0) bad.push([id, p, link.fact]);
                });
              });
            });
            return bad;
        """)
        self.assertEqual(bad, [])

    def test_a_continuation_actually_consumes_something_established_here(self):
        bad = self.run_js("""
            const bad = [];
            Object.keys(D.units).forEach(function (id) {
              const g = H.localGraph(D, id, 9999);
              const made = (D.units[id].yields || []);
              g.outgoing.shown.forEach(function (link) {
                const reasons = link.via.concat(link.hint);
                if (!reasons.length) bad.push([id, link.unit, "no reason"]);
                reasons.forEach(function (f) {
                  if (made.indexOf(f) < 0) bad.push([id, link.unit, f]);
                });
              });
            });
            return bad;
        """)
        self.assertEqual(bad, [])

    def test_a_motivation_is_a_different_kind_of_edge_from_a_requirement(self):
        result = self.run_js("""
            let hard = 0, soft = 0, mixed = 0;
            Object.keys(D.units).forEach(function (id) {
              H.localGraph(D, id, 9999).outgoing.shown.forEach(function (link) {
                if (link.kind === "requires") hard++;
                else if (link.kind === "motivated_by") soft++;
                else mixed++;
                if (link.kind === "motivated_by" && link.via.length) mixed++;
              });
            });
            return {hard: hard, soft: soft, mixed: mixed};
        """)
        self.assertGreater(result["hard"], 0)
        self.assertGreater(result["soft"], 0)
        self.assertEqual(result["mixed"], 0, "a hint has become indistinguishable from a gate")

    def test_a_prerequisite_the_engagement_supplies_is_labelled_rather_than_orphaned(self):
        result = self.run_js("""
            const roots = [];
            Object.keys(D.units).forEach(function (id) {
              H.localGraph(D, id, 9999).incoming.shown.forEach(function (link) {
                if (link.given) roots.push([id, link.fact, link.producers.length]);
              });
            });
            return roots;
        """)
        self.assertTrue(result, "no unit requires a root of the graph any more")
        for _, fact, producers in result:
            self.assertIn(fact, self.data["given"])

    def test_an_impact_is_shown_as_where_a_chain_ends(self):
        result = self.run_js("""
            const out = [];
            Object.keys(D.units).forEach(function (id) {
              const g = H.localGraph(D, id, 9999);
              g.yields.shown.forEach(function (y) {
                if (y.family === "impact") out.push([id, y.fact, y.terminal, y.consumers.length]);
              });
            });
            return out;
        """)
        self.assertTrue(result, "no unit establishes an impact any more")
        for _, _, terminal, consumers in result:
            self.assertEqual(terminal, "impact")
            self.assertEqual(consumers, 0)

    def test_a_test_that_leads_nowhere_says_so_rather_than_drawing_nothing(self):
        result = self.run_js("""
            let leaf = 0, allTerminal = 0, silent = 0;
            Object.keys(D.units).forEach(function (id) {
              const g = H.localGraph(D, id, 9999);
              if (g.leaf) leaf++;
              else if (!g.outgoing.shown.length) {
                if (g.allTerminal || g.terminal.length) allTerminal++;
                else silent++;
              }
            });
            return {leaf: leaf, allTerminal: allTerminal, silent: silent};
        """)
        self.assertGreater(result["leaf"] + result["allTerminal"], 0)
        self.assertEqual(result["silent"], 0, "a dead end is being drawn with no explanation")

    def test_a_unit_with_several_routes_is_not_rendered_as_a_line(self):
        result = self.run_js("""
            const g = H.localGraph(D, "HRR-INJ-01-UNION", 9999);
            return {
              incoming: g.incoming.shown.length,
              kinds: g.incoming.shown.map(function (l) { return l.kind; })
            };
        """)
        self.assertGreater(result["incoming"], 2)
        self.assertIn("any_of", result["kinds"])
        self.assertIn("all_of", result["kinds"])

    def test_an_unknown_identifier_produces_nothing_rather_than_a_shape(self):
        for name in ("__proto__", "constructor", "toString", "NOPE"):
            self.assertIsNone(
                self.run_js("return H.localGraph(D, %r, 3);" % name), name
            )


@unittest.skipUnless(node_available(), "node is not installed")
class TheNegativeReading(unittest.TestCase):
    """A clean result rules out less than it looks like it does, and the page has
    to be the thing that says so."""

    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)

    def test_a_clean_union_result_does_not_exclude_sql_injection(self):
        result = run_in_node("""
            const r = H.negativeReading(D, "HRR-INJ-01-UNION");
            return {
              closes: r.closes,
              open: r.open.map(function (o) { return [o.fact, o.others.length]; })
            };
        """, self.data)
        self.assertEqual(result["closes"], [])
        self.assertTrue(result["open"])
        for fact, others in result["open"]:
            self.assertGreater(others, 0, f"{fact} is shown as having no alternative route")

    def test_only_a_sole_producer_is_shown_as_settling_anything(self):
        bad = run_in_node("""
            const bad = [];
            Object.keys(D.units).forEach(function (id) {
              H.negativeReading(D, id).closes.forEach(function (f) {
                if ((D.producers[f] || []).length !== 1) bad.push([id, f]);
              });
            });
            return bad;
        """, self.data)
        self.assertEqual(bad, [])

    def test_an_alternative_route_is_never_the_test_itself(self):
        bad = run_in_node("""
            const bad = [];
            Object.keys(D.units).forEach(function (id) {
              H.negativeReading(D, id).open.forEach(function (o) {
                if (o.others.indexOf(id) >= 0) bad.push([id, o.fact]);
              });
            });
            return bad;
        """, self.data)
        self.assertEqual(bad, [])


@unittest.skipUnless(node_available(), "node is not installed")
class TheGeneralGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)

    def test_the_family_summary_matches_the_source_data(self):
        result = run_in_node("return H.familyOverview(D);", self.data)
        self.assertEqual(
            [n["name"] for n in result["nodes"]],
            [f["name"] for f in self.data["families"]],
        )
        for node in result["nodes"]:
            family = [f for f in self.data["families"] if f["name"] == node["name"]][0]
            self.assertEqual(node["facts"], len(family["facts"]))
            produced = sum(len(self.data["producers"].get(f, [])) for f in family["facts"])
            required = sum(len(self.data["requiredBy"].get(f, [])) for f in family["facts"])
            self.assertEqual(node["produced"], produced)
            self.assertEqual(node["required"], required)

    def test_a_drill_down_never_names_something_the_file_does_not_carry(self):
        bad = run_in_node("""
            const bad = [];
            const names = H.familyOverview(D).nodes.map(function (n) { return n.name; });
            D.familyEdges.forEach(function (e) {
              if (names.indexOf(e.from) < 0) bad.push(e.from);
              if (names.indexOf(e.to) < 0) bad.push(e.to);
            });
            D.families.forEach(function (f) {
              f.facts.forEach(function (fact) {
                if (!H.own(D.facts, fact)) bad.push(fact);
                (D.producers[fact] || []).concat(D.requiredBy[fact] || [])
                  .forEach(function (u) { if (!H.own(D.units, u)) bad.push(u); });
              });
            });
            return bad;
        """, self.data)
        self.assertEqual(bad, [])

    def test_a_path_ends_at_an_impact_and_keeps_the_reason_for_every_step(self):
        result = run_in_node("""
            const starts = Object.keys(D.facts).filter(function (f) {
              return H.familyOf(f) !== "impact";
            }).sort();
            const found = [];
            for (let i = 0; i < starts.length && found.length < 12; i++) {
              const routes = H.pathsToImpact(D, starts[i], {maxPaths: 2, maxDepth: 5});
              routes.forEach(function (r) { found.push(r); });
            }
            return found;
        """, self.data)
        self.assertTrue(result, "no capability reaches an impact within five steps")
        for route in result:
            self.assertTrue(route["impact"].startswith("impact."))
            self.assertEqual(route["steps"][-1]["to"], route["impact"])
            previous = route["start"]
            for step in route["steps"]:
                self.assertEqual(step["from"], previous)
                self.assertIn(step["unit"], self.data["units"])
                # The reason: this unit really does consume the capability on
                # its left and establish the one on its right.
                unit = self.data["units"][step["unit"]]
                requires = unit.get("requires") or {}
                hard = set(requires.get("all_of") or []) | set(requires.get("any_of") or [])
                self.assertIn(step["from"], hard)
                self.assertIn(step["to"], unit.get("yields") or [])
                previous = step["to"]

    def test_the_readme_states_the_real_number_of_charted_routes_to_an_impact(self):
        """The figure a reader uses to judge how far the chain actually runs.
        Only the walk can produce it, so it is pinned where the walk lives."""
        result = run_in_node("""
            let withRoute = 0, total = 0;
            Object.keys(D.facts).forEach(function (f) {
              if (H.familyOf(f) === "impact") return;
              total++;
              if (H.pathsToImpact(D, f, {maxPaths: 5, maxDepth: 6}).length) withRoute++;
            });
            return {withRoute: withRoute, total: total};
        """, self.data)
        readme = " ".join((REPO_ROOT / "README.md").read_text(encoding="utf-8").split())
        self.assertIn(
            f"| Capabilities with a charted route to an impact | "
            f"{result['withRoute']} of {result['total']} |",
            readme,
        )
        # The prose has to carry the figure too, because that is the sentence a
        # reader takes away. Asserted as the number rather than as a phrasing:
        # the adjective that fitted twelve does not fit ninety, and a test that
        # pins the editorial rather than the fact makes the document wrong to
        # keep it green.
        self.assertIn(
            f"{result['withRoute']} of {result['total']} capabilities have a charted route",
            readme,
        )

    def test_the_readme_states_the_real_number_of_derived_edges(self):
        edges = sum(len(e["out"]) for e in self.data["chain"].values())
        readme = " ".join((REPO_ROOT / "README.md").read_text(encoding="utf-8").split())
        self.assertIn(f"| Derived unit-to-unit edges | {edges} |", readme)

    def test_shorter_routes_come_first(self):
        result = run_in_node("""
            const out = [];
            Object.keys(D.facts).sort().forEach(function (f) {
              const routes = H.pathsToImpact(D, f, {maxPaths: 5, maxDepth: 6});
              if (routes.length > 1) out.push(routes.map(function (r) { return r.steps.length; }));
            });
            return out.slice(0, 40);
        """, self.data)
        self.assertTrue(result)
        for lengths in result:
            self.assertEqual(lengths, sorted(lengths))

    def test_two_routes_through_the_same_capability_are_both_reported(self):
        """The failure a shared visited set caused, and the reason the walk
        keeps its history per path instead.

        Two tests establish the same capability. Marking it visited globally
        lets whichever route reached it first claim it and silently discards the
        other -- and where the first route cannot continue and the second can,
        the discarded one was the answer."""
        forked = {
            "facts": {"a.start": {}, "a.mid": {}, "impact.done": {}},
            "given": [],
            "units": {
                "HRR-A-01-P": {"id": "HRR-A-01-P", "requires": {"all_of": ["a.start"]}, "yields": ["a.mid"]},
                "HRR-A-01-Q": {"id": "HRR-A-01-Q", "requires": {"all_of": ["a.start"]}, "yields": ["a.mid"]},
                "HRR-A-01-Z": {"id": "HRR-A-01-Z", "requires": {"all_of": ["a.mid"]}, "yields": ["impact.done"]},
            },
            "requiredBy": {"a.start": ["HRR-A-01-P", "HRR-A-01-Q"], "a.mid": ["HRR-A-01-Z"]},
        }
        routes = run_in_node(
            "return H.pathsToImpact(D, 'a.start', {maxPaths: 9, maxDepth: 5});", forked
        )
        self.assertEqual(
            sorted(tuple(s["unit"] for s in r["steps"]) for r in routes),
            [("HRR-A-01-P", "HRR-A-01-Z"), ("HRR-A-01-Q", "HRR-A-01-Z")],
        )

    def test_every_step_carries_the_conditions_that_step_still_owes(self):
        """A route stated only the first edge's unmet conditions before. A unit
        three steps in has its own, and they are what makes the route honest."""
        result = run_in_node("""
            const out = [];
            Object.keys(D.facts).sort().forEach(function (f) {
              H.pathsToImpact(D, f, {maxPaths: 2, maxDepth: 5}).forEach(function (r) {
                r.steps.forEach(function (s, i) { out.push([s.unit, i, s.also]); });
              });
            });
            return out;
        """, self.data)
        self.assertTrue(result)
        carried = 0
        for uid, position, also in result:
            self.assertIsNotNone(also, uid)
            unit = self.data["units"][uid]
            declared = set((unit.get("requires") or {}).get("all_of") or [])
            for fact in also["all_of"]:
                self.assertIn(fact, declared, uid)
            if also["all_of"] or also["any_of"]:
                carried += 1
        self.assertGreater(carried, 0, "no step in any route still owes anything")

    def test_performing_a_unit_establishes_everything_it_yields(self):
        """Carrying only the capability the route continues through understated
        what the route had in hand, so a later step was reported as still owing
        a condition an earlier step had already established."""
        multi = {
            "facts": {"a.1": {}, "b.1": {}, "b.2": {}, "impact.done": {}},
            "given": [],
            "units": {
                "HRR-A-01-X": {"id": "HRR-A-01-X", "requires": {"all_of": ["a.1"]},
                               "yields": ["b.1", "b.2"]},
                "HRR-A-01-Z": {"id": "HRR-A-01-Z", "requires": {"all_of": ["b.1", "b.2"]},
                               "yields": ["impact.done"]},
            },
            "requiredBy": {"a.1": ["HRR-A-01-X"], "b.1": ["HRR-A-01-Z"], "b.2": ["HRR-A-01-Z"]},
        }
        routes = run_in_node(
            "return H.pathsToImpact(D, 'a.1', {maxPaths: 9, maxDepth: 5});", multi
        )
        self.assertTrue(routes)
        for route in routes:
            final = route["steps"][-1]
            self.assertEqual(final["unit"], "HRR-A-01-Z")
            self.assertEqual(
                final["also"], {"all_of": [], "any_of": []},
                "X yielded both, so Z owes nothing on either route",
            )

    def test_one_unit_reached_by_two_capabilities_is_two_routes(self):
        """A route is its whole shape -- the capability each step arrives on,
        the unit, the capability it leaves on -- not its unit list. Identifying
        it by units alone collapses these two into one and drops the other."""
        multi = {
            "facts": {"a.1": {}, "b.1": {}, "b.2": {}, "impact.done": {}},
            "given": [],
            "units": {
                "HRR-A-01-X": {"id": "HRR-A-01-X", "requires": {"all_of": ["a.1"]},
                               "yields": ["b.1", "b.2"]},
                "HRR-A-01-Z": {"id": "HRR-A-01-Z", "requires": {"any_of": ["b.1", "b.2"]},
                               "yields": ["impact.done"]},
            },
            "requiredBy": {"a.1": ["HRR-A-01-X"], "b.1": ["HRR-A-01-Z"], "b.2": ["HRR-A-01-Z"]},
        }
        routes = run_in_node(
            "return H.pathsToImpact(D, 'a.1', {maxPaths: 9, maxDepth: 5});", multi
        )
        shapes = sorted(
            tuple((s["from"], s["unit"], s["to"]) for s in r["steps"]) for r in routes
        )
        self.assertEqual(shapes, [
            (("a.1", "HRR-A-01-X", "b.1"), ("b.1", "HRR-A-01-Z", "impact.done")),
            (("a.1", "HRR-A-01-X", "b.2"), ("b.2", "HRR-A-01-Z", "impact.done")),
        ])
        self.assertEqual(
            {tuple(s["unit"] for s in r["steps"]) for r in routes},
            {("HRR-A-01-X", "HRR-A-01-Z")},
            "the two routes share their units, which is why units alone cannot identify them",
        )

    def test_a_route_that_revisits_a_capability_is_not_extended(self):
        """The yields now added wholesale must not become a way back round: a
        capability already in the path's history is not stepped onto again."""
        loop = {
            "facts": {"a.1": {}, "a.2": {}, "impact.done": {}},
            "given": [],
            "units": {
                "HRR-A-01-X": {"id": "HRR-A-01-X", "requires": {"all_of": ["a.1"]},
                               "yields": ["a.2", "a.1"]},
                "HRR-A-01-Z": {"id": "HRR-A-01-Z", "requires": {"all_of": ["a.2"]},
                               "yields": ["impact.done"]},
            },
            "requiredBy": {"a.1": ["HRR-A-01-X"], "a.2": ["HRR-A-01-Z"]},
        }
        routes = run_in_node(
            "return H.pathsToImpact(D, 'a.1', {maxPaths: 9, maxDepth: 6});", loop
        )
        self.assertEqual(
            [tuple(s["to"] for s in r["steps"]) for r in routes],
            [("a.2", "impact.done")],
        )

    def test_what_earlier_steps_established_counts_at_a_later_one(self):
        """The same unit owes different things depending on how it was reached.

        Y declares both capabilities. Reached directly it still owes the one
        nothing established; reached through X it owes nothing, because X
        established it on the way. A walk that computed the conditions once, at
        the first edge, would report the same answer for both -- cautious in one
        case and wrong in the other."""
        result = run_in_node("""
            const chained = {
              facts: {"a.one": {}, "a.two": {}, "impact.done": {}},
              given: [],
              units: {
                "HRR-A-01-X": {id: "HRR-A-01-X", requires: {all_of: ["a.one"]}, yields: ["a.two"]},
                "HRR-A-01-Y": {id: "HRR-A-01-Y", requires: {all_of: ["a.two", "a.one"]}, yields: ["impact.done"]}
              },
              requiredBy: {"a.one": ["HRR-A-01-X", "HRR-A-01-Y"], "a.two": ["HRR-A-01-Y"]}
            };
            return H.pathsToImpact(chained, "a.one", {maxPaths: 5, maxDepth: 4});
        """, self.data)
        routes = {
            tuple(step["unit"] for step in r["steps"]): r["steps"][-1]["also"]
            for r in result
        }
        self.assertEqual(
            routes.get(("HRR-A-01-Y",)), {"all_of": ["a.two"], "any_of": []},
            "reached directly, Y still owes what nothing established",
        )
        self.assertEqual(
            routes.get(("HRR-A-01-X", "HRR-A-01-Y")), {"all_of": [], "any_of": []},
            "reached through X, Y owes nothing: X established it on the way",
        )

    def test_the_walk_stops_rather_than_running_without_a_bound(self):
        result = run_in_node("""
            const before = Date.now();
            const routes = H.pathsToImpact(D, "recon.target.reachable",
                                           {maxPaths: 99, maxDepth: 12, maxExplore: 500});
            return {routes: routes.length, ms: Date.now() - before};
        """, self.data)
        self.assertLess(result["ms"], 4000, "the walk is not bounded")

    def test_a_cycle_terminates_rather_than_walking_for_ever(self):
        cyclic = {
            "facts": {"a.one": {}, "a.two": {}, "impact.done": {}},
            "units": {
                "HRR-A-01-X": {"id": "HRR-A-01-X", "requires": {"all_of": ["a.one"]}, "yields": ["a.two"]},
                "HRR-A-01-Y": {"id": "HRR-A-01-Y", "requires": {"all_of": ["a.two"]}, "yields": ["a.one"]},
                "HRR-A-01-Z": {"id": "HRR-A-01-Z", "requires": {"all_of": ["a.two"]}, "yields": ["impact.done"]},
            },
            "requiredBy": {"a.one": ["HRR-A-01-X"], "a.two": ["HRR-A-01-Y", "HRR-A-01-Z"]},
        }
        result = run_in_node(
            "return H.pathsToImpact(D, 'a.one', {maxPaths: 9, maxDepth: 9});", cyclic
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["impact"], "impact.done")
        self.assertEqual(len(result[0]["steps"]), 2)

    def test_a_walk_never_visits_the_same_test_twice_in_one_route(self):
        bad = run_in_node("""
            const bad = [];
            Object.keys(D.facts).sort().slice(0, 60).forEach(function (f) {
              H.pathsToImpact(D, f, {maxPaths: 3, maxDepth: 6}).forEach(function (r) {
                const seen = {};
                r.steps.forEach(function (s) {
                  if (seen[s.unit]) bad.push([f, s.unit]);
                  seen[s.unit] = true;
                });
              });
            });
            return bad;
        """, self.data)
        self.assertEqual(bad, [])

    def test_an_impact_is_never_a_starting_point_with_somewhere_to_go(self):
        result = run_in_node("""
            return D.impacts.map(function (f) {
              return [f, H.pathsToImpact(D, f, {maxPaths: 3, maxDepth: 4}).length];
            });
        """, self.data)
        self.assertTrue(result)
        for fact, routes in result:
            self.assertEqual(routes, 0, f"{fact} is not terminal")


@unittest.skipUnless(node_available(), "node is not installed")
class TheLayoutIsDeterministic(unittest.TestCase):
    """No layout library, so the geometry is this project's and is testable."""

    def test_columns_advance_and_nodes_within_one_do_not_overlap(self):
        result = run_in_node("""
            const plan = H.layout([
              {heading: "a", nodes: [{id: "1", title: "one", sub: "s"}, {id: "2", title: "two", sub: "s"}]},
              {heading: "b", nodes: [{id: "3", title: "three", sub: "s"}]},
              {heading: "c", nodes: []}
            ]);
            return {
              width: plan.width, height: plan.height,
              nodes: plan.nodes.map(function (n) {
                return {id: n.id, col: n.col, x: n.x, y: n.y, w: n.w, h: n.h};
              })
            };
        """, {})
        nodes = {n["id"]: n for n in result["nodes"]}
        self.assertLess(nodes["1"]["x"], nodes["3"]["x"])
        self.assertGreaterEqual(
            nodes["2"]["y"], nodes["1"]["y"] + nodes["1"]["h"], "two nodes overlap"
        )
        for node in result["nodes"]:
            self.assertLessEqual(node["x"] + node["w"], result["width"])
            self.assertLessEqual(node["y"] + node["h"], result["height"])

    def test_a_single_node_column_is_centred_against_a_taller_one(self):
        result = run_in_node("""
            const plan = H.layout([
              {heading: "a", nodes: [{id: "1"}, {id: "2"}, {id: "3"}]},
              {heading: "b", nodes: [{id: "4"}]}
            ]);
            const by = {};
            plan.nodes.forEach(function (n) { by[n.id] = n; });
            return {tallMid: (by["1"].y + by["3"].y + by["3"].h) / 2, oneMid: by["4"].y + by["4"].h / 2};
        """, {})
        self.assertAlmostEqual(result["tallMid"], result["oneMid"], places=6)

    def test_the_same_input_lays_out_the_same_way_twice(self):
        result = run_in_node("""
            const make = function () {
              return H.layout([{heading: "a", nodes: [{id: "1"}, {id: "2"}]}]).nodes;
            };
            return JSON.stringify(make()) === JSON.stringify(make());
        """, {})
        self.assertTrue(result)

    def test_a_long_title_is_truncated_rather_than_overflowing_its_box(self):
        result = run_in_node("""
            return {
              short: H.wrap("two words", 25, 2),
              long: H.wrap("a title far longer than any box on the page could ever hold in two lines", 25, 2),
              empty: H.wrap("", 25, 2)
            };
        """, {})
        self.assertEqual(result["short"], ["two words"])
        self.assertEqual(len(result["long"]), 2)
        self.assertTrue(result["long"][1].endswith("…"))
        for line in result["long"]:
            self.assertLessEqual(len(line), 25)
        self.assertEqual(result["empty"], [])


@unittest.skipUnless(node_available(), "node is not installed")
class SearchRetrievesEverythingTheFileCarries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)

    def kinds(self, term):
        return run_in_node(
            "return H.searchAll(D, %r).map(function (g) { return [g.kind, g.items.length]; });" % term,
            self.data,
        )

    def test_a_test_case_identifier_finds_the_test_case(self):
        self.assertIn(["Test cases", 1], self.kinds("WSTG-INPV-05"))

    def test_a_technique_name_finds_tests_and_payloads(self):
        found = dict(self.kinds("union"))
        self.assertIn("Tests", found)
        self.assertIn("Payloads", found)

    def test_a_parameter_name_finds_the_test_that_starts_from_it(self):
        """The one route into the catalogue that does not begin at the standard:
        a tester who has just seen a parameter named `tpl` cannot get here from
        WSTG, and `triage` is where that name is written down."""
        hits = run_in_node("""
            return H.searchAll(D, "tpl").filter(function (g) { return g.kind === "Tests"; })
              .map(function (g) { return g.items.map(function (i) { return i.sub; }); })[0] || [];
        """, self.data)
        self.assertIn("HRR-RES-01-PROBE", hits)
        # Not reachable from the title or the objective, which is the point.
        unit = self.data["units"]["HRR-RES-01-PROBE"]
        self.assertNotIn("tpl", (unit["title"] + unit["objective"]).lower())

    def test_a_sink_is_searchable_as_prose(self):
        hits = run_in_node("""
            return H.searchAll(D, "file resolver").filter(function (g) { return g.kind === "Tests"; })
              .map(function (g) { return g.items.length; })[0] || 0;
        """, self.data)
        self.assertGreater(hits, 0)

    def test_a_capability_is_retrievable_by_its_label(self):
        self.assertIn("Capabilities", dict(self.kinds("session identifier")))

    def test_prose_only_in_a_card_is_still_found(self):
        result = run_in_node("""
            const key = Object.keys(D.cards)[0];
            const words = D.cards[key].split(/\\s+/).filter(function (w) { return w.length > 9; });
            const groups = H.searchAll(D, words[0]);
            return {word: words[0], kinds: groups.map(function (g) { return g.kind; })};
        """, self.data)
        self.assertIn("Cards", result["kinds"], result["word"])

    def test_every_result_says_what_kind_of_thing_it_is_and_where_it_goes(self):
        bad = run_in_node("""
            const bad = [];
            ["union", "session", "WSTG-INPV-05", "sqlmap"].forEach(function (term) {
              H.searchAll(D, term).forEach(function (group) {
                if (!group.kind) bad.push(["no kind", term]);
                group.items.forEach(function (item) {
                  if (!item.title) bad.push(["no title", term, group.kind]);
                  if (item.href && item.href.indexOf("#/") !== 0) bad.push(["bad href", item.href]);
                });
              });
            });
            return bad;
        """, self.data)
        self.assertEqual(bad, [])

    def test_a_route_a_result_points_at_names_something_that_exists(self):
        """Every kind is checked, not only the kinds that happen to have a
        store. The earlier version skipped any href whose head it did not
        recognise, so a result pointing at a route the router never implemented
        passed silently -- which is exactly what payloads and tools were doing."""
        bad = run_in_node("""
            const stores = {
              unit: D.units, topic: D.topics, case: D.wstg, capability: D.facts,
              payloads: D.payloads, tools: D.toolbox
            };
            const bad = [];
            ["union", "injection", "WSTG-INPV", "cookie", "sqlmap", "burp",
             "traversal", "session"].forEach(function (term) {
              H.searchAll(D, term).forEach(function (group) {
                group.items.forEach(function (item) {
                  if (!item.href) return;
                  const parts = item.href.replace("#/", "").split("/").map(decodeURIComponent);
                  if (!H.own(stores, parts[0])) { bad.push(["unknown kind", item.href]); return; }
                  if (parts.length < 2 || !parts[1]) { bad.push(["no identifier", item.href]); return; }
                  if (!H.own(stores[parts[0]], parts[1])) bad.push(["unknown id", item.href]);
                });
              });
            });
            return bad;
        """, self.data)
        self.assertEqual(bad, [])

    def test_every_kind_search_advertises_has_a_route(self):
        """The search page names eight kinds of content. A kind that reaches
        nothing is a kind the page should not be advertising."""
        kinds = run_in_node("""
            const seen = {};
            ["union", "sqlmap", "WSTG-INPV-05", "session", "traversal", "path",
             "injection", "cookie"].forEach(function (term) {
              H.searchAll(D, term).forEach(function (group) {
                group.items.forEach(function (item) {
                  if (item.href) seen[group.kind] = item.href.replace("#/", "").split("/")[0];
                });
              });
            });
            return seen;
        """, self.data)
        for kind in ("Test cases", "Tests", "Topics", "Capabilities", "Payloads",
                     "Cards", "Tools"):
            self.assertIn(kind, kinds, f"{kind} reaches nothing")

    def test_a_term_too_short_to_mean_anything_returns_nothing(self):
        self.assertEqual(self.kinds("u"), [])


@unittest.skipUnless(node_available(), "node is not installed")
class TheMarkdownRendererStaysSafe(unittest.TestCase):
    """Cards and mitigations are contributor-written Markdown, and this is the
    one place they become markup."""

    def render(self, source):
        return run_in_node("return H.md(%r);" % source, {})

    def test_a_tag_in_prose_is_shown_and_not_executed(self):
        out = self.render("Consider <script>alert(1)</script> in a value.")
        self.assertIn("&lt;script&gt;", out)
        self.assertNotIn("<script>", out)

    def test_a_tag_inside_a_fenced_block_is_escaped_too(self):
        out = self.render("```\n<img src=x onerror=alert(1)>\n```")
        self.assertIn("&lt;img", out)
        self.assertNotIn("<img", out)

    def test_a_link_becomes_its_text_and_never_a_destination(self):
        out = self.render("See [the note](javascript:alert(1)) for detail.")
        self.assertIn("the note", out)
        self.assertNotIn("javascript:", out)
        self.assertNotIn("<a ", out)

    def test_a_quote_in_a_table_cell_cannot_close_an_attribute(self):
        out = self.render('| a | b |\n|---|---|\n| " onmouseover=x | y |\n')
        self.assertIn("&quot;", out)
        self.assertNotIn('" onmouseover', out)

    def test_ordinary_structure_still_renders(self):
        out = self.render("# Heading\n\n- one\n- two\n\n`code`\n")
        self.assertIn("<h3>Heading</h3>", out)
        self.assertIn("<li>one</li>", out)
        self.assertIn("<code>code</code>", out)


@unittest.skipUnless(browser_available(), "no browser driver is installed")
class TheBuiltFileWorksInABrowser(unittest.TestCase):
    """The artefact, driven the way a person drives it.

    Everything above calls functions. This opens the built file from disk and
    uses it: navigates, types, clicks, presses keys. That is the only way to
    test the routing, the Content-Security-Policy and the rendered wording
    together -- under a hash-based policy a script whose hash no longer matches
    simply never runs, and nothing below would render at all.

    One browser for the class: launching one per test costs more than the tests.
    """

    @classmethod
    def setUpClass(cls):
        cls._tmp = TemporaryDirectory(prefix="harrier-browser-")
        target = Path(cls._tmp.name) / "harrier.html"
        build(REPO_ROOT, target)
        cls.data = catalogue(REPO_ROOT)
        cls.driver = Page(target)

    @classmethod
    def tearDownClass(cls):
        cls.driver.close()
        cls._tmp.cleanup()

    def open(self, fragment=""):
        return self.driver.open(fragment)

    def text(self, fragment=""):
        self.open(fragment)
        return self.driver.text()

    def assertShows(self, text, phrase, note=None):
        """Case-insensitive: the stylesheet upper-cases section labels, and a
        test that asserts on the casing is a test that breaks on a font change
        rather than on a defect."""
        self.assertIn(phrase.lower(), text.lower(), note or phrase)

    # --- what it renders -------------------------------------------------

    def test_it_opens_on_standards(self):
        page = self.open()
        self.assertEqual(page.inner_text("main h2"), "Standards")
        self.assertIn("OWASP Web Security Testing Guide", self.driver.text())

    def test_the_script_runs_under_its_own_policy(self):
        # An empty <main> means the script never executed, which under a
        # hash-based policy means the hash did not match what was embedded.
        self.assertTrue(self.text())

    def test_the_required_journey_reaches_a_test_and_its_chain(self):
        for fragment, expected in (
            ("#/wstg", "Input Validation Testing"),
            ("#/wstg/INPV", "Testing for SQL Injection"),
            ("#/case/WSTG-INPV-05", "SQL injection"),
            ("#/unit/HRR-INJ-01-UNION", "UNION-based extraction"),
            ("#/wstg/ATHZ", "Testing Directory Traversal File Include"),
            ("#/unit/HRR-RES-01-READ", "Confirmed read outside the intended root"),
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(expected, self.text(fragment))

    def test_the_test_detail_carries_what_a_tester_performs_it_from(self):
        text = self.text("#/unit/HRR-INJ-01-UNION")
        for section in ("Objective", "Why this is a separate test", "Oracle",
                        "Sequence", "First false positive", "Done when",
                        "Safety boundary", "Payloads", "Tool", "Card",
                        "Local attack chain", "If this test is unsuccessful"):
            self.assertShows(text, section)

    def test_where_success_may_lead_is_answered_before_the_procedure(self):
        """On an authored unit the procedure runs for several screens. The
        product's own feature must not be at the bottom of them."""
        page = self.open("#/unit/HRR-RES-01-READ")
        strip = page.evaluate(
            "document.querySelector('.strip').getBoundingClientRect().top"
        )
        oracle = page.evaluate(
            "[...document.querySelectorAll('.k')].find(e => e.textContent === 'Oracle')"
            ".getBoundingClientRect().top"
        )
        self.assertLess(strip, oracle, "the chain summary is below the procedure")
        text = self.driver.text(".strip")
        self.assertShows(text, "Needs first")
        self.assertShows(text, "Success establishes")
        self.assertShows(text, "May then be relevant")
        self.assertShows(text, "Inclusion and execution of the resolved path")

    def test_the_local_chain_is_drawn_with_its_reasons(self):
        page = self.open("#/unit/HRR-INJ-01-PROBE")
        self.assertGreaterEqual(page.locator(".gnode").count(), 5)
        self.assertGreaterEqual(page.locator(".gedge").count(), 4)
        text = self.driver.text()
        for heading in ("Prerequisite", "This test", "Establishes",
                        "Potential continuation"):
            self.assertShows(text, heading)
        # Direction is drawn, not implied.
        self.assertGreater(page.locator("path.gedge[marker-end]").count(), 0)

    def test_every_producer_of_a_prerequisite_is_named_not_just_the_first(self):
        text = self.text("#/unit/HRR-RES-01-READ")
        self.assertShows(text, "Established by")
        self.assertShows(text, "Traversal sequence survival probe")

    def test_a_continuation_states_what_success_here_does_not_supply(self):
        # Succeeding here supplies one condition of each continuation and not
        # the rest, which is the ordinary case and the one the old model got
        # wrong by calling it "unlocked".
        text = self.text("#/unit/HRR-RCN-07-MAP")
        self.assertShows(text, "Potential continuation")
        self.assertShows(text, "Established here")
        self.assertShows(text, "Still required")

    def test_a_test_whose_result_leads_nowhere_explains_itself(self):
        # See the note in test_cli: this subject is the one still terminal.
        text = self.text("#/unit/HRR-INJ-11-TIME")
        self.assertIn("no test declares a use for it", text.lower())
        self.assertIn("does not rule out", text.lower())

    def test_both_routes_to_a_topic_separate_its_stages_from_its_alternatives(self):
        """The topic page and the test case page are two routes to the same
        list, and the standard-first one -- through the test case -- is the one
        the documentation calls primary. A split that reached only the other
        route would be a split most readers never see."""
        for fragment in ("#/topic/HRR-INJ-01", "#/case/WSTG-INPV-05"):
            with self.subTest(route=fragment):
                body = self.text(fragment)
                self.assertIn("Stages", body)
                self.assertIn("Alternatives", body)
                self.assertIn("Choose among these on the evidence", body)
                self.assertIn("Perform each of these", body)

    def test_a_topic_that_returns_to_its_stages_keeps_its_declared_order(self):
        """EVADE reads a negative result from one of the techniques, so the
        topic lists it after them. Collecting the stages together would move it
        ahead of the tests it depends on."""
        body = self.text("#/topic/HRR-INJ-01")
        probe = body.index("Injection point probe")
        union = body.index("UNION-based extraction")
        evade = body.index("Filter and encoding evasion")
        self.assertLess(probe, union)
        self.assertLess(union, evade)

    def test_the_general_view_is_a_counted_directed_matrix(self):
        # On the catalogue page since 0.13.0: a count of tests per pair of
        # families is a statement about the catalogue, which the matrix said
        # about itself in its own second sentence while sitting under a page
        # named for routes.
        page = self.open("#/status")
        self.assertEqual(page.locator("table.matrix").count(), 1)
        self.assertEqual(page.locator(".gnode").count(), 0, "the hairball is back")
        text = self.driver.text()
        for family in ("Reconnaissance", "Surface", "Access", "Artefact",
                       "Primitive", "Control", "Impact"):
            self.assertIn(family, text, family)
        # The counts are drawn, not merely computed.
        filled = page.locator("table.matrix td.cell:not(.zero)")
        self.assertGreater(filled.count(), 5)
        self.assertRegex(filled.first.inner_text(), r"^\d+$")

    def test_reaching_an_impact_is_not_counted_as_stopping_short(self):
        """Every impact is unconsumed by construction, so folding impacts into
        the stops-short count inflates it by the set listed directly above and
        describes arriving as failing to arrive."""
        self.assertShows(self.text("#/chains"), "Where chains are meant to end")
        text = self.text("#/status")
        self.assertShows(text, "impacts excluded")
        dead = len(self.data["deadEnds"])
        impacts = len(self.data["impacts"])
        self.assertShows(text, str(dead))
        self.assertNotIn(str(dead + impacts) + " ", text)

    def test_the_status_page_partitions_every_test_by_where_its_chain_goes(self):
        text = self.text("#/status")
        reach = self.data["reach"]
        self.assertEqual(sum(reach.values()), len(self.data["units"]))
        for label in ("Has a potential continuation", "Establishes an impact",
                      "Stops short", "Declares no capability"):
            self.assertShows(text, label)
        for value in reach.values():
            self.assertShows(text, str(value))

    def test_neither_general_view_claims_an_ordering_it_has_not_earned(self):
        """Both say it, because both could be read as a progression: the matrix
        by having axes, and the map by having columns."""
        matrix = self.text("#/status").lower()
        self.assertNotIn("a chain runs left to right", matrix)
        self.assertIn("not the stages of an attack", matrix)

        chart = self.text("#/chains").lower()
        self.assertIn("not by any claim about how an attack proceeds", chart)
        # The column order is a measurement, so the picture prints the edges
        # that run against it rather than leaving them out of the picture.
        back = run_in_node("return H.chainBackEdges(D);", self.data)
        self.assertIn(str(sum(e["units"] for e in back)) + " run against this order",
                      chart)

    def test_a_matrix_cell_drills_down_to_the_tests_it_counted(self):
        page = self.open("#/status")
        cell = page.locator("table.matrix td.cell:not(.zero) a").first
        counted = int(cell.inner_text())
        before = self.driver.heading()
        cell.click()
        self.driver.wait_for_view(before)
        text = self.driver.text()
        self.assertShows(text, str(counted) + " test")
        self.assertShows(text, "Requires:")
        self.assertShows(text, "Establishes:")

    def test_a_route_to_an_impact_names_what_each_step_still_owes(self):
        """A route drawn as an unbroken capability → test → capability chain
        reads as executable when one of its tests is not performable from what
        the route supplies."""
        page = self.open("#/capability/access.anon")
        text = self.driver.text()
        self.assertShows(text, "Routes to an impact")
        self.assertShows(text, "Still required here")
        self.assertShows(text, "unmet condition")
        # The condition named is one the step's own unit actually declares.
        owed = page.locator(".rstep.unit").first
        self.assertGreater(page.locator(".rstep.unit").count(), 1)
        self.assertTrue(owed.inner_text())

    def test_a_search_result_for_a_payload_or_a_tool_reaches_its_own_page(self):
        """Both used to land on Standards: the router had no branch for either,
        so retrieval was broken for two of the kinds search advertises."""
        for term, expect in (("sqlmap", "Automated SQL injection"),
                             ("NULL-padded arity probe", "reviewed")):
            with self.subTest(term=term):
                page = self.open("#/search/" + term.replace(" ", "%20"))
                card = page.locator("a.card").first
                target = card.get_attribute("href")
                before = self.driver.heading()
                card.click()
                heading = self.driver.wait_for_view(before)
                self.assertEqual(self.driver.hash(), target)
                text = self.driver.text()
                self.assertNotEqual(heading, "Standards",
                                    f"{target} fell through to the landing page")
                self.assertShows(text, expect)
                self.assertShows(text, "Tests that")

    def test_the_about_page_states_the_alpha_and_derives_its_figures(self):
        """A figure maintained separately from the data it describes is wrong
        somewhere, and this file is the copy a reader has offline."""
        text = self.text("#/about")
        # Counted by tier name rather than "not an outline": the middle tier
        # exists precisely so that a sketch is not reported as full depth, and
        # a negation here would pass while the page said the optimistic thing.
        depths = [u.get("status", "authored") for u in self.data["units"].values()]
        self.assertShows(text, "early public alpha")
        self.assertShows(text, f"{len(self.data['units'])} tests across "
                               f"{len(self.data['topics'])} topics")
        self.assertShows(text, f"{depths.count('authored')} are written to full "
                               f"procedural depth")
        self.assertShows(text, f"{depths.count('sketched')} are sketched")

    def test_a_sketched_test_is_rendered_as_its_own_tier(self):
        """The pill, the notice and the sections present are what a reader
        judges depth by. All three once collapsed to "written in full" for
        anything that was not an outline, which is exactly what the middle tier
        exists to stop."""
        page = self.open("#/unit/HRR-RCN-02-MAP")
        self.assertEqual(page.locator("main .pill").first.inner_text().lower(), "sketched")
        self.assertShows(self.driver.text(), "this test is sketched")
        # Asserted against the section labels rather than the page text: the
        # words themselves occur in the prose a unit is free to write.
        labels = [t.strip().lower() for t in page.locator("main .k").all_inner_texts()]
        for present in ("sequence", "first false positive", "done when"):
            self.assertIn(present, labels)
        for absent in ("safety boundary", "evidence", "preconditions"):
            self.assertNotIn(absent, labels,
                             f"a sketch showed {absent}, which it does not carry")

    def test_an_outline_and_a_sketch_are_not_given_the_same_notice(self):
        # Taken from the catalogue rather than named: naming one made this a
        # test about a particular unit, and it failed the day that unit was
        # written to a deeper tier rather than the day the notice broke.
        uid = next(i for i in sorted(self.data["units"])
                   if self.data["units"][i].get("status") == "outline")
        outline = self.text("#/unit/" + uid)
        self.assertShows(outline, "this test is an outline")
        self.assertNotIn("this test is sketched", outline.lower())

    def test_the_orientation_fields_are_rendered_before_the_procedure(self):
        """Where to start comes before how to run it. A reader who cannot answer
        the first has nothing to point the sequence at."""
        page = self.open("#/unit/HRR-RES-01-PROBE")
        text = self.driver.text()
        for section in ("What this assumes", "Where to start", "Where the input lands"):
            self.assertShows(text, section)
        labels = [t.strip().lower() for t in page.locator("main .k").all_inner_texts()]
        self.assertLess(labels.index("where to start"), labels.index("sequence"),
                        "orientation is printed below the procedure it orients")
        self.assertLess(labels.index("what this assumes"), labels.index("oracle"))

    def test_a_recon_unit_shows_no_sink(self):
        """The schema forbids the field there; this is the page agreeing, so a
        section cannot appear from a stale build."""
        page = self.open("#/unit/HRR-RCN-02-MAP")
        labels = [t.strip().lower() for t in page.locator("main .k").all_inner_texts()]
        self.assertIn("where to start", labels)
        self.assertNotIn("where the input lands", labels)

    def test_the_chains_page_shows_the_map_and_not_the_matrix(self):
        """The page is named for routes. The family matrix counts tests per pair
        of families, which is a statement about the catalogue, and it said so in
        its own second sentence while sitting here."""
        page = self.open("#/chains")
        self.assertEqual(page.locator(".mcol").count(), 7)
        self.assertEqual(page.locator(".mcell").count(), len(self.data["facts"]))
        self.assertEqual(page.locator("table.matrix").count(), 0)

    def test_the_matrix_is_on_the_catalogue_page_and_names_both_axes(self):
        """A legend under a table is read after the table has been misread."""
        page = self.open("#/status")
        self.assertEqual(page.locator("table.matrix").count(), 1)
        text = self.driver.text()
        self.assertShows(text, "requires")
        self.assertShows(text, "establishes")
        self.assertShows(text, "Catalogue status and model")
        # Every cell states its own sentence rather than leaving the reader to
        # reconstruct it from the axis it forgot which way round was which.
        titled = page.locator("table.matrix td.cell[title]").count()
        self.assertEqual(titled, page.locator("table.matrix td.cell").count())

    def test_the_column_headings_stay_put_while_the_columns_are_read(self):
        """Fifty-nine cells is a long way to scroll with no idea which column
        you are in. The first version stuck them to a wrapper whose overflow
        made it the scrollport, so they slid away at every width; the second
        stuck them to the top of the viewport, where the site header already
        is. What the offset has to track is the header's real height, which
        changes as it wraps."""
        page = self.open("#/chains")
        for width in (1280, 700):
            with self.subTest(width=width):
                page.set_viewport_size({"width": width, "height": 800})
                self.open("#/chains")
                page.evaluate("window.scrollTo(0, 1500)")
                self.driver.wait_for_render(
                    lambda: page.evaluate("window.scrollY") > 1000
                )
                below = page.evaluate("""() => {
                  const bar = document.querySelector('header').getBoundingClientRect().bottom;
                  const tallest = [...document.querySelectorAll('.mcol')].sort(
                    (a, b) => b.getBoundingClientRect().height - a.getBoundingClientRect().height)[0];
                  return tallest.querySelector('.mhead').getBoundingClientRect().top - bar;
                }""")
                self.assertGreaterEqual(
                    below, -1.5,
                    "the column heading is behind the site header rather than below it",
                )
                self.assertLess(below, 40, "the column heading is not stuck at all")
        page.set_viewport_size({"width": 1280, "height": 900})

    def test_the_map_filter_narrows_the_picture_and_gives_it_back(self):
        page = self.open("#/chains")
        every = page.locator(".mcell").count()
        page.fill("#mapfilter", "session")
        self.driver.wait_for_render(
            lambda: page.locator(".mcell:not(.off)").count() < every
        )
        narrowed = page.locator(".mcell:not(.off)").count()
        self.assertGreater(narrowed, 0)
        self.assertIn(f"{narrowed} of {every}", page.inner_text("#mapcount"))
        page.fill("#mapfilter", "")
        self.driver.wait_for_render(
            lambda: page.locator(".mcell:not(.off)").count() == every
        )

    def test_a_cell_of_the_map_opens_the_capability_it_stands_for(self):
        """The map is the way in: every cell is a link to the page that answers
        what this capability opens and what establishes it."""
        page = self.open("#/chains")
        first = page.locator(".mcell").first
        fact = first.get_attribute("href").split("/")[-1]
        first.click()
        self.driver.wait_for_view("Attack chains")
        self.assertIn("capability", self.driver.hash())
        self.assertShows(self.driver.text(), "Required by")
        self.assertIn(fact.split("%2E")[0][:6].lower(), self.driver.text().lower())

    def test_the_status_page_reports_each_tier_separately(self):
        text = self.text("#/status")
        depths = [u.get("status", "authored") for u in self.data["units"].values()]
        self.assertShows(text, f"Written to full depth {depths.count('authored')}")
        self.assertShows(text, f"Sketched {depths.count('sketched')}")
        self.assertShows(text, f"Outline only {depths.count('outline')}")
        # The three tiers are the catalogue: a row that stopped agreeing with
        # the total would be a depth figure quietly counting something else.
        self.assertEqual(sum(depths.count(t) for t in ("authored", "sketched", "outline")),
                         len(self.data["units"]))

    def test_the_about_page_says_what_the_file_does_not_know(self):
        text = self.text("#/about")
        for phrase in ("never seen the application you are testing", "potential continuation",
                       "not affiliated with", "no network request",
                       "stores nothing in this browser"):
            self.assertShows(text, phrase)

    def test_the_about_page_explains_an_outline_rather_than_hiding_it(self):
        text = self.text("#/about")
        self.assertShows(text, "outline")
        self.assertShows(text, "no procedure")

    def test_a_focused_capability_shows_a_smaller_view_than_the_catalogue(self):
        text = self.text("#/capability/surface.sql.injectable")
        self.assertShows(text, "Established by")
        self.assertShows(text, "Required by")

    def test_an_unknown_route_says_so_rather_than_rendering_nothing(self):
        self.assertIn("Not here", self.text("#/unit/__proto__"))

    # --- what a person can do with it ------------------------------------

    def test_typing_in_the_search_box_searches(self):
        page = self.open()
        page.fill("#q", "sqlmap")
        self.driver.wait_for_render(lambda: "sqlmap" in self.driver.text())
        self.assertEqual(self.driver.hash(), "#/search/sqlmap")
        self.assertShows(self.driver.text(), "Tools")

    def test_clearing_the_search_box_leaves_the_results(self):
        page = self.open()
        page.fill("#q", "union")
        self.driver.wait_for_render(lambda: "UNION-based" in self.driver.text())
        page.fill("#q", "")
        self.driver.wait_for_render(lambda: "is searchable" in self.driver.text())
        self.assertEqual(self.driver.hash(), "#/search")
        self.assertShows(self.driver.text(), "Everything the file carries is searchable")

    def test_clicking_a_node_in_the_graph_opens_what_it_names(self):
        page = self.open("#/unit/HRR-INJ-01-PROBE")
        node = page.locator(".gnode.link").first
        target = node.get_attribute("data-go")
        before = self.driver.heading()
        node.click()
        self.assertNotEqual(self.driver.wait_for_view(before), "Standards")
        self.assertEqual(self.driver.hash(), target)

    def test_a_graph_node_is_reachable_and_usable_from_the_keyboard(self):
        page = self.open("#/unit/HRR-INJ-01-PROBE")
        node = page.locator(".gnode.link").first
        self.assertEqual(node.get_attribute("role"), "link")
        self.assertTrue(node.get_attribute("aria-label"))
        target = node.get_attribute("data-go")
        before = self.driver.heading()
        node.focus()
        page.keyboard.press("Enter")
        self.assertNotEqual(self.driver.wait_for_view(before), "Standards")
        self.assertEqual(self.driver.hash(), target)

    def test_show_more_expands_the_graph_and_is_a_place_to_come_back_to(self):
        page = self.open("#/unit/HRR-INJ-01-PROBE")
        before = page.locator(".gnode").count()
        self.assertShows(self.driver.text(), "Show more")
        page.click("a.more")
        self.driver.wait_for_render(lambda: self.driver.count(".gnode") > before)
        after = page.locator(".gnode").count()
        self.assertGreater(after, before)
        self.assertIn("/all", self.driver.hash())
        self.assertShows(self.driver.text(), "Show less")
        page.click("a.more")
        self.driver.wait_for_render(lambda: self.driver.count(".gnode") == before)
        self.assertNotIn("/all", self.driver.hash())

    def test_a_continuation_navigates_to_its_own_test(self):
        page = self.open("#/unit/HRR-RES-01-READ")
        before = self.driver.heading()
        page.click("text=Inclusion and execution of the resolved path")
        self.driver.wait_for_view(before)
        self.assertIn("HRR-RES-01-EXEC", self.driver.hash())

    def test_the_boundary_notes_are_folded_away_until_asked_for(self):
        page = self.open("#/case/WSTG-INPV-05")
        fold = page.locator("details.fold").first
        self.assertFalse(fold.evaluate("e => e.open"))
        # Units lead; the fold follows them.
        unit = page.locator("a.card").first.evaluate("e => e.getBoundingClientRect().top")
        note = fold.evaluate("e => e.getBoundingClientRect().top")
        self.assertLess(unit, note)
        fold.locator("summary").click()
        self.assertTrue(fold.evaluate("e => e.open"))

    def test_the_search_box_has_an_accessible_name(self):
        page = self.open()
        self.assertTrue(page.get_attribute("#q", "aria-label"))

    # --- the two guarantees, as behaviour --------------------------------

    def test_no_rendered_page_claims_to_know_the_reader_s_target(self):
        forbidden = ("unlocked", "available now", "you hold", "your target",
                     "ruled out for", "is possible now")
        for fragment in ("", "#/wstg", "#/case/WSTG-INPV-05",
                         "#/unit/HRR-INJ-01-UNION", "#/unit/HRR-RES-01-READ",
                         "#/chains", "#/status", "#/capability/access.user"):
            text = self.text(fragment).lower()
            for phrase in forbidden:
                self.assertNotIn(phrase, text, f"{fragment}: {phrase}")

    def test_the_conditional_wording_the_model_depends_on_is_present(self):
        text = self.text("#/unit/HRR-INJ-01-PROBE")
        self.assertShows(text, "may become relevant")
        self.assertShows(text, "Potential continuation")

    def test_it_asks_the_network_for_nothing_at_any_point(self):
        """Not a substring check: every request the browser attempted, across
        every page these tests have opened."""
        self.assertEqual(self.driver.offsite(), [])

    def test_nothing_it_does_raises_an_error_in_the_console(self):
        """A policy that blocks something the page needed reports it here and
        nowhere else. Runs last so it covers what the others did."""
        self.open("#/chains")
        self.open("#/unit/HRR-RES-01-READ")
        self.assertEqual(self.driver.console_errors, [])


@unittest.skipUnless(node_available(), "node is not installed")
class DepthIsThreeTiersRatherThanTwo(unittest.TestCase):
    """`depthOf` is what every count and every label on the page now goes
    through. It was a negation -- "not an outline" -- and a third tier turned
    that into a claim that a twenty-minute sketch was written to full depth."""

    def test_each_status_maps_to_its_own_tier_and_label(self):
        got = run_in_node("""
            return [{status: "outline"}, {status: "sketched"}, {status: "authored"},
                    {}, {status: "nonsense"}].map(function (u) {
              return [H.depthOf(u), H.depthLabel(u)];
            });
        """, {})
        self.assertEqual(got, [
            ["outline", "outline"],
            ["sketched", "sketched"],
            ["authored", "written in full"],
            # Absent means authored, matching every count in the repository.
            ["authored", "written in full"],
            ["authored", "written in full"],
        ])

    def test_the_catalogue_agrees_with_the_counts_the_page_publishes(self):
        data = catalogue(REPO_ROOT)
        tiers = run_in_node("""
            const out = {outline: 0, sketched: 0, authored: 0};
            Object.keys(D.units).forEach(function (id) { out[H.depthOf(D.units[id])] += 1; });
            return out;
        """, data)
        self.assertEqual(tiers["authored"], data["counts"]["units_authored"])
        self.assertEqual(tiers["sketched"], data["counts"]["units_sketched"])
        self.assertEqual(sum(tiers.values()), data["counts"]["units"])


class TheChainMapIsTheWholeCatalogueAtOnce(unittest.TestCase):
    """Seven columns of cells rather than a node-link drawing.

    185 capabilities and six hundred edges rendered as a graph is the hairball
    `PIVOT.md` rejected once already. What a reader wants from a picture of the
    model is what kind of thing each capability is and how far the chart reaches
    from it, and columns carry both without drawing a line that would have to be
    believed.
    """

    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)
        cls.map = run_in_node("return H.chainMap(D);", cls.data)

    def test_every_capability_appears_exactly_once(self):
        """A picture that quietly drops part of the catalogue is worse than no
        picture: it is read as the whole thing."""
        seen = [cell["fact"] for col in self.map for cell in col["cells"]]
        self.assertEqual(sorted(seen), sorted(self.data["facts"]))
        self.assertEqual(len(seen), len(set(seen)))

    def test_the_order_covers_every_family_the_catalogue_declares(self):
        order = run_in_node("return H.CHAIN_ORDER;", self.data)
        self.assertEqual(sorted(order),
                         sorted(f["name"] for f in self.data["families"]))
        self.assertEqual([col["name"] for col in self.map], order)

    def test_the_four_states_partition_the_capabilities(self):
        total = sum(sum(col["tally"].values()) for col in self.map)
        self.assertEqual(total, len(self.data["facts"]))

    def test_the_shading_agrees_with_the_figures_published_beside_it(self):
        """The picture and the numbers on the status page come from one source.
        Two ways of counting the same thing is one of them being wrong."""
        tally = {k: sum(col["tally"][k] for col in self.map)
                 for k in ("impact", "routed", "short", "unused")}
        self.assertEqual(tally["unused"], len(self.data["deadEnds"]))
        self.assertEqual(tally["impact"], len(self.data["impacts"]))
        routed = run_in_node("""
            let n = 0;
            Object.keys(D.facts).forEach(function (f) {
              if (H.familyOf(f) === "impact") return;
              if (H.pathsToImpact(D, f, {maxPaths: 5, maxDepth: 6}).length) n++;
            });
            return n;
        """, self.data)
        self.assertEqual(tally["routed"], routed)

    def test_the_columns_report_the_gap_rather_than_hiding_it(self):
        """The reason the picture is worth having: control is where the chart
        runs out, and a reader should be able to see that without reading a
        paragraph about it."""
        control = [c for c in self.map if c["name"] == "control"][0]
        primitive = [c for c in self.map if c["name"] == "primitive"][0]
        self.assertGreater(control["tally"]["unused"], control["tally"]["routed"])
        self.assertGreater(primitive["tally"]["routed"], primitive["tally"]["unused"])

    def test_the_edges_running_against_the_order_are_reported(self):
        """The order is a measurement, and a measurement whose exceptions are
        invisible is an assertion."""
        order = run_in_node("return H.CHAIN_ORDER;", self.data)
        back = run_in_node("return H.chainBackEdges(D);", self.data)
        for edge in back:
            self.assertGreater(order.index(edge["from"]), order.index(edge["to"]))
        reported = {(e["from"], e["to"]) for e in back}
        for edge in self.data["familyEdges"]:
            if edge["from"] == edge["to"]:
                continue
            if order.index(edge["from"]) > order.index(edge["to"]):
                self.assertIn((edge["from"], edge["to"]), reported)


class ATopicSeparatesItsStagesFromItsAlternatives(unittest.TestCase):
    """The listing is the first thing a tester reads, and it used to answer
    "perform all of these" and "choose one of these" with the same shape.

    These run against `unitRuns`, the function both the topic page and the test
    case page file units with, so a block quietly dropped from either fails here.
    """

    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)

    def test_the_runs_together_hold_every_unit_the_topic_lists(self):
        """A unit in no run would vanish from the pages that list it -- a worse
        failure than the flat list this replaces."""
        lost = run_in_node("""
            const out = {};
            Object.keys(D.topics).forEach(function (tid) {
              const runs = H.unitRuns(D, D.topics[tid]);
              let seen = 0;
              runs.forEach(function (r) { seen += r.units.length; });
              const ids = D.topics[tid].units || [];
              if (seen !== ids.length) out[tid] = [seen, ids.length];
            });
            return out;
        """, self.data)
        self.assertEqual(lost, {})

    def test_the_declared_order_is_preserved_exactly(self):
        """The order carries meaning that collecting the roles destroys, and
        HRR-INJ-01 is the case: EVADE reads a negative result from one of the
        techniques, so it is listed after them and must stay there."""
        mismatched = run_in_node("""
            const out = {};
            Object.keys(D.topics).forEach(function (tid) {
              const flat = [];
              H.unitRuns(D, D.topics[tid]).forEach(function (r) {
                r.units.forEach(function (u) { flat.push(u); });
              });
              const ids = (D.topics[tid].units || []).filter(function (u) {
                return !!D.units[u];
              });
              if (flat.join(",") !== ids.join(",")) out[tid] = [flat, ids];
            });
            return out;
        """, self.data)
        self.assertEqual(mismatched, {})

    def test_a_topic_that_returns_to_its_stages_gets_three_runs(self):
        result = run_in_node("""
            return H.unitRuns(D, D.topics["HRR-INJ-01"]).map(function (r) {
              return {role: r.role, units: r.units};
            });
        """, self.data)
        self.assertEqual([r["role"] for r in result], ["stage", "variant", "stage"])
        self.assertEqual(result[0]["units"], ["HRR-INJ-01-PROBE", "HRR-INJ-01-FPRINT"])
        self.assertEqual(len(result[1]["units"]), 7)
        self.assertEqual(result[2]["units"], ["HRR-INJ-01-EVADE"])

    def test_nothing_in_the_catalogue_falls_through_to_unclassified(self):
        strays = run_in_node("""
            const out = [];
            Object.keys(D.topics).forEach(function (tid) {
              H.unitRuns(D, D.topics[tid]).forEach(function (r) {
                if (r.role === "unroled") out.push(r.units);
              });
            });
            return out;
        """, self.data)
        self.assertEqual(strays, [])

    def test_a_unit_declaring_no_role_is_shown_rather_than_dropped(self):
        """The schema forbids it, so this can only reach the page from a file
        assembled by something other than this repository -- and dropping it
        silently would be the one outcome worse than showing it uncategorised."""
        result = run_in_node("""
            const D2 = JSON.parse(JSON.stringify(D));
            const tid = "HRR-INJ-01";
            const uid = D2.topics[tid].units[0];
            delete D2.units[uid].role;
            return H.unitRuns(D2, D2.topics[tid]).map(function (r) {
              return {role: r.role, n: r.units.length};
            });
        """, self.data)
        self.assertEqual(result[0], {"role": "unroled", "n": 1})
