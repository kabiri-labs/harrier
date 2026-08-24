"""The vocabularies and the pinned standard.

Everything downstream resolves against these, so a defect here would surface
later as many failures with no obvious common cause.
"""

import unittest

from tests.test_identifiers_and_axes import SandboxCase


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
