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

# What it does: the checks Claude runs before committing code: the version bump, then every test

# There is no git hook, by the user's rule, so that a person editing documents commits at once; Claude
# stages its files and runs this before committing anything that changes code, tests, examples or
# tools, and commits only when it passes (.claude/TESTING.md).

set -e
# Run from the repository's top folder, wherever it is started.
cd "$(git rev-parse --show-toplevel)"
# A commit that changes the program's Python carries a version bump, which `internal_tools/bump.sh` writes. The check comes
# before the tests because it takes no time: on 2026-11-09 two commits went in without their bump.
.venv/bin/python internal_tools/bump_version.py --check
echo 'check before commit: running every test'
internal_tools/test.sh
