#!/bin/sh
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# What it does: publish the documentation website, web_docs/ as committed on main, to the gh-pages branch on GitHub,
# which GitHub Pages serves at https://mpdehaan.github.io/llamatron/ once the repository's Settings > Pages >
# Build and deployment > Source is "Deploy from a branch", with the branch gh-pages and the folder / (root).
# GitHub Pages can serve only a branch's top folder or its docs/ folder, never web_docs/, so the site is
# published as the whole of a branch of its own. The gh-pages branch holds one commit, made fresh each time from
# the committed web_docs/, with no history, and is pushed with --force. Nothing is built here: run
# internal_tools/build_docs.sh and commit web_docs/ first. Uncommitted changes to web_docs/ are not published.

set -eu
cd "$(dirname "$0")/.."

if ! git cat-file -e HEAD:web_docs/index.html 2>/dev/null; then
    echo "web_docs/index.html isn't committed: run internal_tools/build_docs.sh and commit web_docs/ first" >&2
    exit 1
fi
if [ -n "$(git status --porcelain -- web_docs)" ]; then
    echo "web_docs/ has uncommitted changes, which won't be published: commit them first to publish them" >&2
fi
tree=$(git rev-parse HEAD:web_docs)
commit=$(git commit-tree "$tree" -m "The documentation website, from web_docs/ at $(git rev-parse --short HEAD)")
git push --force origin "$commit:refs/heads/gh-pages"
echo "published web_docs/ to the gh-pages branch: https://mpdehaan.github.io/llamatron/ in a minute or two"
