"""Provider body bounds must accommodate durable history without silent truncation."""
from io import BytesIO
import json
import unittest
from unittest.mock import patch

from tripmate.operations.common import OperationsError
from tripmate.portal.supabase import Supabase, MAX_RESPONSE_BYTES


class SupabaseResponseTests(unittest.TestCase):
    def setUp(self):
        self.cloud = Supabase('https://demo.supabase.co', 'test-public', 'test-server')

    def test_private_snapshot_larger_than_old_limit_is_parsed_completely(self):
        snapshot = dict(version=7, records=[], traces=[], commands=[], history='x' * MAX_RESPONSE_BYTES)
        with patch('tripmate.portal.supabase.urlopen', return_value=BytesIO(json.dumps(snapshot).encode())):
            self.assertEqual(self.cloud.rpc('tripmate_snapshot'), snapshot)

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
