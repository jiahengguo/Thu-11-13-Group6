"""UC-08 HTTP acceptance, source freshness, atomicity and UC-06/07 handoffs."""
import json
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

from test_portals import Browser
import test_supplier_portal as supplier_tests
from test_supplier import AT
from tripmate.planning.pricing import DeterministicPricingService
from tripmate.supplier.campaigns import INTROS


class DraftModel:
    def extract(self, content, schema):
        return {'intro': INTROS[0]}


class CampaignTests(unittest.TestCase):
    stop = supplier_tests.SupplierPortalTests.stop
    login = supplier_tests.SupplierPortalTests.login
    operation = supplier_tests.SupplierPortalTests.operation
    submission = supplier_tests.SupplierPortalTests.submission
    assess = supplier_tests.SupplierPortalTests.assess
    view = supplier_tests.SupplierPortalTests.view
    action = supplier_tests.SupplierPortalTests.action

    def setUp(self):
        supplier_tests.SupplierPortalTests.setUp(self)
        self.app = self.server.app
        self.at = AT
        self.app.operations.clock = lambda: self.at
        self.app.operations.entitlement.clock = lambda: self.at
        self.app.supplier.runtime.clock = lambda: self.at
        pricing = DeterministicPricingService('0.10', {'amount': '15.00', 'currency': 'AUD'}, 'fixture-1', lambda: self.at)
        self.app.supplier.pricing = self.app.supplier.runtime.pricing = pricing
        self.case_id = self.assess()
        self.login(self.operator)
        self.action(self.case_id)
        self.offer_id = self.view(self.case_id)['offer']['offerId']
        self.app.operations.llm = DraftModel()

    def brief(self, **changes):
        b = dict(objective='Show approved travel offers', audience='Domestic Free travellers',
            audienceTiers=['FREE'], channel='SIMULATED_EMAIL', startAt='2026-10-12T10:01:00+11:00',
            endAt='2026-10-15T10:00:00+11:00', budget='50.00', units=20,
            restrictions=['No personal targeting', 'No guaranteed outcomes'], offerIds=[self.offer_id], memberOffer=None)
        b.update(changes)
        return b

    def post(self, action, body, expected=200):
        result = self.browser.call('/api/campaigns/' + action, dict(requestKey=str(uuid4()), **body))
        self.assertEqual(result[0], expected, result[1])
        return result[1]

    def save(self, brief=None, current=None):
        return self.post('save', dict(campaignId=current['campaignId'] if current else None,
            revision=current['revision'] if current else 0, confirmed=True, brief=brief or self.brief()))

    def evaluate(self, current):
        return self.post('evaluate', dict(campaignId=current['campaignId'], revision=current['revision']))

    def decide(self, current, decision='APPROVE', expected=200):
        return self.post('decide', dict(campaignId=current['campaignId'], revision=current['revision'],
            decision=decision, reason='Checked supplier sources, restrictions and exact simulated budget.'), expected)

    def approved(self, member=False):
        benefit = dict(eligibleTiers=['FREE'], discount='2.00', validFrom='2026-10-12T10:01:00+11:00',
                       validUntil='2026-10-14T10:00:00+11:00') if member else None
        return self.decide(self.evaluate(self.save(self.brief(memberOffer=benefit))))

    def test_end_to_end_sourced_budget_human_approval_and_history(self):
        draft = self.save()
        pending = self.evaluate(draft)
        self.assertEqual(pending['status'], 'AWAITING_APPROVAL')
        self.assertFalse(pending['approved'])
        self.assertEqual(pending['proposal']['costItems']['total']['amount'], '50.00')
        self.assertIn('AUD 198.00', pending['proposal']['content'])
        self.assertEqual(pending['review']['outcome'], 'PASS')
        approved = self.decide(pending)
        status, value, _ = self.browser.call('/api/campaigns/view?campaignId=' + approved['campaignId'])
        self.assertEqual(status, 200)
        self.assertTrue(value['usable'])
        self.assertEqual([x['eventType'] for x in value['history']], ['VERSION_CREATED', 'REVIEW', 'APPROVAL_DECIDED'])
        self.assertFalse(any('publish' in path or 'spend' in path for path, _ in self.cloud.requests))

    def test_missing_brief_and_unconfirmed_input_do_not_invent_facts(self):
        for field in ['budget', 'startAt', 'objective', 'offerIds', 'restrictions']:
            brief = self.brief()
            del brief[field]
            self.post('save', dict(campaignId=None, revision=0, confirmed=True, brief=brief), 422)
        self.post('save', dict(campaignId=None, revision=0, confirmed=False, brief=self.brief()), 409)
        self.assertEqual(self.app.operations.repository.list('campaign'), [])

    def test_over_budget_and_paid_advertising_cannot_reach_approval(self):
        for changes, code in [(dict(budget='49.99'), 'BUDGET_EXCEEDED'), (dict(audienceTiers=['PAID']), 'ACCESS_DENIED')]:
            failed = self.evaluate(self.save(self.brief(**changes)))
            self.assertEqual(failed['status'], 'REVISION_REQUIRED')
            self.assertIn(code, failed['issues'][0])
            self.decide(failed, expected=409)

    def test_unknown_channel_or_cost_and_invalid_date_basis_rejected(self):
        self.post('save', dict(campaignId=None, revision=0, confirmed=True,
            brief=self.brief(channel='LIVE_ADS')), 422)
        b = self.brief()
        b['unitCost'] = '0.00'
        self.post('save', dict(campaignId=None, revision=0, confirmed=True, brief=b), 422)
        failed = self.evaluate(self.save(self.brief(endAt='2026-10-21T00:00:00Z')))
        self.assertIn('OFFER_INVALID', failed['issues'][0])

    def test_missing_model_and_unsupported_claims_fail_closed(self):
        for model, code in [(None, 'TOOL_UNAVAILABLE'), (object(), 'TOOL_UNAVAILABLE')]:
            self.app.operations.llm = model
            failed = self.evaluate(self.save())
            self.assertIn(code, failed['issues'][0])
            self.assertFalse(failed['approved'])
        model = DraftModel()
        model.extract = lambda *args: {'intro': 'Guaranteed best price, unlimited availability and free refunds!'}
        self.app.operations.llm = model
        failed = self.evaluate(self.save())
        self.assertIn('REVIEW_FAILED', failed['issues'][0])

    def test_operator_only_routes_csrf_and_strict_request_fields(self):
        for actor in [self.owner, self.traveller]:
            self.login(actor)
            for path in ['/campaigns', '/api/campaigns', '/api/campaigns/catalog']:
                self.assertEqual(self.browser.call(path)[0], 403, path)
            self.post('save', dict(campaignId=None, revision=0, confirmed=True, brief=self.brief()), 403)
        self.login(self.operator)
        self.assertEqual(self.browser.call('/campaigns')[0], 200)
        self.assertEqual(self.browser.call('/api/campaigns/save', {}, {'X-CSRF-Token': 'bad'})[0], 403)
        self.post('save', dict(campaignId=None, revision=0, confirmed=True, brief=self.brief(), approved=True), 422)

    def test_reject_and_request_revision_require_a_new_material_version(self):
        for decision, state in [('REJECT', 'REJECTED'), ('REQUEST_REVISION', 'REVISION_REQUIRED')]:
            pending = self.evaluate(self.save())
            record = self.decide(pending, decision)
            self.assertEqual(record['status'], state)
            self.assertFalse(record['approved'])
            self.decide(record, expected=409)
            revised = self.save(current=record)
            self.assertEqual(revised['materialVersion'], 2)

    def test_material_revision_preserves_snapshots_and_withdraws_rule(self):
        old = self.approved(member=True)
        snapshot = self.app.operations.repository.read('campaign_proposal', old['campaignId'] + '/1')
        new = self.save(self.brief(budget='60.00'), old)
        self.assertEqual(new['status'], 'DRAFT')
        self.assertFalse(new['approved'])
        self.assertFalse(self.app.operations.repository.read('member_offer', old['memberOfferRuleId'])['approved'])
        self.assertEqual(snapshot, self.app.operations.repository.read('campaign_proposal', old['campaignId'] + '/1'))
        self.decide(old, expected=409)

    def test_stale_or_expired_supplier_source_invalidates_approval_on_reopen(self):
        record = self.approved(member=True)
        with self.app.operations.repository.transaction() as rows:
            pointer = rows.get('supplier_current', self.offer_id)
            rows.put('supplier_current', self.offer_id, dict(pointer, invalidated=True))
        status, current, _ = self.browser.call('/api/campaigns/view?campaignId=' + record['campaignId'])
        self.assertEqual(status, 200)
        self.assertEqual(current['status'], 'REVISION_REQUIRED')
        self.assertFalse(current['usable'])
        self.assertFalse(self.app.operations.repository.read('member_offer', record['memberOfferRuleId'])['approved'])

    def test_failed_persistence_has_no_partial_approval_or_rule(self):
        current = self.evaluate(self.save(self.brief(memberOffer=dict(eligibleTiers=['FREE'], discount='2.00',
            validFrom='2026-10-12T10:01:00+11:00', validUntil='2026-10-14T10:00:00+11:00'))))
        before = deepcopy(self.cloud.state)
        self.cloud.fail_commit = True
        self.decide(current, expected=503)
        self.assertEqual(before, self.cloud.state)
        self.cloud.fail_commit = False
        self.assertTrue(self.decide(current)['approved'])

    def test_idempotent_decision_and_conflicting_retry_keys(self):
        current = self.evaluate(self.save())
        body = dict(requestKey=str(uuid4()), campaignId=current['campaignId'], revision=current['revision'],
                    decision='APPROVE', reason='Checked exact current version.')
        first = self.browser.call('/api/campaigns/decide', body)
        version = self.cloud.state['version']
        again = self.browser.call('/api/campaigns/decide', body)
        self.assertEqual(first[:2], again[:2])
        self.assertEqual(version, self.cloud.state['version'])
        self.assertEqual(self.browser.call('/api/campaigns/decide', dict(body, decision='REJECT'))[0], 409)

    def test_member_quotation_uses_live_eligibility_and_keeps_base_offer(self):
        record = self.approved(member=True)
        base = deepcopy(self.app.supplier.repository.current(self.offer_id))
        self.at = '2026-10-12T10:02:00+11:00'
        self.login(self.traveller)
        result = self.post('quote', dict(memberOfferRuleId=record['memberOfferRuleId'], offerId=self.offer_id))
        self.assertEqual(result['quotation']['sellingPrice']['amount'], '196.00')
        self.assertNotIn('supplierCost', json.dumps(result))
        self.assertNotIn('marginAmount', json.dumps(result))
        self.assertEqual(base, self.app.supplier.repository.current(self.offer_id))
        self.cloud.accounts[self.traveller].update(membership='PAID', paidUntil='2026-10-16T00:00:00Z')
        self.post('quote', dict(memberOfferRuleId=record['memberOfferRuleId'], offerId=self.offer_id), 403)

    def test_discount_margin_fail_expiry_and_no_stacking(self):
        b = self.brief(memberOffer=dict(eligibleTiers=['FREE'], discount='5.00',
            validFrom='2026-10-12T10:01:00+11:00', validUntil='2026-10-14T10:00:00+11:00'))
        record = self.decide(self.evaluate(self.save(b)))
        self.at = '2026-10-12T10:02:00+11:00'
        self.login(self.traveller)
        body = dict(memberOfferRuleId=record['memberOfferRuleId'], offerId=self.offer_id)
        self.post('quote', body, 422)
        self.post('quote', dict(body, extraDiscount='1.00'), 422)
        self.at = '2026-10-15T10:00:00+11:00'
        self.post('quote', body, 403)
        self.assertEqual(self.app.supplier.repository.current(self.offer_id)['offer']['status'], 'APPROVED')

    def test_simulated_response_reaches_operations_with_source_and_consent(self):
        record = self.approved()
        self.at = '2026-10-12T10:02:00+11:00'
        self.login(self.traveller)
        body = dict(text='I would like travel information from this simulated campaign.',
            intents=[{'caseType': 'ROUTINE_ENQUIRY', 'fields': {'details': 'Simulated travel information request'}}],
            campaignId=record['campaignId'], channel='SIMULATED_CAMPAIGN', consent=True)
        intake = self.operation('intake', body)
        self.assertEqual(intake['campaignId'], record['campaignId'])
        self.assertEqual(intake['sourceChannel'], 'SIMULATED_CAMPAIGN')
        self.assertEqual(intake['campaignMaterialVersion'], 1)
        self.assertTrue(any(ref['sourceId'].endswith(record['campaignId'] + ':1') for ref in intake['sources']))
        self.assertEqual(self.app.operations.repository.read('lead', intake['id'])['campaignId'], record['campaignId'])
        self.assertEqual(self.browser.call('/api/operations/intake', dict(body, consent=False, requestKey=str(uuid4())))[0], 403)
        self.cloud.accounts[self.traveller].update(membership='PAID', paidUntil='2026-10-16T00:00:00Z')
        self.assertEqual(self.browser.call('/api/operations/intake', dict(body, requestKey=str(uuid4())))[0], 403)

    def test_member_benefit_catalog_hides_internal_data_and_ineligible_rules(self):
        self.approved(member=True)
        self.at = '2026-10-12T10:02:00+11:00'
        self.login(self.traveller)
        status, data, _ = self.browser.call('/api/campaigns/benefits')
        self.assertEqual(status, 200)
        self.assertEqual(len(data['benefits']), 1)
        self.assertNotIn('supplierCost', json.dumps(data))
        self.assertNotIn('content', json.dumps(data))
        self.cloud.accounts[self.traveller].update(membership='PAID', paidUntil='2026-10-16T00:00:00Z')
        self.assertEqual(self.browser.call('/api/campaigns/benefits')[1]['benefits'], [])
        self.login(self.operator)
        self.assertEqual(self.browser.call('/api/campaigns/benefits')[0], 403)

    def test_confirmed_privacy_restrictions_block_sourced_personal_contact(self):
        with self.app.operations.repository.transaction() as rows:
            key = self.app.supplier.repository.key(self.offer_id, 1)
            current = rows.get('supplier_version', key)
            current['offer']['cancellationTerms'] = 'Contact qa@example.invalid to cancel.'
            rows.put('supplier_version', key, current)
        record = self.evaluate(self.save())
        self.assertEqual(record['status'], 'REVISION_REQUIRED')
        self.assertIn('REVIEW_FAILED', record['issues'][0])

    def test_source_revision_during_drafting_cannot_commit_an_old_proposal(self):
        record = self.save()
        def revise(*args):
            with self.app.operations.repository.transaction() as rows:
                pointer = rows.get('supplier_current', self.offer_id)
                rows.put('supplier_current', self.offer_id, dict(pointer, invalidated=True))
            return {'intro': INTROS[0]}
        self.app.operations.llm.extract = revise
        result = self.post('evaluate', dict(campaignId=record['campaignId'], revision=record['revision']), 409)
        self.assertEqual(result['error'], 'UNCONFIRMED_REQUEST')
        current = self.app.operations.repository.read('campaign', record['campaignId'])
        self.assertFalse(current['approved'])
        self.assertIsNone(self.app.operations.repository.read('campaign_proposal', record['campaignId'] + '/1'))

    def test_sqlite_reopen_retains_campaign_proposal_decision_and_history(self):
        from pathlib import Path
        from tripmate.operations import OperationsService
        from tripmate.operations.repository import OperationsRepository
        from tripmate.portal.repository import NoUserFixtures
        from tripmate.supplier.gateway import SupplierGateway
        from tripmate.supplier.campaigns import CampaignService
        current = self.approved(member=True)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'campaign.sqlite3'
            repository = OperationsRepository(path)
            with repository.transaction() as rows:
                for item in self.cloud.state['records']:
                    rows.put(item['kind'], item['id'], item['payload'])
                for actor, profile in self.cloud.accounts.items():
                    rows.put('profile', actor, profile)
            # Construct fresh services and connections; do not reuse in-memory campaign objects.
            ops = OperationsService(OperationsRepository(path), NoUserFixtures(), clock=lambda: self.at, seed_profiles=False)
            supplier = SupplierGateway(ops, self.app.supplier.pricing, self.app.supplier.policy)
            service = CampaignService(ops, supplier)
            reloaded = service.view(self.operator, current['campaignId'])
            self.assertTrue(reloaded['usable'])
            self.assertEqual(reloaded['decision'], current['decision'])
            self.assertEqual(len(reloaded['history']), 3)
            self.assertEqual(reloaded['proposal'], current['proposal'])

    def test_human_decision_after_campaign_start_still_checks_current_sources(self):
        current = self.evaluate(self.save())
        self.at = '2026-10-12T10:02:00+11:00'
        self.assertTrue(self.decide(current)['approved'])

    def test_anonymous_campaign_link_retains_context_through_sign_in(self):
        anonymous = Browser(self.root)
        campaign_id = 'approved-campaign-context'
        with anonymous.client.open(self.root + '/app?campaign=' + campaign_id) as response:
            self.assertEqual(response.status, 200)
            self.assertTrue(response.geturl().endswith('/login?campaign=' + campaign_id))


if __name__ == '__main__':
    unittest.main()
