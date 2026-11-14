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

"""Import every sample MIDI file into a new set and report what it made and whether it plays back the same, the proof the user asked for on 2026-11-10.

    .venv/bin/python internal_tools/import_check.py                     # the MIDI files in examples/midi/, then every example set
    .venv/bin/python internal_tools/import_check.py some.mid other.mid  # only the MIDI files named
    .venv/bin/python internal_tools/import_check.py --longest 64        # with another Longest pattern, as the import dialog offers
    internal_tools/test_all_sample_midi_against_import.sh

Each file is imported as the import dialog would with its defaults, into a new set, so nothing
the project holds affects it. Each example set is first exported as one MIDI file in memory, its
first song with a fixed seed, and that file imported. The report gives each file's tracks,
patterns and scenes, and then whether the song, played and exported again, plays the same notes
at the same tempos, and the CCs it brought in at the same values, as the file: "same", or what differs and what the import said had to change.
Nothing is written. It exits with a failure only when something differs that the import didn't
warn about, since that would be the import's own mistake.
"""

import argparse
import glob
import os
import sys

import mido

from llamatron.composition.setlist import Setlist
from llamatron.exporters.midi_arrangement import MidiSong
from llamatron.importers.comparison import round_trip
from llamatron.importers.midi_import import DEFAULT_LONGEST_PATTERN, LONGEST_PATTERN_CHOICES, ImportChoices
from llamatron.playback.song_renderer import SongRenderer

MIDI_FILES = os.path.join('examples', 'midi', '*.mid')
EXAMPLE_SETS = os.path.join('examples', '*.yml')
SEED = 1
FAILED = 1
HEADING = '{file:<34} {tracks:>6} {patterns:>8} {scenes:>6}  {result}'
COLUMNS = {'file': 'file', 'tracks': 'tracks', 'patterns': 'patterns', 'scenes': 'scenes', 'result': 'plays back'}
SECTION_MIDI = 'MIDI files ({longest} steps at most a pattern):'
SECTION_SETS = 'Example sets, exported as MIDI and imported again:'
SAME = 'same'
DIFFERS = 'differs: {missing} of {notes} notes not played as the file plays them, {tempos} tempo changes'
WARNING = '{indent}warned: {warning}'
NOT_WARNED = '{indent}NOT WARNED: the import said nothing would change'
LONG = '{indent}{count} patterns longer than {longest} steps, where no clean split was near'
CONTROLS_EXACT = '{indent}CC values: {count} lanes, every value as the file has it at every moment'
CONTROLS_NEAR = '{indent}CC values: {count} lanes, within {largest} of the file, off for at most {longest} of a whole note at a time'
INDENT = '    '
# What each file's result is counted as.
SAME_RESULT = 'same'
WARNED = 'warned'
UNWARNED = 'unwarned'
TOTAL = '{same} of {count} play back the same; {warned} differ with a warning; {unwarned} differ without one'


def report(*, name, midi_file, longest):
    """Print one file's line and what came with it, and return SAME_RESULT, WARNED or UNWARNED."""
    trip = round_trip(midi_file=midi_file, choices=ImportChoices(song_name=os.path.splitext(os.path.basename(name))[0], longest_pattern=longest))
    imported = trip.imported
    comparison = trip.comparison
    result = SAME if comparison.is_same() else DIFFERS.format(
        missing=len(comparison.missing), notes=comparison.notes, tempos=len(comparison.tempos_missing) + len(comparison.tempos_extra),
    )
    print(HEADING.format(file=name, tracks=imported.tracks, patterns=imported.patterns, scenes=imported.scenes, result=result))
    difference = comparison.largest_control_difference()
    if difference is not None:
        largest, off_for = difference
        if largest:
            print(CONTROLS_NEAR.format(indent=INDENT, count=len(comparison.controls), largest=largest, longest=off_for))
        else:
            print(CONTROLS_EXACT.format(indent=INDENT, count=len(comparison.controls)))
    if imported.long_patterns:
        print(LONG.format(indent=INDENT, count=imported.long_patterns, longest=longest))
    for warning in imported.warnings:
        print(WARNING.format(indent=INDENT, warning=warning))
    if comparison.is_same():
        return SAME_RESULT
    if not imported.warnings:
        print(NOT_WARNED.format(indent=INDENT))
        return UNWARNED
    return WARNED


def exported(path):
    """Return an example set's first song exported as one MIDI file in memory, with the fixed seed."""
    setlist = Setlist.read_file(path)
    name = setlist.first_song_name()
    return MidiSong(directory=os.curdir, grid=SongRenderer(setlist.get_song(name), seed=SEED).render(), name=name).midi_file()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('files', nargs='*', help='MIDI files to import, or every one in examples/midi/ and every example set')
    parser.add_argument('--longest', type=int, choices=LONGEST_PATTERN_CHOICES, default=DEFAULT_LONGEST_PATTERN, help='the longest pattern, in steps')
    arguments = parser.parse_args()
    results = []
    print(SECTION_MIDI.format(longest=arguments.longest))
    print(HEADING.format(**COLUMNS))
    for path in arguments.files or sorted(glob.glob(MIDI_FILES)):
        results.append(report(name=os.path.basename(path), midi_file=mido.MidiFile(path), longest=arguments.longest))
    if not arguments.files:
        print()
        print(SECTION_SETS)
        print(HEADING.format(**COLUMNS))
        for path in sorted(glob.glob(EXAMPLE_SETS)):
            results.append(report(name=os.path.basename(path), midi_file=exported(path), longest=arguments.longest))
    print()
    print(TOTAL.format(same=results.count(SAME_RESULT), count=len(results), warned=results.count(WARNED), unwarned=results.count(UNWARNED)))
    return FAILED if UNWARNED in results else 0


if __name__ == '__main__':
    sys.exit(main())
