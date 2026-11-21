#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: strings written out in tests/ and internal_tools/, or in the files named, that repeat a value the program already names

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

if [ $# -eq 0 ]; then
    set -- tests internal_tools
fi
exec .venv/bin/python internal_tools/repeated_values.py "$@"
