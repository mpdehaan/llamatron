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

"""Opens the tracker, or turns a song file into an Ableton Live set or a directory of MIDI clips.

    llamatron
    llamatron examples/minimal_techno.yml
    llamatron examples/minimal_techno.yml --to ableton
    llamatron examples/minimal_techno.yml --to cliptree --out output/my_song

Without --to it opens the tracker, on the song if one is named.
"""

import argparse
import glob
import os
import sys

from llamatron.renderers.ableton_project import DEFAULT_TEMPLATE, AbletonProject
from llamatron.renderers.clip_tree import ClipTree
from llamatron.song import ClipGrid
from llamatron.song_file import SongFileError, load_song


def _arguments(argv):
    parser = argparse.ArgumentParser(
        prog='llamatron',
        description='Open the tracker, or with --to, turn a song file into Ableton Live or MIDI files.')
    parser.add_argument('song', nargs='?', help='the song file to open, or to read with --to')
    parser.add_argument('--to', choices=['ableton', 'cliptree'], help='write the song instead of opening the tracker')
    parser.add_argument('--out', help='the directory to write to (default: output/<song name>)')
    parser.add_argument('--template', help='the Live set to build from (default: the one installed with llamatron)')
    parser.add_argument('--replace', action='store_true', help='replace this song\'s earlier output, so you can regenerate and listen')
    arguments = parser.parse_args(argv)
    if arguments.to is None:
        given = [option for option, value in [('--out', arguments.out), ('--template', arguments.template), ('--replace', arguments.replace)] if value]
        if given:
            parser.error(f"{', '.join(given)} only works with --to")
    elif arguments.song is None:
        parser.error('--to needs a song file')
    return arguments


def replace_output(to, directory):
    """Remove what rendering a song to a directory would write, and leave everything else."""
    if to == 'ableton':
        targets = [AbletonProject(directory, ClipGrid()).path]
    else:
        targets = glob.glob(os.path.join(glob.escape(directory), '[0-9]*-[0-9]*.mid'))
    for path in targets:
        if os.path.exists(path):
            os.remove(path)


def main(argv=None):
    """Return 0 if the tracker closed or the song was written, or 1 after explaining what went wrong."""
    arguments = _arguments(argv)
    if arguments.to is None:
        # Imported here so that rendering doesn't need to load the text UI.
        from llamatron.tui.app import main as open_tracker
        return open_tracker([arguments.song] if arguments.song else [])
    name = os.path.splitext(os.path.basename(arguments.song))[0]
    directory = arguments.out or os.path.join('output', name)
    try:
        song = load_song(arguments.song)
        if arguments.replace:
            replace_output(arguments.to, directory)
        if arguments.to == 'ableton':
            AbletonProject(directory, song, template=arguments.template or DEFAULT_TEMPLATE).render()
        else:
            ClipTree(directory, song).render()
    except (SongFileError, ValueError, OSError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1
    print(f'wrote {arguments.to} output to {directory}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
