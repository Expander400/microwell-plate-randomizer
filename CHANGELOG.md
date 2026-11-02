# Changelog

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
