"""Authenticated Supplier -> Planning -> reviewed delivery -> atomic adoption."""
import json
import threading
import unittest
from copy import deepcopy
from uuid import uuid4
from unittest.mock import patch

from test_portals import Browser, FakeCloud
from tripmate.fixtures.b03 import fixture_quotes, FIXTURE_TIME
from tripmate.portal.server import make_server, Portal
from tripmate.supplier.common import PricingPolicy, SOURCE_FIELDS
from tripmate.planning.common import PlanningError


class PlanningPortalTests(unittest.TestCase):
    def setUp(self):
        self.cloud = FakeCloud()
        self.traveller, _ = self.cloud.add()
        self.other, _ = self.cloud.add()
        self.supplier, _ = self.cloud.add('SUPPLIER')
        self.operator, _ = self.cloud.add('OPERATOR')
        self.policy = PricingPolicy('0.10', '15.00', 'demo-2026-10-24')
        self.server = make_server(self.cloud, port=0, supplier_policy=self.policy)
        self.app = self.server.app
        self.app.operations.clock = lambda: FIXTURE_TIME
        self.app.operations.entitlement.clock = lambda: FIXTURE_TIME
        self.app.supplier.runtime.clock = lambda: FIXTURE_TIME
        self.app.supplier.pricing.clock = lambda: FIXTURE_TIME
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.root = 'http://127.0.0.1:' + str(self.server.server_port)
        self.clients = {}
        for actor in (self.traveller, self.other, self.supplier, self.operator):
            client = Browser(self.root)
            self.assertEqual(client.login(actor)[0], 200)
            self.clients[actor] = client
        self.seed_offers()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def post(self, actor, action, body):
        status, data, _ = self.clients[actor].call('/api/operations/' + action, dict(body, requestKey=str(uuid4())))
        self.assertEqual(status, 200, data)
        return data

    def confirm(self, actor, case_type, fields):
        intents = [dict(caseType=case_type, fields=fields)]
        intake = self.post(actor, 'intake', dict(text='Explicitly confirmed simulated request.', intents=intents))
        confirmed = self.post(actor, 'confirm', dict(intakeId=intake['id'], revision=intake['revision'],
                                                    intents=intents, confirmed=True))
        return confirmed['caseIds'][0]

    def seed_offers(self, restricted=False):
        for quote in fixture_quotes():
            if quote['offer']['offerId'] not in ('coach', 'express', 'basic-stay', 'walk'):
                continue
            source = quote['offer']
            submission = {key: deepcopy(source[key]) for key in SOURCE_FIELDS if key != 'supplierId'}
            # Explicit test inventory meets the authorised demo policy, including activities.
            submission.update(supplierCost=dict(amount='180.00', currency='AUD'), commercialTerms=['Restricted exclusive commitment'] if restricted else [],
                              offerReference=source['offerId'], sourceReference='synthetic://portal/' + source['offerId'],
                              product={key: deepcopy(value) for key, value in quote['product'].items()
                                       if key not in ('productId', 'sourceIds')})
            cid = self.confirm(self.supplier, 'OFFER', dict(details='Simulated service package.', supplierOffer=submission))
            dispatched = self.post(self.supplier, 'dispatch', dict(caseId=cid, revision=1))
            assessment = self.clients[self.operator].call('/api/supplier/assessment?caseId=' + cid)[1]
            status, data, _ = self.clients[self.operator].call('/api/supplier/review', dict(
                caseId=cid, revision=dispatched['revision'], materialVersion=assessment['offer']['materialVersion'],
                decision='PASS', reason='Checked source and configured simulated prices.', requestKey=str(uuid4())))
            self.assertEqual(status, 200, data)
            if restricted:
                self.assertEqual(data['status'], 'AWAITING_APPROVAL', data)
                pending = self.clients[self.operator].call('/api/operations/case?caseId=' + cid)[1]
                status, data, _ = self.clients[self.operator].call('/api/supplier/decision', dict(
                    caseId=cid, revision=pending['revision'], materialVersion=assessment['offer']['materialVersion'],
                    decision='APPROVE', reason='Approve exact synthetic restricted terms.', requestKey=str(uuid4())))
                self.assertEqual(status, 200, data)
            self.assertEqual(data['status'], 'APPROVED', data)

    def generate(self, baseline=None, budget='900.00', member_quote=None):
        fields = dict(origin='Sydney Central', destination='Melbourne Centre', partySize=1,
                      budgetCeiling=dict(amount=budget, currency='AUD'),
                      travelDates=dict(startDate='2026-10-20', endDate='2026-10-22'),
                      rankingMode='VALUE', preferences=[], constraints=[])
        if member_quote:
            fields['memberQuoteId'] = member_quote
        if baseline:
            fields['baselineVersionId'] = baseline
        cid = self.confirm(self.traveller, 'PLAN_REVISION' if baseline else 'TRAVEL_PLANNING', fields)
        result = self.post(self.traveller, 'dispatch', dict(caseId=cid, revision=1))
        self.assertEqual(result['case']['status'], 'UNDER_REVIEW', result)
        record = self.app.operations.repository.read('case', cid)
        ids = [ref['subjectId'] for ref in record['specialistResult']['subjects']]
        return cid, ids, result

    def release(self, cid, revision):
        reviewed = self.post(self.operator, 'review', dict(caseId=cid, revision=revision, decision='APPROVE',
                               reason='Checked the shared Planning review and response.'))
        self.post(self.traveller, 'deliver', dict(caseId=cid, revision=reviewed['revision']))
        return self.clients[self.traveller].call('/api/operations/case?caseId=' + cid)[1]

    def adopt(self, vid, baseline=None, key=None):
        body = dict(versionId=vid, expectedBaseline=baseline, accepted=True, requestKey=key or str(uuid4()))
        return self.clients[self.traveller].call('/api/operations/adopt', body), body

    def test_operator_delivers_reviewed_plan_for_confirmed_requester(self):
        cid, ids, generated = self.generate()
        reviewed = self.post(self.operator, 'review', dict(caseId=cid, revision=generated['revision'],
                           decision='APPROVE', reason='Checked the exact requester plan and its review.'))
        body = dict(caseId=cid, revision=reviewed['revision'], requestKey=str(uuid4()))
        self.assertEqual(self.clients[self.other].call('/api/operations/deliver', body)[0], 403)
        status, delivered, _ = self.clients[self.operator].call('/api/operations/deliver', body)
        self.assertEqual(status, 200, delivered)
        self.assertTrue(delivered['delivered'])
        saved = self.clients[self.traveller].call('/api/operations/case?caseId=' + cid)[1]
        self.assertEqual(saved['case']['status'], 'CLOSED')
        self.assertEqual(self.clients[self.traveller].call('/api/operations/plan?versionId=' + ids[0])[0], 200)
        self.assertEqual(self.clients[self.other].call('/api/operations/plan?versionId=' + ids[0])[0], 403)
        self.assertEqual(self.clients[self.operator].call('/api/operations/plan?versionId=' + ids[0])[0], 403)

    def test_authenticated_plan_options_adoption_revision_and_restart(self):
        cid, ids, result = self.generate()
        self.assertGreater(len(ids), 1)
        self.assertNotIn('planVersionIds', result)
        self.assertNotEqual(self.clients[self.traveller].call('/api/operations/plan?versionId=' + ids[0])[0], 200)
        released = self.release(cid, result['revision'])
        self.assertEqual(released['planVersionIds'], ids)
        status, public, _ = self.clients[self.traveller].call('/api/operations/plan?versionId=' + ids[0])
        self.assertEqual(status, 200, public)
        self.assertEqual(public['version']['review']['policyVersion'], 'shared-deterministic-review-1')
        self.assertEqual(public['version']['totalPrice']['amount'], '594.00')
        self.assertNotIn('supplierCost', json.dumps(public))
        self.assertNotIn('quotes', public)
        self.assertEqual(self.clients[self.other].call('/api/operations/plan?versionId=' + ids[0])[0], 403)
        original = self.app.planning.get_version(ids[0])
        adopted, body = self.adopt(ids[0])
        self.assertEqual(adopted[0], 200, adopted[1])
        self.assertEqual(self.clients[self.traveller].call('/api/operations/adopt', body)[1], adopted[1])
        self.assertEqual(self.app.planning.get_version(ids[0]), original)
        self.assertEqual(self.adopt(ids[1])[0][0], 422)
        self.seed_offers()  # Current supplier material versions refresh; baseline remains immutable.
        revision_cid, revised_ids, revision = self.generate(ids[0], budget='850.00')
        self.release(revision_cid, revision['revision'])
        comparison = self.clients[self.traveller].call('/api/operations/plan?versionId=' + revised_ids[0])[1]
        self.assertIn('budgetCeiling', comparison['comparison']['changedRequirements'])
        self.assertTrue(comparison['comparison']['itineraryChanges'])
        self.assertTrue(all(item['before']['offerVersion'] == 1 and item['after']['offerVersion'] == 2
                            for item in comparison['comparison']['itineraryChanges']))
        self.assertNotIn('supplierCost', json.dumps(comparison))
        self.assertEqual(self.adopt(revised_ids[0], ids[0])[0][0], 200)
        restarted = Portal(self.cloud, supplier_policy=self.policy)
        self.assertEqual(restarted.planning.selected(original['version']['planId']), revised_ids[0])
        self.assertEqual(restarted.planning.get_version(ids[0]), original)
        trace = self.app.operations.traces(self.operator, cid)
        self.assertEqual(len(trace), len({event['eventId'] for event in trace}))
        self.assertTrue(any(event['actor'] == 'planning' for event in trace))

    def test_adoption_cloud_failure_rolls_back_selection_lifecycle_and_audit(self):
        cid, ids, result = self.generate()
        self.release(cid, result['revision'])
        before = deepcopy(self.cloud.state)
        self.cloud.fail_commit = True
        adopted, body = self.adopt(ids[0])
        self.assertNotEqual(adopted[0], 200)
        self.assertEqual(self.cloud.state, before)
        self.cloud.fail_commit = False
        self.assertIsNone(self.app.planning.selected(self.app.planning.get_version(ids[0])['version']['planId']))
        self.assertEqual(self.clients[self.traveller].call('/api/operations/adopt', body)[0], 200)

    def test_changed_supplier_source_blocks_adoption_and_forged_review(self):
        cid, ids, result = self.generate()
        self.release(cid, result['revision'])
        version = self.app.planning.get_version(ids[0])['version']
        with self.app.operations.repository.transaction() as rows:
            pointer = rows.get('supplier_current', version['items'][0]['offerId'])
            rows.put('supplier_current', version['items'][0]['offerId'], dict(pointer, invalidated=True))
        before = deepcopy(self.cloud.state)
        self.assertNotEqual(self.adopt(ids[0])[0][0], 200)
        self.assertEqual(self.cloud.state, before)
        from tripmate.planning.review import planning_reviewer
        checked = planning_reviewer(self.app.operations, self.app.supplier).review(
            version, version['sourceReferences'], ['planning-1.0'])
        self.assertEqual(checked['outcome'], 'REVISION_REQUIRED')

    def test_no_inventory_cannot_substitute_demo_catalog(self):
        with self.app.operations.repository.transaction() as rows:
            for pointer in rows.all('supplier_current'):
                rows.put('supplier_current', pointer['offerId'], dict(pointer, invalidated=True))
        self.app.fixtures.reset()
        fields = dict(origin='Sydney Central', destination='Melbourne Centre', partySize=1,
                      budgetCeiling=dict(amount='900.00', currency='AUD'),
                      travelDates=dict(startDate='2026-10-20', endDate='2026-10-22'), rankingMode='VALUE')
        cid = self.confirm(self.traveller, 'TRAVEL_PLANNING', fields)
        result = self.post(self.traveller, 'dispatch', dict(caseId=cid, revision=1))
        self.assertEqual(result['case']['status'], 'HUMAN_ASSISTANCE')
        self.assertIsNone(result['response'])
        self.assertNotIn('planVersionIds', result)

    def test_immutable_run_cannot_be_overwritten(self):
        cid, ids, _ = self.generate()
        run = self.app.operations.repository.read('case', cid)['specialistResult']
        before = deepcopy(self.cloud.state)
        with self.assertRaises(PlanningError):
            self.app.planning.save_run(run, [self.app.planning.get_version(ids[0])], [])
        self.assertEqual(self.cloud.state, before)

    def test_assessment_revision_requires_regeneration_and_handoff_is_durable(self):
        cid, ids, generated = self.generate()
        self.assertEqual(generated['planningAssessment']['state'], 'UNDER_REVIEW')
        revised = self.post(self.operator, 'review', dict(caseId=cid, revision=generated['revision'],
            decision='REQUEST_REVISION', reason='Please clarify the confirmed budget.'))
        self.assertEqual(revised['planningAssessment']['state'], 'REVISION_REQUIRED')
        status, _, _ = self.clients[self.operator].call('/api/operations/review',dict(requestKey=str(uuid4()),
            caseId=cid,revision=revised['revision'],decision='APPROVE',reason='Old proposal must not pass.'))
        self.assertEqual(status,409)
        fields = revised['fields']
        confirmed = self.post(self.traveller,'clarify',dict(caseId=cid,revision=revised['revision'],
            intents=[dict(caseType='TRAVEL_PLANNING',fields=fields)],confirmed=True))
        self.assertEqual(confirmed['planningAssessment']['state'],'DRAFT')
        regenerated = self.post(self.traveller,'dispatch',dict(caseId=cid,revision=confirmed['revision']))
        self.assertEqual(regenerated['planningAssessment']['state'],'UNDER_REVIEW')
        released = self.release(cid,regenerated['revision'])
        self.assertEqual(released['planningAssessment']['state'],'HANDED_OFF')
        restarted=Portal(self.cloud,supplier_policy=self.policy)
        self.assertEqual(restarted.operations.case_view(self.traveller,cid)['planningAssessment']['state'],'HANDED_OFF')

    def test_restricted_supplier_approval_is_preserved_through_planning_and_revocation_blocks_release(self):
        self.seed_offers(restricted=True)
        cid, ids, generated = self.generate()
        record = self.app.planning.get_version(ids[0])
        self.assertTrue(all(q['offer']['requiresApproval'] and q['approval']['decision'] == 'APPROVE' for q in record['quotes']))
        approval_id = record['quotes'][0]['approval']['approvalId'] + '/DECIDED'
        with self.app.operations.repository.transaction() as rows:
            approval = rows.get('supplier_approval', approval_id)
            approval['decision'] = 'REJECT'
            rows.put('supplier_approval', approval_id, approval)
        status, refused, _ = self.clients[self.operator].call('/api/operations/review', dict(requestKey=str(uuid4()),
            caseId=cid, revision=generated['revision'], decision='APPROVE', reason='Approval was revoked.'))
        self.assertEqual(status, 422)
        self.assertEqual(refused['error'], 'STALE_EVIDENCE')
        self.assertFalse(self.app.operations.repository.list('inbox'))

    def test_planning_phase_history_and_rejected_proposal_require_reconfirmation(self):
        cid, ids, generated = self.generate()
        events = [e['state'] for e in self.app.operations.repository.list('planning_assessment_event') if e['caseId'] == cid]
        self.assertEqual(events[:4], ['DRAFT', 'VALIDATING', 'FEASIBLE', 'UNDER_REVIEW'])
        original = self.app.planning.get_version(ids[0])
        rejected = self.post(self.operator, 'review', dict(caseId=cid, revision=generated['revision'], decision='REJECT', reason='Needs changed requirements.'))
        self.assertEqual(rejected['planningAssessment']['state'], 'REJECTED')
        body = dict(caseId=cid, revision=rejected['revision'], action='RETRY', reason='Cannot bypass rejection.', requestKey=str(uuid4()))
        self.assertNotEqual(self.clients[self.operator].call('/api/operations/planning-lifecycle', body)[0], 200)
        body.update(action='REOPEN', requestKey=str(uuid4()))
        self.assertEqual(self.clients[self.traveller].call('/api/operations/planning-lifecycle', body)[0], 403)
        status, reopened, _ = self.clients[self.operator].call('/api/operations/planning-lifecycle', body)
        self.assertEqual(status, 200, reopened)
        self.assertEqual(self.clients[self.operator].call('/api/operations/planning-lifecycle', body)[0], 200)
        self.assertEqual(reopened['case']['status'], 'AWAITING_REQUESTER')
        confirmed = self.post(self.traveller, 'clarify', dict(caseId=cid, revision=reopened['revision'],
            confirmed=True, intents=[dict(caseType='TRAVEL_PLANNING', fields=generated['fields'])]))
        renewed = self.post(self.traveller, 'dispatch', dict(caseId=cid, revision=confirmed['revision']))
        self.assertEqual(renewed['case']['status'], 'UNDER_REVIEW')
        self.assertEqual(original, self.app.planning.get_version(ids[0]))
        self.assertTrue(self.app.operations.case_view(self.operator, cid)['planningAssessment']['priorRunIds'])

    def test_technical_failure_can_retry_without_fabricated_approval(self):
        cid, _, generated = self.generate()
        revised = self.post(self.operator, 'review', dict(caseId=cid, revision=generated['revision'], decision='REQUEST_REVISION', reason='Regenerate.'))
        confirmed = self.post(self.traveller, 'clarify', dict(caseId=cid, revision=revised['revision'], confirmed=True,
            intents=[dict(caseType='TRAVEL_PLANNING', fields=generated['fields'])]))
        with patch('tripmate.planning.application.lookup', side_effect=TimeoutError('offline')):
            failed = self.post(self.traveller, 'dispatch', dict(caseId=cid, revision=confirmed['revision']))
        self.assertEqual(failed['planningAssessment']['state'], 'REVISION_REQUIRED')
        body = dict(requestKey=str(uuid4()), caseId=cid, revision=failed['revision'], decision='APPROVE',
                    reason='Cannot fabricate a passed result.', editedText='A supposedly successful plan.')
        self.assertNotEqual(self.clients[self.operator].call('/api/operations/review', body)[0], 200)
        ready = self.post(self.operator, 'planning-lifecycle', dict(caseId=cid, revision=failed['revision'], action='RETRY', reason='Provider restored.'))
        self.assertEqual(ready['case']['status'], 'CONFIRMED')
        renewed = self.post(self.traveller, 'dispatch', dict(caseId=cid, revision=ready['revision']))
        self.assertEqual(renewed['case']['status'], 'UNDER_REVIEW')

    def test_infeasible_and_pending_human_review_are_durable(self):
        cid, _, generated = self.generate()
        pending = self.post(self.operator, 'review', dict(caseId=cid, revision=generated['revision'], decision='TAKE_OVER', reason='Manual decision pending.'))
        self.assertEqual(pending['planningAssessment']['state'], 'AWAITING_HUMAN_REVIEW')
        reopened = self.post(self.operator, 'planning-lifecycle', dict(caseId=cid, revision=pending['revision'], action='REOPEN', reason='Confirm affordable requirements.'))
        fields = deepcopy(generated['fields']); fields['budgetCeiling']['amount'] = '1.00'
        confirmed = self.post(self.traveller, 'clarify', dict(caseId=cid, revision=reopened['revision'], confirmed=True,
            intents=[dict(caseType='TRAVEL_PLANNING', fields=fields)]))
        failed = self.post(self.traveller, 'dispatch', dict(caseId=cid, revision=confirmed['revision']))
        self.assertEqual(failed['planningAssessment']['state'], 'INFEASIBLE')
        restarted = Portal(self.cloud, supplier_policy=self.policy)
        self.assertEqual(restarted.operations.case_view(self.operator, cid)['planningAssessment']['state'], 'INFEASIBLE')

    def test_factor_input_is_operator_only_persisted_and_bound_to_confirmation(self):
        from tripmate.planning.daily_demo import daily_fixture
        case, context, runtime = daily_fixture()
        self.addCleanup(runtime.repository.close)
        cid = self.confirm(self.traveller, 'TRAVEL_PLANNING', dict(origin='Sydney Central', destination='Melbourne Centre',
            partySize=1, budgetCeiling=dict(amount='900.00', currency='AUD'),
            travelDates=dict(startDate='2026-10-20', endDate='2026-10-22'), rankingMode='VALUE', preferences=[], constraints=[]))
        data = deepcopy(runtime.factors.data)
        body = dict(requestKey=str(uuid4()), caseId=cid, revision=1, data=data, confirmed=True)
        self.assertEqual(self.clients[self.traveller].call('/api/planning/factors', body)[0], 403)
        status, saved, _ = self.clients[self.operator].call('/api/planning/factors', body)
        self.assertEqual(status, 200, saved)
        self.assertEqual(self.clients[self.operator].call('/api/planning/factors', body)[0], 200)
        restarted = Portal(self.cloud, supplier_policy=self.policy)
        self.assertEqual(restarted.factor_inputs.view(self.operator, cid)['snapshot']['data'], data)
        self.assertEqual(len(self.app.operations.repository.list('travel_factor_history')), 1)
        request=self.app.operations.load_context(cid)['request']
        self.assertEqual(self.app.factor_inputs.snapshot(request, [], FIXTURE_TIME), data)
        self.cloud.accounts[self.operator]['role']='TRAVELLER'
        with self.assertRaises(ValueError):
            self.app.factor_inputs.snapshot(request, [], FIXTURE_TIME)


    def test_member_discount_reaches_plan_and_revocation_blocks_adoption(self):
        from test_campaigns import DraftModel
        from tripmate.supplier.campaigns import INTROS
        self.app.operations.llm = DraftModel()
        offer = self.app.supplier.find_selectable({}, FIXTURE_TIME)[0]['offer']['offerId']
        brief = dict(objective='Approved travel benefit', audience='Free travellers', audienceTiers=['FREE'],
            channel='SIMULATED_EMAIL', startAt='2026-10-12T10:01:00+11:00', endAt='2026-10-15T10:00:00+11:00',
            budget='50.00', units=20, restrictions=['No personal targeting','No guaranteed outcomes'], offerIds=[offer],
            memberOffer=dict(eligibleTiers=['FREE'], discount='2.00', validFrom='2026-10-12T10:01:00+11:00', validUntil='2026-10-14T10:00:00+11:00'))
        def campaign(action, body):
            status, value, _ = self.clients[self.operator].call('/api/campaigns/'+action, dict(body, requestKey=str(uuid4())))
            self.assertEqual(status,200,value)
            return value
        saved=campaign('save',dict(campaignId=None,revision=0,confirmed=True,brief=brief))
        reviewed=campaign('evaluate',dict(campaignId=saved['campaignId'],revision=saved['revision']))
        approved=campaign('decide',dict(campaignId=saved['campaignId'],revision=reviewed['revision'],decision='APPROVE',reason='Approve exact simulated benefit.'))
        at='2026-10-12T10:02:00+11:00'
        self.app.operations.clock=lambda:at
        self.app.operations.entitlement.clock=lambda:at
        self.app.supplier.pricing.clock=lambda:at
        status, quoted, _=self.clients[self.traveller].call('/api/campaigns/quote',dict(requestKey=str(uuid4()),memberOfferRuleId=approved['memberOfferRuleId'],offerId=offer))
        self.assertEqual(status,200,quoted)
        quote_id=quoted['quotation']['priceBreakdownId']
        cid, ids, view=self.generate(member_quote=quote_id)
        record=self.app.planning.get_version(ids[0])
        wrong_owner=deepcopy(record['request']);wrong_owner['travellerId']=self.other
        with self.assertRaises(ValueError):
            self.app.planning_offers.find_selectable(wrong_owner,at)
        self.assertEqual(record['version']['totalPrice']['amount'],'592.00')
        self.assertEqual(sum(q['price']['discountAmount']['amount']=='2.00' for q in record['quotes']),1)
        self.release(cid,view['revision'])
        adopted=self.post(self.traveller,'adopt',dict(versionId=ids[0],expectedBaseline=None,accepted=True))
        self.assertIsNotNone(adopted)
        revised_cid, revised_ids, revised = self.generate(baseline=ids[0], budget='850.00', member_quote=quote_id)
        self.assertEqual(self.app.planning.get_version(revised_ids[0])['version']['totalPrice']['amount'], '592.00')
        self.release(revised_cid, revised['revision'])
        latest=self.clients[self.operator].call('/api/campaigns/view?campaignId='+approved['campaignId'])[1]
        campaign('save',dict(campaignId=approved['campaignId'],revision=latest['revision'],confirmed=True,brief=dict(brief,budget='60.00')))
        refused, _ = self.adopt(revised_ids[0], ids[0])
        self.assertNotEqual(refused[0], 200)
        with self.assertRaises(ValueError):
            self.app.operations.validate_planning_release(record)
