import csv
import itertools
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from microwell_plate_randomizer.core import (
    DEFAULT_LABELS, GROUPS, ROWS, SAMPLE_WELLS, WELLS, SearchLimitError,
    default_water, export_csv, parse_samples, randomize_plate,
)


class SampleInputTests(unittest.TestCase):
    def test_parse_mixed_counts_and_commas(self):
        self.assertEqual(parse_samples(' LB-A, 3\n\nSample, special, 2\n'),
                         {'LB-A': 3, 'Sample, special': 2})

    def test_reject_invalid_input(self):
        for text in ('', 'sample', ', 3', 'sample, 0', 'sample, 9', 'sample, 1.5',
                     'sample, nope', 'sample, 1\nsample, 2', 'Water, 2', 'unused, 1'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_samples(text)


class RandomizationTests(unittest.TestCase):
    def assert_layout(self, plate, samples, water, excluded):
        self.assertEqual(set(plate), set(WELLS))
        self.assertTrue(all(plate[well] == 'Water' for well in water))
        self.assertTrue(all(plate[well] == 'Unused' for well in excluded))
        observed = Counter(value for value in plate.values() if value not in ('Water', 'Unused'))
        self.assertEqual(observed, samples)
        for label, count in samples.items():
            wells = [well for well, value in plate.items() if value == label]
            self.assertEqual(len({row for row, _ in wells}), count)
            self.assertTrue(all(well in SAMPLE_WELLS for well in wells))
            grouped = [sum(col in group for _, col in wells) for group in GROUPS]
            self.assertLessEqual(max(grouped) - min(grouped), 1)

    def test_default_across_seeds(self):
        samples = dict.fromkeys(DEFAULT_LABELS, 3)
        water = default_water()
        for seed in range(25):
            with self.subTest(seed=seed):
                self.assert_layout(randomize_plate(seed, samples, water, set()), samples, water, set())

    def test_reproducible(self):
        args = (20539, {'A': 1, 'B': 2, 'C': 3, 'D': 5}, default_water(), set())
        self.assertEqual(randomize_plate(*args), randomize_plate(*args))
        self.assertNotEqual(randomize_plate(*args), randomize_plate(7, *args[1:]))

    def test_all_counts_and_selected_wells(self):
        samples = {f'Sample {count}': count for count in range(1, 9)}
        water, excluded = {('A', 2), ('C', 4)}, {('B', 2), ('F', 7)}
        self.assert_layout(randomize_plate(4, samples, water, excluded), samples, water, excluded)

    def test_single_replicates_use_only_available_group(self):
        # Previously, preselecting groups rejected this feasible design.
        available = {('B', 2), ('C', 2), ('D', 3), ('E', 4)}
        excluded = set(WELLS) - available
        samples = {f'Sample {index}': 1 for index in range(4)}
        for seed in range(10):
            self.assert_layout(randomize_plate(seed, samples, set(), excluded), samples, set(), excluded)

    def test_tiny_layouts_agree_with_exhaustive_search(self):
        candidates = [('A', 2), ('B', 3), ('A', 5), ('C', 6), ('B', 8), ('C', 9)]
        samples = {'X': 2, 'Y': 1}
        for kept in itertools.combinations(candidates, 4):
            feasible = any(len({w[0] for w in pair}) == 2
                           and len({next(i for i, group in enumerate(GROUPS) if w[1] in group)
                                    for w in pair}) == 2
                           for pair in itertools.combinations(kept, 2))
            excluded = set(WELLS) - set(kept)
            if feasible:
                self.assert_layout(randomize_plate(42, samples, set(), excluded), samples, set(), excluded)
            else:
                with self.assertRaises(ValueError):
                    randomize_plate(42, samples, set(), excluded)

    def test_capacity_and_row_errors(self):
        for samples, excluded in [({'X': 7}, set()), ({f'S{i}': 6 for i in range(11)}, set()),
                                  ({'X': 1}, set(WELLS))]:
            with self.subTest(samples=samples), self.assertRaises(ValueError):
                randomize_plate(1, samples, default_water() - excluded, excluded)

    def test_impossible_balanced_groups(self):
        available = {('A', 2), ('B', 3), ('C', 4)}
        with self.assertRaisesRegex(ValueError, 'No layout'):
            randomize_plate(1, {'X': 3}, set(), set(WELLS) - available)

    def test_invalid_api_inputs(self):
        for samples, seed, water, excluded in [({'X': True}, 1, set(), set()),
                                               ({'X': 1}, 'seed', set(), set()),
                                               ({'X': 1}, 1, {('Z', 1)}, set()),
                                               ({'X': 1}, 1, {('A', 1)}, {('A', 1)})]:
            with self.assertRaises(ValueError):
                randomize_plate(seed, samples, water, excluded)

    def test_search_budget_is_reported_separately(self):
        with self.assertRaises(SearchLimitError):
            randomize_plate(1, {'X': 3}, set(), set(), max_steps=1)

    def test_does_not_mutate_inputs(self):
        samples, water, excluded = {'X': 3}, default_water(), {('B', 2)}
        original = samples.copy(), water.copy(), excluded.copy()
        randomize_plate(1, samples, water, excluded)
        self.assertEqual((samples, water, excluded), original)


class CsvTests(unittest.TestCase):
    def test_round_trip_unicode_commas_and_quotes(self):
        samples = {'α, "sample"': 3}
        plate = randomize_plate(1, samples, default_water(), {('B', 2)})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'plate.csv'
            export_csv(path, plate)
            self.assertTrue(path.read_bytes().startswith(b'\xef\xbb\xbf'))
            with path.open(encoding='utf-8-sig', newline='') as source:
                rows = list(csv.reader(source))
        self.assertEqual(rows[0], ['Row', *map(str, range(1, 13))])
        self.assertEqual(len(rows), 9)
        for index, row in enumerate(ROWS, 1):
            self.assertEqual(rows[index], [row, *(plate[row, col] for col in range(1, 13))])


if __name__ == '__main__':
    unittest.main()
