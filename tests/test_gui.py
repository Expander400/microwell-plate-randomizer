"""Real-widget smoke tests; skipped when Tk or a display is unavailable."""
import tempfile
import csv
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
        self.assertNotIn(('A', 1), self.app.water)
        self.app.reset()
        self.assertFalse(self.app.excluded)
        self.assertFalse(self.app.water)
        self.assertFalse(self.app.custom_marks)
        self.assertFalse(self.app.fill_unused.get())

    def test_initial_defaults_and_perimeter_button(self):
        from microwell_plate_randomizer.core import DEFAULT_LABELS, WELLS, default_water
        self.assertEqual(DEFAULT_LABELS, [f'Sample {letter}' for letter in 'ABCDEF'])
        self.assertFalse(self.app.water)
        self.assertTrue(all(self.app.well_display(well)[0] == 'Available' for well in WELLS))
        self.app.add_water_perimeter()
        self.assertEqual(self.app.water, default_water())
        self.app.reset()
        self.assertFalse(self.app.water)

    def test_edit_unused_preserves_samples_and_exports(self):
        self.generate()
        samples = {well: self.app.result[well] for well in self.app.sample_wells}
        unused = [well for well, value in self.app.result.items() if value == 'Unused']
        self.app.mode.set('water')
        self.app.set_well(unused[0])
        self.app.mode.set('custom')
        self.app.custom_text.set('Control, positive')
        self.app.set_well(unused[1])
        self.app.mode.set('excluded')
        self.app.set_well(unused[2])
        self.assertEqual({well: self.app.result[well] for well in samples}, samples)
        self.assertEqual(self.app.result[unused[0]], 'Water')
        self.assertEqual(self.app.result[unused[1]], 'Control, positive')
        self.assertEqual(self.app.result[unused[2]], 'Unused')
        self.assertEqual(str(self.app.export_button['state']), 'normal')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'plate.csv'
            with patch('microwell_plate_randomizer.gui.filedialog.asksaveasfilename', return_value=str(path)):
                self.app.export()
            with path.open(encoding='utf-8-sig', newline='') as source:
                values = [value for row in csv.reader(source) for value in row]
        self.assertIn('Control, positive', values)

    def test_assigned_samples_protected_until_layout_cleared(self):
        self.generate()
        well = next(iter(self.app.sample_wells))
        original = self.app.result.copy()
        self.app.mode.set('water')
        self.app.set_well(well)
        self.assertEqual(self.app.result, original)
        self.assertNotIn(well, self.app.water)
        self.app.clear_layout()
        self.app.set_well(well)
        self.assertIsNone(self.app.result)
        self.assertIn(well, self.app.water)

    def test_fill_unused_toggle_preserves_samples_and_manual_water(self):
        self.app.mode.set('water')
        self.app.set_well(('A', 1))
        self.app.mode.set('excluded')
        self.app.set_well(('A', 2))
        self.app.mode.set('custom')
        self.app.custom_text.set('Control')
        self.app.set_well(('A', 3))
        self.app.fill_unused.set(True)
        self.generate()
        samples = {well: self.app.result[well] for well in self.app.sample_wells}
        self.assertEqual(self.app.result['A', 2], 'Unused')
        self.assertEqual(self.app.result['A', 3], 'Control')
        self.assertEqual(self.app.result['H', 12], 'Water' if ('H', 12) not in samples else samples['H', 12])
        self.assertEqual(self.app.water, {('A', 1)})
        self.app.fill_unused.set(False)
        self.assertEqual({well: self.app.result[well] for well in samples}, samples)
        self.assertEqual(self.app.result['A', 1], 'Water')
        self.assertTrue(any(value == 'Unused' for value in self.app.result.values()))
        self.app.fill_unused.set(True)
        before = self.app.result.copy()
        self.generate()
        self.assertEqual(self.app.result, before)

    def test_custom_marks_validate_and_remain_reserved(self):
        well = ('A', 1)
        self.app.mode.set('custom')
        for label in ('', 'Water', 'Unused', 'Sample A'):
            self.app.custom_text.set(label)
            with patch('microwell_plate_randomizer.gui.messagebox.showerror') as error:
                self.app.set_well(well)
            error.assert_called_once()
            self.assertNotIn(well, self.app.custom_marks)
        self.app.custom_text.set('Reference')
        self.app.set_well(well)
        self.generate()
        self.assertEqual(self.app.result[well], 'Reference')
        self.assertNotIn(well, self.app.sample_wells)
        self.app.mode.set('available')
        self.app.set_well(well)
        self.assertNotIn(well, self.app.custom_marks)
        self.assertEqual(self.app.result[well], 'Unused')

    def test_perimeter_after_generation_preserves_samples_and_reserved_wells(self):
        self.app.mode.set('excluded')
        self.app.set_well(('A', 1))
        self.app.mode.set('custom')
        self.app.custom_text.set('Reference')
        self.app.set_well(('A', 2))
        self.generate()
        samples = {well: self.app.result[well] for well in self.app.sample_wells}
        self.app.add_water_perimeter()
        self.assertEqual({well: self.app.result[well] for well in samples}, samples)
        self.assertEqual(self.app.result['A', 1], 'Unused')
        self.assertEqual(self.app.result['A', 2], 'Reference')

    def test_mark_edits_during_generation_discard_pending_result(self):
        self.app.generate()
        self.app.mode.set('custom')
        self.app.custom_text.set('Reference')
        self.app.set_well(('A', 1))
        deadline = time.monotonic() + 10
        while self.app.busy and time.monotonic() < deadline:
            self.app.update()
            time.sleep(0.01)
        self.assertFalse(self.app.busy)
        self.assertIsNone(self.app.result)
        self.assertEqual(self.app.custom_marks['A', 1], 'Reference')

    def test_border_wells_support_every_mode(self):
        for well in (('A', 1), ('H', 1), ('A', 12), ('H', 12), ('C', 1), ('D', 12)):
            with self.subTest(well=well):
                self.app.mode.set('available')
                self.app.set_well(well)
                self.assertNotIn(well, self.app.water)
                self.assertNotIn(well, self.app.excluded)
                self.assertEqual(self.app.well_display(well)[0], 'Available')
                self.app.mode.set('excluded')
                self.app.set_well(well)
                self.assertNotIn(well, self.app.water)
                self.assertIn(well, self.app.excluded)
                self.assertEqual(self.app.well_display(well)[0], 'Excluded')
                self.app.mode.set('water')
                self.app.set_well(well)
                self.assertIn(well, self.app.water)
                self.assertNotIn(well, self.app.excluded)
                self.assertEqual(self.app.well_display(well)[0], 'Water')

    def test_generate_samples_in_border_wells(self):
        from microwell_plate_randomizer.core import WELLS
        available = {('A', 1), ('B', 5), ('H', 12)}
        self.app.water.clear()
        self.app.excluded = set(WELLS) - available
        self.app.labels.delete('1.0', 'end')
        self.app.labels.insert('1.0', 'Sample, 3')
        self.generate()
        for well in available:
            self.assertEqual(self.app.result[well], 'Sample')
            self.assertEqual(self.app.well_display(well)[0], 'Sample')
        self.assertEqual(self.app.result['H', 1], 'Unused')

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
