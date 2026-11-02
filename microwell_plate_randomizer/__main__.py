"""Command-line entry point with actionable startup errors."""

import argparse
import sys

from . import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(description="Open the Microwell Plate Randomizer desktop app.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--check", action="store_true", help="check Python, Tkinter and desktop display, then exit")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 10):
        print("Python 3.10 or newer is required. See README.md for installation instructions.", file=sys.stderr)
        return 1
    try:
        import tkinter as tk
        from .gui import App
    except ImportError as exc:
        print(f"Tkinter could not be loaded: {exc}\n"
              "Install Python with Tcl/Tk support. On Ubuntu/Debian: sudo apt install python3-tk\n"
              "On Arch/CachyOS: sudo pacman -Syu tk\n"
              "On Windows/macOS, use a full Python distribution from python.org.\n"
              "See README.md for details; Tkinter is not installed with pip.", file=sys.stderr)
        return 1
    try:
        app = App()
    except tk.TclError as exc:
        print(f"The graphical interface could not start: {exc}\n"
              "Run from a local desktop session with a working display and Tcl/Tk installation.\n"
              "See the troubleshooting section in README.md.", file=sys.stderr)
        return 1
    if args.check:
        app.withdraw()
        print(f"Python {sys.version.split()[0]}, Tk {app.tk.call('info', 'patchlevel')}, desktop display: OK")
        app.destroy()
    else:
        app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
