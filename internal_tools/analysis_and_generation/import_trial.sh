#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
# What it does: imports every MIDI file in a folder as the Import Wizard would and reports how well each song was cut up, into /tmp/claude/llamatron/import_trials/, development only.
set -eu
# Run from the top folder, two above this script's, wherever it is started from.
cd "$(dirname "$0")/../.."

exec env PYTHONPATH=. .venv/bin/python internal_tools/analysis_and_generation/import_trial.py "$@"
