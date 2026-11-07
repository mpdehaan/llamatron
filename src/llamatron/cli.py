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

"""Opens the tracker, or turns a song file into an Ableton Live set or MIDI files.

    llamatron
    llamatron examples/minimal_techno.yml
    llamatron examples/minimal_techno.yml --to
    llamatron examples/minimal_techno.yml --to midi
    llamatron examples/minimal_techno.yml --to stems --out output/my_song

Without --to it opens the tracker, on the song if one is named. --to writes the song instead,
as a Live set unless it says which kind of output: midi (one file), stems (a file per track)
or cliptree (a file per clip).
"""

import argparse
import os
import sys

from llamatron.composition.song import Song
from llamatron.composition.song_file_error import SongFileError
from llamatron.playback.song_renderer import SongRenderer
from llamatron.renderers.outputs import OUTPUT_KINDS, OutputKind, make_writer, replace_output

PROGRAM = 'llamatron'
# What --to writes when it doesn't say.
DEFAULT_KIND = OutputKind.ABLETON
# Where a song's output goes unless --out says otherwise: output/<song name>.
OUTPUT_DIRECTORY = 'output'
OPTION_TO = '--to'
OPTION_OUT = '--out'
OPTION_TEMPLATE = '--template'
OPTION_REPLACE = '--replace'
SONG_ARGUMENT = 'song'
ONE_OR_NONE = '?'
STORE_TRUE = 'store_true'
SUCCEEDED, FAILED = 0, 1

HELP_DESCRIPTION = 'Open the tracker, or with --to, turn a song file into an Ableton Live set or MIDI files.'
HELP_SONG = 'the song file to open, or to read with --to'
HELP_TO = (
    'write the song instead of opening the tracker, as an Ableton Live set (ableton, the default), '
    'one MIDI file of every track (midi), a MIDI file per track (stems) or a MIDI file per clip (cliptree)'
)
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
    parser.add_argument(OPTION_TO, nargs=ONE_OR_NONE, const=DEFAULT_KIND, choices=OUTPUT_KINDS, help=HELP_TO)
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
        make_writer(arguments.to, directory, song, template=arguments.template).render()
    except (SongFileError, ValueError, OSError) as error:
        print(MSG_ERROR.format(problem=error), file=sys.stderr)
        return FAILED
    print(MSG_WROTE.format(target=arguments.to, directory=directory))
    return SUCCEEDED


if __name__ == '__main__':
    sys.exit(main())
