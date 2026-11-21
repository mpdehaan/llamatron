#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: say how big the step in loudness is into the first chorus of what the song wizard makes, in every subgenre
# What it does: print a line for the song every choice of the song wizard makes, each song as a short hash, to compare before and after a change that should leave the wizard's songs alone

set -eu
# Plain sh, so that internal_tools/wizard_songs.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

# The tests' list of every choice the wizard offers is what the tool goes through, so the top folder is where modules are found.
PYTHONPATH=. exec .venv/bin/python internal_tools/wizard_songs.py "$@"
