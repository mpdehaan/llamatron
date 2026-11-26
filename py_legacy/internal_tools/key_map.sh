#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: writes .claude/reference/KEYMAP.md, what every key does on every page and at each place of its cursor, from the
# key tour of tests/interface/tracker/test_tui_help_keys.py, so that a question about a key is one lookup. Run it after changing a key.
set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

LLAMATRON_WRITE_KEY_MAP=1 exec .venv/bin/python -m unittest tests.interface.tracker.test_tui_help_keys.TestKeyTour
