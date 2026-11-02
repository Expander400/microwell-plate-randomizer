"""Plate layout logic and CSV export, usable without a graphical display."""

import csv
import random
from pathlib import Path

ROWS = "ABCDEFGH"
COLUMNS = range(1, 13)
# Extend the original outer groups to include the optional border columns.
# Adding a water perimeter keeps the original interior sampling groups.
GROUPS = (range(1, 5), range(5, 8), range(8, 13))
WELLS = tuple((row, col) for row in ROWS for col in COLUMNS)
SAMPLE_WELLS = frozenset((row, col) for row in ROWS for group in GROUPS for col in group)
DEFAULT_LABELS = [f"Sample {letter}" for letter in "ABCDEF"]


class SearchLimitError(ValueError):
    """The search budget was reached; this does not prove a layout impossible."""


def default_water():
    """Return the optional water perimeter; the GUI starts with no water."""
    return {(row, col) for row, col in WELLS if row in "AH" or col in (1, 12)}


def validate_custom_marks(marks, samples):
    """Custom reservations cannot masquerade as sample or built-in status labels."""
    sample_names = {label.casefold() for label in samples}
    for label in marks.values():
        if not isinstance(label, str) or not label.strip() or '\n' in label or '\r' in label:
            raise ValueError("Enter a non-empty, single-line custom mark.")
        if label.strip().casefold() in {"water", "unused", "available", "excluded"} | sample_names:
            raise ValueError(f"Custom mark '{label}' must differ from sample names and well status labels.")


def validate_samples(samples):
    if not samples:
        raise ValueError("Enter at least one sample.")
    for label, count in samples.items():
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Each sample needs a non-empty label.")
        if label.strip().casefold() in {"water", "unused"}:
            raise ValueError(f"'{label}' is reserved for well status. Choose another label.")
        if type(count) is not int or not 1 <= count <= 8:
            raise ValueError(f"Replicates for '{label}' must be a whole number from 1 to 8.")


def parse_samples(text):
    """Read 'label, count' lines, allowing commas inside a label."""
    samples = {}
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        parts = line.rsplit(",", 1)
        if len(parts) != 2 or not parts[0].strip():
            raise ValueError(f"Line {number}: enter a label and count, for example: Sample A, 3")
        label = parts[0].strip()
        if label in samples:
            raise ValueError(f"Line {number}: duplicate sample label '{label}'.")
        try:
            samples[label] = int(parts[1].strip())
        except ValueError:
            raise ValueError(f"Line {number}: replicates must be a whole number.") from None
    validate_samples(samples)
    return samples


def randomize_plate(seed, samples, water, excluded, *, custom_marks=None,
                    fill_unused=False, max_steps=25000):
    """Find a seeded layout with balanced groups and distinct rows per sample.

    Each group gets floor(count / 3) or ceil(count / 3) replicates. The search
    chooses which groups receive extras, rather than committing before checking
    well availability. A bounded search keeps difficult requests finite.
    """
    validate_samples(samples)
    if type(seed) is not int:
        raise ValueError("The seed must be a whole number.")
    water, excluded = set(water), set(excluded)
    custom_marks = dict(custom_marks or {})
    validate_custom_marks(custom_marks, samples)
    marked = set(custom_marks)
    if (water | excluded | marked) - set(WELLS):
        raise ValueError("Well selections must be within rows A–H and columns 1–12.")
    if water & excluded or marked & (water | excluded):
        raise ValueError("Water, excluded, and custom-marked well selections must not overlap.")
    rng = random.Random(seed)
    available = [well for well in WELLS if well in SAMPLE_WELLS and well not in water | excluded | marked]
    if sum(samples.values()) > len(available):
        raise ValueError(f"Requested {sum(samples.values())} replicates, but only {len(available)} sampling wells are available.")
    row_count = len({row for row, _ in available})
    for label, count in samples.items():
        if count > row_count:
            raise ValueError(f"'{label}' needs {count} different rows, but only {row_count} are available. Free rows or reduce replicates.")
    group_for = {col: group for group, columns in enumerate(GROUPS) for col in columns}
    labels = list(samples)
    # Fixed random candidate orders avoid dependence on unordered set iteration.
    orders = {label: rng.sample(available, len(available)) for label in labels}
    remaining = dict(samples)
    lower = {label: count // 3 for label, count in samples.items()}
    upper = {label: (count + 2) // 3 for label, count in samples.items()}
    used_rows = {label: set() for label in labels}
    counts = {label: [0, 0, 0] for label in labels}
    last_index = {label: -1 for label in labels}
    assignments = {}
    steps = 0

    def solve():
        nonlocal steps
        steps += 1
        if steps > max_steps:
            raise SearchLimitError("Search limit reached; a layout may still exist. Try another seed, free more wells, or reduce replicates.")
        active = [label for label in labels if remaining[label]]
        if not active:
            return True
        free_per_group = [sum(well not in assignments and group_for[well[1]] == group
                              for well in available) for group in range(3)]
        for group in range(3):
            minimum_needed = sum(max(0, lower[label] - counts[label][group]) for label in active)
            if minimum_needed > free_per_group[group]:
                return False
        best_label, best_candidates, best_slack = None, None, None
        for label in active:
            deficits = [max(0, lower[label] - count) for count in counts[label]]
            needs_minimum = sum(deficits) == remaining[label]
            candidates = [(index, well) for index, well in enumerate(orders[label])
                          if index > last_index[label] and well not in assignments
                          and well[0] not in used_rows[label]
                          and counts[label][group_for[well[1]]] < upper[label]
                          and (not needs_minimum or deficits[group_for[well[1]]])]
            if len({well[0] for _, well in candidates}) < remaining[label]:
                return False
            capacity = 0
            for group in range(3):
                group_rows = {well[0] for _, well in candidates if group_for[well[1]] == group}
                if len(group_rows) < deficits[group]:
                    return False
                capacity += min(len(group_rows), upper[label] - counts[label][group])
            if capacity < remaining[label]:
                return False
            slack = len(candidates) - remaining[label]
            if best_slack is None or slack < best_slack:
                best_label, best_candidates, best_slack = label, candidates, slack
        label = best_label
        previous_index = last_index[label]
        for index, well in best_candidates:
            group = group_for[well[1]]
            assignments[well] = label
            used_rows[label].add(well[0])
            counts[label][group] += 1
            remaining[label] -= 1
            last_index[label] = index
            if solve():
                return True
            last_index[label] = previous_index
            remaining[label] += 1
            counts[label][group] -= 1
            used_rows[label].remove(well[0])
            del assignments[well]
        return False

    if not solve():
        raise ValueError("No layout satisfies the distinct-row and balanced-group rules. Free more wells or reduce replicates.")
    return {
        well: ("Water" if well in water else custom_marks[well] if well in custom_marks
               else "Unused" if well in excluded else assignments.get(well, "Water" if fill_unused else "Unused"))
        for well in WELLS
    }


def export_csv(path, plate):
    """Write an Excel-friendly UTF-8 CSV, including unused and water wells."""
    with Path(path).open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.writer(output)
        writer.writerow(["Row", *COLUMNS])
        for row in ROWS:
            writer.writerow([row, *(plate[(row, col)] for col in COLUMNS)])
