"""Module-local simulated input contract; shared v1 envelopes are unchanged."""
from jsonschema import Draft202012Validator, FormatChecker
from tripmate.contracts import schema_bundle, ContractError

TEXT = {"type": "string", "minLength": 1}
MONEY = {"type": "string", "pattern": r"^(0|[1-9][0-9]*)\.[0-9]{2}$"}
TIME = {"type": "string", "format": "date-time"}
IDS = {"type": "array", "items": TEXT, "minItems": 1, "uniqueItems": True}

def obj(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}

def array(item):
    return {"type": "array", "items": item}

ITEM = obj({"itemId": TEXT, "kind": {"enum": ["FLIGHT", "TRANSPORT", "HOTEL", "ACTIVITY"]},
            "origin": TEXT, "destination": TEXT, "startAt": TIME, "endAt": TIME,
            "remainingCost": MONEY, "sourceIds": IDS})
OFFER = obj({"offerId": TEXT, "status": {"enum": ["APPROVED", "PENDING", "EXPIRED"]},
             "available": {"type": "boolean"}, "validUntil": TIME,
             "terms": TEXT, "sourceIds": IDS, "replacement": ITEM})
EVIDENCE = obj({"source": {"$ref": "#/$defs/SourceReference"}, "validUntil": TIME,
                "assertions": array(obj({"key": TEXT, "value": TEXT})), "note": TEXT})
CONTEXT = obj({
    "contextVersion": {"const": "exception-fixture-1"}, "caseId": TEXT, "travellerId": TEXT,
    "simulationOnly": {"const": True}, "assessedAt": TIME,
    "issue": obj({"kind": {"enum": ["DISRUPTION", "COMPLAINT"]}, "itemId": TEXT,
                  "summary": TEXT, "confidence": {"enum": ["SUFFICIENT", "LOW", "UNKNOWN"]},
                  "legalConcern": {"type": "boolean"}, "safetyConcern": {"type": "boolean"},
                  "requestedActions": array({"enum": ["REFUND", "COMPENSATION", "PAYMENT", "BINDING_COMMITMENT"]})}),
    "itinerary": obj({"versionId": TEXT, "materialVersion": {"type": "integer", "minimum": 1},
                      "travellerId": TEXT, "planStatus": {"enum": ["ACTIVE", "PLANNED", "COMPLETED"]},
                      "sunkCost": MONEY, "items": array(ITEM)}),
    "constraints": array(obj({"name": TEXT, "value": TEXT})),
    "evidence": array(EVIDENCE), "supplierOffers": array(OFFER),
    "policies": array(obj({"policyId": TEXT, "version": TEXT, "sourceIds": IDS,
                           "action": {"enum": ["EXPLAIN_AND_APOLOGISE", "HUMAN_REVIEW_REFUND"]},
                           "description": TEXT})),
})
# Optional integration input reuses the project's existing Planning contracts.
CONTEXT['properties']['planningContext'] = obj({
    'request': {'$ref': '#/$defs/TravelRequest'}, 'spec': {'type': 'object'},
    'baseline': {'type': 'object'}})
CONTEXT['properties']['complaintCategory'] = {'enum': ['DELAY', 'ITINERARY', 'SUPPLIER_TERMS']}

def validate_context(value):
    schema = schema_bundle()
    schema["$defs"]["ExceptionContext"] = CONTEXT
    schema["$ref"] = "#/$defs/ExceptionContext"
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value))
    if errors:
        # Do not echo arbitrary submitted content into logs or errors.
        raise ContractError("ExceptionContext: missing or invalid structured fields.")
