#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: say how much of what the song wizard makes repeats, for each player and each kind of section of a subgenre

set -eu
# Plain sh, so that internal_tools/monotony_report.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/monotony_report.py "$@"
