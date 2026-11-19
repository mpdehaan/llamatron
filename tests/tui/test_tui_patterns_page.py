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

import os

from llamatron.composition import file_format, limits
from llamatron.composition.setlist import Setlist
from llamatron.strings import errors, labels, marks, messages
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.pattern import patterns_page
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor
from llamatron.tui.screens.pattern.patterns_page import Listed
from llamatron.tui.screens.set.main_page import MainPage
from tests.support import ui_testing
from tests.support.ui_testing import back_key, every_key, first_key, forward_key, key_name, UITest

# Names the tests give to their own things, and other values they use.
# Patterns added out of order, with a capital, to see a picker sort them.
UNSORTED_PATTERN_NAMES = ('zed', 'Alpha', 'mid')
# Typed into a search, and the one of those names it finds.
SEARCH_TEXT = 'al'
SEARCH_HIT = 'Alpha'
NEW = 'new'
MELODY = 'melody'
TUNE_COPY = 'tune-2'
ALREADY_IN_USE = 'already in use'
# Patterns whose names end in numbers, in the order the page lists them, the number read as a number.
NUMBERED = ['riff', 'riff-2', 'riff-10']
# Groups the tests make, a group's name as its copy is first offered, and what a copied group's patterns are called.
BASSES = 'basses'
SONGS = 'songs'
MELODIES_COPY = 'melodies-2'
TUNE_IN_COPY = 'melodies-2_tune'
MELODIES_RIFF = 'melodies_riff'
SONGS_RIFF = 'songs_riff'
# A group's name that makes the name of a copied pattern too long.
LONG_GROUP = 'g' * (limits.MAX_NAME_LENGTH - 2)
A_SCENE = 'x{number}'
SCENES_ADDED = 7
SCENES_LISTED = 5
A_SCENE_SHOWN = '(x'
AND_MORE = '... and 2 more'
A_USE = 'scene 1 (one), track lead'
DEFAULT_STEPS = 16
SAVED_FILE = 'groups.yml'


class PatternsPageTest(UITest):
    """The Patterns page open on the test set: the tune in one group, the beat in another and a third pattern in none."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS)
        self.page = self.app.screen

    def names(self):
        return self.document.song().get_pattern_names()

    def rows(self):
        """Return what each row of the page is, in order."""
        return [what for what, _ in self.page.remembered_rows()]

    def group_of(self, name):
        return self.document.pattern_group(name)

    async def go_to(self, listed):
        """Move the cursor to a row by what the row is."""
        self.assertIn(listed, self.rows())
        while self.page.listed() != listed:
            await self.press(Key.UP if self.rows().index(listed) < self.page.place else Key.DOWN)

    async def go_to_pattern(self, name):
        await self.go_to(Listed(patterns_page.PATTERN, name))

    async def go_to_heading(self, group):
        await self.go_to(Listed(patterns_page.HEADING, group))

    async def answer(self, text):
        """Type an answer over what a prompt offers and press ENTER."""
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = text
        await self.press(Key.ENTER)

    def bound(self):
        return [name for item in self.page.key_table() for name in item.keys]

    def heading(self, *, group, count, closed=False):
        return labels.MSG_GROUP_HEADING.format(mark=marks.MSG_SECTION_CLOSED_MARK if closed else marks.MSG_SECTION_OPEN_MARK, name=group, count=count)


class TestPatternsPage(PatternsPageTest):
    """A pattern's row: adding, copying, deleting, renaming and searching."""

    async def test_the_page_opens_on_its_first_pattern_and_enter_edits_it(self):
        self.assertEqual(self.page.current(), ui_testing.TUNE)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.app.screen.item, ui_testing.TUNE)

    async def test_a_adds_one_to_the_cursors_group_and_opens_it(self):
        await self.press(keybindings.PatternsPage.ADD, keybindings.NewPatternDialog.OK)
        await self.answer(NEW)
        self.assertIn(NEW, self.names())
        self.assertEqual(self.group_of(NEW), ui_testing.MELODIES)
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertEqual(self.document.song().get_pattern(NEW).get_steps(), DEFAULT_STEPS)
        await self.press(Key.ESCAPE)
        self.assertEqual(self.page.current(), NEW)

    async def test_nothing_moves_or_sorts_since_the_page_is_always_sorted(self):
        for binding in (keybindings.ListPage.MOVE, keybindings.ListPage.SORT):
            for key in every_key(binding):
                self.assertNotIn(key, self.bound())

    async def test_c_copies_into_the_patterns_own_group(self):
        await self.press(keybindings.PatternsPage.COPY)
        self.assertIn(TUNE_COPY, self.names())
        self.assertEqual(self.group_of(TUNE_COPY), ui_testing.MELODIES)
        self.assertEqual(self.page.current(), TUNE_COPY)

    async def test_deleting_something_used_is_refused_and_says_what_uses_it(self):
        await self.press(Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(A_USE, self.text())
        await self.press(Key.ENTER)
        self.assertIn(ui_testing.TUNE, self.names())

    async def test_a_refusal_lists_five_and_then_dots(self):
        for number in range(SCENES_ADDED):
            index = len(self.document.song().get_scenes())
            self.document.add_scene(index=index, name=A_SCENE.format(number=number))
            self.document.add_clip_slot(index=index, track=ui_testing.LEAD, pattern=ui_testing.OTHER)
        await self.go_to_pattern(ui_testing.OTHER)
        await self.press(Key.BACKSPACE)
        text = self.text()
        self.assertEqual(text.count(A_SCENE_SHOWN), SCENES_LISTED)
        self.assertIn(AND_MORE, text)

    async def test_deleting_something_unused_confirms_first(self):
        await self.go_to_pattern(ui_testing.OTHER)
        await self.press(Key.BACKSPACE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertIn(ui_testing.OTHER, self.names())
        await self.press(Key.BACKSPACE, keybindings.ConfirmDialog.YES)
        self.assertNotIn(ui_testing.OTHER, self.names())

    async def test_a_duplicate_name_is_refused(self):
        await self.press(keybindings.PatternsPage.RENAME)
        await self.answer(ui_testing.BEAT)
        self.assertIn(ui_testing.TUNE, self.names())
        self.assertIn(ALREADY_IN_USE, self.text())

    async def test_a_name_another_pattern_has_in_other_capitals_is_refused(self):
        await self.press(keybindings.PatternsPage.RENAME)
        await self.answer(ui_testing.BEAT.upper())
        self.assertIn(ui_testing.TUNE, self.names())
        self.assertIn(ALREADY_IN_USE, self.text())

    async def test_a_pattern_can_change_the_capitals_of_its_own_name(self):
        await self.press(keybindings.PatternsPage.RENAME)
        await self.answer(ui_testing.TUNE.upper())
        self.assertIn(ui_testing.TUNE.upper(), self.names())
        self.assertNotIn(ui_testing.TUNE, self.names())

    async def test_renaming_updates_clips_and_keeps_the_group_and_the_cursor(self):
        await self.press(keybindings.PatternsPage.RENAME)
        await self.answer(MELODY)
        self.assertEqual(self.document.clip_slot(index=0, track=ui_testing.LEAD).get_pattern_name(), MELODY)
        self.assertEqual(self.group_of(MELODY), ui_testing.MELODIES)
        self.assertEqual(self.page.current(), MELODY)

    async def test_slash_searches_the_patterns_and_enter_keeps_the_place(self):
        for name in UNSORTED_PATTERN_NAMES:
            self.add_pattern_with_rows(name=name, steps=1, rows={})
        self.assertEqual(self.page.current(), ui_testing.TUNE)
        await self.press(keybindings.PatternsPage.SEARCH)
        await self.type(SEARCH_TEXT)
        self.assertEqual(self.page.current(), SEARCH_HIT)
        self.assertIn(messages.MSG_SEARCH_STATUS.format(text=SEARCH_TEXT), self.text())
        self.assertNotIn(ui_testing.BEAT, self.text())
        await self.press(Key.TAB)
        self.assertEqual(self.page.typed, SEARCH_HIT)
        await self.press(Key.ENTER)
        self.assertEqual(self.page.current(), SEARCH_HIT)
        self.assertIn(ui_testing.BEAT, self.text())
        self.assertFalse(self.page.searching)

    async def test_esc_ends_a_search_and_puts_the_cursor_back(self):
        for name in UNSORTED_PATTERN_NAMES:
            self.add_pattern_with_rows(name=name, steps=1, rows={})
        await self.go_to_pattern(ui_testing.BEAT)
        await self.press(keybindings.PatternsPage.SEARCH)
        await self.type(SEARCH_TEXT)
        self.assertEqual(self.page.current(), SEARCH_HIT)
        await self.press(Key.ESCAPE)
        self.assertEqual(self.page.current(), ui_testing.BEAT)
        await self.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, MainPage)

    async def test_a_search_finds_a_pattern_in_a_closed_group_and_enter_opens_the_group(self):
        self.document.show_pattern_group(group=ui_testing.RHYTHMS, closed=True)
        await self.press(Key.DOWN, Key.UP)
        self.assertNotIn(Listed(patterns_page.PATTERN, ui_testing.BEAT), self.rows())
        await self.press(keybindings.PatternsPage.SEARCH)
        await self.type(ui_testing.BEAT)
        self.assertEqual(self.page.current(), ui_testing.BEAT)
        await self.press(Key.ENTER)
        self.assertEqual(self.page.current(), ui_testing.BEAT)
        self.assertFalse(self.document.setlist().is_pattern_group_closed(ui_testing.RHYTHMS))

    async def test_a_search_left_with_esc_leaves_a_closed_group_closed(self):
        self.document.show_pattern_group(group=ui_testing.RHYTHMS, closed=True)
        await self.press(keybindings.PatternsPage.SEARCH)
        await self.type(ui_testing.BEAT)
        await self.press(Key.ESCAPE)
        self.assertTrue(self.document.setlist().is_pattern_group_closed(ui_testing.RHYTHMS))
        self.assertEqual(self.page.current(), ui_testing.TUNE)


class TestPatternGroups(PatternsPageTest):
    """The groups: what the page lists, a heading's keys, the two buttons and the group a pattern is in."""

    async def test_the_rows_are_each_group_sorted_then_the_ungrouped_then_the_button(self):
        self.assertEqual(self.rows(), [
            Listed(patterns_page.HEADING, ui_testing.MELODIES), Listed(patterns_page.PATTERN, ui_testing.TUNE), Listed(patterns_page.NEW_PATTERN, ui_testing.MELODIES),
            Listed(patterns_page.HEADING, ui_testing.RHYTHMS), Listed(patterns_page.PATTERN, ui_testing.BEAT), Listed(patterns_page.NEW_PATTERN, ui_testing.RHYTHMS),
            Listed(patterns_page.HEADING, patterns_page.UNGROUPED), Listed(patterns_page.PATTERN, ui_testing.OTHER), Listed(patterns_page.NEW_GROUP, None),
        ])
        text = self.text()
        for line in (self.heading(group=ui_testing.MELODIES, count=1), self.heading(group=labels.MSG_UNGROUPED, count=1), patterns_page.INDENT + ui_testing.TUNE, patterns_page.INDENT + labels.MSG_NEW_PATTERN_BUTTON, labels.MSG_NEW_GROUP_BUTTON):
            self.assertIn(line, text)

    async def test_a_groups_patterns_are_sorted_with_a_number_at_the_end_read_as_a_number(self):
        for name in reversed(NUMBERED):
            self.document.add_pattern(name=name, group=BASSES)
        await self.press(Key.DOWN, Key.UP)
        rows = self.rows()
        self.assertEqual(rows[0], Listed(patterns_page.HEADING, BASSES))
        self.assertEqual(rows[1:1 + len(NUMBERED)], [Listed(patterns_page.PATTERN, name) for name in NUMBERED])

    async def test_the_ungrouped_heading_shows_only_while_a_pattern_is_in_no_group(self):
        self.document.set_pattern_group(name=ui_testing.OTHER, group=ui_testing.RHYTHMS)
        await self.press(Key.DOWN, Key.UP)
        self.assertNotIn(Listed(patterns_page.HEADING, patterns_page.UNGROUPED), self.rows())
        self.assertNotIn(labels.MSG_UNGROUPED, self.text())

    async def test_space_or_enter_on_a_heading_closes_and_opens_its_group(self):
        await self.go_to_heading(ui_testing.MELODIES)
        for key in every_key(keybindings.PatternsPage.TOGGLE_GROUP):
            await self.press(key)
            self.assertNotIn(Listed(patterns_page.PATTERN, ui_testing.TUNE), self.rows())
            self.assertIn(self.heading(group=ui_testing.MELODIES, count=1, closed=True), self.text())
            await self.press(key)
            self.assertIn(Listed(patterns_page.PATTERN, ui_testing.TUNE), self.rows())

    async def test_closing_a_group_is_kept_in_the_file_and_is_no_change_and_no_undo_step(self):
        dirty = self.document.is_dirty()
        before = self.document.setlist().to_data()
        await self.go_to_heading(ui_testing.RHYTHMS)
        await self.press(keybindings.PatternsPage.TOGGLE_GROUP)
        self.assertEqual(self.document.is_dirty(), dirty)
        self.assertEqual(self.document.setlist().to_data(), before)
        await self.press(keybindings.Page.UNDO)
        self.assertTrue(self.document.setlist().is_pattern_group_closed(ui_testing.RHYTHMS))
        self.assertEqual(self.document.setlist().to_data(), before)
        path = os.path.join(self.folder, SAVED_FILE)
        self.document.setlist().write_file(path)
        self.assertEqual(Setlist.read_file(path).get_closed_pattern_groups(), [ui_testing.RHYTHMS])

    async def test_page_down_and_page_up_jump_between_the_headings_and_stop_at_the_ends(self):
        await self.go_to_pattern(ui_testing.TUNE)
        await self.press(forward_key(keybindings.PatternsPage.NEXT_GROUP))
        self.assertEqual(self.page.listed(), Listed(patterns_page.HEADING, ui_testing.RHYTHMS))
        await self.press(forward_key(keybindings.PatternsPage.NEXT_GROUP), forward_key(keybindings.PatternsPage.NEXT_GROUP))
        self.assertEqual(self.page.listed(), Listed(patterns_page.HEADING, patterns_page.UNGROUPED))
        await self.press(back_key(keybindings.PatternsPage.NEXT_GROUP), back_key(keybindings.PatternsPage.NEXT_GROUP), back_key(keybindings.PatternsPage.NEXT_GROUP))
        self.assertEqual(self.page.listed(), Listed(patterns_page.HEADING, ui_testing.MELODIES))

    async def test_a_groups_button_makes_a_pattern_in_that_group(self):
        await self.go_to(Listed(patterns_page.NEW_PATTERN, ui_testing.RHYTHMS))
        self.assertIn(key_name(keybindings.PatternsPage.NEW_PATTERN), self.text())
        await self.press(keybindings.PatternsPage.NEW_PATTERN, keybindings.NewPatternDialog.OK)
        await self.answer(NEW)
        self.assertEqual(self.group_of(NEW), ui_testing.RHYTHMS)
        self.assertIsInstance(self.app.screen, PatternEditor)

    async def test_a_on_a_heading_makes_a_pattern_in_its_group(self):
        await self.go_to_heading(ui_testing.RHYTHMS)
        await self.press(keybindings.PatternsPage.ADD, keybindings.NewPatternDialog.OK)
        await self.answer(NEW)
        self.assertEqual(self.group_of(NEW), ui_testing.RHYTHMS)

    async def test_the_last_button_makes_a_group_that_shows_with_its_button_alone_until_a_pattern_is_made(self):
        before = self.document.setlist().to_data()
        await self.go_to(Listed(patterns_page.NEW_GROUP, None))
        await self.press(keybindings.PatternsPage.NEW_GROUP)
        await self.answer(BASSES)
        self.assertEqual(self.page.listed(), Listed(patterns_page.NEW_PATTERN, BASSES))
        self.assertIn(self.heading(group=BASSES, count=0), self.text())
        # A group is only what its patterns hold, so an empty one is not in the set.
        self.assertEqual(self.document.setlist().to_data(), before)
        await self.press(keybindings.PatternsPage.NEW_PATTERN, keybindings.NewPatternDialog.OK)
        await self.answer(NEW)
        self.assertEqual(self.group_of(NEW), BASSES)
        self.assertEqual(self.document.setlist().get_pattern_groups(), [BASSES, ui_testing.MELODIES, ui_testing.RHYTHMS])

    async def test_a_new_group_cannot_take_a_groups_name(self):
        await self.go_to(Listed(patterns_page.NEW_GROUP, None))
        await self.press(keybindings.PatternsPage.NEW_GROUP)
        await self.answer(ui_testing.MELODIES.upper())
        self.assertIn(ALREADY_IN_USE, self.text())
        self.assertNotIn(Listed(patterns_page.HEADING, ui_testing.MELODIES.upper()), self.rows())

    async def test_g_moves_a_pattern_to_a_group_picked_from_the_sorted_groups(self):
        await self.press(keybindings.PatternsPage.GROUP)
        dialog = self.app.screen
        self.assertIsInstance(dialog, ChoiceDialog)
        self.assertEqual(dialog.options, [ui_testing.MELODIES, ui_testing.RHYTHMS, labels.MSG_NEW_GROUP_BUTTON])
        self.assertEqual(dialog.options[dialog.place], ui_testing.MELODIES)
        await self.press(Key.DOWN, Key.ENTER)
        self.assertEqual(self.group_of(ui_testing.TUNE), ui_testing.RHYTHMS)
        self.assertEqual(self.page.current(), ui_testing.TUNE)
        # The group left with no pattern is gone.
        self.assertNotIn(Listed(patterns_page.HEADING, ui_testing.MELODIES), self.rows())
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.group_of(ui_testing.TUNE), ui_testing.MELODIES)

    async def test_g_can_make_the_group_and_takes_a_pattern_out_of_ungrouped(self):
        await self.go_to_pattern(ui_testing.OTHER)
        await self.press(keybindings.PatternsPage.GROUP, Key.DOWN, Key.DOWN, Key.ENTER)
        await self.answer(BASSES)
        self.assertEqual(self.group_of(ui_testing.OTHER), BASSES)
        self.assertEqual(self.page.current(), ui_testing.OTHER)
        self.assertNotIn(Listed(patterns_page.HEADING, patterns_page.UNGROUPED), self.rows())

    async def test_nothing_can_be_added_to_ungrouped_and_its_heading_only_opens_and_closes(self):
        await self.go_to_pattern(ui_testing.OTHER)
        self.assertNotIn(first_key(keybindings.PatternsPage.ADD), self.bound())
        await self.go_to_heading(patterns_page.UNGROUPED)
        for binding in (keybindings.PatternsPage.ADD, keybindings.PatternsPage.RENAME, keybindings.PatternsPage.COPY, keybindings.PatternsPage.UNGROUP):
            for key in every_key(binding):
                self.assertNotIn(key, self.bound())
        self.assertNotIn(Listed(patterns_page.NEW_PATTERN, patterns_page.UNGROUPED), self.rows())
        await self.press(keybindings.PatternsPage.TOGGLE_GROUP)
        self.assertNotIn(Listed(patterns_page.PATTERN, ui_testing.OTHER), self.rows())

    async def test_n_on_a_heading_renames_the_group_of_every_pattern_in_it_as_one_step(self):
        self.document.add_pattern(name=NEW, group=ui_testing.MELODIES)
        await self.go_to_heading(ui_testing.MELODIES)
        await self.press(keybindings.PatternsPage.RENAME)
        await self.answer(SONGS)
        self.assertEqual((self.group_of(ui_testing.TUNE), self.group_of(NEW)), (SONGS, SONGS))
        self.assertEqual(self.page.listed(), Listed(patterns_page.HEADING, SONGS))
        await self.press(keybindings.Page.UNDO)
        self.assertEqual((self.group_of(ui_testing.TUNE), self.group_of(NEW)), (ui_testing.MELODIES, ui_testing.MELODIES))

    async def test_a_group_cannot_be_renamed_to_another_groups_name(self):
        await self.go_to_heading(ui_testing.MELODIES)
        await self.press(keybindings.PatternsPage.RENAME)
        await self.answer(ui_testing.RHYTHMS)
        self.assertEqual(self.group_of(ui_testing.TUNE), ui_testing.MELODIES)
        self.assertIn(ALREADY_IN_USE, self.text())

    async def test_bksp_on_a_heading_asks_and_then_ungroups_and_deletes_no_pattern(self):
        names = self.names()
        await self.go_to_heading(ui_testing.MELODIES)
        await self.press(keybindings.PatternsPage.UNGROUP)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertEqual(self.group_of(ui_testing.TUNE), ui_testing.MELODIES)
        await self.press(keybindings.PatternsPage.UNGROUP, keybindings.ConfirmDialog.YES)
        self.assertIsNone(self.group_of(ui_testing.TUNE))
        self.assertEqual(self.names(), names)
        self.assertEqual(self.page.listed(), Listed(patterns_page.HEADING, patterns_page.UNGROUPED))
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.group_of(ui_testing.TUNE), ui_testing.MELODIES)

    async def test_c_on_a_heading_confirms_with_a_name_counted_up_and_copies_every_pattern_as_one_step(self):
        self.document.add_pattern(name=MELODIES_RIFF, group=ui_testing.MELODIES)
        names = self.names()
        await self.go_to_heading(ui_testing.MELODIES)
        await self.press(keybindings.PatternsPage.COPY)
        dialog = self.app.screen
        self.assertIsInstance(dialog, PromptDialog)
        self.assertEqual((dialog.title, dialog.label, dialog.value), (messages.MSG_COPY_GROUP_TITLE, labels.MSG_NEW_GROUP_NAME_LABEL, MELODIES_COPY))
        self.assertIn(labels.MSG_NEW_GROUP_NAME_LABEL + MELODIES_COPY, self.text())
        await self.press(Key.ENTER)
        # The new group's name goes at the front: joined to a name that lacked the old group's, and in its place where the name began with it.
        self.assertEqual(self.document.setlist().patterns_in_group(MELODIES_COPY), [MELODIES_COPY + MELODIES_RIFF[len(ui_testing.MELODIES):], TUNE_IN_COPY])
        self.assertEqual(self.page.listed(), Listed(patterns_page.HEADING, MELODIES_COPY))
        self.assertEqual(self.document.song().get_pattern(TUNE_IN_COPY).to_data(), {**self.document.song().get_pattern(ui_testing.TUNE).to_data(), **self.document.song().get_pattern(TUNE_IN_COPY).to_data()})
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.names(), names)

    async def test_a_copy_under_another_name_names_its_patterns_after_it(self):
        self.document.add_pattern(name=MELODIES_RIFF, group=ui_testing.MELODIES)
        await self.go_to_heading(ui_testing.MELODIES)
        await self.press(keybindings.PatternsPage.COPY)
        await self.answer(SONGS)
        self.assertIn(SONGS_RIFF, self.document.setlist().patterns_in_group(SONGS))

    async def test_a_copy_whose_names_would_be_too_long_is_refused_whole_with_the_reason(self):
        names = self.names()
        await self.go_to_heading(ui_testing.MELODIES)
        await self.press(keybindings.PatternsPage.COPY)
        await self.answer(LONG_GROUP)
        self.assertEqual(self.names(), names)
        self.assertIn(errors.ERR_GROUP_COPY_NAME_TOO_LONG.format(name=self.document.setlist().names_in_copied_group(group=ui_testing.MELODIES, new=LONG_GROUP)[ui_testing.TUNE], most=limits.MAX_NAME_LENGTH)[:40], self.text())

    async def test_a_copy_cannot_take_a_groups_name_and_esc_copies_nothing(self):
        names = self.names()
        await self.go_to_heading(ui_testing.MELODIES)
        await self.press(keybindings.PatternsPage.COPY)
        await self.answer(ui_testing.RHYTHMS)
        self.assertIn(ALREADY_IN_USE, self.text())
        await self.press(keybindings.PatternsPage.COPY, Key.ESCAPE)
        self.assertEqual(self.names(), names)

    async def test_the_cursor_opens_a_closed_group_to_stand_on_a_pattern_in_it(self):
        self.document.show_pattern_group(group=ui_testing.RHYTHMS, closed=True)
        self.page.put_cursor_on(ui_testing.BEAT)
        self.assertEqual(self.page.current(), ui_testing.BEAT)
        self.assertFalse(self.document.setlist().is_pattern_group_closed(ui_testing.RHYTHMS))

    async def test_the_closed_groups_in_a_file_are_only_groups_that_exist(self):
        self.document.show_pattern_group(group=ui_testing.RHYTHMS, closed=True)
        self.document.rename_pattern_group(old=ui_testing.RHYTHMS, new=BASSES)
        self.assertEqual(self.document.setlist().get_closed_pattern_groups(), [BASSES])
        self.document.ungroup_patterns(BASSES)
        self.assertNotIn(BASSES, self.document.setlist().get_closed_pattern_groups())
        self.assertNotIn(file_format.CLOSED_PATTERN_GROUPS, self.document.setlist().to_data())
