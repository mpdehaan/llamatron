# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of a section's lines in the song wizard's choices: each line read as the song has it, and a line given its own breath, early note and notes."""

import unittest

from llamatron.model.file import version
from llamatron.model.schema.file_format import Section
from llamatron.wizards.create_song import line_edits, melody, notation, phrasing, wizard_limits
from llamatron.wizards.create_song.wizard_choices import WizardChoices

A_NAME = 'made'
A_SEED = 11
A_GENRE = 'rock'
A_SUBGENRE = 'arena rock'
A_POP_GENRE = 'sixties_pop'
A_VERSE = 1
FIRST = 0
A_LONG_BREATH = 7
UP_TWO = 2
NOT_A_FIELD = 'colour'
NOT_A_LINE = 99


def chosen(*, genre=A_GENRE, subgenre=A_SUBGENRE, plan=None):
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre if genre == A_GENRE else choices.subgenres()[FIRST])
    choices.set_seed(A_SEED)
    if plan is not None:
        choices.set_song_plan(plan)
    return choices


def patterns(choices):
    return choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.PATTERNS]


def notes_of(choices, *, line, place=A_VERSE):
    return choices.section(place).lines()[line][melody.LINE_NOTES]


class TestWizardLines(unittest.TestCase):
    """A section's lines, one by one."""

    __slots__ = ()

    def cases(self):
        return [chosen(plan=True), chosen(plan=False), chosen(genre=A_POP_GENRE)]

    def test_a_section_s_lines_are_read_with_their_player_their_notes_and_whether_they_breathe(self):
        for choices in self.cases():
            lines = choices.section(A_VERSE).lines()
            self.assertTrue(lines)
            for line in lines:
                self.assertEqual(line[wizard_limits.LINE_PLAYER], choices.get_band().tune_player())
                self.assertEqual(line_edits.steps_of(line[melody.LINE_NOTES]) % choices.tune_steps_in_bar(), 0)
                self.assertEqual(line[wizard_limits.LINE_OWN], {})
            # The first line is a new idea, and so breathes; a line that says an idea again does not.
            self.assertTrue(lines[FIRST][wizard_limits.LINE_BREATHES])
            self.assertFalse(all(line[wizard_limits.LINE_BREATHES] for line in lines))

    def test_a_line_s_own_breath_ends_the_line_in_that_rest_and_none_gives_the_breath_back(self):
        for choices in self.cases():
            before = notes_of(choices, line=FIRST)
            usual = patterns(choices)
            eighth = choices.tune_steps_in_bar() // 8
            choices.section(A_VERSE).set_line(line=FIRST, field=phrasing.LINE_BREATH, value=A_LONG_BREATH)
            self.assertEqual(notes_of(choices, line=FIRST)[-1], {notation.REST: A_LONG_BREATH * eighth})
            self.assertNotEqual(patterns(choices), usual)
            choices.section(A_VERSE).set_line(line=FIRST, field=phrasing.LINE_BREATH, value=phrasing.NO_BREATH)
            # With no breath the line is as its writer left it, which may end in a rest of the line's own, shorter than the breath.
            self.assertLess(notes_of(choices, line=FIRST)[-1].get(notation.REST, phrasing.NO_BREATH), A_LONG_BREATH * eighth)
            choices.section(A_VERSE).set_line(line=FIRST, field=phrasing.LINE_BREATH, value=None)
            self.assertEqual(notes_of(choices, line=FIRST), before)
            self.assertEqual(patterns(choices), usual)

    def test_a_line_s_early_note_is_switched_for_the_line_alone(self):
        for choices in self.cases():
            both = []
            for early in (True, False):
                choices.section(A_VERSE).set_line(line=FIRST, field=phrasing.LINE_EARLY, value=early)
                self.assertEqual(choices.section(A_VERSE).lines()[FIRST][wizard_limits.LINE_OWN], {phrasing.LINE_EARLY: early})
                both.append(notes_of(choices, line=FIRST))
            self.assertNotEqual(both[0], both[1])

    def test_a_line_s_own_notes_are_the_line_and_the_idea_wherever_the_section_says_the_idea_again(self):
        for choices in self.cases():
            lines = choices.section(A_VERSE).lines()
            written = line_edits.moved(line=lines[FIRST][melody.LINE_NOTES], step=0, by=UP_TWO)
            choices.section(A_VERSE).set_line(line=FIRST, field=melody.LINE_NOTES, value=written)
            after = choices.section(A_VERSE).lines()
            self.assertEqual([line_edits.place_of(note) for note in after[FIRST][melody.LINE_NOTES] if not line_edits.is_rest(note)],
                             [line_edits.place_of(note) for note in written if not line_edits.is_rest(note)])
            self.assertFalse(after[FIRST][wizard_limits.LINE_BREATHES])
            # A line of another idea is as it was.
            unchanged = [count for count, line in enumerate(lines) if line[wizard_limits.LINE_BREATHES] and count != FIRST]
            for count in unchanged:
                self.assertEqual(after[count][melody.LINE_NOTES], lines[count][melody.LINE_NOTES])
            again = WizardChoices.from_data(choices.to_data())
            self.assertEqual(again.section(A_VERSE).lines(), after)
            self.assertEqual(patterns(again), patterns(choices))
            choices.section(A_VERSE).set_line(line=FIRST, field=melody.LINE_NOTES, value=None)
            self.assertEqual(choices.section(A_VERSE).lines(), lines)

    def test_what_a_line_cannot_take_is_refused(self):
        choices = chosen()
        notes = notes_of(choices, line=FIRST)
        refused = [dict(line=NOT_A_LINE, field=phrasing.LINE_BREATH, value=1), dict(line=FIRST, field=NOT_A_FIELD, value=1), dict(line=FIRST, field=phrasing.LINE_BREATH, value=phrasing.LONGEST_BREATH + 1),
                   dict(line=FIRST, field=phrasing.LINE_BREATH, value=True), dict(line=FIRST, field=phrasing.LINE_EARLY, value=1), dict(line=FIRST, field=melody.LINE_NOTES, value=notes[:1]),
                   dict(line=FIRST, field=melody.LINE_NOTES, value=NOT_A_FIELD)]
        for given in refused:
            with self.subTest(given=given):
                with self.assertRaises(ValueError):
                    choices.section(A_VERSE).set_line(**given)
        self.assertEqual(notes_of(choices, line=FIRST), notes)
