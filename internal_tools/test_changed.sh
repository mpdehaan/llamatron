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

# What it does: run only the test classes that cover the files changed since the last commit, staged or not, and new files,
# by the map internal_tools/test_map.sh made, with the rule tests always; the whole suite when a changed file is one the map
# can't place, or when there is no map. The quick run while working and before a commit; the whole suite runs before a push.
#
#     internal_tools/test_changed.sh

set -e
cd "$(dirname "$0")/.."
changed=$( { git diff --name-only HEAD; git ls-files --others --exclude-standard; } | sort -u)
if [ -z "$changed" ]; then
    echo "nothing has changed since the last commit"
    exit 0
fi
classes=$(.venv/bin/python internal_tools/test_map.py changed $changed)
if [ "$classes" = "ALL" ]; then
    exec internal_tools/test.sh
fi
exec internal_tools/test.sh $classes
