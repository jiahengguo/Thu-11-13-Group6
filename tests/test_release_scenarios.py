"""Release acceptance must not report empty or skipped modules as verified."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('release_scenario_verifier',
    Path(__file__).resolve().parents[1] / 'scripts/verify_release_scenarios.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class ReleaseScenarioEvidenceTests(unittest.TestCase):
    def test_executed_passing_tests_are_accepted(self):
        for number, word in [(1, 'test'), (4, 'tests')]:
            value = verifier.test_evidence(0, f'Ran {number} {word} in 0.100s\n\nOK\n')
            self.assertTrue(value['passed'])
            self.assertEqual(value['testCount'], number)
            self.assertEqual(value['skippedCount'], 0)

    def test_zero_tests_are_not_release_evidence(self):
        self.assertFalse(verifier.test_evidence(0, 'Ran 0 tests in 0.000s\n\nOK\n')['passed'])

    def test_missing_result_summary_is_not_release_evidence(self):
        self.assertFalse(verifier.test_evidence(0, 'Process exited successfully without running tests.')['passed'])
        self.assertFalse(verifier.test_evidence(0, 'Ran 4 tests in 0.100s\n')['passed'])

    def test_skipped_acceptance_is_not_claimed_as_passed(self):
        value = verifier.test_evidence(0, 'Ran 4 tests in 0.100s\n\nOK (skipped=1)\n')
        self.assertFalse(value['passed'])
        self.assertEqual(value['skippedCount'], 1)

    def test_failure_exit_or_failed_summary_cannot_pass(self):
        self.assertFalse(verifier.test_evidence(1, 'Ran 4 tests in 0.100s\n\nOK\n')['passed'])
        self.assertFalse(verifier.test_evidence(0, 'Ran 4 tests in 0.100s\n\nFAILED (failures=1)\n')['passed'])


if __name__ == '__main__':
    unittest.main()
