#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: the MacroComposer: a set composed from a song's input file, an existing set written as an input (--decompose), or the two compared (--same-as)

set -eu
# Plain sh, so that internal_tools/macro_compose.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/macro_compose.py "$@"
