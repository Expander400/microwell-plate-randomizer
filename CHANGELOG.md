# Changelog

## 1.2.0 — 2026-11-02

- Start with all wells available and generic Sample A–F examples, each with three replicates.
- Add a quick water-perimeter button and a checkbox to fill unassigned wells with water.
  Explicitly blank and custom-marked wells are preserved.
- Edit non-sample wells after generation without moving samples or clearing the layout.
  Automatic water can be toggled without reserving those wells for the next randomization.
- Add custom text marks that reserve wells from sampling and appear in CSV exports.
- Protect assigned sample wells from accidental edits, with a Clear layout button
  to return to editing. Reset now makes all wells available.
- Update documentation, screenshot, example list and regression tests.

## 1.1.0 — 2026-11-02

- All 96 wells, including columns 1 and 12 and corner wells, can now be marked
  available for samples, water, or excluded (blank).
- Extended the outer column groups to 1–4 and 8–12; the middle group remains 5–7.
  Default water selections and layouts with the default perimeter are unchanged.
- Updated the GUI guidance, README and screenshot, with regression tests for
  border sample placement, blank wells and CSV export.

## 1.0.0 — 2026-11-02

First packaged release, based on the original plate randomizer prototype.

- Editable seed, sample labels and per-sample replicate counts.
- Selectable water and excluded wells; CSV export.
- Balanced column-group placement with distinct rows per sample.
- Fixed premature rejection of layouts caused by randomly preassigning groups.
- Added validation for insufficient rows, well capacity, reserved sample names
  and malformed input; clarified search-limit errors.
- Added background generation, stale-result protection, a scrollable window,
  full-label inspection, and clearer well-status labels.
- Added source launchers, Python package metadata, tests, CI, documentation and
  an MIT license.

The updated search changes generated layouts relative to the prototype, even
when the seed and inputs are identical. Retain the app version with saved results.
