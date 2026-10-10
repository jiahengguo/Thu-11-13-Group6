"""B01 boundary tests. These do not substitute for B04 business-rule tests."""
import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from tripmate.contracts import ContractError, SCHEMA_NAMES, schema_bundle, validate
from tripmate.orchestrator import build_agents

EXAMPLES = Path(__file__).resolve().parents[1] / "docs/contracts/v1/examples"


def load(name):
    return json.loads((EXAMPLES / name).read_text())


class ContractTests(unittest.TestCase):
    def test_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(schema_bundle())

    def test_all_examples_and_all_eight_contracts(self):
        seen = set()
        for path in sorted(EXAMPLES.glob("*.json")):
            with self.subTest(example=path.name):
                name = path.name.split(".")[0]
                validate(name, json.loads(path.read_text()))
                seen.add(name)
        self.assertEqual(seen, set(SCHEMA_NAMES))

    def test_every_required_field_is_enforced(self):
        bundle = schema_bundle()
        for name in SCHEMA_NAMES:
            path = next(EXAMPLES.glob(f"{name}.*.json"))
            example = json.loads(path.read_text())
            for field in bundle["$defs"][name]["required"]:
                with self.subTest(contract=name, field=field):
                    candidate = copy.deepcopy(example)
                    del candidate[field]
                    with self.assertRaises(ContractError):
                        validate(name, candidate)

    def test_undeclared_fields_and_wrong_contract_version(self):
        for field, value in [("secret", "do not trace this"), ("schemaVersion", "2.0.0")]:
            candidate = load("Case.confirmed.json")
            candidate[field] = value
            with self.assertRaises(ContractError):
                validate("Case", candidate)

    def test_money_has_explicit_currency_and_decimal_string(self):
        for value in [198.0, "198", "198.001", "1e2"]:
            candidate = load("PriceBreakdown.base.json")
            candidate["sellingPrice"]["amount"] = value
            with self.assertRaises(ContractError):
                validate("PriceBreakdown", candidate)
        candidate["sellingPrice"] = {"amount": "198.00", "currency": "USD"}
        with self.assertRaises(ContractError):
            validate("PriceBreakdown", candidate)

    def test_invalid_dates_and_missing_timezone(self):
        candidate = load("TravelRequest.confirmed.json")
        candidate["travelDates"]["startDate"] = "2026-02-30"
        with self.assertRaises(ContractError):
            validate("TravelRequest", candidate)
        candidate = load("Case.confirmed.json")
        candidate["confirmedAt"] = "2026-10-10T10:00:00"
        with self.assertRaises(ContractError):
            validate("Case", candidate)

    def test_pending_is_not_an_inferred_human_decision(self):
        candidate = load("Approval.pending.json")
        candidate["decision"] = "APPROVE"
        with self.assertRaises(ContractError):
            validate("Approval", candidate)
        candidate = load("Approval.approved.json")
        candidate["operatorId"] = None
        with self.assertRaises(ContractError):
            validate("Approval", candidate)

    def test_failure_and_approval_flags(self):
        candidate = load("AgentResult.supplier.failure.json")
        candidate["errors"] = []
        with self.assertRaises(ContractError):
            validate("AgentResult", candidate)
        for field, value in [("requiresApproval", False), ("approvalIds", [])]:
            candidate = load("AgentResult.supplier.approval-pending.json")
            candidate[field] = value
            with self.assertRaises(ContractError):
                validate("AgentResult", candidate)

    def test_case_is_confirmed_and_source_tagged(self):
        for field, value in [("status", "DRAFT"), ("confirmedAt", None), ("sourceReferences", [])]:
            candidate = load("Case.confirmed.json")
            candidate[field] = value
            with self.assertRaises(ContractError):
                validate("Case", candidate)
        candidate = load("Case.confirmed.json")
        candidate["caseKind"] = "SUPPLIER"
        with self.assertRaises(ContractError):
            validate("Case", candidate)

    def test_partial_plan_cannot_claim_feasible(self):
        candidate = load("ItineraryVersion.draft.json")
        candidate["assessmentState"] = "FEASIBLE"
        with self.assertRaises(ContractError):
            validate("ItineraryVersion", candidate)

    def test_unassessed_offer_cannot_claim_approved(self):
        candidate = load("SupplierOffer.draft.json")
        candidate["status"] = "APPROVED"
        with self.assertRaises(ContractError):
            validate("SupplierOffer", candidate)

    def test_all_four_stubs_fail_explicitly_and_preserve_context(self):
        agents = build_agents()
        self.assertEqual({k: a.owner for k, a in agents.items()}, {
            "operations": "Jiaheng", "planning": "Moore",
            "exception": "wrd", "supplier": "Jason",
        })
        case = load("Case.confirmed.json")
        baseline = copy.deepcopy(case)
        for agent in agents.values():
            result = agent.handle_case(case)
            validate("AgentResult", result)
            self.assertEqual(result["status"], "FAILURE")
            self.assertEqual(result["executionMode"], "STUB")
            self.assertEqual(result["errors"][0]["code"], "NOT_IMPLEMENTED")
            for field in ["caseId", "correlationId", "sourceReferences"]:
                self.assertEqual(result[field], case[field])
            result["status"] = "SUCCESS"
            result["errors"] = []
            with self.assertRaises(ContractError):
                validate("AgentResult", result)
        self.assertEqual(case, baseline)

    def test_unknown_contract_rejected(self):
        with self.assertRaises(ContractError):
            validate("Unknown", {})


if __name__ == "__main__":
    unittest.main()
