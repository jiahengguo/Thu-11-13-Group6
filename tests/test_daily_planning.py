from copy import deepcopy
import json
import unittest
import tempfile
from pathlib import Path

from tripmate.agents.planning import TravelPlanningAgent
from tripmate.planning.application import accept_proposal
from tripmate.planning.common import PlanningError, money
from tripmate.planning.daily_demo import daily_fixture
from tripmate.planning.campus import ModelPlanningEngine


class DailyPlanningTests(unittest.TestCase):
    def setUp(self):
        self.case,self.context,self.runtime=daily_fixture()
        self.addCleanup(self.runtime.repository.close)
        self.policy=self.context['spec']['constraintBindings']['daily']['value']
        self.facts=self.runtime.factors.data

    def run_plan(self):
        return TravelPlanningAgent(self.runtime).handle_case(self.case)

    def record(self):
        result=self.run_plan()
        self.assertEqual(result['status'],'SUCCESS',result['errors'])
        return self.runtime.repository.get_version(result['subjects'][0]['subjectId'])

    def assert_rejected(self):
        result=self.run_plan()
        self.assertEqual(result['status'],'FAILURE')
        self.assertEqual(result['subjects'],[])
        return result

    def test_multicity_transfers_multi_activity_and_rain_alternative(self):
        record=self.record()
        ids=[i['offerId'] for i in record['version']['items']]
        self.assertIn('indoor-aquarium',ids)
        self.assertNotIn('outdoor-garden',ids)
        self.assertEqual(len(ids),9)
        self.assertEqual(record['metrics']['transfers'],1)
        self.assertEqual(record['version']['totalPrice'],money('851.50'))
        self.assertTrue(all(c['outcome']=='PASS' for c in record['version']['validationResults']))
        self.assertEqual(record['dailySchedule']['additionalCost'],money('120.00'))
        timeline=record['dailySchedule']['timeline']
        self.assertEqual(len([e for e in timeline if e['kind']=='MEAL']),5)
        self.assertTrue(any(e['kind']=='REST' for e in timeline))
        for a,b in zip(timeline,timeline[1:]):
            self.assertLessEqual(a['endAt'],b['startAt'])

    def test_delay_breaks_interchange(self):
        self.facts['delays'][0]['arrivalDelayMinutes']=60
        result=self.assert_rejected()
        self.assertTrue(any(c['ruleId']=='DAILY_CONNECTION' and c['outcome']=='FAIL' for c in result['validationResults']))

    def test_cancelled_transport_rejected(self):
        self.facts['delays'][0]['status']='CANCELLED'
        self.assert_rejected()

    def test_missing_route_is_not_free_teleportation(self):
        self.facts['routes']=self.facts['routes'][1:]
        self.assert_rejected()

    def test_missing_forecast_blocks_unqualified_success(self):
        self.facts['weather']=[]
        self.assert_rejected()

    def test_stale_facts_block_generation(self):
        self.facts['venues'][0]['validUntil']=self.runtime.clock()
        self.assertEqual(self.assert_rejected()['errors'][0]['code'],'STALE_EVIDENCE')

    def test_venue_calendar_exception_and_capacity(self):
        for field,value in [('remainingCapacity',0),('reservationStatus','SOLD_OUT')]:
            with self.subTest(field=field):
                original=deepcopy(self.facts['venues'][0])
                self.facts['venues'][0][field]=value
                self.assert_rejected()
                self.facts['venues'][0]=original
        v=self.facts['venues'][0]
        v['closedIntervals']=deepcopy(v['openIntervals'])
        self.assert_rejected()

    def test_walking_and_activity_load(self):
        self.policy['limits']['maxWalkingMinutes']=20
        self.assert_rejected()
        self.policy['limits']['maxWalkingMinutes']=180
        self.policy['limits']['maxActivityMinutes']=60
        self.assert_rejected()

    def test_insufficient_rest_is_not_silently_relaxed(self):
        self.policy['limits']['maxContinuousMinutes']=120
        self.assert_rejected()

    def test_meal_window_cannot_overlap_activity(self):
        self.policy['mealWindows']=[{'start':'10:00','end':'10:30','minutes':30}]
        self.assert_rejected()

    def test_meals_and_route_costs_count_towards_budget(self):
        self.context['request']['budgetCeiling']=money('800.00')
        self.context['spec']['constraintBindings']['budget']['value']=money('800.00')
        self.assert_rejected() # quoted items 731.50 alone fit; full allowance does not.

    def test_route_party_basis_must_match(self):
        self.facts['routes'][0]['partySize']=2
        self.assert_rejected()

    def test_wrong_city_accommodation_rejected(self):
        q=next(q for q in self.runtime.offers.quotes if q['offer']['offerId']=='canberra-stay')
        q['product']['origin']=q['product']['destination']='Sydney Central'
        self.assert_rejected()

    def test_factors_change_between_proposal_and_adoption(self):
        r=self.record()
        self.facts['venues'][0]['reservationStatus']='SOLD_OUT'
        with self.assertRaisesRegex(PlanningError,'snapshot changed'):
            accept_proposal(self.runtime,'demo-traveller',r['version']['versionId'],None,accepted=True)
        self.assertIsNone(self.runtime.repository.selected(r['version']['planId']))

    def test_daily_adoption_preserves_schedule_and_is_repeat_safe(self):
        r=self.record()
        adopted=accept_proposal(self.runtime,'demo-traveller',r['version']['versionId'],None,accepted=True)
        self.assertEqual(adopted['dailySchedule'],r['dailySchedule'])
        self.assertEqual(accept_proposal(self.runtime,'demo-traveller',r['version']['versionId'],None,accepted=True),adopted)

    def test_revision_keeps_baseline_and_confirms_policy_changes(self):
        r=self.record()
        self.case['caseType']='PLAN_REVISION'
        req=self.context['request']
        req.update(baselineVersionId=r['version']['versionId'],constraintSetVersion=2,confirmedChangedFields=['hardConstraints'])
        req['hardConstraints'][-1]['description']='Confirmed lower walking tolerance'
        self.context['spec']['constraintBindings']['daily']['description']='Confirmed lower walking tolerance'
        self.policy['limits']['maxWalkingMinutes']=170
        revised=self.record()
        self.assertIn('comparison',revised)
        self.assertEqual(self.runtime.repository.get_version(r['version']['versionId']),r)

    def test_no_factor_adapter_fails_closed(self):
        self.runtime.factors=None
        self.assertEqual(self.assert_rejected()['errors'][0]['code'],'TOOL_UNAVAILABLE')

    def test_unknown_model_offer_and_repair_feedback(self):
        groups=[s['offerIds'][0] for s in self.policy['slots']]
        repaired=groups[:-1]+['indoor-aquarium']
        class Client:
            model='TEST_DOUBLE'
            def __init__(self):self.calls=[]
            def chat(self,messages):
                self.calls.append(deepcopy(messages))
                return json.dumps({'candidates':[groups if len(self.calls)==1 else repaired],'explanation':'test'})
        client=Client()
        self.runtime.planner=ModelPlanningEngine(client,self.runtime.clock)
        r=self.record()
        self.assertEqual(len(client.calls),2)
        self.assertIn('DAILY_WEATHER',client.calls[1][-1]['content'])
        self.assertEqual(r['modelPlanning']['attempts'][0]['toolFeedback'][0]['checks'][0]['outcome'],'FAIL')

    def test_daily_policy_is_structurally_validated(self):
        self.policy['limits']['maxWalkingMinutes']=-1
        self.assertEqual(self.assert_rejected()['errors'][0]['code'],'INVALID_CONTRACT')

    def test_transfer_limit_counts_actual_legs(self):
        self.context['request']['hardConstraints'].append({'constraintId':'transfers','kind':'TRANSFER_LIMIT','description':'No transfers','confirmed':True})
        self.context['spec']['constraintBindings']['transfers']={'description':'No transfers','value':0}
        self.assert_rejected()

    def test_operations_confirm_daily_context_release_and_adopt(self):
        from tripmate.fixtures import FixtureRepository
        from tripmate.operations import OperationsService, OperationsRepository
        from tripmate.operations.integration import connect_planning
        from tripmate.planning.repository import PlanningRepository
        from tripmate.planning.integration import WorkbenchFixtureReviewer
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'daily.sqlite3'
            fixtures=FixtureRepository(path);fixtures.ensure_seeded()
            repo=PlanningRepository(path)
            try:
                ops=OperationsService(OperationsRepository(path),fixtures,clock=self.runtime.clock)
                connect_planning(ops,self.runtime.offers,WorkbenchFixtureReviewer(ops.clock),repo,factors=self.runtime.factors)
                req=self.context['request']
                fields={k:deepcopy(req[k]) for k in ['origin','destination','partySize','budgetCeiling','travelDates','rankingMode','preferences']}
                fields['constraints']=[{'kind':'OTHER','description':'Confirmed daily policy','value':deepcopy(self.policy)}]
                intents=[{'caseType':'TRAVEL_PLANNING','fields':fields}]
                intake=ops.intake('traveller:paid','intake','Daily itinerary',intents)
                cid=ops.confirm('traveller:paid','confirm',intake['id'],1,intents,True)['caseIds'][0]
                state=ops.dispatch('traveller:paid','dispatch',cid,1)
                self.assertEqual(state['case']['status'],'UNDER_REVIEW',state)
                ref=ops.repository.read('case',cid)['specialistResult']['subjects'][0]['subjectId']
                ops.review_case('operator:fixture','review',cid,state['revision'],'APPROVE','Checked daily simulation')
                state=ops.case_view('traveller:paid',cid)
                ops.deliver('traveller:paid','deliver',cid,state['revision'])
                view=ops.plan_view('traveller:paid',ref)
                self.assertIn('dailySchedule',view)
                self.assertNotIn('factorSnapshot',view)
                self.assertNotIn('supplierCost',json.dumps(view))
                self.assertTrue(ops.adopt_plan('traveller:paid','adopt',ref,None,True)['adopted'])
            finally:repo.close()
