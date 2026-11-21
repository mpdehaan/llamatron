#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: say how big the step in loudness is into the first chorus of what the song wizard makes, in every subgenre

set -eu
# Plain sh, so that internal_tools/loudness_steps.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/loudness_steps.py "$@"
