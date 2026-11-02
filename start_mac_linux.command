#!/bin/sh
# Works even if launched from a different directory or a path containing spaces.
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
    python3 plate_randomizer_gui.py "$@"
    result=$?
elif command -v python >/dev/null 2>&1; then
    python plate_randomizer_gui.py "$@"
    result=$?
else
    echo 'Python was not found. Install Python 3.10 or newer; see README.md.' >&2
    result=1
fi
if [ "$result" -ne 0 ] && [ -t 0 ]; then
    printf '\nPress Enter to close… '
    read -r answer
fi
exit "$result"
