import unittest
from unittest.mock import Mock, patch
from test_portals import FakeCloud
from tripmate.portal.server import Portal

class SharedModelServiceTests(unittest.TestCase):
    def test_injected_service_is_shared_without_environment_credentials(self):
        service = Mock()
        with patch.dict('os.environ', {'ELEC5620_API_KEY': ''}):
            app = Portal(FakeCloud(), model_planning=True, llm_service=service)
        self.assertIs(app.model_service, service)
        self.assertIs(app.operations.llm, service)
        self.assertIs(app.campaigns.ops.llm, service)
        service.chat.assert_not_called()

    def test_model_mode_requires_configured_credentials(self):
        with patch.dict('os.environ', {'ELEC5620_API_KEY': 'REPLACE_LOCALLY'}):
            with self.assertRaises(ValueError):
                Portal(FakeCloud(), model_planning=True)
