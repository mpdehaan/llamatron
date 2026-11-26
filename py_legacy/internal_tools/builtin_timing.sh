#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
# What it does: play a few seconds through the built-in synths and report their timing: start, MIDI's delay, dropouts, late notes and callback times

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python -m internal_tools.builtin_timing "$@"
