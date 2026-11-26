#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: how long each visualizer mode takes to draw a frame, with 8 and 64 tracks, on an 80 by 24 console and a large terminal

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/time_visualizer.py "$@"
