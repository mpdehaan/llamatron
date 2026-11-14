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

# What it does: the tests whose name holds any of the names given: internal_tools/test_one.sh test_rational

set -eu
# Run from the top folder, the one above this script's, wherever it is started from.
cd "$(dirname "$0")/.."

if [ "$#" -eq 0 ]; then
    echo "name the tests to run, such as: internal_tools/test_one.sh test_rational" >&2
    exit 1
fi
exec internal_tools/test.sh "$@"
