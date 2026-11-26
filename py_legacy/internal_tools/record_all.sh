#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: record a batch video of every example through FluidSynth, shortest first, each with its visualizer mode filling the frame (LLAMATRON_BATCH_RECORD_MAX=2 for the two shortest)

set -eu
# Plain sh. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/record_batch.py "$@"
