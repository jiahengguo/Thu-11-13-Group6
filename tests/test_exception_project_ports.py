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


if __name__ == '__main__':
    unittest.main()
