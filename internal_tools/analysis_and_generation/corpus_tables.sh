#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
# What it does: measures every corpus source fetched into .corpus/ into tables for meta-analysis and calibration, rebuilding stale ones, development only.
set -eu
# Run from the top folder, two above this script's, wherever it is started from.
cd "$(dirname "$0")/../.."

cd internal_tools/analysis_and_generation && exec ../../.venv/bin/python corpus_tables.py "$@"
