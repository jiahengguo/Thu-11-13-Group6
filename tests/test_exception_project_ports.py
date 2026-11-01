"""Recovery uses the installed Planning engine/validator on approved quote records."""
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from tripmate.exception_handling import ExceptionRepository, ExceptionRuntime
from tripmate.exception_handling.fixtures import fixture
from tripmate.exception_handling.ports import MemoryContext
from tripmate.exception_handling.project_ports import ProjectSupplier, ProjectPlanning, ProjectComplaintFindings
from tripmate.exception_handling.review import exception_reviewer
from tripmate.planning.engine import PlanningEngine
from tripmate.planning.fixtures import fixture_request, fixture_quotes, FixtureOffers, FIXTURE_TIME
from tripmate.planning.repository import PlanningRepository
from tripmate.planning.integration import B03ApprovedOffers
from tripmate.fixtures import FixtureRepository


class ExceptionProjectPortTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'project.sqlite3'
        self.repo = ExceptionRepository(self.path)

    def inputs(self):
        _, request, spec = fixture_request(budget='900.00')
        request['hardConstraints'].append(dict(constraintId='accessible', kind='ACCESSIBILITY',
                                              description='Step-free resources required', confirmed=True))
        spec['constraintBindings']['accessible'] = dict(description='Step-free resources required', value=True)
        quotes = fixture_quotes()
        records, _ = PlanningEngine(lambda: FIXTURE_TIME).generate(request, quotes, spec)
        baseline = records[0]
        case, context = fixture()
        case.update(caseId=request['caseId'], correlationId=request['correlationId'], requesterId=request['travellerId'],
                    confirmedAt=FIXTURE_TIME, createdAt=FIXTURE_TIME)
        case['sourceReferences'][0]['capturedAt'] = FIXTURE_TIME
        context.update(caseId=case['caseId'], travellerId=case['requesterId'], assessedAt=FIXTURE_TIME, constraints=[])
        items = [dict(itemId=i['itemId'], kind={'TRANSPORT':'TRANSPORT','ACCOMMODATION':'HOTEL','ACTIVITY':'ACTIVITY'}[i['productType']],
                      origin=i['origin'], destination=i['destination'], startAt=i['startAt'], endAt=i['endAt'],
                      remainingCost=i['quotedPrice']['amount'], sourceIds=i['sourceIds']) for i in baseline['version']['items']]
        affected = next(i for i in items if i['kind'] == 'TRANSPORT')
        context['issue']['itemId'] = affected['itemId']
        context['itinerary'].update(versionId=baseline['version']['versionId'], travellerId=case['requesterId'], items=items)
        context['evidence'] = [dict(source=deepcopy(s), validUntil='2026-10-20T00:00:00+11:00', assertions=[], note='Recorded project baseline.')
                               for s in baseline['version']['sourceReferences']]
        context['evidence'][0]['assertions'].append(dict(key=affected['itemId']+':status', value='CANCELLED'))
        recovery_request = deepcopy(request)
        recovery_request['baselineVersionId'] = baseline['version']['versionId']
        context['planningContext'] = dict(request=recovery_request, spec=spec, baseline=baseline)
        context['supplierOffers'] = []
        return case, context, quotes

    def run_case(self, case, context, quotes, findings=None):
        runtime = ExceptionRuntime(MemoryContext({case['caseId']: context}), self.repo,
                                   ProjectSupplier(FixtureOffers(quotes)), ProjectPlanning(),
                                   exception_reviewer(lambda: FIXTURE_TIME), complaint_findings=findings)
        original = deepcopy((case, context, quotes))
        result = runtime.handle_case(case)
        self.assertEqual((case, context, quotes), original)
        return result, self.repo.get(result['runId'])

    def test_project_recovery_preserves_preferences_constraints_and_unaffected_offers(self):
        case, context, quotes = self.inputs()
        result, snapshot = self.run_case(case, context, quotes)
        self.assertEqual(result['status'], 'SUCCESS', result)
        original = context['planningContext']['baseline']['version']
        affected_offer = next(i['offerId'] for i in original['items'] if i['itemId'] == context['issue']['itemId'])
        for option in snapshot['proposal']['options']:
            version = option['planningRecord']['version']
            current = {i['offerId'] for i in version['items']}
            self.assertNotIn(affected_offer, current)
            self.assertTrue({i['offerId'] for i in original['items']} - {affected_offer} <= current)
            self.assertTrue(all(c['outcome'] == 'PASS' for c in version['validationResults']))
            self.assertIn('CONSTRAINT:accessible', [c['ruleId'] for c in version['validationResults']])

    def test_existing_planning_accessibility_and_confirmed_requirement_gates(self):
        case, context, quotes = self.inputs()
        for quote in quotes:
            if quote['product']['role'] == 'OUTBOUND':
                quote['product']['accessible'] = False
        result, _ = self.run_case(case, context, quotes)
        self.assertEqual(result['status'], 'HUMAN_ASSISTANCE')
        case, context, quotes = self.inputs()
        context['planningContext']['request']['preferences'] = ['Unconfirmed change']
        result, _ = self.run_case(case, context, quotes)
        self.assertEqual(result['status'], 'HUMAN_ASSISTANCE')

    def test_recovery_checks_additional_confirmed_baggage_and_arrival_constraints(self):
        case, context, quotes = self.inputs()
        request = context['planningContext']['request']
        spec = context['planningContext']['spec']
        request['hardConstraints'].append(dict(constraintId='baggage', kind='BAGGAGE',
                                               description='Carry 20 kg', confirmed=True))
        spec['constraintBindings']['baggage'] = dict(description='Carry 20 kg', value=20)
        request['hardConstraints'].append(dict(constraintId='arrival', kind='ARRIVAL_TIME',
                                               description='Arrive by 18:00', confirmed=True))
        spec['constraintBindings']['arrival'] = dict(description='Arrive by 18:00',
                                                   value='2026-10-20T18:00:00+11:00')
        baseline = context['planningContext']['baseline']
        baseline['request'] = deepcopy(request)
        baseline['spec'] = deepcopy(spec)
        result, saved = self.run_case(case, context, quotes)
        self.assertEqual(result['status'], 'SUCCESS', result)
        self.assertTrue(saved['proposal']['options'])
        for option in saved['proposal']['options']:
            checks = {check['ruleId']: check['outcome']
                      for check in option['planningRecord']['version']['validationResults']}
            self.assertEqual(checks['CONSTRAINT:baggage'], 'PASS')
            self.assertEqual(checks['CONSTRAINT:arrival'], 'PASS')
            self.assertIsInstance(option['arrivalChangeMinutes'], int)
            self.assertEqual(option['planningRecord']['comparison']['baselineVersionId'],
                             baseline['version']['versionId'])

        case, context, quotes = self.inputs()
        request = context['planningContext']['request']
        spec = context['planningContext']['spec']
        request['hardConstraints'].append(dict(constraintId='baggage', kind='BAGGAGE',
                                               description='Carry 21 kg', confirmed=True))
        spec['constraintBindings']['baggage'] = dict(description='Carry 21 kg', value=21)
        context['planningContext']['baseline']['request'] = deepcopy(request)
        context['planningContext']['baseline']['spec'] = deepcopy(spec)
        result, saved = self.run_case(case, context, quotes)
        self.assertEqual(result['status'], 'HUMAN_ASSISTANCE')
        self.assertEqual(result['errors'][0]['code'], 'NO_FEASIBLE_ITINERARY')
        self.assertIsNone(saved['proposal'])

    def test_project_supplier_port_reads_the_actual_b03_catalog(self):
        case, context, _ = self.inputs()
        fixtures = FixtureRepository(self.path)
        fixtures.ensure_seeded()
        quotes = ProjectSupplier(B03ApprovedOffers(fixtures)).alternatives(context)
        self.assertTrue(quotes)
        self.assertTrue(all(q['offer']['status'] == 'APPROVED' for q in quotes))

    def test_non_delay_complaint_records_specialist_facts_and_refers_without_policy(self):
        case, context, quotes = self.inputs()
        case['caseType'] = context['issue']['kind'] = 'COMPLAINT'
        context['complaintCategory'] = 'SUPPLIER_TERMS'
        baseline = context['planningContext']['baseline']
        class Plans:
            def get_version(self, version_id):
                return deepcopy(baseline)
        findings = ProjectComplaintFindings(Plans(), FixtureOffers(quotes))
        result, saved = self.run_case(case, context, quotes, findings)
        self.assertEqual(result['status'], 'HUMAN_ASSISTANCE')
        self.assertTrue(saved['specialistFindings']['findings'])
        self.assertIsNone(result['proposedResponse'])
        self.assertIn('No agreed resolution policy', result['errors'][0]['message'])



    def test_daily_recovery_reconciles_factor_based_meal_cost(self):
        from tripmate.planning.daily_demo import daily_fixture
        from tripmate.planning.daily import DailyPlanningEngine
        from tripmate.planning.factors import FixtureTravelFactors
        from tripmate.planning.common import money
        _, daily, rt = daily_fixture()
        self.addCleanup(rt.repository.close)
        quotes = deepcopy(rt.offers.quotes)
        alternate = deepcopy(quotes[0])
        alternate['offer']['offerId'] = 'z-replacement'
        alternate['offer']['review']['subject']['subjectId'] = 'z-replacement'
        alternate['price']['offerId'] = 'z-replacement'
        alternate['price']['priceBreakdownId'] = 'z-price'
        alternate['offer']['priceBreakdownId'] = 'z-price'
        quotes.append(alternate)
        daily['spec']['constraintBindings']['daily']['value']['slots'][0]['offerIds'].append('z-replacement')
        facts=deepcopy(rt.factors.data)
        delay=deepcopy(facts['delays'][0]);delay['offerId']='z-replacement';facts['delays'].append(delay)
        records,_=DailyPlanningEngine(facts,rt.clock).generate(daily['request'],quotes,daily['spec'])
        baseline=next(r for r in records if r['version']['items'][0]['offerId']=='sydney-goulburn')
        case,context,_=self.inputs()
        case.update(caseId=daily['request']['caseId'],correlationId=daily['request']['correlationId'],requesterId=daily['request']['travellerId'])
        context.update(caseId=case['caseId'],travellerId=case['requesterId'])
        affected=baseline['version']['items'][0]
        context['issue']['itemId']=affected['itemId']
        context['itinerary'].update(versionId=baseline['version']['versionId'],travellerId=case['requesterId'],sunkCost='0.00',items=[dict(itemId=i['itemId'],kind={'TRANSPORT':'TRANSPORT','ACCOMMODATION':'HOTEL','ACTIVITY':'ACTIVITY'}[i['productType']],origin=i['origin'],destination=i['destination'],startAt=i['startAt'],endAt=i['endAt'],remainingCost=i['quotedPrice']['amount'],sourceIds=i['sourceIds']) for i in baseline['version']['items']])
        context['evidence']=[dict(source=deepcopy(source),validUntil='2026-10-13T10:00:00+11:00',assertions=[],note='Simulated daily baseline.') for source in baseline['version']['sourceReferences']]
        context['evidence'][0]['assertions']=[dict(key=affected['itemId']+':status',value='CANCELLED')]
        request=deepcopy(daily['request']);request['baselineVersionId']=baseline['version']['versionId']
        context['planningContext']=dict(request=request,spec=daily['spec'],baseline=baseline)
        runtime=ExceptionRuntime(MemoryContext({case['caseId']:context}),self.repo,ProjectSupplier(FixtureOffers(quotes)),ProjectPlanning(FixtureTravelFactors(facts)),exception_reviewer(lambda:FIXTURE_TIME))
        result=runtime.handle_case(case)
        self.assertEqual(result['status'],'SUCCESS',result)
        proposal=self.repo.get(result['runId'])['proposal']
        self.assertEqual(proposal['options'][0]['additionalCost'],money('120.00'))
        self.assertEqual(proposal['options'][0]['totalCost'],'851.50')
