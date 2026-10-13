import json
import tempfile
import threading
import unittest
from contextlib import closing
from http.client import HTTPConnection
from pathlib import Path

from tripmate.api.server import make_server, Workbench
from tripmate.api.settings import Settings
from tripmate.operations.integration import connect_planning
from tripmate.planning.integration import B03ApprovedOffers, WorkbenchFixtureReviewer
from tripmate.planning.repository import PlanningRepository


class MainPlanningIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'shared.sqlite3'
        self.server = make_server(Settings(self.path), port=0, planning_fixture=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.app = self.server.app
        self.token = self.request('GET', '/api/status')[1]['csrfToken']
        self.paid = self.post('session', {'identityId': 'traveller:paid'})['session']
        self.operator = self.post('session', {'identityId': 'operator:fixture'})['session']
        self.counter = 0

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.server.app.integrated_planning.close()

    def request(self, method, path, data=None, session=None):
        conn = HTTPConnection('127.0.0.1', self.server.server_port, timeout=20)
        try:
            headers = {'Content-Type': 'application/json', 'X-TripMate-Token': getattr(self, 'token', '')}
            if session:
                headers['X-Ops-Session'] = session
            conn.request(method, path, None if data is None else json.dumps(data), headers)
            response = conn.getresponse()
            return response.status, json.loads(response.read())
        finally:
            conn.close()

    def post(self, action, body, session=None):
        if action != 'session':
            self.counter += 1
            body = dict(body, requestKey='integration-' + str(self.counter))
        status, result = self.request('POST', '/api/operations/' + action, body, session)
        self.assertEqual(status, 200, result)
        return result

    def generate(self):
        fields = {'origin': 'Sydney Central', 'destination': 'Melbourne Centre', 'partySize': 1,
                  'budgetCeiling': {'amount': '450.00', 'currency': 'AUD'},
                  'travelDates': {'startDate': '2026-10-20', 'endDate': '2026-10-22'},
                  'rankingMode': 'VALUE', 'preferences': [], 'constraints': []}
        intents = [{'caseType': 'TRAVEL_PLANNING', 'fields': fields}]
        intake = self.post('intake', {'text': 'Confirmed test request', 'intents': intents}, self.paid)
        confirmed = self.post('confirm', {'intakeId': intake['id'], 'revision': 1,
                                         'intents': intents, 'confirmed': True}, self.paid)
        cid = confirmed['caseIds'][0]
        result = self.post('dispatch', {'caseId': cid, 'revision': 1}, self.paid)
        self.assertEqual(result['case']['status'], 'UNDER_REVIEW', result)
        internal = self.app.operations.repository.read('case', cid)
        vid = internal['specialistResult']['subjects'][0]['subjectId']
        return cid, vid, result

    def test_http_review_delivery_read_and_adoption(self):
        cid, vid, result = self.generate()
        path = '/api/operations/plan?versionId=' + vid
        self.assertNotEqual(self.request('GET', path, session=self.paid)[0], 200)
        self.post('review', {'caseId': cid, 'revision': result['revision'], 'decision': 'APPROVE',
                            'reason': 'Explicit fixture operator checked response'}, self.operator)
        view = self.app.operations.case_view('traveller:paid', cid)
        self.post('deliver', {'caseId': cid, 'revision': view['revision']}, self.paid)
        status, public = self.request('GET', path, session=self.paid)
        self.assertEqual(status, 200)
        self.assertEqual(public['version']['totalPrice']['amount'], '396.00')
        self.assertNotIn('supplierCost', json.dumps(public))
        self.assertNotIn('modelPlanning', public)
        adopted = self.post('adopt', {'versionId': vid, 'expectedBaseline': None, 'accepted': True}, self.paid)
        self.assertTrue(adopted['adopted'])
        free = self.post('session', {'identityId': 'traveller:free'})['session']
        self.assertEqual(self.request('GET', path, session=free)[0], 403)

    def test_b03_database_refresh_and_expired_quote_filter(self):
        offers = B03ApprovedOffers(self.app.fixtures)
        criteria = {'partySize': 1}
        self.assertEqual(len(offers.find_selectable(criteria, self.app.operations.clock())), 6)
        entity = self.app.fixtures.get_entity('offer:coach')
        entity['data']['offer']['validUntil'] = self.app.operations.clock()
        entity['data']['offer']['validFrom'] = '2026-10-11T10:00:00+11:00'
        with closing(self.app.fixtures._connect()) as db, db:
            db.execute('UPDATE fixture_entities SET payload=? WHERE id=?', (json.dumps(entity), entity['id']))
        current = offers.find_selectable(criteria, self.app.operations.clock())
        self.assertNotIn('coach', [q['offer']['offerId'] for q in current])

    def test_b03_reset_preserves_integrated_plans(self):
        _, vid, _ = self.generate()
        before = self.app.integrated_planning.get_version(vid)
        self.app.reset_fixtures()
        self.assertEqual(self.app.integrated_planning.get_version(vid), before)

    def test_integration_remains_explicit_and_status_is_honest(self):
        plain = Workbench(Settings(Path(self.tmp.name) / 'plain.sqlite3'))
        self.assertIsNone(plain.operations.planning_repository)
        self.assertEqual(self.app.status()['integration']['reviewer'], 'EXPLICIT_FIXTURE')
        self.assertEqual(self.app.status()['integration']['planning'], 'OPERATIONS_B03_FIXTURE')
        with self.assertRaises(ValueError):
            Workbench(Settings(Path(self.tmp.name) / 'bad.sqlite3'), planning_live_model=True)

    def test_planner_factory_is_per_case_and_uses_operations_context(self):
        created = []
        from tripmate.planning.engine import PlanningEngine
        def factory():
            engine = PlanningEngine(self.app.operations.clock)
            created.append(engine)
            return engine
        connect_planning(self.app.operations, B03ApprovedOffers(self.app.fixtures),
                         WorkbenchFixtureReviewer(self.app.operations.clock), self.app.integrated_planning,
                         planner_factory=factory)
        self.generate()
        self.generate()
        self.assertEqual(len(created), 2)
        self.assertIsNot(created[0], created[1])
