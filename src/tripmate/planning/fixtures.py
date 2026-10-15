"""Explicit offline fixtures, not implementations of teammates' services."""
from copy import deepcopy

from tripmate.contracts import validate
from .application import PlanningRuntime
from .common import check, envelope, money, subject
from .pricing import DeterministicPricingService
from .repository import PlanningRepository

FIXTURE_TIME = "2026-10-12T10:00:00+11:00"


def source(identifier):
    return {"sourceId": identifier, "sourceType": "FIXTURE", "sourceReference": "fixture://moore-planning/" + identifier,
            "capturedAt": FIXTURE_TIME, "freshness": "FRESH", "simulated": True}


def fixture_request(mode="VALUE", budget="900.00"):
    base = {"caseId": "demo-case", "correlationId": "demo-correlation", "sourceReferences": [source("confirmed-request")]}
    request = envelope(base)
    request.update(requestId="demo-request", travellerId="demo-traveller", origin="Sydney Central", destination="Melbourne Centre",
                   partySize=1, budgetCeiling=money(budget), travelDates={"startDate": "2026-10-20", "endDate": "2026-10-22"},
                   rankingMode=mode, confirmedAt=FIXTURE_TIME, constraintSetId="demo-constraints", constraintSetVersion=1,
                   hardConstraints=[{"constraintId": "budget", "kind": "BUDGET", "description": "Use the confirmed total AUD budget", "confirmed": True}],
                   preferences=[], baselineVersionId=None, confirmedChangedFields=[])
    spec = {"roundTrip": False, "constraintBindings": {"budget": {"description": request["hardConstraints"][0]["description"], "value": deepcopy(request["budgetCeiling"])}}}
    case = envelope(base)
    case.update(caseKind="CUSTOMER", caseType="TRAVEL_PLANNING", externalRequestId="demo-intake", requesterId="demo-traveller",
                requesterType="TRAVELLER", confirmedAt=FIXTURE_TIME, createdAt=FIXTURE_TIME, status="CONFIRMED",
                coordinator="operations", primaryHandler="planning", relatedCaseIds=[], humanRequestCount=0,
                confirmedRequest="Confirmed one-way Sydney to Melbourne, 20–22 October, one traveller; co-located city-centre fixtures.",
                unresolvedQuestions=[], entitlementDecision=None)
    validate("Case", case)
    validate("TravelRequest", request)
    return case, request, spec


def fixture_quotes():
    quotes = []
    rows = [
        ("coach", "OUTBOUND", "120.00", "2026-10-20T06:00:00+11:00", "2026-10-20T16:00:00+11:00", "0.35", "0.85"),
        ("express", "OUTBOUND", "230.00", "2026-10-20T08:00:00+11:00", "2026-10-20T11:00:00+11:00", "0.95", "0.98"),
        ("basic-stay", "STAY", "200.00", "2026-10-20T17:00:00+11:00", "2026-10-22T10:00:00+11:00", "0.45", "0.90"),
        ("comfort-stay", "STAY", "300.00", "2026-10-20T17:00:00+11:00", "2026-10-22T10:00:00+11:00", "0.95", "0.98"),
        ("walk", "ACTIVITY", "40.00", "2026-10-21T10:00:00+11:00", "2026-10-21T12:00:00+11:00", "0.60", "0.95"),
        ("guided-tour", "ACTIVITY", "70.00", "2026-10-21T10:00:00+11:00", "2026-10-21T12:00:00+11:00", "0.95", "0.98"),
    ]
    for name, role, cost, start, end, comfort, reliability in rows:
        o = envelope({"caseId": "demo-case", "correlationId": "demo-correlation", "sourceReferences": [source(name)]})
        o.update(offerId=name, materialVersion=1, supplierId="fixture-supplier", productId=name,
                 productType={"OUTBOUND": "TRANSPORT", "STAY": "ACCOMMODATION", "ACTIVITY": "ACTIVITY"}[role],
                 availableQuantity=10, quotedQuantity=1, unitBasis="complete one-person package including mandatory charges",
                 supplierCost=money(cost), mandatoryChargesIncluded=True, validFrom=FIXTURE_TIME,
                 validUntil="2026-10-20T00:00:00+11:00", cancellationTerms="Simulated: refundable until 24 hours before service.",
                 commercialTerms=["Simulation only; no real supplier commitment."], status="DRAFT",
                 priceBreakdownId=None, review=None, approvalId=None)
        price = DeterministicPricingService("0.10", money("0.00"), "fixture-pricing-1", lambda: FIXTURE_TIME).calculate(o)
        o.update(status="APPROVED", priceBreakdownId=price["priceBreakdownId"],
                 review={"reviewId": "fixture-review-" + name, "subject": {"subjectType": "SupplierOffer", "subjectId": name, "materialVersion": 1},
                         "outcome": "PASS", "reasons": ["Explicit offline fixture approval"], "reviewedAt": FIXTURE_TIME,
                         "policyVersion": "fixture-only-1", "sourceIds": [name]})
        o["validationResults"] = [check("FIXTURE_SUPPLIER", True, "Prepared simulated supplier record", FIXTURE_TIME, [name])]
        p = {"productId": name, "role": role, "startAt": start, "endAt": end,
             "origin": "Sydney Central" if role == "OUTBOUND" else "Melbourne Centre", "destination": "Melbourne Centre",
             "partySize": 1, "accessible": True, "baggageKg": 20, "comfort": comfort, "reliability": reliability,
             "minConnectionMinutes": 30, "openingStart": "2026-10-21T09:00:00+11:00" if role == "ACTIVITY" else None,
             "openingEnd": "2026-10-21T17:00:00+11:00" if role == "ACTIVITY" else None, "sourceIds": [name]}
        validate("SupplierOffer", o)
        quotes.append({"offer": o, "price": price, "product": p})
    return quotes


class FixtureOffers:
    def __init__(self, quotes):
        self.quotes = quotes

    def find_selectable(self, criteria, at):
        return deepcopy(self.quotes)


class FixtureAccess:
    def authorise(self, requester_id, action, target):
        return requester_id == target.get("travellerId") == "demo-traveller"


class FixtureEntitlement:
    def evaluate(self, traveller_id, action, dates):
        return {"travellerId": traveller_id, "action": action, "outcome": "ALLOWED",
                "reason": "Offline paid-member fixture, not B07 production authorisation"}


class FixtureReviewer:
    def review(self, version, evidence, policies):
        passed = bool(version["validationResults"]) and all(r["outcome"] == "PASS" for r in version["validationResults"])
        return {"reviewId": "fixture-review-" + version["versionId"], "subject": subject(version),
                "outcome": "PASS" if passed else "REVISION_REQUIRED", "reasons": ["Offline fixture reviewer; B10 integration pending"],
                "reviewedAt": FIXTURE_TIME, "policyVersion": "fixture-only-1", "sourceIds": [s["sourceId"] for s in evidence]}


def fixture_runtime(mode="VALUE", budget="900.00", database=":memory:"):
    case, request, spec = fixture_request(mode, budget)
    context = {"request": request, "spec": spec}
    runtime = PlanningRuntime(lambda case_id: deepcopy(context), FixtureOffers(fixture_quotes()), FixtureAccess(),
                              FixtureEntitlement(), FixtureReviewer(), PlanningRepository(database), lambda: FIXTURE_TIME)
    return case, context, runtime
