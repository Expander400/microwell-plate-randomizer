"""Real-widget smoke tests; skipped when Tk or a display is unavailable."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from microwell_plate_randomizer.gui import App
        except ImportError as exc:
            raise unittest.SkipTest(f'Tkinter unavailable: {exc}')
        cls.app_class = App
        try:
            probe = App()
        except Exception as exc:
            import tkinter
            if isinstance(exc, tkinter.TclError):
                raise unittest.SkipTest(f'No desktop display: {exc}')
            raise
        probe.destroy()

    def setUp(self):
        self.app = self.app_class()
        self.app.withdraw()
        self.app.update()

    def tearDown(self):
        self.app.destroy()

    def generate(self):
        self.app.generate()
        deadline = time.monotonic() + 10
        while self.app.busy and time.monotonic() < deadline:
            self.app.update()
            time.sleep(0.01)
        self.assertFalse(self.app.busy)

    def test_generate_export_and_invalidation(self):
        self.generate()
        self.assertIsNotNone(self.app.result)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'plate.csv'
            with patch('microwell_plate_randomizer.gui.filedialog.asksaveasfilename', return_value=str(path)):
                self.app.export()
            self.assertTrue(path.exists())
        self.app.seed.set('10')
        self.assertIsNone(self.app.result)
        self.assertEqual(str(self.app.export_button['state']), 'disabled')

    def test_selection_and_reset(self):
        self.app.mode.set('excluded')
        self.app.set_well(('B', 2))
        self.assertIn(('B', 2), self.app.excluded)
        self.app.mode.set('available')
        self.app.set_well(('A', 2))
        self.assertNotIn(('A', 2), self.app.water)
        self.app.set_well(('A', 1))
        self.assertIn(('A', 1), self.app.water)
        self.app.reset()
        self.assertFalse(self.app.excluded)
        self.assertIn(('A', 2), self.app.water)

    def test_changed_settings_discard_pending_result(self):
        self.app.generate()
        self.app.seed.set('42')
        deadline = time.monotonic() + 10
        while self.app.busy and time.monotonic() < deadline:
            self.app.update()
            time.sleep(0.01)
        self.assertFalse(self.app.busy)
        self.assertIsNone(self.app.result)

    def test_invalid_sample_error(self):
        self.app.labels.delete('1.0', 'end')
        self.app.labels.insert('1.0', 'sample, nope')
        with patch('microwell_plate_randomizer.gui.messagebox.showerror') as error:
            self.app.generate()
        error.assert_called_once()
        self.assertFalse(self.app.busy)
