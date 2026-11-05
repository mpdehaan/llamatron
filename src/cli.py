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

"""Turns a song file into an Ableton Live set or a directory of MIDI clips.

    python -m src.cli examples/minimal_techno.yml --to ableton
    python -m src.cli examples/minimal_techno.yml --to cliptree --out output/my_song
"""

import argparse
import glob
import os
import sys

from src.renderers.ableton_project import DEFAULT_TEMPLATE, AbletonProject
from src.renderers.clip_tree import ClipTree
from src.song import Song
from src.song_file import SongFileError, load_song


def _arguments(argv):
    parser = argparse.ArgumentParser(prog='noose', description='Turn a song file into Ableton Live or MIDI files.')
    parser.add_argument('song', help='the song file to read')
    parser.add_argument('--to', choices=['ableton', 'cliptree'], default='ableton', help='what to write (default: ableton)')
    parser.add_argument('--out', help='the directory to write to (default: output/<song name>)')
    parser.add_argument('--template', default=DEFAULT_TEMPLATE, help='the Live set to build from')
    parser.add_argument('--replace', action='store_true', help='replace this song\'s earlier output, so you can regenerate and listen')
    return parser.parse_args(argv)


def replace_output(to, directory):
    """Remove what rendering a song to a directory would write, and leave everything else."""
    if to == 'ableton':
        targets = [AbletonProject(directory, Song()).path]
    else:
        targets = glob.glob(os.path.join(glob.escape(directory), '[0-9]*-[0-9]*.mid'))
    for path in targets:
        if os.path.exists(path):
            os.remove(path)


def main(argv=None):
    """Return 0 if the song was written, or 1 after explaining what went wrong."""
    arguments = _arguments(argv)
    name = os.path.splitext(os.path.basename(arguments.song))[0]
    directory = arguments.out or os.path.join('output', name)
    try:
        song = load_song(arguments.song)
        if arguments.replace:
            replace_output(arguments.to, directory)
        if arguments.to == 'ableton':
            AbletonProject(directory, song, template=arguments.template).render()
        else:
            ClipTree(directory, song).render()
    except (SongFileError, ValueError, OSError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    print(f'wrote {arguments.to} output to {directory}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
