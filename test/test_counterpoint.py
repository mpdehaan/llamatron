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
from fractions import Fraction

from demo.tunes import C_MAJOR, SIMPLE_GIFTS, SIMPLE_GIFTS_CHORDS
from src.analyzers.clash_finder import ClashFinder
from src.chord import ChordType
from src.generators.base import ClipGenerator
from src.legacy.generators.counterpoint import Counterpoint, CounterpointStyle
from src.note import Note, Rest
from src.renderers.timing import timed_notes
from src.song import Clip

CONSONANT = {0, 3, 4, 7, 8, 9}
NOTE_AGAINST_NOTE = CounterpointStyle.NOTE_AGAINST_NOTE
FLOWING = CounterpointStyle.FLOWING
CANON = CounterpointStyle.CANON

CHORDS = SIMPLE_GIFTS_CHORDS.measures(2, 9)
MELODY = SIMPLE_GIFTS.measures(2, 9)
ALL_STYLES = [NOTE_AGAINST_NOTE, FLOWING, CANON]


def write(style, melody=MELODY, chords=CHORDS, **options):
    return Counterpoint(chords, style=style, **options).generate(melody)


def notes_of(clip):
    return sorted(timed_notes(clip, clip.scale)[0])


def melody_at(time, melody):
    sounding = [pitch for start, end, pitch in notes_of(melody) if start <= time < end]
    return max(sounding) if sounding else None


class TestEveryStyle(unittest.TestCase):

    def test_is_a_clip_generator(self):
        self.assertIsInstance(Counterpoint(CHORDS), ClipGenerator)

    def test_lasts_as_long_as_the_melody(self):
        for style in ALL_STYLES:
            with self.subTest(style=style):
                self.assertEqual(write(style).total_length(), MELODY.total_length())

    def test_stays_in_its_range(self):
        for style in ALL_STYLES:
            with self.subTest(style=style):
                pitches = [pitch for _, _, pitch in notes_of(write(style))]
                self.assertGreaterEqual(min(pitches), Note('C', 2).midi_number)
                self.assertLessEqual(max(pitches), Note('C', 3).midi_number)

    def test_range_can_change(self):
        for style in ALL_STYLES:
            with self.subTest(style=style):
                clip = write(style, low=Note('G', 3), high=Note('G', 4))
                pitches = [pitch for _, _, pitch in notes_of(clip)]
                self.assertGreaterEqual(min(pitches), Note('G', 3).midi_number)
                self.assertLessEqual(max(pitches), Note('G', 4).midi_number)

    def test_never_clashes_with_the_chords(self):
        for style in ALL_STYLES:
            with self.subTest(style=style):
                self.assertEqual(ClashFinder().analyze(write(style), CHORDS), [])

    def test_same_seed_gives_the_same_line(self):
        for style in ALL_STYLES:
            with self.subTest(style=style):
                self.assertEqual(write(style, seed=3).notes, write(style, seed=3).notes)

    def test_keeps_details_and_leaves_the_originals_alone(self):
        original = Clip('Riff', notes=list(MELODY.notes), scale=C_MAJOR)
        before = list(original.notes)
        result = Counterpoint(CHORDS).generate(original)
        self.assertEqual(result.name, 'Riff')
        self.assertIs(result.scale, C_MAJOR)
        self.assertEqual(original.notes, before)

    def test_uses_the_spelling_of_the_scale(self):
        for style in ALL_STYLES:
            with self.subTest(style=style):
                names = {p.name for p in write(style).notes if isinstance(p, Note)}
                self.assertLessEqual(names, {'C', 'D', 'E', 'F', 'G', 'A', 'B'})

    def test_needs_a_scale(self):
        with self.assertRaises(ValueError):
            write(NOTE_AGAINST_NOTE, melody=Clip(notes=[Note('C', 4, 1)]))
        self.assertTrue(write(NOTE_AGAINST_NOTE, melody=Clip(notes=[Note('C', 4, 1)]), scale=C_MAJOR).notes)

    def test_empty_melody_is_silent(self):
        for style in [NOTE_AGAINST_NOTE, CANON]:
            with self.subTest(style=style):
                clip = Clip(scale=C_MAJOR, notes=[Rest(1)])
                self.assertEqual(write(style, melody=clip).notes, [Rest(1)])


class RuleChecks:
    """Rules that a written line must follow, for styles that choose their own notes."""

    style = None

    def line(self):
        return write(self.style)

    def test_scale_notes_only(self):
        allowed = {(C_MAJOR.root.midi_number + step) % 12 for step in C_MAJOR.typ.value}
        self.assertLessEqual({pitch % 12 for _, _, pitch in notes_of(self.line())}, allowed)

    def test_never_goes_above_the_melody(self):
        for start, _, pitch in notes_of(self.line()):
            melody = melody_at(start, MELODY)
            if melody is not None:
                self.assertLess(pitch, melody)

    def test_strong_notes_are_consonant_with_the_melody(self):
        for start, end, pitch in notes_of(self.line()):
            melody = melody_at(start, MELODY)
            if melody is not None and (start % Fraction(1, 4) == 0 or end - start >= Fraction(1, 4)):
                with self.subTest(start=start):
                    self.assertIn((melody - pitch) % 12, CONSONANT)

    def test_no_parallel_fifths_or_octaves(self):
        notes = notes_of(self.line())
        for (start, _, pitch), (next_start, _, next_pitch) in zip(notes, notes[1:]):
            first, second = melody_at(start, MELODY), melody_at(next_start, MELODY)
            if first is None or second is None or next_pitch == pitch or first == second:
                continue
            same_direction = (next_pitch - pitch) * (second - first) > 0
            interval = (first - pitch) % 12
            if same_direction and interval == (second - next_pitch) % 12:
                with self.subTest(start=start):
                    self.assertNotIn(interval, {0, 7})

    def test_moves_mostly_by_small_steps(self):
        pitches = [pitch for _, _, pitch in notes_of(self.line())]
        leaps = [abs(b - a) for a, b in zip(pitches, pitches[1:])]
        self.assertGreater(sum(leap <= 4 for leap in leaps) / len(leaps), 0.8)

    def test_different_seeds_can_write_different_lines(self):
        lines = {tuple(write(self.style, seed=seed).notes) for seed in range(6)}
        self.assertGreater(len(lines), 1)


class TestStrongNotes(unittest.TestCase):

    def test_leaves_the_chord_when_no_chord_note_is_consonant_with_the_melody(self):
        melody = Clip(notes=[Note('C', 5, 1)], scale=C_MAJOR)
        chords = Clip(notes=[Note('G', 3, 1).to_chord(ChordType.MAJOR)], scale=C_MAJOR)
        line = write(NOTE_AGAINST_NOTE, melody=melody, chords=chords)
        pitch = notes_of(line)[0][2]
        self.assertIn((60 - pitch) % 12, CONSONANT)
        self.assertEqual(ClashFinder().analyze(line, chords), [])


class TestNoteAgainstNote(RuleChecks, unittest.TestCase):

    style = NOTE_AGAINST_NOTE

    def test_one_note_for_each_melody_note(self):
        melody = notes_of(MELODY)
        line = notes_of(self.line())
        self.assertEqual([note[:2] for note in line], [note[:2] for note in melody])

    def test_keeps_rests_in_the_melody(self):
        melody = Clip(notes=[Rest(0.5), Note('E', 4, 0.5), Rest(0.5), Note('G', 4, 0.5)], scale=C_MAJOR)
        chords = Clip(notes=[Note('C', 3, 2).to_chord(ChordType.MAJOR)], scale=C_MAJOR)
        result = write(NOTE_AGAINST_NOTE, melody=melody, chords=chords).notes
        self.assertEqual([type(p) for p in result], [Rest, Note, Rest, Note])
        self.assertEqual([p.length for p in result], [0.5, 0.5, 0.5, 0.5])


class TestFlowing(RuleChecks, unittest.TestCase):

    style = FLOWING

    def test_every_note_is_one_step_long(self):
        self.assertEqual({p.length for p in self.line().notes}, {Fraction(1, 8)})

    def test_step_can_change(self):
        step = Fraction(1, 6)
        clip = write(FLOWING, step=step)
        self.assertEqual({p.length for p in clip.notes}, {step})
        self.assertEqual(clip.total_length(), MELODY.total_length())

    def test_keeps_playing_through_rests_in_the_melody(self):
        melody = Clip(notes=[Note('E', 4, 0.5), Rest(0.5)], scale=C_MAJOR)
        chords = Clip(notes=[Note('C', 3, 1).to_chord(ChordType.MAJOR)], scale=C_MAJOR)
        result = write(FLOWING, melody=melody, chords=chords).notes
        self.assertEqual(len(result), 8)
        self.assertTrue(all(isinstance(p, Note) for p in result))

    def test_rarely_stands_still(self):
        pitches = [pitch for _, _, pitch in notes_of(self.line())]
        repeats = sum(a == b for a, b in zip(pitches, pitches[1:]))
        self.assertLess(repeats / len(pitches), 0.2)


class TestCanon(unittest.TestCase):

    def test_starts_with_silence_for_the_delay(self):
        self.assertEqual(write(CANON).notes[0], Rest(1))

    def test_delay_can_change(self):
        self.assertEqual(write(CANON, delay=2).notes[0], Rest(2))

    def test_follows_the_melody_after_the_delay(self):
        melody = {start: pitch for start, _, pitch in notes_of(MELODY)}
        line = notes_of(write(CANON))
        same = sum(pitch % 12 == melody[start - 1] % 12 for start, _, pitch in line)
        self.assertGreater(same / len(line), 0.75)

    def test_uses_the_melody_rhythm(self):
        melody_starts = {start + 1 for start, _, _ in notes_of(MELODY)}
        self.assertLessEqual({start for start, _, _ in notes_of(write(CANON))}, melody_starts)

    def test_stops_at_the_end_of_the_clip(self):
        line = notes_of(write(CANON))
        self.assertLessEqual(line[-1][1], MELODY.total_length())

    def test_a_clashing_note_moves(self):
        melody = Clip(notes=[Note('C', 5, 1), Note('C', 5, 1)], scale=C_MAJOR)
        f_chord = Note('F', 3, 1).to_chord(ChordType.MAJOR)
        chords = Clip(notes=[f_chord, Note('C#', 3, 1).to_chord(ChordType.MAJOR)], scale=C_MAJOR)
        self.assertEqual(ClashFinder().analyze(write(CANON, melody=melody, chords=chords), chords), [])


class TestFields(unittest.TestCase):

    def test_rejects_invalid_values(self):
        for chords in [None, 'chords']:
            with self.subTest(chords=chords):
                with self.assertRaises(ValueError):
                    Counterpoint(chords)
        cases = [
            {'style': 'CANON'}, {'low': 24}, {'high': 'C3'}, {'step': 0}, {'delay': -1},
            {'scale': 'C major'}, {'seed': '1'},
        ]
        for options in cases:
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    Counterpoint(CHORDS, **options)

    def test_rejects_a_range_upside_down(self):
        with self.assertRaises(ValueError):
            write(FLOWING, low=Note('C', 3), high=Note('C', 2))

    def test_rejects_anything_but_a_clip(self):
        with self.assertRaises(ValueError):
            Counterpoint(CHORDS).generate('clip')

    def test_fields_can_be_edited_and_are_validated(self):
        generator = Counterpoint(CHORDS)
        generator.style = CANON
        self.assertIs(generator.style, CANON)
        with self.assertRaises(ValueError):
            generator.style = None
        self.assertIs(generator.style, CANON)


if __name__ == '__main__':
    unittest.main()
