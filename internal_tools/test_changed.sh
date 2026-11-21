#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: run only the test classes that cover the files changed since the last commit, staged or not, and new files,
# by the map internal_tools/test_map.sh made, with the rule tests always; the whole suite when a changed file is one the map
# can't place, or when there is no map. The quick run while working and before a commit; the whole suite runs before a push.
#
#     internal_tools/test_changed.sh

set -e
cd "$(dirname "$0")/.."
changed=$( { git diff --name-only HEAD; git ls-files --others --exclude-standard; } | sort -u)
if [ -z "$changed" ]; then
    echo "nothing has changed since the last commit"
    exit 0
fi
classes=$(.venv/bin/python internal_tools/test_map.py changed $changed)
if [ "$classes" = "ALL" ]; then
    exec internal_tools/test.sh
fi
exec internal_tools/test.sh $classes
