#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: bring the documents people see up to date, without pushing: retake the screenshots and commit those that
# changed, then rebuild the documentation website into output/web_docs/, which git ignores and the publishing pushes to the gh-pages branch. It is run when the documents are asked to be rebuilt, and by internal_tools/push_all.sh before every push, so
# that the website never goes up stale.

set -eu
cd "$(dirname "$0")/.."

for folder in docs/screenshots; do
    if [ -n "$(git status --porcelain -- "$folder")" ]; then
        echo "not rebuilt: $folder has changes that are not committed; commit or discard them first" >&2
        exit 1
    fi
done
internal_tools/screenshots.sh
if [ -n "$(git status --porcelain -- docs/screenshots)" ]; then
    git add docs/screenshots
    git commit -q -m "The screenshots retaken."
    echo "committed the screenshots that changed"
fi
internal_tools/build_docs.sh
