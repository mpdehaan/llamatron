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
# What it does: takes the kit's, bass's and chord part's cells of every song of Lakh's clean subset into .corpus/tables/lakh-cells.jsonl, development only.
set -eu
# Run from the top folder, two above this script's, wherever it is started from.
cd "$(dirname "$0")/../.."

cd internal_tools/analysis_and_generation && exec ../../.venv/bin/python extract_cells.py "$@"
