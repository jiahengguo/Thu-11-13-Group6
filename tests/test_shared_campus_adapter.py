import json
import unittest
from unittest.mock import patch

from tripmate.adapters.campus import CampusLLMService
from tripmate.planning.common import PlanningError


class SharedCampusAdapterTests(unittest.TestCase):
    def setUp(self):
        with patch.dict('os.environ', {'ELEC5620_API_KEY': 'test-only'}, clear=True):
            self.llm = CampusLLMService()
        self.schema = {'type': 'object', 'properties': {'partySize': {'type': 'integer', 'minimum': 1}},
                       'required': ['partySize'], 'additionalProperties': False}

    def test_extract_validates_shared_schema(self):
        with patch.object(self.llm, 'chat', return_value='{"partySize":2}') as chat:
            self.assertEqual(self.llm.extract('Two travellers', self.schema), {'partySize': 2})
        sent = json.loads(chat.call_args.args[0][1]['content'])
        self.assertEqual(sent['schema'], self.schema)

    def test_extract_rejects_invalid_or_invented_fields(self):
        for text in ['not json', '[]', '{"partySize":0}', '{"partySize":2,"approved":true}']:
            with self.subTest(text=text), patch.object(self.llm, 'chat', return_value=text):
                with self.assertRaises(PlanningError):
                    self.llm.extract('Two travellers', self.schema)

    def test_draft_and_explain_preserve_inputs_as_data(self):
        data = {'cost': {'amount': '396.00', 'currency': 'AUD'}}
        for method in [self.llm.draft, self.llm.explain]:
            with patch.object(self.llm, 'chat', return_value='Unreviewed draft') as chat:
                self.assertEqual(method(data), 'Unreviewed draft')
                self.assertEqual(json.loads(chat.call_args.args[0][1]['content']), data)

    def test_shared_model_placeholder_takes_precedence(self):
        with patch.dict('os.environ', {'ELEC5620_API_KEY': 'test-only', 'ELEC5620_MODEL': 'fallback',
                                      'TRIPMATE_LLM_MODEL': 'shared-model', 'TRIPMATE_LLM_PROVIDER': 'elec5620'}, clear=True):
            self.assertEqual(CampusLLMService().model, 'shared-model')

    def test_other_provider_does_not_silently_call_course_proxy(self):
        with patch.dict('os.environ', {'ELEC5620_API_KEY': 'test-only', 'TRIPMATE_LLM_PROVIDER': 'other'}, clear=True):
            with self.assertRaises(PlanningError):
                CampusLLMService()
