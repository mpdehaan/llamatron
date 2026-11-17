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

from llamatron.macro_composer import hook_kinds
from llamatron.macro_composer.song_plan import USUAL_CONTRAST
from llamatron.strings.labels import (
    MSG_WIZARD_CONTRAST_LABEL, MSG_WIZARD_FORM_BRANCH, MSG_WIZARD_HOOK_PART_LABELS, MSG_WIZARD_HOOKS_BRANCH, MSG_WIZARD_PHRASING_LABEL, MSG_WIZARD_PICK_SHOWN,
    MSG_WIZARD_SONG_PLAN_LABEL,
)
from llamatron.tui import keybindings
from llamatron.tui.keys import Key
from tests.support.ui_testing import key_of
from tests.tui.test_tui_wizard import WizardTest

A_PLANNED_GENRE = 'rock'
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

    async def switch_plan_on(self):
        await self.go_to_named_branch(MSG_WIZARD_FORM_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        await self.select_field(MSG_WIZARD_SONG_PLAN_LABEL)
        await self.press(Key.ENTER)

    async def test_the_plan_is_switched_on_from_the_form_panel_and_shows_its_fields_and_each_section(self):
        await self.choose()
        await self.go_to_named_branch(MSG_WIZARD_FORM_BRANCH)
        self.assertIn(MSG_WIZARD_SONG_PLAN_LABEL, self.text())
        self.assertNotIn(MSG_WIZARD_CONTRAST_LABEL, self.text())
        await self.switch_plan_on()
        choices = self.choices()
        self.assertTrue(choices.has_song_plan())
        shown = self.text()
        for label in (MSG_WIZARD_CONTRAST_LABEL, MSG_WIZARD_PHRASING_LABEL):
            self.assertIn(label, shown)
        for said in choices.said_of_sections():
            self.assertIn(said.split('.')[0], shown)
        self.assertTrue(self.wizard().has_choices_to_lose())

    async def test_contrast_steps_and_phrasing_toggles(self):
        await self.choose()
        await self.switch_plan_on()
        await self.select_field(MSG_WIZARD_CONTRAST_LABEL)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertEqual(self.choices().get_contrast(), USUAL_CONTRAST + 1)
        await self.select_field(MSG_WIZARD_PHRASING_LABEL)
        await self.press(Key.ENTER)
        self.assertFalse(self.choices().has_phrasing())

    async def test_a_genre_with_no_plan_shows_no_switch_and_a_song_in_six_no_phrasing(self):
        await self.choose(genre=AN_UNPLANNED_GENRE, subgenre=None)
        await self.go_to_named_branch(MSG_WIZARD_FORM_BRANCH)
        self.assertNotIn(MSG_WIZARD_SONG_PLAN_LABEL, self.text())
        await self.choose(subgenre=A_SUBGENRE_IN_SIX)
        await self.switch_plan_on()
        self.assertIn(MSG_WIZARD_CONTRAST_LABEL, self.text())
        self.assertNotIn(MSG_WIZARD_PHRASING_LABEL, self.text())

    async def test_the_hooks_panel_shows_the_kind_only_under_a_plan_and_marks_the_wizard_s_pick(self):
        await self.choose()
        await self.go_to_hooks()
        for label in MSG_WIZARD_HOOK_PART_LABELS.values():
            self.assertNotIn(label, self.text())
        self.choices().set_song_plan(True)
        self.choices().set_hook_part(part=hook_kinds.CONTOUR, value=hook_kinds.CHANT)
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_hooks()
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
        self.assertIn(MSG_WIZARD_HOOK_PART_LABELS[hook_kinds.CONTOUR], self.text())
        self.assertNotIn(MSG_WIZARD_HOOK_PART_LABELS[hook_kinds.DETAIL], self.text())
