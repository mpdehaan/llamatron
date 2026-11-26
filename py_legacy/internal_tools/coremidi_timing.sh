#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: how tightly MIDI arrives from the Realtime Sender Process with each driver, immediate and timestamped, at rest or under load (macOS only)

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."
exec .venv/bin/python internal_tools/coremidi_timing.py "$@"
