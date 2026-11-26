#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: one line per example set: its length when played, scenes, tracks and a few features; --format ascii or --format markdown for borders or Markdown

set -eu
# Plain sh, so that internal_tools/demo_summary.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/demo_summary.py "$@"
