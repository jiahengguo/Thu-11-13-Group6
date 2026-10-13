"""B02 startup evidence only; business traces remain owned by B05."""
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class PlatformStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS platform_checks (
                id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
                kind TEXT NOT NULL, outcome TEXT NOT NULL, details TEXT NOT NULL)""")

    def connect(self):
        return sqlite3.connect(str(self.path), timeout=10)

    def healthy(self):
        with closing(self.connect()) as db:
            return db.execute("SELECT 1 FROM platform_checks LIMIT 1").fetchall() is not None

    def record(self, kind, outcome, details):
        entry = {"id": str(uuid4()), "createdAt": datetime.now(timezone.utc).isoformat(),
                 "kind": kind, "outcome": outcome, "details": details}
        with closing(self.connect()) as db, db:
            db.execute("INSERT INTO platform_checks VALUES (?, ?, ?, ?, ?)",
                       (entry["id"], entry["createdAt"], kind, outcome, json.dumps(details)))
        return entry

    def recent(self):
        with closing(self.connect()) as db:
            rows = db.execute("SELECT id, created_at, kind, outcome, details FROM platform_checks "
                              "ORDER BY created_at DESC, rowid DESC LIMIT 30").fetchall()
        return [{"id": r[0], "createdAt": r[1], "kind": r[2], "outcome": r[3],
                 "details": json.loads(r[4])} for r in rows]
