"""B04 shared pricing arithmetic; commercial policy remains owned by Supplier."""
from copy import deepcopy
from decimal import Decimal

from tripmate.contracts import validate
from .common import PlanningError, amount, check, decimal, envelope, money, now, timestamp, uid


class DeterministicPricingService:
    def __init__(self, markup_rate, minimum_margin, config_version, clock=now):
        self.rate = decimal(markup_rate)
        self.minimum = amount(minimum_margin)
        if self.rate < 0 or self.minimum < 0 or not config_version:
            raise ValueError("Pricing policy must be nonnegative and versioned")
        self.config_version, self.clock = config_version, clock

    def calculate(self, offer, discount=None):
        validate("SupplierOffer", offer)
        at = self.clock()
        cost = amount(offer["supplierCost"])
        if cost < 0 or not offer["mandatoryChargesIncluded"]:
            raise PlanningError("OFFER_INVALID", "Negative cost or missing mandatory charges", "pricing")
        reduction = Decimal("0")
        if discount is not None:
            # B17 supplies a verified single rule, not a list of stackable discounts.
            if (not isinstance(discount, dict) or discount.get("approved") is not True
                    or discount.get("eligible") is not True
                    or not discount.get("memberOfferRuleId") or not discount.get("entitlementDecisionId")
                    or offer["offerId"] not in discount.get("offerIds", [])
                    or not timestamp(discount["validFrom"]) <= timestamp(at) < timestamp(discount["validUntil"])):
                raise PlanningError("ENTITLEMENT_DENIED", "Discount requires current verified eligibility", "pricing")
            reduction = amount(discount["amount"])
            if reduction < 0:
                raise PlanningError("OFFER_INVALID", "Discount cannot be negative", "pricing")
        base = amount(money(cost * (1 + self.rate)))
        selling = amount(money(base - reduction))
        margin = selling - cost
        if selling <= 0 or margin < self.minimum:
            raise PlanningError("MARGIN_FAILED", "Rounded selling price fails the configured minimum margin", "pricing")
        result = envelope(offer)
        result.update(priceBreakdownId=uid("price"), offerId=offer["offerId"],
                      offerVersion=offer["materialVersion"], supplierCost=deepcopy(offer["supplierCost"]),
                      markupRate=str(self.rate), basePrice=money(base), discountAmount=money(reduction),
                      sellingPrice=money(selling), marginAmount=money(margin), minimumMargin=money(self.minimum),
                      quotedQuantity=offer["quotedQuantity"], unitBasis=offer["unitBasis"],
                      pricingConfigVersion=self.config_version, calculatedAt=at,
                      memberOfferRuleId=discount["memberOfferRuleId"] if discount else None,
                      entitlementDecisionId=discount["entitlementDecisionId"] if discount else None)
        result["validationResults"] = [check("PRICE_MARGIN", True, "AUD ROUND_HALF_UP; margin verified after rounding", at)]
        validate("PriceBreakdown", result)
        return result


def price_errors(offer, price):
    """Verify received arithmetic without replacing Supplier's configured policy."""
    failures = []
    cost, rate = amount(price["supplierCost"]), decimal(price["markupRate"])
    base = amount(money(cost * (1 + rate)))
    reduction = amount(price["discountAmount"])
    selling = amount(money(base - reduction))
    if (price["offerId"] != offer["offerId"] or price["offerVersion"] != offer["materialVersion"]
            or price["priceBreakdownId"] != offer["priceBreakdownId"]
            or price["quotedQuantity"] != offer["quotedQuantity"] or price["unitBasis"] != offer["unitBasis"]
            or price["supplierCost"] != offer["supplierCost"]):
        failures.append("Quote identity, quantity or cost basis differs from offer")
    if (cost < 0 or reduction < 0 or amount(price["minimumMargin"]) < 0 or selling <= 0
            or amount(price["basePrice"]) != base or amount(price["sellingPrice"]) != selling
            or amount(price["marginAmount"]) != selling - cost
            or selling - cost < amount(price["minimumMargin"])):
        failures.append("Price arithmetic or minimum margin failed")
    # Reusable offers are base quotations. Context-specific discounts require B17 revalidation.
    if reduction != 0 or price["memberOfferRuleId"] is not None or price["entitlementDecisionId"] is not None:
        failures.append("Member quotation needs B17 eligibility revalidation; not supported by base-offer lookup")
    return failures
