"""Confirmed supplier form fields, not client-supplied identities or approvals."""
import re
from copy import deepcopy
from decimal import Decimal
from jsonschema import Draft202012Validator, FormatChecker
from tripmate.operations.common import safe_text
from .common import SOURCE_FIELDS, extraction_schema, timestamp


def normalise_submission(value):
    if not isinstance(value, dict):
        raise ValueError('Supplier offer must be a structured object')
    fields = set(SOURCE_FIELDS) - {'supplierId'}
    allowed = fields | {'offerReference', 'sourceReference', 'product'}
    if set(value) - allowed:
        raise ValueError('Supplier submission contains unrecognised or protected fields')
    result = deepcopy(value)
    for key in ('offerReference', 'productId'):
        if key not in result or not isinstance(result[key], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}', result[key]):
            raise ValueError('Use a short product and offer reference containing letters, numbers, dot, dash or underscore')
    if not isinstance(result.get('sourceReference'), str) or not 1 <= len(result['sourceReference'].strip()) <= 200:
        raise ValueError('Provide a source document reference')
    result['sourceReference'] = safe_text(result['sourceReference'], 200)
    for key, limit in [('unitBasis', 300), ('cancellationTerms', 500)]:
        if key in result:
            result[key] = safe_text(result[key], limit)
    if 'commercialTerms' in result:
        if not isinstance(result['commercialTerms'], list) or len(result['commercialTerms']) > 20:
            raise ValueError('Supply a bounded list of commercial terms')
        result['commercialTerms'] = [safe_text(term, 500) for term in result['commercialTerms']]
    # Missing source facts may still be confirmed for a recorded B08 refusal.
    # Present fields must have stable wire types; business validity belongs to B08.
    schema = extraction_schema()
    schema['properties'].pop('supplierId')
    schema['required'] = []
    raw = {key: result[key] for key in fields if key in result}
    # Keep unsupported currency as a business failure, not a transport error.
    if 'supplierCost' in raw:
        cost = raw['supplierCost']
        if not isinstance(cost, dict) or set(cost) != {'amount', 'currency'} or not isinstance(cost['currency'], str):
            raise ValueError('Supply a currency and two-decimal cost')
        schema['properties']['supplierCost'] = {'type': 'object', 'properties': {
            'amount': {'type': 'string', 'pattern': r'^-?(0|[1-9][0-9]*)\.[0-9]{2}$'},
            'currency': {'type': 'string', 'minLength': 1}}, 'required': ['amount', 'currency'], 'additionalProperties': False}
    if not Draft202012Validator(schema, format_checker=FormatChecker()).is_valid(raw):
        raise ValueError('Supplier fields have invalid types or timestamp formats')
    if 'product' in result:
        product = result['product']
        if not isinstance(product, dict) or 'sourceIds' in product or 'productId' in product:
            raise ValueError('Service metadata cannot supply internal product or evidence IDs')
        permitted = {'role', 'startAt', 'endAt', 'origin', 'destination', 'partySize', 'accessible',
                     'baggageKg', 'comfort', 'reliability', 'minConnectionMinutes', 'openingStart', 'openingEnd'}
        if set(product) != permitted:
            raise ValueError('Supply the complete service metadata, including nullable opening times')
        if any(not isinstance(product[key], str) for key in ('startAt', 'endAt')):
            raise ValueError('Service times require timezone-aware timestamp strings')
        if (product['role'] not in {'OUTBOUND', 'RETURN', 'STAY', 'ACTIVITY'}
                or type(product['partySize']) is not int or not 1 <= product['partySize'] <= 20
                or type(product['accessible']) is not bool
                or any(type(product[key]) is not int or product[key] < 0 for key in ('baggageKg', 'minConnectionMinutes'))
                or timestamp(product['endAt']) <= timestamp(product['startAt'])):
            raise ValueError('Invalid service interval, capacity or capability fields')
        for key in ('comfort', 'reliability'):
            if not isinstance(product[key], str) or not Decimal(product[key]).is_finite() or not 0 <= Decimal(product[key]) <= 1:
                raise ValueError('Service scores must be decimal strings in 0–1')
        for key in ('origin', 'destination'):
            product[key] = safe_text(product[key], 200)
        if product['role'] == 'ACTIVITY':
            if any(not isinstance(product[key], str) for key in ('openingStart', 'openingEnd')):
                raise ValueError('Activities require evidenced opening times')
            if not timestamp(product['openingStart']) <= timestamp(product['startAt']) < timestamp(product['endAt']) <= timestamp(product['openingEnd']):
                raise ValueError('Activity service must fit its stated opening hours')
        elif product['openingStart'] is not None or product['openingEnd'] is not None:
            raise ValueError('Opening hours apply only to activities')
        result['product'] = product
    return result
