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
"""The picker of a new generator's type: the types under headings that open and close, searched by typing, on the Generators page."""

from llamatron.composition.file_format import Section
from llamatron.strings import labels, marks, messages
from llamatron.tui import keybindings
from llamatron.tui.dialogs.grouped_choice_dialog import GroupedChoiceDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.generators.follow_chords_editor import FollowChordsEditor
from llamatron.tui.screens.generators.generator_pages import GENERATOR_PAGES
from llamatron.tui.screens.generators.generators_page import GeneratorsPage
from tests.support.ui_testing import UITest, back_key, forward_key

HEADINGS = sorted([labels.GeneratorGroup.ARRANGEMENT, labels.GeneratorGroup.ARTICULATION, labels.GeneratorGroup.HARMONY, labels.GeneratorGroup.RHYTHM, labels.GeneratorGroup.TIMING, labels.GeneratorGroup.TRANSITIONS, labels.GeneratorGroup.VOICING])
HARMONY_PLACE = HEADINGS.index(labels.GeneratorGroup.HARMONY)
# What is typed to search for Strum: its name in small letters, since a search ignores case.
SEARCHED = labels.MSG_STRUM_LABEL.lower()


def heading(*, name, is_open):
    return marks.MSG_GROUP_OF_CHOICES.format(mark=marks.MSG_SECTION_OPEN_MARK if is_open else marks.MSG_SECTION_CLOSED_MARK, name=name)


class TestGeneratorTypePicker(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.GENERATORS, keybindings.ListPage.ADD)
        self.dialog = self.app.screen
        self.assertIsInstance(self.dialog, GroupedChoiceDialog)

    async def test_it_opens_on_closed_headings_in_order_under_its_title(self):
        shown = self.text()
        self.assertIn(messages.MSG_NEW_GENERATOR_KIND_TITLE, shown)
        places = [shown.index(heading(name=name, is_open=False)) for name in HEADINGS]
        self.assertEqual(places, sorted(places))
        self.assertNotIn(labels.MSG_FOLLOW_CHORDS_LABEL, shown)

    async def test_every_type_is_under_a_heading_once_by_name(self):
        self.assertEqual(sorted(self.dialog.options), sorted(listing.label for listing in GENERATOR_PAGES.values()))
        self.assertEqual(self.dialog.headings, HEADINGS)
        in_harmony = [listing.label for listing in GENERATOR_PAGES.values() if listing.group == labels.GeneratorGroup.HARMONY]
        self.assertEqual(in_harmony, [labels.MSG_FOLLOW_CHORDS_LABEL, labels.MSG_PROGRESSION_LABEL])
        self.assertEqual(GENERATOR_PAGES[Section.STRUMS].group, labels.GeneratorGroup.RHYTHM)
        self.assertEqual(GENERATOR_PAGES[Section.VOICE_LEADINGS].group, labels.GeneratorGroup.VOICING)

    async def test_space_or_enter_opens_a_heading_and_closes_it_again(self):
        await self.press(*[Key.DOWN] * HARMONY_PLACE, Key.SPACE)
        self.assertIn(heading(name=labels.GeneratorGroup.HARMONY, is_open=True), self.text())
        self.assertIn(labels.MSG_FOLLOW_CHORDS_LABEL, self.text())
        await self.press(Key.ENTER)
        self.assertIn(heading(name=labels.GeneratorGroup.HARMONY, is_open=False), self.text())
        self.assertNotIn(labels.MSG_FOLLOW_CHORDS_LABEL, self.text())
        self.assertIsInstance(self.app.screen, GroupedChoiceDialog)

    async def test_enter_on_a_type_makes_one_and_opens_it(self):
        await self.press(*[Key.DOWN] * HARMONY_PLACE, Key.SPACE, Key.DOWN, Key.ENTER)
        self.assertIsInstance(self.app.screen, FollowChordsEditor)
        self.assertEqual(len(self.document.names_of(Section.FOLLOW_CHORDS)), 2)

    async def test_an_open_heading_is_remembered_when_the_picker_opens_again(self):
        await self.press(*[Key.DOWN] * HARMONY_PLACE, Key.SPACE, Key.ESCAPE)
        self.assertIsInstance(self.app.screen, GeneratorsPage)
        await self.press(keybindings.ListPage.ADD)
        self.assertIn(heading(name=labels.GeneratorGroup.HARMONY, is_open=True), self.text())

    async def test_the_heading_keys_jump_between_headings_and_stop_at_the_ends(self):
        await self.press(Key.SPACE, forward_key(keybindings.GroupedChoiceDialog.HEADING))
        self.assertEqual(self.dialog.rows()[self.dialog.row], (1, None))
        await self.press(back_key(keybindings.GroupedChoiceDialog.HEADING), back_key(keybindings.GroupedChoiceDialog.HEADING))
        self.assertEqual(self.dialog.row, 0)

    async def test_the_cursor_stops_at_the_last_heading(self):
        await self.press(*[Key.DOWN] * (len(HEADINGS) + 2))
        self.assertEqual(self.dialog.row, len(HEADINGS) - 1)

    async def test_typing_searches_every_type_with_no_headings_and_enter_picks(self):
        await self.type(SEARCHED)
        shown = self.text()
        self.assertIn(labels.MSG_STRUM_LABEL, shown)
        self.assertNotIn(heading(name=labels.GeneratorGroup.RHYTHM, is_open=False), shown)
        await self.press(Key.ENTER)
        self.assertEqual(len(self.document.names_of(Section.STRUMS)), 2)

    async def test_erasing_the_search_shows_the_headings_again_on_the_found_types_heading(self):
        await self.type(labels.MSG_VOICE_LEADING_LABEL)
        await self.press(*[keybindings.ChoiceDialog.ERASE] * len(labels.MSG_VOICE_LEADING_LABEL))
        self.assertEqual(self.dialog.headings[self.dialog.rows()[self.dialog.row][0]], labels.GeneratorGroup.VOICING)
        self.assertIn(heading(name=labels.GeneratorGroup.VOICING, is_open=False), self.text())
