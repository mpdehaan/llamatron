#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: export every example as one General MIDI file each into previews/, to listen to them all in any MIDI player

set -eu
# Plain sh. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/preview_midi.py --out previews "$@"
