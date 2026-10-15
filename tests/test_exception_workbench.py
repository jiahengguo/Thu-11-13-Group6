"""Reopen saved investigations through the real local HTTP boundary."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib import request, error
from uuid import uuid4

from tripmate.api.server import Workbench, make_server
from tripmate.api.settings import Settings
from tripmate.exception_handling.integration_demo import demonstrate


class ExceptionWorkbenchTests(unittest.TestCase):
    def test_opt_in_and_separate_fixture_configuration_are_required(self):
        with tempfile.TemporaryDirectory() as folder:
            settings = Settings(Path(folder) / 'empty.sqlite3')
            self.assertIsNone(Workbench(settings).integrated_exception)
            with self.assertRaises(ValueError):
                Workbench(settings, exception_fixture=True)
            with self.assertRaises(ValueError):
                Workbench(settings, exception_fixture=True, planning_fixture=True)

    def test_http_pending_review_selection_and_private_evidence_after_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'recovery.sqlite3'
            seeded = demonstrate(path)
            case_id = seeded['case']['case']['caseId']
            server = make_server(Settings(path), port=0, exception_fixture=True)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = 'http://127.0.0.1:' + str(server.server_port)

            def call(route, body=None, session='', token=True):
                headers = {'X-Ops-Session': session}
                if token:
                    headers['X-TripMate-Token'] = server.app.token
                if body is not None:
                    headers['Content-Type'] = 'application/json'
                req = request.Request(base + '/api/operations/' + route, headers=headers,
                                      data=json.dumps(body).encode() if body is not None else None)
                with request.urlopen(req, timeout=5) as response:
                    return json.load(response)

            def post(action, body, session):
                return call(action, dict(requestKey=str(uuid4()), caseId=case_id, **body), session)

            try:
                traveller = call('session', {'identityId': 'traveller:paid'})['session']
                operator = call('session', {'identityId': 'operator:fixture'})['session']
                view = call('case?caseId=' + case_id, session=traveller)
                self.assertIsNone(view['response'])
                self.assertNotIn('recoveryOptions', view)
                with self.assertRaises(error.HTTPError) as caught:
                    call('exception?caseId=' + case_id, session=traveller)
                self.assertEqual(caught.exception.code, 403)
                caught.exception.close()
                snapshot = call('exception?caseId=' + case_id, session=operator)['investigation']
                self.assertEqual(snapshot['result']['runId'], seeded['investigation']['result']['runId'])
                view = post('review', dict(revision=view['revision'], decision='APPROVE', reason='Reviewed supplied evidence.'), operator)
                post('deliver', dict(revision=view['revision']), traveller)
                view = call('case?caseId=' + case_id, session=traveller)
                self.assertTrue(view['canSelectRecovery'])
                payload = dict(revision=view['revision'], runId=view['recoveryOptions']['runId'],
                               optionId=view['recoveryOptions']['options'][0]['offerId'], confirmed=True)
                with self.assertRaises(error.HTTPError) as caught:
                    call('exception-selection', dict(requestKey=str(uuid4()), caseId=case_id, **payload), traveller, token=False)
                self.assertEqual(caught.exception.code, 403)
                caught.exception.close()
                selected = post('exception-selection', payload, traveller)
                self.assertEqual(selected['case']['status'], 'UNDER_REVIEW')
                self.assertNotIn('recoveryOptions', selected)
                view = post('review', dict(revision=selected['revision'], decision='APPROVE', reason='Review exact selected recommendation.'), operator)
                post('deliver', dict(revision=view['revision']), traveller)
                view = call('case?caseId=' + case_id, session=traveller)
                self.assertFalse(view['canSelectRecovery'])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_changed_supplier_terms_block_release_of_saved_project_proposal(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'recovery.sqlite3'
            seeded = demonstrate(path)
            app = Workbench(Settings(path), exception_fixture=True)
            bridge = app.integrated_exception
            case_id = seeded['case']['case']['caseId']
            with patch.object(bridge.runtime.supplier, 'alternatives', return_value=[]):
                from tripmate.operations.common import OperationsError
                with self.assertRaises(OperationsError):
                    app.operations.review_case('operator:fixture', str(uuid4()), case_id,
                                               seeded['case']['revision'], 'APPROVE', 'Attempt stale review')
            self.assertEqual(app.operations.repository.read('case', case_id)['case']['status'], 'UNDER_REVIEW')


if __name__ == '__main__':
    unittest.main()
