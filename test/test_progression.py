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
"""The Progression generator and what its chords are in a scale, the user's design of 2026-11-11.

Most tests play a one-bar figure of four quarter notes, C, E, G and A in C major, through a
progression a chord a bar, so that each bar shows where one chord moved the figure.
"""

import unittest

from llamatron.composition.file_format import (
    Accidental, ChordSymbol, ClipSlotSetting, GeneratorKind, NamedProgression, PatternSetting, Row, SceneSetting, Section, SongSetting, Tension,
)
from llamatron.composition.generator_settings import ProgressionSetting
from llamatron.composition.named_scale import NamedScale
from llamatron.composition.progressions import chord_name, named_progression_in, roman_numeral
from llamatron.composition.song_file_error import SongFileError
from llamatron.music.note import NoteName
from llamatron.support.rational import Rational
from rendering import setlist_from_data
from test_registers import LEAD, X, pattern, song
from test_shapes import notes

PROGRESSION = 'changes'
CHAIN = 'chords'
FIGURE = [1, 3, 5, 6]
STEPS = len(FIGURE)
BARS = 4
TRIAD = '3'
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
MAJOR = 'major'
MINOR = 'minor'


def through(progression, *, repeat=BARS, rows=None, drum=False, time_signature=None):
    """Return a song whose lead plays the figure, a quarter note a step, repeated, through a progression."""
    made = dict(pattern(STEPS, **{Row.DEGREE: list(FIGURE), **(rows or {})}), **{PatternSetting.STEP_SIZE: '1/4'})
    if drum:
        made.update({PatternSetting.DRUM: True, Row.DEGREE: [NoteName.C] * STEPS})
    data = song(patterns={X: made}, scenes=[{SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X, ClipSlotSetting.REPEAT: repeat, ClipSlotSetting.CHAINS: [CHAIN]}}}])
    data[Section.PROGRESSIONS] = {PROGRESSION: progression}
    data[Section.CHAINS] = {CHAIN: [{GeneratorKind.PROGRESSION: PROGRESSION}]}
    if time_signature:
        data[SongSetting.TIME_SIGNATURE] = time_signature
    return data


def bars(data, *, per_bar=STEPS):
    """Return the note names the lead plays, a list a bar."""
    played = [NAMES[pitch % len(NAMES)] for _, _, pitch, _ in notes(data)]
    return [played[place:place + per_bar] for place in range(0, len(played), per_bar)]


class TestMoving(unittest.TestCase):

    def test_a_new_progression_moves_nothing(self):
        self.assertEqual(bars(through({ProgressionSetting.CHORDS: [1]})), [['C', 'E', 'G', 'A']] * BARS)

    def test_plain_degrees_move_the_figure_along_the_scale(self):
        self.assertEqual(bars(through({ProgressionSetting.CHORDS: [1, 5, 6, 4]})), [['C', 'E', 'G', 'A'], ['G', 'B', 'D', 'E'], ['A', 'C', 'E', 'F'], ['F', 'A', 'C', 'D']])

    def test_a_flat_moves_by_exact_half_steps_keeping_the_figures_sound(self):
        played = bars(through({ProgressionSetting.CHORDS: [1, 7, 4, 1], ProgressionSetting.ACCIDENTALS: [None, Accidental.FLAT, None, None]}))
        self.assertEqual(played[1], ['A#', 'D', 'F', 'G'])

    def test_it_loops_and_starts_again_with_each_clip(self):
        self.assertEqual(bars(through({ProgressionSetting.CHORDS: [1, 5]})), [['C', 'E', 'G', 'A'], ['G', 'B', 'D', 'E']] * 2)

    def test_every_sets_how_long_each_chord_lasts(self):
        played = bars(through({ProgressionSetting.CHORDS: [1, 5], ProgressionSetting.EVERY: '1/2'}))
        self.assertEqual(played[0], ['C', 'E', 'D', 'E'])

    def test_every_in_bars_follows_the_time_signature(self):
        data = through({ProgressionSetting.CHORDS: [1, 5], ProgressionSetting.EVERY: '1 bar'}, time_signature='3/4')
        played = [NAMES[pitch % len(NAMES)] for _, _, pitch, _ in notes(data)]
        # A bar of 3/4 is three of the figure's quarter notes, so the fourth note plays under the second chord.
        self.assertEqual(played[:STEPS], ['C', 'E', 'G', 'E'])

    def test_a_chord_moves_whole_and_its_inversion_lifts_its_lowest_notes(self):
        rows = {Row.CHORD: [TRIAD, None, None, None]}
        plain = notes(through({ProgressionSetting.CHORDS: [1]}, rows=rows, repeat=1))
        inverted = notes(through({ProgressionSetting.CHORDS: [1], ProgressionSetting.INVERSIONS: [1]}, rows=rows, repeat=1))
        lowest = min(pitch for start, _, pitch, _ in plain if start == 0)
        self.assertNotIn(lowest, [pitch for start, _, pitch, _ in inverted if start == 0])
        self.assertIn(lowest + 12, [pitch for start, _, pitch, _ in inverted if start == 0])

    def test_a_drum_pattern_is_left_alone(self):
        played = bars(through({ProgressionSetting.CHORDS: [1, 5, 6, 4]}, drum=True))
        self.assertEqual({tuple(bar) for bar in played}, {('C', 'C', 'C', 'C')})

    def test_the_rhythm_stays_as_written(self):
        moved = notes(through({ProgressionSetting.CHORDS: [1, 5, 6, 4]}))
        written = notes(through({ProgressionSetting.CHORDS: [1]}))
        self.assertEqual([(start, length) for start, length, _, _ in moved], [(start, length) for start, length, _, _ in written])
        self.assertEqual(moved[STEPS][0], Rational(1))



class TestLeavingTheScale(unittest.TestCase):
    """A chord's scale, quality and tensions (the user's design): the figure is 1 3 5 7 of C major, C E G B."""

    SEVENTH_FIGURE = {Row.DEGREE: [1, 3, 5, 7]}
    SCALE_FIGURE = {Row.DEGREE: [1, 2, 4, 6]}
    THIRTEENTH_FLAT_NINE = ['G', 'B', 'D', 'F', 'G#', 'E']

    def played(self, progression, *, rows=None):
        return bars(through(progression, repeat=len(progression[ProgressionSetting.CHORDS]), rows=rows or self.SEVENTH_FIGURE))

    def test_a_quality_sets_the_third_the_fifth_and_the_seventh(self):
        # III as the scale builds it is E minor seventh; named major it is E major, and named dom7 the seventh stays D.
        progression = {ProgressionSetting.CHORDS: [3, 3, 3], ProgressionSetting.QUALITIES: [None, ChordSymbol.MAJOR7, ChordSymbol.HALF_DIMINISHED7]}
        self.assertEqual(self.played(progression), [['E', 'G', 'B', 'D'], ['E', 'G#', 'B', 'D#'], ['E', 'G', 'A#', 'D']])

    def test_a_triad_quality_leaves_the_seventh_to_the_scale(self):
        progression = {ProgressionSetting.CHORDS: [2], ProgressionSetting.QUALITIES: [ChordSymbol.MAJOR]}
        self.assertEqual(self.played(progression), [['D', 'F#', 'A', 'C']])

    def test_a_scale_borrows_the_chord_and_its_passing_notes(self):
        # VI of C major is A minor; drawn from C minor it is A flat major, and the figure's other notes are C minor's too.
        progression = {ProgressionSetting.CHORDS: [6, 6], ProgressionSetting.SCALES: [None, MINOR]}
        self.assertEqual(self.played(progression), [['A', 'C', 'E', 'G'], ['G#', 'C', 'D#', 'G']])
        self.assertEqual(self.played({ProgressionSetting.CHORDS: [1], ProgressionSetting.SCALES: [MINOR]}, rows=self.SCALE_FIGURE), [['C', 'D', 'F', 'G#']])

    def test_a_tension_sets_the_note_between_the_chords_notes(self):
        # On V, the figure's 2, 4 and 6 are A, C and E; a flat ninth, a sharp eleventh and a flat thirteenth make them A flat, C sharp and E flat.
        progression = {ProgressionSetting.CHORDS: [5, 5], ProgressionSetting.TENSIONS: [None, [Tension.FLAT_NINTH, Tension.SHARP_ELEVENTH, Tension.FLAT_THIRTEENTH]]}
        self.assertEqual(self.played(progression, rows=self.SCALE_FIGURE), [['G', 'A', 'C', 'E'], ['G', 'G#', 'C#', 'D#']])

    def test_a_tension_is_added_on_top_of_a_chord_of_the_figure(self):
        rows = {Row.DEGREE: [1, None, None, None], Row.CHORD: [ChordSymbol.SCALE_SEVENTH, None, None, None]}
        progression = {ProgressionSetting.CHORDS: [5], ProgressionSetting.QUALITIES: [ChordSymbol.DOMINANT7], ProgressionSetting.TENSIONS: [[Tension.FLAT_NINTH, Tension.THIRTEENTH]]}
        chord = bars(through(progression, repeat=1, rows=rows), per_bar=len(self.THIRTEENTH_FLAT_NINE))[0]
        self.assertEqual(sorted(chord), sorted(self.THIRTEENTH_FLAT_NINE))

    def test_a_scale_a_quality_and_a_flat_together(self):
        # bVI7 of C major: the root a half step under A, the figure made a dominant seventh.
        progression = {ProgressionSetting.CHORDS: [6], ProgressionSetting.ACCIDENTALS: [Accidental.FLAT], ProgressionSetting.QUALITIES: [ChordSymbol.DOMINANT7]}
        self.assertEqual(self.played(progression), [['G#', 'C', 'D#', 'F#']])

    def test_a_note_outside_the_scale_keeps_its_distance_and_is_not_replaced(self):
        rows = {Row.DEGREE: [1, 3, 5, 7], Row.ACCIDENTAL: [None, Accidental.FLAT, None, None]}
        progression = {ProgressionSetting.CHORDS: [1], ProgressionSetting.QUALITIES: [ChordSymbol.MAJOR7]}
        self.assertEqual(self.played(progression, rows=rows), [['C', 'D#', 'G', 'B']])

    def test_a_file_refuses_a_scale_a_quality_or_tensions_it_does_not_know(self):
        for row, values in ((ProgressionSetting.SCALES, ['nonsense']), (ProgressionSetting.QUALITIES, [ChordSymbol.SCALE_SEVENTH]),
                            (ProgressionSetting.TENSIONS, [['b7']]), (ProgressionSetting.TENSIONS, [Tension.NINTH])):
            with self.assertRaises(SongFileError, msg=(row, values)):
                setlist_from_data(through({ProgressionSetting.CHORDS: [1], row: values}))


class TestWhatAFileHolds(unittest.TestCase):

    def test_a_degree_out_of_range_is_refused(self):
        with self.assertRaises(SongFileError):
            setlist_from_data(through({ProgressionSetting.CHORDS: [8]}))

    def test_no_chords_is_refused(self):
        with self.assertRaises(SongFileError):
            setlist_from_data(through({ProgressionSetting.CHORDS: []}))

    def test_a_wrong_inversion_is_refused(self):
        with self.assertRaises(SongFileError):
            setlist_from_data(through({ProgressionSetting.CHORDS: [1], ProgressionSetting.INVERSIONS: [3]}))


class TestChordsInAScale(unittest.TestCase):

    C_MAJOR = NamedScale(root=NoteName.C, kind=MAJOR)
    A_MINOR = NamedScale(root=NoteName.A, kind=MINOR)

    def test_numerals_and_names_of_c_major(self):
        self.assertEqual([roman_numeral(scale=self.C_MAJOR, degree=degree) for degree in range(1, 8)], ['I', 'ii', 'iii', 'IV', 'V', 'vi', 'vii°'])
        self.assertEqual([chord_name(scale=self.C_MAJOR, degree=degree) for degree in range(1, 8)], ['C', 'Dm', 'Em', 'F', 'G', 'Am', 'B°'])

    def test_a_flat_chord_keeps_the_figures_quality_and_is_spelled_with_a_flat(self):
        self.assertEqual(roman_numeral(scale=self.C_MAJOR, degree=7, accidental=Accidental.FLAT), '♭VII')
        self.assertEqual(chord_name(scale=self.C_MAJOR, degree=7, accidental=Accidental.FLAT), 'Bb')

    def test_the_same_degrees_follow_an_edited_scale(self):
        self.assertEqual([chord_name(scale=self.A_MINOR, degree=degree) for degree in (1, 5, 6, 4)], ['Am', 'Em', 'F', 'Dm'])

    def test_a_named_progression_is_matched_to_the_scale(self):
        self.assertEqual(named_progression_in(key=NamedProgression.ANDALUSIAN, scale=self.A_MINOR), ([1, 7, 6, 5], [None] * 4))
        self.assertEqual(named_progression_in(key=NamedProgression.ROCK, scale=self.C_MAJOR), ([1, 7, 4], [None, Accidental.FLAT, None]))
        self.assertEqual(named_progression_in(key=NamedProgression.GRUNGE, scale=self.C_MAJOR), ([1, 6, 3, 7], [None, Accidental.FLAT, Accidental.FLAT, Accidental.FLAT]))

    def test_no_scale_reads_as_c_major(self):
        self.assertEqual(chord_name(scale=None, degree=6), 'Am')
