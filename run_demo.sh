#!/bin/sh
# noose6: a Python language and framework for producing MIDI clips.
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

# Runs every demo in demo/ in alphabetical order, which also runs mary_arp before
# mary_transpose, as that demo needs. Demos won't replace files they've already
# written, so to run them all again from scratch, use: rm -rf output && ./run_demo.sh

set -e

# Demos have to run from the top folder of the project.
cd "$(dirname "$0")"

# Sorts the files the same way everywhere, with mary.py before mary_arp.py.
LC_ALL=C

if [ ! -x .venv/bin/python ]; then
    echo '.venv is missing, so please set it up first:'
    echo '    python3 -m venv .venv'
    echo '    .venv/bin/python -m pip install -r requirements.txt'
    exit 1
fi

for file in demo/*.py; do
    demo="$(basename "$file" .py)"
    echo "Running demo.$demo"
    .venv/bin/python -m "demo.$demo"
done
