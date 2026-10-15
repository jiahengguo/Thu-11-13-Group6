"""B04 fail-closed complete-plan validation for a bounded domestic prototype."""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from tripmate.contracts import ContractError, validate
from .common import amount, check, duration, now, timestamp
from .pricing import price_errors


def validate_product(product):
    """B03 adapter record; never infer capabilities from a product name or an LLM."""
    required = {"productId", "role", "startAt", "endAt", "origin", "destination", "partySize",
                "accessible", "baggageKg", "comfort", "reliability", "minConnectionMinutes",
                "openingStart", "openingEnd", "sourceIds"}
    if set(product) != required:
        raise ValueError("Product details must match the documented planning adapter record")
    if product["role"] not in {"OUTBOUND", "RETURN", "STAY", "ACTIVITY"}:
        raise ValueError("Unsupported route role; multi-leg transport needs an explicit future adapter")
    if (type(product["partySize"]) is not int or product["partySize"] < 1
            or type(product["accessible"]) is not bool
            or type(product["minConnectionMinutes"]) is not int or product["minConnectionMinutes"] < 0
            or not product["origin"] or not product["destination"] or not product["sourceIds"]):
        raise ValueError("Invalid product capacity, locations, capability or connection data")
    if timestamp(product["endAt"]) <= timestamp(product["startAt"]):
        raise ValueError("Invalid product time interval")
    if not 0 <= Decimal(product["comfort"]) <= 1 or not 0 <= Decimal(product["reliability"]) <= 1:
        raise ValueError("Comfort/reliability must be within 0..1")
    if type(product["baggageKg"]) is not int or product["baggageKg"] < 0:
        raise ValueError("Invalid baggage allowance")
    if product["role"] == "ACTIVITY":
        if not (timestamp(product["openingStart"]) <= timestamp(product["startAt"])
                < timestamp(product["endAt"]) <= timestamp(product["openingEnd"])):
            raise ValueError("Activity is outside evidenced opening hours")
    elif product["openingStart"] is not None or product["openingEnd"] is not None:
        raise ValueError("Opening hours apply only to activities")


class PlanningValidator:
    """Bind request, typed constraints and current supplier snapshot per call/run."""
    def __init__(self, request, quotes, spec, clock=now, daily=None):
        self.request, self.quotes, self.spec, self.clock = request, quotes, spec, clock
        self.daily = daily

    def validate_proposal(self, subject):
        return self.validate_plan(subject)

    def validate_plan(self, version):
        at, results = self.clock(), []

        def record(rule, passed, reason, sources=(), unsupported=False):
            results.append(check(rule, passed, reason, at, sources, unsupported))

        try:
            validate("TravelRequest", self.request)
            validate("ItineraryVersion", version)
            request, spec = self.request, self.spec
            days = duration(request["travelDates"])
            if (set(spec) != {"roundTrip", "constraintBindings"} or type(spec["roundTrip"]) is not bool
                    or not isinstance(spec["constraintBindings"], dict)):
                raise ValueError("Invalid PlanningSpec")
            record("REQUEST_BINDING", all(version[k] == request[k] for k in
                   ["caseId", "correlationId", "travellerId", "requestId", "constraintSetId",
                    "constraintSetVersion", "travelDates", "rankingMode", "baselineVersionId"]),
                   "Version must retain the exact confirmed request identity and constraint snapshot")
            record("CONFIRMED_REQUEST", timestamp(request["confirmedAt"]) <= timestamp(at)
                   and not request["errors"], "Request is confirmed, not future-dated, and has no unresolved errors")
            quote_map = {q["offer"]["offerId"]: q for q in self.quotes}
            if len(quote_map) != len(self.quotes):
                raise ValueError("Duplicate offer IDs in current supplier snapshot")
            sources = {s["sourceId"]: s for s in version["sourceReferences"]}
            record("SOURCE_IDENTITIES", len(sources) == len(version["sourceReferences"]), "Source IDs must be unambiguous")
            record("ITEM_IDENTITIES", len({i["itemId"] for i in version["items"]}) == len(version["items"])
                   and len({i["offerId"] for i in version["items"]}) == len(version["items"]),
                   "A quoted package cannot be reused as multiple billable components")
            products, total = [], Decimal("0")
            for item in version["items"]:
                q = quote_map.get(item["offerId"])
                if q is None:
                    record("OFFER_REFERENCE", False, "Missing current offer " + item["offerId"])
                    continue
                offer, price, product = q["offer"], q["price"], q["product"]
                validate("SupplierOffer", offer)
                validate("PriceBreakdown", price)
                validate_product(product)
                ids = [s["sourceId"] for s in offer["sourceReferences"]]
                products.append(product)
                expected_type = {"OUTBOUND": "TRANSPORT", "RETURN": "TRANSPORT",
                                 "STAY": "ACCOMMODATION", "ACTIVITY": "ACTIVITY"}[product["role"]]
                record("ITEM_BINDING", item["offerVersion"] == offer["materialVersion"]
                       and item["productType"] == offer["productType"] == expected_type
                       and product["productId"] == offer["productId"]
                       and item["priceBreakdownId"] == price["priceBreakdownId"]
                       and item["quotedPrice"] == price["sellingPrice"]
                       and all(item[k] == product[k] for k in ["startAt", "endAt", "origin", "destination"]),
                       "Item must match its product, offer version and price snapshot", ids)
                review = offer["review"] or {}
                record("OFFER_APPROVED", offer["status"] == "APPROVED" and review.get("outcome") == "PASS"
                       and review.get("subject") == {"subjectType": "SupplierOffer", "subjectId": offer["offerId"],
                                                    "materialVersion": offer["materialVersion"]}
                       and not offer["errors"] and not price["errors"]
                       and not offer["requiresApproval"] and not price["requiresApproval"],
                       "Only reviewed unrestricted Approved base offers are supported; restricted offers need shared approval integration", ids)
                record("OFFER_VALIDITY", timestamp(offer["validFrom"]) <= timestamp(at) < timestamp(offer["validUntil"])
                       and timestamp(price["calculatedAt"]) <= timestamp(at),
                       "Quote must be current at validation time", ids)
                evidence = offer["sourceReferences"] + price["sourceReferences"]
                record("EVIDENCE", all(sources.get(s["sourceId"]) == s and s["freshness"] == "FRESH"
                       and timestamp(s["capturedAt"]) <= timestamp(at) for s in evidence)
                       and all(s in ids for s in product["sourceIds"])
                       and set(item["sourceIds"]) == set(ids), "Current provenance must resolve without stale or missing evidence", ids)
                record("AVAILABILITY", offer["availableQuantity"] >= item["quantity"] == offer["quotedQuantity"]
                       and product["partySize"] == request["partySize"],
                       "Inventory and complete-package party size must match; no implicit price scaling", ids)
                errors = price_errors(offer, price)
                record("PRICE", not errors and offer["mandatoryChargesIncluded"], "; ".join(errors) or "Price reconciles on the quoted package basis", ids)
                total += amount(item["quotedPrice"])
                local_start = timestamp(item["startAt"]).astimezone(ZoneInfo("Australia/Sydney")).date()
                local_end = timestamp(item["endAt"]).astimezone(ZoneInfo("Australia/Sydney")).date()
                record("ITEM_DATES", date.fromisoformat(request["travelDates"]["startDate"]) <= local_start
                       <= local_end <= date.fromisoformat(request["travelDates"]["endDate"]),
                       "Item must fall within confirmed Sydney calendar dates", ids)
            if self.daily is not None:
                total += amount(self.daily["additionalCost"])
                results.extend(self.daily["checks"])
            record("TOTAL", amount(version["totalPrice"]) == total, "Total equals package prices plus explicit daily route/meal allowances when enabled")
            record("BUDGET", Decimal("0") <= total <= amount(request["budgetCeiling"]), "Complete total must not exceed confirmed AUD budget")
            roles = {role: [p for p in products if p["role"] == role] for role in ["OUTBOUND", "RETURN", "STAY", "ACTIVITY"]}
            if self.daily is None:
                complete = (len(products) == len(version["items"]) and len(roles["OUTBOUND"]) == 1
                            and len(roles["RETURN"]) == int(spec["roundTrip"])
                            and len(roles["STAY"]) == int(days > 1) and len(roles["ACTIVITY"]) >= 1)
                record("COMPLETENESS", complete, "Need outbound, activity, overnight stay when applicable and requested return")
                if complete:
                    outbound = roles["OUTBOUND"][0]
                    record("ROUTE", outbound["origin"] == request["origin"] and outbound["destination"] == request["destination"],
                           "Outbound must connect confirmed origin and destination")
                    record("OUTBOUND_DATE", timestamp(outbound["startAt"]).astimezone(ZoneInfo("Australia/Sydney")).date().isoformat()
                           == request["travelDates"]["startDate"], "Outbound leaves on the first confirmed date")
                    for p in roles["STAY"] + roles["ACTIVITY"]:
                        record("DESTINATION", p["origin"] == p["destination"] == request["destination"],
                               "Stay/activity must share the evidenced destination; missing transfers are not inferred")
                        record("AFTER_ARRIVAL", (timestamp(p["startAt"]) - timestamp(outbound["endAt"])).total_seconds() / 60
                               >= max(outbound["minConnectionMinutes"], p["minConnectionMinutes"]),
                               "Destination services require the evidenced buffer after arrival")
                    if roles["RETURN"]:
                        back = roles["RETURN"][0]
                        record("RETURN_ROUTE", back["origin"] == request["destination"] and back["destination"] == request["origin"]
                               and timestamp(back["endAt"]).astimezone(ZoneInfo("Australia/Sydney")).date().isoformat() == request["travelDates"]["endDate"],
                               "Return must reach origin on the last confirmed date")
                    if days > 1:
                        stay = roles["STAY"][0]
                        record("STAY_COVERAGE", timestamp(stay["startAt"]).astimezone(ZoneInfo("Australia/Sydney")).date().isoformat() == request["travelDates"]["startDate"]
                               and timestamp(stay["endAt"]).astimezone(ZoneInfo("Australia/Sydney")).date().isoformat() == request["travelDates"]["endDate"],
                               "Stay must cover every requested night")
                        if roles["RETURN"]:
                            back = roles["RETURN"][0]
                            record("STAY_RETURN", (timestamp(back["startAt"]) - timestamp(stay["endAt"])).total_seconds() / 60
                                   >= max(stay["minConnectionMinutes"], back["minConnectionMinutes"]), "Stay ends with enough buffer before return departure")
                # A stay is an accommodation reservation window, not a continuously occupied activity.
                busy = sorted([p for p in products if p["role"] != "STAY"], key=lambda p: timestamp(p["startAt"]))
                for left, right in zip(busy, busy[1:]):
                    gap = (timestamp(right["startAt"]) - timestamp(left["endAt"])).total_seconds() / 60
                    record("SCHEDULE", gap >= max(left["minConnectionMinutes"], right["minConnectionMinutes"]), "No overlap; evidenced connection buffer must pass")
                    record("CONNECTION", left["destination"] == right["origin"], "Every movement must connect; no free implicit airport/hotel transfers")
            ids = [c["constraintId"] for c in request["hardConstraints"]]
            if len(ids) != len(set(ids)) or set(spec["constraintBindings"]) != set(ids):
                raise ValueError("Constraint bindings must exactly match unique confirmed constraint IDs")
            for constraint in request["hardConstraints"]:
                binding = spec["constraintBindings"][constraint["constraintId"]]
                kind, value = constraint["kind"], binding.get("value")
                supported, passed = True, False
                if binding.get("description") != constraint["description"] or set(binding) != {"description", "value"}:
                    supported = False
                elif kind == "BUDGET":
                    passed = value == request["budgetCeiling"] and total <= amount(value)
                elif kind == "DATES":
                    passed = value == request["travelDates"]
                elif kind == "ACCESSIBILITY" and type(value) is bool:
                    passed = not value or all(p["accessible"] for p in products)
                elif kind == "BAGGAGE" and type(value) is int and value >= 0:
                    passed = all(p["baggageKg"] >= value for p in roles["OUTBOUND"] + roles["RETURN"])
                elif kind == "ARRIVAL_TIME" and isinstance(value, str):
                    arrivals = ([timestamp(e['endAt']) for e in self.daily['timeline'] if e['kind'] == 'OUTBOUND']
                                if self.daily is not None else [timestamp(p['endAt']) for p in roles['OUTBOUND']])
                    passed = bool(arrivals) and max(arrivals) <= timestamp(value)
                elif kind == "TRANSFER_LIMIT" and type(value) is int and value >= 0:
                    passed = (self.daily["transfers"] if self.daily is not None else 0) <= value
                elif kind == "OTHER" and self.daily is not None and value == self.daily["policy"]:
                    passed = True
                else:
                    supported = False
                record("CONSTRAINT:" + constraint["constraintId"], passed, "Confirmed " + kind + " evaluated" if supported
                       else "Unsupported or unbound constraint; Operations must clarify its structured meaning", unsupported=not supported)
        except (ContractError, ValueError, KeyError, TypeError, InvalidOperation, OverflowError) as exc:
            record("INVALID_PLANNING_INPUT", False, "Invalid or incomplete planning input: " + str(exc))
        return results
