import subprocess
import sys
import unittest
from unittest.mock import patch

from microwell_plate_randomizer.__main__ import main


class StartupTests(unittest.TestCase):
    def test_version_without_gui(self):
        result = subprocess.run([sys.executable, '-m', 'microwell_plate_randomizer', '--version'],
                                capture_output=True, text=True, check=True)
        self.assertIn('1.0.0', result.stdout)

    def test_legacy_launcher(self):
        result = subprocess.run([sys.executable, 'plate_randomizer_gui.py', '--help'],
                                capture_output=True, text=True, check=True)
        self.assertIn('--check', result.stdout)

    def test_missing_tk_explained(self):
        with patch.dict(sys.modules, {'tkinter': None}), patch('sys.stderr') as output:
            self.assertEqual(main([]), 1)
        self.assertIn('Tkinter could not be loaded', str(output.write.call_args_list))
