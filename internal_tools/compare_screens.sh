#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: capture every page as the key tour draws it, at 80x24 and 160x50, into a directory (capture DIR), or capture again and say where any screen differs from one made before (compare DIR), the dialogs the UI tests show among them, or the dialogs alone (capture-dialogs DIR, compare-dialogs DIR), so that a change meant to leave the screens alone is proved to

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

# The hash seed is fixed so that nothing a capture shows can differ by the order of a hash. The tool says what it found on its
# output; what goes to the errors is asyncio's notes of slow steps, which the tests turn on, and is left out.
exec env PYTHONHASHSEED=0 PYTHONPATH=. .venv/bin/python internal_tools/compare_screens.py "${1:-compare}" "${2:-.compare_screens}" 2>/dev/null
