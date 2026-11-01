"""Release boundaries: committed sources, private-file exclusion and ZIP integrity."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from package_release import REQUIRED, package
from verify_release import validate_archive


class ReleasePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.root.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Release Test')
        self.git('config', 'user.email', 'release-test@example.invalid')
        for name in REQUIRED:
            self.write(name, b'Committed release fixture\n')
        self.write('web/package.json', json.dumps({'dependencies': {'react': 'test'},
                                                 'devDependencies': {'vite': 'test'}}).encode())
        self.write('docs/stage2/DEMO_SCENARIOS.zh-CN.md', b'Committed public guide\n')
        for name in ['.env', '.demo-accounts.local.json', '.DS_Store',
                     'src/tripmate/private.sqlite3', 'web/node_modules/private.txt']:
            self.write(name, b'PRIVATE TEST SENTINEL\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'Synthetic release baseline')

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.STDOUT)

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def build(self):
        with redirect_stdout(StringIO()):
            return package(self.root, Path(self.temp.name) / 'releases')

    def mutate(self, original, transform):
        changed = Path(self.temp.name) / 'changed.zip'
        with zipfile.ZipFile(original) as source, zipfile.ZipFile(changed, 'w') as target:
            for entry in source.infolist():
                entry, data = transform(entry, source.read(entry.filename))
                target.writestr(entry, data)
        return changed

    def test_packages_committed_content_without_local_edits_or_private_files(self):
        self.write('docs/stage2/DEMO_SCENARIOS.zh-CN.md', b'PRIVATE EDITED GUIDE\n')
        self.write('docs/untracked.md', b'PRIVATE UNTRACKED FILE\n')
        archive = self.build()
        folder, metadata = validate_archive(archive)
        self.assertEqual(metadata['commit'], self.git('rev-parse', 'HEAD').decode().strip())
        with zipfile.ZipFile(archive) as zipped:
            self.assertEqual(zipped.read(folder + '/docs/stage2/DEMO_SCENARIOS.zh-CN.md'),
                             b'Committed public guide\n')
            self.assertFalse(any('PRIVATE' in zipped.read(name).decode() for name in zipped.namelist()))
        self.assertEqual((self.root / 'docs/stage2/DEMO_SCENARIOS.zh-CN.md').read_bytes(),
                         b'PRIVATE EDITED GUIDE\n')

    def test_missing_committed_runtime_asset_blocks_packaging(self):
        self.git('rm', 'src/tripmate/portal/static/portal-queue.js')
        self.git('commit', '-qm', 'Missing bundle fixture')
        with self.assertRaisesRegex(ValueError, 'Required committed release files missing'):
            self.build()

    def test_archive_bytes_do_not_depend_on_windows_autocrlf(self):
        self.git('config', 'core.autocrlf', 'true')
        self.git('config', 'core.eol', 'crlf')
        expected = self.git('show', 'HEAD:docs/stage2/DEMO_SCENARIOS.zh-CN.md')
        archive = self.build()
        folder, _ = validate_archive(archive)
        with zipfile.ZipFile(archive) as zipped:
            self.assertEqual(zipped.read(folder + '/docs/stage2/DEMO_SCENARIOS.zh-CN.md'), expected)

    def test_checkout_must_match_the_commit_that_triggered_delivery(self):
        with self.assertRaisesRegex(ValueError, 'Checkout differs'):
            package(self.root, Path(self.temp.name) / 'releases', expected_commit='0' * 40)

    def test_hash_mismatch_is_rejected_before_extraction(self):
        archive = self.build()
        changed = self.mutate(archive, lambda entry, data:
                              (entry, b'tampered') if entry.filename.endswith('/README.md') else (entry, data))
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            validate_archive(changed)

    def test_unlisted_file_is_rejected(self):
        archive = self.build()
        with zipfile.ZipFile(archive, 'a') as zipped:
            zipped.writestr('unexpected.txt', 'not in manifest')
        with self.assertRaises(ValueError):
            validate_archive(archive)

    def test_traversal_paths_are_rejected(self):
        archive = self.build()
        changed = self.mutate(archive, lambda entry, data:
                              (zipfile.ZipInfo('../escape'), data)
                              if entry.filename.endswith('/README.md') else (entry, data))
        with self.assertRaisesRegex(ValueError, 'Unsafe ZIP path'):
            validate_archive(changed)

    def test_symlinks_are_rejected(self):
        archive = self.build()
        def symlink(entry, data):
            if entry.filename.endswith('/README.md'):
                entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            return entry, data
        changed = self.mutate(archive, symlink)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            validate_archive(changed)

    def test_wrong_sidecar_checksum_is_rejected(self):
        archive = self.build()
        archive.with_name(archive.name + '.sha256').write_text('wrong checksum\n')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            validate_archive(archive)

    def test_existing_release_is_not_overwritten(self):
        archive = self.build()
        original = archive.read_bytes()
        with self.assertRaises(FileExistsError):
            self.build()
        self.assertEqual(archive.read_bytes(), original)
