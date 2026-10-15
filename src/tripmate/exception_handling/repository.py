"""Append-only local simulation snapshots. One transaction per completed handoff."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from tripmate.contracts import validate

class ExceptionRepository:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS exception_runs '
                       '(run_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, recorded_at TEXT NOT NULL, payload TEXT NOT NULL)')

    def save(self, snapshot):
        validate("AgentResult", snapshot["result"])
        for event in snapshot["trace"]:
            validate("TraceEvent", event)
        for approval in snapshot["approvals"]:
            validate("Approval", approval)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('INSERT INTO exception_runs VALUES (?,?,?,?)',
                       (snapshot["result"]["runId"], snapshot["result"]["caseId"],
                        snapshot["recordedAt"], json.dumps(snapshot, ensure_ascii=False)))

    def recent(self):
        with closing(sqlite3.connect(self.path)) as db:
            rows = db.execute('SELECT payload FROM exception_runs ORDER BY rowid DESC LIMIT 30').fetchall()
        return [json.loads(row[0]) for row in rows]

    def get(self, run_id):
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute('SELECT payload FROM exception_runs WHERE run_id=?', (run_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def find_by_case(self, case_id):
        with closing(sqlite3.connect(self.path)) as db:
            rows = db.execute('SELECT payload FROM exception_runs WHERE case_id=? ORDER BY rowid', (case_id,)).fetchall()
        return [event for row in rows for event in json.loads(row[0])["trace"]]
