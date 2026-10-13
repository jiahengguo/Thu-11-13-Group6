"""B08 policy checks; calculation remains the shared B04 PricingService's job."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from jsonschema import Draft202012Validator, FormatChecker
from tripmate.contracts import schema_bundle, validate


class SupplierError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() is None:
        raise ValueError('Timezone offset required')
    return parsed


def uid(prefix):
    return prefix + '-' + str(uuid4())


def envelope(source):
    return dict(schemaVersion='1.0.0', caseId=source['caseId'],
                correlationId=source['correlationId'],
                sourceReferences=deepcopy(source['sourceReferences']),
                validationResults=[], errors=[], requiresApproval=False)


def subject(offer):
    return dict(subjectType='SupplierOffer', subjectId=offer['offerId'],
                materialVersion=offer['materialVersion'])


def check(rule, at, sources, passed=True, reason='Verified'):
    return dict(ruleId=rule, ruleVersion='supplier-1.0',
                outcome='PASS' if passed else 'FAIL', reason=reason,
                checkedAt=at, sourceIds=list(sources))


SOURCE_FIELDS = ('supplierId', 'productId', 'productType', 'availableQuantity',
                 'quotedQuantity', 'unitBasis', 'supplierCost',
                 'mandatoryChargesIncluded', 'validFrom', 'validUntil',
                 'cancellationTerms', 'commercialTerms')


def extraction_schema():
    bundle = schema_bundle()
    properties = bundle['$defs']['SupplierOffer']['properties']
    return {'$schema': bundle['$schema'], '$defs': bundle['$defs'],
            'type': 'object', 'additionalProperties': False,
            'properties': {key: properties[key] for key in SOURCE_FIELDS},
            'required': list(SOURCE_FIELDS)}


def validate_source(candidate):
    if not isinstance(candidate, dict) or any(key not in candidate for key in SOURCE_FIELDS):
        raise SupplierError('MISSING_REQUIRED_FIELDS', 'Supplier source is missing required fields')
    if not isinstance(candidate['supplierCost'], dict):
        raise SupplierError('OFFER_INVALID', 'Supplier cost must include AUD amount and currency')
    if candidate['supplierCost'].get('currency') != 'AUD':
        raise SupplierError('OFFER_INVALID', 'Only AUD supplier costs are supported')
    validator = Draft202012Validator(extraction_schema(), format_checker=FormatChecker())
    if next(validator.iter_errors(candidate), None):
        raise SupplierError('OFFER_INVALID', 'Source fields do not match the agreed offer contract')


def validate_offer(offer, at):
    validate('SupplierOffer', offer)
    if not timestamp(offer['validFrom']) <= timestamp(at) < timestamp(offer['validUntil']):
        raise SupplierError('OFFER_EXPIRED', 'Offer is outside its validity interval')
    if (offer['availableQuantity'] < offer['quotedQuantity']
            or not offer['mandatoryChargesIncluded']
            or Decimal(offer['supplierCost']['amount']) < 0
            or not offer['unitBasis'].strip() or not offer['cancellationTerms'].strip()):
        raise SupplierError('OFFER_INVALID', 'Stock, cost, quantity basis or mandatory terms are invalid')
    refs = offer['sourceReferences']
    if len({ref['sourceId'] for ref in refs}) != len(refs):
        raise SupplierError('VERIFICATION_FAILED', 'Supplier evidence identifiers must be unique')
    if any(ref['freshness'] != 'FRESH' or timestamp(ref['capturedAt']) > timestamp(at) for ref in refs):
        raise SupplierError('STALE_EVIDENCE', 'Supplier evidence must be fresh and not future-dated')


@dataclass(frozen=True)
class PricingPolicy:
    markup_rate: str
    minimum_margin: str
    version: str

    def __post_init__(self):
        for value in (self.markup_rate, self.minimum_margin):
            number = Decimal(value)
            if not number.is_finite() or number < 0:
                raise ValueError('Pricing policy must be finite and nonnegative')
        if Decimal(self.minimum_margin) != Decimal(self.minimum_margin).quantize(Decimal('.01')) or not self.version:
            raise ValueError('Minimum margin uses AUD cents and policy must be versioned')


def verify_price(offer, price, policy):
    validate('PriceBreakdown', price)
    cost = Decimal(offer['supplierCost']['amount'])
    base = (cost * (1 + Decimal(policy.markup_rate))).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
    minimum = Decimal(policy.minimum_margin)
    identity_ok = (price['offerId'] == offer['offerId']
                   and price['offerVersion'] == offer['materialVersion']
                   and price['supplierCost'] == offer['supplierCost']
                   and price['quotedQuantity'] == offer['quotedQuantity']
                   and price['unitBasis'] == offer['unitBasis']
                   and price['caseId'] == offer['caseId']
                   and price['correlationId'] == offer['correlationId']
                   and price['sourceReferences'] == offer['sourceReferences'])
    arithmetic_ok = (Decimal(price['markupRate']) == Decimal(policy.markup_rate)
                     and price['pricingConfigVersion'] == policy.version
                     and Decimal(price['minimumMargin']['amount']) == minimum
                     and Decimal(price['basePrice']['amount']) == base
                     and Decimal(price['discountAmount']['amount']) == 0
                     and price['memberOfferRuleId'] is None and price['entitlementDecisionId'] is None
                     and Decimal(price['sellingPrice']['amount']) == base
                     and Decimal(price['marginAmount']['amount']) == base - cost
                     and base > 0 and base - cost >= minimum
                     and not price['errors'] and not price['requiresApproval']
                     and price['validationResults']
                     and all(row['outcome'] == 'PASS' for row in price['validationResults']))
    if not identity_ok or not arithmetic_ok:
        raise SupplierError('MARGIN_FAILED', 'Price does not match source cost, configured base policy or minimum margin')
