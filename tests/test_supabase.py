"""Provider body bounds must accommodate durable history without silent truncation."""
from io import BytesIO
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from tripmate.operations.common import OperationsError
from tripmate.portal.supabase import Supabase, MAX_RESPONSE_BYTES


class SupabaseResponseTests(unittest.TestCase):
    def setUp(self):
        self.cloud = Supabase('https://demo.supabase.co', 'test-public', 'test-server')

    def cancelled(self, code='57014', status=500):
        return HTTPError('https://demo.supabase.co', status, 'Provider error', {},
                         BytesIO(json.dumps({'code': code, 'message': 'private-provider-detail'}).encode()))

    def test_cancelled_private_snapshot_can_be_read_once_more(self):
        snapshot = dict(version=9, records=[], traces=[], commands=[])
        with patch('tripmate.portal.supabase.urlopen', side_effect=[self.cancelled(), BytesIO(json.dumps(snapshot).encode())]) as request:
            self.assertEqual(self.cloud.rpc('tripmate_snapshot'), snapshot)
        self.assertEqual(request.call_count, 2)

    def test_repeated_snapshot_cancellation_stops_after_two_attempts(self):
        with patch('tripmate.portal.supabase.urlopen', side_effect=[self.cancelled(), self.cancelled()]) as request:
            with self.assertRaises(OperationsError) as caught:
                self.cloud.rpc('tripmate_snapshot')
        self.assertEqual(request.call_count, 2)
        self.assertEqual(caught.exception.code, 'CLOUD_UNAVAILABLE')
        self.assertNotIn('private-provider-detail', str(caught.exception))

    def test_cancelled_writes_other_rpcs_and_public_requests_are_never_retried(self):
        for path, admin in [('/rest/v1/rpc/tripmate_commit', True), ('/auth/v1/token', False),
                            ('/rest/v1/rpc/other', True), ('/rest/v1/rpc/tripmate_snapshot', False)]:
            with self.subTest(path=path, admin=admin), patch('tripmate.portal.supabase.urlopen', side_effect=self.cancelled()) as request:
                with self.assertRaises(OperationsError):
                    self.cloud.request(path, method='POST', body={}, admin=admin)
            self.assertEqual(request.call_count, 1)

    def test_other_snapshot_provider_errors_are_not_retried(self):
        with patch('tripmate.portal.supabase.urlopen', side_effect=self.cancelled('XX000')) as request:
            with self.assertRaises(OperationsError):
                self.cloud.rpc('tripmate_snapshot')
        self.assertEqual(request.call_count, 1)

    def test_business_conflicts_require_refresh_without_replaying_writes(self):
        for code in ('PT409', '40001'):
            with self.subTest(code=code), patch('tripmate.portal.supabase.urlopen',
                    side_effect=self.cancelled(code, 409 if code == 'PT409' else 500)) as request:
                with self.assertRaises(OperationsError) as caught:
                    self.cloud.rpc('tripmate_commit', {'expected_version': 0})
            self.assertEqual(request.call_count, 1)
            self.assertEqual(caught.exception.code, 'UNCONFIRMED_REQUEST')
            self.assertIn('Reload', str(caught.exception))
            self.assertNotIn('private-provider-detail', str(caught.exception))

    def test_private_snapshot_larger_than_old_limit_is_parsed_completely(self):
        snapshot = dict(version=7, records=[], traces=[], commands=[], history='x' * MAX_RESPONSE_BYTES)
        with patch('tripmate.portal.supabase.urlopen', return_value=BytesIO(json.dumps(snapshot).encode())):
            self.assertEqual(self.cloud.rpc('tripmate_snapshot'), snapshot)

    def test_private_transaction_state_keeps_bounded_large_response_support(self):
        state = dict(version=7, records=[], commands=[], payload='x' * MAX_RESPONSE_BYTES)
        with patch('tripmate.portal.supabase.urlopen', return_value=BytesIO(json.dumps(state).encode())):
            self.assertEqual(self.cloud.rpc('tripmate_state'), state)

    def test_oversized_snapshot_has_explicit_recovery_action_without_payload(self):
        with patch('tripmate.portal.supabase.MAX_SNAPSHOT_BYTES', 100), \
             patch('tripmate.portal.supabase.urlopen', return_value=BytesIO(b'private-data' * 20)):
            with self.assertRaises(OperationsError) as caught:
                self.cloud.rpc('tripmate_snapshot')
        self.assertEqual(caught.exception.code, 'CLOUD_UNAVAILABLE')
        self.assertIn('administrator', str(caught.exception))
        self.assertNotIn('private-data', str(caught.exception))

    def test_other_endpoints_and_non_admin_calls_keep_the_smaller_bound(self):
        payload = json.dumps(dict(untrusted='x' * MAX_RESPONSE_BYTES)).encode()
        for path, admin in [('/auth/v1/user', False), ('/rest/v1/rpc/other', True),
                            ('/rest/v1/rpc/tripmate_snapshot', False)]:
            with self.subTest(path=path, admin=admin), \
                 patch('tripmate.portal.supabase.urlopen', return_value=BytesIO(payload)):
                with self.assertRaises(OperationsError):
                    self.cloud.request(path, admin=admin)
