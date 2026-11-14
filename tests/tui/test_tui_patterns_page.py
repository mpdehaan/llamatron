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

"""The Patterns page."""

from tests.support.ui_testing import UITest
from llamatron.tui.screens.set.main_page import MainPage
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor
from llamatron.strings.messages import MSG_SEARCH_STATUS
from llamatron.tui import keybindings

# Names the tests give to their own things, and other values they use.
# Patterns added out of order, with a capital, to see a picker sort them.
UNSORTED_PATTERN_NAMES = ('zed', 'Alpha', 'mid')
# Typed into a search, and the one of those names it finds.
SEARCH_TEXT = 'al'
SEARCH_HIT = 'Alpha'
NEW = 'new'
BEAT = 'beat'
MELODY = 'melody'
TUNE = 'tune'
TUNE_COPY = 'tune-2'
OTHER = 'other'
ALREADY_IN_USE = 'already in use'
LEAD = 'lead'


class TestPatternsPage(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS)

    def names(self):
        return self.document.song().get_pattern_names()

    async def test_a_adds_one_and_opens_it(self):
        await self.press(keybindings.PatternsPage.ADD)
        self.app.screen.value = NEW
        await self.press(Key.ENTER)
        self.assertIn(NEW, self.names())
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.document.song().get_pattern(NEW).get_steps(), 16)

    async def test_u_and_d_move_the_selected_pattern(self):
        await self.press(keybindings.PatternsPage.MOVE, Key.DOWN, Key.ENTER)
        self.assertEqual(self.names(), [BEAT, TUNE, OTHER])
        self.assertEqual(self.app.screen.current(), TUNE)
        await self.press(keybindings.PatternsPage.MOVE, Key.UP, Key.ENTER)
        self.assertEqual(self.names(), [TUNE, BEAT, OTHER])

    async def test_s_sorts(self):
        await self.press(keybindings.PatternsPage.SORT)
        self.assertEqual(self.names(), [BEAT, OTHER, TUNE])

    async def test_c_copies(self):
        await self.press(keybindings.PatternsPage.COPY)
        self.assertIn(TUNE_COPY, self.names())

    async def test_deleting_something_used_is_refused_and_says_what_uses_it(self):
        await self.press(Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn('scene 1 (one), track lead', self.text())
        await self.press(Key.ENTER)
        self.assertIn(TUNE, self.names())

    async def test_a_refusal_lists_five_and_then_dots(self):
        for number in range(7):
            index = len(self.document.song().get_scenes())
            self.document.add_scene(index=index, name=f'x{number}')
            self.document.add_clip_slot(index=index, track=LEAD, pattern=OTHER)
        await self.press(Key.DOWN, Key.DOWN, Key.BACKSPACE)
        text = self.text()
        self.assertEqual(text.count('(x'), 5)
        self.assertIn('... and 2 more', text)

    async def test_deleting_something_unused_confirms_first(self):
        await self.press(Key.DOWN, Key.DOWN, Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertIn(OTHER, self.names())
        await self.press(Key.BACKSPACE, keybindings.ConfirmDialog.YES)
        self.assertNotIn(OTHER, self.names())

    async def test_a_duplicate_name_is_refused(self):
        await self.press(keybindings.PatternsPage.RENAME)
        self.app.screen.value = BEAT
        await self.press(Key.ENTER)
        self.assertIn(TUNE, self.names())
        self.assertIn(ALREADY_IN_USE, self.text())

    async def test_a_name_another_pattern_has_in_other_capitals_is_refused(self):
        await self.press(keybindings.PatternsPage.RENAME)
        self.app.screen.value = BEAT.upper()
        await self.press(Key.ENTER)
        self.assertIn(TUNE, self.names())
        self.assertIn(ALREADY_IN_USE, self.text())

    async def test_a_pattern_can_change_the_capitals_of_its_own_name(self):
        await self.press(keybindings.PatternsPage.RENAME)
        self.app.screen.value = TUNE.upper()
        await self.press(Key.ENTER)
        self.assertIn(TUNE.upper(), self.names())
        self.assertNotIn(TUNE, self.names())

    async def test_renaming_updates_clips(self):
        await self.press(keybindings.PatternsPage.RENAME)
        self.app.screen.value = MELODY
        await self.press(Key.ENTER)
        self.assertEqual(self.document.clip_slot(index=0, track=LEAD).get_pattern_name(), MELODY)

    async def test_slash_searches_the_list_and_enter_keeps_the_place(self):
        for name in UNSORTED_PATTERN_NAMES:
            self.add_pattern_with_rows(name=name, steps=1, rows={})
        self.assertEqual(self.app.screen.current(), TUNE)
        await self.press(keybindings.PatternsPage.SEARCH)
        await self.type(SEARCH_TEXT)
        self.assertEqual(self.app.screen.current(), SEARCH_HIT)
        self.assertIn(MSG_SEARCH_STATUS.format(text=SEARCH_TEXT), self.text())
        self.assertNotIn(BEAT, self.text())
        await self.press(Key.TAB)
        self.assertEqual(self.app.screen.typed, SEARCH_HIT)
        await self.press(Key.ENTER)
        self.assertEqual(self.app.screen.current(), SEARCH_HIT)
        self.assertIn(BEAT, self.text())
        self.assertFalse(self.app.screen.searching)

    async def test_esc_ends_a_search_and_puts_the_cursor_back(self):
        for name in UNSORTED_PATTERN_NAMES:
            self.add_pattern_with_rows(name=name, steps=1, rows={})
        await self.press(Key.DOWN, keybindings.PatternsPage.SEARCH)
        await self.type(SEARCH_TEXT)
        self.assertEqual(self.app.screen.current(), SEARCH_HIT)
        await self.press(Key.ESCAPE)
        self.assertEqual(self.app.screen.current(), BEAT)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, MainPage)
