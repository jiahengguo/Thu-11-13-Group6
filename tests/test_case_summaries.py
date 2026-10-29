import unittest
from unittest.mock import Mock
from tripmate.operations import OperationsService

class CaseSummaryTests(unittest.TestCase):
    def test_one_bulk_read_private_details_omitted_and_latest_authorised_first(self):
        app=OperationsService.__new__(OperationsService)
        def record(key, day, allowed=True):
            return {'case':{'caseId':key,'caseType':'TRAVEL_PLANNING','status':'IN_PROGRESS',
                            'createdAt':f'2026-10-{day}T00:00:00Z','allowed':allowed},
                    'response':'private-draft','sources':['private']}
        app.repository=Mock()
        app.repository.list.return_value=[record('old',27),record('hidden',29,False),record('new',28)]
        app.repository.read.side_effect=AssertionError('List must not fetch individual case/inbox')
        app.access=Mock()
        app.access.authorise.side_effect=lambda actor,action,case:case['allowed']
        result=app.case_summaries('operator')
        self.assertEqual([r['case']['caseId'] for r in result],['new','old'])
        self.assertEqual(set(result[0]),{'case'})
        self.assertEqual(set(result[0]['case']),{'caseId','caseType','status','createdAt'})
        app.repository.list.assert_called_once_with('case')
        app.repository.read.assert_not_called()
