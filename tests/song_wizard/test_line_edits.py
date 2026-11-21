# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of a tune's line edited by hand (song_wizard/line_edits.py), and of a hook whose notes a person wrote in the wizard's choices."""

import unittest

from llamatron.model.file import version
from llamatron.model.schema.file_format import Section
from llamatron.song_wizard import line_edits, notation
from llamatron.song_wizard.line_edits import found, moved, place_of, steps_of, stretched, tidied, toggled
from llamatron.song_wizard.wizard_choices import WizardChoices

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
NOT_LINES = ('tune', [{notation.DEGREE: 9, notation.STEPS: 16}], [{notation.DEGREE: 1, notation.STEPS: 4}], [{notation.REST: 16}], [{notation.DEGREE: 1, notation.STEPS: 0}, {notation.DEGREE: 1, notation.STEPS: 16}], [{notation.DEGREE: True, notation.STEPS: 16}])


def a_line():
    """Two notes, a rest of three steps and a note: eight steps."""
    return [{notation.DEGREE: 3, notation.STEPS: 2, notation.STRESS: notation.ARRIVAL}, {notation.DEGREE: 7, notation.ACCIDENTAL: notation.SHARP, notation.STEPS: 2}, {notation.REST: 2}, {notation.DEGREE: 1, notation.OCTAVE: 1, notation.STEPS: 2}]


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
        self.assertEqual(up[1], {notation.DEGREE: 1, notation.OCTAVE: 1, notation.STEPS: 2})
        self.assertEqual(place_of(moved(line=a_line(), step=FIRST_STEP, by=DOWN)[0]), place_of(a_line()[0]) + DOWN)
        # What else a note holds stays with the note.
        self.assertEqual(moved(line=a_line(), step=FIRST_STEP, by=UP)[0][notation.STRESS], notation.ARRIVAL)
        below = moved(line=a_line(), step=FIRST_STEP, by=-line_edits.NOTES_IN_SCALE)[0]
        self.assertEqual((below[notation.DEGREE], below[notation.OCTAVE]), (3, -1))

    def test_a_note_stops_at_the_highest_and_lowest_places_and_a_rest_does_not_move(self):
        self.assertEqual(place_of(moved(line=a_line(), step=FIRST_STEP, by=FAR)[0]), line_edits.HIGHEST_PLACE)
        self.assertEqual(place_of(moved(line=a_line(), step=FIRST_STEP, by=-FAR)[0]), line_edits.LOWEST_PLACE)
        self.assertEqual(moved(line=a_line(), step=A_STEP_IN_THE_REST, by=UP), a_line())

    def test_a_note_stretches_into_the_rest_after_it_and_never_into_a_note(self):
        longer = stretched(line=a_line(), step=2, by=UP)
        self.assertEqual((longer[1][notation.STEPS], longer[2]), (3, {notation.REST: 1}))
        twice = stretched(line=longer, step=2, by=UP)
        self.assertEqual([note.get(notation.STEPS) for note in twice], [2, 4, 2])
        self.assertEqual(stretched(line=a_line(), step=FIRST_STEP, by=UP), a_line())
        self.assertEqual(stretched(line=a_line(), step=THE_LAST_NOTE_S_STEP, by=UP), a_line())

    def test_a_note_shrinks_to_one_step_leaving_a_rest_that_joins_the_rest_after(self):
        shorter = stretched(line=a_line(), step=2, by=DOWN)
        self.assertEqual((shorter[1][notation.STEPS], shorter[2]), (1, {notation.REST: 3}))
        self.assertEqual(stretched(line=shorter, step=2, by=DOWN), shorter)

    def test_a_note_is_taken_out_and_one_is_put_in_at_the_place_of_the_note_before(self):
        without = toggled(line=a_line(), step=2)
        self.assertEqual(without[1], {notation.REST: 4})
        put = toggled(line=a_line(), step=A_STEP_IN_THE_REST)
        self.assertEqual(put[2:5], [{notation.REST: 1}, {notation.DEGREE: 7, notation.STEPS: 1}, {notation.DEGREE: 1, notation.OCTAVE: 1, notation.STEPS: 2}])
        # With no note before, the note after gives the place; with none at all, the scale's first note.
        first = toggled(line=[{notation.REST: 2}, {notation.DEGREE: 5, notation.STEPS: 2}], step=FIRST_STEP)
        self.assertEqual(first[0], {notation.DEGREE: 5, notation.STEPS: 1})
        self.assertEqual(toggled(line=[{notation.REST: 2}], step=1), [{notation.REST: 1}, {notation.DEGREE: 1, notation.STEPS: 1}])

    def test_every_edit_keeps_the_line_s_length_and_leaves_the_line_given_alone(self):
        line = a_line()
        for step in range(steps_of(line)):
            for edited in (moved(line=line, step=step, by=UP), stretched(line=line, step=step, by=UP), stretched(line=line, step=step, by=DOWN), toggled(line=line, step=step)):
                self.assertEqual(steps_of(edited), steps_of(line))
        self.assertEqual(line, a_line())
        self.assertEqual(tidied([{notation.REST: 1}, {notation.REST: 2}, {notation.DEGREE: 1, notation.STEPS: 0}, {notation.REST: 1}]), [{notation.REST: 4}])


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
        return choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.PATTERNS]

    def test_the_wizard_s_own_line_written_back_is_the_same_hook_and_the_same_song(self):
        choices = self.chosen()
        before = self.made(choices)
        notes = choices.get_hook().hook_notes()
        self.assertFalse(choices.get_hook().hook_is_own())
        choices.get_hook().set_hook_line(choices.get_hook().hook_line())
        self.assertTrue(choices.get_hook().hook_is_own())
        self.assertEqual(choices.get_hook().hook_notes(), notes)
        self.assertEqual(self.made(choices), before)

    def test_an_edited_line_is_the_hook_everywhere_the_hook_is_said_and_none_gives_it_back(self):
        choices = self.chosen()
        before = self.made(choices)
        notes = choices.get_hook().hook_notes()
        edited = line_edits.moved(line=choices.get_hook().hook_line(), step=FIRST_STEP, by=UP)
        choices.get_hook().set_hook_line(edited)
        self.assertEqual(choices.get_hook().hook_line(), edited)
        self.assertNotEqual(choices.get_hook().hook_notes(), notes)
        # The first note alone moved, to the next note of the scale.
        self.assertEqual(choices.get_hook().hook_notes()[2][1:], notes[2][1:])
        self.assertEqual(choices.get_hook().hook_notes()[2][0][2], choices.get_hook().pitch_of_place(place_of(edited[0])))
        self.assertNotEqual(self.made(choices), before)
        again = WizardChoices.from_data(choices.to_data())
        self.assertTrue(again.get_hook().hook_is_own())
        self.assertEqual(self.made(again), self.made(choices))
        choices.get_hook().set_hook_line(None)
        self.assertFalse(choices.get_hook().hook_is_own())
        self.assertEqual(self.made(choices), before)

    def test_notes_written_by_hand_stay_through_a_new_take_a_chosen_kind_and_the_plan_switched_off(self):
        choices = self.chosen()
        edited = line_edits.moved(line=choices.get_hook().hook_line(), step=FIRST_STEP, by=UP)
        choices.get_hook().set_hook_line(edited)
        choices.get_hook().new_hook()
        self.assertEqual(choices.get_hook().hook_line(), edited)
        choices.set_song_plan(False)
        self.assertEqual(choices.get_hook().hook_line(), edited)

    def test_a_line_that_is_not_one_is_refused_and_the_hook_stays(self):
        choices = self.chosen()
        notes = choices.get_hook().hook_notes()
        for refused in NOT_LINES:
            with self.assertRaises(ValueError):
                choices.get_hook().set_hook_line(refused)
        self.assertEqual(choices.get_hook().hook_notes(), notes)
        self.assertFalse(choices.get_hook().hook_is_own())

    def test_a_song_with_no_hook_has_no_line_to_write(self):
        choices = self.chosen()
        choices.get_hook().set_hook(False)
        self.assertIsNone(choices.get_hook().hook_line())
        with self.assertRaises(ValueError):
            choices.get_hook().set_hook_line([{notation.DEGREE: 1, notation.STEPS: 16}])
