"""Readiness is explicit about configuration vs live validation and hides secrets."""
import json
import unittest
from unittest.mock import patch

from tripmate.portal.doctor import readiness
from tripmate.operations.common import OperationsError
from tripmate.planning.common import PlanningError
from tripmate.adapters.campus import CampusClient

CONFIG = {'SUPABASE_URL': 'https://example.supabase.co', 'SUPABASE_PUBLISHABLE_KEY': 'public-test',
          'SUPABASE_SECRET_KEY': 'private-test', 'ELEC5620_API_KEY': 'course-test',
          'TRIPMATE_LLM_PROVIDER': 'elec5620', 'ELEC5620_MODEL': 'campus-qwen'}


class ReadinessTests(unittest.TestCase):
    def test_configuration_check_makes_no_provider_request(self):
        with patch.dict('os.environ', CONFIG, clear=True), patch('tripmate.portal.supabase.Supabase.rpc') as rpc, \
                patch('tripmate.adapters.campus.CampusLLMService.extract') as extract:
            result = readiness(demo_pricing=True)
        self.assertTrue(result['ready'])
        self.assertEqual({c['status'] for c in result['checks']}, {'CONFIGURED'})
        rpc.assert_not_called()
        extract.assert_not_called()
        for secret in ['private-test', 'public-test', 'course-test']:
            self.assertNotIn(secret, json.dumps(result))

    def test_empty_and_placeholder_settings_block(self):
        for settings in ({}, {k: 'REPLACE_LOCALLY' for k in CONFIG}):
            with patch.dict('os.environ', settings, clear=True):
                result = readiness()
            self.assertFalse(result['ready'])
            self.assertEqual({c['status'] for c in result['checks']}, {'BLOCKED'})

    def test_partial_or_invalid_pricing_does_not_become_zero_margin_default(self):
        for price in ({'TRIPMATE_MARKUP_RATE': '0.1'},
                      {'TRIPMATE_MARKUP_RATE': 'NaN', 'TRIPMATE_MINIMUM_MARGIN': '15.00',
                       'TRIPMATE_PRICING_CONFIG_VERSION': 'test'}):
            with patch.dict('os.environ', dict(CONFIG, **price), clear=True):
                report = readiness()
            self.assertEqual(next(c for c in report['checks'] if c['component'] == 'pricing')['status'], 'BLOCKED')

    def test_live_checks_verify_schema_valid_extraction_and_private_rpc(self):
        snapshot = []
        with patch.dict('os.environ', CONFIG, clear=True), \
                patch('tripmate.portal.supabase.Supabase.rpc', return_value=snapshot) as rpc, \
                patch('tripmate.adapters.campus.CampusLLMService.extract', return_value={'partySize': 2}) as extract:
            report = readiness(demo_pricing=True, check_cloud=True, check_model=True)
        self.assertTrue(report['ready'])
        rpc.assert_called_once_with('tripmate_read_records', {'record_kind': '__readiness__'})
        self.assertEqual(extract.call_args.args[0], 'Two travellers are requesting a simulated trip.')
        self.assertEqual([c['status'] for c in report['checks']], ['VERIFIED', 'CONFIGURED', 'VERIFIED'])

    def test_failure_messages_do_not_expose_provider_bodies_or_keys(self):
        with patch.dict('os.environ', CONFIG, clear=True), \
                patch('tripmate.portal.supabase.Supabase.rpc', side_effect=OperationsError('CLOUD_UNAVAILABLE', 'private-test')), \
                patch('tripmate.adapters.campus.CampusLLMService.extract', side_effect=PlanningError('TOOL_UNAVAILABLE', 'course-test')):
            report = readiness(demo_pricing=True, check_cloud=True, check_model=True)
        self.assertFalse(report['ready'])
        self.assertNotIn('private-test', json.dumps(report))
        self.assertNotIn('course-test', json.dumps(report))

    def test_wrong_semantic_model_result_is_not_a_successful_probe(self):
        with patch.dict('os.environ', CONFIG, clear=True), \
                patch('tripmate.adapters.campus.CampusLLMService.extract', return_value={'partySize': 3}):
            report = readiness(demo_pricing=True, check_model=True)
        self.assertEqual(report['checks'][-1]['status'], 'BLOCKED')

    def test_course_client_rejects_placeholder_and_invalid_token_limits(self):
        for key, limit in [('REPLACE_LOCALLY', 256), ('test', 0), ('test', 8193), ('test', True)]:
            with patch.dict('os.environ', {'ELEC5620_API_KEY': key}, clear=True):
                with self.assertRaises((PlanningError, ValueError)):
                    CampusClient(max_completion_tokens=limit)
