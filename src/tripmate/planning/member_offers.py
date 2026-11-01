"""Apply one explicitly selected persisted member quotation to a plan."""
from copy import deepcopy
from tripmate.operations.common import OperationsError

class MemberPlanningOffers:
    def __init__(self, operations, supplier, campaigns):
        self.ops, self.supplier, self.campaigns = operations, supplier, campaigns

    def find_selectable(self, request, at):
        quotes = self.supplier.find_selectable(request, at)
        if not isinstance(request, dict) or 'caseId' not in request:
            return quotes
        # The quote selection is part of the confirmed constraint description.
        import json
        constraints = [c for c in request['hardConstraints'] if c['constraintId'] == 'member_quote']
        if not constraints:
            return quotes
        try:
            if len(constraints) != 1 or not constraints[0]['confirmed']:
                raise ValueError()
            value = json.loads(constraints[0]['description'].split(': ', 1)[1])
            if set(value) != {'version', 'quoteId'} or value['version'] != 'member-quote-1':
                raise ValueError()
            quote_id = value['quoteId']
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise OperationsError('INVALID_CONTRACT', 'Confirm one supported member quotation.') from exc
        saved = self.ops.repository.read('member_quote', quote_id)
        if not saved or saved['travellerId'] != request['travellerId']:
            raise OperationsError('ACCESS_DENIED', 'Member quotation belongs to another traveller or is unavailable.')
        price = saved['price']
        rule = self.ops.repository.read('member_offer', price['memberOfferRuleId'])
        if not rule or not self.campaigns.member_offer_check(rule):
            raise OperationsError('STALE_EVIDENCE', 'Member offer approval is no longer current.')
        decision = self.ops.entitlement.evaluate(request['travellerId'], 'MEMBER_OFFER', {'memberOfferRule': rule})
        if decision['outcome'] != 'ALLOWED':
            raise OperationsError('ENTITLEMENT_DENIED', 'Current membership does not allow this quotation.')
        original = next((q for q in quotes if q['offer']['offerId'] == price['offerId']), None)
        if not original or original['offer']['materialVersion'] != price['offerVersion']:
            raise OperationsError('STALE_EVIDENCE', 'The member quotation source is unavailable or changed.')
        fresh = self.supplier.pricing.calculate(original['offer'], dict(rule, eligible=True, entitlementDecisionId=decision['decisionId']))
        fields = ('offerId','offerVersion','supplierCost','markupRate','basePrice','discountAmount','sellingPrice',
                  'marginAmount','minimumMargin','quotedQuantity','unitBasis','pricingConfigVersion','memberOfferRuleId')
        if any(fresh[k] != price[k] for k in fields) or fresh['sourceReferences'] != price['sourceReferences']:
            raise OperationsError('STALE_EVIDENCE', 'Member pricing changed; obtain and confirm a new quotation.')
        result = deepcopy(quotes)
        selected = next(q for q in result if q['offer']['offerId'] == price['offerId'])
        selected['memberQuote'] = deepcopy(saved)
        selected['price'] = deepcopy(price)
        return result
