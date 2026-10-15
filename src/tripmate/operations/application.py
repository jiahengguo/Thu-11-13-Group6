"""UC-05 coordinator. Local simulated identities are explicit, not production login.

Specialists, Planning storage/adoption and a shared Reviewer are injected ports.
Absent dependencies never fabricate a completed workflow.
"""
import hashlib
import json
from copy import deepcopy
from decimal import Decimal
from threading import BoundedSemaphore, RLock, Thread

from jsonschema import Draft202012Validator, FormatChecker

from tripmate.contracts import ContractError, schema_bundle, validate
from .common import OperationsError, check, envelope, identifier, instant, now, safe_text, source
from .rules import AccessService, Entitlements

ROUTES = {"TRAVEL_PLANNING": "planning", "PLAN_REVISION": "planning",
          "DISRUPTION": "exception", "COMPLAINT": "exception",
          "SUPPLIER_COOPERATION": "supplier", "INVENTORY": "supplier",
          "OFFER": "supplier", "PRICE_NEGOTIATION": "supplier",
          "MEMBERSHIP": "operations", "ROUTINE_ENQUIRY": "operations"}
SUPPLIER_TYPES = {k for k, v in ROUTES.items() if v == "supplier"}
TRAVEL_FIELDS = {"origin", "destination", "partySize", "budgetCeiling", "travelDates", "rankingMode",
                 "preferences", "constraints", "roundTrip", "baselineVersionId"}
REQUIRED = {k: ["details"] for k in ROUTES}
REQUIRED.update(TRAVEL_PLANNING=["origin", "destination", "partySize", "budgetCeiling", "travelDates", "rankingMode"],
                PLAN_REVISION=["origin", "destination", "partySize", "budgetCeiling", "travelDates", "rankingMode", "baselineVersionId"],
                DISRUPTION=["planId", "details"], COMPLAINT=["planId", "details"])
APPROVED_SERVICE_INFO = "TripMate provides simulated Australian domestic travel proposals. Plans require confirmation and review. This prototype does not book, pay, refund or sign contracts. Free membership allows two Planned/Active trips, each up to five calendar days."


def extraction_schema():
    primitives = schema_bundle()["$defs"]
    text = {"type": "string", "minLength": 1, "maxLength": 1000}
    travel = {"origin": text, "destination": text, "partySize": {"type": "integer", "minimum": 1, "maximum": 20},
              "budgetCeiling": {"$ref": "#/$defs/Money"}, "travelDates": {"$ref": "#/$defs/DateRange"},
              "rankingMode": {"enum": ["VALUE", "COMFORT", "BUDGET"]}, "roundTrip": {"type": "boolean"},
              "preferences": {"type": "array", "maxItems": 12, "items": text}, "baselineVersionId": text,
              "constraints": {"type": "array", "maxItems": 12, "items": {"type": "object",
                  "properties": {"kind": {"enum": ["ACCESSIBILITY", "BAGGAGE", "TRANSFER_LIMIT", "ARRIVAL_TIME"]},
                                 "value": {"type": ["boolean", "integer", "string"]}, "description": text},
                  "required": ["kind", "value", "description"], "additionalProperties": False}}}
    alternatives = []
    for kind in ROUTES:
        properties = travel if kind in {"TRAVEL_PLANNING", "PLAN_REVISION"} else {"details": text, "planId": text, "feature": text, "memberOfferRuleId": text}
        alternatives.append({"type": "object", "properties": {"caseType": {"const": kind},
                           "fields": {"type": "object", "properties": properties, "additionalProperties": False,
                                      "description": "Extract only explicitly supplied facts. Omit unknown fields; Operations asks for missing required information."}},
                           "required": ["caseType", "fields"], "additionalProperties": False})
    return {"type": "object", "$defs": {k: primitives[k] for k in ("Money", "DateRange")},
            "properties": {"intents": {"type": "array", "minItems": 1, "maxItems": 4, "items": {"oneOf": alternatives}},
                           "confidence": {"type": "number", "minimum": 0, "maximum": 1}},
            "required": ["intents", "confidence"], "additionalProperties": False}


def validate_fragment(name, value):
    bundle = schema_bundle()
    bundle["$ref"] = "#/$defs/" + name
    if not Draft202012Validator(bundle, format_checker=FormatChecker()).is_valid(value):
        raise OperationsError("INVALID_CONTRACT", "The shared " + name + " contract was not satisfied.")


class OperationsService:
    def __init__(self, repository, fixtures, clock=now, llm=None, specialists=None,
                 planning_repository=None, adopt=None, reviewer=None, dependency_timeout=30, seed_profiles=True):
        self.repository, self.fixtures, self.clock = repository, fixtures, clock
        self.llm, self.specialists = llm, specialists or {}
        self.planning_repository, self.adopt, self.reviewer = planning_repository, adopt, reviewer
        if not 0 < dependency_timeout <= 60:
            raise ValueError("Dependency timeout must be between zero and sixty seconds")
        self.dependency_timeout = dependency_timeout
        self.dependency_slot = BoundedSemaphore(1)
        self.adoption_lock = RLock()
        self.access = AccessService(self.profile)
        self.entitlement = Entitlements(self.profile, self.trips, clock)
        if seed_profiles:
            self._seed_profiles()

    def _dependency(self, operation):
        """Bound waiting without retrying a timed-out, possibly still-running task.

Late specialist writes may create internal proposals, but the caller case cannot
release them. One running dependency per coordinator prevents unbounded threads.
"""
        if not self.dependency_slot.acquire(blocking=False):
            raise OperationsError("TOOL_UNAVAILABLE", "A previous dependency is still running; request human assistance.")
        box = {}
        def run():
            try:
                box["value"] = operation()
            except Exception as exc:
                box["error"] = exc
            finally:
                self.dependency_slot.release()
        worker = Thread(target=run, daemon=True)
        worker.start()
        worker.join(self.dependency_timeout)
        if worker.is_alive():
            raise TimeoutError("Dependency deadline reached")
        if "error" in box:
            raise box["error"]
        return box["value"]

    def _seed_profiles(self):
        # New fixture evidence is explicitly owned by Operations. B03 is unchanged.
        with self.repository.transaction() as records:
            for e in self.fixtures.list_entities("TRAVELLER"):
                if not records.get("profile", e["id"]):
                    p = e["data"]
                    records.put("profile", e["id"], {"id": e["id"], "role": "TRAVELLER", "verified": p["verified"],
                                "membership": p["membership"], "paidUntil": "2026-10-30T00:00:00+11:00" if p["membership"] == "PAID" else None,
                                "simulated": True})
            for role, key in [("SUPPLIER", "supplier:fixture-supplier"), ("OPERATOR", "operator:fixture")]:
                if not records.get("profile", key):
                    records.put("profile", key, {"id": key, "role": role, "verified": True, "simulated": True})

    def profile(self, actor):
        return self.repository.read("profile", actor)

    def trips(self, actor):
        snapshot = self.fixtures.snapshot()
        owners = {src for src, rel, dest in snapshot["relations"] if rel == "traveller" and dest == actor}
        case_ids = {e["id"] for e in snapshot["entities"] if e["kind"] == "CASE" and e["id"] in owners}
        owners |= {src for src, rel, dest in snapshot["relations"] if rel == "case" and dest in case_ids}
        plans = {e["id"]: {"planId": e["id"], "planStatus": e["data"]["status"]}
                 for e in snapshot["entities"] if e["kind"] == "ITINERARY" and e["id"] in owners}
        plans.update({p["planId"]: p for p in self.repository.list("lifecycle") if p["travellerId"] == actor})
        if self.planning_repository is not None:
            for rec in self.repository.list("case"):
                if rec["case"]["requesterId"] == actor and rec.get("planId"):
                    plans[rec["planId"]] = self.planning_repository.lifecycle(rec["planId"])
        return list(plans.values())

    def identities(self):
        return [{"id": p["id"], "role": p["role"], "verified": p["verified"], "simulated": True}
                for p in self.repository.list("profile")]

    def _command(self, actor, action, key, body, callback):
        command_key, fingerprint = self._command_identity(actor, action, key, body)
        return self.repository.command(command_key, fingerprint, callback)

    @staticmethod
    def _command_identity(actor, action, key, body):
        if not isinstance(key, str) or not 1 <= len(key) <= 100:
            raise OperationsError("INVALID_CONTRACT", "An operation ID is required for safe retries.")
        fingerprint = hashlib.sha256(json.dumps([actor, action, body], sort_keys=True).encode()).hexdigest()
        return actor + ":" + action + ":" + key, fingerprint

    def _event(self, records, rec, event_type, summary, result="SUCCESS", actor="operations", approval_id=None):
        case = rec.get("case")
        subject_id = case["caseId"] if case else rec["id"]
        sources = rec["sources"]
        event = envelope(subject_id if case else None, rec["correlationId"], sources)
        event.update(eventId=identifier(), runId=rec.get("runId"), timestamp=self.clock(), actor=actor,
                     eventType=event_type, subject={"subjectType": "Case" if case else "ExternalRequest",
                     "subjectId": subject_id, "materialVersion": rec["revision"]},
                     parentEventId=rec.get("lastEventId"), executionMode="FIXTURE", summary=summary,
                     result=result, approvalId=approval_id)
        event["requiresApproval"] = case["requiresApproval"] if case else False
        event["validationResults"] = deepcopy(case["validationResults"]) if case else []
        event["errors"] = deepcopy(case["errors"]) if case else []
        snapshot = {k: deepcopy(rec[k]) for k in ("id", "revision", "case", "fields", "intents", "questions", "state", "campaignId", "sourceChannel", "membershipSnapshots", "responseVersion") if k in rec}
        records.put("history", event["eventId"], snapshot)
        event["sourceReferences"] = deepcopy(sources) + [source("history:" + event["eventId"], self.clock())]
        records.trace(event)
        rec["lastEventId"] = event["eventId"]

    def _save(self, records, rec, kind="case"):
        if kind == "case":
            validate("Case", rec["case"])
        records.put(kind, rec["id"], rec)

    def _owned(self, records, actor, case_id, action="READ_CASE", revision=None):
        rec = records.get("case", case_id)
        if not rec or not self.access.authorise(actor, action, rec["case"]):
            raise OperationsError("ACCESS_DENIED", "This case is unavailable to this identity.")
        if revision is not None and revision != rec["revision"]:
            raise OperationsError("UNCONFIRMED_REQUEST", "This case changed. Reload and confirm the current version.")
        return rec

    def _intake_owned(self, records, actor, intake_id):
        rec = records.get("intake", intake_id)
        if not rec or rec["requesterId"] != actor:
            raise OperationsError("ACCESS_DENIED", "This intake is unavailable to this identity.")
        return rec

    def _normalise(self, actor, intents):
        if not isinstance(intents, list) or not 1 <= len(intents) <= 4:
            raise OperationsError("INVALID_CONTRACT", "Supply one to four independent request intents.")
        profile = self.profile(actor)
        if not profile:
            raise OperationsError("ACCESS_DENIED", "The requester identity is unavailable.")
        output = []
        for intent in intents:
            if not isinstance(intent, dict) or set(intent) != {"caseType", "fields"} or intent["caseType"] not in ROUTES:
                raise OperationsError("INVALID_CONTRACT", "Unknown request category or fields.")
            kind, fields = intent["caseType"], deepcopy(intent["fields"])
            if (kind in SUPPLIER_TYPES) != (profile["role"] == "SUPPLIER") or profile["role"] == "OPERATOR":
                raise OperationsError("ACCESS_DENIED", "The request category does not match the requester role.")
            allowed = TRAVEL_FIELDS if kind in {"TRAVEL_PLANNING", "PLAN_REVISION"} else {"details", "planId", "feature", "memberOfferRuleId"}
            if kind in SUPPLIER_TYPES:
                allowed = allowed | {'supplierOffer'}
            if not isinstance(fields, dict) or set(fields) - allowed:
                raise OperationsError("INVALID_CONTRACT", "Unexpected structured request fields.")
            if 'supplierOffer' in fields:
                from tripmate.supplier.intake import normalise_submission
                try:
                    fields['supplierOffer'] = normalise_submission(fields['supplierOffer'])
                except ValueError as exc:
                    raise OperationsError('INVALID_CONTRACT', str(exc)) from None
            for k in {"origin", "destination", "details", "baselineVersionId", "planId"} & fields.keys():
                fields[k] = safe_text(fields[k], 1000)
            if "preferences" in fields:
                if not isinstance(fields["preferences"], list) or len(fields["preferences"]) > 12:
                    raise OperationsError("INVALID_CONTRACT", "Preferences must be a short list.")
                fields["preferences"] = [safe_text(p, 250) for p in fields["preferences"]]
            if "partySize" in fields and (type(fields["partySize"]) is not int or not 1 <= fields["partySize"] <= 20):
                raise OperationsError("INVALID_CONTRACT", "Party size must be an integer from 1 to 20.")
            if "budgetCeiling" in fields:
                validate_fragment("Money", fields["budgetCeiling"])
                if Decimal(fields["budgetCeiling"]["amount"]) <= 0:
                    raise OperationsError("INVALID_CONTRACT", "Budget must be positive AUD.")
            if "travelDates" in fields:
                validate_fragment("DateRange", fields["travelDates"])
                if fields["travelDates"]["endDate"] < fields["travelDates"]["startDate"]:
                    raise OperationsError("INVALID_CONTRACT", "End date must not precede start date.")
            if "rankingMode" in fields and fields["rankingMode"] not in {"VALUE", "COMFORT", "BUDGET"}:
                raise OperationsError("INVALID_CONTRACT", "Choose Value, Comfort or Budget.")
            if "roundTrip" in fields and type(fields["roundTrip"]) is not bool:
                raise OperationsError("INVALID_CONTRACT", "Round trip must be a boolean.")
            constraints = fields.get("constraints", [])
            if not isinstance(constraints, list) or len(constraints) > 12:
                raise OperationsError("INVALID_CONTRACT", "Supply at most twelve typed constraints.")
            for c in constraints:
                if not isinstance(c, dict) or set(c) != {"kind", "value", "description"}:
                    raise OperationsError("INVALID_CONTRACT", "Each constraint needs kind, typed value and description.")
                c["description"] = safe_text(c["description"], 250)
                k, v = c["kind"], c["value"]
                valid = ((k == "ACCESSIBILITY" and type(v) is bool) or
                         (k in {"BAGGAGE", "TRANSFER_LIMIT"} and type(v) is int and v >= 0) or
                         (k == "ARRIVAL_TIME" and isinstance(v, str)))
                if k == 'OTHER' and isinstance(v, dict) and v.get('version') == 'daily-1':
                    from tripmate.planning.daily import validate_policy
                    try:
                        validate_policy(v, fields.get('travelDates'))
                        valid = True
                    except ValueError:
                        raise OperationsError('INVALID_CONTRACT', 'Invalid confirmed daily planning policy.') from None
                if not valid:
                    raise OperationsError("UNSUPPORTED_CONSTRAINT", "This constraint has no supported deterministic binding.")
                if k == "ARRIVAL_TIME":
                    try:
                        instant(v)
                    except ValueError:
                        raise OperationsError("INVALID_CONTRACT", "Arrival time requires an ISO timestamp with timezone.")
            if len({c["kind"] for c in constraints}) != len(constraints):
                raise OperationsError("INVALID_CONTRACT", "Duplicate constraint kinds are not supported.")
            output.append({"caseType": kind, "fields": fields})
        return output

    @staticmethod
    def _missing(intents):
        return [f"Request {i+1}: please supply {k}." for i, x in enumerate(intents)
                for k in REQUIRED[x["caseType"]] if k not in x["fields"]]

    def _require_affected_plan(self, actor, intent):
        if intent["caseType"] not in {"DISRUPTION", "COMPLAINT"}:
            return
        plan = next((p for p in self.trips(actor) if p["planId"] == intent["fields"]["planId"]), None)
        if not plan or (intent["caseType"] == "DISRUPTION" and plan["planStatus"] != "ACTIVE"):
            raise OperationsError("ACCESS_DENIED", "The affected trip is unavailable to this traveller or is not active for disruption recovery.")

    def intake(self, actor, key, text, intents=None, campaign_id=None, channel="LOCAL", consent=False):
        profile = self.profile(actor)
        if not profile:
            raise OperationsError("ACCESS_DENIED", "Choose an available simulated identity.")
        text = safe_text(text)
        request_body = [text, intents, campaign_id, channel, consent]
        cached, value = self.repository.cached(*self._command_identity(actor, "intake", key, request_body))
        if cached:
            return value
        if channel not in {"LOCAL", "SIMULATED_CAMPAIGN"} or type(consent) is not bool:
            raise OperationsError("INVALID_CONTRACT", "Unsupported source channel or consent value.")
        if campaign_id is not None:
            campaign = self.repository.read("campaign", campaign_id)
            if not campaign or campaign.get("approved") is not True or channel != "SIMULATED_CAMPAIGN":
                raise OperationsError("ACCESS_DENIED", "A campaign response must reference an approved simulated campaign.")
        extraction = "MANUAL_FIXTURE"
        confidence = 1.0 if intents else 0.0
        if intents is None and self.llm is not None and profile.get("verified"):
            schema = extraction_schema()
            try:
                extracted = self._dependency(lambda: self.llm.extract(text, schema))
                if not Draft202012Validator(schema).is_valid(extracted):
                    raise ValueError("Invalid extraction")
                intents, confidence = extracted["intents"], extracted["confidence"]
                extraction = "LIVE_MODEL_UNCONFIRMED"
            except Exception:
                # Never save raw model/adapter exceptions or fall back as success.
                extraction = "MODEL_FAILED"
        try:
            normalised = self._normalise(actor, intents) if intents else []
        except OperationsError:
            if extraction != "LIVE_MODEL_UNCONFIRMED":
                raise
            normalised, confidence, extraction = [], 0.0, "MODEL_FAILED"
        timestamp, intake_id = self.clock(), identifier()
        def create(records):
            rec = {"id": intake_id, "requesterId": actor, "requesterType": profile["role"],
                   "correlationId": identifier(), "revision": 1, "createdAt": timestamp,
                   "sources": [source("intake:" + intake_id, timestamp)], "text": text,
                   "intents": normalised, "confidence": confidence, "extraction": extraction,
                   "questions": self._missing(normalised) if normalised else ["Please identify and confirm your request category."],
                   "state": "AWAITING_CONFIRMATION" if profile.get("verified") else "AWAITING_VERIFICATION",
                   "humanRequestCount": 0, "campaignId": campaign_id, "sourceChannel": channel,
                   "consent": consent, "caseIds": []}
            if confidence < 0.7:
                rec["questions"].append("Please clarify the request intent before confirmation.")
            self._event(records, rec, "INTAKE", "External intake recorded; extracted information is unconfirmed.", "PENDING", actor)
            self._save(records, rec, "intake")
            if campaign_id:
                records.put("lead", intake_id, {"leadId": intake_id, "campaignId": campaign_id,
                            "sourceChannel": channel, "createdAt": timestamp, "consent": consent,
                            "qualificationStatus": "UNASSESSED", "conversionStatus": "UNASSESSED", "simulated": True})
            return rec
        return self._command(actor, "intake", key, request_body, create)

    def confirm(self, actor, key, intake_id, revision, intents, confirmed):
        if confirmed is not True:
            raise OperationsError("UNCONFIRMED_REQUEST", "Explicitly confirm the complete summary and any intent split.")
        intents = self._normalise(actor, intents)
        questions = self._missing(intents)
        if questions:
            raise OperationsError("MISSING_REQUIRED_FIELDS", " ".join(questions))
        def commit(records):
            intake = self._intake_owned(records, actor, intake_id)
            if revision != intake["revision"] or intake["state"] not in {"AWAITING_CONFIRMATION", "AWAITING_VERIFICATION"}:
                raise OperationsError("UNCONFIRMED_REQUEST", "Reload the current intake before confirming.")
            if not self.profile(actor).get("verified"):
                raise OperationsError("VERIFICATION_FAILED", "Identity is unverified; no protected case is created.")
            ids = [identifier() for _ in intents]
            for case_id, intent in zip(ids, intents):
                self._require_affected_plan(actor, intent)
                timestamp = self.clock()
                case = envelope(case_id, intake["correlationId"], deepcopy(intake["sources"]))
                case.update(caseKind="SUPPLIER" if intent["caseType"] in SUPPLIER_TYPES else "CUSTOMER",
                            caseType=intent["caseType"], externalRequestId=intake_id, requesterId=actor,
                            requesterType=intake["requesterType"], confirmedAt=timestamp, createdAt=timestamp,
                            status="CONFIRMED", coordinator="operations", primaryHandler=None,
                            relatedCaseIds=[i for i in ids if i != case_id], humanRequestCount=intake["humanRequestCount"],
                            confirmedRequest=json.dumps(intent, sort_keys=True), unresolvedQuestions=[], entitlementDecision=None)
                rec = {"id": case_id, "revision": 1, "case": case, "correlationId": case["correlationId"],
                       "sources": case["sourceReferences"], "fields": intent["fields"], "response": None,
                       "responseVersion": 0, "review": None, "approvalId": None, "dispatchStarted": False,
                       "deliveryAttempts": 0, "campaignId": intake["campaignId"], "sourceChannel": intake["sourceChannel"]}
                if intent["caseType"] in {"TRAVEL_PLANNING", "PLAN_REVISION"}:
                    rec["context"] = self._planning_context(rec)
                if case["humanRequestCount"] >= 2:
                    case["status"] = "HUMAN_ASSISTANCE"
                self._event(records, rec, "CONFIRMATION", "Requester confirmed the complete structured summary and related-case split.", actor=actor)
                self._save(records, rec)
            intake.update(intents=intents, caseIds=ids, state="CONFIRMED", revision=intake["revision"]+1, questions=[])
            self._event(records, intake, "CONFIRMATION", "Confirmed intake created linked cases.", actor=actor)
            self._save(records, intake, "intake")
            return {"caseIds": ids, "intakeId": intake_id}
        return self._command(actor, "confirm", key, [intake_id, revision, intents, confirmed], commit)

    def _planning_context(self, rec):
        c, f = rec["case"], rec["fields"]
        request = envelope(c["caseId"], c["correlationId"], c["sourceReferences"])
        baseline = None
        if c["caseType"] == "PLAN_REVISION":
            if self.planning_repository is None:
                raise OperationsError("TOOL_UNAVAILABLE", "Planning storage must be integrated before confirming a revision.")
            baseline = self.planning_repository.get_version(f["baselineVersionId"])
            if not baseline or not self.access.authorise(c["requesterId"], "READ_PLAN", baseline["version"]):
                raise OperationsError("ACCESS_DENIED", "The revision baseline is unavailable to this traveller.")
        request.update(requestId=identifier(), travellerId=c["requesterId"], origin=f["origin"], destination=f["destination"],
                       partySize=f["partySize"], budgetCeiling=f["budgetCeiling"], travelDates=f["travelDates"],
                       rankingMode=f["rankingMode"], confirmedAt=c["confirmedAt"],
                       constraintSetId=baseline["request"]["constraintSetId"] if baseline else identifier(),
                       constraintSetVersion=baseline["request"]["constraintSetVersion"]+1 if baseline else 1,
                       hardConstraints=[], preferences=f.get("preferences", []),
                       baselineVersionId=f.get("baselineVersionId"), confirmedChangedFields=[])
        spec = {"roundTrip": f.get("roundTrip", False), "constraintBindings": {}}
        constraints = [{"kind": "BUDGET", "value": f["budgetCeiling"], "description": "Confirmed total AUD budget"},
                       {"kind": "DATES", "value": f["travelDates"], "description": "Confirmed inclusive travel dates"}] + f.get("constraints", [])
        for value in constraints:
            key = value["kind"].lower()
            description = value["description"] + ": " + json.dumps(value["value"], sort_keys=True)
            request["hardConstraints"].append({"constraintId": key, "kind": value["kind"],
                                              "description": description, "confirmed": True})
            spec["constraintBindings"][key] = {"description": description, "value": value["value"]}
        if baseline:
            keys = ["origin", "destination", "partySize", "budgetCeiling", "travelDates", "rankingMode", "preferences", "hardConstraints"]
            request["confirmedChangedFields"] = [k for k in keys if request[k] != baseline["request"][k]]
            if spec["roundTrip"] != baseline["spec"]["roundTrip"]:
                raise OperationsError("UNSUPPORTED_CONSTRAINT", "The current Planning module does not support hidden round-trip revisions.")
            if not request["confirmedChangedFields"]:
                raise OperationsError("UNCONFIRMED_REQUEST", "Confirm at least one changed requirement for a revision.")
        validate("TravelRequest", request)
        return {"request": request, "spec": spec}

    def load_context(self, case):
        if isinstance(case, str):
            rec = self.repository.read("case", case)
            if not rec:
                raise OperationsError("UNCONFIRMED_REQUEST", "The confirmed case context is unavailable.")
            case = rec["case"]
        validate("Case", case)
        rec = self.repository.read("case", case["caseId"])
        if not rec or rec["case"] != case or not rec.get("context") or not self.access.authorise(case["requesterId"], "READ_CASE", case):
            raise OperationsError("UNCONFIRMED_REQUEST", "Planning requires the current persisted, confirmed case context.")
        return deepcopy(rec["context"])

    def _decision(self, records, rec, action, dates):
        decision = self.entitlement.evaluate(rec["case"]["requesterId"], action, dates)
        decision["tripDates"] = deepcopy(dates)
        self._record_decision(records, rec, decision)
        return decision

    def _record_decision(self, records, rec, decision):
        rec["sources"].append(source(decision["sourceIds"][0], self.clock()))
        rec["case"]["sourceReferences"] = rec["sources"]
        rec["case"]["entitlementDecision"] = Entitlements.wire(decision)
        rec["case"]["validationResults"] = [check("ENTITLEMENT", "PASS" if decision["outcome"] == "ALLOWED" else "FAIL",
                                              decision["reason"], self.clock(), decision["sourceIds"])]
        # Full membership snapshot remains operator-only, outside the strict Case contract.
        rec.setdefault("membershipSnapshots", []).append(deepcopy(decision))
        self._event(records, rec, "TOOL_RESULT", json.dumps(decision, sort_keys=True))

    def dispatch(self, actor, key, case_id, revision):
        def start(records):
            rec = self._owned(records, actor, case_id, "DISPATCH", revision)
            c = rec["case"]
            if c["status"] not in {"CONFIRMED", "ASSIGNED"} or rec["dispatchStarted"]:
                raise OperationsError("UNCONFIRMED_REQUEST", "This dispatch is already started or needs clarification/human handling.")
            if c["humanRequestCount"] >= 2:
                c["status"] = "HUMAN_ASSISTANCE"
            else:
                c["primaryHandler"] = ROUTES[c["caseType"]]
                if c["caseType"] in {"TRAVEL_PLANNING", "PLAN_REVISION", "MEMBERSHIP"}:
                    action = {"TRAVEL_PLANNING": "CREATE_PLAN", "PLAN_REVISION": "REVISE_PLAN", "MEMBERSHIP": "MEMBERSHIP"}[c["caseType"]]
                    dates = deepcopy(rec["fields"].get("travelDates", {}))
                    if c["caseType"] == "MEMBERSHIP":
                        action = rec["fields"].get("feature", "MEMBERSHIP")
                        if rec["fields"].get("memberOfferRuleId"):
                            action = "MEMBER_OFFER"
                            dates["memberOfferRule"] = records.get("member_offer", rec["fields"]["memberOfferRuleId"])
                    if c["caseType"] == "PLAN_REVISION":
                        dates["planId"] = self.planning_repository.get_version(rec["fields"]["baselineVersionId"])["version"]["planId"]
                    d = self._decision(records, rec, action, dates)
                    if d["outcome"] == "VERIFICATION_FAILED":
                        c["status"] = "AWAITING_VERIFICATION"
                    elif d["outcome"] == "DENIED":
                        self._routine_response(rec, d["reason"])
                if c["status"] == "CONFIRMED":
                    c["status"] = "IN_PROGRESS"
                    rec["dispatchStarted"] = True
                    rec["runId"] = identifier()
                    self._event(records, rec, "HANDOFF", "Confirmed request assigned to " + c["primaryHandler"] + "; case remains open.", "PENDING")
            rec["revision"] += 1
            self._save(records, rec)
            return {"caseId": case_id, "runId": rec.get("runId"), "execute": c["status"] == "IN_PROGRESS"}
        reservation = self._command(actor, "dispatch", key, [case_id, revision], start)
        rec = self.repository.read("case", case_id)
        # Replay never invokes a specialist twice. An interrupted call needs human handling.
        if not reservation["execute"] or rec.get("completedRun") == reservation.get("runId"):
            return self.case_view(actor, case_id)
        if rec.get("runId") != reservation["runId"] or rec["case"]["status"] != "IN_PROGRESS":
            return self.case_view(actor, case_id)
        if rec.get("invokedRun") == reservation["runId"]:
            return self.case_view(actor, case_id)
        with self.repository.transaction() as records:
            current = records.get("case", case_id)
            if current.get("invokedRun") == reservation["runId"]:
                return self.case_view(actor, case_id)
            current["invokedRun"] = reservation["runId"]
            self._save(records, current)
        result = None
        kind = rec["case"]["caseType"]
        failure = None
        if ROUTES[kind] == "operations":
            text = APPROVED_SERVICE_INFO if kind == "ROUTINE_ENQUIRY" else rec["case"]["entitlementDecision"]["reason"]
        else:
            agent = self.specialists.get(ROUTES[kind])
            try:
                if agent is None:
                    raise OperationsError("TOOL_UNAVAILABLE", "The responsible specialist has not been integrated.")
                result = self._dependency(lambda: agent.handle_case(deepcopy(rec["case"])))
                validate("AgentResult", result)
                if result["caseId"] != case_id or result["correlationId"] != rec["correlationId"] or result["agent"] != ROUTES[kind]:
                    raise ContractError("Mismatched result")
            except ContractError:
                failure = ("INVALID_CONTRACT", "Specialist output did not match the confirmed case contract.")
            except Exception as exc:
                code = "LLM_TIMEOUT" if isinstance(exc, TimeoutError) else "TOOL_UNAVAILABLE"
                failure = (code, "Specialist processing is unavailable; available context is retained for human assistance.")
        with self.repository.transaction() as records:
            current = records.get("case", case_id)
            # Withdrawal/human requests while a specialist runs invalidate late results.
            if current["case"]["status"] != "IN_PROGRESS" or current["revision"] != rec["revision"]:
                return self.case_view(actor, case_id)
            if failure:
                self._failure(current, *failure)
            elif ROUTES[kind] == "operations":
                self._routine_response(current, text)
            else:
                try:
                    self._receive(records, current, result)
                except Exception:
                    self._failure(current, "REVIEW_FAILED", "Proposal context, evidence or review could not be verified; human assistance is required.")
            current["completedRun"] = reservation["runId"]
            current["revision"] += 1
            self._event(records, current, "FAILURE" if failure else "TOOL_RESULT", "Specialist/internal result recorded; no external delivery occurred.", "FAILURE" if failure else "PENDING")
            self._save(records, current)
        if self.reviewer is not None:
            candidate = self.repository.read("case", case_id)
            if candidate["case"]["status"] == "UNDER_REVIEW":
                try:
                    review = self._dependency(lambda: self.reviewer.review(self._response_subject(candidate), candidate["sources"], ["ops-response-1.0"]))
                except Exception:
                    review = None
                with self.repository.transaction() as records:
                    latest = records.get("case", case_id)
                    if latest["revision"] == candidate["revision"] and latest["case"]["status"] == "UNDER_REVIEW":
                        try:
                            if review is None:
                                raise OperationsError("REVIEW_FAILED", "Review unavailable")
                            self._apply_review(records, latest, review)
                        except Exception:
                            self._failure(latest, "REVIEW_FAILED", "The response reviewer is unavailable or did not verify this exact version.")
                        latest["revision"] += 1
                        self._event(records, latest, "REVIEW", "External response review recorded; restricted authority remains with the operator.", "PENDING")
                        self._save(records, latest)
        return self.case_view(actor, case_id)

    def _failure(self, rec, code, message):
        rec["case"]["status"] = "HUMAN_ASSISTANCE"
        rec["case"]["errors"] = [{"code": code, "message": message, "step": "coordination", "retryable": True, "sourceIds": []}]
        rec["response"] = None
        rec["review"] = None

    def _routine_response(self, rec, text):
        rec["response"] = safe_text(text)
        rec["responseVersion"] += 1
        rec["case"]["status"] = "READY_TO_RESPOND"
        rec["review"] = {"reviewId": identifier(), "subject": self._response_subject(rec), "outcome": "PASS",
                         "reasons": ["Deterministic approved service information or entitlement explanation."],
                         "reviewedAt": self.clock(), "policyVersion": "ops-approved-service-info-1.0",
                         "sourceIds": [rec["sources"][0]["sourceId"]]}

    @staticmethod
    def _response_subject(rec):
        return {"subjectType": "Case", "subjectId": rec["id"], "materialVersion": rec["responseVersion"]}

    def _receive(self, records, rec, result):
        if result["executionMode"] == "STUB":
            self._failure(rec, "TOOL_UNAVAILABLE", "The specialist is still an unconfigured stub.")
            return
        rec["specialistResult"] = deepcopy(result)
        if result['agent'] == 'supplier' and result['status'] == 'APPROVAL_PENDING':
            rec['case']['requiresApproval'] = True
            rec['case']['status'] = 'AWAITING_HUMAN_APPROVAL'
            rec['response'] = None
            rec['review'] = None
            rec['approvalId'] = None  # Offer approval is scoped to SupplierOffer, not Case response.
            return
        if result["status"] != "SUCCESS":
            rec["case"]["unresolvedQuestions"] = [safe_text(result["nextAction"])]
            rec["case"]["status"] = "AWAITING_REQUESTER" if result["status"] == "REVISION_REQUIRED" else "HUMAN_ASSISTANCE"
            rec["response"] = None
            return
        if rec["case"]["caseType"] in {"TRAVEL_PLANNING", "PLAN_REVISION"} and not any(
                ref["subjectType"] == "ItineraryVersion" for ref in result["subjects"]):
            self._failure(rec, "INVALID_CONTRACT", "A successful planning result must reference a saved itinerary version.")
            return
        if not result["proposedResponse"] or not result["validationResults"] or any(v["outcome"] != "PASS" for v in result["validationResults"]):
            self._failure(rec, "REVIEW_FAILED", "A specialist proposal needs passing deterministic checks and supporting evidence.")
            return
        if any(s["freshness"] != "FRESH" or instant(s["capturedAt"]) > instant(self.clock()) for s in result["sourceReferences"]):
            self._failure(rec, "STALE_EVIDENCE", "The proposal contains stale or unverified evidence.")
            return
        ids = {s["sourceId"] for s in result["sourceReferences"]}
        if any(not set(v["sourceIds"]).issubset(ids) for v in result["validationResults"]):
            self._failure(rec, "INVALID_CONTRACT", "Validation references unresolved evidence.")
            return
        rec["sources"] += [s for s in result["sourceReferences"] if s["sourceId"] not in {x["sourceId"] for x in rec["sources"]}]
        rec["case"]["sourceReferences"] = rec["sources"]
        rec["case"]["validationResults"] = deepcopy(result["validationResults"])
        # For a generated plan, membership is evaluated again from exact returned facts.
        for ref in result["subjects"]:
            if ref["subjectType"] == "ItineraryVersion":
                version = self._plan_record(rec["case"]["requesterId"], ref["subjectId"])["version"]
                if version["versionNo"] != ref["materialVersion"] or version["caseId"] != rec["id"]:
                    raise OperationsError("INVALID_CONTRACT", "Planning returned a mismatched plan version.")
                rec["planId"] = version["planId"]
                dates = dict(version["travelDates"], planId=version["planId"])
                d = self._decision(records, rec, "PRESENT_PLAN", dates)
                if d["outcome"] != "ALLOWED":
                    self._failure(rec, "ENTITLEMENT_DENIED", d["reason"])
                    return
        rec["response"] = safe_text(result["proposedResponse"])
        rec["responseVersion"] += 1
        rec["review"] = None
        rec["approvalId"] = None
        # Specialist declared restrictions plus deterministic sensitive intent check.
        rec["case"]["requiresApproval"] = bool(result["requiresApproval"] or any(
            word in rec["response"].lower() for word in ("refund", "compensation", "contract", "binding", "spending", "payment")))
        rec["case"]["status"] = "UNDER_REVIEW"

    def _apply_review(self, records, rec, review):
        validate_fragment("ReviewResult", review)
        if (review["subject"] != self._response_subject(rec)
                or instant(review["reviewedAt"]) > instant(self.clock())
                or not set(review["sourceIds"]).issubset({s["sourceId"] for s in rec["sources"]})):
            raise OperationsError("REVIEW_FAILED", "Review does not cover this exact response version and evidence.")
        rec["review"] = deepcopy(review)
        if review["outcome"] != "PASS":
            rec["case"]["status"] = "AWAITING_REQUESTER"
            rec["case"]["unresolvedQuestions"] = review["reasons"] or ["Proposal requires revision."]
        elif rec["case"]["requiresApproval"]:
            approval = envelope(rec["id"], rec["correlationId"], rec["sources"])
            approval.update(approvalId=identifier(), subject=self._response_subject(rec),
                            scope="SIMULATED_EXTERNAL_RESPONSE", status="PENDING", decision=None,
                            requestedAt=self.clock(), decidedAt=None, operatorId=None, reason=None, reviewId=review["reviewId"])
            approval["requiresApproval"] = True
            validate("Approval", approval)
            records.put("approval", approval["approvalId"], approval)
            rec["approvalId"] = approval["approvalId"]
            rec["case"]["status"] = "AWAITING_HUMAN_APPROVAL"
            self._event(records, rec, "APPROVAL_REQUESTED", "Scoped human decision required before simulated response delivery.", "PENDING", approval_id=approval["approvalId"])
        else:
            rec["case"]["status"] = "READY_TO_RESPOND"

    def review_case(self, actor, key, case_id, revision, decision, reason, edited_text=None):
        reason = safe_text(reason, 1000)
        if decision not in {"APPROVE", "REQUEST_REVISION", "REJECT", "TAKE_OVER"}:
            raise OperationsError("INVALID_CONTRACT", "Choose an operator decision.")
        def review(records):
            rec = self._owned(records, actor, case_id, "REVIEW_CASE", revision)
            if rec["case"]["status"] in {"CLOSED", "WITHDRAWN"}:
                raise OperationsError("UNCONFIRMED_REQUEST", "A closed case cannot be reviewed again.")
            if edited_text is not None:
                rec["response"] = safe_text(edited_text)
                rec["responseVersion"] += 1
                rec["review"], rec["approvalId"] = None, None
                rec["case"]["requiresApproval"] = True
            if decision == "TAKE_OVER":
                rec["case"]["status"] = "HUMAN_ASSISTANCE"
            elif decision in {"REQUEST_REVISION", "REJECT"}:
                if rec["approvalId"]:
                    self._decide(records, rec, actor, decision, reason)
                rec["case"]["status"] = "AWAITING_REQUESTER" if decision == "REQUEST_REVISION" else "HUMAN_ASSISTANCE"
                rec["case"]["unresolvedQuestions"] = [reason]
                rec["review"] = None
            else:
                if not rec["response"]:
                    raise OperationsError("REVIEW_FAILED", "Supply an evidence-supported response before approval.")
                if rec["case"]["errors"]:
                    raise OperationsError("REVIEW_FAILED", "Failed dependency/validation conditions must be resolved before release.")
                review = {"reviewId": identifier(), "subject": self._response_subject(rec), "outcome": "PASS",
                          "reasons": [reason], "reviewedAt": self.clock(), "policyVersion": "ops-human-response-review-1.0",
                          "sourceIds": [s["sourceId"] for s in rec["sources"]]}
                self._apply_review(records, rec, review)
                if rec["case"]["requiresApproval"]:
                    self._decide(records, rec, actor, decision, reason)
                    rec["case"]["status"] = "READY_TO_RESPOND"
            rec["revision"] += 1
            self._event(records, rec, "REVIEW", "Operator response review: " + reason, actor=actor)
            self._save(records, rec)
            return {"caseId": case_id}
        self._command(actor, "review", key, [case_id, revision, decision, reason, edited_text], review)
        return self.case_view(actor, case_id)

    def _decide(self, records, rec, actor, decision, reason):
        pending = records.get("approval", rec["approvalId"])
        # Keep the pending record and append a new, immutable decision record.
        decided = dict(pending, approvalId=identifier(), status="DECIDED", decision=decision,
                       decidedAt=self.clock(), operatorId=actor, reason=reason)
        validate("Approval", decided)
        records.put("approval", decided["approvalId"], decided)
        rec["approvalId"] = decided["approvalId"]
        self._event(records, rec, "APPROVAL_DECIDED", "Human decision: " + decision + "; " + reason,
                    actor=actor, approval_id=decided["approvalId"])

    def deliver(self, actor, key, case_id, revision, sink_available=True):
        def deliver(records):
            rec = self._owned(records, actor, case_id, "DELIVER", revision)
            if rec["case"]["status"] != "READY_TO_RESPOND" or not rec["review"] or rec["review"]["outcome"] != "PASS" or rec["review"]["subject"] != self._response_subject(rec):
                raise OperationsError("REVIEW_FAILED", "Only the current reviewed response can be delivered.")
            if rec["case"]["requiresApproval"]:
                approval = records.get("approval", rec["approvalId"])
                if not approval or approval["status"] != "DECIDED" or approval["decision"] != "APPROVE" or approval["subject"] != self._response_subject(rec) or approval["reviewId"] != rec["review"]["reviewId"] or approval["scope"] != "SIMULATED_EXTERNAL_RESPONSE":
                    raise OperationsError("APPROVAL_REQUIRED", "A scoped decision for this exact response version is required.")
            if rec["case"]["caseType"] in {"TRAVEL_PLANNING", "PLAN_REVISION"} and rec.get("specialistResult"):
                for ref in rec["specialistResult"]["subjects"]:
                    if ref["subjectType"] == "ItineraryVersion":
                        v = self._plan_record(actor, ref["subjectId"])["version"]
                        if self._decision(records, rec, "PRESENT_PLAN", dict(v["travelDates"], planId=v["planId"]))["outcome"] != "ALLOWED":
                            rec["case"]["status"] = "AWAITING_PLAN_ACCESS_DECISION"
                            rec["revision"] += 1
                            self._save(records, rec)
                            return {"delivered": False, "caseId": case_id}
            rec["deliveryAttempts"] += 1
            rec["revision"] += 1
            if not sink_available:
                rec["case"]["status"] = "HUMAN_ASSISTANCE" if rec["deliveryAttempts"] >= 3 else "READY_TO_RESPOND"
                self._event(records, rec, "FAILURE", "Simulated delivery failed; response retained and case remains open.", "FAILURE")
            else:
                # No external side effect: the durable local inbox IS simulated delivery.
                records.put("inbox", case_id + ":" + str(rec["responseVersion"]),
                            {"caseId": case_id, "requesterId": rec["case"]["requesterId"], "response": rec["response"],
                             "responseVersion": rec["responseVersion"], "deliveredAt": self.clock(), "simulated": True})
                self._event(records, rec, "RESPONSE_DELIVERED", "Reviewed response saved to the simulated requester inbox.")
                rec["case"]["status"] = "CLOSED"
                self._event(records, rec, "CASE_CLOSED", "Closed after successful simulated delivery.")
            self._save(records, rec)
            return {"delivered": bool(sink_available), "caseId": case_id}
        return self._command(actor, "deliver", key, [case_id, revision], deliver)

    def case_action(self, actor, key, case_id, revision, action, reason="Requester action"):
        if action not in {"HUMAN", "WITHDRAW", "CLOSE_CASE"}:
            raise OperationsError("INVALID_CONTRACT", "Unsupported case action.")
        reason = safe_text(reason, 1000)
        def change(records):
            rec = self._owned(records, actor, case_id, action, revision)
            if rec["case"]["status"] in {"CLOSED", "WITHDRAWN"}:
                raise OperationsError("UNCONFIRMED_REQUEST", "The case is already closed.")
            if action == "HUMAN":
                rec["case"]["humanRequestCount"] += 1
                if rec["case"]["humanRequestCount"] >= 2:
                    rec["case"]["status"] = "HUMAN_ASSISTANCE"
            else:
                rec["case"]["status"] = "WITHDRAWN" if action == "WITHDRAW" else "CLOSED"
            rec["revision"] += 1
            self._event(records, rec, "HANDOFF" if action == "HUMAN" else "CASE_CLOSED", action + ": " + reason, actor=actor)
            self._save(records, rec)
            return {"caseId": case_id}
        self._command(actor, action, key, [case_id, revision, reason], change)
        return self.case_view(actor, case_id)

    def case_view(self, actor, case_id):
        rec = self.repository.read("case", case_id)
        if not rec or not self.access.authorise(actor, "READ_CASE", rec["case"]):
            raise OperationsError("ACCESS_DENIED", "This case is unavailable to this identity.")
        operator = self.profile(actor)["role"] == "OPERATOR"
        # Specialist draft/finding/quote payloads are never sent to a traveller.
        delivered = self.repository.read("inbox", rec["id"] + ":" + str(rec["responseVersion"]))
        value = {"case": rec["case"], "revision": rec["revision"], "fields": rec["fields"],
                 "response": rec["response"] if operator else delivered["response"] if delivered else None,
                 "responseVersion": rec["responseVersion"], "simulationOnly": True,
                 "review": rec["review"] if operator else None, "campaignId": rec["campaignId"], "sourceChannel": rec["sourceChannel"]}
        if operator:
            value.update(membershipSnapshots=rec.get("membershipSnapshots", []), approvalId=rec["approvalId"])
        return value

    def update_intake(self, actor, key, intake_id, revision, intents=None, human=False):
        normalised = self._normalise(actor, intents) if intents is not None else None
        def update(records):
            rec = self._intake_owned(records, actor, intake_id)
            if rec["revision"] != revision or rec["caseIds"]:
                raise OperationsError("UNCONFIRMED_REQUEST", "Use the current unconfirmed intake version.")
            if human:
                rec["humanRequestCount"] += 1
                if rec["humanRequestCount"] >= 2:
                    rec["state"] = "HUMAN_ASSISTANCE"
            elif normalised is not None:
                rec["intents"] = normalised
                rec["questions"] = self._missing(normalised)
                rec["confidence"] = 1.0
                rec["state"] = "AWAITING_CONFIRMATION" if self.profile(actor)["verified"] else "AWAITING_VERIFICATION"
            rec["revision"] += 1
            self._event(records, rec, "HANDOFF" if human else "INTAKE", "Human assistance requested." if human else "Clarification captured; requester confirmation is still required.", "PENDING", actor)
            self._save(records, rec, "intake")
            return rec
        return self._command(actor, "update_intake", key, [intake_id, revision, normalised, human], update)

    def clarify(self, actor, key, case_id, revision, intents, confirmed):
        if confirmed is not True:
            raise OperationsError("UNCONFIRMED_REQUEST", "Confirm the whole revised request summary before continuing.")
        intents = self._normalise(actor, intents)
        if len(intents) != 1 or self._missing(intents):
            raise OperationsError("MISSING_REQUIRED_FIELDS", "Clarify this case with one complete intent; new independent intents need a separate intake.")
        def revise(records):
            rec = self._owned(records, actor, case_id, "CONFIRM", revision)
            if rec["case"]["status"] in {"CLOSED", "WITHDRAWN", "IN_PROGRESS", "HUMAN_ASSISTANCE"}:
                raise OperationsError("UNCONFIRMED_REQUEST", "This case cannot be re-confirmed in its current state.")
            intent = intents[0]
            self._require_affected_plan(actor, intent)
            rec["fields"] = intent["fields"]
            rec["case"].update(caseType=intent["caseType"], confirmedAt=self.clock(),
                               confirmedRequest=json.dumps(intent, sort_keys=True), status="CONFIRMED",
                               primaryHandler=None, unresolvedQuestions=[], entitlementDecision=None,
                               requiresApproval=False, validationResults=[], errors=[])
            rec.update(response=None, responseVersion=rec["responseVersion"]+1, review=None,
                       approvalId=None, dispatchStarted=False, completedRun=None, invokedRun=None)
            rec.pop("specialistResult", None)
            rec.pop("context", None)
            supplier = self.specialists.get('supplier')
            if rec['case']['caseKind'] == 'SUPPLIER' and hasattr(supplier, 'invalidate_confirmation'):
                supplier.invalidate_confirmation(records, rec)
            if intent["caseType"] in {"TRAVEL_PLANNING", "PLAN_REVISION"}:
                rec["context"] = self._planning_context(rec)
            rec["revision"] += 1
            self._event(records, rec, "CONFIRMATION", "Requester explicitly re-confirmed the complete revised summary; prior response authority invalidated.", actor=actor)
            self._save(records, rec)
            return {"caseId": case_id}
        self._command(actor, "clarify", key, [case_id, revision, intents, confirmed], revise)
        return self.case_view(actor, case_id)

    def premium(self, actor, key, action, member_offer_id=None):
        if not self.access.authorise(actor, "PREMIUM", {"travellerId": actor}):
            raise OperationsError("ACCESS_DENIED", "A verified traveller is required.")
        rule = self.repository.read("member_offer", member_offer_id) if member_offer_id else None
        decision = self.entitlement.evaluate(actor, action, {"memberOfferRule": rule})
        def save(records):
            rec = {"id": identifier(), "revision": 1, "correlationId": identifier(),
                   "sources": [source(decision["sourceIds"][0], self.clock())]}
            self._event(records, rec, "TOOL_RESULT", json.dumps(decision, sort_keys=True), actor=actor)
            return {"decision": decision, "advertising": "AD_FREE" if decision.get("membershipLevel") == "PAID" else "LABELLED_SIMULATED_ADS",
                    "rankingAffected": False, "simulationOnly": True}
        return self._command(actor, "premium", key, [action, member_offer_id], save)

    def cases(self, actor):
        return [self.case_view(actor, rec["id"]) for rec in self.repository.list("case")
                if self.access.authorise(actor, "READ_CASE", rec["case"])]

    def traces(self, actor, case_id):
        rec = self.repository.read("case", case_id)
        if not rec or not self.access.authorise(actor, "READ_TRACE", rec["case"]):
            raise OperationsError("ACCESS_DENIED", "The trace is unavailable to this identity.")
        events = self.repository.find_by_case(case_id)
        if self.profile(actor)["role"] == "OPERATOR":
            return events
        return [{k: e[k] for k in ("eventId", "timestamp", "eventType", "result", "executionMode", "subject")} for e in events]

    def history(self, actor, case_id):
        rec = self.repository.read("case", case_id)
        if not rec or not self.access.authorise(actor, "REVIEW_CASE", rec["case"]):
            raise OperationsError("ACCESS_DENIED", "Only the operator can inspect full decision snapshots.")
        return [{"eventId": e["eventId"], "snapshot": self.repository.read("history", e["eventId"])}
                for e in self.repository.find_by_case(case_id)]

    def _plan_record(self, actor, version_id):
        if not self.planning_repository:
            raise OperationsError("TOOL_UNAVAILABLE", "Planning storage has not been integrated.")
        record = self.planning_repository.get_version(version_id)
        if not record or not self.access.authorise(actor, "READ_PLAN", record["version"]):
            raise OperationsError("ACCESS_DENIED", "This plan is unavailable to this traveller.")
        validate("ItineraryVersion", record["version"])
        return record

    def plan_view(self, actor, version_id):
        record = self._plan_record(actor, version_id)
        rec = self.repository.read("case", record["version"]["caseId"])
        ref = {"subjectType": "ItineraryVersion", "subjectId": version_id, "materialVersion": record["version"]["versionNo"]}
        if (not rec or rec["case"]["status"] != "CLOSED"
                or not self.repository.read("inbox", rec["id"] + ":" + str(rec["responseVersion"]))
                or not rec["response"] or not rec["review"] or rec["review"]["outcome"] != "PASS"
                or rec["review"]["subject"] != self._response_subject(rec)
                or rec["case"]["errors"] or ref not in rec.get("specialistResult", {}).get("subjects", [])):
            raise OperationsError("REVIEW_FAILED", "Operations has not released this plan.")
        if self.entitlement.evaluate(actor, "PRESENT_PLAN", dict(record["version"]["travelDates"], planId=record["version"]["planId"]))["outcome"] != "ALLOWED":
            raise OperationsError("ENTITLEMENT_DENIED", "Current membership does not allow plan presentation.")
        # Nested allowlist: comparison contains internal records on some adapters.
        comparison = record.get("comparison", {})
        output = {"version": deepcopy(record["version"]),
                "comparison": {k: deepcopy(comparison[k]) for k in ("baselineVersionId", "proposalVersionId", "costDelta", "journeyMinutesDelta", "changedRequirements", "addedOffers", "removedOffers", "changedOffers", "unchangedOffers", "scopeChanged", "dataRefresh", "attribution") if k in comparison},
                "simulationOnly": True}
        if 'dailySchedule' in record:
            daily = record['dailySchedule']
            output['dailySchedule'] = {k: deepcopy(daily[k]) for k in ['timeline', 'days', 'additionalCost', 'journeyMinutes', 'transfers']}
        return output

    def adopt_plan(self, actor, key, version_id, expected_baseline, accepted):
        with self.adoption_lock:
            return self._adopt_plan(actor, key, version_id, expected_baseline, accepted)

    def _adopt_plan(self, actor, key, version_id, expected_baseline, accepted):
        if accepted is not True:
            raise OperationsError("UNCONFIRMED_REQUEST", "Explicit acceptance of the exact proposal is required.")
        if self.adopt is None:
            raise OperationsError("TOOL_UNAVAILABLE", "Planning adoption is not integrated.")
        record = self._plan_record(actor, version_id)
        cached, value = self.repository.cached(*self._command_identity(actor, "adopt", key, [version_id, expected_baseline, accepted]))
        if cached:
            return value
        self.plan_view(actor, version_id)
        if not self.access.authorise(actor, "ADOPT_PLAN", record["version"]):
            raise OperationsError("ACCESS_DENIED", "Plan adoption is not authorised.")
        dates = dict(record["version"]["travelDates"], planId=record["version"]["planId"])
        decision = self.entitlement.evaluate(actor, "ADOPT_PLAN", dates)
        decision.update(tripDates=dates, planVersionId=version_id)
        if decision["outcome"] != "ALLOWED":
            raise OperationsError("ENTITLEMENT_DENIED", "Current membership does not allow adoption.")
        # Planning owns the atomic selected-baseline/idempotency transaction and
        # revalidation of offers/review. Never hold an Operations write lock here.
        adopted = self._dependency(lambda: self.adopt(actor, version_id, expected_baseline, accepted=True))
        if adopted["version"]["versionId"] != version_id or adopted["version"]["travellerId"] != actor:
            raise OperationsError("INVALID_CONTRACT", "Adoption returned a mismatched version.")
        case_id = record["version"]["caseId"]
        def persist(records):
            rec = self._owned(records, actor, case_id)
            self._record_decision(records, rec, decision)
            records.put("lifecycle", record["version"]["planId"], {"planId": record["version"]["planId"],
                        "travellerId": actor, "planStatus": "PLANNED", "selectedVersionId": version_id})
            rec["revision"] += 1
            self._event(records, rec, "VERSION_CREATED", "Exact proposal explicitly adopted; no booking or payment.", actor=actor)
            self._save(records, rec)
            return {"versionId": version_id, "adopted": True, "simulationOnly": True}
        return self._command(actor, "adopt", key, [version_id, expected_baseline, accepted], persist)
