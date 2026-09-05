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

from pentest_navgrid.build import build, catalogue
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

    def test_routes_through_the_same_capabilities_are_one_route_with_a_choice(self):
        """Four cards that differ only in which technique carries a step read as
        four ways in. There is one way, with four techniques for its first step,
        and a tester acts on the count."""
        result = self.run_js("""
            const raw = H.pathsToImpact(D, "surface.sql.injectable", {maxPaths: 12, maxDepth: 5});
            const grouped = H.collapseRoutes(raw);
            const shapes = {};
            grouped.forEach(function (g) {
              shapes[[g.start].concat(g.steps.map(function (s) { return s.to; })).join(">")] = 1;
            });
            return {
              raw: raw.length,
              grouped: grouped.length,
              distinctShapes: Object.keys(shapes).length,
              firstStepChoices: grouped[0].steps[0].units.length
            };
        """)
        self.assertEqual(result["grouped"], result["distinctShapes"],
                         "grouping must leave exactly one card per capability sequence")
        self.assertLess(result["grouped"], result["raw"],
                        "this capability is the case the grouping exists for")
        self.assertGreater(result["firstStepChoices"], 1)

    def test_widening_the_search_never_loses_a_shape_a_narrower_one_found(self):
        """Grouping a truncated search is the wrong order, and a fixed multiple
        of the display count only makes it less likely rather than settling it:
        walks that all collapse to one shape can fill the limit while a walk of
        a different shape sits just past it.

        Asserted as the property the view needs -- widening the search is
        monotone in shapes -- rather than by pinning today's numbers, which
        would pass on a catalogue where the case is simply absent.
        """
        result = self.run_js("""
            const bad = [];
            Object.keys(D.facts).forEach(function (f) {
              if (H.familyOf(f) === "impact") return;
              const narrow = H.collapseRoutes(H.pathsToImpact(D, f, {maxPaths: 12, maxDepth: 5}));
              if (!narrow.length) return;
              const wide = H.collapseRoutes(H.pathsToImpact(D, f, {maxPaths: 96, maxDepth: 5}));
              const seen = {};
              wide.forEach(function (g) {
                seen[[g.start].concat(g.steps.map(function (s) { return s.to; })).join(">")] = 1;
              });
              narrow.forEach(function (g) {
                const k = [g.start].concat(g.steps.map(function (s) { return s.to; })).join(">");
                if (!seen[k]) bad.push([f, k]);
              });
              if (wide.length < narrow.length) bad.push([f, "fewer shapes when searched wider"]);
            });
            return bad.slice(0, 10);
        """)
        self.assertEqual(result, [])

    def test_grouping_never_drops_a_step_or_a_condition(self):
        """The collapse is a reading of the walk, not a second walk. Every card
        must keep the shape it came from and the conditions each step still
        owes -- a route drawn shorter or cleaner than it is would be the one
        failure this view cannot afford."""
        result = self.run_js("""
            const bad = [];
            Object.keys(D.facts).forEach(function (f) {
              if (H.familyOf(f) === "impact") return;
              const raw = H.pathsToImpact(D, f, {maxPaths: 12, maxDepth: 5});
              if (!raw.length) return;
              const grouped = H.collapseRoutes(raw);
              // The same key the grouping uses: capabilities and what each step
              // still owes. Matching on capabilities alone would look for a walk
              // in a group it was deliberately kept out of.
              const owed = function (a) {
                a = a || {all_of: [], any_of: []};
                return (a.all_of || []).slice().sort().join(",") + "/" +
                  (a.any_of || []).slice().sort().join(",");
              };
              const key = function (start, steps) {
                return [start].concat(steps.map(function (s) {
                  return s.to + "!" + owed(s.also);
                })).join(">");
              };
              grouped.forEach(function (g) {
                const shape = key(g.start, g.steps);
                raw.forEach(function (r) {
                  if (key(r.start, r.steps) !== shape) return;
                  if (r.steps.length !== g.steps.length) bad.push([f, "length"]);
                  r.steps.forEach(function (step, i) {
                    if (g.steps[i].units.indexOf(step.unit) < 0) bad.push([f, "lost unit"]);
                    const a = g.steps[i].also || {all_of: [], any_of: []};
                    if (a.all_of.length + a.any_of.length
                        < step.also.all_of.length + step.also.any_of.length) {
                      bad.push([f, "lost condition"]);
                    }
                  });
                });
              });
            });
            return bad.slice(0, 10);
        """)
        self.assertEqual(result, [])

    def test_the_totals_survive_the_preview_being_smaller_than_the_tier(self):
        result = self.run_js("""
            const g = H.localGraph(D, "PTN-IDN-01-POLICY", 3);
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
        edges = self.data["chain"]["PTN-IDN-01-POLICY"]["out"]
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
            const g = H.localGraph(D, "PTN-INJ-01-UNION", 9999);
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
            const r = H.negativeReading(D, "PTN-INJ-01-UNION");
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

    def test_the_readme_counts_the_journey_chain_from_the_catalogue(self):
        """It said four of five where the catalogue holds 3 of 4, and had said
        it since before the outcome layer gave one of them a consumer.

        The figure is about the walked chain rather than the whole graph, so it
        is derived the way the sentence means it: the capabilities those four
        tests establish, and how many of them nothing outside the chain declares
        -- as a prerequisite or as a motivation, since either is a declared use.
        """
        walk = ["PTN-RES-01-PROBE", "PTN-RES-01-READ",
                "PTN-RES-01-EXEC", "PTN-OUT-02-IMPACT"]
        established = []
        for uid in walk:
            for fact in self.data["units"][uid].get("yields") or []:
                if fact not in established:
                    established.append(fact)

        def used_elsewhere(fact):
            declared = (self.data["requiredBy"].get(fact) or []) + \
                (self.data["motivates"].get(fact) or [])
            return [uid for uid in declared if uid not in walk]

        unused = [f for f in established if not used_elsewhere(f)]
        readme = " ".join((REPO_ROOT / "README.md").read_text(encoding="utf-8").split())
        self.assertIn(
            f"{len(unused)} of the {len(established)} capabilities that chain establishes",
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
                "PTN-A-01-P": {"id": "PTN-A-01-P", "requires": {"all_of": ["a.start"]}, "yields": ["a.mid"]},
                "PTN-A-01-Q": {"id": "PTN-A-01-Q", "requires": {"all_of": ["a.start"]}, "yields": ["a.mid"]},
                "PTN-A-01-Z": {"id": "PTN-A-01-Z", "requires": {"all_of": ["a.mid"]}, "yields": ["impact.done"]},
            },
            "requiredBy": {"a.start": ["PTN-A-01-P", "PTN-A-01-Q"], "a.mid": ["PTN-A-01-Z"]},
        }
        routes = run_in_node(
            "return H.pathsToImpact(D, 'a.start', {maxPaths: 9, maxDepth: 5});", forked
        )
        self.assertEqual(
            sorted(tuple(s["unit"] for s in r["steps"]) for r in routes),
            [("PTN-A-01-P", "PTN-A-01-Z"), ("PTN-A-01-Q", "PTN-A-01-Z")],
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
                "PTN-A-01-X": {"id": "PTN-A-01-X", "requires": {"all_of": ["a.1"]},
                               "yields": ["b.1", "b.2"]},
                "PTN-A-01-Z": {"id": "PTN-A-01-Z", "requires": {"all_of": ["b.1", "b.2"]},
                               "yields": ["impact.done"]},
            },
            "requiredBy": {"a.1": ["PTN-A-01-X"], "b.1": ["PTN-A-01-Z"], "b.2": ["PTN-A-01-Z"]},
        }
        routes = run_in_node(
            "return H.pathsToImpact(D, 'a.1', {maxPaths: 9, maxDepth: 5});", multi
        )
        self.assertTrue(routes)
        for route in routes:
            final = route["steps"][-1]
            self.assertEqual(final["unit"], "PTN-A-01-Z")
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
                "PTN-A-01-X": {"id": "PTN-A-01-X", "requires": {"all_of": ["a.1"]},
                               "yields": ["b.1", "b.2"]},
                "PTN-A-01-Z": {"id": "PTN-A-01-Z", "requires": {"any_of": ["b.1", "b.2"]},
                               "yields": ["impact.done"]},
            },
            "requiredBy": {"a.1": ["PTN-A-01-X"], "b.1": ["PTN-A-01-Z"], "b.2": ["PTN-A-01-Z"]},
        }
        routes = run_in_node(
            "return H.pathsToImpact(D, 'a.1', {maxPaths: 9, maxDepth: 5});", multi
        )
        shapes = sorted(
            tuple((s["from"], s["unit"], s["to"]) for s in r["steps"]) for r in routes
        )
        self.assertEqual(shapes, [
            (("a.1", "PTN-A-01-X", "b.1"), ("b.1", "PTN-A-01-Z", "impact.done")),
            (("a.1", "PTN-A-01-X", "b.2"), ("b.2", "PTN-A-01-Z", "impact.done")),
        ])
        self.assertEqual(
            {tuple(s["unit"] for s in r["steps"]) for r in routes},
            {("PTN-A-01-X", "PTN-A-01-Z")},
            "the two routes share their units, which is why units alone cannot identify them",
        )

    def test_a_route_that_revisits_a_capability_is_not_extended(self):
        """The yields now added wholesale must not become a way back round: a
        capability already in the path's history is not stepped onto again."""
        loop = {
            "facts": {"a.1": {}, "a.2": {}, "impact.done": {}},
            "given": [],
            "units": {
                "PTN-A-01-X": {"id": "PTN-A-01-X", "requires": {"all_of": ["a.1"]},
                               "yields": ["a.2", "a.1"]},
                "PTN-A-01-Z": {"id": "PTN-A-01-Z", "requires": {"all_of": ["a.2"]},
                               "yields": ["impact.done"]},
            },
            "requiredBy": {"a.1": ["PTN-A-01-X"], "a.2": ["PTN-A-01-Z"]},
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
                "PTN-A-01-X": {id: "PTN-A-01-X", requires: {all_of: ["a.one"]}, yields: ["a.two"]},
                "PTN-A-01-Y": {id: "PTN-A-01-Y", requires: {all_of: ["a.two", "a.one"]}, yields: ["impact.done"]}
              },
              requiredBy: {"a.one": ["PTN-A-01-X", "PTN-A-01-Y"], "a.two": ["PTN-A-01-Y"]}
            };
            return H.pathsToImpact(chained, "a.one", {maxPaths: 5, maxDepth: 4});
        """, self.data)
        routes = {
            tuple(step["unit"] for step in r["steps"]): r["steps"][-1]["also"]
            for r in result
        }
        self.assertEqual(
            routes.get(("PTN-A-01-Y",)), {"all_of": ["a.two"], "any_of": []},
            "reached directly, Y still owes what nothing established",
        )
        self.assertEqual(
            routes.get(("PTN-A-01-X", "PTN-A-01-Y")), {"all_of": [], "any_of": []},
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
                "PTN-A-01-X": {"id": "PTN-A-01-X", "requires": {"all_of": ["a.one"]}, "yields": ["a.two"]},
                "PTN-A-01-Y": {"id": "PTN-A-01-Y", "requires": {"all_of": ["a.two"]}, "yields": ["a.one"]},
                "PTN-A-01-Z": {"id": "PTN-A-01-Z", "requires": {"all_of": ["a.two"]}, "yields": ["impact.done"]},
            },
            "requiredBy": {"a.one": ["PTN-A-01-X"], "a.two": ["PTN-A-01-Y", "PTN-A-01-Z"]},
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
class RoutesToAnImpactAreTheSameGraphWalkedBackwards(unittest.TestCase):
    """Standing at an outcome, the question is what reaches it.

    The page linking to an impact promised "the routes charted to it" and the
    impact said a chain ends here, because the only search the artefact had ran
    forwards. `routesToImpact` walks the same relation the other way. Two
    searches describing one graph have to agree about it, and these are the
    assertions that say they do."""

    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)

    def run_js(self, body):
        return run_in_node(body, self.data)

    KEY = """
        const key = function (start, steps) {
          return start + "|" + steps.map(function (s) {
            return s.from + ">" + s.unit + ">" + s.to + "!" +
              (s.also.all_of || []).slice().sort().join(",") + "/" +
              (s.also.any_of || []).slice().sort().join(",");
          }).join("|");
        };
    """

    def test_a_route_to_an_impact_is_a_route_from_its_start(self):
        """The backward walk cannot apply the forward search's rule that a walk
        may not arrive on a capability an earlier unit already established:
        backwards, the units before a step are the ones not yet chosen. It
        settles that in a pass over the finished walk and drops what breaks it.

        This is what says the dropping is complete rather than approximate.
        Every route drawn at an impact must be a walk the forward search returns
        from the same start -- the same steps, the same units, and the same
        outstanding conditions, which is the part a reader acts on."""
        result = self.run_js(self.KEY + """
            const forward = {};
            const walksFrom = function (start) {
              if (!forward[start]) {
                forward[start] = {};
                H.pathsToImpact(D, start, {maxPaths: 100000, maxDepth: 5, maxExplore: 2000000})
                  .forEach(function (w) { forward[start][key(w.start, w.steps)] = 1; });
              }
              return forward[start];
            };
            const bad = [];
            let checked = 0;
            Object.keys(D.facts).sort().forEach(function (f) {
              if (H.familyOf(f) !== "impact") return;
              H.routesToImpact(D, f, {maxPaths: 8, maxDepth: 5}).forEach(function (r) {
                checked++;
                if (!walksFrom(r.start)[key(r.start, r.steps)]) bad.push([f, r.start]);
              });
            });
            return {checked: checked, bad: bad.slice(0, 10)};
        """)
        self.assertGreater(result["checked"], 0, "no route to any impact was drawn")
        self.assertEqual(result["bad"], [], "a route drawn backwards is not a forward walk")

    def test_a_drawn_route_begins_where_an_engagement_does(self):
        """A backward walk is reported when it reaches a capability nothing
        establishes -- what an engagement supplies rather than what a test
        earns. Reporting at any earlier point would draw the one-step
        restatement of the tests already listed above it on the same page and
        call it a chain."""
        result = self.run_js("""
            const out = {reported: 0, earned: [], impactsWithNoRoute: []};
            Object.keys(D.facts).sort().forEach(function (f) {
              if (H.familyOf(f) !== "impact") return;
              const routes = H.routesToImpact(D, f, {maxPaths: 8, maxDepth: 5});
              if (!routes.length) out.impactsWithNoRoute.push(f);
              routes.forEach(function (r) {
                out.reported++;
                if ((D.producers[r.start] || []).length) out.earned.push([f, r.start]);
                if (r.impact !== f) out.earned.push([f, "arrives elsewhere"]);
              });
            });
            return out;
        """)
        self.assertGreater(result["reported"], 0)
        self.assertEqual(result["earned"], [])
        # An outcome this catalogue charts no way to is a gap in the catalogue,
        # and this is where it should be noticed. It may now be written down
        # rather than absent -- but only written down: the set has to be exactly
        # the registered ones, so neither an unregistered gap nor a stale entry
        # gets past here.
        registered = sorted(
            f for entry in self.data["uncovered"] for f in entry["facts"]
            if f.startswith("impact.")
        )
        self.assertEqual(result["impactsWithNoRoute"], registered)

    def test_the_list_of_starts_names_every_start_the_drawings_use(self):
        """The page draws a few routes and lists every capability a route to
        this outcome can begin at. They are two computations -- an enumeration
        and a reachability sweep -- and a reader takes them for one thing. So
        the drawing may never begin somewhere the list omits, and the distance,
        which is a lower bound, may never exceed a route actually drawn from
        there."""
        result = self.run_js("""
            const bad = [];
            Object.keys(D.facts).sort().forEach(function (f) {
              if (H.familyOf(f) !== "impact") return;
              const dist = H.reachesImpact(D, f);
              H.routesToImpact(D, f, {maxPaths: 8, maxDepth: 5}).forEach(function (r) {
                if (!(r.start in dist)) bad.push([f, r.start, "drawn but unlisted"]);
                else if (dist[r.start] > r.steps.length) {
                  bad.push([f, r.start, dist[r.start] + " > " + r.steps.length]);
                }
              });
            });
            return bad.slice(0, 10);
        """)
        self.assertEqual(result, [])

    def test_the_distance_is_the_shortest_there_is(self):
        """A breadth-first sweep of the reverse relation, so the first time a
        capability is seen is its shortest distance. Asserted against the
        relation itself: a capability one step from the outcome is a condition
        of a test that establishes it, and no capability may be listed further
        away than a neighbour of it already listed."""
        result = self.run_js("""
            const bad = [];
            Object.keys(D.facts).sort().forEach(function (f) {
              if (H.familyOf(f) !== "impact") return;
              const dist = H.reachesImpact(D, f);
              Object.keys(dist).forEach(function (cap) {
                // Every capability this one could reach in one step, and what
                // the sweep says about them.
                (D.requiredBy[cap] || []).forEach(function (uid) {
                  const unit = D.units[uid];
                  if (!unit) return;
                  (unit.yields || []).forEach(function (made) {
                    const onward = made === f ? 0 : dist[made];
                    if (onward === undefined) return;
                    if (dist[cap] > onward + 1) bad.push([f, cap, dist[cap], made, onward]);
                  });
                });
              });
            });
            return bad.slice(0, 10);
        """)
        self.assertEqual(result, [])

    def test_a_capability_that_reaches_no_outcome_is_named_by_none_of_them(self):
        """The negative reading, and the one a coverage claim rests on.

        `access.host` is granted by an engagement rather than earned, and no
        test consumes it on a way to an outcome. A sweep that reported it anyway
        would put a capability on a page it does not reach, which is the failure
        this whole view exists to avoid -- and it would do it silently, because
        a reader has no way to check a reachability claim by eye."""
        result = self.run_js("""
            const out = {listed: [], unreachable: []};
            Object.keys(D.facts).sort().forEach(function (f) {
              if (H.familyOf(f) === "impact") return;
              let anywhere = false;
              Object.keys(D.facts).forEach(function (i) {
                if (H.familyOf(i) !== "impact") return;
                if (f in H.reachesImpact(D, i)) anywhere = true;
              });
              if (!anywhere) out.unreachable.push(f);
              else if (f === "access.host") out.listed.push(f);
            });
            return out;
        """)
        self.assertEqual(
            result["listed"], [],
            "access.host reaches no impact and must appear on no impact's list",
        )
        self.assertIn("access.host", result["unreachable"])

    def test_an_outcome_nothing_establishes_draws_nothing(self):
        """An impact with no producer is not an error -- the vocabulary may name
        an outcome before a test reaches it -- and the view must say so rather
        than fail or draw an empty card. Held on a fixture, because the
        catalogue has no such impact today and the case would otherwise go
        untested until the day one appears."""
        orphan = {
            "facts": {"a.start": {}, "impact.reached": {}, "impact.unreached": {}},
            "given": [],
            "units": {
                "PTN-A-01-Z": {"id": "PTN-A-01-Z", "requires": {"all_of": ["a.start"]},
                               "yields": ["impact.reached"]},
            },
            "producers": {"impact.reached": ["PTN-A-01-Z"]},
            "requiredBy": {"a.start": ["PTN-A-01-Z"]},
        }
        result = run_in_node("""
            return {
              reached: H.routesToImpact(D, "impact.reached", {maxPaths: 9, maxDepth: 5}),
              unreached: H.routesToImpact(D, "impact.unreached", {maxPaths: 9, maxDepth: 5}),
              reach: H.reachesImpact(D, "impact.unreached"),
              absent: H.routesToImpact(D, "impact.nosuchthing", {maxPaths: 9, maxDepth: 5})
            };
        """, orphan)
        self.assertEqual(
            [s["unit"] for s in result["reached"][0]["steps"]], ["PTN-A-01-Z"]
        )
        self.assertEqual(result["reached"][0]["start"], "a.start")
        self.assertEqual(result["unreached"], [])
        self.assertEqual(result["reach"], {})
        self.assertEqual(result["absent"], [])

    def test_the_figures_the_readme_publishes_are_the_sweep(self):
        """The README says how many capabilities reach two of the outcomes, and
        a figure in prose is a claim like any other. Read from the artefact's
        own function rather than recomputed here: a second implementation
        agreeing with itself proves nothing about what the page draws."""
        counts = self.run_js("""
            const out = {};
            Object.keys(D.facts).forEach(function (f) {
              if (H.familyOf(f) !== "impact") return;
              out[f] = Object.keys(H.reachesImpact(D, f)).length;
            });
            return out;
        """)
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            f"{counts['impact.data.disclosed']} begin a charted route to a data "
            f"disclosure, {counts['impact.account.denied']} to a chosen user",
            readme,
        )

    def test_a_route_never_uses_one_test_twice(self):
        """The same rule the forward search keeps, kept walking the other way:
        a route that performs a test it has already performed is a cycle drawn
        as a chain."""
        result = self.run_js("""
            const bad = [];
            Object.keys(D.facts).sort().forEach(function (f) {
              if (H.familyOf(f) !== "impact") return;
              H.routesToImpact(D, f, {maxPaths: 8, maxDepth: 5}).forEach(function (r) {
                const seen = {};
                r.steps.forEach(function (s) {
                  if (seen[s.unit]) bad.push([f, s.unit]);
                  seen[s.unit] = 1;
                });
              });
            });
            return bad.slice(0, 10);
        """)
        self.assertEqual(result, [])

    def test_a_cycle_in_the_reverse_relation_terminates(self):
        """Two tests each establishing what the other requires. The walk stops
        because the path's own history stops it, not because a global visited
        set does -- the same reason the forward search can report two routes
        through one capability."""
        loop = {
            "facts": {"a.root": {}, "a.one": {}, "a.two": {}, "impact.done": {}},
            "given": [],
            "units": {
                "PTN-A-01-P": {"id": "PTN-A-01-P", "requires": {"all_of": ["a.two"]},
                               "yields": ["a.one"]},
                "PTN-A-01-Q": {"id": "PTN-A-01-Q", "requires": {"all_of": ["a.one"]},
                               "yields": ["a.two"]},
                "PTN-A-01-R": {"id": "PTN-A-01-R", "requires": {"all_of": ["a.root"]},
                               "yields": ["a.one"]},
                "PTN-A-01-Z": {"id": "PTN-A-01-Z", "requires": {"all_of": ["a.two"]},
                               "yields": ["impact.done"]},
            },
            "producers": {
                "a.one": ["PTN-A-01-P", "PTN-A-01-R"],
                "a.two": ["PTN-A-01-Q"],
                "impact.done": ["PTN-A-01-Z"],
            },
            "requiredBy": {
                "a.root": ["PTN-A-01-R"],
                "a.one": ["PTN-A-01-Q"],
                "a.two": ["PTN-A-01-P", "PTN-A-01-Z"],
            },
        }
        routes = run_in_node(
            "return H.routesToImpact(D, 'impact.done', {maxPaths: 9, maxDepth: 9});", loop
        )
        self.assertEqual(
            [tuple(s["unit"] for s in r["steps"]) for r in routes],
            [("PTN-A-01-R", "PTN-A-01-Q", "PTN-A-01-Z")],
        )


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
        self.assertIn("PTN-RES-01-PROBE", hits)
        # Not reachable from the title or the objective, which is the point.
        unit = self.data["units"]["PTN-RES-01-PROBE"]
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
class ShorthandReachesTheCatalogueItNames(unittest.TestCase):
    """Titles here name mechanisms; testers type vulnerability classes.

    The validator already refuses an alias that resolves to nothing, but it
    resolves against its own reading of which fields are searchable. These run
    the artefact's real search, which is the only thing that can tell the two
    apart -- and the only thing that would notice if a field were dropped from
    one and not the other.
    """

    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)

    def test_every_alias_the_vocabulary_carries_answers(self):
        empty = run_in_node("""
            return D.aliases.filter(function (a) {
              return H.searchAll(D, a.term).length === 0;
            }).map(function (a) { return a.term; });
        """, self.data)
        self.assertEqual(empty, [], "an alias that answers nothing is the defect it was added to fix")

    def test_every_expansion_reaches_something_the_bare_term_does_not(self):
        """The validator's second rule, re-asked of the code that implements it.
        An alias that only ever returns what the typed term already returned
        tells the reader their term was expanded and shows them nothing for it."""
        idle = run_in_node("""
            return D.aliases.filter(function (a) {
              const viaCount = H.searchAll(D, a.term).reduce(function (n, g) {
                return n + g.items.filter(function (i) { return i.via; }).length;
              }, 0);
              return viaCount === 0;
            }).map(function (a) { return a.term; });
        """, self.data)
        self.assertEqual(idle, [])

    def test_the_shorthand_for_object_level_access_control_reaches_it(self):
        hits = run_in_node("""
            const out = {};
            ["idor", "bola"].forEach(function (t) {
              out[t] = [];
              H.searchAll(D, t).forEach(function (g) {
                g.items.forEach(function (i) { out[t].push(i.sub); });
              });
            });
            return out;
        """, self.data)
        for term in ("idor", "bola"):
            with self.subTest(term=term):
                self.assertIn("PTN-ACL-02", hits[term])

    def test_the_shorthand_the_readme_names_matches_no_title(self):
        """The README says `IDOR`, `SSRF` and `SSTI` match no title at all, and
        that sentence is the reason the file exists. If a topic were renamed to
        carry one of them, the sentence would be wrong -- and the validator
        would reject the alias for it the same day, which is the pair of checks
        this depends on rather than a count that goes stale."""
        titles = [t["title"].lower() for t in self.data["topics"].values()]
        titles += [u["title"].lower() for u in self.data["units"].values()]
        for term in ("idor", "ssrf", "ssti"):
            with self.subTest(term=term):
                self.assertEqual([t for t in titles if term in t], [])

    def test_an_expanded_hit_says_which_phrase_found_it(self):
        """A result the reader did not ask for has to say so. This is the same
        split the context page makes between a tag chosen and a tag implied, and
        for the same reason: silence would read as a direct answer."""
        rows = run_in_node("""
            const out = [];
            H.searchAll(D, "ssrf").forEach(function (g) {
              g.items.forEach(function (i) { out.push([i.sub, i.via]); });
            });
            return out;
        """, self.data)
        self.assertTrue(rows)
        for sub, via in rows:
            with self.subTest(sub=sub):
                self.assertEqual(via, "server-side request forgery")

    def test_a_term_with_no_alias_reports_no_expansion(self):
        vias = run_in_node("""
            const out = [];
            ["union", "session", "traversal"].forEach(function (t) {
              H.searchAll(D, t).forEach(function (g) {
                g.items.forEach(function (i) { if (i.via) out.push([t, i.sub, i.via]); });
              });
            });
            return out;
        """, self.data)
        self.assertEqual(vias, [])

    def test_an_alias_finds_nothing_the_expansion_itself_would_not(self):
        """The safety property. An alias is a spelling: it may reach what the
        phrase reaches and nothing else, so no alias can quietly become an
        editorial claim that one thing is related to another."""
        extra = run_in_node("""
            const extra = [];
            D.aliases.forEach(function (a) {
              const reachable = {};
              a.expands.forEach(function (phrase) {
                H.searchAll(D, phrase).forEach(function (g) {
                  g.items.forEach(function (i) { reachable[g.kind + " " + i.sub + " " + i.title] = true; });
                });
              });
              H.searchAll(D, a.term).forEach(function (g) {
                g.items.forEach(function (i) {
                  if (!i.via) return;
                  const key = g.kind + " " + i.sub + " " + i.title;
                  if (!H.own(reachable, key)) extra.push([a.term, key]);
                });
              });
            });
            return extra;
        """, self.data)
        self.assertEqual(extra, [])


@unittest.skipUnless(node_available(), "node is not installed")
class SearchOrderIsLexicalAndNothingElse(unittest.TestCase):
    """Ordering a search box is where a catalogue starts having opinions about
    its own content. Every rule here is about the letters typed and where they
    landed -- never about which test is worth more, which is the reader's to
    decide and the line `PIVOT.md` draws.
    """

    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)

    def first(self, term, kind):
        return run_in_node("""
            const g = H.searchAll(D, %r).filter(function (g) { return g.kind === %r; })[0];
            return g ? g.items[0].sub : null;
        """ % (term, kind), self.data)

    def test_an_identifier_typed_in_full_comes_first(self):
        self.assertEqual(self.first("PTN-INJ-01-PROBE", "Tests"), "PTN-INJ-01-PROBE")
        self.assertEqual(self.first("WSTG-INPV-05", "Test cases"), "WSTG-INPV-05")

    def test_a_whole_title_outranks_the_same_words_further_down_a_page(self):
        rows = run_in_node("""
            const g = H.searchAll(D, "sql injection").filter(function (g) { return g.kind === "Topics"; })[0];
            return g ? g.items.map(function (i) { return [i.sub, i.rank]; }) : [];
        """, self.data)
        self.assertEqual(rows[0][0], "PTN-INJ-01")
        self.assertEqual(rows[0][1], 1, "an exact title is rank 1")

    def test_a_term_standing_as_a_word_outranks_the_same_letters_buried_in_one(self):
        """`rce` is a substring of `resource` and `force`, which is how four
        letters reached most of the catalogue and neither of the two topics that
        name the thing. Nothing is excluded by this -- the buried matches are
        still found, and still shown."""
        rows = run_in_node("""
            const g = H.searchAll(D, "rce").filter(function (g) { return g.kind === "Topics"; })[0];
            return g.items.map(function (i) { return [i.sub, i.whole]; });
        """, self.data)
        self.assertTrue(rows[0][1], "the first row matched inside a longer word")
        self.assertIn(rows[0][0], ("PTN-INJ-08", "PTN-OUT-02"))
        self.assertTrue(any(not whole for _, whole in rows), "the buried matches are still there")

    def test_a_kind_whose_matches_are_all_buried_is_listed_last(self):
        order = run_in_node("""
            return H.searchAll(D, "rce").map(function (g) { return [g.kind, g.whole]; });
        """, self.data)
        whole = [i for i, (_, w) in enumerate(order) if w]
        buried = [i for i, (_, w) in enumerate(order) if not w]
        self.assertTrue(whole and buried, "this term needs both kinds to be a test of the order")
        self.assertLess(max(whole), min(buried))

    def test_the_kinds_keep_one_order_rather_than_the_order_matches_arrived_in(self):
        """Groups used to be created as matches were found, so an alias hit
        could push the topic a reader was looking for below three kinds of
        supporting prose."""
        order = run_in_node("""
            return H.searchAll(D, "xss").map(function (g) { return g.kind; });
        """, self.data)
        canonical = ["Test cases", "Tests", "Topics", "Capabilities", "Payloads",
                     "Cards", "Mitigations", "Tools"]
        whole = run_in_node("""
            return H.searchAll(D, "xss").filter(function (g) { return g.whole; })
              .map(function (g) { return g.kind; });
        """, self.data)
        self.assertEqual(whole, [k for k in canonical if k in whole])
        self.assertEqual(order[0], "Topics")

    def test_the_same_query_answers_the_same_way_every_time(self):
        runs = run_in_node("""
            const shape = function () {
              return H.searchAll(D, "injection").map(function (g) {
                return g.kind + ":" + g.items.map(function (i) { return i.sub; }).join(",");
              }).join("|");
            };
            return [shape(), shape(), shape()];
        """, self.data)
        self.assertEqual(len(set(runs)), 1)


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


@unittest.skipUnless(node_available(), "node is not installed")
class ChoosingAContextSelectsTestsAndNothingElse(unittest.TestCase):
    """The second way in: from the kind of surface rather than from a standard.

    Everything asserted here is a statement about the catalogue -- which topics
    declare which tags, and which capabilities a test still owes. None of it is
    a statement about an application, and the tests below are as much about that
    boundary holding as about the selection being right.
    """

    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)

    def run_js(self, body):
        return run_in_node(body, self.data)

    def test_a_selection_brings_what_it_always_also_is(self):
        """A GraphQL endpoint is a machine-facing API by `rest-api`'s own
        description -- always, not usually -- so a reader who said the first has
        said the second, and the topics filed under it are answers rather than
        suggestions."""
        out = self.run_js("""
            return H.contextClosure(D, ["graphql"]);
        """)
        self.assertEqual(out["selected"], ["graphql"])
        self.assertEqual(out["parents"], ["rest-api"])

    def test_a_selection_reports_what_it_is_often_found_with_separately(self):
        """The relation that used to be called implication. A search box often
        reaches a relational store and may query no database at all, so it can
        be offered and cannot be counted as chosen."""
        out = self.run_js("""
            return H.contextClosure(D, ["search"]);
        """)
        self.assertEqual(out["selected"], ["search"])
        self.assertEqual(out["parents"], [])
        self.assertEqual(out["often"], ["sql-backed-param"])

    def test_the_two_relations_are_never_merged(self):
        """The whole point of the split. A tag reached by both is reported under
        the stronger one only, so the page never has to decide which wording to
        use for a tag that arrived twice."""
        out = self.run_js("""
            const bad = [];
            D.surfaces.forEach(function (s) {
              const r = H.contextClosure(D, [s.tag]);
              r.parents.forEach(function (t) {
                if (r.often.indexOf(t) >= 0) bad.push([s.tag, t]);
                if (r.selected.indexOf(t) >= 0) bad.push([s.tag, t]);
              });
              r.often.forEach(function (t) {
                if (r.selected.indexOf(t) >= 0) bad.push([s.tag, t]);
              });
            });
            return bad;
        """)
        self.assertEqual(out, [])

    def test_a_tag_chosen_outright_is_never_reported_as_inferred(self):
        """Telling a reader the catalogue worked something out when they said it
        themselves misrepresents where the answer came from."""
        out = self.run_js("""
            return H.contextClosure(D, ["search", "sql-backed-param"]);
        """)
        self.assertIn("sql-backed-param", out["selected"])
        self.assertNotIn("sql-backed-param", out["often"])
        self.assertNotIn("sql-backed-param", out["parents"])

    def test_an_unknown_tag_is_ignored_rather_than_invented(self):
        out = self.run_js("""
            return H.contextClosure(D, ["not-a-tag", "search"]);
        """)
        self.assertEqual(out["selected"], ["search"])

    def test_a_topic_is_reported_with_every_tag_that_reached_it(self):
        """The reason line is the whole point. A list of tests with no statement
        of what put them there is a recommendation, and this file does not make
        recommendations."""
        out = self.run_js("""
            const r = H.contextTopics(D, ["object-id-param", "rest-api"]);
            const hit = r.topics.filter(function (t) { return t.topic === "PTN-ACL-02"; })[0];
            return hit || null;
        """)
        self.assertEqual(
            [[v["tag"], v["how"]] for v in out["via"]],
            [["object-id-param", "chosen"], ["rest-api", "chosen"]],
        )
        self.assertFalse(out["often"])

    def test_a_topic_reached_only_through_an_association_is_marked_as_weaker(self):
        out = self.run_js("""
            const r = H.contextTopics(D, ["search"]);
            const rows = {};
            r.topics.forEach(function (t) { rows[t.topic] = t.often; });
            return rows;
        """)
        self.assertFalse(out["PTN-CLT-01"], "declares search itself")
        self.assertFalse(out["PTN-IDN-03"], "declares search itself")
        # SQL injection is not filed under "search" and a search box does not
        # have to reach SQL. It arrives as an association, and the page has to
        # say which of the two it was.
        self.assertTrue(out["PTN-INJ-01"], "reached only through sql-backed-param")

    def test_a_topic_reached_through_a_parent_is_as_strong_as_one_chosen(self):
        """`rest-api` is not a weaker answer for a GraphQL endpoint; it is a
        true statement about it. Reporting it in the association tier would
        understate the catalogue as badly as the old wording overstated it."""
        out = self.run_js("""
            const r = H.contextTopics(D, ["graphql"]);
            const rows = {};
            r.topics.forEach(function (t) {
              rows[t.topic] = { often: t.often, via: t.via.map(function (v) { return v.tag; }) };
            });
            return rows;
        """)
        reached = [t for t, row in out.items() if "rest-api" in row["via"]]
        self.assertTrue(reached, "no topic is reached through the parent")
        for topic in reached:
            with self.subTest(topic=topic):
                self.assertFalse(out[topic]["often"])

    def test_every_tag_that_reached_a_topic_carries_which_relation_did_it(self):
        """The tier a row lands in is not enough. A row in the stronger tier can
        still be reached by an association as well as by the tag the reader
        chose -- `graphql` reaches object-level access control through both --
        and a card printing the two the same way would go on saying "the context
        is" over a tag the selection never established."""
        out = self.run_js("""
            const r = H.contextTopics(D, ["graphql"]);
            const hit = r.topics.filter(function (t) { return t.topic === "PTN-ACL-02"; })[0];
            return hit.via;
        """)
        self.assertEqual(
            [[v["tag"], v["how"]] for v in out],
            [["graphql", "chosen"], ["object-id-param", "often"], ["rest-api", "always"]],
        )

    def test_no_tag_is_reported_under_a_relation_the_closure_does_not_give_it(self):
        out = self.run_js("""
            const bad = [];
            D.surfaces.forEach(function (s) {
              const closure = H.contextClosure(D, [s.tag]);
              H.contextTopics(D, [s.tag]).topics.forEach(function (row) {
                row.via.forEach(function (v) {
                  const list = closure[v.how === "chosen" ? "selected"
                    : v.how === "always" ? "parents" : "often"];
                  if (list.indexOf(v.tag) < 0) bad.push([s.tag, v.tag, v.how]);
                });
              });
            });
            return bad;
        """)
        self.assertEqual(out, [])

    def test_the_deleted_edges_reach_nothing(self):
        """Three relations were removed rather than relabelled. A selection that
        still reached through one would mean the vocabulary and the page had
        drifted apart -- and the page is where it would be believed."""
        out = self.run_js("""
            return {
              login: H.contextClosure(D, ["login-form"]),
              tenant: H.contextClosure(D, ["multi-tenant"]),
              search: H.contextClosure(D, ["search"])
            };
        """)
        self.assertEqual(out["login"]["often"], [])
        self.assertEqual(out["login"]["parents"], [])
        self.assertEqual(out["tenant"]["often"], [])
        self.assertNotIn("stored-then-rendered", out["search"]["often"])

    def test_a_selection_is_the_union_of_its_tags_and_not_their_intersection(self):
        """Asserted directly rather than left to the wording. The selector is
        grouped by dimension as of 0.28.0, which looks like a control where you
        pick one from each and get the overlap -- so what the code does has to
        be pinned separately from what the page says it does.

        Intersecting was measured before it was built and is unusable at topic
        level; see `docs/DISCOVERY.md`. If it is ever made to work, this test is
        the one that must be rewritten deliberately rather than deleted.
        """
        out = self.run_js("""
            const pairs = [["rest-api", "object-id-param"],
                           ["search", "sql-backed-param"],
                           ["payment", "multi-tenant"]];
            return pairs.map(function (pair) {
              const names = function (sel) {
                return H.contextTopics(D, sel).topics.map(function (t) { return t.topic; });
              };
              const together = names(pair).sort();
              const apart = {};
              names([pair[0]]).concat(names([pair[1]])).forEach(function (t) { apart[t] = true; });
              return [pair.join("+"), together, Object.keys(apart).sort()];
            });
        """)
        for label, together, apart in out:
            with self.subTest(selection=label):
                self.assertEqual(together, apart)
                self.assertTrue(together, "this pair reaches nothing, so it proves nothing")

    def test_a_test_declaring_its_own_surface_answers_for_itself(self):
        """The defect this closes. `multi-tenant` returned all five object-level
        access-control tests when one of them is about tenancy -- the tag was
        carried by the subject, and the subject spans a contrast a single tag
        cannot separate."""
        out = self.run_js("""
            const r = H.contextTopics(D, ["multi-tenant"]);
            const hit = r.topics.filter(function (t) { return t.topic === "PTN-ACL-02"; })[0];
            return { matched: hit.matched, broad: hit.broad };
        """)
        self.assertEqual([m["unit"] for m in out["matched"]], ["PTN-ACL-02-TENANT"])
        self.assertEqual(sorted(out["broad"]), [
            "PTN-ACL-02-IMPACT", "PTN-ACL-02-MAP",
            "PTN-ACL-02-PEER", "PTN-ACL-02-WRITE",
        ])

    def test_a_test_declaring_nothing_is_still_answered_for_by_its_topic(self):
        """The half that must not regress. Writing a clause on one test cannot
        cost the others their topic's answer, or the mapping would remove more
        than it adds."""
        out = self.run_js("""
            const r = H.contextTopics(D, ["multi-tenant"]);
            const hit = r.topics.filter(function (t) { return t.topic === "PTN-ACL-02"; })[0];
            return hit.matched;
        """)
        self.assertEqual(out, [{"unit": "PTN-ACL-02-TENANT", "precise": False}])
        # It carries no clause of its own -- the topic's list is exactly its
        # surface, so declaring one would have changed no answer.
        self.assertIsNone(self.data["units"]["PTN-ACL-02-TENANT"].get("surfaces"))

    def test_a_test_may_name_a_surface_its_topic_does_not(self):
        """Unit-level mapping is more precise, not merely narrower. A bulk
        export over an unencrypted channel is what `PTN-CRY-02-EXPORT` tests,
        and its subject does not carry that tag."""
        topic = self.data["topics"]["PTN-CRY-02"]["surfaces"]["any_of"]
        self.assertNotIn("export-report", topic)
        out = self.run_js("""
            const r = H.contextTopics(D, ["export-report"]);
            const hit = r.topics.filter(function (t) { return t.topic === "PTN-CRY-02"; })[0];
            return hit ? hit.matched.map(function (m) { return m.unit; }) : null;
        """)
        self.assertEqual(out, ["PTN-CRY-02-EXPORT"])

    def test_nothing_in_a_matched_topic_is_dropped(self):
        """Folded, never lost. A test hidden because a tag missed is a test the
        reader cannot discover was there, and they have just been sent to the
        subject it sits under."""
        out = self.run_js("""
            const bad = [];
            D.surfaces.forEach(function (s) {
              H.contextTopics(D, [s.tag]).topics.forEach(function (row) {
                const shown = row.matched.map(function (m) { return m.unit; })
                  .concat(row.broad).sort();
                const held = (D.topics[row.topic].units || []).slice().sort();
                if (shown.join(",") !== held.join(",")) bad.push([s.tag, row.topic]);
              });
            });
            return bad;
        """)
        self.assertEqual(out, [])

    def test_a_topic_reaches_the_page_only_when_one_of_its_tests_does(self):
        """A topic every one of whose tests has just said the selection does not
        name its surface is a card with nothing in it."""
        out = self.run_js("""
            return H.contextTopics(D, D.surfaces.map(function (s) { return s.tag; }))
              .topics.filter(function (r) { return r.matched.length === 0; })
              .map(function (r) { return r.topic; });
        """)
        self.assertEqual(out, [])

    def test_a_topic_says_whether_its_own_tag_or_a_test_in_it_reached_it(self):
        """A topic can be here because one of its tests declares a tag the
        subject does not. Six pairs do that today, and a card telling the reader
        the topic matched would be attributing to a subject a surface only one
        of its tests claims."""
        out = self.run_js("""
            const out = [];
            D.surfaces.forEach(function (s) {
              H.contextTopics(D, [s.tag]).topics.forEach(function (r) {
                if (!r.byTopic) out.push([s.tag, r.topic]);
              });
            });
            return out;
        """)
        self.assertIn(["export-report", "PTN-CRY-02"], out)
        # And the flag is the topic's own clause, not a guess from the units.
        for tag, tid in out:
            with self.subTest(tag=tag, topic=tid):
                self.assertNotIn(tag, self.data["topics"][tid]["surfaces"]["any_of"])

    def test_a_topic_whose_own_tag_matched_says_so(self):
        out = self.run_js("""
            return H.contextTopics(D, ["multi-tenant"]).topics.map(function (r) {
              return [r.topic, r.byTopic];
            });
        """)
        self.assertIn(["PTN-ACL-02", True], out)

    def test_a_topic_is_listed_once_even_when_two_tags_reach_it(self):
        out = self.run_js("""
            const seen = {}, dup = [];
            H.contextTopics(D, D.surfaces.map(function (s) { return s.tag; }))
              .topics.forEach(function (t) {
                if (seen[t.topic]) dup.push(t.topic);
                seen[t.topic] = true;
              });
            return dup;
        """)
        self.assertEqual(out, [])

    def test_selecting_every_tag_still_leaves_the_universal_topics_apart(self):
        """Seventeen topics that match every context would bury the handful the
        context actually selected, every time, under the same rows."""
        out = self.run_js("""
            const r = H.contextTopics(D, D.surfaces.map(function (s) { return s.tag; }));
            const tagged = {};
            r.topics.forEach(function (t) { tagged[t.topic] = true; });
            return r.always.filter(function (t) { return tagged[t]; });
        """)
        self.assertEqual(out, [])

    def test_an_entry_test_is_one_no_other_test_has_to_precede(self):
        """The only "you can begin here" claim the data supports. It is about
        the catalogue: nothing in it is a claim that a target permits the test.
        """
        out = self.run_js("""
            const out = {};
            D.topics["PTN-INJ-01"].units.forEach(function (id) {
              const c = H.entryCost(D, id);
              out[id] = { entry: c.entry, earned: c.earned };
            });
            return out;
        """)
        self.assertTrue(out["PTN-INJ-01-PROBE"]["entry"])
        # Everything else in the topic waits on what the probe establishes,
        # which is the chain this view exists to lead a reader into.
        rest = [k for k in out if k != "PTN-INJ-01-PROBE"]
        self.assertTrue(rest)
        for uid in rest:
            self.assertFalse(out[uid]["entry"], uid)
            self.assertEqual(out[uid]["earned"], ["surface.sql.injectable"], uid)

    def test_a_general_condition_of_the_engagement_is_not_something_owed(self):
        """Holding a session is not a test that has to have been run. Counting
        it as one would put "still required" on all but eight of the catalogue
        and make the label carry no information at all."""
        out = self.run_js("""
            let entry = 0, wrong = [];
            Object.keys(D.units).forEach(function (id) {
              const c = H.entryCost(D, id);
              if (c.entry) entry += 1;
              c.earned.forEach(function (f) {
                if ((D.facts[f] || {}).tier === "engagement") wrong.push([id, f]);
              });
            });
            return { entry: entry, wrong: wrong, total: Object.keys(D.units).length };
        """)
        self.assertEqual(out["wrong"], [])
        # A figure rather than a range: it is what the view's usefulness rests
        # on, and it must move visibly when the catalogue moves.
        self.assertEqual(out["entry"], 176)
        self.assertEqual(out["total"], 393)

    def test_an_engagement_condition_is_not_the_same_as_no_condition(self):
        """An engagement-tier fact is not a chain step and is also not nothing.

        `access.user` and `recon.entrypoints.mapped` are each established by a
        test in this catalogue. A unit requiring one has a condition its reader
        has to have met, so the classification may separate it from a chain step
        but must not lose it -- and the page has to print both lists.
        """
        out = self.run_js("""
            const out = {};
            ["PTN-INJ-10-PROBE", "PTN-ACL-02-PEER"].forEach(function (id) {
              const c = H.entryCost(D, id);
              out[id] = { engagement: c.engagement, earned: c.earned, entry: c.entry };
            });
            return out;
        """)
        probe = out["PTN-INJ-10-PROBE"]
        self.assertIn("recon.entrypoints.mapped", probe["engagement"])
        # Producers exist for it, which is exactly why the old label was wrong.
        self.assertTrue(self.data["producers"]["recon.entrypoints.mapped"])
        self.assertTrue(probe["entry"], "no chain step precedes it")
        self.assertNotEqual(probe["engagement"], [], "and it is not free of conditions")

    def test_every_unit_the_view_can_show_carries_at_least_one_named_condition(self):
        """Nothing in the catalogue declares an empty `requires`, so a rendered
        unit that named no condition at all would mean the classification had
        dropped one rather than that there was none to name."""
        out = self.run_js("""
            const bare = [];
            Object.keys(D.units).forEach(function (id) {
              const c = H.entryCost(D, id);
              if (!c.engagement.length && !c.earned.length) bare.push(id);
            });
            return bare;
        """)
        self.assertEqual(out, [])

    def test_a_tag_cannot_carry_a_character_that_would_leave_an_attribute(self):
        """The selector builds an href by concatenating tags. The schema
        constrains a tag to `[a-z0-9-]` and the validator refuses anything else,
        so this is the assertion that the two agree -- and the page escapes the
        attribute regardless, because the interesting case is the one where they
        stop agreeing."""
        out = self.run_js("""
            return D.surfaces.map(function (s) { return s.tag; })
              .filter(function (t) { return !/^[a-z0-9][a-z0-9-]*$/.test(t); });
        """)
        self.assertEqual(out, [])

    def test_a_context_establishes_no_capability(self):
        """The boundary this whole view sits behind. A surface tag describes a
        kind of thing, and no tag may be read as a fact in hand -- the two
        vocabularies do not meet, and a page that let them would be asserting
        something about a target it has never seen."""
        out = self.run_js("""
            const facts = {};
            Object.keys(D.facts).forEach(function (f) { facts[f] = true; });
            return D.surfaces.filter(function (s) { return facts[s.tag]; })
              .map(function (s) { return s.tag; });
        """)
        self.assertEqual(out, [])


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
        cls._tmp = TemporaryDirectory(prefix="navgrid-browser-")
        target = Path(cls._tmp.name) / "pentest-navgrid.html"
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
            ("#/unit/PTN-INJ-01-UNION", "UNION-based extraction"),
            ("#/wstg/ATHZ", "Testing Directory Traversal File Include"),
            ("#/unit/PTN-RES-01-READ", "Confirmed read outside the intended root"),
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(expected, self.text(fragment))

    def test_the_test_detail_carries_what_a_tester_performs_it_from(self):
        text = self.text("#/unit/PTN-INJ-01-UNION")
        for section in ("Objective", "Why this is a separate test", "Oracle",
                        "Sequence", "First false positive", "Done when",
                        "Safety boundary", "Payloads", "Tool", "Card",
                        "Local attack chain", "If this test is unsuccessful"):
            self.assertShows(text, section)

    def test_where_success_may_lead_is_answered_before_the_procedure(self):
        """On an authored unit the procedure runs for several screens. The
        product's own feature must not be at the bottom of them."""
        page = self.open("#/unit/PTN-RES-01-READ")
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
        page = self.open("#/unit/PTN-INJ-01-PROBE")
        self.assertGreaterEqual(page.locator(".gnode").count(), 5)
        self.assertGreaterEqual(page.locator(".gedge").count(), 4)
        text = self.driver.text()
        # The last heading names the relation the column holds. Every one of
        # this probe's nine outgoing edges is another context to try the same
        # test in, so the column is alternatives -- which is what it now says.
        for heading in ("Prerequisite", "This test", "Establishes",
                        "Another technique for this test"):
            self.assertShows(text, heading)
        # Direction is drawn, not implied.
        self.assertGreater(page.locator("path.gedge[marker-end]").count(), 0)

    def test_every_producer_of_a_prerequisite_is_named_not_just_the_first(self):
        text = self.text("#/unit/PTN-RES-01-READ")
        self.assertShows(text, "Established by")
        self.assertShows(text, "Traversal sequence survival probe")

    def test_a_continuation_states_what_success_here_does_not_supply(self):
        # Succeeding here supplies one condition of each continuation and not
        # the rest, which is the ordinary case and the one the old model got
        # wrong by calling it "unlocked".
        text = self.text("#/unit/PTN-RCN-07-MAP")
        # All five of this map's outgoing edges are escalations, so the column
        # is headed as one.
        self.assertShows(text, "Escalates to")
        self.assertShows(text, "Established here")
        self.assertShows(text, "Still required")

    def test_a_test_whose_result_leads_nowhere_explains_itself(self):
        # See the note in test_cli: this subject is the one still terminal.
        text = self.text("#/unit/PTN-INJ-11-TIME")
        self.assertIn("no test declares a use for it", text.lower())
        self.assertIn("does not rule out", text.lower())

    def test_both_routes_to_a_topic_separate_its_stages_from_its_alternatives(self):
        """The topic page and the test case page are two routes to the same
        list, and the standard-first one -- through the test case -- is the one
        the documentation calls primary. A split that reached only the other
        route would be a split most readers never see."""
        for fragment in ("#/topic/PTN-INJ-01", "#/case/WSTG-INPV-05"):
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
        body = self.text("#/topic/PTN-INJ-01")
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
        self.assertShows(self.text("#/chains"), "Where chains end")
        text = self.text("#/status")
        self.assertShows(text, "impacts excluded")
        dead = len(self.data["deadEnds"])
        impacts = len(self.data["impacts"])
        self.assertShows(text, str(dead))
        # Anchored to the label the figure is published under. A bare number
        # scan collides with every other figure on a page full of them: the
        # control family is 59 capabilities, and 49 dead ends plus 10 impacts is
        # also 59, which fails the check while the page says exactly the right
        # thing.
        self.assertNotIn(f"{dead + impacts} — impacts excluded", text)

    # --- a concept written ahead of the tests ----------------------------

    def test_a_capability_no_test_reaches_says_so_rather_than_reporting_a_search(self):
        """"No route is charted within five steps" is true of a fact nothing in
        the catalogue names, and it is the wrong sentence: it reports the result
        of a search, which reads as a route that might be six steps long. The
        register knows the difference, and the page has to say which one it is
        looking at."""
        entry = self.data["uncovered"][0]
        fid = entry["facts"][0]
        text = self.text("#/capability/" + fid)
        self.assertShows(text, "No test in this catalogue establishes this")
        self.assertNotIn("within five steps", text)
        # The authored reason, not a paraphrase of it.
        self.assertShows(text, " ".join(entry["reason"].split()[:8]))

    def test_every_registered_capability_says_it_on_its_own_page(self):
        """A sweep rather than the one entry that prompted it: what would undo
        this is a second entry added to the register and never rendered."""
        listed = [f for e in self.data["uncovered"] for f in e["facts"]]
        self.assertTrue(listed, "nothing is registered, so this proves nothing")
        for fid in listed:
            with self.subTest(fact=fid):
                self.assertShows(self.text("#/capability/" + fid),
                                 "No test in this catalogue establishes this")

    def test_an_outcome_nothing_reaches_is_not_listed_as_two_zeroes(self):
        """It sits in the same list as the outcomes tests do arrive at. Reported
        by the numbers it happens to have, it reads as an oversight rather than
        as a decision that was written down."""
        fid = self.data["uncovered"][0]["facts"][0]
        self.assertIn(fid, self.data["impacts"])
        row = self.open("#/chains").locator('a[href="#/capability/' + fid + '"]').first
        self.assertShows(row.inner_text(), "no test reaches it yet")

    def test_the_map_shades_it_apart_from_the_outcomes_tests_reach(self):
        """Against `unused` rather than against `impact`: both are places the
        chart is not, and "nothing goes on from here" is a different fact about
        the catalogue than "nothing arrives here yet"."""
        page = self.open("#/chains")
        listed = [f for e in self.data["uncovered"] for f in e["facts"]]
        self.assertTrue(listed, "nothing is registered, so this proves nothing")
        for fid in listed:
            with self.subTest(fact=fid):
                cell = page.locator('.mcell[href="#/capability/' + fid + '"]').first
                self.assertIn("unwritten", cell.get_attribute("class"))
        self.assertShows(self.driver.text(),
                         "modelled, and no test in this catalogue names it yet")

    def test_the_status_page_counts_it_apart_from_the_dead_ends(self):
        """One number covering both would answer neither question. A capability
        tests establish and none uses is a gap in the chart; one no test names
        at all is a gap in the catalogue."""
        text = self.text("#/status")
        listed = {f for e in self.data["uncovered"] for f in e["facts"]}
        self.assertShows(text, "Capabilities no test reaches yet")
        self.assertShows(text, "Capabilities no test uses")
        # And the two sets really are disjoint, which is what makes two rows
        # honest rather than double counting.
        self.assertFalse(listed & set(self.data["deadEnds"]))

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

    def test_an_impact_shows_the_routes_charted_to_it(self):
        """The defect this view exists for. The chains page sent a reader to an
        impact "to see the routes charted to it" and the impact said a chain
        ends here and stopped, because the only search the artefact had ran
        forwards and forwards from an outcome there is nothing."""
        page = self.open("#/capability/impact.data.disclosed")
        text = self.driver.text()
        self.assertShows(text, "Routes charted to here")
        self.assertNotIn("A chain ends here", text)
        self.assertGreater(page.locator(".route").count(), 0)
        # Drawn in reading order: the route starts on a capability and every
        # step names a test, whichever direction the search that found it walked.
        self.assertGreater(page.locator(".rstep.unit").count(), 0)
        self.assertTrue(page.locator(".rstep.start").first.inner_text())

    def test_an_impact_lists_every_capability_a_route_to_it_begins_at(self):
        """The count in the heading and the rows below it are one claim printed
        twice. A heading saying forty-eight above nine rows would be read as the
        catalogue's figure rather than as a rendering fault."""
        page = self.open("#/capability/impact.data.disclosed")
        heading = [h for h in page.locator("main h3").all_inner_texts()
                   if "route to here can begin" in h.lower()]
        self.assertEqual(len(heading), 1, "the list of starts is not on the page")
        counted = int(heading[0].rsplit("·", 1)[1].strip())
        self.assertGreater(counted, 0)
        rows = page.locator("main .rows").last.locator("a.row")
        self.assertEqual(rows.count(), counted)
        # Nearest first, and the distance is printed rather than implied.
        self.assertRegex(rows.first.inner_text(), r"\d+ steps?")

    def test_an_outcome_no_route_reaches_is_not_listed_as_a_destination(self):
        """`access.host` is granted rather than earned and reaches no outcome,
        so it appears on no impact's list of starts. Checked in the rendered
        page because that is where the claim is made."""
        page = self.open("#/capability/impact.data.disclosed")
        rows = page.locator("main .rows").last.locator("a.row").all_inner_texts()
        self.assertTrue(rows)
        self.assertNotIn("access.host", "\n".join(rows))

    def test_the_chains_page_leads_with_the_destinations(self):
        """A page named for chains opened on a picture of every capability in
        the file -- a glossary, shaded by coverage. Both belong here; the order
        is the claim."""
        text = self.text("#/chains")
        ends = text.lower().index("where chains end")
        chart = text.lower().index("the chart, at the scale of the whole catalogue")
        self.assertLess(ends, chart)

    def test_following_a_destination_from_the_chains_page_reaches_a_route(self):
        """End to end, the way a reader meets it: the promise on one page and
        what the next page actually draws."""
        page = self.open("#/chains")
        page.click('main .rows a.row[href^="#/capability/impact."]')
        self.driver.wait_for_view("Attack chains")
        self.assertShows(self.driver.text(), "Routes charted to here")
        self.assertGreater(page.locator(".route").count(), 0)

    def test_typing_the_shorthand_for_a_class_of_bug_reaches_the_topic(self):
        """The end-to-end version of the whole change: four letters typed into
        the real file, and the topic they name on the page."""
        for term, topic in (("idor", "PTN-ACL-02"), ("ssrf", "PTN-RES-03"),
                            ("ssti", "PTN-INJ-10"), ("lfi", "PTN-RES-01")):
            with self.subTest(term=term):
                text = self.text("#/search/" + term)
                self.assertGreater(self.driver.count('a.card[href="#/topic/%s"]' % topic), 0,
                                   f"{term} did not reach {topic}")
                self.assertShows(text, "Also searched")

    def test_the_page_says_which_phrase_was_searched_instead(self):
        text = self.text("#/search/idor")
        self.assertShows(text, "No entry here is named idor")
        self.assertShows(text, "object-level access control")

    def test_an_expanded_result_carries_the_expansion_that_found_it(self):
        self.open("#/search/idor")
        card = self.driver.text('a.card[href="#/topic/PTN-ACL-02"]')
        self.assertIn("object-level access control", card.lower())

    def test_following_an_expanded_result_reaches_the_topic_it_named(self):
        page = self.open("#/search/bola")
        before = self.driver.heading()
        page.locator('a.card[href="#/topic/PTN-ACL-02"]').first.click()
        self.driver.wait_for_view(before)
        self.assertEqual(self.driver.hash(), "#/topic/PTN-ACL-02")
        self.assertShows(self.driver.text(), "Object-level access control")

    def test_a_term_that_only_matches_inside_longer_words_says_so(self):
        """`rce` is in `resource` and `force`. The count in the heading is real;
        what it counts is coincidence, and the reader cannot see that from the
        cards themselves."""
        text = self.text("#/search/rce")
        self.assertShows(text, "inside a longer word rather than standing as one")

    def test_results_past_the_first_forty_are_readable_rather_than_withheld(self):
        """A count of what is not shown is not the same as being able to read
        it, and a substring cannot be made narrower."""
        page = self.open("#/search/path")
        self.assertGreater(page.locator("details.fold").count(), 0,
                           "no kind overflowed, so this term no longer tests anything")
        fold = page.locator("details.fold").first
        summary = fold.locator("summary").inner_text()
        hidden = fold.locator("a.card").count()
        # The number in the summary is the number of cards behind it, asserted
        # against each other rather than against a figure that goes stale the
        # next time a unit is written.
        self.assertEqual(summary.strip(), f"Show the other {hidden}")
        self.assertFalse(fold.locator("a.card").first.is_visible())
        fold.locator("summary").click()
        self.assertTrue(fold.locator("a.card").first.is_visible())

    def test_the_execution_fields_are_reachable_without_scrolling(self):
        """The measurement this change was built on, kept as the check.

        Before it, on a 900px viewport, the oracle sat below the fold on 39 of
        the 47 written units that have one and the sequence on 54 of 72 — so a
        tester who came back mid-test to see what counts as a positive found the
        assumptions instead, every time. Asserted rather than described, because
        the thing that would undo it is a block quietly added above them.
        """
        live = [
            uid for uid, u in self.data["units"].items()
            if u.get("status") in ("authored", "sketched")
        ]
        self.assertGreater(len(live), 50, "too few written units for this to mean anything")
        below = {"Oracle": [], "Sequence": [], "First false positive": []}
        for uid in sorted(live):
            page = self.open("#/unit/" + uid)
            tops = page.evaluate("""() => {
              const out = {};
              document.querySelectorAll('main .card .k').forEach(el => {
                if (!(el.textContent in out)) {
                  out[el.textContent] = el.getBoundingClientRect().top + window.scrollY;
                }
              });
              return out;
            }""")
            for label in below:
                if label in tops and tops[label] > 900:
                    below[label].append(uid)
        self.assertEqual(below["Oracle"], [])
        self.assertEqual(below["Sequence"], [])
        # The first false positive follows the sequence, so a long procedure can
        # still push it under. A quarter of them at most, and never the oracle.
        self.assertLess(len(below["First false positive"]), len(live) // 4)

    def test_the_procedure_is_grouped_and_named_before_the_orientation(self):
        page = self.open("#/unit/PTN-INJ-01-UNION")
        headings = [h.strip() for h in page.locator("main h3").all_inner_texts()]
        self.assertIn("Run this test", headings)
        self.assertIn("Orientation", headings)
        self.assertLess(headings.index("Run this test"), headings.index("Orientation"))

    def test_the_orientation_is_moved_rather_than_hidden(self):
        """One screen down, not folded away. A first reader is reading the whole
        unit; a returning one is not, and neither is served by material that has
        to be opened before it can be read."""
        # A unit that carries all three: `PTN-INJ-01-UNION` has no triage or
        # hypotheses, so it would pass this by having nothing to move.
        text = self.text("#/unit/PTN-ACL-02-IMPACT")
        for phrase in ("Where to start", "What this assumes", "Why this is a separate test"):
            with self.subTest(phrase=phrase):
                self.assertShows(text, phrase)
        self.assertEqual(self.driver.count("main details.fold"), 0)

    def test_an_outline_unit_shows_no_empty_procedure_heading(self):
        """It has no procedure to head. The notice saying so is what the reader
        gets instead, and it sits where the procedure would have been."""
        page = self.open("#/unit/PTN-AUT-07-BINDING")
        headings = [h.strip() for h in page.locator("main h3").all_inner_texts()]
        self.assertNotIn("Run this test", headings)
        self.assertShows(self.driver.text(), "This test is an outline")

    def test_focus_follows_the_route_rather_than_staying_where_it_was(self):
        """Replacing the document leaves focus on a link that no longer exists,
        which browsers reset to the body — so a keyboard reader tabs through the
        whole header to reach what they just opened, on every navigation."""
        page = self.open("#/topic/PTN-INJ-01")
        page.locator('main a[href^="#/unit/"]').first.focus()
        before = self.driver.heading()
        page.keyboard.press("Enter")
        self.driver.wait_for_view(before)
        focused = page.evaluate("""() => {
          const el = document.activeElement;
          return { tag: el.tagName, text: (el.textContent || '').trim().slice(0, 60) };
        }""")
        self.assertEqual(focused["tag"], "H2")
        self.assertEqual(focused["text"], self.driver.heading().strip()[:60])

    def test_the_focused_heading_is_not_put_into_the_tab_order(self):
        """Focusable so the route can move focus to it; not tabbable, or every
        reader would meet a stop that is not a control."""
        page = self.open("#/unit/PTN-INJ-01-UNION")
        self.assertEqual(page.get_attribute("main h2", "tabindex"), "-1")

    def test_the_search_box_is_reachable_from_the_keyboard(self):
        page = self.open("#/unit/PTN-INJ-01-UNION")
        page.keyboard.press("Control+k")
        self.assertEqual(page.evaluate("document.activeElement.id"), "q")

    def test_the_shortcut_does_not_fire_without_its_modifier(self):
        """A bare key would fire while the reader is typing into the box it
        focuses."""
        page = self.open("#/unit/PTN-INJ-01-UNION")
        page.keyboard.press("k")
        self.assertNotEqual(page.evaluate("document.activeElement.id"), "q")

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
        page = self.open("#/unit/PTN-RCN-02-MAP")
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

    def test_the_procedure_is_rendered_before_the_orientation(self):
        """This asserts the reverse of what it used to, and the reversal is the
        change rather than a concession to it.

        What it asserted before was that where to start comes before how to run
        the test, because a reader who cannot answer the first has nothing to
        point the sequence at. That is a true description of a first read and
        not of the read this page mostly gets: the cost of it was the oracle
        sitting below the fold on most units that have one. The orientation is
        still rendered in full, one screen down -- which is what the assertions
        below keep, on a unit the newer order test does not use.
        """
        page = self.open("#/unit/PTN-RES-01-PROBE")
        text = self.driver.text()
        for section in ("What this assumes", "Where to start", "Where the input lands"):
            self.assertShows(text, section)
        labels = [t.strip().lower() for t in page.locator("main .k").all_inner_texts()]
        self.assertLess(labels.index("sequence"), labels.index("where to start"),
                        "the procedure is printed below the orientation again")
        self.assertLess(labels.index("oracle"), labels.index("what this assumes"))

    def test_a_recon_unit_shows_no_sink(self):
        """The schema forbids the field there; this is the page agreeing, so a
        section cannot appear from a stale build."""
        page = self.open("#/unit/PTN-RCN-02-MAP")
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

    def test_the_sticky_offset_tracks_the_header_it_has_to_clear(self):
        """The mechanism, asserted directly rather than through the geometry it
        produces.

        The sibling test below reads the heading's position, which depends on
        scroll, on which column is tallest and on how the cells wrapped. When it
        failed under load it took a diagnosis to learn that the offset itself
        was stale. This asks the offset, at all three widths the site header
        wraps at: one row, two rows, three.
        """
        page = self.driver.page
        read = lambda: (
            page.evaluate("parseFloat(getComputedStyle(document.documentElement)"
                          ".getPropertyValue('--stick')) || 0"),
            page.evaluate("document.querySelector('header').getBoundingClientRect().height"),
        )
        for width in (1280, 700, 480):
            with self.subTest(width=width):
                page.set_viewport_size({"width": width, "height": 800})
                self.open("#/chains")
                # The observer delivers its first notification on the frame
                # after it starts observing, so the assertion is about where
                # the offset settles rather than what it reads in the first
                # millisecond. A value that never settles fails here, which is
                # the defect this replaced.
                self.driver.wait_for_render(
                    lambda: abs(read()[0] - read()[1]) <= 1.5
                )
                offset, header = read()
                self.assertAlmostEqual(
                    offset, header, delta=1.5,
                    msg=f"the offset is {offset} and the header is {header}",
                )
        page.set_viewport_size({"width": 1280, "height": 900})

    def test_the_column_headings_stay_put_while_the_columns_are_read(self):
        """Fifty-nine cells is a long way to scroll with no idea which column
        you are in. The first version stuck them to a wrapper whose overflow
        made it the scrollport, so they slid away at every width; the second
        stuck them to the top of the viewport, where the site header already
        is. What the offset has to track is the header's real height, which
        changes as it wraps.

        Scrolled to the map rather than to a fixed pixel. A hard-coded offset
        measures whatever the page happens to have above the map, so it stops
        testing stickiness the moment anything is added or removed there --
        which is how it read a heading sitting at its natural position as a
        heading that had come unstuck."""
        page = self.open("#/chains")
        for width in (1280, 700):
            with self.subTest(width=width):
                page.set_viewport_size({"width": width, "height": 800})
                self.open("#/chains")
                # Far enough into the map that its columns are being read, and
                # its headings can only still be at the top of the viewport by
                # sticking there.
                page.evaluate("""() => {
                  const map = document.querySelector('.chainmap');
                  window.scrollTo(0, window.scrollY + map.getBoundingClientRect().top + 600);
                }""")
                self.driver.wait_for_render(
                    lambda: page.evaluate("""() => {
                      const bar = document.querySelector('header')
                                    .getBoundingClientRect().bottom;
                      return document.querySelector('.chainmap')
                               .getBoundingClientRect().top < bar - 400;
                    }""")
                )
                # The offset is delivered by a resize observer, which runs after
                # layout rather than during it, so between the render and that
                # delivery --stick still holds the previous width's height. The
                # assertions below are about the settled state; measuring before
                # the observer has caught up reads a transient the page corrects
                # a frame later, and fails roughly once in fifteen runs at the
                # width where the header wraps.
                self.driver.wait_for_render(
                    lambda: page.evaluate("""() => {
                      const stick = parseFloat(getComputedStyle(document.documentElement)
                                      .getPropertyValue('--stick')) || 0;
                      return Math.abs(stick - document.querySelector('header')
                                      .getBoundingClientRect().height) <= 1;
                    }""")
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
        page = self.open("#/unit/PTN-INJ-01-PROBE")
        node = page.locator(".gnode.link").first
        target = node.get_attribute("data-go")
        before = self.driver.heading()
        node.click()
        self.assertNotEqual(self.driver.wait_for_view(before), "Standards")
        self.assertEqual(self.driver.hash(), target)

    def test_a_graph_node_is_reachable_and_usable_from_the_keyboard(self):
        page = self.open("#/unit/PTN-INJ-01-PROBE")
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
        page = self.open("#/unit/PTN-INJ-01-PROBE")
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
        page = self.open("#/unit/PTN-RES-01-READ")
        before = self.driver.heading()
        page.click("text=Inclusion and execution of the resolved path")
        self.driver.wait_for_view(before)
        self.assertIn("PTN-RES-01-EXEC", self.driver.hash())

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
                         "#/unit/PTN-INJ-01-UNION", "#/unit/PTN-RES-01-READ",
                         "#/chains", "#/status", "#/capability/access.user"):
            text = self.text(fragment).lower()
            for phrase in forbidden:
                self.assertNotIn(phrase, text, f"{fragment}: {phrase}")

    def test_the_conditional_wording_the_model_depends_on_is_present(self):
        text = self.text("#/unit/PTN-INJ-01-PROBE")
        self.assertShows(text, "may become relevant")
        self.assertShows(text, "Another technique for this test")

    # --- the context journey ---------------------------------------------

    def test_attack_chains_offers_a_way_in_that_needs_no_identifier(self):
        """The page a reader lands on from the navigation. Before this it opened
        on the capability map, which is the model rather than a way in."""
        text = self.text("#/chains")
        self.assertShows(text, "Start from what you are looking at")

    def test_the_selector_lists_every_tag_with_what_it_reaches(self):
        page = self.open("#/chains/context")
        self.assertEqual(self.driver.count(".chip"), len(self.data["surfaces"]))
        self.assertShows(self.driver.text(), "Nothing chosen yet")
        # A tag no topic declares is dimmed rather than dropped: a reader who
        # cannot find it would conclude the vocabulary lacks it.
        self.assertEqual(
            page.inner_text('.chip[href$="nosql-backed-param"]').split()[-1], "0"
        )
        self.assertEqual(self.driver.count(".chip.none"), 1)

    def test_the_selector_is_grouped_by_what_each_tag_names(self):
        """52 tags in one grid asked a reader to hold the whole list to discover
        that `payment` and `sql-backed-param` are not the same kind of answer."""
        page = self.open("#/chains/context")
        headings = [h.strip().lower() for h in page.locator(".dimension h4").all_inner_texts()]
        self.assertEqual(headings, [
            "channel", "entry point", "business function", "security context",
            "environment", "processor", "observed behaviour",
        ])

    def test_every_tag_is_in_exactly_one_group_and_none_is_lost(self):
        page = self.open("#/chains/context")
        placed = []
        for group in range(page.locator(".dimension").count()):
            block = page.locator(".dimension").nth(group)
            placed += [c.split()[0] for c in block.locator(".chip").all_inner_texts()]
        self.assertEqual(sorted(placed), sorted(s["tag"] for s in self.data["surfaces"]))
        self.assertEqual(len(placed), len(set(placed)), "a tag appears in two groups")

    def test_each_group_says_what_choosing_from_it_means(self):
        """The caveat belongs where it is read. A reader picking from `processor`
        is choosing a hypothesis, and a document saying so elsewhere is a
        document they are not looking at."""
        page = self.open("#/chains/context")
        notes = {}
        for group in range(page.locator(".dimension").count()):
            block = page.locator(".dimension").nth(group)
            notes[block.locator("h4").inner_text().strip().lower()] = \
                block.locator("p.muted").inner_text()
        self.assertEqual(len(notes), 7)
        for heading, note in notes.items():
            with self.subTest(group=heading):
                self.assertTrue(note.strip(), heading)
        self.assertIn("hypothesis until a test confirms it", notes["processor"])
        self.assertIn("the tester has actually seen", notes["observed behaviour"])

    def test_the_page_says_the_grouping_is_not_a_filter(self):
        """Seven labelled rows look like a control where you pick one from each
        and get the intersection. This page unions, and a layout implying a
        semantics the code does not have is the same defect as prose that does."""
        text = self.text("#/chains/context")
        self.assertShows(text, "not how the selection works")
        self.assertShows(text, "does not narrow to where they overlap")

    def test_choosing_from_a_group_still_selects(self):
        page = self.open("#/chains/context")
        page.click('.dimension a.chip[href="#/chains/context/graphql"]')
        self.driver.wait_for_render(lambda: self.driver.count(".chip.on") == 1)
        self.assertEqual(page.evaluate("location.hash"), "#/chains/context/graphql")
        self.assertShows(self.driver.text(), "Object-level access control")

    def test_choosing_a_tag_is_navigation_rather_than_state(self):
        """The selection lives in the URL, so it can be sent to a colleague and
        nothing is held in this browser."""
        page = self.open("#/chains/context")
        before = self.driver.heading()
        page.click('a.chip[href="#/chains/context/search"]')
        # Waited on the redraw rather than on the hash. The assignment happens
        # first and `hashchange` is dispatched in a later task, so a test that
        # waits on the URL reads the document in the gap and passes or fails on
        # which the machine got to first.
        self.driver.wait_for_render(lambda: self.driver.count(".chip.on") == 1)
        self.assertEqual(page.evaluate("location.hash"), "#/chains/context/search")
        self.assertEqual(before, "Tests by context")

    def test_a_second_tag_adds_to_the_selection_and_a_third_click_removes_it(self):
        page = self.open("#/chains/context/search")
        page.click('a.chip[href="#/chains/context/search+rest-api"]')
        self.driver.wait_for_render(lambda: self.driver.count(".chip.on") == 2)
        # The href on the search chip is now the selection without it, so this
        # takes search back out and leaves rest-api behind.
        page.click('a.chip[href="#/chains/context/rest-api"]')
        self.driver.wait_for_render(lambda: self.driver.count(".chip.on") == 1)
        self.assertEqual(page.evaluate("location.hash"), "#/chains/context/rest-api")

    def test_a_result_says_what_put_each_topic_in_front_of_the_reader(self):
        text = self.text("#/chains/context/search")
        self.assertShows(text, "Matched because the context is")
        self.assertShows(text, "Free-text query surface")
        # The relation is stated rather than applied silently: a reader who
        # never typed "sql-backed-param" is owed the reason SQL injection is here.
        self.assertShows(text, "Often carried alongside")
        self.assertShows(text, "sql-backed-param")
        self.assertShows(text, "SQL injection")

    def test_a_card_never_says_the_context_is_a_tag_only_associated_with_it(self):
        """The sentence a reader actually reads, next to each topic.

        Correcting the paragraph above the results and leaving this one alone
        left the page still asserting, one line lower, that a search box *is* a
        parameter reaching a SQL data store. The disclaimer was two inches away
        and said the opposite.
        """
        page = self.open("#/chains/context/search")
        card = page.locator('.card:has-text("SQL injection")').first
        text = " ".join(card.inner_text().split())
        self.assertIn("Often carried by such a surface", text)
        self.assertNotIn("Matched because the context is: Parameter reaching a SQL", text)

    def test_a_card_separates_the_three_reasons_a_topic_can_be_here(self):
        """`graphql` reaches object-level access control by all three at once:
        the tag chosen, the tag it always also is, and one it is merely often
        found with. One line for all three cannot be true of all three."""
        page = self.open("#/chains/context/graphql")
        card = page.locator('.card:has-text("Object-level access control")').first
        text = " ".join(card.inner_text().split())
        self.assertIn("Matched because the context is: GraphQL endpoint", text)
        self.assertIn("And always also is: Structured machine-facing API", text)
        self.assertIn(
            "Often carried by such a surface, and not implied by your selection: "
            "Direct object reference in a request",
            text,
        )

    def test_no_card_anywhere_presents_an_association_as_the_context(self):
        """Swept over every tag rather than the two that happen to show it, so a
        relation added later cannot reintroduce the wording."""
        bad, read = [], 0
        for surface in self.data["surfaces"]:
            if not surface["often"]:
                continue
            page = self.open("#/chains/context/" + surface["tag"])
            labels = {
                s["label"] for s in self.data["surfaces"] if s["tag"] in surface["often"]
            }
            for block in page.locator(".why").all_inner_texts():
                line = " ".join(block.split())
                if not line.startswith("Matched because the context is:"):
                    continue
                read += 1
                for label in labels:
                    if label in line:
                        bad.append((surface["tag"], label))
        self.assertEqual(bad, [])
        # A selector that stopped matching would make this pass by reading none.
        self.assertGreater(read, 20, "no reason lines were examined at all")

    def test_no_label_says_a_topic_declared_a_tag_it_does_not(self):
        """The wording this round removed, swept over every tag rather than the
        one that showed it. `export-report` reaches `PTN-CRY-02` because a test
        in it is about a bulk export; the subject is about assets in transit and
        declares no such tag, and the page used to head that result "topics
        declare a tag you chose"."""
        checked = 0
        for surface in self.data["surfaces"]:
            if not surface["units"]:
                continue
            text = self.text("#/chains/context/" + surface["tag"]).lower()
            checked += 1
            with self.subTest(tag=surface["tag"]):
                self.assertNotIn("declare a tag you chose", text)
                self.assertNotIn("declares a tag you chose", text)
                self.assertIn("your selection reaches", text)
        self.assertGreater(checked, 5, "no tag with a unit-level declaration was read")

    def test_a_card_reached_only_through_a_test_says_which_route(self):
        page = self.open("#/chains/context/export-report")
        card = page.locator('.card:has-text("Sensitive data over unprotected transport")').first
        text = " ".join(card.inner_text().split())
        self.assertIn("This topic declares none of these", text)
        self.assertIn("Reached because a test in it declares", text)
        self.assertNotIn("Matched because the context is", text)

    def test_the_selector_no_longer_calls_its_count_a_declaration(self):
        """The count became a union in this same change and the sentence beside
        it did not: three tags show a number larger than the topics declaring
        them."""
        text = self.text("#/chains/context")
        self.assertNotIn("how many topics in this catalogue declare it", text)
        self.assertShows(text, "how many topics it reaches")
        self.assertShows(text, "through a test that declares one")

    def test_an_association_is_never_printed_as_something_that_follows(self):
        """The sentence this change exists to remove. It said an edge was "true
        of every surface carrying the first" over a relation where 19 of 20 were
        not, and a reader had no way to tell which one they were reading."""
        text = self.text("#/chains/context/search")
        self.assertNotIn("true of every surface carrying", text)
        self.assertNotIn("Also counted as chosen", text)
        # And says what it is instead, on the same screen.
        self.assertShows(text, "not implied by anything you chose")
        self.assertShows(text, "may query no database at all")

    def test_a_tag_a_selection_always_is_reads_as_certain(self):
        """`graphql` carries the one relation in the file that is true of every
        surface, so it is the one place the stronger wording is earned."""
        text = self.text("#/chains/context/graphql")
        self.assertShows(text, "Also chosen, because a surface you described always is one")
        self.assertShows(text, "rest-api")

    def test_the_weaker_tier_says_which_kind_of_reach_produced_it(self):
        text = self.text("#/chains/context/search")
        self.assertShows(text, "more through a tag often carried alongside")
        self.assertShows(text, "not something your selection established")

    def test_a_selection_with_no_relations_shows_neither_paragraph(self):
        """`login-form` used to imply a session cookie, which its own
        description contradicts. Nothing replaced the edge, so nothing should
        appear where it used to be."""
        text = self.text("#/chains/context/login-form")
        self.assertNotIn("Often carried alongside", text)
        self.assertNotIn("always is one", text)
        self.assertShows(text, "Matched because the context is")

    def test_a_chip_says_what_kind_of_thing_its_tag_names(self):
        """52 tags in one list mixed six kinds of statement with nothing to tell
        them apart. Grouping the selector is a later change; naming the kind is
        what stops the list being unreadable in the meantime."""
        page = self.open("#/chains/context")
        for tag, kind in (("rest-api", "channel"),
                          ("payment", "business function"),
                          ("multi-tenant", "security context"),
                          ("sql-backed-param", "processor"),
                          ("stored-then-rendered", "observed behaviour")):
            with self.subTest(tag=tag):
                title = page.get_attribute('.chip[href$="/%s"]' % tag, "title")
                self.assertIn("(" + kind + ")", title)

    def test_a_test_that_needs_no_predecessor_is_told_apart_from_one_that_does(self):
        text = self.text("#/chains/context/sql-backed-param")
        self.assertShows(text, "Injection point probe")
        self.assertShows(text, "no chain step has to precede it")
        self.assertShows(text, "a chain step establishes first")

    def test_an_engagement_condition_is_printed_rather_than_dropped(self):
        """The whole reason both lists are computed. Printing only the second
        put "nothing precedes this" over units requiring a capability a test in
        the catalogue establishes -- false, and false on the units the view is
        most likely to be read for."""
        page = self.open("#/chains/context/sql-backed-param")
        text = self.driver.text()
        self.assertShows(text, "assumed held")
        self.assertShows(text, "Unauthenticated caller")
        # Its own line, so it cannot be read as either of the other two states.
        self.assertTrue(self.driver.count(".need.assumed") > 0)
        row = page.inner_text('a.row[href="#/unit/PTN-INJ-01-PROBE"]')
        self.assertIn("assumed held", row)
        self.assertIn("no chain step has to precede it", row)

    def test_the_page_never_claims_a_unit_declares_no_earlier_test(self):
        """The wording that was wrong, asserted absent by name. Every unit in
        the catalogue declares at least one condition, so this sentence could
        never have been true of any of them."""
        for fragment in ("#/chains/context/sql-backed-param",
                         "#/chains/context/search",
                         "#/chains/context/object-id-param"):
            with self.subTest(fragment=fragment):
                self.assertNotIn("no earlier test declared", self.text(fragment))

    def test_the_universal_topics_are_folded_rather_than_repeated(self):
        page = self.open("#/chains/context/search")
        # Selected by what it is rather than by being the only fold on the page:
        # a topic whose tests declare their own surfaces folds the rest of
        # itself, and this one is not that.
        self.assertEqual(self.driver.count("details.fold:not(.rest)"), 1)
        summary = page.inner_text("details.fold:not(.rest) > summary")
        self.assertIn("every context", summary)
        self.assertIn(str(len(self.data["alwaysTopics"])), summary)

    def test_a_result_opens_a_test_and_its_existing_chain(self):
        """The context view hands off to the catalogue and adds no chain of its
        own: what follows a test is the same derivation it always was."""
        page = self.open("#/chains/context/sql-backed-param")
        before = self.driver.heading()
        page.click('a.row[href="#/unit/PTN-INJ-01-PROBE"]')
        self.assertEqual(self.driver.wait_for_view(before), "Injection point probe")
        self.assertShows(self.driver.text(), "Local attack chain")

    def test_the_graph_column_is_headed_by_the_relation_it_holds(self):
        """The picture must not call an alternative an escalation.

        `PTN-CLT-01-PROBE` establishes a reflection point, and every one of the
        nine tests that follow is another context to try it in -- alternatives
        to each other, not steps past it. The list under the graph has grouped
        them correctly since the tiers landed; the graph headed the same column
        "Potential continuation" regardless, which is the one thing the tier
        vocabulary exists to prevent: three different relations printing under
        one word.

        Asserted against the wording the list already uses, so the two views of
        one derivation cannot drift into two vocabularies.
        """
        alternatives = self.text("#/unit/PTN-CLT-01-PROBE")
        self.assertShows(alternatives, "Another technique for this test")
        self.assertNotIn("Potential continuation", alternatives)

        # The same graph, on a test whose outgoing edge really is an escalation.
        escalation = self.text("#/unit/PTN-CLT-01-HTMLBODY")
        self.assertShows(escalation, "Escalates to")

    def test_a_mixed_column_names_the_relation_on_the_edge_not_the_subtitle(self):
        """The subtitle is wrapped to one line and carries the condition count.

        Prefixing the relation onto it pushed that count off the end -- "This is
        a general prerequisite of — 2 further conditions" rendered as "This is a
        general prerequisite…", losing the figure the node exists to carry. The
        arrow says the relation instead, and the subtitle keeps its number.
        """
        self.open("#/unit/PTN-IDN-01-POLICY/all")
        self.driver.page.wait_for_timeout(200)
        labels = self.driver.page.eval_on_selector_all(
            "svg text", "els => els.map(e => e.textContent)"
        )
        self.assertTrue([x for x in labels if x in ("escalates to", "also needs")],
                        "a mixed column must name each relation on its edge")
        truncated = [x for x in labels if x.endswith("\u2026")]
        for phrase in ("This is a general prerequisite", "Escalates to", "Another technique"):
            self.assertFalse([x for x in truncated if x.startswith(phrase)],
                             f"a relation is being truncated into the subtitle: {phrase}")

    def test_an_unknown_tag_in_the_url_leaves_the_rest_of_the_selection(self):
        """A link may arrive from a colleague running a different build. The
        useful answer to a tag this file does not carry is the rest."""
        text = self.text("#/chains/context/search+not-a-real-tag")
        self.assertShows(text, "Free-text query surface")
        self.assertNotIn("not-a-real-tag", text)

    def test_it_never_says_a_test_applies_to_anything(self):
        """The language is the control. Every statement is about the catalogue's
        own filing, and a page that said "applicable" would be claiming
        something about an application it has never seen."""
        text = self.text("#/chains/context/object-id-param").lower()
        for claim in ("applies to your", "applicable to", "is reachable",
                      "unlocked", "available on your target", "you have"):
            self.assertNotIn(claim, text, claim)
        self.assertIn("may apply", text)
        # The page has to say what it is not, not merely avoid saying what it is.
        self.assertIn("ever a claim that you do or do not have it", text)
        self.assertIn("not of an application", self.text("#/chains/context").lower())

    def test_choosing_a_context_writes_nothing_into_the_browser(self):
        """The selection is a URL and nothing else. Asserted after driving the
        view, because an empty store before the interaction proves nothing."""
        page = self.open("#/chains/context/search+rest-api")
        page.click('a.chip[href="#/chains/context/rest-api"]')
        self.driver.wait_for_render(lambda: self.driver.count(".chip.on") == 1)
        self.assertEqual(
            page.evaluate("[localStorage.length, sessionStorage.length, document.cookie]"),
            [0, 0, ""],
        )

    def test_the_capability_map_is_still_on_the_page_it_was_on(self):
        """Kept rather than moved. It is where the catalogue's own gaps are
        reported, and burying the honesty behind a friendlier view is the one
        way this change could make the product worse."""
        page = self.open("#/chains")
        self.assertEqual(self.driver.count(".chainmap"), 1)
        self.assertEqual(
            page.evaluate("document.querySelector('nav a.on').textContent"),
            "Attack Chains",
        )

    def test_no_link_is_nested_inside_another(self):
        """Invisible to every assertion on text, and fatal to the layout.

        An anchor inside an anchor is not nesting the parser accepts: it closes
        the outer one, and the rest of that row becomes a sibling of it rather
        than content inside it. The row visibly breaks apart while the page
        still contains every word a text assertion looks for, which is how this
        reached a screenshot rather than a failing test the first time.
        """
        for fragment in ("#/chains/context/sql-backed-param", "#/chains/context/search",
                         "#/chains", "#/unit/PTN-INJ-01-PROBE", "#/topic/PTN-INJ-01",
                         "#/case/WSTG-INPV-05", "#/status", "#/search/injection"):
            page = self.open(fragment)
            with self.subTest(fragment=fragment):
                self.assertEqual(page.evaluate("document.querySelectorAll('a a').length"), 0)

    def test_no_page_scrolls_sideways(self):
        """The row that broke apart also overflowed. Checked as geometry rather
        than inferred from the markup."""
        for fragment in ("#/chains/context", "#/chains/context/search+rest-api",
                         "#/chains/context/sql-backed-param"):
            page = self.open(fragment)
            with self.subTest(fragment=fragment):
                self.assertFalse(page.evaluate(
                    "document.documentElement.scrollWidth > "
                    "document.documentElement.clientWidth"
                ))

    def test_it_asks_the_network_for_nothing_at_any_point(self):
        """Not a substring check: every request the browser attempted, across
        every page these tests have opened."""
        self.assertEqual(self.driver.offsite(), [])

    def test_nothing_it_does_raises_an_error_in_the_console(self):
        """A policy that blocks something the page needed reports it here and
        nowhere else. Runs last so it covers what the others did."""
        self.open("#/chains")
        self.open("#/unit/PTN-RES-01-READ")
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
        paragraph about it.

        The inequality this asserted until 0.23.0 -- more control capabilities
        unused than routed -- stopped being true when 24 of them gained the test
        that says what defeating the control permits. What did not change is
        which family the gap is in, so that is what is asserted now: control
        still holds more unused capabilities than any other family, and the
        assertion moves with the catalogue instead of being re-pinned each time
        the figure does.
        """
        control = [c for c in self.map if c["name"] == "control"][0]
        primitive = [c for c in self.map if c["name"] == "primitive"][0]
        worst = max(self.map, key=lambda col: col["tally"]["unused"])
        self.assertEqual(worst["name"], "control")
        self.assertGreater(control["tally"]["unused"], 0)
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

    def test_the_readme_reports_the_same_count_the_page_does(self):
        """The page's copy of this figure was asserted and the README's was not,
        so the two drifted: the page said 15 while the README still said
        fourteen, and the screenshot beside that sentence showed 15.

        Spelled as a numeral in the README for the same reason every other
        figure there is -- a number written as a word is a number the suite
        cannot check, which is exactly how this one went stale.
        """
        back = run_in_node("return H.chainBackEdges(D);", self.data)
        total = sum(e["units"] for e in back)
        readme = " ".join((REPO_ROOT / "README.md").read_text(encoding="utf-8").split())
        self.assertIn(f"the {total} that run the other way", readme)


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
        PTN-INJ-01 is the case: EVADE reads a negative result from one of the
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
            return H.unitRuns(D, D.topics["PTN-INJ-01"]).map(function (r) {
              return {role: r.role, units: r.units};
            });
        """, self.data)
        self.assertEqual([r["role"] for r in result], ["stage", "variant", "stage"])
        self.assertEqual(result[0]["units"], ["PTN-INJ-01-PROBE", "PTN-INJ-01-FPRINT"])
        self.assertEqual(len(result[1]["units"]), 7)
        self.assertEqual(result[2]["units"], ["PTN-INJ-01-EVADE"])

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
            const tid = "PTN-INJ-01";
            const uid = D2.topics[tid].units[0];
            delete D2.units[uid].role;
            return H.unitRuns(D2, D2.topics[tid]).map(function (r) {
              return {role: r.role, n: r.units.length};
            });
        """, self.data)
        self.assertEqual(result[0], {"role": "unroled", "n": 1})
