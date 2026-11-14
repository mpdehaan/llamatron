#!/usr/bin/env python3
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
"""Export every example as one MIDI file each, made for listening in a plain MIDI player.

Run it from the top folder (sh user_scripts/demos_to_midi.sh):

    .venv/bin/python internal_tools/preview_midi.py              # every set in examples/ into previews/
    .venv/bin/python internal_tools/preview_midi.py some.yml     # only the sets named

Each song is written as the General MIDI export writes it (--to gm): a track per llamatron track,
each on a channel of its own, a drum track on channel 10, which General MIDI players play as drums,
and each track's instrument's General MIDI sound sent first, so that a player with no DAW behind it
plays every part on a sound chosen for it. sh user_scripts/demos_to_wavs.sh makes WAV files of them with
FluidSynth, and sh user_scripts/play_demo.sh picks one to play in the terminal on a Mac.

Beside the files it writes DEMOS.md, a table of every set previewed: its name, what it plays (its
description), how long it plays, and the features it uses (internal_tools/demo_features.py), to review the
demos while listening.
"""

import argparse
import glob
import os
import sys
import tempfile

import importlib.util

from llamatron.composition.setlist import Setlist
from llamatron.exporters.midi_arrangement import MidiGeneralMidi
from llamatron.exporters.midi_messages import safe_file_name
from llamatron.playback.song_renderer import SongRenderer
from llamatron.tui.document import Document
from llamatron.tui.text import clock

EXAMPLES = os.path.join('examples', '*.yml')
PREVIEWS = 'previews'
SET_SUFFIX = '.yml'
NAME_JOIN = '{set}_{song}'
# Each preview is named after the set and the song, as the plain MIDI export names its file, or after
# the set alone when the song has the set's name, as every demo's one song has, a space in the song's
# name counting as the underscore a file name holds, so that the song minimal techno of
# minimal_techno.yml is previews/minimal_techno.mid.
PREVIEW_FILE = '{name}.mid'
WROTE = 'wrote {path}'
FEATURES_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'demo_features.py')
FEATURES_MODULE = 'demo_features'
REVIEW_FILE = 'DEMOS.md'
REVIEW_LINES = [
    '# The examples, for review', '',
    'Every set previewed here, with its genre, what it plays, how long it plays and the features it uses. Made by sh user_scripts/demos_to_midi.sh. sh user_scripts/demos_to_wavs.sh makes WAV files of them, and sh user_scripts/play_demo.sh picks one to play in the terminal on a Mac.', '',
    '| set | genre | plays | length | features |', '| --- | --- | --- | ---: | --- |',
]
REVIEW_ROW = '| {set} | {genre} | {plays} | {length} | {features} |'
# Between a set's songs' genres, when they differ.
GENRE_JOIN = ', '
FEATURE_JOIN = ', '
LINE_BREAK = '\n'
NO_DESCRIPTION = ''
UNKNOWN_LENGTH = '?'
DONE = 'every example is in {folder}/, one General MIDI file each: drums on channel 10, every other track on a channel of its own with its sound'


def preview_name(*, stem, song):
    """Return what a song's preview is called: the set's name when the song has it, and otherwise the set's and the song's, with no spaces."""
    song_in_file = safe_file_name(song)
    return stem if song_in_file == stem else NAME_JOIN.format(set=stem, song=song_in_file)


def preview(*, path, folder):
    """Write a preview MIDI file of every song of a set into folder, and return their paths."""
    setlist = Setlist.read_file(path)
    stem = os.path.basename(path).removesuffix(SET_SUFFIX)
    written = []
    for name in setlist.get_song_names():
        named = preview_name(stem=stem, song=name)
        with tempfile.TemporaryDirectory() as scratch:
            exporter = MidiGeneralMidi(directory=scratch, grid=SongRenderer(setlist.get_song(name)).render(), name=named)
            exporter.export()
            target = os.path.join(folder, PREVIEW_FILE.format(name=named))
            os.replace(exporter.path(), target)
        written.append(target)
    return written


def load_features():
    """Load internal_tools/demo_features.py, which knows what features a set uses, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(FEATURES_MODULE, FEATURES_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def review_row(*, path, features):
    """Return one set's line of the review table: its name, what it plays, its length and its features in the report's order."""
    document = Document.load(path)
    seconds = document.lengths().song_seconds()
    used = features.features_used(path)
    named = [name for name, _ in features.FEATURES if name in used]
    return REVIEW_ROW.format(
        set=features.short_name(path), genre=GENRE_JOIN.join(document.setlist().get_genres()), plays=document.setlist().get_description() or NO_DESCRIPTION,
        length=UNKNOWN_LENGTH if seconds is None else clock(seconds), features=FEATURE_JOIN.join(named),
    )


def write_review(*, paths, folder):
    """Write the review table of the sets into the folder, and return its path."""
    features = load_features()
    lines = [*REVIEW_LINES, *[review_row(path=path, features=features) for path in paths]]
    target = os.path.join(folder, REVIEW_FILE)
    with open(target, 'w', encoding='utf-8') as file:
        file.write(LINE_BREAK.join(lines) + LINE_BREAK)
    return target


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('paths', nargs='*', help='the sets to preview; with none, every set in examples/')
    parser.add_argument('--out', default=PREVIEWS, help='the directory to write to')
    arguments = parser.parse_args(argv)
    os.makedirs(arguments.out, exist_ok=True)
    paths = arguments.paths or sorted(glob.glob(EXAMPLES))
    for path in paths:
        for written in preview(path=path, folder=arguments.out):
            print(WROTE.format(path=written))
    print(WROTE.format(path=write_review(paths=paths, folder=arguments.out)))
    print(DONE.format(folder=arguments.out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
