"""Operations-owned records and append-only traces in the shared SQLite file.

B03 reset does not touch these tables. Business state and its trace commit together.
The TraceRepository port can read these events for future B05 integration.
"""
import json
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from tripmate.contracts import validate
from .common import OperationsError


class Records:
    def __init__(self, db):
        self.db = db

    @contextmanager
    def savepoint(self):
        """Rollback an imported specialist receipt before recording a safe failure."""
        self.db.execute('SAVEPOINT specialist_receipt')
        try:
            yield
        except Exception:
            self.db.execute('ROLLBACK TO specialist_receipt')
            self.db.execute('RELEASE specialist_receipt')
            raise
        else:
            self.db.execute('RELEASE specialist_receipt')

    def get(self, kind, key):
        row = self.db.execute("SELECT payload FROM ops_records WHERE kind=? AND id=?", (kind, key)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self, kind):
        return [json.loads(r[0]) for r in self.db.execute(
            "SELECT payload FROM ops_records WHERE kind=? ORDER BY rowid", (kind,))]

    def put(self, kind, key, payload):
        self.db.execute("INSERT INTO ops_records VALUES (?, ?, ?) ON CONFLICT(kind,id) "
                        "DO UPDATE SET payload=excluded.payload", (kind, key, json.dumps(payload)))

    def trace(self, event):
        validate("TraceEvent", event)
        self.db.execute("INSERT INTO ops_traces VALUES (?, ?, ?)",
                        (event["eventId"], event["caseId"], json.dumps(event)))


class OperationsRepository:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS ops_records (
                    kind TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(kind,id));
                CREATE TABLE IF NOT EXISTS ops_traces (
                    event_id TEXT PRIMARY KEY, case_id TEXT, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS ops_commands (
                    key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, result TEXT NOT NULL);
            """)

    def connect(self):
        return sqlite3.connect(str(self.path), timeout=10)

    @contextmanager
    def transaction(self):
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            yield Records(db)

    def read(self, kind, key):
        with closing(self.connect()) as db:
            return Records(db).get(kind, key)

    def list(self, kind):
        with closing(self.connect()) as db:
            return Records(db).all(kind)

    def command(self, key, fingerprint, callback):
        with self.transaction() as records:
            previous = records.db.execute("SELECT fingerprint,result FROM ops_commands WHERE key=?", (key,)).fetchone()
            if previous:
                if previous[0] != fingerprint:
                    raise OperationsError("UNCONFIRMED_REQUEST", "This operation ID was already used for different content.")
                return json.loads(previous[1])
            result = callback(records)
            records.db.execute("INSERT INTO ops_commands VALUES (?, ?, ?)", (key, fingerprint, json.dumps(result)))
            return result

    def cached(self, key, fingerprint):
        with closing(self.connect()) as db:
            row = db.execute("SELECT fingerprint,result FROM ops_commands WHERE key=?", (key,)).fetchone()
        if row and row[0] != fingerprint:
            raise OperationsError("UNCONFIRMED_REQUEST", "This operation ID was already used for different content.")
        return (True, json.loads(row[1])) if row else (False, None)

    def append(self, event):
        with self.transaction() as records:
            records.trace(event)

    def find_by_case(self, case_id):
        with closing(self.connect()) as db:
            return [json.loads(r[0]) for r in db.execute(
                "SELECT payload FROM ops_traces WHERE case_id=? ORDER BY rowid", (case_id,))]
