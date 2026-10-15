"""Reproducible cross-branch acceptance using actual Planning code and fixture ports.

Run with --planning-source pointing to a clean PR #9 archive/checkout. No files
from that branch are copied into the Operations implementation or shared main.
Supplier offers and the test Reviewer are explicitly simulated substitutes.
"""
import argparse
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from copy import deepcopy
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--planning-source", type=Path)
args = parser.parse_args()
import tripmate
import tripmate.agents
if args.planning_source:
    root = args.planning_source.resolve() / "src/tripmate"
    if not (root / "planning/application.py").is_file():
        parser.error("The supplied checkout/archive does not contain Planning.")
    tripmate.__path__.append(str(root))
    tripmate.agents.__path__.insert(0, str(root / "agents"))

from tripmate.fixtures import FixtureRepository
from tripmate.fixtures.b03 import fixture_quotes
from tripmate.operations import OperationsRepository, OperationsService
from tripmate.operations.common import OperationsError
from tripmate.operations.integration import connect_planning
from tripmate.planning.repository import PlanningRepository
from tripmate.planning.common import PlanningError

TIME = "2026-10-13T10:00:00+11:00"
PAID, FREE, OPERATOR = "traveller:paid", "traveller:free", "operator:fixture"


class FixtureOffers:
    def __init__(self):
        self.quotes = fixture_quotes()

    def find_selectable(self, criteria, at):
        return deepcopy(self.quotes)


class FixtureReviewer:
    def review(self, v, sources, policies):
        return {"reviewId": "test-review-"+v["versionId"],
                "subject": {"subjectType": "ItineraryVersion", "subjectId": v["versionId"], "materialVersion": v["versionNo"]},
                "outcome": "PASS", "reasons": ["Explicit test substitute; not completed B10."],
                "reviewedAt": TIME, "policyVersion": "test-fixture-only",
                "sourceIds": [s["sourceId"] for s in sources]}


class PlanningIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/"shared.db"
        self.fixtures = FixtureRepository(self.path); self.fixtures.ensure_seeded()
        self.repo = PlanningRepository(self.path); self.addCleanup(self.repo.close)
        self.offers = FixtureOffers()
        self.ops = OperationsService(OperationsRepository(self.path), self.fixtures, clock=lambda: TIME)
        connect_planning(self.ops, self.offers, FixtureReviewer(), self.repo)
        self.number = 0

    def key(self):
        self.number += 1
        return str(self.number)

    def fields(self, budget="900.00"):
        return {"origin": "Sydney Central", "destination": "Melbourne Centre", "partySize": 1,
                "budgetCeiling": {"amount": budget, "currency": "AUD"},
                "travelDates": {"startDate": "2026-10-20", "endDate": "2026-10-22"},
                "rankingMode": "VALUE", "preferences": [], "constraints": []}

    def generate(self, fields=None, actor=PAID, kind="TRAVEL_PLANNING", review=True):
        intents = [{"caseType": kind, "fields": fields or self.fields()}]
        intake = self.ops.intake(actor, self.key(), "Explicit simulated planning request", intents)
        cid = self.ops.confirm(actor, self.key(), intake["id"], 1, intents, True)["caseIds"][0]
        out = self.ops.dispatch(actor, self.key(), cid, 1)
        self.assertEqual(out["case"]["status"], "UNDER_REVIEW", out)
        refs = self.ops.repository.read("case", cid)["specialistResult"]["subjects"]
        version = refs[0]["subjectId"]
        if review:
            self.ops.review_case(OPERATOR, self.key(), cid, out["revision"], "APPROVE", "Checked exact version, simulated evidence and response.")
            reviewed = self.ops.case_view(actor, cid)
            self.ops.deliver(actor, self.key(), cid, reviewed["revision"])
        return version

    def test_actual_generation_review_and_explicit_adoption(self):
        version = self.generate()
        view = self.ops.plan_view(PAID, version)
        self.assertEqual(view["version"]["totalPrice"], {"amount": "517.00", "currency": "AUD"})
        self.assertIsNone(self.repo.selected(view["version"]["planId"]))
        self.ops.adopt_plan(PAID, self.key(), version, None, True)
        self.assertEqual(self.repo.selected(view["version"]["planId"]), version)
        rec = self.ops.repository.read("case", view["version"]["caseId"])
        self.assertEqual(rec["membershipSnapshots"][-1]["action"], "ADOPT_PLAN")
        self.assertEqual(rec["membershipSnapshots"][-1]["planVersionId"], version)

    def test_unreviewed_version_and_missing_acceptance_blocked(self):
        version = self.generate(review=False)
        with self.assertRaises(OperationsError):
            self.ops.plan_view(PAID, version)
        with self.assertRaises(OperationsError):
            self.ops.adopt_plan(PAID, self.key(), version, None, False)

    def test_revision_preserves_baseline_and_compares_exact_confirmed_fields(self):
        original = self.generate()
        self.ops.adopt_plan(PAID, self.key(), original, None, True)
        snapshot = self.repo.get_version(original)
        fields = self.fields("550.00"); fields["baselineVersionId"] = original
        revised = self.generate(fields, kind="PLAN_REVISION")
        self.assertEqual(self.repo.get_version(original), snapshot)
        self.assertEqual(self.repo.selected(snapshot["version"]["planId"]), original)
        comparison = self.ops.plan_view(PAID, revised)["comparison"]
        self.assertIn("budgetCeiling", comparison["changedRequirements"])
        self.assertIn("hardConstraints", comparison["changedRequirements"])
        self.ops.adopt_plan(PAID, self.key(), revised, original, True)
        self.assertEqual(self.repo.selected(snapshot["version"]["planId"]), revised)

    def test_free_two_trip_revision_and_adoption_use_scoped_membership(self):
        # B03 normally has two Free trips; this test completes one explicitly.
        with closing(self.fixtures._connect()) as db, db:
            entity = self.fixtures.get_entity("itinerary:free-second")
            entity["data"]["status"] = "COMPLETED"
            db.execute("UPDATE fixture_entities SET payload=? WHERE id=?", (json.dumps(entity), entity["id"]))
        original = self.generate(actor=FREE)
        self.ops.adopt_plan(FREE, self.key(), original, None, True)
        fields = self.fields("550.00"); fields["baselineVersionId"] = original
        revised = self.generate(fields, actor=FREE, kind="PLAN_REVISION")
        self.ops.adopt_plan(FREE, self.key(), revised, original, True)
        self.assertEqual(len([p for p in self.ops.trips(FREE) if p["planStatus"] in {"PLANNED", "ACTIVE"}]), 2)

    def test_internal_supplier_costs_and_drafts_are_not_public(self):
        version = self.generate()
        internal = self.repo.get_version(version)
        self.assertIn("supplierCost", json.dumps(internal))
        public = self.ops.plan_view(PAID, version)
        self.assertNotIn("supplierCost", json.dumps(public))
        self.assertNotIn("quotes", public)
        self.assertNotIn("llmDraftForReview", public)
        with self.assertRaises(OperationsError):
            self.ops.plan_view(FREE, version)

    def test_expired_quote_and_stale_selected_baseline_rejected(self):
        original = self.generate()
        self.ops.adopt_plan(PAID, self.key(), original, None, True)
        fields = self.fields("550.00"); fields["baselineVersionId"] = original
        a = self.generate(fields, kind="PLAN_REVISION")
        b = self.generate(fields, kind="PLAN_REVISION")
        self.ops.adopt_plan(PAID, self.key(), a, original, True)
        with self.assertRaises(PlanningError):
            self.ops.adopt_plan(PAID, self.key(), b, original, True)
        new = self.generate()
        for quote in self.offers.quotes:
            quote["offer"]["validUntil"] = TIME
        with self.assertRaises(PlanningError):
            self.ops.adopt_plan(PAID, self.key(), new, None, True)

    def test_audit_failure_after_adoption_retains_canonical_count_and_retry_safe(self):
        version = self.generate()
        with self.ops.repository.transaction() as records:
            records.db.execute("CREATE TRIGGER fail_ops BEFORE INSERT ON ops_traces BEGIN SELECT RAISE(ABORT,'injected audit failure'); END")
        with self.assertRaises(sqlite3.Error):
            self.ops.adopt_plan(PAID, "retry", version, None, True)
        plan_id = self.repo.get_version(version)["version"]["planId"]
        self.assertEqual(self.repo.selected(plan_id), version)
        self.assertEqual(next(p for p in self.ops.trips(PAID) if p["planId"] == plan_id)["planStatus"], "PLANNED")
        with self.ops.repository.transaction() as records:
            records.db.execute("DROP TRIGGER fail_ops")
        result = self.ops.adopt_plan(PAID, "retry", version, None, True)
        self.assertTrue(result["adopted"])
        self.assertEqual(self.ops.adopt_plan(PAID, "retry", version, None, True), result)


unittest.main(argv=[sys.argv[0]], verbosity=2)
