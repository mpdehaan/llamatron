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

"""The melody engines: the row operations, the serial engine's row, forms, lengths and voices, and which engine a song's tune
is made by."""

import unittest

from llamatron.macro_composer import arranger, composer, melody, notation, operations

MINOR = 'minor'
SEED = 9
OTHER_SEED = 10
GRID = 8
LINE_BARS = 2
# C E D G B A F as places in the notes of C major, and that row upside down and backwards.
ROW = [0, 2, 1, 4, 6, 5, 3]
ROW_UPSIDE_DOWN = [0, 5, 6, 3, 1, 2, 4]
ROW_BACKWARDS = [3, 5, 6, 4, 1, 2, 0]
ROW_MOVED_UP_TWO = [2, 4, 3, 6, 1, 0, 5]
ROW_BEGUN_TWO_LATER = [1, 4, 6, 5, 3, 0, 2]
NOTES_IN_SCALE = 7
NOTES_IN_OCTAVE = 12
CHORDS = [{notation.DEGREE: 1}]
HABITS = {
    melody.GRID: GRID, melody.LINE_BARS: LINE_BARS, melody.SPAN: 4, melody.HOME: {notation.DEGREE: 1},
    melody.LADDER: [{notation.DEGREE: degree} for degree in range(1, NOTES_IN_SCALE + 1)], melody.RHYTHMS: [], melody.ANSWER_RHYTHMS: [],
    melody.LENGTHS: [1, 1, 2, 1, 3, 2, 1],
}
# Three lines nobody has heard, then the first again, then the first varied.
PLAN = [{melody.LINE: 'a'}, {melody.LINE: 'b'}, {melody.LINE: 'c'}, {melody.LINE: 'a'}, {melody.LINE: 'a', melody.VARIED: True}]
NEW_LINES = 3
HIGH = 'high'
LOW = 'low'
ROCK = 'rock'
EXPERIMENTAL = 'experimental'
LEAD = 'lead'
THREE = 'three'
VERSE = 'verse'
BEAT_GROUP = 'beat group'
SERIAL_TRIO = 'serial trio'


def pitch_of(note):
    """A note without its octave or its length: which note of the row it is."""
    return (note[notation.DEGREE], note.get(notation.ACCIDENTAL))


def serial(*, seed=SEED, voice=None, **habits):
    return melody.Serial(habits={**HABITS, **habits}, chords=CHORDS, scale_type=MINOR, seed=seed, answers=False, voice=voice)


class TestRowOperations(unittest.TestCase):

    def test_a_row_backwards_upside_down_moved_and_begun_later(self):
        self.assertEqual(operations.backwards(ROW), ROW_BACKWARDS)
        self.assertEqual(operations.upside_down(row=ROW, size=NOTES_IN_SCALE), ROW_UPSIDE_DOWN)
        self.assertEqual(operations.moved(row=ROW, by=2, size=NOTES_IN_SCALE), ROW_MOVED_UP_TWO)
        self.assertEqual(operations.rotated(row=ROW, by=2), ROW_BEGUN_TWO_LATER)

    def test_every_operation_keeps_every_note_once_and_leaves_the_row_alone(self):
        kept = list(ROW)
        for made in (operations.backwards(ROW), operations.upside_down(row=ROW, size=NOTES_IN_SCALE), operations.moved(row=ROW, by=3, size=NOTES_IN_SCALE),
                     operations.rotated(row=ROW, by=3)):
            self.assertEqual(sorted(made), sorted(ROW))
        self.assertEqual(ROW, kept)

    def test_upside_down_twice_and_backwards_twice_are_the_row(self):
        self.assertEqual(operations.upside_down(row=operations.upside_down(row=ROW, size=NOTES_IN_SCALE), size=NOTES_IN_SCALE), ROW)
        self.assertEqual(operations.backwards(operations.backwards(ROW)), ROW)


class TestSerial(unittest.TestCase):

    def sounds(self, lines):
        return [note for line in lines for note in line if notation.REST not in note]

    def test_the_row_is_every_note_of_the_scale_once_and_all_twelve_when_chromatic(self):
        self.assertEqual(sorted(serial().row()), list(range(NOTES_IN_SCALE)))
        self.assertEqual(sorted(serial(**{melody.CHROMATIC: True}).row()), list(range(NOTES_IN_OCTAVE)))
        self.assertEqual(len({pitch_of(note) for note in melody.twelve_notes(MINOR)}), NOTES_IN_OCTAVE)

    def test_no_note_returns_until_the_others_have_sounded(self):
        for habits in ({}, {melody.CHROMATIC: True}, {melody.LEAPS: True}):
            engine = serial(**habits)
            size = len(engine.row())
            heard = [pitch_of(note) for note in self.sounds(engine.sketched(PLAN[:NEW_LINES]))]
            for start in range(0, len(heard) - size + 1, size):
                with self.subTest(habits=habits, start=start):
                    self.assertEqual(len(set(heard[start:start + size])), size)

    def test_a_form_begins_beside_the_note_the_form_before_ended_on(self):
        engine = serial()
        notes = engine.notes()
        places = [next(place for place, note in enumerate(notes) if pitch_of(note) == pitch) for pitch in
                  (pitch_of(note) for note in self.sounds(engine.sketched(PLAN[:NEW_LINES])))]
        for start in range(NOTES_IN_SCALE, len(places), NOTES_IN_SCALE):
            self.assertIn((places[start] - places[start - 1]) % NOTES_IN_SCALE, (1, NOTES_IN_SCALE - 1))

    def test_every_line_fills_its_bars_and_a_line_named_again_returns(self):
        lines = serial().sketched(PLAN)
        for line in lines:
            self.assertEqual(sum(note[notation.STEPS] for note in line), GRID * LINE_BARS)
        self.assertEqual(lines[3], lines[0])

    def test_a_varied_line_is_the_lines_notes_backwards_in_its_own_rhythm(self):
        lines = serial().sketched(PLAN)
        first, varied = lines[0], lines[4]
        self.assertEqual([note[notation.STEPS] for note in varied], [note[notation.STEPS] for note in first])
        self.assertEqual([pitch_of(note) for note in varied], [pitch_of(note) for note in reversed(first)])

    def test_the_lengths_are_a_row_read_forwards_and_then_backwards(self):
        engine = serial()
        count = len(HABITS[melody.LENGTHS])
        lengths = [engine.next_length() for _ in range(count * 2)]
        self.assertEqual(sorted(lengths[:count]), sorted(HABITS[melody.LENGTHS]))
        self.assertEqual(lengths[count:], list(reversed(lengths[:count])))

    def test_the_same_seed_gives_the_same_tune_and_another_seed_another_row(self):
        self.assertEqual(serial().sketched(PLAN), serial().sketched(PLAN))
        self.assertNotEqual(serial().row(), serial(seed=OTHER_SEED).row())

    def test_two_voices_share_the_row_and_read_it_differently(self):
        high, low = serial(voice=HIGH), serial(voice=LOW)
        self.assertEqual(high.row(), low.row())
        self.assertNotEqual(high.sketched(PLAN), low.sketched(PLAN))

    def test_with_leaps_a_note_may_take_any_octave_in_range_and_without_it_takes_the_nearest(self):
        near = self.sounds(serial().sketched(PLAN[:NEW_LINES]))
        thrown = self.sounds(serial(**{melody.LEAPS: True}).sketched(PLAN[:NEW_LINES]))
        self.assertEqual([pitch_of(note) for note in near][:NOTES_IN_SCALE], [pitch_of(note) for note in thrown][:NOTES_IN_SCALE])
        self.assertNotEqual([note.get(notation.OCTAVE, 0) for note in near], [note.get(notation.OCTAVE, 0) for note in thrown])


class TestEngineChosen(unittest.TestCase):

    def lead(self, song):
        made = arranger.arranged(style=arranger.style_named(song[arranger.STYLE]), song=song)
        return [part for name, part in made[composer.PARTS].items() if notation.LINES in part and name.endswith(LEAD)]

    def song(self, **more):
        return {arranger.NAME: 'a_song', arranger.TITLE: 'A song', arranger.STYLE: ROCK, arranger.TEMPLATE: BEAT_GROUP, arranger.KEY: {arranger.ROOT: 'D'},
                arranger.SEED: SEED, arranger.FORM: [VERSE], **more}

    def test_a_song_picks_the_engine_its_tunes_are_made_by_and_the_step_walk_is_usual(self):
        usual = self.lead(self.song())
        self.assertEqual(usual, self.lead(self.song(**{arranger.MELODY_ENGINE: melody.STEP_WALK})))
        self.assertNotEqual(usual, self.lead(self.song(**{arranger.MELODY_ENGINE: melody.SERIAL})))

    def test_a_style_may_name_its_engine_and_every_voice_plays_the_row(self):
        style = arranger.style_named(EXPERIMENTAL)
        song = {**self.song(), arranger.STYLE: EXPERIMENTAL, arranger.TEMPLATE: SERIAL_TRIO, arranger.FORM: [THREE]}
        made = arranger.arranged(style=style, song=song)
        self.assertEqual(style[arranger.MELODY][melody.ENGINE], melody.SERIAL)
        voices = [part for name, part in made[composer.PARTS].items() if name.startswith(THREE)]
        self.assertEqual(len(voices), len(style[arranger.ROLES]))
        for voice in voices:
            heard = [pitch_of(note) for line in voice[notation.LINES] for note in line][:NOTES_IN_SCALE]
            self.assertEqual(len(set(heard)), NOTES_IN_SCALE)

