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

# What it does: export every example as an Ableton Live set beside it, replacing earlier exports

# Writes an Ableton Live set for every song in examples/, beside its set as <set name>_<song name>.als in the set's own folder.
# This replaces each song's earlier set, including anything saved over it in Live, so that you
# can edit a song, run this again and listen. Save your own work in Live under another name.

set -e

# The program has to run from the top folder of the project, the one above this script's.
cd "$(dirname "$0")/.."

if [ ! -x .venv/bin/python ]; then
    echo '.venv is missing, so please set it up first:'
    echo '    python3 -m venv .venv'
    echo '    .venv/bin/python -m pip install -e .'
    exit 1
fi

if ! .venv/bin/python -c 'import llamatron' 2>/dev/null; then
    echo 'llamatron is not installed in .venv, so please install it first:'
    echo '    .venv/bin/python -m pip install -e .'
    exit 1
fi

# Every set in the folders of examples/, at any depth, leaving out examples/midi, which holds MIDI files rather than sets.
find examples -name '*.yml' -not -path 'examples/midi/*' | sort | while read -r file; do
    .venv/bin/python -m llamatron "$file" --to ableton --replace
done
