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

"""The song wizard's page on a planned song: the plan's fields on the Form panel and the hook's kind on the Hooks panel."""

from llamatron.composition.limits import MAX_NAME_LENGTH
from llamatron.macro_composer import hook_kinds, phrasing
from llamatron.macro_composer.arranger import CHORDS
from llamatron.macro_composer.joins import LEAVES
from llamatron.macro_composer.song_plan import ENERGY, FADES, RISES, ROOT_OF_PLACE, TEMPO_END_OF_PLACE, TYPE_OF_PLACE
from llamatron.macro_composer.wizard_choices import DRUM_SOLO_KIND, chords_as_text
from llamatron.strings.errors import ERR_WIZARD_CHORDS
from llamatron.macro_composer.song_plan import USUAL_CONTRAST
from llamatron.strings.labels import MSG_WIZARD_GROUP_HOOK_KIND, MSG_WIZARD_GROUP_HARMONY, MSG_WIZARD_GROUP_JOINS, MSG_WIZARD_GROUP_PLAYERS, MSG_WIZARD_GROUP_SHAPE, MSG_WIZARD_GROUP_TUNE
from llamatron.strings.marks import MSG_SECTION_SET
from llamatron.strings.labels import (
    MSG_WIZARD_CONTRAST_LABEL, MSG_WIZARD_FORM_BRANCH, MSG_WIZARD_FORM_QUESTION_TITLES, MSG_WIZARD_FORM_QUESTIONS_BUTTON, MSG_WIZARD_REPLACE_SECTIONS_TITLE, MSG_WIZARD_HOOK_PART_LABELS, MSG_WIZARD_HOOKS_BRANCH, MSG_WIZARD_MELODY_BRANCH, MSG_WIZARD_PHRASING_LABEL, MSG_WIZARD_PHRASING_WAY_LABELS, MSG_WIZARD_PICK_SHOWN,
    MSG_WIZARD_SECTION_ORIGINS, MSG_WIZARD_SECTION_OWN_LABELS, MSG_WIZARD_SONG_PLAN_LABEL, MSG_WIZARD_VALUE_FROM,
)
from llamatron.tui import keybindings
from llamatron.tui.keys import Key
from tests.support.ui_testing import key_of
from tests.tui.test_tui_wizard import WizardTest

A_PLANNED_GENRE = 'rock'
A_SECTION = 'verse-1'
A_PLACE = 1
SOME_CHORDS = '6 4 1 5'
NOT_A_CHORD = ' x'
A_FEW_WORDS = 20
A_SUBGENRE = 'arena rock'
A_SUBGENRE_IN_SIX = 'rock ballad'
AN_UNPLANNED_GENRE = 'blues'


class TestWizardPlan(WizardTest):
    """The Form panel's Song plan, Contrast and Phrasing, and the Hooks panel's Contour, Rhythm and Detail."""

    async def choose(self, *, genre=A_PLANNED_GENRE, subgenre=A_SUBGENRE):
        choices = self.choices()
        choices.set_genre(genre)
        choices.set_subgenre(subgenre or choices.subgenres()[0])
        await self.press(Key.DOWN, Key.UP)

    async def go_to_hooks(self):
        names = [branch.name() for _, branch in self.wizard().rows()]
        await self.go_to_branch(names.index(MSG_WIZARD_HOOKS_BRANCH))

    async def go_to_melody(self):
        names = [branch.name() for _, branch in self.wizard().rows()]
        await self.go_to_branch(names.index(MSG_WIZARD_MELODY_BRANCH))

    async def switch_plan_on(self):
        """Go into the Form panel's fields, where a genre with a plan has the plan on from the start."""
        await self.go_to_named_branch(MSG_WIZARD_FORM_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)

    async def test_a_genre_with_a_plan_plans_the_song_from_the_start_and_the_switch_takes_the_plan_s_fields_away(self):
        await self.choose()
        await self.switch_plan_on()
        choices = self.choices()
        self.assertTrue(choices.has_song_plan())
        shown = self.text()
        self.assertIn(MSG_WIZARD_CONTRAST_LABEL, shown)
        for said in choices.said_of_sections():
            self.assertIn(said.split('.')[0], shown)
        await self.select_field(MSG_WIZARD_SONG_PLAN_LABEL)
        await self.press(Key.ENTER)
        self.assertFalse(choices.has_song_plan())
        self.assertNotIn(MSG_WIZARD_CONTRAST_LABEL, self.text())
        self.assertTrue(self.wizard().has_choices_to_lose())

    async def test_contrast_steps_and_phrasing_toggles(self):
        await self.choose()
        await self.switch_plan_on()
        await self.select_field(MSG_WIZARD_CONTRAST_LABEL)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.choices().get_contrast(), USUAL_CONTRAST + 1)
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.go_to_melody()
        for label in MSG_WIZARD_PHRASING_WAY_LABELS.values():
            self.assertIn(label, self.text())
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_PHRASING_WAY_LABELS[phrasing.BREATH])
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.choices().phrasing_way(phrasing.BREATH), phrasing.LONG)
        await self.select_field(MSG_WIZARD_PHRASING_WAY_LABELS[phrasing.EARLY_NOTES])
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.choices().phrasing_way(phrasing.EARLY_NOTES), phrasing.USUAL_EARLY + 1)
        await self.select_field(MSG_WIZARD_PHRASING_LABEL)
        await self.press(Key.ENTER)
        self.assertFalse(self.choices().has_phrasing())
        self.assertNotIn(MSG_WIZARD_PHRASING_WAY_LABELS[phrasing.BREATH], self.text())

    async def test_a_genre_with_no_plan_shows_no_switch_and_a_song_in_six_no_phrasing(self):
        await self.choose(genre=AN_UNPLANNED_GENRE, subgenre=None)
        await self.go_to_named_branch(MSG_WIZARD_FORM_BRANCH)
        self.assertNotIn(MSG_WIZARD_SONG_PLAN_LABEL, self.text())
        await self.choose(subgenre=A_SUBGENRE_IN_SIX)
        await self.switch_plan_on()
        self.assertIn(MSG_WIZARD_CONTRAST_LABEL, self.text())
        await self.press(keybindings.WizardPage.TO_TREE)
        await self.go_to_melody()
        self.assertNotIn(MSG_WIZARD_PHRASING_LABEL, self.text())

    async def open_kind(self):
        """Open the Hooks panel's Kind group where it is closed, so that the hook's parts show."""
        wizard = self.wizard()
        if MSG_WIZARD_GROUP_HOOK_KIND not in self.app.open_field_sections:
            wizard.toggle_section(MSG_WIZARD_GROUP_HOOK_KIND)
            await self.press(Key.DOWN, Key.UP)

    async def test_the_hooks_panel_shows_the_kind_only_under_a_plan_and_marks_the_wizard_s_pick(self):
        await self.choose()
        self.choices().set_song_plan(False)
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_hooks()
        for label in MSG_WIZARD_HOOK_PART_LABELS.values():
            self.assertNotIn(label, self.text())
        self.choices().set_song_plan(True)
        self.choices().set_hook_part(part=hook_kinds.CONTOUR, value=hook_kinds.CHANT)
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_hooks()
        await self.open_kind()
        shown = self.text()
        kind = self.choices().hook_kind()
        self.assertIn(hook_kinds.CHANT, shown)
        self.assertNotIn(MSG_WIZARD_PICK_SHOWN.format(value=hook_kinds.CHANT), shown)
        self.assertIn(MSG_WIZARD_PICK_SHOWN.format(value=kind[hook_kinds.RHYTHM]), shown)

    async def test_stepping_a_part_chooses_it_and_the_picture_follows(self):
        await self.choose()
        self.choices().set_song_plan(True)
        self.choices().set_hook_part(part=hook_kinds.CONTOUR, value=hook_kinds.CHANT)
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_hooks()
        before = self.choices().hook_notes()
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_HOOK_PART_LABELS[hook_kinds.CONTOUR])
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.choices().hook_kind()[hook_kinds.CONTOUR], hook_kinds.ARCH)
        self.assertNotEqual(self.choices().hook_notes(), before)

    async def test_a_long_note_shows_no_rhythm_and_no_detail(self):
        await self.choose()
        self.choices().set_song_plan(True)
        self.choices().set_hook_part(part=hook_kinds.CONTOUR, value=hook_kinds.LONG_NOTE)
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_hooks()
        await self.open_kind()
        self.assertIn(MSG_WIZARD_HOOK_PART_LABELS[hook_kinds.CONTOUR], self.text())
        self.assertNotIn(MSG_WIZARD_HOOK_PART_LABELS[hook_kinds.DETAIL], self.text())

THE_GROUPS = (MSG_WIZARD_GROUP_TUNE, MSG_WIZARD_GROUP_HARMONY, MSG_WIZARD_GROUP_SHAPE, MSG_WIZARD_GROUP_JOINS, MSG_WIZARD_GROUP_PLAYERS)


class TestWizardSectionOwnFields(WizardTest):
    """A section's panel on a planned song: what the section is given of its own."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        choices = self.choices()
        choices.set_genre(A_PLANNED_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        choices.set_song_plan(True)
        await self.press(Key.DOWN, Key.UP)
        names = [branch.name() for _, branch in self.wizard().rows()]
        await self.go_to_branch(names.index(A_SECTION))
        await self.press(keybindings.WizardPage.INTO_FIELDS)

    def label(self, field):
        return MSG_WIZARD_SECTION_OWN_LABELS[field]

    async def open_every_group(self):
        """Open each heading of the section's panel that is closed, so that every field shows."""
        for label in THE_GROUPS:
            headings = [field for field in self.app.screen.shown_fields() if field.label == label]
            if headings and not self.app.screen.is_open(headings[0]):
                await self.select_field(label)
                await self.press(Key.ENTER)

    async def test_the_fields_are_in_groups_closed_until_opened_that_say_when_something_inside_is_set(self):
        choices = self.choices()
        shown = self.text()
        for label in THE_GROUPS:
            self.assertIn(label, shown)
        self.assertIn(self.label(ENERGY), shown)
        self.assertNotIn(self.label(TEMPO_END_OF_PLACE), shown)
        self.assertNotIn(MSG_SECTION_SET, shown)
        choices.set_section_own(place=A_PLACE, field=FADES, value=True)
        await self.press(Key.DOWN, Key.UP)
        self.assertIn(MSG_SECTION_SET, self.text())
        await self.open_every_group()
        self.assertIn(self.label(TEMPO_END_OF_PLACE), self.text())

    async def test_each_field_shows_what_the_section_takes_and_where_from(self):
        choices = self.choices()
        await self.open_every_group()
        shown = self.text()
        for field in choices.section_own_fields(A_PLACE):
            self.assertIn(self.label(field), shown)
            if field in (RISES, FADES):
                # A switch shows on or off and no origin.
                continue
            self.assertIn(MSG_WIZARD_VALUE_FROM.format(value=choices.section_from_plan(place=A_PLACE, field=field), origin=MSG_WIZARD_SECTION_ORIGINS[field]), shown)

    async def test_energy_steps_from_the_plan_s_and_bksp_gives_it_back(self):
        choices = self.choices()
        usual = choices.energies()[A_PLACE]
        await self.select_field(self.label(ENERGY))
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(choices.section_own(place=A_PLACE, field=ENERGY), usual + 1)
        self.assertNotIn(MSG_WIZARD_VALUE_FROM.format(value=usual, origin=MSG_WIZARD_SECTION_ORIGINS[ENERGY]), self.text())
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertIsNone(choices.section_own(place=A_PLACE, field=ENERGY))

    async def test_a_way_of_leaving_a_key_and_a_scale_are_chosen_from_a_list(self):
        choices = self.choices()
        for field in (LEAVES, ROOT_OF_PLACE, TYPE_OF_PLACE):
            await self.select_field(self.label(field))
            await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
            self.assertIsNotNone(choices.section_own(place=A_PLACE, field=field))

    async def test_chords_are_typed_and_what_cannot_be_chords_is_said(self):
        choices = self.choices()
        await self.select_field(self.label(CHORDS))
        await self.press(Key.ENTER)
        for _ in range(MAX_NAME_LENGTH):
            await self.press(Key.BACKSPACE)
        await self.type(SOME_CHORDS)
        await self.press(Key.ENTER)
        self.assertEqual(chords_as_text(choices.section_own(place=A_PLACE, field=CHORDS)), SOME_CHORDS)
        await self.press(Key.ENTER)
        await self.type(NOT_A_CHORD)
        await self.press(Key.ENTER)
        self.assertEqual(chords_as_text(choices.section_own(place=A_PLACE, field=CHORDS)), SOME_CHORDS)
        self.assertIn(ERR_WIZARD_CHORDS.split('{')[0][:A_FEW_WORDS], self.text())

    async def test_a_song_with_no_plan_keeps_the_chords_the_tempo_the_key_and_the_scale(self):
        self.choices().set_song_plan(False)
        await self.press(Key.DOWN, Key.UP)
        await self.open_every_group()
        shown = self.text()
        self.assertNotIn(self.label(ENERGY), shown)
        for field in (CHORDS, TEMPO_END_OF_PLACE, ROOT_OF_PLACE, TYPE_OF_PLACE):
            self.assertIn(self.label(field), shown)


class TestWizardFormQuestions(WizardTest):
    """The Form panel's questions, a dialog each, and the form made from the answers."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        choices = self.choices()
        choices.set_genre(A_PLANNED_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_named_branch(MSG_WIZARD_FORM_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_FORM_QUESTIONS_BUTTON)

    async def test_the_usual_answers_make_the_usual_form_of_the_questions(self):
        choices = self.choices()
        await self.press(Key.ENTER)
        for name, _, _ in choices.form_questions():
            self.assertIn(MSG_WIZARD_FORM_QUESTION_TITLES[name], self.text())
            await self.press(Key.ENTER)
        self.assertTrue(choices.has_own_form())
        self.assertEqual(choices.section_kinds_in_form(), choices.form_of_answers({}))
        self.assertTrue(self.wizard().has_choices_to_lose())

    async def test_another_answer_is_in_the_form_made(self):
        choices = self.choices()
        await self.press(Key.ENTER)
        for name, _, _ in choices.form_questions():
            await self.press(*([Key.DOWN] if name == DRUM_SOLO_KIND else []), Key.ENTER)
        self.assertIn(DRUM_SOLO_KIND, choices.section_kinds_in_form())

    async def test_esc_at_a_question_leaves_the_form_alone(self):
        choices = self.choices()
        before = choices.section_kinds_in_form()
        await self.press(Key.ENTER, Key.ENTER, Key.ESCAPE)
        self.assertFalse(choices.has_own_form())
        self.assertEqual(choices.section_kinds_in_form(), before)

    async def test_a_form_a_person_changed_is_replaced_only_on_a_yes(self):
        choices = self.choices()
        choices.copy_section(A_PLACE)
        before = choices.section_kinds_in_form()
        await self.press(Key.ENTER)
        for _ in choices.form_questions():
            await self.press(Key.ENTER)
        self.assertIn(MSG_WIZARD_REPLACE_SECTIONS_TITLE, self.text())
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertEqual(choices.section_kinds_in_form(), before)

    async def test_a_genre_with_no_verse_and_chorus_has_no_questions(self):
        choices = self.choices()
        choices.set_genre(AN_UNPLANNED_GENRE)
        choices.set_subgenre(choices.subgenres()[0])
        await self.press(keybindings.WizardPage.TO_TREE, Key.DOWN, Key.UP)
        await self.go_to_named_branch(MSG_WIZARD_FORM_BRANCH)
        self.assertNotIn(MSG_WIZARD_FORM_QUESTIONS_BUTTON, self.text())
