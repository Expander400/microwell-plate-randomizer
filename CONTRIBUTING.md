# Contributing

Use Python 3.10 or newer. The app and test suite use only the standard library;
Tkinter is required for the GUI. See the README for installation instructions.

## AI-assisted development

This project was developed with OpenAI Codex. AI assistance was used to write
and revise the application code, tests and documentation, starting from an initial
Python script and user requirements. Review AI-generated changes and run the
relevant tests just as you would for any other contribution.

## Project structure

```text
plate_randomizer_gui.py        Download-and-run launcher
start_windows.bat              Windows launcher with visible error messages
start_mac_linux.command        macOS/Linux launcher
microwell_plate_randomizer/
    __init__.py               App version
    __main__.py               CLI and startup diagnostics
    core.py                   Input validation, constraint search, CSV export
    gui.py                    Tkinter interface and background search
examples/                     Default sample list
tests/                        Core, startup and GUI tests
.github/workflows/tests.yml   Automated checks
tools/build_source_archive.py Clean source ZIP builder
docs/screenshot.png          App screenshot for the README
```

## Checks before submitting a change

```sh
python3 -m unittest discover -s tests -v
python3 plate_randomizer_gui.py --check
```

On Windows use `py -3` in place of `python3`. The second command needs a desktop
display. On a Linux system with Xvfb installed, GUI tests can run headlessly:

```sh
xvfb-run -a python3 -m unittest discover -s tests -v
```

Add tests for changes to placement constraints, parsing or export behavior.
Preserve deterministic ordering; do not use unordered sets to choose candidates.
Keep GUI calls on the main thread. Worker results must be discarded when their
settings snapshot no longer matches the current settings.

Changes to the search algorithm may change seeded layouts. Document this in
`CHANGELOG.md` and update the version in both `pyproject.toml` and
`microwell_plate_randomizer/__init__.py` for releases.

Report bugs with the operating system, Python/app versions, exact error, seed,
sample list and well selections needed to reproduce the issue.
