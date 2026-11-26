#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# Runs every test, several test classes at once, which takes about 20 seconds rather than
# about two minutes, and reports every result. Add a name to only run the tests matching it,
# one at a time: internal_tools/test.sh test_blend. Use internal_tools/test.sh --serial to run every test in
# one process, the plain unittest way.

set -e

# Tests have to run from the top folder of the project, the one above this script's.
cd "$(dirname "$0")/.."

if [ ! -x .venv/bin/python ]; then
    echo '.venv is missing, so please set it up first:'
    echo '    python3 -m venv .venv'
    echo '    .venv/bin/python -m pip install -e .'
    exit 1
fi

if ! .venv/bin/python -c 'import llamatron' 2>/dev/null; then
    echo 'llamatron is not installed in .venv, so please install it first:'
    echo '    .venv/bin/python -m pip install -e .'
    exit 1
fi

if [ "$1" = "--serial" ]; then
    exec .venv/bin/python -m unittest discover -s tests -t .
fi
# Any names given narrow the run to the tests whose names contain one of them, as unittest's -k does, still in parallel.
exec .venv/bin/python tests/support/parallel.py "$@"
