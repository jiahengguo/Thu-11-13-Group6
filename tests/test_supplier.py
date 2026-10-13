"""B08 boundary, revision, evidence and fail-closed approval checks."""
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from tripmate.agents.supplier import SupplierPartnershipAgent
from tripmate.contracts import validate
from tripmate.supplier import PricingPolicy, SupplierError, SupplierRepository, SupplierRuntime
from tripmate.supplier.common import SOURCE_FIELDS, envelope, subject, verify_price

AT = '2026-10-12T10:00:00+11:00'
ROOT = Path(__file__).resolve().parents[1]


def example(name):
    return json.loads((ROOT / 'docs/contracts/v1/examples' / name).read_text())


class TestPricing:
    """Fixed expected values; arithmetic implementation is supplied by B04."""
    def calculate(self, offer, discount):
        price = example('PriceBreakdown.base.json')
        price.update(envelope(offer), offerId=offer['offerId'], offerVersion=offer['materialVersion'],
                     priceBreakdownId='price-' + str(offer['materialVersion']),
                     supplierCost=deepcopy(offer['supplierCost']), unitBasis=offer['unitBasis'],
                     quotedQuantity=offer['quotedQuantity'], calculatedAt=AT)
        price['validationResults'] = [dict(ruleId='TEST_PRICE', ruleVersion='test-1', outcome='PASS',
                                          reason='Fixed expected price', checkedAt=AT, sourceIds=['evidence-001'])]
        return price


class TestReview:
    def review(self, offer, evidence, policies):
        return dict(reviewId='review-' + str(offer['materialVersion']), subject=subject(offer),
                    outcome='PASS', reasons=['Test-only review'], reviewedAt=AT,
                    policyVersion='test-1', sourceIds=[s['sourceId'] for s in evidence])


class TestTraces:
    def __init__(self):
        self.events = []

    def append(self, event):
        validate('TraceEvent', event)
        self.events.append(deepcopy(event))


class TestApprovals:
    def __init__(self):
        self.records = []

    def save(self, approval):
        validate('Approval', approval)
        self.records.append(deepcopy(approval))

    def find_by_subject(self, ref):
        return [deepcopy(a) for a in self.records if a['subject'] == ref]


class TestAccess:
    def authorise(self, identity, action, target):
        return identity == ('operator-001' if action == 'APPROVE_SUPPLIER_TERMS' else 'supplier-001')


class SupplierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repository = SupplierRepository(Path(self.tmp.name) / 'shared.sqlite3')
        self.case = example('Case.confirmed.json')
        self.case.update(caseKind='SUPPLIER', caseType='OFFER', requesterType='SUPPLIER',
                         requesterId='supplier-001', primaryHandler='supplier')
        offer = example('SupplierOffer.draft.json')
        self.context = dict(offerId='offer-001', sourceReferences=offer['sourceReferences'],
                            candidate={key: offer[key] for key in SOURCE_FIELDS})
        self.policy = PricingPolicy('0.10', '15.00', 'fixture-1')
        self.approvals, self.traces = TestApprovals(), TestTraces()
        self.runtime = SupplierRuntime(lambda _: deepcopy(self.context), self.repository,
                                       TestPricing(), self.policy, TestReview(), self.traces,
                                       self.approvals, TestAccess(), clock=lambda: AT)
        self.agent = SupplierPartnershipAgent(self.runtime)

    def run_offer(self):
        result = self.agent.handle_case(self.case)
        validate('AgentResult', result)
        return result

    def test_valid_offer_and_exact_price_are_reusable_until_expiry(self):
        self.assertEqual(self.run_offer()['status'], 'SUCCESS')
        records = self.runtime.find_selectable({}, AT)
        self.assertEqual(records[0]['price']['sellingPrice']['amount'], '198.00')
        self.assertEqual(records[0]['price']['marginAmount']['amount'], '18.00')
        self.assertEqual(self.runtime.find_selectable({}, '2026-10-19T23:59:59+11:00'), [])
        self.assertTrue(self.traces.events)

    def test_invalid_offers_record_reason_and_are_never_selectable(self):
        mutations = [
            ('OFFER_EXPIRED', lambda x: x.update(validUntil='2026-10-11T10:00:00+11:00')),
            ('OFFER_INVALID', lambda x: x.update(availableQuantity=0)),
            ('OFFER_INVALID', lambda x: x.update(availableQuantity=1, quotedQuantity=2)),
            ('MISSING_REQUIRED_FIELDS', lambda x: x.pop('supplierCost')),
            ('OFFER_INVALID', lambda x: x['supplierCost'].update(currency='USD')),
            ('OFFER_INVALID', lambda x: x.update(cancellationTerms=' ')),
            ('OFFER_INVALID', lambda x: x.update(mandatoryChargesIncluded=False)),
        ]
        original = deepcopy(self.context)
        for code, mutate in mutations:
            with self.subTest(code=code):
                self.context = deepcopy(original)
                mutate(self.context['candidate'])
                result = self.run_offer()
                self.assertEqual(result['status'], 'FAILURE')
                self.assertEqual(result['errors'][0]['code'], code)
                self.assertEqual(self.runtime.find_selectable({}, AT), [])
        self.assertEqual(len(self.repository.history('offer-001')), len(mutations))

    def test_cost_cannot_be_changed_by_pricing_or_review(self):
        original = deepcopy(self.context)
        calculate = self.runtime.pricing.calculate
        def tamper(offer, discount):
            offer['supplierCost']['amount'] = '170.00'
            return calculate(offer, discount)
        self.runtime.pricing.calculate = tamper
        self.assertEqual(self.run_offer()['errors'][0]['code'], 'MARGIN_FAILED')
        self.assertEqual(self.context, original)

    def test_rounding_and_minimum_margin_are_checked_independently(self):
        offer = example('SupplierOffer.draft.json')
        offer['supplierCost']['amount'] = '0.05'
        price = TestPricing().calculate(offer, None)
        for field, value in [('basePrice', '0.06'), ('sellingPrice', '0.06'), ('marginAmount', '0.01'), ('minimumMargin', '0.01')]:
            price[field]['amount'] = value
        verify_price(offer, price, PricingPolicy('0.10', '0.01', 'fixture-1'))
        price['basePrice']['amount'] = '0.05'
        with self.assertRaises(SupplierError):
            verify_price(offer, price, PricingPolicy('0.10', '0.01', 'fixture-1'))

    def test_revision_clears_old_review_and_approval_even_if_new_input_invalid(self):
        self.context['candidate']['commercialTerms'] = ['Restricted exclusive commitment']
        self.assertEqual(self.run_offer()['status'], 'APPROVAL_PENDING')
        old = self.repository.current('offer-001')['offer']
        self.context['candidate'].pop('supplierCost')
        self.assertEqual(self.run_offer()['status'], 'FAILURE')
        self.assertEqual(self.runtime.find_selectable({}, AT), [])
        current = self.repository.current('offer-001')
        self.assertIsNone(current['offer'])
        self.assertEqual(old['materialVersion'], 1)
        self.assertEqual(len(self.repository.history('offer-001')), 2)

    def decision(self, identity='operator-001', decision='APPROVE'):
        pending = deepcopy(self.approvals.records[-1])
        pending.update(status='DECIDED', decision=decision, operatorId=identity,
                       decidedAt=AT, reason='Explicit synthetic test decision')
        return pending

    def test_restricted_terms_need_persisted_authorised_current_human_decision(self):
        self.context['candidate']['commercialTerms'] = ['Restricted exclusive commitment']
        self.assertEqual(self.run_offer()['status'], 'APPROVAL_PENDING')
        decision = self.decision()
        with self.assertRaises(SupplierError):
            self.runtime.apply_decision(decision)
        self.approvals.save(decision)
        self.assertEqual(self.runtime.apply_decision(decision)['status'], 'SUCCESS')
        self.assertEqual(len(self.runtime.find_selectable({}, AT)), 1)
        # A new source revision invalidates the previously authorised version.
        self.assertEqual(self.run_offer()['status'], 'APPROVAL_PENDING')
        with self.assertRaises(SupplierError):
            self.runtime.apply_decision(decision)
        self.assertEqual(self.runtime.find_selectable({}, AT), [])

    def test_unknown_operator_and_wrong_scope_cannot_approve(self):
        self.context['candidate']['commercialTerms'] = ['Binding commitment']
        self.run_offer()
        for mutate in [lambda d: d.update(operatorId='unknown'), lambda d: d.update(scope='payment'),
                       lambda d: d.update(reviewId='wrong-review')]:
            decision = self.decision()
            mutate(decision)
            self.approvals.save(decision)
            with self.assertRaises(SupplierError):
                self.runtime.apply_decision(decision)
        self.assertEqual(self.runtime.find_selectable({}, AT), [])

    def test_review_for_wrong_version_and_stale_source_block_release(self):
        review = self.runtime.reviewer.review
        def wrong(*args):
            result = review(*args)
            result['subject']['materialVersion'] += 1
            return result
        self.runtime.reviewer.review = wrong
        self.assertEqual(self.run_offer()['errors'][0]['code'], 'REVIEW_FAILED')
        self.context['sourceReferences'][0]['freshness'] = 'STALE'
        self.assertEqual(self.run_offer()['errors'][0]['code'], 'STALE_EVIDENCE')

    def test_trace_and_snapshot_save_failure_cannot_leave_selectable_offer(self):
        with patch.object(self.traces, 'append', side_effect=OSError('disk unavailable')):
            self.assertEqual(self.run_offer()['errors'][0]['code'], 'PERSISTENCE_FAILED')
        self.assertEqual(self.runtime.find_selectable({}, AT), [])
        with patch.object(self.repository, 'save', side_effect=OSError('disk unavailable')):
            self.assertEqual(self.run_offer()['errors'][0]['code'], 'PERSISTENCE_FAILED')
        self.assertEqual(self.runtime.find_selectable({}, AT), [])

    def test_unconfirmed_and_unauthorised_sources_do_not_invalidate_existing_offer(self):
        self.run_offer()
        self.case['status'] = 'WITHDRAWN'
        self.assertEqual(self.run_offer()['errors'][0]['code'], 'UNCONFIRMED_REQUEST')
        self.assertEqual(len(self.runtime.find_selectable({}, AT)), 1)
        self.case['status'] = 'CONFIRMED'
        self.case['requesterId'] = 'unknown'
        self.assertEqual(self.run_offer()['errors'][0]['code'], 'ACCESS_DENIED')
        self.assertEqual(len(self.runtime.find_selectable({}, AT)), 1)

    def test_extraction_preserves_evidence_and_rejects_fabricated_cost_or_approval(self):
        candidate = deepcopy(self.context.pop('candidate'))
        self.context.update(sourceText='Untrusted supplier document',
                            verifiedFacts={key: deepcopy(candidate[key]) for key in ('supplierCost', 'unitBasis', 'quotedQuantity')})
        class LLM:
            def extract(inner, text, schema):
                self.assertFalse(schema['additionalProperties'])
                return deepcopy(candidate)
        self.runtime.llm = LLM()
        self.assertEqual(self.run_offer()['status'], 'SUCCESS')
        candidate['supplierCost']['amount'] = '1.00'
        self.assertEqual(self.run_offer()['errors'][0]['code'], 'VERIFICATION_FAILED')
        candidate['supplierCost']['amount'] = '180.00'
        candidate['status'] = 'APPROVED'
        self.assertEqual(self.run_offer()['errors'][0]['code'], 'OFFER_INVALID')

    def test_late_assessment_cannot_overwrite_newer_revision(self):
        self.run_offer()
        old = self.repository.current('offer-001')
        self.repository.reserve('offer-001', self.case['caseId'], 'FIXTURE', 'supplier-001')
        with self.assertRaises(SupplierError):
            self.repository.save('offer-001', 1, old)
        self.assertEqual(self.runtime.find_selectable({}, AT), [])

    def test_failed_revision_retains_owner_and_cannot_mix_fixture_and_real_identity(self):
        self.run_offer()
        self.context['candidate'].pop('supplierCost')
        self.run_offer()
        with self.assertRaises(SupplierError) as denied:
            self.repository.reserve('offer-001', 'another-case', 'FIXTURE', 'another-supplier')
        self.assertEqual(denied.exception.code, 'ACCESS_DENIED')
        with self.assertRaises(SupplierError) as mixed:
            self.repository.reserve('offer-001', 'another-case', 'REAL', 'supplier-001')
        self.assertEqual(mixed.exception.code, 'VERIFICATION_FAILED')


if __name__ == '__main__':
    unittest.main()
