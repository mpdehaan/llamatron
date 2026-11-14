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
# What it does: print a report of the demos as comma-separated values, for a spreadsheet: one row per demo with its length, scenes, tracks and features, or with --features one row per feature and a column per demo

set -eu
# Plain sh, so that sh user_scripts/demo_report.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

if [ "${1:-}" = '--features' ]; then
    shift
    exec .venv/bin/python internal_tools/demo_features.py --csv "$@"
fi
exec .venv/bin/python internal_tools/demo_summary.py --csv "$@"
