#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: the tests whose name holds any of the names given: internal_tools/test_one.sh test_rational

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

if [ "$#" -eq 0 ]; then
    echo "name the tests to run, such as: internal_tools/test_one.sh test_rational" >&2
    exit 1
fi
exec internal_tools/test.sh "$@"
