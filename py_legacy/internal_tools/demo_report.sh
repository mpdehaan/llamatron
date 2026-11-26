#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
# What it does: print a report of the demos as comma-separated values, for a spreadsheet: one row per demo with its length, scenes, tracks and features, or with --features one row per feature and a column per demo

set -eu
# Plain sh, so that sh user_scripts/demo_report.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

if [ "${1:-}" = '--features' ]; then
    shift
    exec .venv/bin/python internal_tools/demo_features.py --csv "$@"
fi
exec .venv/bin/python internal_tools/demo_summary.py --csv "$@"
