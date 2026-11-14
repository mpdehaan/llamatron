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

"""A chord's scale, quality and tensions (the user's design): on a pattern's step, the Tension row adding notes on top of the
step's chord and the Scale row drawing the step from another scale type on the clip's root; what a file refuses of both; and
what a chord comes to in a scale, its names and its notes, as the editors show it."""

import unittest

from llamatron.composition.chords import chord_half_steps, replaced_places, spelled_chord, FIFTH_PLACE, NINTH_PLACE, SEVENTH_PLACE, THIRD_PLACE
from llamatron.composition.file_format import Accidental, ChordSymbol, ClipSlotSetting, PatternSetting, Row, SceneSetting, Tension, TENSIONS
from llamatron.composition.named_scale import NamedScale, scale_type_name
from llamatron.composition.song_file_error import SongFileError
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from rendering import setlist_from_data
from test_progression import NAMES
from test_registers import LEAD, X, pattern, song
from test_shapes import notes

MINOR = scale_type_name(ScaleType.MINOR)
C_MAJOR = NamedScale(root=NoteName.C, kind=scale_type_name(ScaleType.MAJOR))
STEPS = 2
ALTERED = (Tension.FLAT_NINTH, Tension.THIRTEENTH)
OUT_OF_ORDER = [Tension.THIRTEENTH, Tension.FLAT_NINTH]
NO_SUCH_TENSION = 'b7'
NO_SUCH_SCALE = 'nonsense'


def stepped(**rows):
    """Return a song whose lead plays a pattern of two steps with the rows given."""
    return song(patterns={X: pattern(STEPS, **rows)}, scenes=[{SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X}}}])


def sounding(data):
    """Return the note names sounding at each step's start, lowest first."""
    by_start = {}
    for start, _, pitch, _ in notes(data):
        by_start.setdefault(start, []).append(pitch)
    return [[NAMES[pitch % len(NAMES)] for pitch in sorted(by_start[start])] for start in sorted(by_start)]


class TestAStepsTensions(unittest.TestCase):

    def test_tensions_are_added_above_the_chords_root(self):
        data = stepped(**{Row.DEGREE: [5, 5], Row.CHORD: [ChordSymbol.DOMINANT7] * STEPS, Row.TENSION: [None, list(ALTERED)]})
        self.assertEqual(sounding(data), [['G', 'B', 'D', 'F'], ['G', 'B', 'D', 'F', 'G#', 'E']])

    def test_a_tension_the_chord_already_holds_is_not_doubled_and_a_single_note_takes_none(self):
        data = stepped(**{Row.DEGREE: [5, 5], Row.CHORD: [ChordSymbol.DOMINANT9, None], Row.TENSION: [[Tension.NINTH], [Tension.NINTH]]})
        self.assertEqual(sounding(data), [['G', 'B', 'D', 'F', 'A'], ['G']])

    def test_a_pattern_keeps_a_steps_tensions_lowest_first_and_writes_a_list(self):
        made = setlist_from_data(stepped(**{Row.DEGREE: [5, 5], Row.CHORD: [ChordSymbol.DOMINANT7] * STEPS, Row.TENSION: [None, OUT_OF_ORDER]})).get_pattern(X)
        self.assertEqual(made.get_value(row=Row.TENSION, step=1), ALTERED)
        made.set_value(row=Row.TENSION, step=0, value=OUT_OF_ORDER)
        self.assertEqual(made.get_value(row=Row.TENSION, step=0), ALTERED)
        self.assertEqual(made.to_data()[Row.TENSION], [list(ALTERED), list(ALTERED)])

    def test_a_file_refuses_tensions_it_does_not_know_and_tensions_on_drums(self):
        for rows in ({Row.TENSION: [[NO_SUCH_TENSION], None]}, {Row.TENSION: [Tension.NINTH, None]}, {Row.TENSION: [[], None]},
                     {Row.TENSION: [[Tension.NINTH, Tension.NINTH], None]}):
            with self.assertRaises(SongFileError, msg=rows):
                setlist_from_data(stepped(**{Row.DEGREE: [1, 1], **rows}))
        with self.assertRaises(SongFileError):
            setlist_from_data(stepped(**{PatternSetting.DRUM: True, Row.DEGREE: [NoteName.C] * STEPS, Row.TENSION: [[Tension.NINTH], None]}))


class TestAStepsScale(unittest.TestCase):

    def test_a_step_is_drawn_from_its_scale_on_the_clips_root(self):
        # Degree 6 of C major is A, and its scale triad A minor; drawn from C minor it is A flat major.
        data = stepped(**{Row.DEGREE: [6, 6], Row.CHORD: [ChordSymbol.SCALE_TRIAD] * STEPS, Row.CHORD_SCALE: [None, MINOR]})
        self.assertEqual(sounding(data), [['A', 'C', 'E'], ['G#', 'C', 'D#']])

    def test_a_single_note_borrows_too(self):
        self.assertEqual(sounding(stepped(**{Row.DEGREE: [3, 3], Row.CHORD_SCALE: [None, MINOR]})), [['E'], ['D#']])

    def test_a_file_refuses_a_scale_it_does_not_know_and_a_scale_on_drums(self):
        with self.assertRaises(SongFileError):
            setlist_from_data(stepped(**{Row.DEGREE: [1, 1], Row.CHORD_SCALE: [NO_SUCH_SCALE, None]}))
        with self.assertRaises(SongFileError):
            setlist_from_data(stepped(**{PatternSetting.DRUM: True, Row.DEGREE: [NoteName.C] * STEPS, Row.CHORD_SCALE: [MINOR, None]}))


class TestSpelling(unittest.TestCase):
    """What a chord comes to in C major."""

    def spelled(self, **chord):
        found = spelled_chord(scale=C_MAJOR, **chord)
        return found.name, found.long_name, ' '.join(found.notes)

    def test_the_scales_own_chords(self):
        self.assertEqual(self.spelled(degree=2), ('Dm', 'D Minor', 'D F A'))
        self.assertEqual(self.spelled(degree=7), ('B°', 'B Diminished', 'B D F'))
        self.assertEqual(self.spelled(degree=2, symbol=7), ('Dm7', 'D Minor Seventh', 'D F A C'))

    def test_a_named_quality_and_its_tensions(self):
        self.assertEqual(self.spelled(degree=3, symbol=ChordSymbol.MAJOR), ('E', 'E Major', 'E G# B'))
        self.assertEqual(self.spelled(degree=6, symbol=ChordSymbol.DOMINANT7, tensions=(Tension.FLAT_NINTH,)), ('A7(b9)', 'A Dominant Seventh (b9)', 'A C# E G Bb'))
        self.assertEqual(self.spelled(degree=5, symbol=ChordSymbol.DOMINANT7, tensions=ALTERED)[2], 'G B D F Ab E')

    def test_a_borrowed_chord_is_spelled_on_its_scales_letters(self):
        self.assertEqual(self.spelled(degree=6, kind=MINOR), ('Ab', 'Ab Major', 'Ab C Eb'))

    def test_a_flat_chord_keeping_the_sound_of_degree_one(self):
        self.assertEqual(self.spelled(degree=7, accidental=Accidental.FLAT, own_degree=1), ('Bb', 'Bb Major', 'Bb D F'))

    def test_no_scale_is_shown_as_c_major(self):
        self.assertEqual(spelled_chord(scale=None, degree=4).name, 'F')

    def test_a_chords_half_steps_leave_out_a_tension_it_holds(self):
        self.assertEqual(chord_half_steps(scale=C_MAJOR, degree=5, symbol=ChordSymbol.DOMINANT9, tensions=(Tension.NINTH, Tension.SHARP_ELEVENTH)), (4, 7, 10, 14, TENSIONS[Tension.SHARP_ELEVENTH]))

    def test_the_places_a_quality_and_tensions_replace(self):
        self.assertEqual(replaced_places(symbol=ChordSymbol.MINOR7, tensions=(Tension.FLAT_NINTH,)), {THIRD_PLACE: 3, FIFTH_PLACE: 7, SEVENTH_PLACE: 10, NINTH_PLACE: 1})
        self.assertEqual(replaced_places(symbol=None, tensions=None), {})


if __name__ == '__main__':
    unittest.main()
