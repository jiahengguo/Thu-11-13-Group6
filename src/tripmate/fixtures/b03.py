"""B03 repeatable, simulated Sydney→Melbourne dataset for the shared local workbench.

These records are *test inputs*, not real supplier feeds, customer accounts, approvals,
bookings or proof that the B06/B08/B10 business workflows have executed.

The fixture clock deliberately matches Moore's independent planning demo.  The
fixture catalog has stable identifiers even when a reset is run repeatedly.
"""
import json
import sqlite3
from contextlib import closing
from copy import deepcopy
from pathlib import Path

from tripmate.contracts import validate
FIXTURE_TIME = "2026-10-12T10:00:00+11:00"


def fixture_quotes():
    """Load B03-owned synthetic examples, not the Planning runtime."""
    return json.loads(Path(__file__).with_name("sample_quotes.json").read_text(encoding="utf-8"))

FIXTURE_VERSION = "b03-sydney-melbourne-v1"


def _entity(kind, identifier, data):
    return {"id": identifier, "kind": kind, "simulated": True, "data": data}


def baseline():
    """Return fresh and deterministic entities, relations, and expected outcomes.

    The baseline intentionally includes malformed source *inputs*.  Do not pass
    invalid candidate offers off as validated SupplierOffer contract outputs.
    """
    entities, links = [], []

    def add(kind, identifier, data, **relations):
        entities.append(_entity(kind, identifier, data))
        for relationship, target in relations.items():
            if isinstance(target, list):
                links.extend((identifier, relationship, value) for value in target)
            else:
                links.append((identifier, relationship, target))

    add("SUPPLIER", "supplier:fixture-supplier", {
        "name": "Simulated Sydney–Melbourne Supplier", "status": "ACTIVE", "currency": "AUD",
        "sourceReference": "fixture://b03/supplier/fixture-supplier", "realSupplier": False,
    })
    add("SUPPLIER", "supplier:backup-supplier", {
        "name": "Synthetic Alternative Supplier", "status": "ACTIVE", "currency": "AUD",
        "sourceReference": "fixture://b03/supplier/backup-supplier", "realSupplier": False,
    })

    # B03-owned synthetic inputs retain the agreed Planning-compatible shape.
    # No dependency on Moore's separate implementation is required.
    quotes = fixture_quotes()
    for quote in quotes:
        name = quote["offer"]["offerId"]
        product = deepcopy(quote["product"])
        offer = deepcopy(quote["offer"])
        price = deepcopy(quote["price"])
        stable_price_id = "fixture-price-" + name
        offer["priceBreakdownId"] = stable_price_id
        price["priceBreakdownId"] = stable_price_id
        validate("SupplierOffer", offer)
        validate("PriceBreakdown", price)
        add("PRODUCT", "product:" + name, product, supplier="supplier:fixture-supplier")
        add("OFFER", "offer:" + name, {"offer": offer, "expectedSourceStatus": "APPROVED_FIXTURE_ONLY"},
            supplier="supplier:fixture-supplier", product="product:" + name, price="price:" + name)
        add("PRICE", "price:" + name, price, offer="offer:" + name)

    # Invalid input examples are intentionally not contract-valid SupplierOffer
    # outputs. They exist so B08 can prove its fail-closed validation behaviour.
    invalid_cases = [
        ("expired", "coach", "OFFER_EXPIRED", "Quoted validity has ended"),
        ("zero-stock", "basic-stay", "OFFER_INVALID", "Available quantity is zero"),
        ("missing-cost", "walk", "MISSING_REQUIRED_FIELDS", "Supplier cost missing"),
        ("unsupported-currency", "coach", "OFFER_INVALID", "Only AUD is supported"),
        ("missing-terms", "walk", "OFFER_INVALID", "Cancellation terms missing"),
        ("pending-approval", "express", "APPROVAL_REQUIRED", "Restricted supplier commitment needs human approval"),
    ]
    by_name = {q["offer"]["offerId"]: q["offer"] for q in quotes}
    for label, template, expected, reason in invalid_cases:
        candidate = deepcopy(by_name[template])
        candidate.update(offerId="candidate-" + label, productId=template,
                         status="DRAFT", priceBreakdownId=None, review=None, approvalId=None)
        if label == "expired":
            candidate["validUntil"] = "2026-10-11T10:00:00+11:00"
        elif label == "zero-stock":
            candidate["availableQuantity"] = 0
        elif label == "missing-cost":
            candidate.pop("supplierCost")
        elif label == "unsupported-currency":
            candidate["supplierCost"]["currency"] = "USD"
        elif label == "missing-terms":
            candidate["cancellationTerms"] = ""
        elif label == "pending-approval":
            candidate["commercialTerms"] = ["Synthetic restricted exclusive supplier commitment; human approval required"]
        add("OFFER_INPUT", "candidate:" + label,
            {"rawCandidate": candidate, "expectedCode": expected, "expectedReason": reason,
             "contractValidated": False, "sourceReference": "fixture://b03/candidate/" + label},
            supplier="supplier:fixture-supplier", product="product:" + template)

    add("TRAVELLER", "traveller:free", {"membership": "FREE", "verified": True,
        "activeOrPlannedTripCount": 2, "name": "Synthetic Free Traveller"})
    add("TRAVELLER", "traveller:paid", {"membership": "PAID", "verified": True,
        "activeOrPlannedTripCount": 1, "name": "Synthetic Paid Traveller"})
    add("TRAVELLER", "traveller:unverified", {"membership": "FREE", "verified": False,
        "activeOrPlannedTripCount": 0, "name": "Unverified Synthetic Traveller"})

    add("CASE", "case:paid-trip", {
        "caseType": "TRAVEL_PLANNING", "caseStatus": "CONFIRMED", "requestConfirmed": True,
        "origin": "Sydney Central", "destination": "Melbourne Centre", "currency": "AUD",
        "partySize": 1, "startDate": "2026-10-20", "endDate": "2026-10-22",
        "budgetCeiling": "900.00", "correlationId": "b03-paid-trip",
    }, traveller="traveller:paid")
    add("CASE", "case:free-limit", {
        "caseType": "TRAVEL_PLANNING", "caseStatus": "CONFIRMED", "requestConfirmed": True,
        "origin": "Sydney Central", "destination": "Melbourne Centre", "currency": "AUD",
        "partySize": 1, "startDate": "2026-10-20", "endDate": "2026-10-22",
        "budgetCeiling": "900.00", "correlationId": "b03-free-limit",
    }, traveller="traveller:free")
    add("CASE", "case:six-days", {
        "caseType": "TRAVEL_PLANNING", "caseStatus": "CONFIRMED", "requestConfirmed": True,
        "origin": "Sydney Central", "destination": "Melbourne Centre", "currency": "AUD",
        "partySize": 1, "startDate": "2026-10-20", "endDate": "2026-10-25",
        "budgetCeiling": "900.00", "correlationId": "b03-free-six-days",
        "membershipTestOverride": "FREE_WITH_NO_ACTIVE_TRIPS",
    }, traveller="traveller:free")

    add("ITINERARY", "itinerary:active-paid", {
        "caseId": "case:paid-trip", "status": "ACTIVE", "versionNo": 1,
        "items": ["offer:express", "offer:comfort-stay", "offer:guided-tour"],
        "realBooking": False, "sourceReference": "fixture://b03/itinerary/active-paid",
    }, case="case:paid-trip", items=["offer:express", "offer:comfort-stay", "offer:guided-tour"])
    add("ITINERARY", "itinerary:free-first", {
        "status": "PLANNED", "versionNo": 1, "realBooking": False,
        "description": "First already-planned Free tier trip; count fixture"},
        traveller="traveller:free")
    add("ITINERARY", "itinerary:free-second", {
        "status": "ACTIVE", "versionNo": 1, "realBooking": False,
        "description": "Second active Free tier trip; count fixture"},
        traveller="traveller:free")

    add("DISRUPTION", "disruption:express-cancelled", {
        "eventType": "SUPPLIER_CANCELLATION", "occurredAt": "2026-10-20T07:00:00+11:00",
        "affectedOfferId": "offer:express", "evidence": "fixture://b03/events/cancel-express",
        "candidateAlternativeIds": ["offer:coach"], "realRebooking": False,
        "expectedAction": "Investigate and request Supplier/Planning recovery without changing the active version",
    }, itinerary="itinerary:active-paid", affectedOffer="offer:express", alternative="offer:coach")
    add("COMPLAINT", "complaint:timing", {
        "reportedAt": "2026-10-20T12:00:00+11:00", "reason": "Simulated late arrival complaint",
        "status": "OPEN", "realRefundOrCompensation": False,
        "expectedAction": "Investigate and route any restricted outcome to human approval",
    }, case="case:paid-trip", itinerary="itinerary:active-paid")
    add("APPROVAL", "approval:pending-exclusive", {
        "status": "PENDING", "subjectId": "candidate:pending-approval", "materialVersion": 1,
        "isRealApproval": False, "reason": "Example of awaiting Human Founder/Operator decision",
    }, subject="candidate:pending-approval")

    scenarios = [
        ("happy-paid", ["case:paid-trip", "offer:coach", "offer:basic-stay", "offer:walk"],
         "Eligible confirmed PAID traveller; feasible approved simulated inventory", "ELIGIBLE_FIXTURE_INPUT"),
        ("expired-offer", ["candidate:expired"], "Expired supplier quote must not be approved", "OFFER_EXPIRED"),
        ("zero-stock", ["candidate:zero-stock"], "Stock 0 must not be approved", "OFFER_INVALID"),
        ("missing-field", ["candidate:missing-cost"], "Missing cost requires correction", "MISSING_REQUIRED_FIELDS"),
        ("unsupported-currency", ["candidate:unsupported-currency"], "Unsupported currency blocks approval", "OFFER_INVALID"),
        ("invalid-terms", ["candidate:missing-terms"], "Missing cancellation terms blocks approval", "OFFER_INVALID"),
        ("approval-pending", ["candidate:pending-approval", "approval:pending-exclusive"],
         "Restricted commitment waits for a human decision", "APPROVAL_REQUIRED"),
        ("free-count-limit", ["traveller:free", "case:free-limit"],
         "Free traveller already has two Planned/Active trips", "ENTITLEMENT_DENIED"),
        ("free-six-days", ["case:six-days"],
         "Free six-calendar-day request fails independently of trip count", "ENTITLEMENT_DENIED"),
        ("cancellation-with-alternative", ["disruption:express-cancelled", "offer:coach"],
         "Supplier cancellation requires recovery proposal; no real rebooking", "RECOVERY_REVIEW_REQUIRED"),
        ("complaint-open", ["complaint:timing"],
         "Complaint needs investigation; cannot issue a real refund", "HUMAN_REVIEW_REQUIRED"),
    ]
    result = {
        "fixtureVersion": FIXTURE_VERSION, "fixtureTime": FIXTURE_TIME,
        "executionMode": "FIXTURE", "simulationOnly": True,
        "entities": sorted(entities, key=lambda item: item["id"]),
        "relations": sorted({(a, b, c) for a, b, c in links}),
        "scenarios": [
            {"scenarioId": name, "entityIds": references, "description": description,
             "expectedOutcome": outcome, "executed": False}
            for name, references, description, outcome in scenarios
        ],
    }
    ids = {e["id"] for e in result["entities"]}
    if len(ids) != len(result["entities"]):
        raise ValueError("Duplicate fixture entity ID")
    for src, _name, target in result["relations"]:
        if src not in ids or target not in ids:
            raise ValueError("Orphaned fixture relationship")
    for scenario in result["scenarios"]:
        if not set(scenario["entityIds"]).issubset(ids):
            raise ValueError("Scenario references missing fixture records")
    return result


class FixtureRepository:
    """A separate B03 namespace in the same shared SQLite file.

    Reset only touches the fixture_* tables. Planning and other team records
    are never deleted by this class.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS fixture_entities (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS fixture_relations (
                    from_id TEXT NOT NULL REFERENCES fixture_entities(id) ON DELETE CASCADE,
                    relation TEXT NOT NULL,
                    to_id TEXT NOT NULL REFERENCES fixture_entities(id) ON DELETE CASCADE,
                    PRIMARY KEY (from_id, relation, to_id)
                );
                CREATE TABLE IF NOT EXISTS fixture_scenarios (
                    scenario_id TEXT PRIMARY KEY, payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS fixture_metadata (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
            """)

    def _connect(self):
        db = sqlite3.connect(str(self.path), timeout=10)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        return db

    @staticmethod
    def _install(db, data):
        # One transaction: interruption cannot leave a half-seeded dataset.
        db.execute("BEGIN IMMEDIATE")
        for table in ("fixture_relations", "fixture_scenarios", "fixture_entities", "fixture_metadata"):
            db.execute("DELETE FROM " + table)
        db.executemany("INSERT INTO fixture_entities (id, kind, payload) VALUES (?, ?, ?)",
                       ((e["id"], e["kind"], json.dumps(e, sort_keys=True)) for e in data["entities"]))
        db.executemany("INSERT INTO fixture_relations VALUES (?, ?, ?)", data["relations"])
        db.executemany("INSERT INTO fixture_scenarios VALUES (?, ?)",
                       ((s["scenarioId"], json.dumps(s, sort_keys=True)) for s in data["scenarios"]))
        db.executemany("INSERT INTO fixture_metadata VALUES (?, ?)",
                       ((k, str(data[k])) for k in ("fixtureVersion", "fixtureTime", "executionMode")))
        db.commit()

    def ensure_seeded(self):
        with closing(self._connect()) as db:
            count = db.execute("SELECT COUNT(*) FROM fixture_entities").fetchone()[0]
            version = db.execute("SELECT value FROM fixture_metadata WHERE key='fixtureVersion'").fetchone()
            if count and version and version[0] == FIXTURE_VERSION:
                return False
            # Initial setup never deletes anyone's existing planning demo results.
            self._install(db, baseline())
            return True

    def reset(self):
        with closing(self._connect()) as db:
            self._install(db, baseline())
        return self.summary()

    def snapshot(self):
        with closing(self._connect()) as db:
            entities = [json.loads(r[0]) for r in db.execute(
                "SELECT payload FROM fixture_entities ORDER BY id").fetchall()]
            relations = [tuple(r) for r in db.execute(
                "SELECT from_id, relation, to_id FROM fixture_relations ORDER BY from_id, relation, to_id").fetchall()]
            scenarios = [json.loads(r[0]) for r in db.execute(
                "SELECT payload FROM fixture_scenarios ORDER BY scenario_id").fetchall()]
            meta = dict(db.execute("SELECT key, value FROM fixture_metadata").fetchall())
        return {"fixtureVersion": meta.get("fixtureVersion"), "fixtureTime": meta.get("fixtureTime"),
                "executionMode": "FIXTURE", "simulationOnly": True,
                "entities": entities, "relations": relations, "scenarios": scenarios}

    def get_entity(self, entity_id):
        """Read one fixture record by stable ID; None if it does not exist."""
        with closing(self._connect()) as db:
            row = db.execute("SELECT payload FROM fixture_entities WHERE id=?", (entity_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def list_entities(self, kind=None):
        """Read synthetic records for a specialist module; never imply approval."""
        with closing(self._connect()) as db:
            if kind is None:
                rows = db.execute("SELECT payload FROM fixture_entities ORDER BY id").fetchall()
            else:
                rows = db.execute("SELECT payload FROM fixture_entities WHERE kind=? ORDER BY id", (kind,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def summary(self):
        with closing(self._connect()) as db:
            counts = dict(db.execute("SELECT kind, COUNT(*) FROM fixture_entities GROUP BY kind"))
            scenario_rows = db.execute("SELECT payload FROM fixture_scenarios ORDER BY scenario_id").fetchall()
            integrity = db.execute("PRAGMA foreign_key_check").fetchall()
        return {"fixtureVersion": FIXTURE_VERSION, "fixtureTime": FIXTURE_TIME,
                "executionMode": "FIXTURE", "simulationOnly": True,
                "entityCounts": counts, "totalEntities": sum(counts.values()),
                "scenarios": [json.loads(row[0]) for row in scenario_rows],
                "referentialIntegrity": "PASS" if not integrity else "FAIL",
                "notice": "Expected outcomes are test expectations, not executed agent decisions. No live booking, approval or payment."}
