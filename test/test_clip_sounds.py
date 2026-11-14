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
"""A clip holds the objects it was given or the sounds a render made, and answers the same either way.

The two ways are two paths through every method of a clip, so each is run both ways here: on
clips written by hand with every kind of position, and on every clip of every example.
"""

import unittest
from fractions import Fraction

from llamatron.exporters.timing import timed_events
from llamatron.grid.clip import Clip
from llamatron.grid.control import Control
from llamatron.music.chord import Chord
from llamatron.music.held import Held, phrase
from llamatron.music.note import Degree, Note, NoteName, Rest
from llamatron.music.scale import Scale, ScaleType
from llamatron.music.sound import Sound
from llamatron.strings.errors import ERR_NO_LENGTH
from llamatron.support.example_sets import example_sets
from rendering import render_file

EXAMPLE_PATHS = example_sets()
QUARTER = Fraction(1, 4)
EIGHTH = Fraction(1, 8)
SIXTEENTH = Fraction(1, 16)
THIRD = Fraction(1, 3)
C4 = Note(name=NoteName.C, octave_number=4, length=QUARTER)
E4 = Note(name=NoteName.E, octave_number=4, length=EIGHTH, velocity=90, glide=True)
G4 = Note(name=NoteName.G, octave_number=4, length=THIRD)
# A note and a degree that take the clip's note_length.
NO_LENGTH_NOTE = Note(name=NoteName.D, octave_number=4)
NO_LENGTH_DEGREE = Degree(number=2)
C_MAJOR = Scale(root=C4, typ=ScaleType.MAJOR)
# Every kind of position a clip can list, with held sounds that outlast their places.
EVERY_KIND = [
    C4, Rest(EIGHTH), Chord([C4, E4, G4]), Degree(number=3, length=EIGHTH), Held(sound=G4, length=SIXTEENTH),
    Held(sound=phrase([E4, Rest(SIXTEENTH), Chord([C4, E4])]), length=EIGHTH), NO_LENGTH_NOTE, NO_LENGTH_DEGREE,
    Chord([C4, NO_LENGTH_NOTE]), E4,
]
# The ends of the sections cut from each hand-written clip: inside notes, on their edges and past the clip's end.
SECTION_ENDS = [(0, SIXTEENTH), (SIXTEENTH, QUARTER), (QUARTER, Fraction(3, 8)), (THIRD, 1), (Fraction(3, 16), Fraction(5, 2)), (2, 3)]
# The lengths a hand-written clip is set to: its own, one that cuts it and one that adds silence.
CLIP_LENGTHS = [None, Fraction(7, 16), 4]
REPEATS = 3
CONTROLS = [Control(time=0, number=1, value=10), Control(time=QUARTER, number=1, value=90, slide=True)]


def held_as_sounds(clip):
    """Return a clip that holds as sounds what a clip holds as objects, with every other setting the same."""
    return Clip(
        name=clip.get_name(), sounds=clip.get_sounds(), scale=clip.get_scale(), length=clip.get_length(),
        note_length=clip.get_note_length(), loop=clip.get_loop(), controls=clip.get_controls(),
    )


def held_as_notes(clip):
    """Return a clip that holds as objects what a clip holds as sounds, with every other setting the same."""
    return Clip(
        name=clip.get_name(), notes=[Sound.position(sound) for sound in clip.get_sounds()], scale=clip.get_scale(),
        length=clip.get_length(), note_length=clip.get_note_length(), loop=clip.get_loop(), controls=clip.get_controls(),
    )


def hand_written_clips():
    """Return clips of every kind of position, at each length a clip can be set to, held as objects."""
    return [Clip(notes=EVERY_KIND, scale=C_MAJOR, length=length, note_length=SIXTEENTH, controls=CONTROLS) for length in CLIP_LENGTHS]


class BothWays(unittest.TestCase):
    """Checks that two clips holding the same positions, one as objects and one as sounds, answer everything the same."""

    def assertSameClip(self, *, first, second):
        """Check two clips list the same sounds, last as long and send the same CC values."""
        self.assertEqual(first.get_sounds(), second.get_sounds())
        self.assertEqual(first.total_length(), second.total_length())
        self.assertEqual(
            [(control.get_time(), control.get_number(), control.get_value()) for control in first.get_controls()],
            [(control.get_time(), control.get_number(), control.get_value()) for control in second.get_controls()],
        )

    def assertAnswersTheSame(self, *, as_notes, as_sounds, scale, section_ends):
        self.assertEqual(as_notes.get_sounds(), as_sounds.get_sounds())
        self.assertEqual(as_notes.resolved_sounds(), as_sounds.resolved_sounds())
        self.assertEqual(as_notes.played_sounds(), as_sounds.played_sounds())
        self.assertEqual(as_notes.total_length(), as_sounds.total_length())
        self.assertEqual(timed_events(clip=as_notes, scale=scale), timed_events(clip=as_sounds, scale=scale))
        for start, end in section_ends:
            with self.subTest(start=start, end=end):
                self.assertSameClip(first=as_notes.section(start=start, end=end), second=as_sounds.section(start=start, end=end))
                self.assertEqual(as_sounds.section(start=start, end=end).total_length(), end - start)
        self.assertSameClip(first=as_notes.repeated(REPEATS), second=as_sounds.repeated(REPEATS))
        # The objects are asked for last, since a clip of sounds keeps objects from then on.
        self.assertEqual(as_notes.resolved_notes(), as_sounds.resolved_notes())
        self.assertEqual(as_notes.played_notes(), as_sounds.played_notes())
        self.assertEqual(as_notes.get_notes(), as_sounds.get_notes())


class TestAHandWrittenClipBothWays(BothWays):

    def test_a_clip_of_every_kind_of_position_answers_the_same_both_ways(self):
        for clip in hand_written_clips():
            with self.subTest(length=clip.get_length()):
                self.assertAnswersTheSame(as_notes=clip, as_sounds=held_as_sounds(clip), scale=C_MAJOR, section_ends=SECTION_ENDS)

    def test_a_missing_length_with_no_note_length_is_refused_in_the_same_words_both_ways(self):
        for position in [NO_LENGTH_NOTE, NO_LENGTH_DEGREE, Chord([C4, NO_LENGTH_NOTE]), Held(sound=phrase([C4, NO_LENGTH_NOTE]), length=EIGHTH)]:
            as_notes = Clip(notes=[C4, position])
            for clip in [as_notes, held_as_sounds(as_notes)]:
                for ask in [clip.resolved_notes, clip.resolved_sounds, clip.total_length, clip.played_sounds]:
                    with self.subTest(position=position, ask=ask.__name__), self.assertRaises(ValueError) as refused:
                        ask()
                    self.assertEqual(str(refused.exception), ERR_NO_LENGTH.format(position=NO_LENGTH_NOTE if position is not NO_LENGTH_DEGREE else NO_LENGTH_DEGREE))


class TestWhatAClipHolds(unittest.TestCase):

    def test_a_clip_given_notes_says_them_as_sounds(self):
        clip = Clip(notes=[C4, Rest(EIGHTH)])
        self.assertEqual(clip.get_sounds(), [Sound.of(C4), Sound.of(Rest(EIGHTH))])
        self.assertEqual(clip.get_notes(), [C4, Rest(EIGHTH)])

    def test_a_clip_given_sounds_says_them_as_notes(self):
        clip = Clip(sounds=[Sound.of(C4), Sound.of(Rest(EIGHTH))])
        self.assertEqual(clip.get_sounds(), [Sound.of(C4), Sound.of(Rest(EIGHTH))])
        self.assertEqual(clip.get_notes(), [C4, Rest(EIGHTH)])

    def test_a_note_appended_to_a_clip_of_sounds_is_part_of_the_clip(self):
        clip = Clip(sounds=[Sound.of(C4)])
        clip.get_notes().append(E4)
        self.assertEqual(clip.get_notes(), [C4, E4])
        self.assertEqual(clip.get_sounds(), [Sound.of(C4), Sound.of(E4)])
        self.assertEqual(clip.total_length(), QUARTER + EIGHTH)

    def test_a_note_appended_to_a_clip_of_notes_is_part_of_the_clip(self):
        clip = Clip(notes=[C4])
        clip.get_notes().append(E4)
        self.assertEqual(clip.get_sounds(), [Sound.of(C4), Sound.of(E4)])
        self.assertEqual(clip.total_length(), QUARTER + EIGHTH)

    def test_the_list_of_notes_is_the_clips_own_both_ways(self):
        for clip in [Clip(notes=[C4]), Clip(sounds=[Sound.of(C4)])]:
            with self.subTest(clip=clip):
                self.assertIs(clip.get_notes(), clip.get_notes())

    def test_printing_a_clip_of_sounds_leaves_it_holding_its_sounds(self):
        sounds = [Sound.of(C4)]
        clip = Clip(sounds=sounds)
        self.assertIn(repr(Sound.position(sounds[0])), repr(clip))
        self.assertIs(clip.get_sounds(), sounds)

    def test_setting_notes_on_a_clip_of_sounds_replaces_the_sounds(self):
        clip = Clip(sounds=[Sound.of(C4)])
        clip.set_notes([E4])
        self.assertEqual(clip.get_sounds(), [Sound.of(E4)])

    def test_whether_a_clip_lists_anything(self):
        for clip, expected in [(Clip(), False), (Clip(sounds=[]), False), (Clip(notes=[C4]), True), (Clip(sounds=[Sound.of(C4)]), True)]:
            with self.subTest(clip=clip):
                self.assertEqual(clip.has_positions(), expected)

    def test_something_appended_that_is_no_position_is_refused_when_the_sounds_are_asked_for(self):
        clip = Clip(notes=[C4])
        clip.get_notes().append(NoteName.C)
        with self.assertRaises(ValueError):
            clip.get_sounds()


class TestEveryExampleBothWays(BothWays):
    """Every clip a render makes holds sounds, and its twin made of the same positions as objects answers the same."""

    def test_every_clip_of_every_example_answers_the_same_both_ways(self):
        clips = 0
        for path in EXAMPLE_PATHS:
            grid = render_file(path)
            for row in grid.get_rows():
                for column in grid.get_columns():
                    clip = grid.get_clip(row=row, column=column)
                    if clip is None:
                        continue
                    clips += 1
                    length = clip.total_length()
                    ends = [(0, length / 3), (length / 3, length), (length / 2, length * 2)]
                    with self.subTest(path=path, row=row.get_name(), column=column.get_name()):
                        self.assertAnswersTheSame(
                            as_notes=held_as_notes(clip), as_sounds=held_as_sounds(clip),
                            scale=grid.scale_at(row=row, column=column), section_ends=ends,
                        )
        self.assertGreater(clips, len(EXAMPLE_PATHS))


if __name__ == '__main__':
    unittest.main()
