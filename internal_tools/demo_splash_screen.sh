#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: show the start screen on its own, its title coming in and holding five seconds (or --seconds N), then fading out and quitting; --scroll-text WORDS then shows those words crossing the screen, as a recording shows the name of a demo

set -eu
# Plain sh. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/demo_splash_screen.py "$@"
