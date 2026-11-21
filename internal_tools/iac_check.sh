#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: a scale run out of a real IAC bus and back, said note by note, the one script that touches real MIDI

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/iac_check.py "$@"
