#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

# What it does: publish the documentation website, web_docs/ as committed on main, to the gh-pages branch on GitHub,
# which GitHub Pages serves at https://mpdehaan.github.io/llamatron/ once the repository's Settings > Pages >
# Build and deployment > Source is "Deploy from a branch", with the branch gh-pages and the folder / (root).
# GitHub Pages can serve only a branch's top folder or its docs/ folder, never web_docs/, so the site is
# published as the whole of a branch of its own. The gh-pages branch holds one commit, made fresh each time from
# the committed web_docs/, with no history, and is pushed with --force. Nothing is built here: run
# internal_tools/build_docs.sh and commit web_docs/ first. Uncommitted changes to web_docs/ are not published.
# The website never goes up ahead of the code it describes: the script refuses while main holds
# commits that GitHub's main doesn't, and internal_tools/push_all.sh pushes main and then publishes, in that order.

set -eu
cd "$(dirname "$0")/.."

if ! git cat-file -e HEAD:web_docs/index.html 2>/dev/null; then
    echo "web_docs/index.html isn't committed: run internal_tools/build_docs.sh and commit web_docs/ first" >&2
    exit 1
fi
if [ -n "$(git status --porcelain -- web_docs)" ]; then
    echo "web_docs/ has uncommitted changes, which won't be published: commit them first to publish them" >&2
fi
# What GitHub's main holds is asked afresh, and the last answer is used when GitHub can't be reached.
git fetch --quiet origin main 2>/dev/null || true
waiting=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo unknown)
if [ "$waiting" != "0" ]; then
    echo "not published: $waiting commits here are not on GitHub's main yet, and the website would describe code nobody can get." >&2
    echo "run internal_tools/push_all.sh, which pushes main and then publishes the website" >&2
    exit 1
fi
tree=$(git rev-parse HEAD:web_docs)
commit=$(git commit-tree "$tree" -m "The documentation website, from web_docs/ at $(git rev-parse --short HEAD)")
git push --force origin "$commit:refs/heads/gh-pages"
echo "published web_docs/ to the gh-pages branch: https://mpdehaan.github.io/llamatron/ in a minute or two"
