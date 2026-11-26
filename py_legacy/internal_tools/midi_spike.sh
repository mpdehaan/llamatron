#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: how tightly a separate process sends an example's MIDI in real time

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/midi_timing_spike.py examples/by_genre/ragtime/entertainer.yml --seconds 25 --busy "$@"
