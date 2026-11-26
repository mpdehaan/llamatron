#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: bring the documentation website up to date, without pushing: rebuild it and commit web_docs/ if the build
# changed it. It is run when the documents are asked to be rebuilt, and by internal_tools/push_all.sh before every push, so
# that the website never goes up stale.

set -eu
cd "$(dirname "$0")/.."

for folder in docs/screenshots web_docs; do
    if [ -n "$(git status --porcelain -- "$folder")" ]; then
        echo "not rebuilt: $folder has changes that are not committed; commit or discard them first" >&2
        exit 1
    fi
done
# The screenshots were taken from the Python tracker, which is retired; they stay as last taken until llamatron takes them.
internal_tools/build_docs.sh
if [ -n "$(git status --porcelain -- web_docs)" ]; then
    git add web_docs
    git commit -q -m "The website rebuilt."
    echo "committed the rebuilt website"
fi
