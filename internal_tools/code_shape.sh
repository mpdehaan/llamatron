#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: list what breaks the rules of a function's shape in the program (--prune takes the places that are gone off the lists)

set -eu
# Plain sh, so that internal_tools/code_shape.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/code_shape.py "$@"
