#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
# What it does: record a video of the tracker playing a set on Arrange (docs/RECORDING.md): --sound daw (the default) for the sound from the DAW, --sound fluidsynth for the set's own instruments and no DAW, --interactive to start, perform and end the take yourself

set -eu
# Plain sh, so that sh user_scripts/record.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/record_demo.py "$@"
