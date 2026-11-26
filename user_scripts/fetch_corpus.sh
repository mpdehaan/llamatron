#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: download the public domain music corpus (scores and traditional tunes) into output/corpus/, asking before each collection

# The corpus llamatron's song wizard was measured from, and which the song wizard is to import songs from, kept on this
# computer only in output/corpus/, which git ignores:
#
#     sh user_scripts/fetch_corpus.sh                  # asks collection by collection, with each one's size and terms
#     sh user_scripts/fetch_corpus.sh joplin thesession     # only the named collections, by their folders
#     sh user_scripts/fetch_corpus.sh --all            # every collection, without asking
#
# docs/CREDITS.md lists each collection, its link, its terms and its folder.
set -eu
# Run from the top folder, one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

exec .venv/bin/python python/src/llamatron_tools/fetch_corpus.py "$@"
