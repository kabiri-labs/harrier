"""The content rules: oracle, kind, outline status, and the vague-language gates.

These are the rules a reviewer would have to apply by reading, which is exactly
why they are applied mechanically instead.
"""

import json
import re
import unittest

import yaml

from harrier.validate import validate
from tests.support import REPO_ROOT, Sandbox, messages
from tests.test_identifiers_and_axes import SandboxCase


class KindDecidesWhetherAnOracleIsAllowed(SandboxCase):
    def test_a_test_unit_without_an_oracle_is_rejected(self):
        self.box.add_topic()
        unit = {
            "id": "HRR-AUT-01-UNION", "topic": "HRR-AUT-01", "role": "variant",
            "title": "UNION-based extraction",
            "objective": "Determine whether a UNION arm can be appended to the query.",
            "done_when": "Column count resolved and one computed value extracted, or the reason recorded.",
        }
        self.box.write("knowledge/aut/HRR-AUT-01-UNION.unit.yaml", unit)
        self.assertRejected("'oracle' is a required property")

    def test_a_recon_unit_with_an_oracle_is_rejected(self):
        # Forbidding the field rather than merely allowing its absence is the
        # point: while it was optional, units wrote "not applicable" into it.
        self.box.add_topic()
        self.box.add_unit(id="HRR-AUT-01-FPRINT", kind="recon")
        self.assertRejected("HRR-AUT-01-FPRINT.unit.yaml: schema (unit)")

    def test_a_recon_unit_without_an_oracle_is_accepted(self):
        self.box.add_topic(order=["HRR-AUT-01-FPRINT", "HRR-AUT-01-UNION"])
        self.box.add_unit(id="HRR-AUT-01-UNION")
        unit = {
            "id": "HRR-AUT-01-FPRINT", "topic": "HRR-AUT-01", "kind": "recon",
            "role": "stage", "status": "sketched",
            "title": "Database engine fingerprint",
            "objective": "Establish which database engine answers the injectable parameter.",
            "sequence": [
                "Submit an expression each engine spells differently.",
                "Read which spelling the response accepted.",
            ],
            "first_false_positive": "A generic error page that every malformed value produces.",
            "done_when": "The engine and version are recorded, or the reason neither could be established.",
        }
        self.box.write("knowledge/aut/HRR-AUT-01-FPRINT.unit.yaml", unit)
        self.assertAccepted()

    def test_an_inquiry_unit_may_carry_questions_instead(self):
        self.box.add_topic(axis="asset", order=["HRR-AUT-01-SEARCH"])
        unit = {
            "id": "HRR-AUT-01-SEARCH", "topic": "HRR-AUT-01", "kind": "inquiry",
            "role": "stage", "status": "sketched",
            "title": "Search workflow assumptions",
            "objective": "Determine whether the search workflow trusts any value it did not compute.",
            "questions": [
                "Can the result set be widened by editing a value the client supplied?",
                "Is any filter enforced only in the query the client sends?",
            ],
            "done_when": "Every question above answered against the workflow in front of you, with the answer recorded.",
        }
        self.box.write("knowledge/aut/HRR-AUT-01-SEARCH.unit.yaml", unit)
        self.assertAccepted()


class PlaceholdersAndVagueLanguageAreRejected(SandboxCase):
    """A rule with a socially acceptable escape hatch stops being a rule."""

    def test_an_oracle_reading_not_applicable_is_rejected(self):
        self.box.add_topic()
        self.box.add_unit(oracle={
            "positive": "n/a",
            "negative": "Every arity and reflected position exhausted with no computed value.",
        })
        self.assertRejected("oracle.positive is a placeholder")

    def test_other_placeholder_spellings_are_rejected(self):
        # The schema enforces a minimum length, so each spelling is padded: the
        # point under test is the placeholder rule, not the length rule.
        for text in ("N/A", "not applicable", "TBD", "---"):
            with self.subTest(text=text):
                self.box.add_topic()
                self.box.add_unit(oracle={
                    "positive": text.ljust(20),
                    "negative": "Every arity and reflected position exhausted with no computed value.",
                })
                problems = validate(self.box.root)
                self.assertTrue(
                    any("placeholder" in item for item in problems.items),
                    f"{text!r} was accepted as an oracle:\n{messages(problems)}",
                )

    def test_an_unfalsifiable_objective_is_rejected(self):
        self.box.add_topic()
        self.box.add_unit(
            objective="Investigate the parameter and review the configuration for problems."
        )
        self.assertRejected("objective is not falsifiable")

    def test_an_uncountable_done_when_is_rejected(self):
        self.box.add_topic()
        self.box.add_unit(
            done_when="The parameter has been tested thoroughly against every relevant case."
        )
        self.assertRejected("done_when is not countable")

    def test_a_legitimate_oracle_mentioning_none_is_not_flagged(self):
        self.box.add_topic(order=["HRR-AUT-01-UNION"])
        self.box.add_unit(oracle={
            "positive": "A computed value appears where none of the request's own values could.",
            "negative": "Every arity exhausted and none of the reflected positions carried a computed value.",
        })
        self.assertAccepted()


class OutlineRelaxesDepthAndNothingElse(SandboxCase):
    def test_an_outline_needs_no_oracle_or_completion_criterion(self):
        self.box.add_topic(order=["HRR-AUT-01-UNION"])
        unit = {
            "id": "HRR-AUT-01-UNION", "topic": "HRR-AUT-01", "status": "outline",
            "role": "variant",
            "title": "UNION-based extraction",
            "objective": "Determine whether a UNION arm can be appended so that computed values reach the response.",
        }
        self.box.write("knowledge/aut/HRR-AUT-01-UNION.unit.yaml", unit)
        self.assertAccepted()

    def test_an_outline_still_needs_a_falsifiable_objective(self):
        self.box.add_topic()
        unit = {
            "id": "HRR-AUT-01-UNION", "topic": "HRR-AUT-01", "status": "outline",
            "role": "variant",
            "title": "UNION-based extraction",
            "objective": "Investigate the parameter for anything that looks like a problem here.",
        }
        self.box.write("knowledge/aut/HRR-AUT-01-UNION.unit.yaml", unit)
        self.assertRejected("objective is not falsifiable")


class DepthRunsInThreeTiers(SandboxCase):
    """outline, sketched, authored -- each a strict superset of the one before.

    How many units sit at each tier is published in the README, the roadmap and
    the artefact's own status page, so what it takes to claim a tier is checked
    rather than trusted. A sketch carries enough to run the test and recognise a
    wrong answer; authored adds when to enter it, what to record and where to
    stop.
    """

    #: Yielding something is a separate rule for authored units, and this test
    #: is not about that one.
    YIELDS = ["primitive.db.read"]

    def test_each_tier_is_accepted_carrying_exactly_what_it_requires(self):
        self.box.add_topic(order=["HRR-AUT-01-UNION"])
        for status in ("outline", "sketched", "authored"):
            with self.subTest(status=status):
                self.box.add_unit(status=status, yields=self.YIELDS)
                self.assertAccepted()

    def test_a_sketch_without_the_procedure_or_what_refutes_it_is_rejected(self):
        self.box.add_topic(order=["HRR-AUT-01-UNION"])
        for field in ("oracle", "sequence", "first_false_positive", "done_when"):
            with self.subTest(field=field):
                self.box.add_unit(status="sketched", yields=self.YIELDS, without=[field])
                self.assertRejected(f"'{field}' is a required property")

    def test_full_depth_without_the_record_or_the_limit_is_rejected(self):
        self.box.add_topic(order=["HRR-AUT-01-UNION"])
        for field in ("enter_when", "preconditions", "evidence", "false_positives", "safety"):
            with self.subTest(field=field):
                self.box.add_unit(status="authored", yields=self.YIELDS, without=[field])
                self.assertRejected(f"'{field}' is a required property")

    def test_an_absent_status_is_still_read_as_full_depth(self):
        """The default is what every count in the repository assumes. A unit
        that quietly meant 'sketched' by omitting the field would be reported as
        written in full."""
        self.box.add_topic(order=["HRR-AUT-01-UNION"])
        self.box.add_unit(yields=self.YIELDS, without=["evidence"])
        self.assertRejected("'evidence' is a required property")

    def test_a_stale_outline_status_is_rejected(self):
        self.box.add_topic(order=["HRR-AUT-01-UNION"])
        self.box.add_unit(status="outline", **Sandbox.SKETCH_DEPTH)
        self.assertRejected("marked outline but carries everything the sketched tier requires")

    def test_a_stale_sketched_status_is_rejected(self):
        self.box.add_topic(order=["HRR-AUT-01-UNION"])
        self.box.add_unit(status="sketched", yields=self.YIELDS, **Sandbox.AUTHORED_DEPTH)
        self.assertRejected("marked sketched but carries everything the authored tier requires")


class ReferencesMustResolve(SandboxCase):
    def test_the_authz_misspelling_is_rejected_by_shape_alone(self):
        # The published prefix is ATHZ. AUTHZ is one letter longer and reads
        # perfectly well in a diff, which is why it is caught mechanically.
        self.box.add_topic(refs={"wstg": ["WSTG-AUTHZ-01"]})
        self.assertRejected("HRR-AUT-01.topic.yaml: schema (topic)")

    def test_a_well_formed_but_unpinned_identifier_is_rejected(self):
        self.box.add_topic(refs={"wstg": ["WSTG-INPV-99"]})
        self.assertRejected("WSTG-INPV-99 is not in the pinned index")

    def test_a_pinned_asvs_requirement_is_accepted(self):
        self.box.add_topic(refs={"asvs": ["V1.2.1"]})
        self.assertAccepted()

    def test_an_asvs_section_may_be_cited_as_well_as_a_requirement(self):
        # Citing a whole section is often the more honest reference than citing
        # one requirement a mitigation only partly satisfies.
        self.box.add_topic(refs={"asvs": ["V1", "V1.2"]})
        self.assertAccepted()

    def test_an_asvs_identifier_absent_from_the_pin_is_rejected(self):
        # V5.3.4 existed in ASVS 4.x and does not exist in 5.0. An identifier
        # remembered from a superseded numbering is exactly the failure the pin
        # exists to catch: it reads as evidence while being none.
        self.box.add_topic(refs={"asvs": ["V5.3.4"]})
        self.assertRejected("V5.3.4 is not in the pinned ASVS index")

    def test_an_invented_asvs_identifier_is_rejected(self):
        self.box.add_topic(refs={"asvs": ["V99.99.99"]})
        self.assertRejected("V99.99.99 is not in the pinned ASVS index")

    def test_an_unknown_surface_tag_is_rejected(self):
        self.box.add_topic(surfaces={"any_of": ["not-a-real-surface"]})
        self.assertRejected("names unknown tag not-a-real-surface")

    def test_an_unknown_dimension_is_rejected(self):
        self.box.add_topic(dimensions={"dbms": ["mysql"]})
        self.assertRejected("unknown dimension dbms")

    def test_a_value_outside_a_dimension_is_rejected(self):
        self.box.add_topic(dimensions={"engine": ["mariadb"]})
        self.assertRejected("dimension engine has no value mariadb")

    def test_a_missing_payload_file_is_rejected(self):
        self.box.add_topic(order=["HRR-AUT-01-UNION"])
        self.box.add_unit(payloads="payloads/sqli/nonexistent.yaml")
        self.assertRejected("does not exist")

    def test_an_unknown_tool_is_rejected(self):
        self.box.add_topic(order=["HRR-AUT-01-UNION"])
        self.box.add_unit(tools=["not-a-tool"])
        self.assertRejected("unknown tool not-a-tool")


if __name__ == "__main__":
    unittest.main()


class TheAuthoringExamplesAreValidDocuments(unittest.TestCase):
    """The examples in AUTHORING.md are what a contributor copies.

    An example that does not validate teaches a mistake and costs its reader a
    rejected pull request to discover. This existed: the topic example carried a
    `kind` line, which is a unit field, and the topic schema refuses unknown
    keys -- so the file anyone built from it had never been valid.
    """

    SCHEMA_DIR = REPO_ROOT / "harrier" / "schema"

    def blocks(self):
        text = (REPO_ROOT / "docs" / "AUTHORING.md").read_text(encoding="utf-8")
        return re.findall(r"```yaml\n(.*?)```", text, re.S)

    def validator(self, name):
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource

        registry = Registry().with_resources([
            (path.name, Resource.from_contents(json.loads(path.read_text("utf-8"))))
            for path in self.SCHEMA_DIR.glob("*.schema.json")
        ])
        schema = json.loads((self.SCHEMA_DIR / f"{name}.schema.json").read_text("utf-8"))
        return Draft202012Validator(schema, registry=registry)

    def test_the_topic_example_validates(self):
        data = yaml.safe_load(self.blocks()[0])
        errors = [e.message for e in self.validator("topic").iter_errors(data)]
        self.assertEqual(errors, [])

    def test_the_unit_example_validates(self):
        data = yaml.safe_load(self.blocks()[1])
        errors = [e.message for e in self.validator("unit").iter_errors(data)]
        self.assertEqual(errors, [])
