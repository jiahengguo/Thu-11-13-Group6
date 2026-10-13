"""Adapters for the merged Operations service and Jason's B03 database.

This module does not implement the unmerged Supplier agent or B10 Reviewer.
"""
from copy import deepcopy

from tripmate.contracts import validate
from tripmate.operations.integration import connect_planning
from .common import PlanningError, subject, timestamp, uid
from .repository import PlanningRepository
from .validation import validate_product


class B03ApprovedOffers:
    """Read current B03 database records, never Moore's independent fixture list."""
    def __init__(self, fixtures):
        self.fixtures = fixtures

    def find_selectable(self, criteria, at):
        quotes = []
        for entity in self.fixtures.list_entities('OFFER'):
            offer = entity['data']['offer']
            validate('SupplierOffer', offer)
            review = offer.get('review') or {}
            if (offer['status'] != 'APPROVED' or offer['requiresApproval'] or offer['errors']
                    or review.get('outcome') != 'PASS'
                    or review.get('subject') != {'subjectType': 'SupplierOffer', 'subjectId': offer['offerId'],
                                                  'materialVersion': offer['materialVersion']}
                    or not timestamp(offer['validFrom']) <= timestamp(at) < timestamp(offer['validUntil'])
                    or offer['availableQuantity'] < offer['quotedQuantity']):
                continue
            product = self.fixtures.get_entity('product:' + offer['productId'])
            price = self.fixtures.get_entity('price:' + offer['offerId'])
            if not product or not price:
                raise PlanningError('INVALID_CONTRACT', 'B03 quote has missing product/price references', 'lookup')
            product, price = product['data'], price['data']
            validate_product(product)
            validate('PriceBreakdown', price)
            if product['partySize'] != criteria['partySize']:
                continue
            quotes.append(deepcopy({'offer': offer, 'price': price, 'product': product}))
        return quotes


class WorkbenchFixtureReviewer:
    """Explicit development substitute: checks recorded rules, not a B10 implementation."""
    def __init__(self, clock):
        self.clock = clock

    def review(self, version, evidence, policies):
        checks = version['validationResults']
        passed = bool(checks) and all(c['outcome'] == 'PASS' for c in checks)
        return {'reviewId': uid('workbench-fixture-review'), 'subject': subject(version),
                'outcome': 'PASS' if passed else 'REVISION_REQUIRED',
                'reasons': ['Explicit development fixture Reviewer; B10 peer integration pending'],
                'reviewedAt': self.clock(), 'policyVersion': 'workbench-fixture-only-1',
                'sourceIds': [s['sourceId'] for s in evidence]}


def connect_workbench_planning(operations, fixtures, database, *, live_model=False):
    """Opt-in development composition, never automatically applied to cloud portals."""
    factory = None
    if live_model:
        from tripmate.adapters.campus import CampusLLMService
        from .campus import ModelPlanningEngine
        # Two bounded requests leave room for deterministic validation under Ops' 60s limit.
        factory = lambda: ModelPlanningEngine(CampusLLMService(timeout=20), operations.clock, max_attempts=2)
    repository = PlanningRepository(database)
    connect_planning(operations, B03ApprovedOffers(fixtures), WorkbenchFixtureReviewer(operations.clock),
                     repository, planner_factory=factory)
    return repository
