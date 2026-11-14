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

"""The cells taken from a band's MIDI file (internal_tools/analysis_and_generation/corpus/cells.py): a song written here note by
note comes back as the kit's, the bass's and the chord part's bars, the bass named by its chord, a shuffle found on a grid of
triplets, a waltz refused, and a lead whose pitches change nothing; and the report's arithmetic."""

import collections
import os
import sys
import tempfile
import unittest

import mido

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'internal_tools', 'analysis_and_generation')
sys.path.insert(0, TOOLS)
from corpus.cells import FIFTH, NO_KIT, NOT_COMMON_TIME, OPEN_CHORD, ROOT, STRAIGHT, TRIPLET, NotRead, cells_of, chord_of  # noqa: E402
import cell_report  # noqa: E402

TICKS = 480
BARS = 12
BEATS = 4
KICK = 36
SNARE = 38
HAT = 42
DRUMS = 9
BASS_CHANNEL = 1
CHORD_CHANNEL = 2
LEAD_CHANNEL = 3
FINGERED_BASS = 33
PIANO = 0
FLUTE = 73
C = 48
G = 55
C_MAJOR = (60, 64, 67)
LEAD_LOW = (72, 74, 76, 77)
LEAD_HIGH = (84, 79, 81, 88)
EIGHTH = 0.5
THIRD_OF_A_BEAT = 1 / 3
SIXTEENTHS = 16
TRIPLETS = 12
HALF_BAR = 8
WALTZ = 3
PITCH_CLASSES = 12
FIFTH_ABOVE = 7


def written(*, notes, programs, numerator=BEATS):
    """Write notes, each (channel, start in beats, length in beats, pitch), to a MIDI file and return its path."""
    events = [(0, mido.MetaMessage('time_signature', numerator=numerator, denominator=4))]
    events += [(0, mido.Message('program_change', channel=channel, program=program)) for channel, program in programs.items()]
    for channel, start, length, pitch in notes:
        events.append((round(start * TICKS), mido.Message('note_on', channel=channel, note=pitch, velocity=90)))
        events.append((round((start + length) * TICKS), mido.Message('note_off', channel=channel, note=pitch, velocity=0)))
    events.sort(key=lambda event: (event[0], event[1].type != 'note_off'))
    track = mido.MidiTrack()
    now = 0
    for tick, message in events:
        track.append(message.copy(time=tick - now))
        now = tick
    midi = mido.MidiFile(ticks_per_beat=TICKS)
    midi.tracks.append(track)
    handle, path = tempfile.mkstemp(suffix='.mid')
    os.close(handle)
    midi.save(path)
    return path


def hits(*, steps, grid=SIXTEENTHS):
    """Return a bar as the extractor writes one: an array, true at the steps named."""
    return tuple(step in steps for step in range(grid))


BACKBEAT = (hits(steps=(0, 8)), hits(steps=(4, 12)), hits(steps=range(0, SIXTEENTHS, 2)))
ROOT_AND_FIFTH = tuple(ROOT if step == 0 else FIFTH if step == HALF_BAR else None for step in range(SIXTEENTHS))
WHOLE_NOTE = hits(steps=(0,))
SHUFFLE_TIME = hits(steps=(0, 2, 3, 5, 6, 8, 9, 11), grid=TRIPLETS)


def kit_notes(*, hats):
    notes = []
    for bar in range(BARS):
        start = bar * BEATS
        notes += [(DRUMS, start, EIGHTH, KICK), (DRUMS, start + 2, EIGHTH, KICK), (DRUMS, start + 1, EIGHTH, SNARE), (DRUMS, start + 3, EIGHTH, SNARE)]
        notes += [(DRUMS, start + hat, EIGHTH / 2, HAT) for hat in hats]
    return notes


def band_notes(*, lead):
    """Return a band's notes: a backbeat, a bass on the root and the fifth, a held C major chord and a lead of four quarters."""
    notes = kit_notes(hats=[step * EIGHTH for step in range(BEATS * 2)])
    for bar in range(BARS):
        start = bar * BEATS
        notes += [(BASS_CHANNEL, start, 2, C), (BASS_CHANNEL, start + 2, 2, G)]
        notes += [(CHORD_CHANNEL, start, BEATS, pitch) for pitch in C_MAJOR]
        notes += [(LEAD_CHANNEL, start + beat, 1, pitch) for beat, pitch in enumerate(lead)]
    return notes


PROGRAMS = {BASS_CHANNEL: FINGERED_BASS, CHORD_CHANNEL: PIANO, LEAD_CHANNEL: FLUTE}


class TestCells(unittest.TestCase):
    """A song of known parts comes back as those parts."""

    def cells(self, **song):
        path = written(**song)
        self.addCleanup(os.remove, path)
        return cells_of(path)

    def test_a_band_comes_back_as_its_kit_its_bass_by_its_chord_and_its_chord_part(self):
        found = self.cells(notes=band_notes(lead=LEAD_LOW), programs=PROGRAMS)
        self.assertEqual(found['grid'], STRAIGHT)
        self.assertEqual(found['kit'], BACKBEAT)
        self.assertEqual(found['kit_share'], 1.0)
        self.assertEqual(found['bass'], ROOT_AND_FIFTH)
        self.assertEqual(found['chords'], WHOLE_NOTE)
        self.assertEqual(found['minor'], 0.0)
        self.assertEqual((found['bass_program'], found['chords_program'], found['lead_program']), (FINGERED_BASS, PIANO, FLUTE))
        self.assertEqual(found['lead_starts'], BEATS)

    def test_a_root_and_a_fifth_with_no_third_are_an_open_chord(self):
        weights = [0.0] * PITCH_CLASSES
        weights[0] = weights[FIFTH_ABOVE] = 4.0
        self.assertEqual(chord_of(weights), (0, OPEN_CHORD))

    def test_a_bar_is_drawn_for_reading_beat_by_beat(self):
        self.assertEqual(cell_report.drawn(ROOT_AND_FIFTH), 'r... .... f... ....')
        self.assertEqual(cell_report.drawn(BACKBEAT), 'x... .... x... .... | .... x... .... x... | x.x. x.x. x.x. x.x.')

    def test_a_leads_pitches_change_nothing(self):
        low = self.cells(notes=band_notes(lead=LEAD_LOW), programs=PROGRAMS)
        high = self.cells(notes=band_notes(lead=LEAD_HIGH), programs=PROGRAMS)
        self.assertEqual(low, high)

    def test_a_shuffle_is_found_on_a_grid_of_triplets(self):
        hats = [beat + part * THIRD_OF_A_BEAT for beat in range(BEATS) for part in (0, 2)]
        found = self.cells(notes=kit_notes(hats=hats), programs={})
        self.assertEqual(found['grid'], TRIPLET)
        self.assertEqual(found['time'], SHUFFLE_TIME)
        self.assertNotIn('bass', found)

    def test_a_waltz_and_a_song_with_no_kit_are_refused_with_why(self):
        for song, why in ((dict(notes=kit_notes(hats=[0]), programs={}, numerator=WALTZ), NOT_COMMON_TIME),
                          (dict(notes=[(BASS_CHANNEL, bar, 1, C) for bar in range(BARS * BEATS)], programs=PROGRAMS), NO_KIT)):
            with self.assertRaises(NotRead) as refused:
                self.cells(**song)
            self.assertEqual(str(refused.exception), why)


class TestCellReport(unittest.TestCase):
    """The report's arithmetic on small numbers."""

    def test_how_many_values_cover_a_share(self):
        counts = collections.Counter({'a': 6, 'b': 3, 'c': 1})
        self.assertEqual(cell_report.covering(counts=counts, share=0.5), 1)
        self.assertEqual(cell_report.covering(counts=counts, share=0.8), 2)
        self.assertEqual(cell_report.covering(counts=counts, share=1.0), 3)

    def test_groups_that_differ_explain_everything_and_groups_alike_nothing(self):
        self.assertEqual(cell_report.explained([[1.0, 1.0], [3.0, 3.0]]), 1.0)
        self.assertEqual(cell_report.explained([[1.0, 3.0], [1.0, 3.0]]), 0.0)

    def test_a_step_is_placed_in_its_bar(self):
        self.assertEqual([cell_report.place_of_step(step) for step in (0, 8, 4, 2, 1)], list(cell_report.PLACES))


if __name__ == '__main__':
    unittest.main()
