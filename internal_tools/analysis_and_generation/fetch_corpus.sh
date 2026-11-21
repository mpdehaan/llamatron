#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
# What it does: fetches the public-domain Humdrum scores the corpus study reads into .corpus/, development only.
set -eu
# Run from the top folder, two above this script's, wherever it is started from.
cd "$(dirname "$0")/../.."

exec .venv/bin/python internal_tools/analysis_and_generation/fetch_corpus.py "$@"
