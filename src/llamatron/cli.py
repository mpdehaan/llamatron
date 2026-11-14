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

"""Opens the tracker, or turns the songs of a set file into Ableton Live sets or MIDI files.

    llamatron
    llamatron examples/by_genre/electronic/minimal_techno.yml
    llamatron examples/by_genre/electronic/minimal_techno.yml --to
    llamatron examples/by_genre/electronic/minimal_techno.yml --to midi
    llamatron examples/by_genre/electronic/minimal_techno.yml --to stems --out exports
    llamatron examples/by_genre/electronic/minimal_techno.yml --to --song intro --seed 1

Without --to it opens the tracker, on the set if one is named. --to writes every song of the
set instead, or the one --song names, as files beside the set's file named <set>_<song>, like
examples/minimal_techno_minimal_techno.als, or in the directory --out names, as a Live set unless
--to says which kind of export: midi (one file), stems (a file per track), cliptree (a file per
clip) or gm (one General MIDI file, drums on channel 10 and each track's instrument's sound). --seed exports with that seed in place of each song's, so that an
export can be repeated exactly, which the tests and internal_tools/compare_exports.py rely on.

A set file that holds values that can't be used, each with an allowed value near it, like a
velocity of 200, isn't exported: every such value is listed with the value that would take its
place, and the command fails. --force exports with those values in their place and lists what
it changed. The set file is never changed. Opening the tracker on such a file asks in a dialog.
"""

import argparse
import os
import sys

from llamatron.composition.setlist import Setlist, file_stem
from llamatron.composition.song_file_error import SongFileError
from llamatron.playback.song_renderer import SongRenderer
from llamatron.exporters.exports import EXPORT_KINDS_IN_HELP, ExportKind, export_name, make_exporter, shown_export_path, remove_earlier_export
from llamatron.strings.errors import ERR_BATCH_VIDEO_NEEDS_VISUALIZER, ERR_LAUNCH_NEEDS_SET, ERR_NEEDS_FORCE, ERR_NOT_WITH_TO, ERR_ONLY_WITH_TO, ERR_PRINTED, ERR_TO_NEEDS_SET
from llamatron.visualizers.modes import mode_options
from llamatron.tui.launch import Launch, start_screen_wanted
from llamatron.strings.cli import (
    MSG_CLI_CHANGED, MSG_CLI_WOULD_CHANGE, MSG_CLI_WROTE, MSG_HELP_AUTOPLAY, MSG_HELP_AUTOPLAY_QUIT, MSG_HELP_DESCRIPTION, MSG_HELP_FORCE,
    MSG_HELP_BATCH_VIDEO, MSG_HELP_NO_ALTERNATE, MSG_HELP_FOR_RECORDING, MSG_HELP_MAX_SECONDS, MSG_HELP_VISUALIZER, MSG_HELP_OUT, MSG_HELP_REPLACE, MSG_HELP_SEED, MSG_HELP_SET, MSG_HELP_SONG, MSG_HELP_TEMPLATE, MSG_HELP_TO,
)

PROGRAM = 'llamatron'
# What --to writes when it doesn't say.
DEFAULT_KIND = ExportKind.ABLETON
# The options that say what to export and where.
OPTION_TO = '--to'
OPTION_OUT = '--out'
OPTION_TEMPLATE = '--template'
OPTION_REPLACE = '--replace'
OPTION_SEED = '--seed'
OPTION_SONG = '--song'
OPTION_FORCE = '--force'
OPTION_AUTOPLAY = '--autoplay'
OPTION_AUTOPLAY_QUIT = '--autoplay-quit-when-finished'
OPTION_FOR_RECORDING = '--launch-for-recording'
OPTION_MAX_SECONDS = '--max-seconds'
OPTION_VISUALIZER = '--visualizer'
OPTION_BATCH_VIDEO = '--batch-video'
OPTION_NO_ALTERNATE = '--no-alternate'
SET_ARGUMENT = 'set'
ONE_OR_NONE = '?'
STORE_TRUE = 'store_true'
SUCCEEDED = 0
FAILED = 1

# Options, as the message about them lists them.
OPTION_SEPARATOR = ', '


def _arguments(argv):
    parser = argparse.ArgumentParser(prog=PROGRAM, description=MSG_HELP_DESCRIPTION)
    parser.add_argument(SET_ARGUMENT, nargs=ONE_OR_NONE, help=MSG_HELP_SET)
    parser.add_argument(OPTION_TO, nargs=ONE_OR_NONE, const=DEFAULT_KIND, choices=EXPORT_KINDS_IN_HELP, help=MSG_HELP_TO)
    parser.add_argument(OPTION_OUT, help=MSG_HELP_OUT)
    parser.add_argument(OPTION_TEMPLATE, help=MSG_HELP_TEMPLATE)
    parser.add_argument(OPTION_REPLACE, action=STORE_TRUE, help=MSG_HELP_REPLACE)
    parser.add_argument(OPTION_SEED, type=int, help=MSG_HELP_SEED)
    parser.add_argument(OPTION_SONG, help=MSG_HELP_SONG)
    parser.add_argument(OPTION_FORCE, action=STORE_TRUE, help=MSG_HELP_FORCE)
    parser.add_argument(OPTION_AUTOPLAY, action=STORE_TRUE, help=MSG_HELP_AUTOPLAY)
    parser.add_argument(OPTION_AUTOPLAY_QUIT, action=STORE_TRUE, help=MSG_HELP_AUTOPLAY_QUIT)
    parser.add_argument(OPTION_FOR_RECORDING, action=STORE_TRUE, help=MSG_HELP_FOR_RECORDING)
    parser.add_argument(OPTION_MAX_SECONDS, type=float, help=MSG_HELP_MAX_SECONDS)
    parser.add_argument(OPTION_VISUALIZER, choices=mode_options(), help=MSG_HELP_VISUALIZER)
    parser.add_argument(OPTION_BATCH_VIDEO, action=STORE_TRUE, help=MSG_HELP_BATCH_VIDEO)
    parser.add_argument(OPTION_NO_ALTERNATE, action=STORE_TRUE, help=MSG_HELP_NO_ALTERNATE)
    arguments = parser.parse_args(argv)
    if arguments.to is None:
        given = _render_options_given(arguments)
        if given:
            parser.error(ERR_ONLY_WITH_TO.format(options=OPTION_SEPARATOR.join(given)))
        if launch_of(arguments).needs_set() and arguments.set is None:
            parser.error(ERR_LAUNCH_NEEDS_SET)
        if arguments.batch_video and arguments.visualizer is None:
            parser.error(ERR_BATCH_VIDEO_NEEDS_VISUALIZER)
    elif arguments.set is None:
        parser.error(ERR_TO_NEEDS_SET)
    else:
        given = _launch_options_given(arguments)
        if given:
            parser.error(ERR_NOT_WITH_TO.format(options=OPTION_SEPARATOR.join(given)))
    return arguments


def launch_of(arguments):
    """Return what the tracker does on its own, by the launch options given."""
    return Launch(autoplay=arguments.autoplay, quit_when_finished=arguments.autoplay_quit_when_finished, for_recording=arguments.launch_for_recording,
                  max_seconds=arguments.max_seconds, visualizer=arguments.visualizer, batch_video=arguments.batch_video, alternate=not arguments.no_alternate)


def _launch_options_given(arguments):
    """Return the options given that only mean something when opening the tracker."""
    options = [
        (OPTION_AUTOPLAY, arguments.autoplay), (OPTION_AUTOPLAY_QUIT, arguments.autoplay_quit_when_finished),
        (OPTION_FOR_RECORDING, arguments.launch_for_recording), (OPTION_MAX_SECONDS, arguments.max_seconds is not None),
        (OPTION_VISUALIZER, arguments.visualizer is not None), (OPTION_BATCH_VIDEO, arguments.batch_video), (OPTION_NO_ALTERNATE, arguments.no_alternate),
    ]
    return [option for option, given in options if given]


def _render_options_given(arguments):
    """Return the options given that only mean something when exporting with --to."""
    options = [
        (OPTION_OUT, arguments.out is not None), (OPTION_TEMPLATE, arguments.template is not None), (OPTION_REPLACE, arguments.replace),
        (OPTION_SEED, arguments.seed is not None), (OPTION_SONG, arguments.song is not None), (OPTION_FORCE, arguments.force),
    ]
    return [option for option, given in options if given]


def export_directory(set_path):
    """Return where a set's exports go unless --out says otherwise: beside the set's file, which is the current directory for a bare file name."""
    return os.path.dirname(set_path) or os.curdir


def read_set(*, path, force):
    """Return the set in a file, or raise SongFileError if it can't be exported as it is.

    A file that holds values that can't be used, each with an allowed value near it, is read
    with those values in their place, and every one is listed on stderr. Without --force that
    is all that happens, and the error says to pass it. The file is never changed.
    """
    try:
        return Setlist.read_file(path)
    except SongFileError as error:
        if error.get_correction() is None:
            raise
    setlist, corrections = Setlist.read_file_corrected(path)
    line = MSG_CLI_CHANGED if force else MSG_CLI_WOULD_CHANGE
    for correction in corrections:
        print(line.format(change=correction.described()), file=sys.stderr)
    if not force:
        raise SongFileError(ERR_NEEDS_FORCE.format(path=path))
    return setlist


def export_song(*, setlist, name, directory, arguments):
    """Write one song of a set into a directory as files named <set>_<song>, as the kind of export --to asks for."""
    files = export_name(setlist=file_stem(arguments.set), song=name)
    grid = SongRenderer(setlist.get_song(name), seed=arguments.seed).render()
    if arguments.replace:
        remove_earlier_export(kind=arguments.to, directory=directory, name=files)
    make_exporter(kind=arguments.to, directory=directory, name=files, grid=grid, template=arguments.template).export()
    print(MSG_CLI_WROTE.format(target=arguments.to, song=name, path=shown_export_path(kind=arguments.to, directory=directory, name=files)))


def main(*, argv=None):
    """Return 0 if the tracker closed or the song was written, or 1 after explaining what went wrong."""
    arguments = _arguments(argv)
    if arguments.to is None:
        # Imported here so that exporting doesn't need to load the text UI.
        from llamatron.tui.app import main as open_tracker
        return open_tracker(argv=[arguments.set] if arguments.set else [], launch=launch_of(arguments), start_screen=start_screen_wanted(os.environ))
    directory = arguments.out or export_directory(arguments.set)
    try:
        setlist = read_set(path=arguments.set, force=arguments.force)
        names = [arguments.song] if arguments.song is not None else setlist.get_song_names()
        for name in names:
            export_song(setlist=setlist, name=name, directory=directory, arguments=arguments)
    except (SongFileError, ValueError, OSError) as error:
        print(ERR_PRINTED.format(problem=error), file=sys.stderr)
        return FAILED
    return SUCCEEDED


if __name__ == '__main__':
    sys.exit(main())
