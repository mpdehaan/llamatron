#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: every key binding of the tracker; internal_tools/keys.sh PatternEditor for one page's, internal_tools/keys.sh --key s for every binding that has a key

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/show_keys.py "$@"
