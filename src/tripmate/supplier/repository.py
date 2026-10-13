"""B08-owned version snapshots. Never touch team fixture, approval or trace tables."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from .common import SupplierError


class SupplierRepository:
    def __init__(self, database):
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db, db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS supplier_current (
                    offer_id TEXT PRIMARY KEY, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS supplier_versions (
                    offer_id TEXT NOT NULL, version INTEGER NOT NULL,
                    payload TEXT NOT NULL, PRIMARY KEY (offer_id, version));
            ''')

    def connect(self):
        return sqlite3.connect(str(self.path), timeout=10)

    def reserve(self, offer_id, case_id, mode, supplier_id=None):
        """Withdraw the old selection before any new extraction or assessment."""
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT version FROM supplier_current WHERE offer_id=?', (offer_id,)).fetchone()
            if previous:
                payload = json.loads(db.execute('SELECT payload FROM supplier_versions WHERE offer_id=? AND version=?',
                                               (offer_id, previous[0])).fetchone()[0])
                owner = payload.get('supplierId') or (payload.get('offer') or {}).get('supplierId')
                if owner and owner != supplier_id:
                    raise SupplierError('ACCESS_DENIED', 'Supplier ownership cannot change across source revisions')
                if payload['executionMode'] != mode:
                    raise SupplierError('VERIFICATION_FAILED', 'Fixture and real offers must use separate identities')
            version = previous[0] + 1 if previous else 1
            pending = dict(offer=None, price=None, result=None, caseId=case_id,
                           supplierId=supplier_id, executionMode=mode)
            db.execute('INSERT INTO supplier_versions VALUES (?, ?, ?)',
                       (offer_id, version, json.dumps(pending)))
            db.execute('INSERT OR REPLACE INTO supplier_current VALUES (?, ?)', (offer_id, version))
        return version

    def save(self, offer_id, version, record):
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            current = db.execute('SELECT version FROM supplier_current WHERE offer_id=?', (offer_id,)).fetchone()
            if current is None or current[0] != version:
                raise SupplierError('INVALID_CONTRACT', 'Assessment was superseded by a newer source revision')
            db.execute('UPDATE supplier_versions SET payload=? WHERE offer_id=? AND version=?',
                       (json.dumps(record), offer_id, version))

    def current(self, offer_id):
        with closing(self.connect()) as db:
            row = db.execute('''SELECT v.payload FROM supplier_versions v JOIN supplier_current c
                ON v.offer_id=c.offer_id AND v.version=c.version WHERE v.offer_id=?''', (offer_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def records(self):
        with closing(self.connect()) as db:
            rows = db.execute('''SELECT v.payload FROM supplier_versions v JOIN supplier_current c
                ON v.offer_id=c.offer_id AND v.version=c.version ORDER BY v.offer_id''').fetchall()
        return [json.loads(row[0]) for row in rows]

    def history(self, offer_id):
        with closing(self.connect()) as db:
            rows = db.execute('SELECT payload FROM supplier_versions WHERE offer_id=? ORDER BY version', (offer_id,)).fetchall()
        return [json.loads(row[0]) for row in rows]
