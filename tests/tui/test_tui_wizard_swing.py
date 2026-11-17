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
"""Tests of the Swing field on the song wizard's Subgenre panel."""

from llamatron.macro_composer.arranger import NO_GROOVE
from llamatron.strings.labels import MSG_WIZARD_SUBGENRE_BRANCH, MSG_WIZARD_SWING_LABEL, MSG_WIZARD_VALUE_FROM
from llamatron.strings.legends import MSG_FROM_GENRE_WHAT
from llamatron.tui import keybindings
from llamatron.tui.keys import Key
from tests.support.ui_testing import key_of
from tests.tui.test_tui_wizard import WizardTest

A_GENRE = 'rock'
A_KIND_THAT_SWINGS = 'rock and roll'
A_GENRE_IN_TRIPLETS = 'blues'
A_KIND_IN_TRIPLETS = 'shuffle'
NEW_LINE = '\n'


class TestWizardSwingField(WizardTest):
    """The swing a song is played with, on the Subgenre panel under the tempo."""

    async def to_genre(self, *, genre, subgenre):
        choices = self.choices()
        choices.set_genre(genre)
        choices.set_subgenre(subgenre)
        await self.go_to_named_branch(MSG_WIZARD_SUBGENRE_BRANCH)
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        return choices

    def labels(self):
        return [field.label for field in self.wizard().shown_fields()]

    async def test_the_swing_is_the_subgenre_s_until_another_is_chosen(self):
        choices = await self.to_genre(genre=A_GENRE, subgenre=A_KIND_THAT_SWINGS)
        usual = choices.swing_of_genre()
        self.assertNotEqual(usual, NO_GROOVE)
        self.assertIn(MSG_WIZARD_VALUE_FROM.format(value=usual, origin=MSG_FROM_GENRE_WHAT), self.text())
        await self.select_field(MSG_WIZARD_SWING_LABEL)
        await self.press(key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET))
        self.assertNotEqual(choices.get_swing(), usual)
        self.assertIn(choices.get_swing(), choices.swings())
        self.assertNotIn(MSG_FROM_GENRE_WHAT, next(line for line in self.text().split(NEW_LINE) if MSG_WIZARD_SWING_LABEL in line))
        self.assertTrue(self.wizard().has_choices_to_lose())

    async def test_a_kind_written_in_triplets_has_no_swing_field(self):
        await self.to_genre(genre=A_GENRE_IN_TRIPLETS, subgenre=A_KIND_IN_TRIPLETS)
        self.assertNotIn(MSG_WIZARD_SWING_LABEL, self.labels())

