"""B09/B13/B14 deterministic candidate construction, ranking and comparison."""
from copy import deepcopy
from decimal import Decimal
from itertools import product

from tripmate.contracts import validate
from .common import PlanningError, amount, decimal, duration, envelope, money, now, timestamp, uid
from .validation import PlanningValidator

SCORING_VERSION = "planning-demo-1.0"
# Versioned prototype weights, not a claim of empirically optimal preference modelling.
PROFILES = {"BUDGET": ("0.80", "0.10", "0.05", "0.05"),
            "VALUE": ("0.40", "0.20", "0.20", "0.20"),
            "COMFORT": ("0.10", "0.15", "0.50", "0.25")}
CHANGE_FIELDS = {"origin", "destination", "partySize", "budgetCeiling", "travelDates",
                 "rankingMode", "hardConstraints", "preferences"}


def metrics(record):
    quotes = record["quotes"]
    transport = [q["product"] for q in quotes if q["product"]["role"] in {"OUTBOUND", "RETURN"}]
    journey = sum((timestamp(p["endAt"]) - timestamp(p["startAt"])).total_seconds() / 60 for p in transport)
    daily = record.get('dailySchedule')
    result = {"cost": record["version"]["totalPrice"], "journeyMinutes": daily['journeyMinutes'] if daily else journey, "transfers": daily['transfers'] if daily else 0,
            "comfort": str(sum(decimal(q["product"]["comfort"]) for q in quotes) / len(quotes)),
            "reliability": str(min(decimal(q["product"]["reliability"]) for q in quotes)),
            "terms": [q["offer"]["cancellationTerms"] for q in quotes],
            "activities": [q["product"]["productId"] for q in quotes if q["product"]["role"] == "ACTIVITY"],
            "accommodation": [q["product"]["productId"] for q in quotes if q["product"]["role"] == "STAY"]}
    if daily:
        limits = daily['policy']['limits']
        load = max((max(Decimal(str(d['walkingMinutes']))/limits['maxWalkingMinutes'], Decimal(str(d['activityMinutes']))/limits['maxActivityMinutes']) for d in daily['days']), default=Decimal('0'))
        result['paceLoad'] = str(load)
        result['productComfort'] = result['comfort']
        result['comfort'] = str(decimal(result['comfort']) * (Decimal('1') - Decimal('0.25') * min(load,Decimal('1'))))
        result['additionalCost'] = daily['additionalCost']
    return result


def compare(baseline, proposal):
    old, new = baseline["version"], proposal["version"]
    old_items = {i["offerId"]: {k: v for k, v in i.items() if k != "itemId"} for i in old["items"]}
    new_items = {i["offerId"]: {k: v for k, v in i.items() if k != "itemId"} for i in new["items"]}
    before, after = metrics(baseline), metrics(proposal)
    old_quotes = {q["offer"]["offerId"]: q for q in baseline["quotes"]}
    new_quotes = {q["offer"]["offerId"]: q for q in proposal["quotes"]}
    refreshed = sorted(k for k in old_quotes.keys() & new_quotes.keys() if old_quotes[k] != new_quotes[k])
    return {"baselineVersionId": old["versionId"], "proposalVersionId": new["versionId"],
            "changedRequirements": {k: {"old": baseline["request"][k], "new": proposal["request"][k]}
                                    for k in sorted(CHANGE_FIELDS) if baseline["request"][k] != proposal["request"][k]},
            "addedOffers": sorted(new_items.keys() - old_items.keys()),
            "removedOffers": sorted(old_items.keys() - new_items.keys()),
            "changedOffers": sorted(k for k in old_items.keys() & new_items.keys() if old_items[k] != new_items[k]),
            "unchangedOffers": sorted(k for k in old_items.keys() & new_items.keys() if old_items[k] == new_items[k]),
            "costDelta": money(amount(new["totalPrice"]) - amount(old["totalPrice"])),
            "journeyMinutesDelta": after["journeyMinutes"] - before["journeyMinutes"],
            "baselineMetrics": before, "proposalMetrics": after,
            "baselineSources": deepcopy(old["sourceReferences"]), "proposalSources": deepcopy(new["sourceReferences"]),
            "scopeChanged": any(baseline["request"][k] != proposal["request"][k] for k in ["partySize", "travelDates", "origin", "destination"]),
            "dataRefresh": bool(refreshed), "refreshedSharedOffers": refreshed,
            "notComparableOfferIds": sorted(old_quotes.keys() ^ new_quotes.keys()),
            "attribution": "Requirement changes and supplier snapshots are shown separately; causal price attribution is not inferred."}


def validate_revision(request, baseline):
    original = baseline["request"]
    if request["baselineVersionId"] != baseline["version"]["versionId"] or request["travellerId"] != original["travellerId"]:
        raise PlanningError("ACCESS_DENIED", "Revision baseline identity does not match", "revision")
    changed = {k for k in CHANGE_FIELDS if request[k] != original[k]}
    if not changed or changed != set(request["confirmedChangedFields"]):
        raise PlanningError("UNCONFIRMED_REQUEST", "Confirm the exact changed fields; unchanged requests create no new version", "revision")
    if (timestamp(request["confirmedAt"]) < timestamp(original["confirmedAt"])
            or request["constraintSetVersion"] <= original["constraintSetVersion"]):
        raise PlanningError("UNCONFIRMED_REQUEST", "Revision requires a new confirmed constraint snapshot", "revision")


class PlanningEngine:
    def __init__(self, clock=now, max_candidates=256):
        self.clock, self.max_candidates = clock, max_candidates

    def generate(self, request, quotes, spec, baseline=None):
        validate("TravelRequest", request)
        if baseline:
            validate_revision(request, baseline)
            if spec["roundTrip"] != baseline["spec"]["roundTrip"]:
                raise PlanningError("UNCONFIRMED_REQUEST", "Route topology changes need an extended confirmed contract", "revision")
            for key, binding in spec["constraintBindings"].items():
                constraint = next((c for c in request["hardConstraints"] if c["constraintId"] == key), None)
                old_binding = baseline["spec"]["constraintBindings"].get(key)
                if old_binding != binding and "hardConstraints" not in request["confirmedChangedFields"]:
                    bound_field = {"BUDGET": "budgetCeiling", "DATES": "travelDates"}.get(constraint["kind"] if constraint else "")
                    if bound_field not in request["confirmedChangedFields"]:
                        raise PlanningError("UNCONFIRMED_REQUEST", "Constraint meaning changed without confirmation", "revision")
        elif request["baselineVersionId"] is not None:
            raise PlanningError("MISSING_REQUIRED_FIELDS", "A revision requires its retrievable baseline", "revision")
        if duration(request["travelDates"]) == 1 and not spec["roundTrip"]:
            raise PlanningError("UNSUPPORTED_CONSTRAINT", "One-way day trips need a shared v1 schema clarification: feasible versions currently require three items", "generation")
        groups = [[q for q in quotes if q["product"]["role"] == "OUTBOUND"]]
        if duration(request["travelDates"]) > 1:
            groups.append([q for q in quotes if q["product"]["role"] == "STAY"])
        groups.append([q for q in quotes if q["product"]["role"] == "ACTIVITY"])
        if spec["roundTrip"]:
            groups.append([q for q in quotes if q["product"]["role"] == "RETURN"])
        count = 1
        for group in groups:
            count *= len(group)
        if count > self.max_candidates:
            raise PlanningError("TOOL_UNAVAILABLE", "Candidate limit exceeded; narrow the inventory explicitly", "generation")
        if not count:
            raise PlanningError("NO_FEASIBLE_ITINERARY", "Inventory lacks required transport, stay or activity", "generation")
        valid, excluded = [], []
        at, plan_id = self.clock(), baseline["version"]["planId"] if baseline else uid("plan")
        for combo in product(*groups):
            version = envelope(request)
            source_map = {s["sourceId"]: deepcopy(s) for s in request["sourceReferences"]}
            for q in combo:
                for s in q["offer"]["sourceReferences"] + q["price"]["sourceReferences"]:
                    if s["sourceId"] in source_map and source_map[s["sourceId"]] != s:
                        raise PlanningError("STALE_EVIDENCE", "Conflicting source IDs in supplier snapshot", "generation")
                    source_map[s["sourceId"]] = deepcopy(s)
            version["sourceReferences"] = list(source_map.values())
            version.update(planId=plan_id, travellerId=request["travellerId"], versionId=uid("version"),
                           versionNo=baseline["version"]["versionNo"] + 1 if baseline else 1,
                           baselineVersionId=request["baselineVersionId"], createdAt=at,
                           assessmentState="DRAFT", planStatus="DRAFT", rankingMode=request["rankingMode"],
                           requestId=request["requestId"], constraintSetId=request["constraintSetId"],
                           constraintSetVersion=request["constraintSetVersion"], travelDates=deepcopy(request["travelDates"]),
                           items=[], totalPrice=money("0"), assumptions=["Bounded direct-route prototype; one activity and one full-stay package; all quoted costs include mandatory charges."],
                           tradeOffs=[], exclusionReasons=[], review=None, approvalId=None)
            for q in combo:
                o, p, detail = q["offer"], q["price"], q["product"]
                version["items"].append({"itemId": uid("item"), "productType": o["productType"], "offerId": o["offerId"],
                    "offerVersion": o["materialVersion"], "priceBreakdownId": p["priceBreakdownId"],
                    **{k: detail[k] for k in ["startAt", "endAt", "origin", "destination"]},
                    "quantity": o["quotedQuantity"], "quotedPrice": deepcopy(p["sellingPrice"]),
                    "sourceIds": [s["sourceId"] for s in o["sourceReferences"]]})
            version["totalPrice"] = money(sum((amount(i["quotedPrice"]) for i in version["items"]), Decimal("0")))
            version["validationResults"] = PlanningValidator(request, quotes, spec, self.clock).validate_plan(version)
            failed = [r for r in version["validationResults"] if r["outcome"] != "PASS"]
            if failed:
                excluded.append({"offerIds": [q["offer"]["offerId"] for q in combo], "checks": failed})
                continue
            version["assessmentState"] = "FEASIBLE"
            validate("ItineraryVersion", version)
            record = {"version": version, "request": deepcopy(request), "spec": deepcopy(spec), "quotes": deepcopy(list(combo))}
            record["metrics"] = metrics(record)
            valid.append(record)
        self.rank(valid, request["rankingMode"])
        for record in valid:
            if baseline:
                record["comparison"] = compare(baseline, record)
        return valid, excluded

    @staticmethod
    def rank(records, mode):
        if not records:
            return
        weights = [decimal(w) for w in PROFILES[mode]]
        costs = [amount(r["version"]["totalPrice"]) for r in records]
        times = [Decimal(str(r["metrics"]["journeyMinutes"])) for r in records]

        def benefit(value, values):
            return (max(values) - value) / (max(values) - min(values)) if max(values) != min(values) else Decimal("1")

        for r, cost, travel in zip(records, costs, times):
            measures = [benefit(cost, costs), benefit(travel, times), decimal(r["metrics"]["comfort"]), decimal(r["metrics"]["reliability"])]
            r["ranking"] = {"mode": mode, "configVersion": 'daily-1' if 'dailySchedule' in r else SCORING_VERSION,
                            "weights": dict(zip(["cost", "journeyTime", "comfort", "reliability"], map(str, weights))),
                            "score": str(sum(w * x for w, x in zip(weights, measures)))}
            r["version"]["tradeOffs"] = [f"{mode}: AUD {cost:.2f}; transport {travel} minutes; comfort {r['metrics']['comfort']}; reliability {r['metrics']['reliability']}. No advertising input is used."]
        records.sort(key=lambda r: (-decimal(r["ranking"]["score"]), amount(r["version"]["totalPrice"]),
                                   tuple(i["offerId"] for i in r["version"]["items"])))
