"""Adapters to installed Supplier lookup and Planning engine, on supplied evidence."""
from copy import deepcopy

from tripmate.contracts import validate
from tripmate.planning.engine import PlanningEngine
from tripmate.planning.validation import validate_product


class ProjectSupplier:
    def __init__(self, lookup):
        # SupplierGateway and B03ApprovedOffers both expose this project port.
        self.lookup = lookup

    def alternatives(self, context):
        planning = context['planningContext']
        quotes = self.lookup.find_selectable(deepcopy(planning['request']), context['assessedAt'])
        for quote in quotes:
            validate('SupplierOffer', quote['offer'])
            validate('PriceBreakdown', quote['price'])
            validate_product(quote['product'])
        return deepcopy(quotes)


class ProjectPlanning:
    def recover(self, context, quotes):
        planning = context['planningContext']
        engine = PlanningEngine(lambda: context['assessedAt'])
        records, excluded = engine.recover(planning['request'], quotes, planning['spec'], planning['baseline'])
        return records, excluded


class ProjectComplaintFindings:
    """Retrieve known plan and supplier facts; never infer service fault or liability."""
    def __init__(self, planning_repository, supplier_lookup):
        self.planning_repository, self.supplier_lookup = planning_repository, supplier_lookup

    def investigate(self, context):
        planning = context.get('planningContext')
        if not planning:
            return {'findings': ['The complaint needs a retrievable confirmed Planning context.'], 'sources': []}
        baseline = self.planning_repository.get_version(context['itinerary']['versionId'])
        if baseline['version']['travellerId'] != context['travellerId']:
            raise ValueError('Complaint baseline ownership mismatch')
        quotes = self.supplier_lookup.find_selectable(planning['request'], context['assessedAt'])
        findings = ['Planning baseline: ' + baseline['version']['versionId']]
        sources = deepcopy(baseline['version']['sourceReferences'])
        for quote in quotes:
            offer = quote['offer']
            findings.append('Supplier offer ' + offer['offerId'] + ': recorded terms: ' + offer['cancellationTerms'])
            sources.extend(deepcopy(offer['sourceReferences']))
        return {'findings': findings, 'sources': sources}
