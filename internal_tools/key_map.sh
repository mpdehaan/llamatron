#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# What it does: writes .claude/KEYMAP.md, what every key does on every page and at each place of its cursor, from the
# key tour of test/test_tui_help_keys.py, so that a question about a key is one lookup. Run it after changing a key.
set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

cd test
LLAMATRON_WRITE_KEY_MAP=1 exec ../.venv/bin/python -m unittest test_tui_help_keys.TestKeyMapIsCurrent
