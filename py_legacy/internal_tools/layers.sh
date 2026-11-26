#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: list the imports that cross the program's layers the wrong way (--prune takes those that are gone off the allowed list)

set -eu
# Plain sh, so that internal_tools/layers.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/layers.py "$@"
