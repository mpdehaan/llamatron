#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: make .venv and install llamatron into it

set -eu
# Plain sh. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

python3 -m venv .venv
.venv/bin/python -m pip install -e .
