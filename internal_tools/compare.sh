#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: export them all again and list every file that differs from the reference in .compare_exports/ or the directory named, byte for byte

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/compare_exports.py compare "${1:-.compare_exports}"
