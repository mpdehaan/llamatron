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

import unittest

from llamatron.chord import ChordType
from llamatron.generators.base import ClipGenerator
from llamatron.generators.take_rhythm import TakeRhythm
from llamatron.note import Note, Rest
from llamatron.scale import Scale, ScaleType
from llamatron.song import Clip

C_MAJOR = Scale(Note('C', 4), ScaleType.MAJOR)


def take(rhythm, notes):
    return TakeRhythm(Clip(notes=rhythm)).generate(Clip(notes=notes)).notes


class TestTakeRhythm(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(TakeRhythm(Clip()), ClipGenerator)

    def test_long_notes_get_the_rhythm_of_quick_notes(self):
        result = take([Note('A', 4, 0.5), Note('A', 4, 0.5)], [Note('C', 4, 1)])
        self.assertEqual(result, [Note('C', 4, 0.5), Note('C', 4, 0.5)])

    def test_quick_notes_get_the_rhythm_of_long_notes_using_the_pitch_at_that_moment(self):
        rhythm = [Note('A', 4, 1)]
        self.assertEqual(take(rhythm, [Note('C', 4, 0.5), Note('D', 4, 0.5)]), [Note('C', 4, 1)])

    def test_each_rhythm_note_uses_its_own_moment(self):
        rhythm = [Note('A', 4, 0.5), Note('A', 4, 0.5)]
        notes = [Note('C', 4, 0.25), Note('D', 4, 0.5), Note('E', 4, 0.25)]
        self.assertEqual(take(rhythm, notes), [Note('C', 4, 0.5), Note('D', 4, 0.5)])

    def test_rests_in_the_rhythm_stay(self):
        result = take([Rest(0.5), Note('A', 4, 0.5)], [Note('C', 4, 1)])
        self.assertEqual(result, [Rest(0.5), Note('C', 4, 0.5)])

    def test_silence_uses_the_pitch_before(self):
        result = take([Note('A', 4, 0.5), Note('A', 4, 0.5)], [Note('C', 4, 0.5), Rest(0.5)])
        self.assertEqual(result, [Note('C', 4, 0.5), Note('C', 4, 0.5)])

    def test_silence_at_the_start_uses_the_next_pitch(self):
        result = take([Note('A', 4, 0.5), Note('A', 4, 0.5)], [Rest(0.75), Note('C', 4, 0.25)])
        self.assertEqual(result, [Note('C', 4, 0.5), Note('C', 4, 0.5)])

    def test_no_notes_at_all_stays_silent(self):
        self.assertEqual(take([Note('A', 4, 1)], [Rest(1)]), [Rest(1)])

    def test_chords_take_the_rhythm_together(self):
        chord = Note('C', 4, 1).to_chord(ChordType.MAJOR)
        shorter = Note('C', 4, 0.5).to_chord(ChordType.MAJOR)
        self.assertEqual(take([Note('A', 4, 0.5), Rest(0.5)], [chord]), [shorter, Rest(0.5)])

    def test_a_rhythm_chord_plays_a_note(self):
        rhythm = [Note('A', 4, 1).to_chord(ChordType.MAJOR)]
        self.assertEqual(take(rhythm, [Note('C', 4, 1)]), [Note('C', 4, 1)])

    def test_a_clip_with_its_own_rhythm_stays_the_same(self):
        notes = [Note('C', 4, 0.25), Rest(0.25), Note('D', 4, 0.5)]
        self.assertEqual(take(notes, notes), notes)

    def test_rejects_clips_of_different_lengths(self):
        with self.assertRaises(ValueError):
            take([Note('A', 4, 1)], [Note('C', 4, 2)])

    def test_keeps_details_and_leaves_the_originals_alone(self):
        rhythm = Clip(notes=[Note('A', 4, 1)])
        original = Clip('Riff', notes=[Note('C', 4, 1)], scale=C_MAJOR)
        result = TakeRhythm(rhythm).generate(original)
        self.assertEqual(result.name, 'Riff')
        self.assertIs(result.scale, C_MAJOR)
        self.assertEqual(rhythm.notes, [Note('A', 4, 1)])

    def test_rejects_invalid_values(self):
        for rhythm in [None, 'clip', Note('C', 4, 1)]:
            with self.subTest(rhythm=rhythm):
                with self.assertRaises(ValueError):
                    TakeRhythm(rhythm)

    def test_rhythm_can_be_edited_and_is_validated(self):
        generator = TakeRhythm(Clip())
        other = Clip()
        generator.rhythm = other
        self.assertIs(generator.rhythm, other)
        with self.assertRaises(ValueError):
            generator.rhythm = None
        self.assertIs(generator.rhythm, other)


if __name__ == '__main__':
    unittest.main()
