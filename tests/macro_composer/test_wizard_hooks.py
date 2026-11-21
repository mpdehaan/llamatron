# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of a song's hooks: the main hook placed among its chorus's lines, and the second hook, a tag sung in another kind of section."""

import unittest

from llamatron.macro_composer import arranger, melody, notation, wizard_limits
from llamatron.macro_composer.arranger import arranged
from llamatron.macro_composer.melody import placement_of, plan_with_hook_placed, plan_with_tag
from llamatron.macro_composer.wizard_choices import WizardChoices
from llamatron.model.schema.file_format import SectionKind
from llamatron.user_strings import macro_composer as composer_text

A_NAME = 'made'
A_SEED = 5
A_GENRE = 'rock'
A_SUBGENRE_WITH_A_PRE_CHORUS = 'arena rock'
A_SUBGENRE = 'folk rock'
A_GENRE_WITH_NO_CHORUS_HOOK = 'blues'
NOT_A_PLACEMENT = 'in the middle'
A_HOOK = {melody.LINE: melody.HOOK, melody.HOOK: True, melody.HIGHER: True}
A_CHORUS = [dict(A_HOOK), {**A_HOOK, melody.VARIED: True}, dict(A_HOOK), {melody.LINE: melody.CLOSE_LINE}]
A_PLAN_OF_NO_NAMED_SHAPE = [{melody.LINE: 'a'}, dict(A_HOOK), {melody.LINE: 'a'}, dict(A_HOOK)]
A_SHORT_PLAN = [{melody.LINE: 'p'}, {melody.LINE: 'p', melody.VARIED: True, melody.ANSWER: True}]
LINES = 'lines'
STRESS = 'stress'
OCTAVE = 'octave'
DEGREE = 'degree'


def chosen(*, subgenre=A_SUBGENRE_WITH_A_PRE_CHORUS):
    choices = WizardChoices()
    choices.set_genre(A_GENRE)
    choices.set_subgenre(subgenre)
    choices.set_seed(A_SEED)
    return choices


def parts(choices):
    return arranged(style=choices.style(), song=choices.song_picks(A_NAME))[arranger.PARTS]


def marked(plan):
    return [bool(entry.get(melody.HOOK)) for entry in plan]


class TestHookPlaced(unittest.TestCase):

    def test_a_plans_placement_is_named_by_which_of_its_four_lines_are_the_hook(self):
        self.assertEqual(placement_of(A_CHORUS), melody.FIRST_LINES)
        self.assertIsNone(placement_of(A_PLAN_OF_NO_NAMED_SHAPE))
        self.assertIsNone(placement_of(A_SHORT_PLAN))

    def test_each_placement_puts_the_hook_on_its_lines_and_placing_again_gives_the_first_back(self):
        last = plan_with_hook_placed(plan=A_CHORUS, placement=melody.LAST_LINE)
        self.assertEqual(marked(last), [False, False, False, True])
        both = plan_with_hook_placed(plan=A_CHORUS, placement=melody.FIRST_AND_LAST)
        self.assertEqual(marked(both), [True, False, False, True])
        for placed in (last, both):
            self.assertEqual(placement_of(plan_with_hook_placed(plan=placed, placement=melody.FIRST_LINES)), melody.FIRST_LINES)

    def test_the_lines_that_are_no_hook_are_never_lifted_so_that_the_hook_keeps_the_top(self):
        for placement in melody.PLACEMENTS:
            for entry in plan_with_hook_placed(plan=A_CHORUS, placement=placement):
                self.assertEqual(bool(entry.get(melody.HIGHER)), bool(entry.get(melody.HOOK)))

    def test_a_plan_of_another_shape_and_a_placement_nobody_named_leave_the_plan_as_it_is(self):
        self.assertEqual(plan_with_hook_placed(plan=A_PLAN_OF_NO_NAMED_SHAPE, placement=melody.LAST_LINE), A_PLAN_OF_NO_NAMED_SHAPE)
        self.assertEqual(plan_with_hook_placed(plan=A_CHORUS, placement=NOT_A_PLACEMENT), A_CHORUS)
        self.assertEqual(plan_with_hook_placed(plan=A_CHORUS, placement=melody.FIRST_LINES), A_CHORUS)

    def test_a_tag_takes_the_last_line_of_a_plan_and_fills_a_section_that_has_no_lines(self):
        tagged = plan_with_tag(plan=A_SHORT_PLAN, lines=2)
        self.assertEqual(tagged[0], A_SHORT_PLAN[0])
        self.assertEqual(tagged[-1], {melody.LINE: melody.TAG_LINE, melody.TAG: True, melody.ANSWER: True})
        self.assertEqual(plan_with_tag(plan=[], lines=3), [{melody.LINE: melody.TAG_LINE, melody.TAG: True}] * 3)


class TestWizardHookPlacement(unittest.TestCase):

    def test_a_chorus_of_a_named_shape_offers_every_placement_and_starts_at_the_genres(self):
        choices = chosen()
        self.assertEqual(choices.get_hook().hook_placements_offered(), list(melody.PLACEMENTS))
        self.assertEqual(choices.get_hook().get_hook_placement(), choices.get_hook().genre_hook_placement())
        self.assertEqual(choices.get_hook().genre_hook_placement(), melody.FIRST_LINES)

    def test_a_genre_whose_hook_is_no_choruss_offers_no_placement(self):
        choices = WizardChoices()
        choices.set_genre(A_GENRE_WITH_NO_CHORUS_HOOK)
        choices.set_subgenre(choices.subgenres()[0])
        self.assertEqual(choices.get_hook().hook_placements_offered(), [])

    def test_a_placement_moves_the_hook_line_changes_the_chorus_and_is_kept(self):
        choices = chosen()
        before = parts(choices)
        first_notes = choices.get_hook().hook_notes()
        choices.get_hook().set_hook_placement(melody.LAST_LINE)
        self.assertEqual(choices.get_hook().hook_line_place(), (SectionKind.CHORUS, 4))
        self.assertNotEqual(parts(choices), before)
        self.assertEqual(choices.get_hook().hook_notes()[0], first_notes[0])
        self.assertEqual(WizardChoices.from_data(choices.to_data()).get_hook().get_hook_placement(), melody.LAST_LINE)
        choices.get_hook().set_hook_placement(melody.FIRST_LINES)
        self.assertEqual(parts(choices), before)
        self.assertEqual(choices.get_hook().hook_line_place(), (SectionKind.CHORUS, 1))

    def test_a_placement_nobody_offers_is_refused(self):
        with self.assertRaises(ValueError):
            chosen().get_hook().set_hook_placement(NOT_A_PLACEMENT)


class TestWizardSecondHook(unittest.TestCase):

    def tag_part(self, *, choices, kind):
        made = parts(choices)
        name = next(name for name in made if name.startswith(kind) and name.endswith(choices.get_band().tune_player()))
        return made[name]

    def test_a_song_has_no_second_hook_until_given_one_and_offers_the_kinds_its_form_has(self):
        choices = chosen()
        self.assertFalse(choices.get_hook().has_second_hook())
        self.assertEqual(choices.get_hook().second_hook_kinds(), [SectionKind.PRE_CHORUS])
        plain = chosen(subgenre=A_SUBGENRE)
        self.assertEqual(plain.get_hook().second_hook_kinds(), [])
        plain.get_song_form().set_end(wizard_limits.OUTRO_THEN_CHORD)
        self.assertEqual(plain.get_hook().second_hook_kinds(), [wizard_limits.OUTRO_KIND])

    def test_a_second_hook_in_the_pre_chorus_is_its_last_line_the_same_bar_twice_and_changes_no_other_section(self):
        choices = chosen()
        before = parts(choices)
        choices.get_hook().set_second_hook(SectionKind.PRE_CHORUS)
        made = parts(choices)
        self.assertEqual([name for name in made if made[name] != before.get(name)], [composer_text.MSG_PART_OF_SECTION.format(SectionKind.PRE_CHORUS, choices.get_band().tune_player())])
        tag = self.tag_part(choices=choices, kind=SectionKind.PRE_CHORUS)[LINES][-1]
        heard = [{field: value for field, value in note.items() if field != STRESS} for note in tag]
        self.assertEqual(heard[:len(heard) // 2], heard[len(heard) // 2:])
        self.assertTrue(any(notation.REST in note for note in tag))

    def test_a_second_hook_in_the_outro_has_the_melodys_player_play_there_every_line_the_tag(self):
        choices = chosen(subgenre=A_SUBGENRE)
        choices.get_song_form().set_end(wizard_limits.OUTRO_THEN_CHORD)
        choices.get_hook().set_second_hook(wizard_limits.OUTRO_KIND)
        lines = self.tag_part(choices=choices, kind=wizard_limits.OUTRO_KIND)[LINES]
        self.assertTrue(all(line == lines[0] for line in lines))
        self.assertNotIn(choices.get_band().tune_player(), choices.style()[arranger.SECTIONS][wizard_limits.OUTRO_KIND][arranger.PLAYS])

    def test_the_tags_top_is_under_the_main_hooks(self):
        choices = chosen()
        choices.get_hook().set_second_hook(SectionKind.PRE_CHORUS)
        tag = self.tag_part(choices=choices, kind=SectionKind.PRE_CHORUS)
        chorus = self.tag_part(choices=choices, kind=SectionKind.CHORUS)

        def top(lines):
            return max((note.get(OCTAVE, 0), note[DEGREE]) for line in lines for note in line if notation.REST not in note)
        self.assertLess(top(tag[LINES][-1:]), top(chorus[LINES][:1]))

    def test_another_second_hook_is_another_tag_and_the_song_is_kept_with_it(self):
        choices = chosen()
        choices.get_hook().set_second_hook(SectionKind.PRE_CHORUS)
        first = self.tag_part(choices=choices, kind=SectionKind.PRE_CHORUS)
        choices.get_hook().new_second_hook()
        self.assertNotEqual(self.tag_part(choices=choices, kind=SectionKind.PRE_CHORUS), first)
        kept = WizardChoices.from_data(choices.to_data())
        self.assertEqual(kept.get_hook().get_second_hook_kind(), SectionKind.PRE_CHORUS)
        self.assertEqual(kept.get_hook().get_second_hook_take(), choices.get_hook().get_second_hook_take())
        self.assertEqual(parts(kept), parts(choices))

    def test_taking_the_second_hook_away_gives_the_song_back_and_a_kind_not_offered_is_refused(self):
        choices = chosen()
        before = parts(choices)
        choices.get_hook().set_second_hook(SectionKind.PRE_CHORUS)
        choices.get_hook().set_second_hook(None)
        self.assertEqual(parts(choices), before)
        with self.assertRaises(ValueError):
            choices.get_hook().set_second_hook(SectionKind.BRIDGE)
        with self.assertRaises(ValueError):
            choices.get_hook().new_second_hook()

    def test_a_song_with_a_second_hook_is_made(self):
        choices = chosen()
        choices.get_hook().set_second_hook(SectionKind.PRE_CHORUS)
        choices.made_for_listening()
