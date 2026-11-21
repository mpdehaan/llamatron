#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: sort the imports each Python file opens with into the project's order (lists the files out of order; --write to rewrite)

set -eu
# Plain sh, so that internal_tools/sort_imports.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/sort_imports.py "$@"
