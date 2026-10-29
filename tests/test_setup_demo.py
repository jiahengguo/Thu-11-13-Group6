"""Bootstrap the installer before a pyproject-only editable install."""
from contextlib import redirect_stdout
import importlib.util
from io import StringIO
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


class SetupDemoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / 'scripts').mkdir()
        python = self.root / '.venv' / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
        python.parent.mkdir(parents=True)
        python.touch()
        self.python = str(python)
        (self.root / '.env.example').write_text('TEMPLATE=yes\n')
        path = Path(__file__).resolve().parents[1] / 'scripts/setup_demo.py'
        spec = importlib.util.spec_from_file_location('setup_demo_under_test', path)
        self.setup = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.setup)
        self.setup.__file__ = str(self.root / 'scripts/setup_demo.py')

    def test_upgrade_precedes_editable_install_and_existing_config_is_preserved(self):
        config = self.root / '.env'
        config.write_text('EXISTING=keep\n')
        with patch.object(sys, 'argv', ['setup_demo.py']), \
             patch.object(self.setup.subprocess, 'run') as run, redirect_stdout(StringIO()):
            self.setup.main()
        self.assertEqual(run.call_args_list[0].args[0],
            [self.python, '-m', 'pip', 'install', '--upgrade', 'pip'])
        self.assertEqual(run.call_args_list[1].args[0],
            [self.python, '-m', 'pip', 'install', '-e', str(self.root)])
        self.assertEqual(run.call_count, 2)
        self.assertTrue(all(c.kwargs['check'] for c in run.call_args_list))
        self.assertEqual(config.read_text(), 'EXISTING=keep\n')

    def test_failed_installer_upgrade_stops_before_install_or_config_creation(self):
        with patch.object(sys, 'argv', ['setup_demo.py']), \
             patch.object(self.setup.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'pip')) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                self.setup.main()
        self.assertEqual(run.call_count, 1)
        self.assertFalse((self.root / '.env').exists())
