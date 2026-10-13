"""Small, explicit boundary helpers; no generated text makes business decisions."""
import re
from datetime import datetime, timezone
from uuid import uuid4


class OperationsError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier():
    return str(uuid4())


def instant(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timezone required")
    return parsed


def safe_text(value, limit=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise OperationsError("INVALID_CONTRACT", "Supply nonempty text within the stated length limit.")
    # Free text is never a place to collect credentials or personal contacts.
    value = re.sub(r"(?i)(bearer\s+|api[_ -]?key\s*[:=]\s*|password\s*[:=]\s*)\S+", "[REDACTED]", value)
    value = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[CONTACT REDACTED]", value)
    return value.strip()


def source(source_id, timestamp):
    return {"sourceId": source_id, "sourceType": "FIXTURE",
            "sourceReference": "fixture://operations/" + source_id,
            "capturedAt": timestamp, "freshness": "FRESH", "simulated": True}


def envelope(case_id, correlation, sources):
    return {"schemaVersion": "1.0.0", "caseId": case_id, "correlationId": correlation,
            "sourceReferences": sources, "validationResults": [], "errors": [], "requiresApproval": False}


def check(rule, outcome, reason, timestamp, sources):
    return {"ruleId": rule, "ruleVersion": "operations-1.0", "outcome": outcome,
            "reason": reason, "checkedAt": timestamp, "sourceIds": sources}
