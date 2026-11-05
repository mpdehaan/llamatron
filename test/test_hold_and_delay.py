# noose6: a Python language and framework for producing MIDI clips.
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

from src.chord import ChordType
from src.generators.base import ClipGenerator
from src.legacy.generators.delay import Delay
from src.legacy.generators.hold import Hold
from src.note import Note, Rest
from src.renderers.timing import timed_notes
from src.scale import Scale, ScaleType
from src.song import Clip

SCALE = Scale(Note('C', 4), ScaleType.MAJOR)
C4 = Note('C', 4, 0.25)
D4 = Note('D', 4, 0.25)


def notes_of(clip):
    return sorted(timed_notes(clip, None)[0])


class TestHold(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(Hold(0.125), ClipGenerator)

    def test_a_note_grows_into_the_rest_after_it(self):
        result = Hold(0.125).generate(Clip(notes=[C4, Rest(0.25), D4])).notes
        self.assertEqual(result, [Note('C', 4, 0.375), Rest(0.125), D4])

    def test_every_note_still_starts_on_time(self):
        notes = [C4, Rest(0.25), D4, Rest(0.5), C4]
        before = [start for start, _, _ in notes_of(Clip(notes=notes))]
        after = [start for start, _, _ in notes_of(Hold(0.125).generate(Clip(notes=notes)))]
        self.assertEqual(after, before)

    def test_a_note_with_no_rest_after_it_stays(self):
        self.assertEqual(Hold(0.125).generate(Clip(notes=[C4, D4])).notes, [C4, D4])

    def test_only_grows_as_far_as_the_rest_allows(self):
        result = Hold(0.5).generate(Clip(notes=[C4, Rest(0.25), D4])).notes
        self.assertEqual(result, [Note('C', 4, 0.5), D4])

    def test_every_chooses_the_notes(self):
        notes = [C4, Rest(0.25), D4, Rest(0.25)]
        result = Hold(0.125, every=2).generate(Clip(notes=notes)).notes
        self.assertEqual(result, [C4, Rest(0.25), Note('D', 4, 0.375), Rest(0.125)])

    def test_rests_do_not_count_towards_every(self):
        notes = [C4, Rest(0.25), Rest(0.25), D4, Rest(0.25)]
        result = Hold(0.125, every=2).generate(Clip(notes=notes)).notes
        self.assertEqual(result[-2:], [Note('D', 4, 0.375), Rest(0.125)])

    def test_chords_grow_together(self):
        chord = C4.to_chord(ChordType.MAJOR)
        result = Hold(0.125).generate(Clip(notes=[chord, Rest(0.25)])).notes
        self.assertEqual(result, [Note('C', 4, 0.375).to_chord(ChordType.MAJOR), Rest(0.125)])

    def test_keeps_total_length_and_details(self):
        original = Clip('Riff', notes=[C4, Rest(0.25)], scale=SCALE)
        result = Hold(0.125).generate(original)
        self.assertEqual(result.total_length(), 0.5)
        self.assertEqual(result.name, 'Riff')
        self.assertEqual(original.notes, [C4, Rest(0.25)])

    def test_rejects_invalid_values(self):
        for length in [0, -1, '1', None, True]:
            with self.assertRaises(ValueError):
                Hold(length)
        for every in [0, -1, 1.5, '2', None, True]:
            with self.assertRaises(ValueError):
                Hold(0.125, every=every)

    def test_fields_can_be_edited_and_are_validated(self):
        generator = Hold(0.125)
        generator.every = 3
        self.assertEqual(generator.every, 3)
        with self.assertRaises(ValueError):
            generator.every = 0
        self.assertEqual(generator.every, 3)


class TestDelay(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(Delay(0.125), ClipGenerator)

    def test_a_note_starts_late_and_ends_on_time(self):
        result = Delay(0.125).generate(Clip(notes=[C4])).notes
        self.assertEqual(result, [Rest(0.125), Note('C', 4, 0.125)])

    def test_nothing_after_it_moves(self):
        result = Delay(0.0625, every=2).generate(Clip(notes=[C4, D4, C4])).notes
        self.assertEqual(result, [C4, Rest(0.0625), Note('D', 4, 0.1875), C4])

    def test_a_note_too_short_stays(self):
        self.assertEqual(Delay(0.25).generate(Clip(notes=[C4])).notes, [C4])

    def test_rests_stay_and_do_not_count_towards_every(self):
        result = Delay(0.125, every=2).generate(Clip(notes=[C4, Rest(0.25), D4])).notes
        self.assertEqual(result, [C4, Rest(0.25), Rest(0.125), Note('D', 4, 0.125)])

    def test_chords_move_together(self):
        chord = Note('C', 4, 0.5).to_chord(ChordType.MAJOR)
        result = Delay(0.25).generate(Clip(notes=[chord])).notes
        self.assertEqual(result, [Rest(0.25), Note('C', 4, 0.25).to_chord(ChordType.MAJOR)])

    def test_keeps_total_length_and_details(self):
        original = Clip('Riff', notes=[C4, D4], scale=SCALE)
        result = Delay(0.0625).generate(original)
        self.assertEqual(result.total_length(), 0.5)
        self.assertEqual(result.name, 'Riff')
        self.assertEqual(original.notes, [C4, D4])

    def test_rejects_invalid_values(self):
        for amount in [0, -1, '1', None, True]:
            with self.assertRaises(ValueError):
                Delay(amount)
        for every in [0, 1.5, '2', True]:
            with self.assertRaises(ValueError):
                Delay(0.125, every=every)

    def test_fields_can_be_edited_and_are_validated(self):
        generator = Delay(0.125)
        generator.amount = 0.25
        self.assertEqual(generator.amount, 0.25)
        with self.assertRaises(ValueError):
            generator.amount = 0
        self.assertEqual(generator.amount, 0.25)


if __name__ == '__main__':
    unittest.main()
