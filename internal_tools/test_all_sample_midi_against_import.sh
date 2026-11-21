#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: import every MIDI file in examples/midi/ and every example set into a new set: tracks, patterns, scenes, and whether it plays back the same; --longest 64 for another Longest pattern

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/import_check.py "$@"
