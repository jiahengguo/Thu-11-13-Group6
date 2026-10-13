"""Deterministic access/membership ports, backed by explicit simulated evidence."""
from datetime import date

from .common import identifier, instant

TRIP_ACTIONS = {"CREATE_PLAN", "REVISE_PLAN", "PRESENT_PLAN", "ADOPT_PLAN"}
PREMIUM_FEATURES = {"ROUTE_MAP", "AD_FREE"}


class AccessService:
    def __init__(self, profiles):
        self.profiles = profiles

    def authorise(self, requester_id, action, subject):
        profile = self.profiles(requester_id)
        if not profile or profile.get("verified") is not True:
            return False
        if profile["role"] == "OPERATOR":
            return action in {"REVIEW_CASE", "CLOSE_CASE", "READ_CASE", "READ_TRACE", "ANALYSE", "DELIVER"}
        owner = subject.get("travellerId", subject.get("requesterId"))
        if owner != requester_id:
            return False
        if profile["role"] == "SUPPLIER":
            return action in {"READ_CASE", "READ_TRACE", "CONFIRM", "DISPATCH", "WITHDRAW", "HUMAN", "DELIVER"}
        return action in TRIP_ACTIONS | {"READ_PLAN", "READ_CASE", "READ_TRACE", "CONFIRM", "DISPATCH", "WITHDRAW", "HUMAN", "DELIVER", "PREMIUM"}


class Entitlements:
    def __init__(self, profiles, trips, clock):
        self.profiles, self.trips, self.clock = profiles, trips, clock

    def evaluate(self, traveller_id, action, dates):
        timestamp = self.clock()
        profile = self.profiles(traveller_id)
        result = {"decisionId": identifier(), "travellerId": traveller_id, "action": action,
                  "outcome": "VERIFICATION_FAILED", "reason": "Membership evidence is unavailable.",
                  "decidedAt": timestamp, "ruleVersion": "ops-membership-1.0",
                  "sourceIds": ["membership:" + traveller_id]}
        result["sourceIds"] = ["membership:" + traveller_id + ":" + result["decisionId"]]
        if not profile or profile.get("verified") is not True or profile.get("role") != "TRAVELLER":
            return result
        try:
            tier = profile["membership"]
            if tier not in {"FREE", "PAID"}:
                return result
            paid = tier == "PAID" and instant(profile["paidUntil"]) > instant(timestamp)
            current = {p["planId"]: p for p in self.trips(traveller_id)
                       if p["planStatus"] in {"PLANNED", "ACTIVE"}}
            result.update(membershipLevel="PAID" if paid else "FREE", tripCount=len(current))
            if action in TRIP_ACTIONS:
                start, end = date.fromisoformat(dates["startDate"]), date.fromisoformat(dates["endDate"])
                duration = (end - start).days + 1
                if duration <= 0:
                    raise ValueError("Reversed dates")
                result["durationDays"] = duration
                # Existing-plan revisions/adoptions do not consume another slot.
                existing = dates.get("planId")
                count = len(current) + (0 if existing in current else 1)
                if not paid and count > 2:
                    result.update(outcome="DENIED", appliedRule="FREE_TRIP_COUNT",
                                  reason=f"Free members may hold at most two Planned/Active trips; you currently have {len(current)}. Complete a trip or upgrade before creating another.")
                elif not paid and duration > 5:
                    result.update(outcome="DENIED", appliedRule="FREE_TRIP_DURATION",
                                  reason=f"Free trips may cover at most five inclusive calendar days; this request covers {duration}. Shorten the requested trip or upgrade.")
                else:
                    result.update(outcome="ALLOWED", appliedRule="ACTIVE_PAID" if paid else "FREE_TRIP_LIMITS",
                                  reason="Current membership and trip rules permit this action.")
            elif action in PREMIUM_FEATURES:
                result.update(outcome="ALLOWED" if paid else "DENIED", reason="Verified active Paid membership permits this premium feature." if paid else "Active Paid membership is required for this premium feature.")
            elif action == "MEMBER_OFFER":
                rule = dates.get("memberOfferRule")
                allowed = (rule and rule.get("approved") is True and result["membershipLevel"] in rule["eligibleTiers"]
                           and instant(rule["validFrom"]) <= instant(timestamp) < instant(rule["validUntil"]))
                result.update(outcome="ALLOWED" if allowed else "DENIED", reason="Approved offer eligibility checked; Supplier owns discount and price calculation.")
            elif action == "MEMBERSHIP":
                result.update(outcome="ALLOWED", reason="Current verified membership snapshot returned.")
            else:
                result.update(outcome="DENIED", reason="This capability is not in the entitlement catalogue.")
        except (KeyError, TypeError, ValueError):
            result.update(outcome="VERIFICATION_FAILED", reason="Required membership, trip or policy facts could not be verified.")
        return result

    @staticmethod
    def wire(result):
        # The shared contract is strict; extra evidence is kept in the audit snapshot.
        keys = {"decisionId", "travellerId", "action", "outcome", "reason", "decidedAt", "ruleVersion", "sourceIds"}
        return {k: v for k, v in result.items() if k in keys}
