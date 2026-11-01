"""Verification provenance must work in source ZIPs without borrowing parent Git data."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    'verification_metadata', Path(__file__).resolve().parents[1] / 'scripts/verification_metadata.py')
metadata = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metadata)


class VerificationMetadataTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def initialise_checkout(self):
        self.git('init', '-q')
        self.git('config', 'user.name', 'Verification Test')
        self.git('config', 'user.email', 'verification-test@example.invalid')
        (self.root / 'tracked.txt').write_text('source\n')
        self.git('add', 'tracked.txt')
        self.git('commit', '-qm', 'Synthetic verification baseline')

    def test_source_zip_without_git_does_not_require_git_executable(self):
        with patch.object(metadata.subprocess, 'run', side_effect=AssertionError('Git is optional')):
            result = metadata.git_metadata(self.root)
        self.assertEqual(result, dict(baseCommit=None, workingTreeDirty=None, sourceControl='UNAVAILABLE'))

    def test_clean_and_dirty_checkout_keep_actual_provenance(self):
        self.initialise_checkout()
        self.assertEqual(metadata.git_metadata(self.root), dict(
            baseCommit=self.git('rev-parse', 'HEAD'), workingTreeDirty=False, sourceControl='GIT'))
        (self.root / 'tracked.txt').write_text('changed\n')
        self.assertTrue(metadata.git_metadata(self.root)['workingTreeDirty'])

    def test_zip_inside_another_repository_cannot_borrow_its_commit(self):
        self.initialise_checkout()
        extracted = self.root / 'extracted'
        extracted.mkdir()
        self.assertIsNone(metadata.git_metadata(extracted)['baseCommit'])

    def test_missing_git_or_invalid_repository_leaves_metadata_unknown(self):
        (self.root / '.git').mkdir()
        for error in (FileNotFoundError('Git is not installed'),
                      subprocess.CalledProcessError(128, ['git'])):
            with self.subTest(error=type(error).__name__), \
                 patch.object(metadata.subprocess, 'run', side_effect=error):
                self.assertIsNone(metadata.git_metadata(self.root)['workingTreeDirty'])
