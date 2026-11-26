#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: publish the documentation website, as built into output/web_docs/, to the gh-pages branch on GitHub,
# which GitHub Pages serves at https://mpdehaan.github.io/llamatron/ once the repository's Settings > Pages >
# Build and deployment > Source is "Deploy from a branch", with the branch gh-pages and the folder / (root).
# GitHub Pages can serve only a branch's top folder or its docs/ folder, so the site is published as the whole of a
# branch of its own. The gh-pages branch holds one commit, made fresh each time from the built output/web_docs/, with
# no history, and is pushed with --force; main never holds the built site. Nothing is built here: run
# internal_tools/build_docs.sh first.
# The website never goes up ahead of the code it describes: the script refuses while main holds
# commits that GitHub's main doesn't, and internal_tools/push_all.sh pushes main and then publishes, in that order.

set -eu
cd "$(dirname "$0")/.."

SITE='output/web_docs'
if [ ! -f "$SITE/index.html" ]; then
    echo "$SITE/index.html isn't built: run internal_tools/build_docs.sh first" >&2
    exit 1
fi
git fetch --quiet origin main 2>/dev/null || true
waiting=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo unknown)
if [ "$waiting" != "0" ]; then
    echo "not published: $waiting commits here are not on GitHub's main yet, and the website would describe code nobody can get." >&2
    echo "run internal_tools/push_all.sh, which pushes main and then publishes the website" >&2
    exit 1
fi
# The built site's files are written into a tree of their own through an index of their own, so that main's index and
# history are never touched, and that tree is the whole of the gh-pages branch.
index="$(git rev-parse --absolute-git-dir)/publish_docs_index"
rm -f "$index"
GIT_INDEX_FILE="$index" git --work-tree="$SITE" add -A .
tree=$(GIT_INDEX_FILE="$index" git write-tree)
rm -f "$index"
commit=$(git commit-tree "$tree" -m "The documentation website, built from main at $(git rev-parse --short HEAD)")
git push --force origin "$commit:refs/heads/gh-pages"
echo "published output/web_docs/ to the gh-pages branch: https://mpdehaan.github.io/llamatron/ in a minute or two"
