#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: measure the program after a step of the refactoring and add a row to .claude/planning/REFACTORING_LOG.md (--show to only print)

set -eu
# Plain sh, so that internal_tools/refactor_log.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/refactor_log.py "$@"
