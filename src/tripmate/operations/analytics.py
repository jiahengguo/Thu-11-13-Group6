"""Optional OPS-O1/O2: deterministic metrics on explicitly supplied simulation records."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .common import OperationsError


def analyse(data):
    required = {"periodStart", "periodEnd", "impressions", "clicks", "costAUD", "leads", "activeAtStart", "activeAtEnd", "qualificationRule"}
    if not isinstance(data, dict) or set(data) != required:
        raise OperationsError("INVALID_CONTRACT", "Supply the complete simulated reporting dataset.")
    try:
        start, end = date.fromisoformat(data["periodStart"]), date.fromisoformat(data["periodEnd"])
        if start > end:
            raise ValueError()
        for k in ("impressions", "clicks"):
            if type(data[k]) is not int or data[k] < 0:
                raise ValueError()
        if data["clicks"] > data["impressions"]:
            raise ValueError()
        cost = Decimal(data["costAUD"])
        if not cost.is_finite() or cost < 0 or cost.as_tuple().exponent < -2 or not isinstance(data["qualificationRule"], str) or not data["qualificationRule"].strip():
            raise ValueError()
        for k in ("activeAtStart", "activeAtEnd"):
            if not isinstance(data[k], list) or any(not isinstance(v, str) or not v for v in data[k]) or len(set(data[k])) != len(data[k]):
                raise ValueError()
        if not isinstance(data["leads"], list):
            raise ValueError()
        ids = set()
        included, missing = [], []
        for lead in data["leads"]:
            if not isinstance(lead, dict) or set(lead) != {"id", "campaignId", "channel", "createdAt", "consent", "qualified", "converted"}:
                raise ValueError()
            if any(not isinstance(lead[k], str) or not lead[k] for k in ("id", "campaignId", "channel")) or lead["id"] in ids:
                raise ValueError()
            ids.add(lead["id"])
            created = date.fromisoformat(lead["createdAt"])
            if any(lead[k] is not None and type(lead[k]) is not bool for k in ("consent", "qualified", "converted")):
                raise ValueError()
            if start <= created <= end:
                if any(lead[k] is None for k in ("consent", "qualified", "converted")):
                    missing.append(lead["id"])
                else:
                    included.append(lead)
    except (ValueError, TypeError, KeyError, ArithmeticError):
        raise OperationsError("INVALID_CONTRACT", "Reporting dates, unique source records and nonnegative counts/costs must be valid.")
    qualified = [x for x in included if x["qualified"]]
    converted = [x for x in qualified if x["converted"]]
    cohort = set(data["activeAtStart"])
    retained = cohort & set(data["activeAtEnd"])
    def ratio(n, d, percentage=True):
        if not d:
            return None
        return str((Decimal(n) / Decimal(d) * (100 if percentage else 1)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return {"simulationOnly": True, "period": [str(start), str(end)], "qualificationRule": data["qualificationRule"],
            "includedLeadIds": [x["id"] for x in included], "missingLeadIds": missing,
            "counts": {"leads": len(included), "qualified": len(qualified), "convertedQualified": len(converted),
                       "startCohort": len(cohort), "retainedSameCohort": len(retained)},
            "metrics": {"clickThroughPercent": ratio(data["clicks"], data["impressions"]),
                        "qualifiedLeadPercent": ratio(len(qualified), len(included)),
                        "qualifiedConversionPercent": ratio(len(converted), len(qualified)),
                        "acquisitionCostAUD": ratio(cost, len(converted), False),
                        "retentionPercent": ratio(len(retained), len(cohort))},
            "assumptions": ["Null metrics mean Not applicable: zero denominator.",
                            "Incomplete leads are excluded and listed; qualification follows the recorded rule.",
                            "Retention uses only the start cohort. Newly acquired customers do not increase retention.",
                            "Recorded associations do not establish causation or statistical significance."]}


def experiment(report):
    enough = report["counts"]["qualified"] > 0 and not report["missingLeadIds"]
    return {"status": "HUMAN_REVIEW_REQUIRED", "simulationOnly": True,
            "evidenceLeadIds": report["includedLeadIds"], "reportingPeriod": report["period"],
            "hypothesis": "A clearer enquiry call to action may improve qualified-lead conversion.",
            "controlCondition": "Keep the current approved simulated enquiry message.",
            "changedVariable": "Call-to-action wording only.", "targetSegment": "Consenting leads matching the recorded qualification rule.",
            "successMetric": "Qualified-lead conversion rate, using the same qualification rule in both groups.",
            "duration": "Proposed 14-day observation window, subject to operator approval.",
            "minimumDataRequirement": "Agree baseline rate, detectable effect and sample size before starting; current records alone do not establish statistical power.",
            "stoppingCondition": "Stop on consent/data-quality issues or the agreed end date; no early success claim without a pre-agreed analysis.",
            "limitation": "Descriptive evidence only; no causal or significance claim." if enough else "Insufficient complete qualified-lead data; collect it before designing a powered experiment.",
            "nextAction": "Operator may use this as input to a UC-08 brief. Supplier owns offer selection, budget evaluation and campaign proposal approval.",
            "published": False, "spendingAuthorised": False}
