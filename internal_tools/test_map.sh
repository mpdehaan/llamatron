#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: run the whole suite once under coverage, each class's data in tests/.cache/coverage/, and turn it into tests/.cache/test_map.json,
# the map of which test classes run which source files that internal_tools/test_changed.sh runs by. Run it again after
# adding many tests or moving code between files; it takes several minutes.
#
#     internal_tools/test_map.sh

set -e
cd "$(dirname "$0")/.."
rm -rf tests/.cache/coverage
mkdir -p tests/.cache/coverage
LLAMATRON_TEST_COVERAGE=tests/.cache/coverage internal_tools/test.sh || true
.venv/bin/python internal_tools/test_map.py build
echo "wrote tests/.cache/test_map.json"
