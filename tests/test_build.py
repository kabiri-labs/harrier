"""The published artefact: what it carries, and what it must never carry.

Two properties matter above the rest. The file reaches for nothing -- it is
opened from a laptop on an engagement network, and a stylesheet fetched from a
content delivery network would tell that network's operator which target
somebody is testing and when. And it holds no engagement state: no target, no
result, no claim about what is true of anybody's application. The second is new
in 0.4.0 and is the point of the pivot; see docs/PIVOT.md.
"""

import json
import re
import unittest

import yaml

from harrier import __version__
from harrier.build import (
    catalogue,
    chain_index,
    content_security_policy,
    family_edges,
    family_of,
    render,
    unit_order,
    wstg_groups,
)
from harrier.validate import coverage
from tests.support import REPO_ROOT

def _without_comments(page: str) -> str:
    """The page with block comments removed, so a rule can explain itself.

    Only `/* ... */`: stripping `//` would have to tell a comment from a regular
    expression literal, and the script is full of the latter.
    """
    return re.sub(r"/\*.*?\*/", " ", page, flags=re.S)


EXTERNAL = re.compile(r"""(?:src|href|action|poster|data)\s*=\s*["'](?!#)((?:https?:)?//|https?:)""", re.I)
NETWORK_CALLS = re.compile(
    r"\b(fetch\(|XMLHttpRequest|WebSocket\(|EventSource\(|importScripts|"
    r"navigator\.sendBeacon|import\s*\(|RTCPeerConnection|SharedWorker\(|new\s+Worker\()"
)
#: Anything in a stylesheet that resolves to a request. `url(` covers background
#: images, fonts, cursors and masks in one; `@import` pulls a whole stylesheet.
CSS_FETCH = re.compile(r"(url\s*\(|@import|image-set\s*\()", re.I)


class TheArtefactReachesForNothing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)
        cls.page = render(cls.data)
        cls.style = cls.page.split("<style>", 1)[1].split("</style>", 1)[0]

    def test_no_element_names_an_external_resource(self):
        found = EXTERNAL.search(self.page)
        self.assertIsNone(found, f"the artefact must fetch nothing: {found}")

    def test_no_script_calls_out(self):
        found = NETWORK_CALLS.search(self.page)
        self.assertIsNone(found, f"the artefact must not call out: {found}")

    def test_no_stylesheet_rule_fetches_anything(self):
        # A stylesheet reaches the network through url(), @import and
        # image-set() as readily as a <link> does, and none of them look like a
        # request in a diff.
        found = CSS_FETCH.search(self.style)
        self.assertIsNone(found, f"the stylesheet must fetch nothing: {found}")

    def test_no_element_that_loads_something_is_present(self):
        for tag in ("<link", "<iframe", "<img", "<object", "<embed", "<video",
                    "<audio", "<source", "<track", "<applet", "<portal"):
            self.assertNotIn(tag, self.page.lower(), tag)

    def test_nothing_navigates_the_page_on_a_timer(self):
        # A meta refresh is a navigation the reader did not ask for, and to an
        # absolute URL it is an outbound request.
        self.assertNotIn("http-equiv=\"refresh\"", self.page.lower())
        self.assertNotIn("http-equiv='refresh'", self.page.lower())

    def test_no_form_can_submit_anywhere(self):
        # There is no form at all; the policy forbids one having a destination
        # even if a later change adds it.
        self.assertNotIn("<form", self.page.lower())
        self.assertIn("form-action 'none'", self.page)

    def test_the_only_font_stack_is_one_the_machine_already_has(self):
        self.assertNotIn("@font-face", self.style.lower())


class TheContentSecurityPolicyMatchesWhatTheFileContains(unittest.TestCase):
    """A policy that does not name the blocks in the file is a policy that
    either blocks the page or permits anything. Both fail silently."""

    @classmethod
    def setUpClass(cls):
        cls.page = render(catalogue(REPO_ROOT))
        cls.policy = re.search(
            r'http-equiv="Content-Security-Policy" content="([^"]+)"', cls.page
        ).group(1)

    def test_everything_is_denied_before_anything_is_allowed(self):
        self.assertTrue(self.policy.startswith("default-src 'none'"))

    def test_the_promise_the_file_is_published_on_is_in_the_policy(self):
        self.assertIn("connect-src 'none'", self.policy)

    def test_inline_blocks_are_named_by_hash_rather_than_blanket_permission(self):
        self.assertNotIn("unsafe-inline", self.policy)
        self.assertNotIn("unsafe-eval", self.policy)
        self.assertGreaterEqual(self.policy.count("'sha256-"), 3)

    def test_the_hashes_are_the_hashes_of_the_blocks_actually_embedded(self):
        style = self.page.split("<style>", 1)[1].split("</style>", 1)[0]
        script = self.page.rsplit("<script>", 1)[1].rsplit("</script>", 1)[0]
        blob = self.page.split('type="application/json">', 1)[1].split("</script>", 1)[0]
        rebuilt = content_security_policy(style, script, blob)
        for directive in ("script-src", "style-src"):
            self.assertIn(
                [d for d in rebuilt.split("; ") if d.startswith(directive)][0],
                self.policy,
                f"{directive} does not name what the file contains",
            )

    def test_nothing_may_be_framed_or_reparented(self):
        for directive in ("frame-ancestors 'none'", "base-uri 'none'", "object-src 'none'"):
            self.assertIn(directive, self.policy)

    def test_no_inline_style_attribute_survives_the_policy(self):
        # style-src by hash does not cover style attributes, so one would simply
        # stop applying -- a layout defect nobody would trace back to here.
        self.assertIsNone(re.search(r'\sstyle\s*=\s*["\']', self.page))


class NoEngagementStateRemains(unittest.TestCase):
    """0.3.0 kept a target name, held facts and a result per unit in the
    browser, and claimed reachability from them. All of it is gone, and the
    assertion is on absence because absence is what regresses quietly."""

    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)
        cls.page = render(cls.data)

    def test_nothing_is_stored_in_the_browser(self):
        for token in ("localStorage", "sessionStorage", "indexedDB", "document.cookie"):
            self.assertNotIn(token, self.page, token)

    def test_there_is_no_run_to_import_or_export(self):
        for token in ("harrier.run", "runOut", "runIn", "exportRun", "importRun",
                      "createObjectURL", "FileReader", "download="):
            self.assertNotIn(token, self.page, token)

    def test_no_result_can_be_recorded(self):
        # Named precisely rather than by word: "found" appears in catalogue
        # prose ("a lookup table returns not-found"), and a test that trips on
        # that is a test nobody can keep.
        for token in ("outcomeRow", "OUTCOMES", "data-out=", "results[",
                      ">Found<", ">Clean<", ">Unclear<", "function record("):
            self.assertNotIn(token, self.page, token)

    def test_there_is_no_target_and_no_anchor(self):
        for token in ('id="target"', "data-anchor", "surface anchor", "Start here",
                      "Waiting on something", "Ruled out", "What you hold"):
            self.assertNotIn(token, self.page, token)

    def test_the_catalogue_carries_no_engagement_key(self):
        for key in ("run", "results", "held", "ruled", "target", "anchor", "scope",
                    "always", "order_hint"):
            self.assertNotIn(key, self.data, f"the catalogue must not carry {key}")

    def test_no_unit_carries_a_board_ranking(self):
        for unit in self.data["units"].values():
            self.assertNotIn("order_hint", unit, unit["id"])

    def test_no_wording_claims_knowledge_of_a_target(self):
        """The old model returns as wording before it returns as code.

        Comments are stripped first. The script explains at its head why it
        never says "unlocked", and a rule that forbids the explanation of the
        rule is a rule that gets deleted rather than obeyed. What a reader can
        actually see -- markup and string literals -- is still covered.
        """
        forbidden = (
            "unlocked", "available now", "you hold", "ruled out for",
            "is possible now", "your target", "you completed", "already true of",
        )
        lowered = _without_comments(self.page).lower()
        for phrase in forbidden:
            self.assertNotIn(phrase, lowered, f"target-state wording: {phrase}")

    def test_the_embedded_data_is_the_catalogue_and_nothing_else(self):
        blob = self.page.split('type="application/json">', 1)[1].split("</script>", 1)[0]
        embedded = json.loads(blob.replace("<\\/", "</"))
        self.assertEqual(set(embedded), set(self.data))


class TheCatalogueTravelsWithTheFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)
        cls.page = render(cls.data)
        blob = cls.page.split('type="application/json">', 1)[1].split("</script>", 1)[0]
        cls.embedded = json.loads(blob.replace("<\\/", "</"))

    def test_the_embedded_json_survives_the_script_tag(self):
        # A "</script>" inside a string would end the block early and leave the
        # rest of the catalogue rendering as markup.
        self.assertEqual(len(self.embedded["units"]), len(self.data["units"]))

    def test_every_unit_and_topic_travels_with_it(self):
        counts = coverage(REPO_ROOT)
        self.assertEqual(len(self.embedded["units"]), counts["units"])
        self.assertEqual(len(self.embedded["topics"]), counts["topics"])

    def test_every_card_a_unit_names_is_embedded(self):
        # A card behind a link the reader cannot follow is a card they do not have.
        for unit in self.embedded["units"].values():
            if unit.get("card"):
                self.assertIn(unit["card"], self.embedded["cards"], unit["id"])
            if unit.get("mitigation"):
                self.assertIn(unit["mitigation"], self.embedded["mitigations"], unit["id"])

    def test_every_payload_file_a_unit_names_is_embedded(self):
        ids = set(self.embedded["payloads"])
        for unit in self.embedded["units"].values():
            rel = unit.get("payloads")
            if rel:
                self.assertIn(rel[len("payloads/"):-len(".yaml")], ids, unit["id"])

    def test_payload_whitespace_survives_the_journey(self):
        """Whitespace in a payload is syntax, not formatting.

        A MySQL comment is "-- " and stops being one without the trailing
        space; a numeric-context probe begins with one because it is appended
        to a bare number. The folding that tidies prose would take both, and
        the reader would copy something that does not work.
        """
        significant = 0
        for path in sorted((REPO_ROOT / "payloads").rglob("*.yaml")):
            source = yaml.safe_load(path.read_text(encoding="utf-8"))
            embedded = self.embedded["payloads"][source["id"]]["entries"]
            for original, carried in zip(source["entries"], embedded):
                self.assertEqual(original["payload"], carried["payload"], source["id"])
                if original["payload"] != original["payload"].strip():
                    significant += 1
        self.assertGreater(significant, 0, "no payload exercises the rule any more")

    def test_it_states_the_version_it_was_built_from(self):
        self.assertEqual(self.embedded["version"], __version__)
        self.assertIn(__version__, self.page)

    def test_the_output_is_deterministic(self):
        self.assertEqual(render(catalogue(REPO_ROOT)), self.page)


class CatalogueContentCannotBecomeMarkup(unittest.TestCase):
    """Everything in the file is contributor-written YAML and Markdown. The
    renderer is the only place it becomes HTML, and it escapes on every path."""

    @classmethod
    def setUpClass(cls):
        cls.page = render(catalogue(REPO_ROOT))

    def test_the_data_block_cannot_close_its_own_element(self):
        blob = self.page.split('type="application/json">', 1)[1].split("</script>", 1)[0]
        self.assertNotIn("</script", blob.lower())
        json.loads(blob.replace("<\\/", "</"))

    def test_the_renderer_escapes_the_characters_that_open_an_element(self):
        script = self.page.rsplit("<script>", 1)[1]
        block = script.split("var esc = function", 1)[1].split("};", 1)[0]
        for char in ("&", "<", ">", '"', "'"):
            self.assertIn(char, block, f"esc no longer handles {char}")

    def test_the_markdown_renderer_escapes_before_it_emits(self):
        script = self.page.rsplit("<script>", 1)[1]
        block = script.split("var md = function", 1)[1].split("\n  };", 1)[0]
        self.assertIn("esc(", block)
        # A link becomes its text, never an href: a card could otherwise carry a
        # javascript: URL into the page.
        self.assertIn('.replace(/\\[([^\\]]+)\\]\\(([^)]+)\\)/g, "$1")', block)
        self.assertNotIn("innerHTML", block)


class TheStandardIsIndexedTheWayItIsNavigated(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)
        cls.standard = yaml.safe_load(
            (REPO_ROOT / "standards" / "wstg.yaml").read_text(encoding="utf-8")
        )

    def test_every_pinned_identifier_belongs_to_exactly_one_group(self):
        placed = [wid for group in self.data["groups"] for wid in group["ids"]]
        self.assertEqual(sorted(placed), sorted(self.data["wstg"]))
        self.assertEqual(len(placed), len(set(placed)))

    def test_the_groups_keep_the_order_the_standard_declares(self):
        self.assertEqual(
            [g["code"] for g in self.data["groups"]],
            [g["code"] for g in self.standard["groups"]],
        )

    def test_titles_come_from_the_pin_and_not_from_a_topic(self):
        for entry in self.standard["wstg"]:
            self.assertEqual(self.data["wstg"][entry["id"]], entry["title"], entry["id"])

    def test_every_claim_resolves_to_a_topic_that_travels_with_the_file(self):
        for wid, topics in self.data["claims"].items():
            self.assertIn(wid, self.data["wstg"], wid)
            for tid in topics:
                self.assertIn(tid, self.data["topics"], f"{wid} claims a topic that is not here")

    def test_a_test_case_claimed_by_several_topics_keeps_all_of_them(self):
        multi = {w: t for w, t in self.data["claims"].items() if len(t) > 1}
        self.assertTrue(multi, "no identifier is claimed by more than one topic any more")
        for wid, topics in multi.items():
            self.assertEqual(len(topics), len(set(topics)), f"{wid} lists a topic twice")

    def test_a_topic_claiming_several_test_cases_keeps_all_of_them(self):
        multi = [t for t in self.data["topics"].values() if len(t["wstg"]) > 1]
        self.assertTrue(multi, "no topic claims more than one identifier any more")
        for topic in multi:
            for wid in topic["wstg"]:
                self.assertIn(topic["id"], self.data["claims"][wid], topic["id"])

    def test_every_resolvable_identifier_is_claimed(self):
        unresolved = set(self.data["unresolved"])
        for wid in self.data["wstg"]:
            if wid in unresolved:
                continue
            self.assertTrue(self.data["claims"].get(wid), f"{wid} reaches no Harrier topic")

    def test_an_identifier_the_map_does_not_resolve_is_named_as_that(self):
        # Not a hole: WSTG-INPV-14 is recorded as one the ordered procedure
        # deliberately does not resolve. The page has to say so rather than
        # showing an empty test case.
        self.assertTrue(self.data["unresolved"])
        for wid in self.data["unresolved"]:
            self.assertIn(wid, self.data["wstg"])

    def test_every_unit_is_reachable_from_a_test_case_or_from_extensions(self):
        reachable = set()
        for topic in self.data["topics"].values():
            reachable.update(topic["units"])
        self.assertEqual(reachable, set(self.data["units"]))

    def test_content_with_no_test_case_is_listed_under_extensions(self):
        for tid, topic in self.data["topics"].items():
            if not topic["wstg"]:
                self.assertIn(tid, self.data["extensions"], tid)
        for tid in self.data["extensions"]:
            self.assertFalse(self.data["topics"][tid]["wstg"], tid)

    def test_units_appear_in_the_order_their_topic_declares(self):
        checked = 0
        for topic in self.data["topics"].values():
            declared = [u for u in (topic.get("order") or []) if u in self.data["units"]]
            if not declared:
                continue
            self.assertEqual(topic["units"][: len(declared)], declared, topic["id"])
            checked += 1
        self.assertGreater(checked, 0, "no topic declares an order any more")


class UnitOrderKeepsWhatTheTopicDidNotDeclare(unittest.TestCase):
    """A unit missing from a topic's `order` is a gap in the topic file. It must
    not become a unit nobody can reach."""

    def test_declared_units_come_first_in_the_declared_order(self):
        units = {"HRR-X-01-B": {"topic": "HRR-X-01"}, "HRR-X-01-A": {"topic": "HRR-X-01"}}
        topic = {"id": "HRR-X-01", "order": ["HRR-X-01-B", "HRR-X-01-A"]}
        self.assertEqual(unit_order(topic, units), ["HRR-X-01-B", "HRR-X-01-A"])

    def test_an_undeclared_unit_follows_rather_than_disappearing(self):
        units = {
            "HRR-X-01-A": {"topic": "HRR-X-01"},
            "HRR-X-01-Z": {"topic": "HRR-X-01"},
        }
        topic = {"id": "HRR-X-01", "order": ["HRR-X-01-A"]}
        self.assertEqual(unit_order(topic, units), ["HRR-X-01-A", "HRR-X-01-Z"])

    def test_an_order_naming_a_unit_that_is_not_here_does_not_invent_one(self):
        units = {"HRR-X-01-A": {"topic": "HRR-X-01"}}
        topic = {"id": "HRR-X-01", "order": ["HRR-X-01-A", "HRR-X-01-GONE"]}
        self.assertEqual(unit_order(topic, units), ["HRR-X-01-A"])

    def test_another_topics_units_are_not_absorbed(self):
        units = {"HRR-X-01-A": {"topic": "HRR-X-01"}, "HRR-Y-01-A": {"topic": "HRR-Y-01"}}
        self.assertEqual(unit_order({"id": "HRR-X-01"}, units), ["HRR-X-01-A"])


class TheGroupIndexIsReadRatherThanDeclaredTwice(unittest.TestCase):
    def test_membership_comes_from_the_identifier(self):
        standard = {
            "groups": [{"code": "INPV", "name": "Input Validation Testing"}],
            "wstg": [{"id": "WSTG-INPV-02"}, {"id": "WSTG-INPV-01"}],
        }
        self.assertEqual(
            wstg_groups(standard),
            [{"code": "INPV", "name": "Input Validation Testing",
              "ids": ["WSTG-INPV-01", "WSTG-INPV-02"]}],
        )

    def test_a_declared_group_with_no_identifiers_comes_back_empty_not_absent(self):
        standard = {"groups": [{"code": "ZZZZ", "name": "Nothing"}], "wstg": []}
        self.assertEqual(wstg_groups(standard)[0]["ids"], [])


class TheLocalChainIsDerivedAndBoundedToTheReason(unittest.TestCase):
    """Every edge carries the capability it travels through. Projecting the
    graph down to unit-to-unit edges would lose the only part of it a reader can
    act on."""

    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)
        cls.chain = cls.data["chain"]

    def test_every_unit_has_a_chain_entry_even_when_it_is_empty(self):
        self.assertEqual(set(self.chain), set(self.data["units"]))

    def test_an_incoming_requirement_names_a_capability_that_exists(self):
        for uid, edge in self.chain.items():
            for link in edge["in"]:
                self.assertIn(link["fact"], self.data["facts"], uid)
                self.assertIn(link["kind"], ("all_of", "any_of", "motivated_by"), uid)

    def test_incoming_requirements_are_exactly_what_the_unit_declares(self):
        for uid, unit in self.data["units"].items():
            requires = unit.get("requires") or {}
            expected = (
                [(f, "all_of") for f in requires.get("all_of") or []]
                + [(f, "any_of") for f in requires.get("any_of") or []]
                + [(f, "motivated_by") for f in unit.get("motivated_by") or []]
            )
            actual = [(link["fact"], link["kind"]) for link in self.chain[uid]["in"]]
            self.assertEqual(actual, expected, uid)

    def test_a_motivation_stays_distinct_from_a_requirement(self):
        soft = [
            (uid, link["fact"])
            for uid, edge in self.chain.items()
            for link in edge["in"]
            if link["kind"] == "motivated_by"
        ]
        self.assertTrue(soft, "nothing is motivated by anything any more")
        for uid, fact in soft:
            requires = self.data["units"][uid].get("requires") or {}
            hard = set(requires.get("all_of") or []) | set(requires.get("any_of") or [])
            self.assertNotIn(fact, hard, f"{uid} lists {fact} as both a gate and a hint")

    def test_every_producer_shown_for_a_capability_actually_yields_it(self):
        for fact, producers in self.data["producers"].items():
            self.assertIn(fact, self.data["facts"])
            for uid in producers:
                self.assertIn(fact, self.data["units"][uid].get("yields") or [], uid)

    def test_every_unit_that_yields_something_is_listed_against_it(self):
        for uid, unit in self.data["units"].items():
            for fact in unit.get("yields") or []:
                self.assertIn(uid, self.data["producers"][fact], uid)

    def test_a_continuation_actually_consumes_what_this_unit_establishes(self):
        for uid, edge in self.chain.items():
            established = set(edge["yields"])
            for link in edge["out"]:
                consumer = self.data["units"][link["unit"]]
                requires = consumer.get("requires") or {}
                hard = set(requires.get("all_of") or []) | set(requires.get("any_of") or [])
                soft = set(consumer.get("motivated_by") or [])
                self.assertTrue(set(link["via"]) <= hard & established, f"{uid} -> {link['unit']}")
                self.assertTrue(set(link.get("hint") or []) <= soft & established,
                                f"{uid} -> {link['unit']}")
                self.assertTrue(link["via"] or link.get("hint"), f"{uid} -> {link['unit']}")

    def test_a_continuation_never_points_back_at_itself(self):
        for uid, edge in self.chain.items():
            for link in edge["out"]:
                self.assertNotEqual(link["unit"], uid)

    def test_the_further_conditions_are_the_ones_success_here_does_not_supply(self):
        given = set(self.data["given"])
        for uid, edge in self.chain.items():
            have = set(edge["yields"]) | given
            for link in edge["out"]:
                consumer = self.data["units"][link["unit"]]
                requires = consumer.get("requires") or {}
                expected_all = [f for f in requires.get("all_of") or [] if f not in have]
                any_of = list(requires.get("any_of") or [])
                expected_any = [] if (not any_of or set(any_of) & have) else any_of
                self.assertEqual(link["also"].get("all_of", []), expected_all,
                                 f"{uid} -> {link['unit']}")
                self.assertEqual(link["also"].get("any_of", []), expected_any,
                                 f"{uid} -> {link['unit']}")

    def test_further_conditions_are_actually_exercised_by_the_catalogue(self):
        """If nothing carried them the rule above would be about nothing."""
        with_also = [
            link for edge in self.chain.values() for link in edge["out"] if link["also"]
        ]
        self.assertGreater(len(with_also), 50, "additional conditions have stopped appearing")

    def test_conditions_are_not_sorted_out_of_the_initial_view(self):
        """Ranking continuations by how little each still needs reads as helpful
        and is not: it puts every conditional continuation below the three the
        reader sees, and the conditions are the honest half."""
        visible = [
            uid
            for uid, edge in self.chain.items()
            if any(link["also"] for link in edge["out"][:3])
        ]
        self.assertGreater(len(visible), 10,
                           "further conditions have been sorted below the initial view")

    def test_a_capability_the_engagement_may_grant_is_not_a_root(self):
        # `granted` is an engagement's gift and usually is not given. It must
        # never join `given`, which is what the chain treats as always holding.
        granted = set(self.data["granted"])
        self.assertTrue(granted)
        self.assertFalse(granted & set(self.data["given"]))

    def test_a_granted_capability_is_still_listed_as_a_further_condition(self):
        # Folding it into what success supplies would hide a real condition
        # behind an assumption about somebody's engagement.
        units = {
            "HRR-A-01-P": {"id": "HRR-A-01-P", "yields": ["surface.x"]},
            "HRR-A-01-U": {
                "id": "HRR-A-01-U",
                "requires": {"all_of": ["surface.x", "access.host"]},
            },
        }
        index = chain_index(units, given={"recon.target.reachable"})
        self.assertEqual(
            index["HRR-A-01-P"]["out"][0]["also"], {"all_of": ["access.host"]}
        )

    def test_an_impact_is_terminal(self):
        for fact in self.data["impacts"]:
            self.assertEqual(family_of(fact), "impact")
            self.assertNotIn(fact, self.data["requiredBy"], f"{fact} is required by something")
        for edge in self.chain.values():
            for item in edge["terminal"]:
                self.assertIn(item["why"], ("impact", "unconsumed"))
                if item["why"] == "impact":
                    self.assertEqual(family_of(item["fact"]), "impact")

    def test_a_unit_whose_result_nothing_consumes_is_marked_rather_than_left_blank(self):
        blank = 0
        for uid, edge in self.chain.items():
            if edge["yields"] and not edge["out"]:
                self.assertTrue(edge["terminal"], f"{uid} yields something, leads nowhere, says nothing")
                blank += 1
        self.assertGreater(blank, 0, "no unit exercises the terminal explanation")

    def test_a_unit_with_several_routes_in_or_out_is_not_flattened_to_a_line(self):
        fan_in = [u for u, e in self.chain.items() if len(e["in"]) > 1]
        fan_out = [u for u, e in self.chain.items() if len(e["out"]) > 1]
        self.assertTrue(fan_in and fan_out)
        many_producers = [f for f, p in self.data["producers"].items() if len(p) > 1]
        self.assertTrue(many_producers, "no capability has more than one route to it")

    def test_the_index_is_derived_and_not_a_stored_edge_list(self):
        units = {
            "HRR-A-01-P": {"id": "HRR-A-01-P", "yields": ["surface.x"]},
            "HRR-A-01-U": {
                "id": "HRR-A-01-U",
                "requires": {"all_of": ["surface.x", "access.host"]},
            },
            "HRR-A-01-M": {"id": "HRR-A-01-M", "motivated_by": ["surface.x"]},
        }
        index = chain_index(units, given=set())
        forward = index["HRR-A-01-P"]["out"]
        self.assertEqual([e["unit"] for e in forward], ["HRR-A-01-U", "HRR-A-01-M"])
        self.assertEqual(index["HRR-A-01-U"]["out"], [])
        self.assertEqual(forward[0]["kind"], "requires")
        self.assertEqual(forward[0]["also"], {"all_of": ["access.host"]})
        self.assertEqual(forward[1]["kind"], "motivated_by")
        self.assertEqual(forward[1]["hint"], ["surface.x"])

    def test_a_given_capability_is_not_listed_as_a_further_condition(self):
        units = {
            "HRR-A-01-P": {"id": "HRR-A-01-P", "yields": ["surface.x"]},
            "HRR-A-01-U": {
                "id": "HRR-A-01-U",
                "requires": {"all_of": ["surface.x"], "any_of": ["access.anon"]},
            },
        }
        index = chain_index(units, given={"access.anon"})
        self.assertEqual(index["HRR-A-01-P"]["out"][0]["also"], {})


class TheFamilyViewSummarisesTheWholeGraph(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)

    def test_every_capability_belongs_to_exactly_one_family(self):
        placed = [f for family in self.data["families"] for f in family["facts"]]
        self.assertEqual(sorted(placed), sorted(self.data["facts"]))
        self.assertEqual(len(placed), len(set(placed)))

    def test_the_families_are_the_seven_the_vocabulary_fixes(self):
        self.assertEqual(
            [f["name"] for f in self.data["families"]],
            ["recon", "surface", "access", "artifact", "primitive", "control", "impact"],
        )

    def test_a_family_edge_counts_units_that_really_span_it(self):
        counted = {}
        for unit in self.data["units"].values():
            requires = unit.get("requires") or {}
            sources = {family_of(f) for f in (requires.get("all_of") or []) + (requires.get("any_of") or [])}
            targets = {family_of(f) for f in unit.get("yields") or []}
            for source in sources:
                for target in targets:
                    counted[(source, target)] = counted.get((source, target), 0) + 1
        self.assertEqual(
            {(e["from"], e["to"]): e["units"] for e in self.data["familyEdges"]}, counted
        )

    def test_a_family_edge_names_only_families_that_exist(self):
        names = {f["name"] for f in self.data["families"]}
        for edge in self.data["familyEdges"]:
            self.assertIn(edge["from"], names)
            self.assertIn(edge["to"], names)

    def test_family_edges_are_derived_from_the_units_and_nothing_else(self):
        units = {
            "HRR-A-01-U": {
                "id": "HRR-A-01-U",
                "requires": {"all_of": ["recon.a"]},
                "yields": ["impact.b"],
            }
        }
        self.assertEqual(
            family_edges(units), [{"from": "recon", "to": "impact", "units": 1}]
        )


class TheIndexesNameOnlyThingsThatTravelWithTheFile(unittest.TestCase):
    """Every drill-down in the page walks these. One dangling identifier is a
    dead end the reader meets and cannot explain."""

    @classmethod
    def setUpClass(cls):
        cls.data = catalogue(REPO_ROOT)

    def test_every_fact_index_names_known_facts_and_known_units(self):
        for name in ("producers", "requiredBy", "motivates"):
            for fact, units in self.data[name].items():
                self.assertIn(fact, self.data["facts"], f"{name}: {fact}")
                for uid in units:
                    self.assertIn(uid, self.data["units"], f"{name}: {uid}")

    def test_every_chain_edge_names_a_unit_that_is_here(self):
        for uid, edge in self.data["chain"].items():
            self.assertIn(uid, self.data["units"])
            for link in edge["out"]:
                self.assertIn(link["unit"], self.data["units"])

    def test_every_unit_names_a_topic_that_is_here(self):
        for uid, unit in self.data["units"].items():
            self.assertIn(unit["topic"], self.data["topics"], uid)

    def test_every_unit_names_test_cases_that_are_pinned(self):
        for uid, unit in self.data["units"].items():
            for wid in unit["wstg"]:
                self.assertIn(wid, self.data["wstg"], uid)

    def test_a_topic_lists_only_its_own_units(self):
        for tid, topic in self.data["topics"].items():
            for uid in topic["units"]:
                self.assertEqual(self.data["units"][uid]["topic"], tid)

    def test_every_axis_a_unit_slug_can_name_travels_with_it(self):
        self.assertIn("phase", self.data["axes"])
        named = 0
        for uid, unit in self.data["units"].items():
            slug = uid.split("-")[3]
            topic = self.data["topics"][unit["topic"]]
            candidates = [topic.get("axis")] + list(self.data["axes"])
            if any(
                slug in (self.data["axes"].get(a) or {}).get("slugs", {})
                for a in candidates if a
            ):
                named += 1
        self.assertEqual(named, len(self.data["units"]),
                         "a unit slug resolves to no axis, so it can state no reason")


class TheCountsAreDerivedRatherThanWrittenDown(unittest.TestCase):
    def test_the_page_reports_the_validator_counts(self):
        data = catalogue(REPO_ROOT)
        self.assertEqual(data["counts"], coverage(REPO_ROOT))

    def test_the_counts_agree_with_what_actually_travels(self):
        data = catalogue(REPO_ROOT)
        self.assertEqual(data["counts"]["units"], len(data["units"]))
        self.assertEqual(data["counts"]["topics"], len(data["topics"]))
        self.assertEqual(data["counts"]["wstg_pinned"], len(data["wstg"]))
