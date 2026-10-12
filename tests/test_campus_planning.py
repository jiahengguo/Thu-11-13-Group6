import json
import unittest
from unittest.mock import patch, MagicMock

from tripmate.agents.planning import TravelPlanningAgent
from tripmate.planning.campus import ModelPlanningEngine, CampusClient
from tripmate.planning.common import PlanningError
from tripmate.planning.fixtures import fixture_runtime


class ScriptedClient:
    model = 'TEST_DOUBLE_NOT_REAL_MODEL'

    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = 0
        self.messages = []

    def chat(self, messages):
        self.calls += 1
        self.messages.append(json.loads(json.dumps(messages)))
        response = next(self.replies)
        if isinstance(response, Exception):
            raise response
        return json.dumps({'candidates': response, 'explanation': 'Test draft'})


class CampusPlanningTests(unittest.TestCase):
    def test_truncated_chat_response_is_not_accepted(self):
        with patch.dict('os.environ', {'ELEC5620_API_KEY': 'test-only'}):
            client = CampusClient()
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}],
            'usage': {'completion_tokens': 4096}}).encode()
        with patch('tripmate.adapters.campus.http.build_opener') as opener:
            opener.return_value.open.return_value = response
            with self.assertRaisesRegex(PlanningError, 'token limit'):
                client.chat([{'role': 'user', 'content': 'Test'}])
        self.assertEqual(client.responses[0]['finishReason'], 'length')

    def run_agent(self, responses, budget='450.00'):
        case, context, runtime = fixture_runtime(budget=budget)
        self.addCleanup(runtime.repository.close)
        client = ScriptedClient(responses)
        runtime.planner = ModelPlanningEngine(client, runtime.clock)
        result = TravelPlanningAgent(runtime).handle_case(case)
        return result, runtime, client

    def test_over_budget_feedback_repairs_without_relaxing_budget(self):
        result, rt, client = self.run_agent([
            [['express', 'comfort-stay', 'guided-tour']],
            [['coach', 'basic-stay', 'walk']]])
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(client.calls, 2)
        self.assertIn('FAIL', client.messages[1][-1]['content'])
        record = rt.repository.get_version(result['subjects'][0]['subjectId'])
        self.assertEqual(record['version']['totalPrice']['amount'], '396.00')
        self.assertEqual(record['request']['budgetCeiling']['amount'], '450.00')
        self.assertTrue(all(c['outcome'] == 'PASS' for c in record['version']['validationResults']))

    def test_unknown_offer_never_reaches_itinerary(self):
        result, rt, client = self.run_agent([[['invented-flight']]] * 3)
        self.assertEqual(result['status'], 'FAILURE')
        self.assertEqual(result['subjects'], [])
        self.assertEqual(client.calls, 3)

    def test_missing_stay_rejected(self):
        result, _, _ = self.run_agent([[['coach', 'walk']]] * 3)
        self.assertEqual(result['status'], 'FAILURE')

    def test_connection_failure_has_no_offline_fallback(self):
        result, _, client = self.run_agent([PlanningError('TOOL_UNAVAILABLE', 'Test timeout')])
        self.assertEqual(result['status'], 'FAILURE')
        self.assertEqual(result['errors'][0]['code'], 'TOOL_UNAVAILABLE')
        self.assertEqual(client.calls, 1)

    def test_candidates_share_plan_and_deduplicate(self):
        result, rt, _ = self.run_agent([[['coach', 'basic-stay', 'walk'],
                                       ['coach', 'basic-stay', 'guided-tour'],
                                       ['coach', 'basic-stay', 'walk']]])
        records = [rt.repository.get_version(s['subjectId']) for s in result['subjects']]
        self.assertEqual(len(records), 2)
        self.assertEqual(len({r['version']['planId'] for r in records}), 1)

    def test_model_cannot_claim_global_infeasibility(self):
        result, _, _ = self.run_agent([[], [], []])
        self.assertEqual(result['status'], 'FAILURE')
        self.assertIn('does not prove inventory infeasibility', result['errors'][0]['message'])


if __name__ == '__main__':
    unittest.main()
