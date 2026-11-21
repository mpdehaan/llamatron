#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: bring the documents people see up to date, without pushing: retake the tracker's screenshots and commit
# only the shots whose picture changed, then rebuild the documentation website and commit web_docs/ if the build changed
# it. It is run when the documents are asked to be rebuilt, and by internal_tools/push_all.sh before every push, so that
# no screenshot is retaken in the middle of other work and none goes up stale.

set -eu
cd "$(dirname "$0")/.."

for folder in docs/screenshots web_docs; do
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
if [ -n "$(git status --porcelain -- web_docs)" ]; then
    git add web_docs
    git commit -q -m "The website rebuilt."
    echo "committed the rebuilt website"
fi
