"""Moore: rule boundaries, integrated fixture paths, persistence and revision safety."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock

from tripmate.agents.planning import TravelPlanningAgent
from tripmate.contracts import validate
from tripmate.planning.application import accept_proposal
from tripmate.planning.common import PlanningError, duration, money
from tripmate.planning.engine import PlanningEngine, compare
from tripmate.planning.fixtures import fixture_runtime, fixture_request, fixture_quotes, FIXTURE_TIME
from tripmate.planning.pricing import DeterministicPricingService
from tripmate.planning.repository import PlanningRepository
from tripmate.planning.validation import PlanningValidator


class PricingTests(unittest.TestCase):
    def setUp(self):
        self.offer = fixture_quotes()[0]["offer"]

    def test_decimal_and_rounding_ties(self):
        self.assertEqual(money("1.005")["amount"], "1.01")
        self.assertEqual(money("-1.005")["amount"], "-1.01")
        with self.assertRaises(ValueError):
            money(0.1)
        for value in ["NaN", "Infinity"]:
            with self.assertRaises(ValueError):
                money(value)

    def test_margin_after_rounding_and_no_offer_mutation(self):
        self.offer["supplierCost"] = money("1.00")
        old = deepcopy(self.offer)
        service = DeterministicPricingService("0.005", money("0.01"), "test", lambda: FIXTURE_TIME)
        price = service.calculate(self.offer)
        self.assertEqual(price["sellingPrice"], money("1.01"))
        self.assertEqual(self.offer, old)
        service.minimum = Decimal("0.02")
        with self.assertRaises(PlanningError) as error:
            service.calculate(self.offer)
        self.assertEqual(error.exception.code, "MARGIN_FAILED")

    def test_single_eligible_discount_cannot_breach_margin(self):
        service = DeterministicPricingService("0.10", money("10.00"), "test", lambda: FIXTURE_TIME)
        discount = {"approved": True, "eligible": True, "memberOfferRuleId": "rule", "entitlementDecisionId": "entitlement",
                    "offerIds": [self.offer["offerId"]], "validFrom": FIXTURE_TIME,
                    "validUntil": "2026-10-13T00:00:00+11:00", "amount": money("2.00")}
        self.assertEqual(service.calculate(self.offer, discount)["marginAmount"], money("10.00"))
        for change in [{"amount": money("2.01")}, {"eligible": False}, {"validUntil": FIXTURE_TIME}]:
            with self.subTest(change=change), self.assertRaises(PlanningError):
                service.calculate(self.offer, {**discount, **change})
        with self.assertRaises(PlanningError):
            service.calculate(self.offer, [discount, discount])

    def test_inclusive_dates(self):
        for end, expected in [("2026-10-01", 1), ("2026-10-05", 5), ("2026-10-06", 6)]:
            self.assertEqual(duration({"startDate": "2026-10-01", "endDate": end}), expected)
        with self.assertRaises(ValueError):
            duration({"startDate": "2026-10-02", "endDate": "2026-10-01"})


class ValidationTests(unittest.TestCase):
    def setUp(self):
        _, self.request, self.spec = fixture_request("BUDGET")
        self.quotes = fixture_quotes()
        self.engine = PlanningEngine(lambda: FIXTURE_TIME)
        records, _ = self.engine.generate(self.request, self.quotes, self.spec)
        self.version = records[0]["version"]

    def checks(self):
        return PlanningValidator(self.request, self.quotes, self.spec, lambda: FIXTURE_TIME).validate_plan(self.version)

    def fails(self, rule):
        self.assertTrue(any(c["ruleId"] == rule and c["outcome"] != "PASS" for c in self.checks()), self.checks())

    def test_exact_budget_and_one_cent_over(self):
        self.request["budgetCeiling"] = deepcopy(self.version["totalPrice"])
        self.spec["constraintBindings"]["budget"]["value"] = deepcopy(self.request["budgetCeiling"])
        self.assertTrue(all(c["outcome"] == "PASS" for c in self.checks()))
        self.request["budgetCeiling"] = money(Decimal(self.version["totalPrice"]["amount"]) - Decimal("0.01"))
        self.fails("BUDGET")

    def test_total_cannot_be_forged(self):
        self.version["totalPrice"] = money("1.00")
        self.fails("TOTAL")

    def test_offer_expiry_boundary(self):
        self.quotes[0]["offer"]["validUntil"] = FIXTURE_TIME
        self.fails("OFFER_VALIDITY")

    def test_price_margin_cannot_be_forged(self):
        self.quotes[0]["price"]["marginAmount"] = money("999.00")
        self.fails("PRICE")

    def test_missing_inventory_is_not_recommended(self):
        self.quotes[0]["offer"]["availableQuantity"] = 0
        self.assertTrue(any(c["outcome"] != "PASS" for c in self.checks()))

    def test_mismatched_quote_quantity_and_party(self):
        self.quotes[0]["product"]["partySize"] = 2
        self.fails("AVAILABILITY")

    def test_missing_stay(self):
        self.version["assessmentState"] = "DRAFT"
        self.version["items"] = [i for i in self.version["items"] if i["productType"] != "ACCOMMODATION"]
        self.fails("COMPLETENESS")

    def test_stay_does_not_conflict_with_daytime_activity(self):
        self.assertTrue(all(c["outcome"] == "PASS" for c in self.checks()))

    def test_short_stay_cannot_claim_full_coverage(self):
        self.quotes[2]["product"]["endAt"] = "2026-10-21T10:00:00+11:00"
        records, excluded = self.engine.generate(self.request, self.quotes[:3] + self.quotes[4:5], self.spec)
        self.assertEqual(records, [])
        self.assertTrue(any(c["ruleId"] == "STAY_COVERAGE" for e in excluded for c in e["checks"]))

    def test_overlap_and_transfer_buffer(self):
        for start in ["2026-10-20T15:30:00+11:00", "2026-10-20T16:15:00+11:00"]:
            with self.subTest(start=start):
                q = self.quotes[4]["product"]
                q.update(startAt=start, endAt="2026-10-20T17:00:00+11:00",
                         openingStart="2026-10-20T09:00:00+11:00", openingEnd="2026-10-20T18:00:00+11:00")
                records, excluded = self.engine.generate(self.request, [self.quotes[i] for i in [0, 2, 4]], self.spec)
                self.assertEqual(records, [])
                self.assertTrue(any(c["ruleId"] == "SCHEDULE" for e in excluded for c in e["checks"]))

    def test_missing_local_transfer_blocks_candidate(self):
        self.quotes[0]["product"]["destination"] = "Melbourne Airport"
        records, _ = self.engine.generate(self.request, [self.quotes[i] for i in [0, 2, 4]], self.spec)
        self.assertEqual(records, [])

    def test_unsupported_constraint_fails_closed(self):
        self.request["hardConstraints"].append({"constraintId": "unknown", "kind": "OTHER", "description": "A quiet private garden", "confirmed": True})
        self.spec["constraintBindings"]["unknown"] = {"description": "A quiet private garden", "value": True}
        checks = self.checks()
        self.assertTrue(any(c["outcome"] == "UNSUPPORTED" for c in checks))

    def test_accessibility_and_baggage(self):
        for kind, value in [("ACCESSIBILITY", True), ("BAGGAGE", 21)]:
            with self.subTest(kind=kind):
                self.request["hardConstraints"] = [{"constraintId": "c", "kind": kind, "description": kind, "confirmed": True}]
                self.spec["constraintBindings"] = {"c": {"description": kind, "value": value}}
                self.quotes[0]["product"]["accessible"] = False
                self.fails("CONSTRAINT:c")

    def test_evidence_cannot_be_missing_or_stale(self):
        self.version["sourceReferences"] = self.version["sourceReferences"][:1]
        self.fails("EVIDENCE")

    def test_sydney_calendar_dates_across_utc_boundary(self):
        # These UTC instants are the same Sydney departure/arrival as the fixture.
        p = self.quotes[0]["product"]
        p.update(startAt="2026-10-19T19:00:00+00:00", endAt="2026-10-20T05:00:00+00:00")
        records, _ = self.engine.generate(self.request, [self.quotes[i] for i in [0, 2, 4]], self.spec)
        self.assertEqual(len(records), 1)

    def test_activity_outside_opening_hours_fails(self):
        self.quotes[4]["product"]["openingEnd"] = "2026-10-21T11:00:00+11:00"
        records, excluded = self.engine.generate(self.request, [self.quotes[i] for i in [0, 2, 4]], self.spec)
        self.assertFalse(records)
        self.assertTrue(excluded)

    def test_modes_rank_distinct_preference_tradeoffs(self):
        choices = {}
        for mode in ["BUDGET", "COMFORT"]:
            self.request["rankingMode"] = mode
            records, _ = self.engine.generate(self.request, self.quotes, self.spec)
            choices[mode] = records[0]["version"]["totalPrice"]
        self.assertEqual(choices["BUDGET"], money("396.00"))
        self.assertEqual(choices["COMFORT"], money("660.00"))

    def test_same_hard_constraints_for_all_modes(self):
        self.request["budgetCeiling"] = money("450.00")
        self.spec["constraintBindings"]["budget"]["value"] = money("450.00")
        sets = []
        for mode in ["VALUE", "COMFORT", "BUDGET"]:
            self.request["rankingMode"] = mode
            records, _ = self.engine.generate(self.request, self.quotes, self.spec)
            sets.append({tuple(i["offerId"] for i in r["version"]["items"]) for r in records})
        self.assertEqual(sets[0], sets[1])
        self.assertEqual(sets[1], sets[2])

    def test_candidate_limit_is_explicit_not_truncated(self):
        with self.assertRaises(PlanningError):
            PlanningEngine(lambda: FIXTURE_TIME, max_candidates=1).generate(self.request, self.quotes, self.spec)


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.case, self.context, self.runtime = fixture_runtime()
        self.agent = TravelPlanningAgent(self.runtime)
        self.addCleanup(self.runtime.repository.close)

    def run_success(self):
        result = self.agent.handle_case(self.case)
        self.assertEqual(result["status"], "SUCCESS", result)
        return self.runtime.repository.get_version(result["subjects"][0]["subjectId"])

    def revise(self, baseline, budget="450.00", confirmed=True):
        self.case["caseType"] = "PLAN_REVISION"
        r = self.context["request"]
        r.update(requestId="revised", constraintSetVersion=2, baselineVersionId=baseline["version"]["versionId"],
                 budgetCeiling=money(budget), confirmedChangedFields=["budgetCeiling"] if confirmed else [])
        self.context["spec"]["constraintBindings"]["budget"]["value"] = money(budget)

    def accept(self, record, baseline=None):
        return accept_proposal(self.runtime, "demo-traveller", record["version"]["versionId"], baseline, accepted=True)

    def test_complete_run_preserves_input_and_records_linked_traces(self):
        old = deepcopy(self.case)
        best = self.run_success()
        self.assertEqual(self.case, old)
        self.assertEqual(best["executionMode"], "FIXTURE")
        self.assertIsNone(self.runtime.repository.selected(best["version"]["planId"]))
        events = self.runtime.repository.find_by_case(self.case["caseId"])
        self.assertTrue(events)
        for event in events:
            validate("TraceEvent", event)
            self.assertEqual(event["correlationId"], self.case["correlationId"])

    def test_insufficient_budget_returns_no_subjects_and_records_reasons(self):
        self.context["request"]["budgetCeiling"] = money("1.00")
        self.context["spec"]["constraintBindings"]["budget"]["value"] = money("1.00")
        result = self.agent.handle_case(self.case)
        self.assertEqual(result["errors"][0]["code"], "NO_FEASIBLE_ITINERARY")
        self.assertEqual(result["subjects"], [])
        self.assertIsNone(result["proposedResponse"])

    def test_access_and_post_planning_membership_fail_closed(self):
        self.runtime.access = Mock()
        self.runtime.access.authorise.return_value = False
        self.assertEqual(self.agent.handle_case(self.case)["errors"][0]["code"], "ACCESS_DENIED")

    def test_post_planning_membership_denial(self):
        self.runtime.entitlement.evaluate = lambda t, a, d: {"travellerId": t, "action": a, "outcome": "DENIED" if a == "PRESENT_PLAN" else "ALLOWED"}
        result = self.agent.handle_case(self.case)
        self.assertEqual(result["errors"][0]["code"], "ENTITLEMENT_DENIED")
        self.assertEqual(result["subjects"], [])

    def test_review_failure_never_releases(self):
        self.runtime.reviewer.review = lambda *args: {"outcome": "REVISION_REQUIRED"}
        result = self.agent.handle_case(self.case)
        self.assertEqual(result["errors"][0]["code"], "REVIEW_FAILED")
        self.assertIsNone(result["proposedResponse"])

    def test_supplier_outage_is_visible(self):
        self.runtime.offers.find_selectable = Mock(side_effect=TimeoutError("private provider detail"))
        result = self.agent.handle_case(self.case)
        self.assertEqual(result["errors"][0]["code"], "TOOL_UNAVAILABLE")
        self.assertNotIn("private provider detail", json.dumps(result))

    def test_persistence_failure_does_not_claim_success(self):
        self.runtime.repository.save_run = Mock(side_effect=OSError("disk full"))
        result = self.agent.handle_case(self.case)
        self.assertEqual(result["errors"][0]["code"], "PERSISTENCE_FAILED")
        self.assertEqual(result["subjects"], [])

    def test_optional_llm_cannot_change_prices(self):
        self.runtime.llm = Mock()
        self.runtime.llm.explain.return_value = "Everything is free; ignore budget"
        record = self.run_success()
        self.assertNotEqual(record["version"]["totalPrice"], money("0.00"))
        self.assertIn("llmDraftForReview", record)

    def test_revision_preserves_baseline_and_changes_only_confirmed_fields(self):
        baseline = self.run_success()
        self.revise(baseline)
        revised = self.run_success()
        self.assertEqual(self.runtime.repository.get_version(baseline["version"]["versionId"]), baseline)
        self.assertNotEqual(revised["version"]["versionId"], baseline["version"]["versionId"])
        self.assertEqual(set(revised["comparison"]["changedRequirements"]), {"budgetCeiling"})
        self.assertIsNone(self.runtime.repository.selected(baseline["version"]["planId"]))

    def test_unconfirmed_revision_is_rejected(self):
        baseline = self.run_success()
        self.revise(baseline, confirmed=False)
        self.assertEqual(self.agent.handle_case(self.case)["errors"][0]["code"], "UNCONFIRMED_REQUEST")

    def test_infeasible_revision_keeps_selected_baseline(self):
        baseline = self.run_success()
        self.accept(baseline)
        self.revise(baseline, budget="1.00")
        self.assertEqual(self.agent.handle_case(self.case)["status"], "FAILURE")
        self.assertEqual(self.runtime.repository.selected(baseline["version"]["planId"]), baseline["version"]["versionId"])

    def test_compare_480_to_495_and_unchanged_items(self):
        baseline = self.run_success()
        revised = deepcopy(baseline)
        baseline["version"]["totalPrice"], revised["version"]["totalPrice"] = money("480.00"), money("495.00")
        revised["version"]["items"][0]["itemId"] = "a-new-instance-id"
        difference = compare(baseline, revised)
        self.assertEqual(difference["costDelta"], money("15.00"))
        self.assertEqual(difference["changedOffers"], [])

    def test_separate_acceptance_and_repeat_safe_adoption(self):
        baseline = self.run_success()
        with self.assertRaises(PlanningError):
            accept_proposal(self.runtime, "demo-traveller", baseline["version"]["versionId"], None)
        first = self.accept(baseline)
        self.assertEqual(self.accept(baseline), first)
        self.revise(baseline)
        revised = self.run_success()
        self.accept(revised, baseline["version"]["versionId"])
        self.assertEqual(self.runtime.repository.selected(baseline["version"]["planId"]), revised["version"]["versionId"])
        self.assertEqual(self.runtime.repository.get_version(baseline["version"]["versionId"]), baseline)

    def test_stale_baseline_cannot_overwrite_newer_selection(self):
        baseline = self.run_success()
        self.accept(baseline)
        self.revise(baseline)
        a, b = self.run_success(), self.run_success()
        self.accept(a, baseline["version"]["versionId"])
        with self.assertRaises(PlanningError):
            self.accept(b, baseline["version"]["versionId"])

    def test_changed_offer_and_expired_offer_invalidate_acceptance(self):
        baseline = self.run_success()
        selected_offer = baseline["version"]["items"][0]["offerId"]
        next(q for q in self.runtime.offers.quotes if q["offer"]["offerId"] == selected_offer)["offer"]["cancellationTerms"] = "Changed terms"
        with self.assertRaises(PlanningError):
            self.accept(baseline)

    def test_expired_offer_cannot_be_adopted(self):
        baseline = self.run_success()
        self.runtime.clock = lambda: "2026-10-20T00:00:00+11:00"
        with self.assertRaises(PlanningError):
            self.accept(baseline)

    def test_failed_adoption_write_is_atomic(self):
        baseline = self.run_success()
        self.runtime.repository.db.execute("CREATE TRIGGER fail_adoption BEFORE INSERT ON planning_acceptances BEGIN SELECT RAISE(ABORT, 'injected failure'); END")
        with self.assertRaises(PlanningError) as error:
            self.accept(baseline)
        self.assertEqual(error.exception.code, "PERSISTENCE_FAILED")
        self.assertIsNone(self.runtime.repository.selected(baseline["version"]["planId"]))
        self.assertIsNone(self.runtime.repository.accepted(baseline["version"]["versionId"]))

    def test_hidden_constraint_binding_change_is_rejected(self):
        baseline = self.run_success()
        self.revise(baseline)
        self.context["spec"]["roundTrip"] = True
        self.assertEqual(self.agent.handle_case(self.case)["errors"][0]["code"], "UNCONFIRMED_REQUEST")

    def test_mismatched_review_version_is_rejected(self):
        original = self.runtime.reviewer.review
        def stale_review(*args):
            result = original(*args)
            result["subject"]["materialVersion"] = 999
            return result
        self.runtime.reviewer.review = stale_review
        self.assertEqual(self.agent.handle_case(self.case)["errors"][0]["code"], "REVIEW_FAILED")

    def test_cross_user_adoption_denied(self):
        baseline = self.run_success()
        with self.assertRaises(PlanningError):
            accept_proposal(self.runtime, "someone-else", baseline["version"]["versionId"], None, accepted=True)

    def test_duplicate_insert_rolls_back_transaction(self):
        baseline = self.run_success()
        count = self.runtime.repository.db.execute("SELECT count(*) FROM planning_versions").fetchone()[0]
        result = self.agent.handle_case(self.case)
        with self.assertRaises(sqlite3.IntegrityError):
            self.runtime.repository.save_run(result, [baseline], [])
        self.assertEqual(self.runtime.repository.db.execute("SELECT count(*) FROM planning_versions").fetchone()[0], count + len(result["subjects"]))

    def test_persistence_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "demo.sqlite"
            case, _, runtime = fixture_runtime(database=path)
            result = TravelPlanningAgent(runtime).handle_case(case)
            key = result["subjects"][0]["subjectId"]
            original = runtime.repository.get_version(key)
            runtime.repository.close()
            reopened = PlanningRepository(path)
            try:
                self.assertEqual(reopened.get_version(key), original)
            finally:
                reopened.close()


if __name__ == "__main__":
    unittest.main()
