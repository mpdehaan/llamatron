#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# Runs the llamatron command from the project folder, which opens the tracker,
# on a set if one is named, or exports with --to, such as:
#     ./llamatron.sh examples/learning/08_tie.yml

set -e

# The program has to run from the top folder of the project, where this script is.
cd "$(dirname "$0")"

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

exec .venv/bin/python -m llamatron "$@"
