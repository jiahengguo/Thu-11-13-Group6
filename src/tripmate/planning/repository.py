"""SQLite adapter for immutable planning snapshots and atomic adoption.

Accepts the team's database path; only owns planning_* tables, not Cases or membership.
"""
import json
import sqlite3
from copy import deepcopy
from threading import RLock

from tripmate.contracts import validate
from .common import PlanningError, uid


class PlanningRepository:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.lock = RLock()
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS planning_versions(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS planning_runs(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS planning_selected(plan_id TEXT PRIMARY KEY, version_id TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS planning_acceptances(proposal_id TEXT PRIMARY KEY, version_id TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS planning_traces(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        """)

    def close(self):
        self.db.close()

    def get_version(self, version_id):
        with self.lock:
            row = self.db.execute("SELECT payload FROM planning_versions WHERE id=?", (version_id,)).fetchone()
        if row is None:
            raise PlanningError("MISSING_REQUIRED_FIELDS", "Baseline/proposal not found", "repository")
        return json.loads(row[0])

    def selected(self, plan_id):
        with self.lock:
            row = self.db.execute("SELECT version_id FROM planning_selected WHERE plan_id=?", (plan_id,)).fetchone()
        return row[0] if row else None

    def accepted(self, proposal_id):
        with self.lock:
            row = self.db.execute("SELECT version_id FROM planning_acceptances WHERE proposal_id=?", (proposal_id,)).fetchone()
        return self.get_version(row[0]) if row else None

    def lifecycle(self, plan_id):
        selected = self.selected(plan_id)
        return {"planId": plan_id, "selectedVersionId": selected, "planStatus": "PLANNED" if selected else "DRAFT"}

    def save_run(self, result, records, traces):
        validate("AgentResult", result)
        for record in records:
            validate("ItineraryVersion", record["version"])
        for event in traces:
            validate("TraceEvent", event)
        # Any failed insert rolls back the entire run; never overwrite immutable content.
        with self.lock, self.db:
            for record in records:
                self.db.execute("INSERT INTO planning_versions VALUES (?,?)",
                                (record["version"]["versionId"], json.dumps(record)))
            for event in traces:
                self.db.execute("INSERT INTO planning_traces VALUES (?,?)", (event["eventId"], json.dumps(event)))
            self.db.execute("INSERT INTO planning_runs VALUES (?,?)", (result["runId"], json.dumps(result)))

    def adopt(self, proposal_id, expected_baseline, at):
        """Internal storage operation; application service MUST perform live gates first."""
        with self.lock, self.db:
            self.db.execute("BEGIN IMMEDIATE")
            existing = self.accepted(proposal_id)
            if existing:
                return existing
            record = self.get_version(proposal_id)
            proposal = record["version"]
            if self.selected(proposal["planId"]) != expected_baseline:
                raise PlanningError("STALE_EVIDENCE", "Selected baseline changed; compare and accept again", "adoption")
            accepted = deepcopy(record)
            v = accepted["version"]
            # The accepted snapshot retains the reviewed content's identifier; lifecycle is metadata.
            # No content, review binding, price, or baseline is rewritten during adoption.
            self.db.execute("INSERT INTO planning_acceptances VALUES (?,?)", (proposal_id, v["versionId"]))
            self.db.execute("INSERT INTO planning_selected VALUES (?,?) ON CONFLICT(plan_id) DO UPDATE SET version_id=excluded.version_id",
                            (v["planId"], v["versionId"]))
            event = {"schemaVersion": "1.0.0", "caseId": v["caseId"], "correlationId": v["correlationId"],
                     "sourceReferences": v["sourceReferences"], "validationResults": [], "errors": [],
                     "requiresApproval": False, "eventId": uid("trace"), "runId": None, "timestamp": at,
                     "actor": "planning", "eventType": "CONFIRMATION", "subject": {"subjectType": "ItineraryVersion",
                     "subjectId": v["versionId"], "materialVersion": v["versionNo"]}, "parentEventId": None,
                     "executionMode": record["executionMode"], "summary": "Explicit proposal acceptance; Plan lifecycle PLANNED; no real booking",
                     "result": "SUCCESS", "approvalId": None}
            validate("TraceEvent", event)
            self.db.execute("INSERT INTO planning_traces VALUES (?,?)", (event["eventId"], json.dumps(event)))
            return accepted

    def find_by_case(self, case_id):
        with self.lock:
            rows = self.db.execute("SELECT payload FROM planning_traces ORDER BY rowid").fetchall()
        return [event for row in rows for event in [json.loads(row[0])] if event["caseId"] == case_id]
