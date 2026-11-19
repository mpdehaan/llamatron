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
"""Tests of how loud a player is on the song wizard's player panels: the Dynamics gauge and the levels under the Loudness heading."""

from llamatron.macro_composer import loudness, notation
from llamatron.strings import labels as labels_text, marks
from llamatron.tui import keybindings
from llamatron.tui.keys import Key
from tests.support.ui_testing import key_of
from tests.tui.test_tui_wizard import WizardTest

A_GENRE = 'rock'
A_SUBGENRE = 'hard rock'
A_SEED = 11
THE_BASS = 'bass'
THE_LEAD = 'lead'


class TestWizardLoudnessFields(WizardTest):
    """Dynamics and the Loudness heading on a player's panel."""

    def chosen(self):
        choices = self.choices()
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        choices.set_seed(A_SEED)
        return choices

    def more(self):
        return key_of(binding=keybindings.WizardPage.MORE, key=Key.RIGHT_BRACKET)

    def labels(self):
        return [field.label for field in self.wizard().shown_fields()]

    async def to_player(self, role):
        choices = self.chosen()
        await self.press(Key.DOWN, Key.UP)
        await self.go_to_named_branch(choices.player(role).title())
        await self.press(keybindings.WizardPage.INTO_FIELDS)
        return choices

    async def test_dynamics_is_a_gauge_that_steps(self):
        choices = await self.to_player(THE_LEAD)
        self.assertIn(labels_text.MSG_WIZARD_DYNAMICS_SAID[loudness.USUAL_DYNAMICS], self.text())
        await self.select_field(labels_text.MSG_WIZARD_DYNAMICS_LABEL)
        await self.press(self.more())
        self.assertEqual(choices.player(THE_LEAD).get_dynamics(), loudness.USUAL_DYNAMICS + 1)
        self.assertIn(labels_text.MSG_WIZARD_DYNAMICS_SAID[loudness.USUAL_DYNAMICS + 1], self.text())
        self.assertEqual(self.wizard().label_under_cursor(), labels_text.MSG_WIZARD_DYNAMICS_LABEL)

    async def test_the_loudness_heading_is_closed_until_opened_and_shows_the_levels_the_player_plays(self):
        choices = await self.to_player(THE_LEAD)
        self.assertIn(labels_text.MSG_WIZARD_GROUP_LOUDNESS, self.labels())
        self.assertNotIn(labels_text.MSG_WIZARD_LEVEL_LABELS[loudness.NORMAL], self.labels())
        await self.select_field(labels_text.MSG_WIZARD_LEVEL_LABELS[loudness.NORMAL])
        offered = choices.player(THE_LEAD).loudness_levels_offered()
        # The levels are the last settings of the panel, with only the panel's button after them.
        after_heading = self.labels()[self.labels().index(labels_text.MSG_WIZARD_GROUP_LOUDNESS) + 1:]
        self.assertEqual(after_heading, [*(labels_text.MSG_WIZARD_LEVEL_LABELS[level] for level in offered), labels_text.MSG_WIZARD_EDIT_PLAYER_BUTTON])
        self.assertNotIn(labels_text.MSG_WIZARD_LEVEL_LABELS[notation.GHOST], self.labels())
        self.assertIn(marks.MSG_WIZARD_LEVEL_FROM_GENRE.format(number=choices.player(THE_LEAD).loudness_levels()[loudness.NORMAL]), self.text())

    async def test_a_level_steps_to_the_songs_own_and_backspace_gives_it_back_to_the_genre(self):
        choices = await self.to_player(THE_LEAD)
        usual = choices.player(THE_LEAD).loudness_levels()
        await self.select_field(labels_text.MSG_WIZARD_LEVEL_LABELS[notation.ACCENT])
        await self.press(self.more())
        self.assertTrue(choices.player(THE_LEAD).loudness_level_is_own(level=notation.ACCENT))
        self.assertEqual(choices.player(THE_LEAD).loudness_levels()[notation.ACCENT], usual[notation.ACCENT] + 1)
        self.assertNotIn(marks.MSG_WIZARD_LEVEL_FROM_GENRE.format(number=usual[notation.ACCENT] + 1), self.text())
        await self.press(keybindings.WizardPage.CLEAR)
        self.assertFalse(choices.player(THE_LEAD).loudness_level_is_own(level=notation.ACCENT))
        self.assertEqual(choices.player(THE_LEAD).loudness_levels(), usual)

    async def test_the_normal_level_carries_the_accent_shown_with_it(self):
        choices = await self.to_player(THE_BASS)
        await self.select_field(labels_text.MSG_WIZARD_LEVEL_LABELS[loudness.NORMAL])
        await self.press(key_of(binding=keybindings.WizardPage.LESS, key=Key.LEFT_BRACKET))
        levels = choices.player(THE_BASS).loudness_levels()
        self.assertEqual(levels[notation.ACCENT] - levels[loudness.NORMAL], loudness.ACCENT_ABOVE)
        self.assertTrue(self.wizard().has_choices_to_lose())
