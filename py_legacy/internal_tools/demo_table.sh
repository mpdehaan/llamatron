#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: write the index of the examples into docs/DEMOS.md and each demo's summary onto its genre's page in docs/demos/

set -eu
# Plain sh, so that internal_tools/demo_table.sh works. Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python internal_tools/demo_summary.py --write-docs
