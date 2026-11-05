#!/bin/sh
# llamatron: a Python language and framework for producing MIDI clips.
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

# Opens the text UI, or opens it on a song if one is named, such as:
#     ./run_tui.sh examples/retro_chill.yml

set -e

# The program has to run from the top folder of the project.
cd "$(dirname "$0")"

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

exec .venv/bin/python -m llamatron "$@"
