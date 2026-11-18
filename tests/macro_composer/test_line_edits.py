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

"""Tests of a tune's line edited by hand (macro_composer/line_edits.py), and of a hook whose notes a person wrote in the wizard's choices."""

import unittest

from llamatron.composition.file_format import Section
from llamatron.macro_composer import line_edits
from llamatron.macro_composer.line_edits import HIGHEST_PLACE, LOWEST_PLACE, NOTES_IN_SCALE, found, moved, place_of, steps_of, stretched, tidied, toggled
from llamatron.macro_composer.notation import ACCIDENTAL, DEGREE, OCTAVE, REST, SHARP, STEPS, STRESS, ARRIVAL
from llamatron.macro_composer.wizard_choices import WizardChoices
from llamatron.support.version import VERSION

A_NAME = 'made'
A_SEED = 11
A_GENRE = 'rock'
A_SUBGENRE = 'arena rock'
UP = 1
DOWN = -1
FAR = 100
FIRST_STEP = 0
A_STEP_IN_THE_REST = 5
THE_LAST_NOTE_S_STEP = 6
NOT_LINES = ('tune', [{DEGREE: 9, STEPS: 16}], [{DEGREE: 1, STEPS: 4}], [{REST: 16}], [{DEGREE: 1, STEPS: 0}, {DEGREE: 1, STEPS: 16}], [{DEGREE: True, STEPS: 16}])


def a_line():
    """Two notes, a rest of three steps and a note: eight steps."""
    return [{DEGREE: 3, STEPS: 2, STRESS: ARRIVAL}, {DEGREE: 7, ACCIDENTAL: SHARP, STEPS: 2}, {REST: 2}, {DEGREE: 1, OCTAVE: 1, STEPS: 2}]


class TestLineEdits(unittest.TestCase):
    """Each edit of a line, which is as long after as before."""

    __slots__ = ()

    def test_a_step_is_found_inside_its_note_and_past_the_end_is_refused(self):
        self.assertEqual(found(line=a_line(), step=3), (1, 2))
        self.assertEqual(found(line=a_line(), step=A_STEP_IN_THE_REST), (2, 4))
        with self.assertRaises(IndexError):
            found(line=a_line(), step=steps_of(a_line()))

    def test_a_note_moves_along_the_scale_through_the_octave_and_loses_its_sharp(self):
        up = moved(line=a_line(), step=2, by=UP)
        self.assertEqual(up[1], {DEGREE: 1, OCTAVE: 1, STEPS: 2})
        self.assertEqual(place_of(moved(line=a_line(), step=FIRST_STEP, by=DOWN)[0]), place_of(a_line()[0]) + DOWN)
        # What else a note holds stays with the note.
        self.assertEqual(moved(line=a_line(), step=FIRST_STEP, by=UP)[0][STRESS], ARRIVAL)
        below = moved(line=a_line(), step=FIRST_STEP, by=-NOTES_IN_SCALE)[0]
        self.assertEqual((below[DEGREE], below[OCTAVE]), (3, -1))

    def test_a_note_stops_at_the_highest_and_lowest_places_and_a_rest_does_not_move(self):
        self.assertEqual(place_of(moved(line=a_line(), step=FIRST_STEP, by=FAR)[0]), HIGHEST_PLACE)
        self.assertEqual(place_of(moved(line=a_line(), step=FIRST_STEP, by=-FAR)[0]), LOWEST_PLACE)
        self.assertEqual(moved(line=a_line(), step=A_STEP_IN_THE_REST, by=UP), a_line())

    def test_a_note_stretches_into_the_rest_after_it_and_never_into_a_note(self):
        longer = stretched(line=a_line(), step=2, by=UP)
        self.assertEqual((longer[1][STEPS], longer[2]), (3, {REST: 1}))
        twice = stretched(line=longer, step=2, by=UP)
        self.assertEqual([note.get(STEPS) for note in twice], [2, 4, 2])
        self.assertEqual(stretched(line=a_line(), step=FIRST_STEP, by=UP), a_line())
        self.assertEqual(stretched(line=a_line(), step=THE_LAST_NOTE_S_STEP, by=UP), a_line())

    def test_a_note_shrinks_to_one_step_leaving_a_rest_that_joins_the_rest_after(self):
        shorter = stretched(line=a_line(), step=2, by=DOWN)
        self.assertEqual((shorter[1][STEPS], shorter[2]), (1, {REST: 3}))
        self.assertEqual(stretched(line=shorter, step=2, by=DOWN), shorter)

    def test_a_note_is_taken_out_and_one_is_put_in_at_the_place_of_the_note_before(self):
        without = toggled(line=a_line(), step=2)
        self.assertEqual(without[1], {REST: 4})
        put = toggled(line=a_line(), step=A_STEP_IN_THE_REST)
        self.assertEqual(put[2:5], [{REST: 1}, {DEGREE: 7, STEPS: 1}, {DEGREE: 1, OCTAVE: 1, STEPS: 2}])
        # With no note before, the note after gives the place; with none at all, the scale's first note.
        first = toggled(line=[{REST: 2}, {DEGREE: 5, STEPS: 2}], step=FIRST_STEP)
        self.assertEqual(first[0], {DEGREE: 5, STEPS: 1})
        self.assertEqual(toggled(line=[{REST: 2}], step=1), [{REST: 1}, {DEGREE: 1, STEPS: 1}])

    def test_every_edit_keeps_the_line_s_length_and_leaves_the_line_given_alone(self):
        line = a_line()
        for step in range(steps_of(line)):
            for edited in (moved(line=line, step=step, by=UP), stretched(line=line, step=step, by=UP), stretched(line=line, step=step, by=DOWN), toggled(line=line, step=step)):
                self.assertEqual(steps_of(edited), steps_of(line))
        self.assertEqual(line, a_line())
        self.assertEqual(tidied([{REST: 1}, {REST: 2}, {DEGREE: 1, STEPS: 0}, {REST: 1}]), [{REST: 4}])


class TestWizardHookNotes(unittest.TestCase):
    """The hook's notes written by hand in the wizard's choices."""

    __slots__ = ()

    def chosen(self):
        choices = WizardChoices()
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        choices.set_seed(A_SEED)
        return choices

    def made(self, choices):
        """The music of the song made: its patterns."""
        return choices.made_setlist(name=A_NAME, version=VERSION).to_data()[Section.PATTERNS]

    def test_the_wizard_s_own_line_written_back_is_the_same_hook_and_the_same_song(self):
        choices = self.chosen()
        before = self.made(choices)
        notes = choices.hook_notes()
        self.assertFalse(choices.hook_is_own())
        choices.set_hook_line(choices.hook_line())
        self.assertTrue(choices.hook_is_own())
        self.assertEqual(choices.hook_notes(), notes)
        self.assertEqual(self.made(choices), before)

    def test_an_edited_line_is_the_hook_everywhere_the_hook_is_said_and_none_gives_it_back(self):
        choices = self.chosen()
        before = self.made(choices)
        notes = choices.hook_notes()
        edited = line_edits.moved(line=choices.hook_line(), step=FIRST_STEP, by=UP)
        choices.set_hook_line(edited)
        self.assertEqual(choices.hook_line(), edited)
        self.assertNotEqual(choices.hook_notes(), notes)
        # The first note alone moved, to the next note of the scale.
        self.assertEqual(choices.hook_notes()[2][1:], notes[2][1:])
        self.assertEqual(choices.hook_notes()[2][0][2], choices.pitch_of_place(place_of(edited[0])))
        self.assertNotEqual(self.made(choices), before)
        again = WizardChoices.from_data(choices.to_data())
        self.assertTrue(again.hook_is_own())
        self.assertEqual(self.made(again), self.made(choices))
        choices.set_hook_line(None)
        self.assertFalse(choices.hook_is_own())
        self.assertEqual(self.made(choices), before)

    def test_notes_written_by_hand_stay_through_a_new_take_a_chosen_kind_and_the_plan_switched_off(self):
        choices = self.chosen()
        edited = line_edits.moved(line=choices.hook_line(), step=FIRST_STEP, by=UP)
        choices.set_hook_line(edited)
        choices.new_hook()
        self.assertEqual(choices.hook_line(), edited)
        choices.set_song_plan(False)
        self.assertEqual(choices.hook_line(), edited)

    def test_a_line_that_is_not_one_is_refused_and_the_hook_stays(self):
        choices = self.chosen()
        notes = choices.hook_notes()
        for refused in NOT_LINES:
            with self.assertRaises(ValueError):
                choices.set_hook_line(refused)
        self.assertEqual(choices.hook_notes(), notes)
        self.assertFalse(choices.hook_is_own())

    def test_a_song_with_no_hook_has_no_line_to_write(self):
        choices = self.chosen()
        choices.set_hook(False)
        self.assertIsNone(choices.hook_line())
        with self.assertRaises(ValueError):
            choices.set_hook_line([{DEGREE: 1, STEPS: 16}])
