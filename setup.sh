#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: install what llamatron needs, then build it

# Install what llamatron needs and build it:
#
#     sh setup.sh
#
# It makes .venv, a Python environment for the development tools, with what python/requirements.txt names, then runs
# build.sh, which offers to install Rust and builds llamatron. FluidSynth, for General MIDI sound, is installed apart by
# user_scripts/install_fluidsynth.sh.

set -eu
# Run from the top folder, where this script is, wherever it is started from.
cd "$(dirname "$0")"

python3 -m venv .venv
.venv/bin/python -m pip install -r python/requirements.txt
sh build.sh
