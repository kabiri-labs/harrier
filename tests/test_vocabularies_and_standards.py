"""The vocabularies and the pinned standard.

Everything downstream resolves against these, so a defect here would surface
later as many failures with no obvious common cause.
"""

import unittest

from pentest_navgrid.validate import validate
from tests.support import messages
from tests.test_identifiers_and_axes import SandboxCase


class FactIdentifiersAreUnique(SandboxCase):
    """Two entries for one fact means one meaning is silently discarded, and a
    graph node whose meaning is uncertain is worse than a missing one."""

    def test_a_duplicate_fact_id_is_rejected(self):
        def duplicate(vocab):
            first = dict(vocab["facts"][0])
            first["label"] = "The same id, a different meaning"
            vocab["facts"].append(first)

        self.box.edit("vocab/facts.yaml", duplicate)
        self.assertRejected("duplicate fact")


class TheDomainMapMustMatchThePin(SandboxCase):
    def test_a_pinned_identifier_left_unmapped_is_rejected(self):
        def drop_one(data):
            data["map"] = [e for e in data["map"] if e["id"] != "WSTG-INPV-05"]
        self.box.edit("standards/wstg-map.yaml", drop_one)
        self.assertRejected("WSTG-INPV-05 is pinned but unmapped")

    def test_a_mapped_identifier_absent_from_the_pin_is_rejected(self):
        def drop_from_pin(data):
            data["wstg"] = [e for e in data["wstg"] if e["id"] != "WSTG-INPV-05"]
        self.box.edit("standards/wstg.yaml", drop_from_pin)
        self.assertRejected("WSTG-INPV-05 is not in the pinned index")

    def test_a_duplicate_map_entry_is_rejected(self):
        def duplicate(data):
            data["map"].append(dict(data["map"][0]))
        self.box.edit("standards/wstg-map.yaml", duplicate)
        self.assertRejected("duplicate entry for")

    def test_a_map_entry_naming_an_undefined_domain_is_rejected(self):
        def retarget(data):
            data["map"][0]["domains"] = ["ZZZ"]
        self.box.edit("standards/wstg-map.yaml", retarget)
        self.assertRejected("names undefined domain ZZZ")

    def test_a_title_that_has_drifted_from_the_pin_is_rejected(self):
        def retitle(data):
            data["map"][0]["title"] = "Something Else Entirely"
        self.box.edit("standards/wstg-map.yaml", retitle)
        self.assertRejected("title has drifted from the pinned index")

    def test_a_numbered_rule_resolving_to_two_domains_is_rejected(self):
        # The procedure stops at the first rule that fires, so a numbered rule
        # resolves to exactly one domain by construction. Two means rule 0.
        def widen(data):
            entry = next(e for e in data["map"] if e["rule"] > 0)
            entry["domains"] = ["INJ", "CLT"]
        self.box.edit("standards/wstg-map.yaml", widen)
        self.assertRejected("schema (wstg-map)")

    def test_rule_zero_without_a_reason_is_rejected(self):
        def strip_note(data):
            entry = next(e for e in data["map"] if e["rule"] == 0)
            entry.pop("note")
        self.box.edit("standards/wstg-map.yaml", strip_note)
        self.assertRejected("schema (wstg-map)")


class ThePinMustStayAuditable(SandboxCase):
    def test_a_branch_name_cannot_stand_in_for_a_commit(self):
        def unpin(data):
            data["source_commit"] = "master"
        self.box.edit("standards/wstg.yaml", unpin)
        self.assertRejected("source_commit")

    def test_a_missing_content_hash_is_rejected(self):
        def unpin(data):
            data.pop("source_sha256")
        self.box.edit("standards/wstg.yaml", unpin)
        self.assertRejected("'source_sha256' is a required property")

    def test_an_unverified_identifier_is_reported(self):
        def unverify(data):
            data["wstg"][0]["verified"] = False
        self.box.edit("standards/wstg.yaml", unverify)
        self.assertRejected("marked unverified")


class VocabulariesAreInternallyConsistent(SandboxCase):
    def test_a_duplicate_domain_code_is_rejected(self):
        def duplicate(data):
            data["domains"].append(dict(data["domains"][0]))
        self.box.edit("vocab/domains.yaml", duplicate)
        self.assertRejected("duplicate domain code")

    def test_a_surface_emitting_an_unknown_tag_is_rejected(self):
        def dangle(data):
            data["surfaces"][0]["emits"] = ["no-such-surface"]
        self.box.edit("vocab/surfaces.yaml", dangle)
        self.assertRejected("emits unknown tag no-such-surface")

    def test_a_surface_emitting_itself_is_rejected(self):
        def loop(data):
            data["surfaces"][0]["emits"] = [data["surfaces"][0]["tag"]]
        self.box.edit("vocab/surfaces.yaml", loop)
        self.assertRejected("emits itself")

    def test_removing_the_universal_axis_is_rejected(self):
        # Without one, recurring steps such as PROBE have nowhere to live and
        # every topic would have to invent its own name for them.
        def demote(data):
            for axis in data["axes"]:
                axis.pop("universal", None)
        self.box.edit("vocab/axes.yaml", demote)
        self.assertRejected("no axis is marked universal")

    def test_a_duplicate_dimension_value_is_rejected(self):
        def duplicate(data):
            data["dimensions"]["engine"]["values"].append(
                dict(data["dimensions"]["engine"]["values"][0])
            )
        self.box.edit("vocab/dimensions.yaml", duplicate)
        self.assertRejected("duplicate value in dimension engine")


class SearchAliasesMustEarnTheirPlace(SandboxCase):
    """An alias exists because catalogue titles name mechanisms and testers type
    vulnerability classes. Both halves of that can move underneath it, and
    neither failure announces itself: an alias whose expansion has been reworded
    away simply answers nothing, silently, which is the failure the file was
    added to fix.

    So both directions are checked, and both are checked against the catalogue
    rather than against the file's own consistency.
    """

    def test_an_expansion_nothing_carries_is_rejected(self):
        def dangle(data):
            data["aliases"][0]["expands_to"] = ["a phrase this catalogue never uses"]
        self.box.edit("vocab/search_aliases.yaml", dangle)
        self.assertRejected("which nothing in the catalogue carries")

    def test_an_alias_reaching_nothing_new_is_rejected(self):
        # The day a topic is renamed to carry the shorthand itself, the alias
        # for it stops adding anything -- and would go on telling the reader
        # their term had been expanded when the direct search had already
        # answered.
        def redundant(data):
            data["aliases"].append(
                {"term": "traversal", "expands_to": ["path traversal and file inclusion"]}
            )
        self.box.edit("vocab/search_aliases.yaml", redundant)
        self.assertRejected("reaches nothing the term itself does not already reach")

    def test_an_expansion_spanning_two_fields_is_rejected(self):
        """The gate mirrors the artefact, and the artefact scores each field on
        its own.

        The phrase is derived here rather than written down, so this keeps
        testing the mechanism after the unit it is built from is reworded: the
        last word of a title followed by the first of the objective under it is
        in neither field, so a reader searching it gets nothing -- and a gate
        that joined the fields into one blob would have accepted an alias
        expanding to it.
        """
        unit = self.box.read("knowledge/cry/PTN-CRY-05-WRITE.unit.yaml")
        phrase = (unit["title"].split()[-1] + " " + unit["objective"].split()[0]).lower()
        self.assertNotIn(phrase, unit["title"].lower())
        self.assertNotIn(phrase, unit["objective"].lower())

        def spanning(data):
            data["aliases"][0]["expands_to"] = [phrase]

        self.box.edit("vocab/search_aliases.yaml", spanning)
        self.assertRejected("which nothing in the catalogue carries")

    def test_a_duplicate_term_is_rejected(self):
        def duplicate(data):
            data["aliases"].append(dict(data["aliases"][0]))
        self.box.edit("vocab/search_aliases.yaml", duplicate)
        self.assertRejected("duplicate alias term")

    def test_an_alias_expanding_to_itself_is_rejected(self):
        def loop(data):
            data["aliases"][0]["expands_to"] = [data["aliases"][0]["term"]]
        self.box.edit("vocab/search_aliases.yaml", loop)
        self.assertRejected("expands to itself")

    def test_an_alias_expanding_to_another_alias_is_rejected(self):
        # Search takes one hop. A second expansion chained behind the first
        # would never run, so the file would read as saying something it does
        # not do.
        def chain(data):
            data["aliases"][0]["expands_to"] = [data["aliases"][1]["term"]]
        self.box.edit("vocab/search_aliases.yaml", chain)
        self.assertRejected("which is itself an alias term")

    def test_the_shorthand_this_field_uses_is_not_left_out(self):
        """The file's own reason for existing, pinned so it cannot quietly
        shrink to whatever still happens to validate."""
        aliases = {a["term"] for a in self.box.read("vocab/search_aliases.yaml")["aliases"]}
        for term in ("idor", "bola", "lfi", "ssti", "ssrf", "xxe", "sqli", "csrf", "jwt"):
            with self.subTest(term=term):
                self.assertIn(term, aliases)


class PayloadsStayCopyAndRun(SandboxCase):
    def test_an_undeclared_placeholder_is_rejected(self):
        def inject(data):
            data["entries"][0]["payload"] = "' ORDER BY {{UNDECLARED}}--"
        self.box.edit("payloads/sqli/union.yaml", inject)
        self.assertRejected("undeclared variable {{UNDECLARED}}")

    def test_a_declared_but_unused_variable_is_rejected(self):
        # This is what a renamed placeholder leaves behind, and it reads as if
        # something still uses it.
        def orphan(data):
            data["variables"].append("ORPHAN")
        self.box.edit("payloads/sqli/union.yaml", orphan)
        self.assertRejected("variable ORPHAN is declared but never used")

    def test_a_selector_on_an_unknown_dimension_is_rejected(self):
        def rename(data):
            entry = next(e for e in data["entries"] if "engine" in e)
            entry["dbms"] = entry.pop("engine")
        self.box.edit("payloads/sqli/union.yaml", rename)
        self.assertRejected("selects on unknown dimension dbms")

    def test_a_value_outside_the_dimension_is_rejected(self):
        def mistype(data):
            entry = next(e for e in data["entries"] if "engine" in e)
            entry["engine"] = ["postgres"]
        self.box.edit("payloads/sqli/union.yaml", mistype)
        self.assertRejected("dimension engine has no value postgres")

    def test_an_undated_payload_file_is_rejected(self):
        def undate(data):
            data.pop("reviewed")
        self.box.edit("payloads/sqli/union.yaml", undate)
        self.assertRejected("'reviewed' is a required property")


class ToolRationaleMustDescribeTheCommand(SandboxCase):
    def test_a_flag_explained_but_not_used_is_rejected(self):
        def orphan(data):
            data[2]["invocations"][0]["flags"]["--tamper=space2comment"] = (
                "Left behind after the invocation was edited; describes nothing here."
            )
        self.box.edit("toolbox/registry.yaml", orphan)
        self.assertRejected("is explained but not used in the command")

    def test_a_described_technique_is_not_mistaken_for_a_flag(self):
        # Interactive tools explain a technique rather than a command-line token.
        def describe(data):
            data[0]["invocations"][0]["flags"]["send twice in a row"] = (
                "Establishes whether the endpoint answers deterministically at all."
            )
        self.box.edit("toolbox/registry.yaml", describe)
        self.assertAccepted()

    def test_a_duplicate_tool_id_is_rejected(self):
        def duplicate(data):
            data.append(dict(data[0]))
        self.box.edit("toolbox/registry.yaml", duplicate)
        self.assertRejected("duplicate tool id")


if __name__ == "__main__":
    unittest.main()


class TheAsvsPinStaysAuditable(SandboxCase):
    """ASVS is CC BY-SA, so what is absent from the pin matters as much as what
    is present."""

    def test_no_requirement_text_is_reproduced(self):
        # Requirement text would force share-alike onto this repository. The
        # schema has no field for it; this asserts none arrived anyway.
        raw = self.box.path("standards/asvs.yaml").read_text(encoding="utf-8")
        body = raw.split("asvs:", 1)[1]
        self.assertNotIn(
            "Verify that",
            body,
            "requirement text must never be reproduced -- identifiers and "
            "structural names only",
        )

    def test_a_branch_cannot_stand_in_for_the_release_tag(self):
        def unpin(data):
            data["source_commit"] = "v5.0.0"
        self.box.edit("standards/asvs.yaml", unpin)
        self.assertRejected("source_commit")

    def test_the_licence_note_is_required(self):
        def strip(data):
            data.pop("licence")
        self.box.edit("standards/asvs.yaml", strip)
        self.assertRejected("'licence' is a required property")

    def test_an_unschemad_standards_file_is_reported(self):
        self.box.path("standards/capec.yaml").write_text("version: 1\ncapec: []\n")
        self.assertRejected("no schema is registered for this standard")


class TheCwePinResolvesReferences(SandboxCase):
    def test_a_real_weakness_is_accepted(self):
        self.box.add_topic(refs={"cwe": [89]})
        self.assertAccepted()

    def test_an_identifier_absent_from_the_catalogue_is_rejected(self):
        self.box.add_topic(refs={"cwe": [999999]})
        self.assertRejected("CWE-999999 is not in the pinned CWE catalogue")

    def test_citing_a_view_is_rejected_with_the_reason(self):
        # CWE-699 is a real identifier and not a weakness, so "not found" would
        # be a misleading thing to say about it.
        self.box.add_topic(refs={"cwe": [699]})
        self.assertRejected("CWE-699 is a view")

    def test_citing_a_category_is_rejected_with_the_reason(self):
        def find_category(data):
            return next(e["id"] for e in data["cwe"] if e["kind"] == "category")
        category = find_category(self.box.read("standards/cwe.yaml"))
        self.box.add_topic(refs={"cwe": [category]})
        self.assertRejected(f"CWE-{category} is a category")

    def test_a_deprecated_weakness_is_rejected(self):
        data = self.box.read("standards/cwe.yaml")
        deprecated = next(
            e["id"] for e in data["cwe"]
            if e["kind"] == "weakness" and e["status"] == "Deprecated"
        )
        self.box.add_topic(refs={"cwe": [deprecated]})
        self.assertRejected(f"CWE-{deprecated} is deprecated")


class TheCwePinCarriesItsLicenceCondition(SandboxCase):
    """MITRE grants use on the condition that a copy reproduces the copyright
    designation and the licence. Dropping either puts this repository outside
    the grant, so both are required rather than decorative."""

    def test_the_copyright_designation_is_required(self):
        def strip(data):
            data.pop("copyright")
        self.box.edit("standards/cwe.yaml", strip)
        self.assertRejected("'copyright' is a required property")

    def test_a_copyright_not_naming_mitre_is_rejected(self):
        def rewrite(data):
            data["copyright"] = "Copyright (c) 2026, Somebody Else"
        self.box.edit("standards/cwe.yaml", rewrite)
        self.assertRejected("schema (cwe)")

    def test_the_moving_latest_url_cannot_be_the_pin(self):
        # cwec_latest moves, so it names a moving target rather than the evidence.
        def unpin(data):
            data["source_url"] = "https://cwe.mitre.org/data/xml/cwec_latest.xml.zip"
        self.box.edit("standards/cwe.yaml", unpin)
        self.assertRejected("source_url")

    def test_the_notice_reproduces_the_mitre_attribution(self):
        notice = (self.box.root / "NOTICE").read_text(encoding="utf-8")
        pin = self.box.read("standards/cwe.yaml")
        self.assertIn(
            pin["copyright"],
            notice,
            "the CWE grant is conditional on reproducing MITRE's copyright "
            "designation; NOTICE is where this repository does that",
        )


class EveryResolvedIdentifierIsClaimedByATopic(SandboxCase):
    """The gate that defines phase 2 as finished."""

    def test_a_resolved_identifier_with_no_topic_is_rejected(self):
        # Deleting the only topic claiming an identifier leaves it mapped to a
        # domain and covered by nothing, which is a coverage hole rather than a
        # decision.
        self.box.path("knowledge/inj/PTN-INJ-01.topic.yaml").unlink()
        self.assertRejected("WSTG-INPV-05 is mapped to INJ but no INJ topic claims it")

    def test_a_domain_claim_cannot_be_masked_by_another_domain(self):
        # WSTG-INFO-01 resolves to both RCN and ERR: two pieces of work. Checking
        # identifier presence alone would let the ERR topic report the RCN half
        # as covered, which reports full coverage over a hole.
        self.box.path("knowledge/rcn/PTN-RCN-08.topic.yaml").unlink()
        self.assertRejected("WSTG-INFO-01 is mapped to RCN but no RCN topic claims it")

    def test_the_surviving_domain_is_not_also_reported(self):
        self.box.path("knowledge/rcn/PTN-RCN-08.topic.yaml").unlink()
        problems = validate(self.box.root)
        self.assertNotIn("mapped to ERR but no ERR topic", messages(problems))

    def test_claiming_an_unresolvable_identifier_is_rejected(self):
        # WSTG-INPV-14 is pinned and resolves to no domain. Claiming it would
        # count coverage the taxonomy does not have, and would let the numerator
        # exceed its own denominator.
        self.box.add_topic(refs={"wstg": ["WSTG-INPV-05", "WSTG-INPV-14"]})
        self.assertRejected("which the map resolves to no domain")

    def test_the_coverage_numerator_never_exceeds_its_denominator(self):
        from pentest_navgrid.validate import coverage

        self.box.add_topic(refs={"wstg": ["WSTG-INPV-05", "WSTG-INPV-14"]})
        counts = coverage(self.box.root)
        self.assertLessEqual(counts["wstg_covered"], counts["wstg_coverable"])

    def test_an_unresolved_identifier_needs_no_topic(self):
        # WSTG-INPV-14 is rule 0 with no domains: it describes second-order
        # delivery, which this model expresses as a dimension. Requiring a topic
        # for it would force a topic that should not exist.
        problems = validate(self.box.root)
        self.assertNotIn("WSTG-INPV-14", messages(problems))
