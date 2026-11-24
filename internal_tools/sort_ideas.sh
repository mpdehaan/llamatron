#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: keep the ideas file, .claude/planning/IDEAS.yml, sorted by priority (--check to only look)

set -eu
# Plain sh, so that internal_tools/sort_ideas.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/sort_ideas.py "$@"
