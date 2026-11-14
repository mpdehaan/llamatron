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
"""The Inversion row: how many of a step's chord's lowest notes move up an octave, the user's design of 2026-11-11."""

import unittest

from llamatron.composition.file_format import Row, Section
from llamatron.composition.song_file_error import SongFileError
from rendering import setlist_from_data
from test_registers import one_clip, pitches

TRIAD = '3'
SEVENTH = '7'
MAJOR_SEVENTH = 'M7'
# C major's triad on C, in octave 5: C, E and G.
C = 60
E = 64
G = 67
B = 71
OCTAVE = 12


def chord(*, symbol, inversion=None):
    """Return the MIDI numbers the one step plays: degree 1 in C major, with a chord and an inversion."""
    rows = {Row.CHORD: [symbol]}
    if inversion is not None:
        rows[Row.INVERSION] = [inversion]
    return sorted(pitches(one_clip(rows=rows)))


class TestPlaying(unittest.TestCase):

    def test_root_position(self):
        self.assertEqual(chord(symbol=TRIAD), [C, E, G])

    def test_first_and_second_inversions(self):
        self.assertEqual(chord(symbol=TRIAD, inversion=1), [E, G, C + OCTAVE])
        self.assertEqual(chord(symbol=TRIAD, inversion=2), [G, C + OCTAVE, E + OCTAVE])

    def test_a_third_inversion_on_a_triad_plays_as_its_second(self):
        self.assertEqual(chord(symbol=TRIAD, inversion=3), chord(symbol=TRIAD, inversion=2))

    def test_a_seventh_chord_has_a_third_inversion(self):
        self.assertEqual(chord(symbol=SEVENTH, inversion=3), [B, C + OCTAVE, E + OCTAVE, G + OCTAVE])

    def test_a_named_chord_inverts_too(self):
        self.assertEqual(chord(symbol=MAJOR_SEVENTH, inversion=1), [E, G, B, C + OCTAVE])

    def test_a_single_note_ignores_it(self):
        self.assertEqual(sorted(pitches(one_clip(rows={Row.INVERSION: [2]}))), [C])


class TestWhatAFileHolds(unittest.TestCase):

    def test_an_inversion_past_three_is_refused(self):
        with self.assertRaises(SongFileError):
            setlist_from_data(one_clip(rows={Row.CHORD: [TRIAD], Row.INVERSION: [4]}))

    def test_a_drum_pattern_holds_none(self):
        data = one_clip(rows={Row.INVERSION: [1]}, drum=True)
        with self.assertRaises(SongFileError):
            setlist_from_data(data)

    def test_it_is_written_back(self):
        setlist = setlist_from_data(one_clip(rows={Row.CHORD: [TRIAD], Row.INVERSION: [2]}))
        pattern = next(iter(setlist.to_data()[Section.PATTERNS].values()))
        self.assertEqual(pattern[Row.INVERSION], [2])


class TestGhosts(unittest.TestCase):
    """The piano roll draws a chord's other notes where the inversion plays them."""

    OCTAVE_NUMBER = 5

    def pattern(self, inversion):
        setlist = setlist_from_data(one_clip(rows={Row.CHORD: [TRIAD], Row.INVERSION: [inversion]}))
        return setlist.get_pattern(setlist.get_pattern_names()[0])

    def test_the_root_goes_up_an_octave_as_a_ghost(self):
        tones = self.pattern(1).chord_tones(step=0, octave=self.OCTAVE_NUMBER, scale=None)
        self.assertEqual(sorted(tones), [(1, self.OCTAVE_NUMBER + 1, None), (3, self.OCTAVE_NUMBER, None), (5, self.OCTAVE_NUMBER, None)])

    def test_a_second_inversion_lifts_the_third_too(self):
        tones = self.pattern(2).chord_tones(step=0, octave=self.OCTAVE_NUMBER, scale=None)
        self.assertEqual(sorted(tones), [(1, self.OCTAVE_NUMBER + 1, None), (3, self.OCTAVE_NUMBER + 1, None), (5, self.OCTAVE_NUMBER, None)])

