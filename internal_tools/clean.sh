#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: remove the tools' caches in .cache/, the examples' exports and Python caches, never output/

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

# Everything in .cache/ is rebuilt by the tool that made it; output/ holds previews, recordings and the library, never removed here.
rm -rf .cache
rm -f examples/*.als examples/*.mid
find . -name __pycache__ -type d -prune -exec rm -rf {} +
