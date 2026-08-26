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
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from harrier.build import build, catalogue
from tests.support import (
    REPO_ROOT,
    find_browser,
    node_available,
    render_in_browser,
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
        bad = run_in_node("""
            const bad = [];
            ["union", "injection", "WSTG-INPV", "cookie"].forEach(function (term) {
              H.searchAll(D, term).forEach(function (group) {
                group.items.forEach(function (item) {
                  if (!item.href) return;
                  const parts = item.href.replace("#/", "").split("/").map(decodeURIComponent);
                  const store = {unit: D.units, topic: D.topics, case: D.wstg,
                                 capability: D.facts, payloads: D.payloads}[parts[0]];
                  if (store && !H.own(store, parts[1])) bad.push(item.href);
                });
              });
            });
            return bad;
        """, self.data)
        self.assertEqual(bad, [])

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


BROWSER = find_browser()


@unittest.skipUnless(BROWSER, "no browser is installed")
class TheBuiltFileWorksInABrowser(unittest.TestCase):
    """The one test that exercises routing, the policy and the wording at once.

    Everything else here calls functions. This opens the artefact the way a
    tester does -- from disk, over `file://`, where a browser is strictest about
    what an inline block may do -- and reads what the script actually produced.
    If the Content-Security-Policy did not name the script's own hash, nothing
    below renders at all.
    """

    @classmethod
    def setUpClass(cls):
        cls._tmp = TemporaryDirectory(prefix="harrier-browser-")
        cls.page = Path(cls._tmp.name) / "harrier.html"
        build(REPO_ROOT, cls.page)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def dom(self, fragment=""):
        return render_in_browser(BROWSER, self.page, fragment)

    @staticmethod
    def text(dom):
        body = re.search(r"<main[^>]*>(.*)</main>", dom, re.S)
        stripped = re.sub(r"<[^>]+>", " ", body.group(1) if body else "")
        return re.sub(r"\s+", " ", stripped).strip()

    def test_it_opens_on_standards(self):
        dom = self.dom()
        self.assertIn("Standards", self.text(dom))
        self.assertIn("OWASP Web Security Testing Guide", self.text(dom))
        self.assertIn("· Standards</title>", dom)

    def test_the_script_runs_under_its_own_policy(self):
        # An empty <main> means the script never executed, which under a
        # hash-based policy means the hash did not match what was embedded.
        self.assertTrue(self.text(self.dom()))

    def test_the_required_journey_reaches_a_test_and_its_chain(self):
        for fragment, expected in (
            ("#/wstg", "Input Validation Testing"),
            ("#/wstg/INPV", "Testing for SQL Injection"),
            ("#/case/WSTG-INPV-05", "SQL injection"),
            ("#/unit/HRR-INJ-01-UNION", "UNION-based extraction"),
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(expected, self.text(self.dom(fragment)))

    def test_the_test_detail_carries_what_a_tester_performs_it_from(self):
        text = self.text(self.dom("#/unit/HRR-INJ-01-UNION"))
        for section in ("Objective", "Why this is a separate test", "Oracle",
                        "Sequence", "First false positive", "Done when",
                        "Safety boundary", "Payloads", "Tool", "Card",
                        "Local attack chain", "If this test is unsuccessful"):
            self.assertIn(section, text, section)

    def test_the_local_chain_is_drawn_with_its_reasons(self):
        dom = self.dom("#/unit/HRR-INJ-01-PROBE")
        self.assertGreaterEqual(dom.count('class="gnode'), 5)
        self.assertGreaterEqual(dom.count('class="gedge'), 4)
        text = self.text(dom)
        for heading in ("Established by", "Prerequisite", "This test",
                        "Establishes", "Potential continuation"):
            self.assertIn(heading, text, heading)

    def test_a_continuation_states_what_success_here_does_not_supply(self):
        # Chosen because succeeding here supplies one condition of each
        # continuation and not the rest, which is the ordinary case and the one
        # the old model got wrong by calling it "unlocked".
        text = self.text(self.dom("#/unit/HRR-RCN-07-MAP"))
        self.assertIn("Potential continuation", text)
        self.assertIn("Established here", text)
        self.assertIn("Still required", text)

    def test_a_test_whose_result_leads_nowhere_explains_itself(self):
        text = self.text(self.dom("#/unit/HRR-INJ-01-UNION"))
        self.assertIn("reportable outcome", text)
        self.assertIn("does not rule out", text.lower())

    def test_the_general_graph_does_not_open_as_every_node_at_once(self):
        dom = self.dom("#/chains")
        # Seven families, not several hundred units.
        self.assertLessEqual(dom.count('class="gnode'), 12)
        self.assertIn("Reconnaissance", self.text(dom))
        self.assertIn("Impact", self.text(dom))

    def test_a_focused_capability_shows_a_smaller_graph_than_the_catalogue(self):
        text = self.text(self.dom("#/capability/surface.sql.injectable"))
        self.assertIn("Established by", text)
        self.assertIn("Required by", text)

    def test_search_finds_a_payload_and_says_what_it_found(self):
        text = self.text(self.dom("#/search/sqlmap"))
        self.assertIn("Tools", text)

    def test_an_unknown_route_says_so_rather_than_rendering_nothing(self):
        self.assertIn("Not here", self.text(self.dom("#/unit/__proto__")))

    def test_no_rendered_page_claims_to_know_the_reader_s_target(self):
        forbidden = ("unlocked", "available now", "you hold", "your target",
                     "ruled out for", "is possible now")
        for fragment in ("", "#/wstg", "#/case/WSTG-INPV-05",
                         "#/unit/HRR-INJ-01-UNION", "#/unit/HRR-INJ-01-PROBE",
                         "#/chains", "#/capability/access.user"):
            text = self.text(self.dom(fragment)).lower()
            for phrase in forbidden:
                self.assertNotIn(phrase, text, f"{fragment}: {phrase}")

    def test_the_conditional_wording_the_model_depends_on_is_present(self):
        text = self.text(self.dom("#/unit/HRR-INJ-01-PROBE"))
        self.assertIn("may become relevant", text)
        self.assertIn("Potential continuation", text)
