#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: export every example in every kind, with a fixed seed, into .cache/compare_exports/ or the directory named, as a reference to compare against later

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/compare_exports.py capture "${1:-.cache/compare_exports}"
