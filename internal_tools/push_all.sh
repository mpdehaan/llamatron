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

# What it does: rebuild the documentation website and commit web_docs/ if the build changed it, push main to GitHub
# and then publish the website, in that order, so that the website is rebuilt only at a push and never describes code
# nobody can get (the user's rules). It stops if the push fails, never pushes with --force, and
# runs only on main. It is the one command that sends anything to GitHub: Claude runs it when asked to push.

set -eu
cd "$(dirname "$0")/.."

branch=$(git rev-parse --abbrev-ref HEAD)
if [ "$branch" != "main" ]; then
    echo "not pushed: this is the branch $branch, and only main is pushed and published" >&2
    exit 1
fi
if [ -n "$(git status --porcelain -- web_docs)" ]; then
    echo "not pushed: web_docs/ has changes that are not committed; commit or discard them first" >&2
    exit 1
fi
internal_tools/build_docs.sh
if [ -n "$(git status --porcelain -- web_docs)" ]; then
    git add web_docs
    git commit -q -m "The website rebuilt before a push."
    echo "committed the rebuilt website"
fi
git push origin main
internal_tools/publish_docs.sh
