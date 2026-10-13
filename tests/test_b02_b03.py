"""Evidence for B02 (local app/SQLite/LLM smoke) and B03 (repeatable data)."""
import json
import os
import sqlite3
import tempfile
from contextlib import closing
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib import error, request

from tripmate.api.server import Workbench, make_server, planning_is_available
from tripmate.api.settings import Settings
from tripmate.contracts import validate
from tripmate.fixtures import FixtureRepository, baseline


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db_path = Path(self.tmp.name) / "tripmate.sqlite3"
        self.repository = FixtureRepository(self.db_path)
        self.repository.ensure_seeded()

    def test_complete_dataset_has_stable_ids_and_scenarios(self):
        first, second = baseline(), baseline()
        self.assertEqual(first, second)
        summary = self.repository.summary()
        self.assertEqual(summary["referentialIntegrity"], "PASS")
        self.assertTrue(summary["simulationOnly"])
        self.assertGreaterEqual(summary["entityCounts"]["OFFER"], 6)
        self.assertGreaterEqual(summary["entityCounts"]["OFFER_INPUT"], 6)
        self.assertGreaterEqual(summary["entityCounts"]["TRAVELLER"], 2)
        self.assertEqual({s["scenarioId"] for s in summary["scenarios"]}, {
            "happy-paid", "expired-offer", "zero-stock", "missing-field", "unsupported-currency",
            "invalid-terms", "approval-pending", "free-count-limit", "free-six-days",
            "cancellation-with-alternative", "complaint-open"
        })
        self.assertTrue(all(not s["executed"] for s in summary["scenarios"]))

    def test_valid_quotes_reuse_planning_contract_but_bad_inputs_are_unapproved(self):
        snapshot = self.repository.snapshot()
        for entity in snapshot["entities"]:
            self.assertTrue(entity["simulated"])
            if entity["kind"] == "OFFER":
                offer = entity["data"]["offer"]
                validate("SupplierOffer", offer)
                self.assertEqual(offer["status"], "APPROVED")
                self.assertTrue(all(r["simulated"] for r in offer["sourceReferences"]))
            elif entity["kind"] == "PRICE":
                validate("PriceBreakdown", entity["data"])
            elif entity["kind"] == "OFFER_INPUT":
                self.assertFalse(entity["data"]["contractValidated"])
                self.assertNotEqual(entity["data"]["rawCandidate"]["status"], "APPROVED")

    def test_repeat_reset_restores_identical_baseline_even_after_mutation(self):
        expected = self.repository.snapshot()
        with closing(sqlite3.connect(self.db_path)) as db, db:
            db.execute("UPDATE fixture_entities SET payload='{}' WHERE id='traveller:free'")
            db.execute("UPDATE fixture_entities SET payload=? WHERE id='approval:pending-exclusive'",
                       (json.dumps({"id": "approval:pending-exclusive", "kind": "APPROVAL", "simulated": True,
                                    "data": {"status": "APPROVED"}}),))
        result = self.repository.reset()
        self.assertEqual(result["referentialIntegrity"], "PASS")
        self.assertEqual(self.repository.snapshot(), expected)
        self.repository.reset()
        self.assertEqual(self.repository.snapshot(), expected)

    def test_db_foreign_keys_enforce_refs_and_failed_reset_rolls_back(self):
        expected = self.repository.snapshot()
        with closing(self.repository._connect()) as db, db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO fixture_relations VALUES (?, ?, ?)",
                           ("offer:coach", "unresolved", "supplier:missing"))
        broken = baseline()
        broken["relations"].append(("offer:coach", "invalid", "supplier:missing"))
        with patch("tripmate.fixtures.b03.baseline", return_value=broken):
            with self.assertRaises(sqlite3.IntegrityError):
                self.repository.reset()
        self.assertEqual(self.repository.snapshot(), expected)

    def test_reset_never_deletes_existing_team_planning_data(self):
        with closing(sqlite3.connect(self.db_path)) as db, db:
            db.execute("CREATE TABLE planning_versions(id TEXT PRIMARY KEY, payload TEXT)")
            db.execute("INSERT INTO planning_versions VALUES ('old-version','{}')")
            db.execute("CREATE TABLE team_approvals(id TEXT PRIMARY KEY, decision TEXT)")
            db.execute("INSERT INTO team_approvals VALUES ('team-approved','APPROVED')")
        self.repository.reset()
        with closing(sqlite3.connect(self.db_path)) as db:
            self.assertEqual(db.execute("SELECT id FROM planning_versions").fetchone()[0], "old-version")
            self.assertEqual(db.execute("SELECT decision FROM team_approvals").fetchone()[0], "APPROVED")

    def test_startup_seed_does_not_destroy_existing_planning_results(self):
        with closing(sqlite3.connect(self.db_path)) as db, db:
            db.execute("CREATE TABLE planning_versions(id TEXT PRIMARY KEY, payload TEXT)")
            db.execute("INSERT INTO planning_versions VALUES ('keep', '{}')")
            db.execute("DELETE FROM fixture_entities")
            db.execute("DELETE FROM fixture_metadata")
        self.assertTrue(self.repository.ensure_seeded())
        with closing(sqlite3.connect(self.db_path)) as db:
            self.assertEqual(db.execute("SELECT id FROM planning_versions").fetchone()[0], "keep")


class WebWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings = Settings(Path(self.tmp.name) / "tripmate.sqlite3", "FIXTURE")
        self.server = make_server(self.settings, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def get(self, path):
        with request.urlopen(self.url + path, timeout=5) as response:
            return response.status, json.loads(response.read()) if path.startswith("/api/") else response.read()

    def post(self, path, body, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-TripMate-Token"] = token
        req = request.Request(self.url + path, method="POST", headers=headers,
                              data=json.dumps(body).encode("utf8"))
        with request.urlopen(req, timeout=5) as response:
            return response.status, json.loads(response.read())

    def test_web_frontend_backend_database_and_fixture_mode(self):
        status_code, result = self.get("/api/status")
        self.assertEqual(status_code, 200)
        self.assertEqual(result["database"], "CONNECTED")
        self.assertEqual(result["executionMode"], "FIXTURE")
        self.assertEqual(result["integration"]["supplier"], "STUB")
        self.assertEqual(self.get("/api/fixtures")[1]["referentialIntegrity"], "PASS")
        code, index = self.get("/")
        self.assertEqual(code, 200)
        self.assertIn(b'fixture-reset', index)
        self.assertNotIn(b'ELEC5620_API_KEY', index)

    def test_csrf_protected_reset_and_two_http_resets(self):
        _, status = self.get("/api/status")
        with self.assertRaises(error.HTTPError) as caught:
            self.post("/api/fixtures/reset", {}, token=None)
        self.assertEqual(caught.exception.code, 403)
        before = self.server.app.fixtures.snapshot()
        _, first = self.post("/api/fixtures/reset", {}, status["csrfToken"])
        _, second = self.post("/api/fixtures/reset", {}, status["csrfToken"])
        self.assertEqual(first, second)
        self.assertEqual(before, self.server.app.fixtures.snapshot())

    def test_smoke_missing_key_is_blocked_and_recorded_without_secret(self):
        _, status = self.get("/api/status")
        with patch.dict(os.environ, {"ELEC5620_API_KEY": "REPLACE_LOCALLY"}):
            code, report = self.post("/api/model-smoke", {}, status["csrfToken"])
        self.assertEqual(code, 200)
        self.assertEqual(report["outcome"], "BLOCKED")
        self.assertEqual(report["details"]["code"], "MODEL_NOT_CONFIGURED")
        checks = self.get("/api/checks")[1]["checks"]
        self.assertEqual(checks[0]["kind"], "LLM_SMOKE")
        self.assertNotIn("REPLACE_LOCALLY", json.dumps(checks))

    def test_planning_demo_remains_optional_and_uses_separate_db(self):
        _, status = self.get("/api/status")
        if planning_is_available():
            self.assertEqual(status["integration"]["planning"], "ISOLATED_FIXTURE")
            code, result = self.post("/api/planning-demo", {"mode": "VALUE", "budget": "900.00"}, status["csrfToken"])
            self.assertEqual(code, 200)
            self.assertEqual(result["result"]["status"], "SUCCESS")
            with closing(sqlite3.connect(self.server.app.planning_db)) as db:
                self.assertGreater(db.execute("SELECT COUNT(*) FROM planning_versions").fetchone()[0], 0)
            self.post("/api/fixtures/reset", {}, status["csrfToken"])
            with closing(sqlite3.connect(self.server.app.planning_db)) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM planning_versions").fetchone()[0], 0)
        else:
            self.assertEqual(status["integration"]["planning"], "NOT_INSTALLED")
            with self.assertRaises(error.HTTPError) as caught:
                self.post("/api/planning-demo", {"mode": "VALUE", "budget": "900.00"}, status["csrfToken"])
            self.assertEqual(caught.exception.code, 422)
            self.assertEqual(json.loads(caught.exception.read())["error"], "PLANNING_NOT_INSTALLED")

    def test_reset_clears_reserved_demo_db_only_not_shared_db(self):
        with closing(sqlite3.connect(self.settings.database)) as db, db:
            db.execute("CREATE TABLE planning_versions(id TEXT PRIMARY KEY, payload TEXT)")
            db.execute("INSERT INTO planning_versions VALUES ('shared-version', '{}')")
        reserved = self.server.app.planning_db
        with closing(sqlite3.connect(reserved)) as db, db:
            db.execute("CREATE TABLE planning_versions(id TEXT PRIMARY KEY, payload TEXT)")
            db.execute("INSERT INTO planning_versions VALUES ('demo-version', '{}')")
        _, status = self.get("/api/status")
        self.post("/api/fixtures/reset", {}, status["csrfToken"])
        with closing(sqlite3.connect(self.settings.database)) as db:
            self.assertEqual(db.execute("SELECT id FROM planning_versions").fetchone()[0], 'shared-version')
        with closing(sqlite3.connect(reserved)) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM planning_versions").fetchone()[0], 0)

    def test_stub_mode_blocks_fixture_api_and_planning(self):
        another_path = Path(self.tmp.name) / "stub.sqlite3"
        server = make_server(Settings(another_path, "STUB"), port=0)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), server_thread.join(timeout=2)))
        url = f"http://127.0.0.1:{server.server_port}/api/fixtures"
        with self.assertRaises(error.HTTPError) as caught:
            request.urlopen(url, timeout=5)
        self.assertEqual(caught.exception.code, 422)


if __name__ == "__main__":
    unittest.main()
