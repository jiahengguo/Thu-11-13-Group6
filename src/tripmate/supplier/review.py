"""Supplier domain checks for the shared authenticated proposal reviewer."""
from copy import deepcopy

from .common import SupplierError, validate_offer, verify_price


def supplier_offer_validator(policy, clock):
    def validate_supplier(proposal, evidence, policies):
        offer = deepcopy(proposal)
        price = offer.pop('price', None)
        if price is None or policies != [{'policyVersion': policy.version}]:
            return ['Current Supplier price and policy evidence is required.']
        if offer['sourceReferences'] != evidence:
            return ['Supplier evidence differs from the assessed offer.']
        try:
            validate_offer(offer, clock())
            verify_price(offer, price, policy)
        except (SupplierError, ValueError, KeyError, TypeError) as exc:
            return [str(exc)]
        return []
    return validate_supplier
