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

from llamatron.composition.song import Song
from llamatron.composition.song_file_error import SongFileError
from llamatron.playback.song_renderer import SongRenderer
from llamatron.renderers.ableton_project import DEFAULT_TEMPLATE, AbletonProject
from llamatron.renderers.clip_tree import ClipTree
from llamatron.clip_grid import ClipGrid

PROGRAM = 'llamatron'
# What --to can write.
TO_ABLETON, TO_CLIP_TREE = 'ableton', 'cliptree'
RENDER_TARGETS = [TO_ABLETON, TO_CLIP_TREE]
# Where a song's output goes unless --out says otherwise: output/<song name>.
OUTPUT_DIRECTORY = 'output'
# The MIDI files a clip tree writes, which --replace removes: <scene>-<track>-<name>.mid.
CLIP_TREE_FILES = '[0-9]*-[0-9]*.mid'
OPTION_TO, OPTION_OUT, OPTION_TEMPLATE, OPTION_REPLACE = '--to', '--out', '--template', '--replace'
SONG_ARGUMENT = 'song'
ONE_OR_NONE = '?'
STORE_TRUE = 'store_true'
SUCCEEDED, FAILED = 0, 1

HELP_DESCRIPTION = 'Open the tracker, or with --to, turn a song file into Ableton Live or MIDI files.'
HELP_SONG = 'the song file to open, or to read with --to'
HELP_TO = 'write the song instead of opening the tracker'
HELP_OUT = 'the directory to write to (default: output/<song name>)'
HELP_TEMPLATE = 'the Live set to build from (default: the one installed with llamatron)'
HELP_REPLACE = "replace this song's earlier output, so you can regenerate and listen"
MSG_ONLY_WITH_TO = '{options} only works with --to'
MSG_TO_NEEDS_SONG = '--to needs a song file'
MSG_ERROR = 'error: {problem}'
MSG_WROTE = 'wrote {target} output to {directory}'
# Options, as the message about them lists them.
OPTION_SEPARATOR = ', '


def _arguments(argv):
    parser = argparse.ArgumentParser(prog=PROGRAM, description=HELP_DESCRIPTION)
    parser.add_argument(SONG_ARGUMENT, nargs=ONE_OR_NONE, help=HELP_SONG)
    parser.add_argument(OPTION_TO, choices=RENDER_TARGETS, help=HELP_TO)
    parser.add_argument(OPTION_OUT, help=HELP_OUT)
    parser.add_argument(OPTION_TEMPLATE, help=HELP_TEMPLATE)
    parser.add_argument(OPTION_REPLACE, action=STORE_TRUE, help=HELP_REPLACE)
    arguments = parser.parse_args(argv)
    if arguments.to is None:
        given = _render_options_given(arguments)
        if given:
            parser.error(MSG_ONLY_WITH_TO.format(options=OPTION_SEPARATOR.join(given)))
    elif arguments.song is None:
        parser.error(MSG_TO_NEEDS_SONG)
    return arguments


def _render_options_given(arguments):
    """Return the options given that only mean something when rendering with --to."""
    options = [(OPTION_OUT, arguments.out), (OPTION_TEMPLATE, arguments.template), (OPTION_REPLACE, arguments.replace)]
    return [option for option, value in options if value]


def replace_output(to, directory):
    """Remove what rendering a song to a directory would write, and leave everything else."""
    if to == TO_ABLETON:
        targets = [AbletonProject(directory, ClipGrid()).path]
    else:
        targets = glob.glob(os.path.join(glob.escape(directory), CLIP_TREE_FILES))
    for path in targets:
        if os.path.exists(path):
            os.remove(path)


def output_directory(song_path):
    """Return where a song's output goes unless --out says otherwise: output/<song name>."""
    name = os.path.splitext(os.path.basename(song_path))[0]
    return os.path.join(OUTPUT_DIRECTORY, name)


def main(argv=None):
    """Return 0 if the tracker closed or the song was written, or 1 after explaining what went wrong."""
    arguments = _arguments(argv)
    if arguments.to is None:
        # Imported here so that rendering doesn't need to load the text UI.
        from llamatron.tui.app import main as open_tracker
        return open_tracker([arguments.song] if arguments.song else [])
    directory = arguments.out or output_directory(arguments.song)
    try:
        song = SongRenderer(Song.read_file(arguments.song)).render()
        if arguments.replace:
            replace_output(arguments.to, directory)
        if arguments.to == TO_ABLETON:
            AbletonProject(directory, song, template=arguments.template or DEFAULT_TEMPLATE).render()
        else:
            ClipTree(directory, song).render()
    except (SongFileError, ValueError, OSError) as error:
        print(MSG_ERROR.format(problem=error), file=sys.stderr)
        return FAILED
    print(MSG_WROTE.format(target=arguments.to, directory=directory))
    return SUCCEEDED


if __name__ == '__main__':
    sys.exit(main())
