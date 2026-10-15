"""Exact money, time, contract envelopes and typed failures."""
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4


class PlanningError(ValueError):
    def __init__(self, code, message, step="planning"):
        super().__init__(message)
        self.code, self.step = code, step


def now():
    return datetime.now(timezone.utc).isoformat()


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("A timezone offset is required")
    return result


def decimal(value):
    if not isinstance(value, (str, Decimal)):
        raise ValueError("Use decimal strings, never binary floats")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("Money and scores must be finite")
    return result


def amount(value):
    if value.get("currency") != "AUD":
        raise ValueError("Only AUD is supported")
    result = decimal(value["amount"])
    if result != result.quantize(Decimal("0.01")):
        raise ValueError("Money must have at most two fractional digits")
    return result


def money(value):
    return {"amount": format(decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), ".2f"), "currency": "AUD"}


def duration(dates):
    days = (date.fromisoformat(dates["endDate"]) - date.fromisoformat(dates["startDate"])).days + 1
    if days < 1:
        raise ValueError("End date precedes start date")
    return days


def envelope(source):
    return {"schemaVersion": "1.0.0", "caseId": source["caseId"],
            "correlationId": source["correlationId"],
            "sourceReferences": deepcopy(source["sourceReferences"]),
            "validationResults": [], "errors": [], "requiresApproval": False}


def check(rule, passed, reason, at, sources=(), unsupported=False):
    return {"ruleId": rule, "ruleVersion": "planning-1.0",
            "outcome": "UNSUPPORTED" if unsupported else "PASS" if passed else "FAIL",
            "reason": reason, "checkedAt": at, "sourceIds": list(sources)}


def subject(version):
    return {"subjectType": "ItineraryVersion", "subjectId": version["versionId"],
            "materialVersion": version["versionNo"]}


def uid(prefix):
    return prefix + "-" + str(uuid4())
