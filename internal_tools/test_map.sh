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

# What it does: run the whole suite once under coverage, each class's data in .test_coverage/, and turn it into .test_map.json,
# the map of which test classes run which source files that internal_tools/test_changed.sh runs by. Run it again after
# adding many tests or moving code between files; it takes several minutes.
#
#     internal_tools/test_map.sh

set -e
cd "$(dirname "$0")/.."
rm -rf .test_coverage
mkdir .test_coverage
LLAMATRON_TEST_COVERAGE=.test_coverage internal_tools/test.sh || true
.venv/bin/python internal_tools/test_map.py build
echo "wrote .test_map.json"
