# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Patterns page."""

from llamatron.interface.pages import pattern_list
from llamatron.interface.pages.pattern_list import Listed, PatternTab
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.interface.tracker.dialogs.message_dialog import MessageDialog
from llamatron.interface.tracker.dialogs.prompt_dialog import PromptDialog
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.pattern.pattern_editor import PatternEditor
from llamatron.interface.tracker.screens.set.main_page import MainPage
from llamatron.model.schema import limits
from llamatron.user_strings import errors, labels, marks, messages
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


class PatternsPageTest(UITest):
    """The Patterns page open on the test set: the tune in one group, the beat in another and a third pattern in none."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS)
        self.page = self.app.screen

    def names(self):
        return self.document.get_setlist().get_pattern_names()

    def rows(self):
        """Return what each row of the page is, in order."""
        return [what for what, _ in self.page.remembered_rows()]

    def group_of(self, name):
        return self.document.pattern_group(name)

    def tab_of(self, group):
        """Return the tab a group's patterns are listed in: the group's own, or Ungrouped for the patterns in no group."""
        if group is pattern_list.UNGROUPED:
            return PatternTab(pattern_list.UNGROUPED_TAB)
        return PatternTab(pattern_list.GROUP_TAB, group)

    async def go_to_tab(self, tab):
        """Put the cursor on the row of tabs, with a tab chosen, by the keys a person presses."""
        if not self.page.on_tabs:
            await self.press(keybindings.PatternsPage.TO_TABS)
        for _ in self.page.tabs():
            tabs = self.page.tabs()
            if self.page.chosen() == tab:
                break
            step = forward_key(keybindings.PatternsPage.ALONG_TABS) if tabs.index(tab) > tabs.index(self.page.chosen()) else back_key(keybindings.PatternsPage.ALONG_TABS)
            await self.press(step)
        self.assertEqual(self.page.chosen(), tab)

    async def go_to_row(self, *, tab, listed):
        """Put the cursor on a row of a tab."""
        await self.go_to_tab(tab)
        await self.press(keybindings.PatternsPage.INTO_TAB)
        await self.go_to(listed)

    async def go_to_pattern(self, name):
        await self.go_to_row(tab=self.tab_of(self.group_of(name)), listed=Listed(pattern_list.PATTERN, name))

    async def answer(self, text):
        """Type an answer over what a prompt offers and press ENTER."""
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = text
        await self.press(Key.ENTER)

    def bound(self):
        return [name for item in self.page.key_table() for name in item.keys]



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
        self.assertEqual(self.document.get_setlist().get_pattern(NEW).get_steps(), DEFAULT_STEPS)
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
        self.assertEqual(self.page.search.get_typed(), SEARCH_HIT)
        await self.press(Key.ENTER)
        self.assertEqual(self.page.current(), SEARCH_HIT)
        self.assertEqual(self.page.chosen(), self.tab_of(self.group_of(SEARCH_HIT)))
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

    async def test_a_search_finds_a_pattern_in_another_tab_and_enter_chooses_its_tab(self):
        self.assertNotIn(Listed(pattern_list.PATTERN, ui_testing.BEAT), self.rows())
        await self.press(keybindings.PatternsPage.SEARCH)
        await self.type(ui_testing.BEAT)
        self.assertEqual(self.page.current(), ui_testing.BEAT)
        await self.press(Key.ENTER)
        self.assertEqual(self.page.current(), ui_testing.BEAT)
        self.assertEqual(self.page.chosen(), self.tab_of(ui_testing.RHYTHMS))

    async def test_a_search_left_with_esc_goes_back_to_the_tab_and_the_pattern(self):
        await self.press(keybindings.PatternsPage.SEARCH)
        await self.type(ui_testing.BEAT)
        await self.press(Key.ESCAPE)
        self.assertEqual(self.page.chosen(), self.tab_of(ui_testing.MELODIES))
        self.assertEqual(self.page.current(), ui_testing.TUNE)


class TestPatternGroups(PatternsPageTest):
    """The groups: the tabs, the keys of the row of tabs, the two buttons and the group a pattern is in."""

    async def test_the_tabs_are_the_groups_sorted_then_ungrouped_then_new_and_a_groups_tab_ends_with_its_new_row(self):
        tabs = [PatternTab(pattern_list.GROUP_TAB, ui_testing.MELODIES), PatternTab(pattern_list.GROUP_TAB, ui_testing.RHYTHMS), PatternTab(pattern_list.UNGROUPED_TAB), PatternTab(pattern_list.NEW_TAB)]
        self.assertEqual(self.page.tabs(), tabs)
        self.assertEqual(self.rows(), [Listed(pattern_list.PATTERN, ui_testing.TUNE), Listed(pattern_list.NEW_PATTERN, ui_testing.MELODIES)])
        text = self.text()
        for shown in (ui_testing.MELODIES, ui_testing.RHYTHMS, labels.MSG_UNGROUPED, labels.MSG_NEW_GROUP_TAB, ui_testing.TUNE, marks.MSG_NEW_ROW):
            self.assertIn(shown, text)
        self.assertNotIn(ui_testing.BEAT, text)
        await self.go_to_tab(PatternTab(pattern_list.NEW_TAB))
        self.assertEqual(self.rows(), [Listed(pattern_list.NEW_GROUP, None)])
        self.assertIn(labels.MSG_NEW_GROUP_BUTTON, self.text())

    async def test_a_groups_patterns_are_sorted_with_a_number_at_the_end_read_as_a_number(self):
        for name in reversed(NUMBERED):
            self.document.add_pattern(name=name, group=BASSES)
        await self.go_to_tab(self.tab_of(BASSES))
        self.assertEqual(self.rows()[:len(NUMBERED)], [Listed(pattern_list.PATTERN, name) for name in NUMBERED])

    async def test_the_ungrouped_tab_shows_only_while_a_pattern_is_in_no_group(self):
        self.document.change_pattern(self.document.pattern(ui_testing.OTHER).set_group, ui_testing.RHYTHMS)
        await self.press(Key.DOWN, Key.UP)
        self.assertNotIn(PatternTab(pattern_list.UNGROUPED_TAB), self.page.tabs())
        self.assertNotIn(labels.MSG_UNGROUPED, self.text())

    async def test_tab_and_up_reach_the_row_of_tabs_whose_arrows_choose_a_tab_and_stop_at_the_ends(self):
        await self.press(Key.UP)
        self.assertTrue(self.page.on_tabs)
        self.assertIsNone(self.page.current())
        await self.press(Key.DOWN)
        self.assertFalse(self.page.on_tabs)
        self.assertEqual(self.page.current(), ui_testing.TUNE)
        await self.press(keybindings.PatternsPage.TO_TABS, back_key(keybindings.PatternsPage.ALONG_TABS))
        self.assertEqual(self.page.chosen(), self.tab_of(ui_testing.MELODIES))
        for _ in self.page.tabs():
            await self.press(forward_key(keybindings.PatternsPage.ALONG_TABS))
        self.assertEqual(self.page.chosen(), PatternTab(pattern_list.NEW_TAB))
        await self.go_to_tab(self.tab_of(ui_testing.RHYTHMS))
        await self.press(keybindings.PatternsPage.INTO_TAB)
        self.assertEqual(self.page.current(), ui_testing.BEAT)

    async def test_page_down_and_page_up_choose_the_tab_after_and_before_from_the_list_and_stop_at_the_ends(self):
        await self.press(forward_key(keybindings.PatternsPage.TAB_PAGES))
        self.assertEqual(self.page.chosen(), self.tab_of(ui_testing.RHYTHMS))
        self.assertEqual(self.page.current(), ui_testing.BEAT)
        for _ in self.page.tabs():
            await self.press(forward_key(keybindings.PatternsPage.TAB_PAGES))
        self.assertEqual(self.page.chosen(), PatternTab(pattern_list.NEW_TAB))
        for _ in self.page.tabs():
            await self.press(back_key(keybindings.PatternsPage.TAB_PAGES))
        self.assertEqual(self.page.chosen(), self.tab_of(ui_testing.MELODIES))

    async def test_a_groups_new_row_makes_a_pattern_in_that_group(self):
        await self.go_to_row(tab=self.tab_of(ui_testing.RHYTHMS), listed=Listed(pattern_list.NEW_PATTERN, ui_testing.RHYTHMS))
        self.assertIn(key_name(keybindings.PatternsPage.NEW_PATTERN), self.text())
        await self.press(keybindings.PatternsPage.NEW_PATTERN, keybindings.NewPatternDialog.OK)
        await self.answer(NEW)
        self.assertEqual(self.group_of(NEW), ui_testing.RHYTHMS)
        self.assertIsInstance(self.app.screen, PatternEditor)

    async def test_a_on_a_groups_tab_makes_a_pattern_in_its_group(self):
        await self.go_to_tab(self.tab_of(ui_testing.RHYTHMS))
        await self.press(keybindings.PatternsPage.ADD, keybindings.NewPatternDialog.OK)
        await self.answer(NEW)
        self.assertEqual(self.group_of(NEW), ui_testing.RHYTHMS)

    async def test_the_last_tabs_button_makes_a_group_whose_tab_shows_its_new_row_alone_until_a_pattern_is_made(self):
        before = self.document.get_setlist().to_data()
        await self.go_to_row(tab=PatternTab(pattern_list.NEW_TAB), listed=Listed(pattern_list.NEW_GROUP, None))
        await self.press(keybindings.PatternsPage.NEW_GROUP)
        await self.answer(BASSES)
        self.assertEqual(self.page.chosen(), self.tab_of(BASSES))
        self.assertEqual(self.rows(), [Listed(pattern_list.NEW_PATTERN, BASSES)])
        # A group is only what its patterns hold, so an empty one is not in the set.
        self.assertEqual(self.document.get_setlist().to_data(), before)
        await self.press(keybindings.PatternsPage.NEW_PATTERN, keybindings.NewPatternDialog.OK)
        await self.answer(NEW)
        self.assertEqual(self.group_of(NEW), BASSES)
        self.assertEqual(self.document.get_setlist().get_pattern_groups(), [BASSES, ui_testing.MELODIES, ui_testing.RHYTHMS])

    async def test_enter_on_the_last_tab_makes_a_group_too(self):
        await self.go_to_tab(PatternTab(pattern_list.NEW_TAB))
        await self.press(keybindings.PatternsPage.NEW_GROUP)
        await self.answer(BASSES)
        self.assertEqual(self.page.chosen(), self.tab_of(BASSES))

    async def test_a_new_group_cannot_take_a_groups_name(self):
        await self.go_to_tab(PatternTab(pattern_list.NEW_TAB))
        await self.press(keybindings.PatternsPage.NEW_GROUP)
        await self.answer(ui_testing.MELODIES.upper())
        self.assertIn(ALREADY_IN_USE, self.text())
        self.assertNotIn(self.tab_of(ui_testing.MELODIES.upper()), self.page.tabs())

    async def test_g_moves_a_pattern_to_a_group_picked_from_the_sorted_groups(self):
        await self.press(keybindings.PatternsPage.GROUP)
        dialog = self.app.screen
        self.assertIsInstance(dialog, ChoiceDialog)
        self.assertEqual(dialog.options, [ui_testing.MELODIES, ui_testing.RHYTHMS, labels.MSG_NEW_GROUP_BUTTON])
        self.assertEqual(dialog.options[dialog.cursor.get_place()], ui_testing.MELODIES)
        await self.press(Key.DOWN, Key.ENTER)
        self.assertEqual(self.group_of(ui_testing.TUNE), ui_testing.RHYTHMS)
        self.assertEqual(self.page.current(), ui_testing.TUNE)
        self.assertEqual(self.page.chosen(), self.tab_of(ui_testing.RHYTHMS))
        # The group left with no pattern is gone.
        self.assertNotIn(self.tab_of(ui_testing.MELODIES), self.page.tabs())
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.group_of(ui_testing.TUNE), ui_testing.MELODIES)

    async def test_g_can_make_the_group_and_takes_a_pattern_out_of_ungrouped(self):
        await self.go_to_pattern(ui_testing.OTHER)
        await self.press(keybindings.PatternsPage.GROUP, Key.DOWN, Key.DOWN, Key.ENTER)
        await self.answer(BASSES)
        self.assertEqual(self.group_of(ui_testing.OTHER), BASSES)
        self.assertEqual(self.page.current(), ui_testing.OTHER)
        self.assertNotIn(PatternTab(pattern_list.UNGROUPED_TAB), self.page.tabs())

    async def test_nothing_can_be_added_to_ungrouped_and_its_tab_has_no_group_keys(self):
        await self.go_to_pattern(ui_testing.OTHER)
        self.assertNotIn(first_key(keybindings.PatternsPage.ADD), self.bound())
        self.assertNotIn(Listed(pattern_list.NEW_PATTERN, pattern_list.UNGROUPED), self.rows())
        await self.go_to_tab(PatternTab(pattern_list.UNGROUPED_TAB))
        for binding in (keybindings.PatternsPage.ADD, keybindings.PatternsPage.RENAME, keybindings.PatternsPage.COPY, keybindings.PatternsPage.UNGROUP):
            for key in every_key(binding):
                self.assertNotIn(key, self.bound())

    async def test_n_on_a_groups_tab_renames_the_group_of_every_pattern_in_it_as_one_step(self):
        self.document.add_pattern(name=NEW, group=ui_testing.MELODIES)
        await self.go_to_tab(self.tab_of(ui_testing.MELODIES))
        await self.press(keybindings.PatternsPage.RENAME)
        await self.answer(SONGS)
        self.assertEqual((self.group_of(ui_testing.TUNE), self.group_of(NEW)), (SONGS, SONGS))
        self.assertEqual(self.page.chosen(), self.tab_of(SONGS))
        await self.press(keybindings.Page.UNDO)
        self.assertEqual((self.group_of(ui_testing.TUNE), self.group_of(NEW)), (ui_testing.MELODIES, ui_testing.MELODIES))

    async def test_a_group_cannot_be_renamed_to_another_groups_name(self):
        await self.go_to_tab(self.tab_of(ui_testing.MELODIES))
        await self.press(keybindings.PatternsPage.RENAME)
        await self.answer(ui_testing.RHYTHMS)
        self.assertEqual(self.group_of(ui_testing.TUNE), ui_testing.MELODIES)
        self.assertIn(ALREADY_IN_USE, self.text())

    async def test_bksp_on_a_groups_tab_asks_and_then_ungroups_and_deletes_no_pattern(self):
        names = self.names()
        await self.go_to_tab(self.tab_of(ui_testing.MELODIES))
        await self.press(keybindings.PatternsPage.UNGROUP)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertEqual(self.group_of(ui_testing.TUNE), ui_testing.MELODIES)
        await self.press(keybindings.PatternsPage.UNGROUP, keybindings.ConfirmDialog.YES)
        self.assertIsNone(self.group_of(ui_testing.TUNE))
        self.assertEqual(self.names(), names)
        self.assertEqual(self.page.chosen(), PatternTab(pattern_list.UNGROUPED_TAB))
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.group_of(ui_testing.TUNE), ui_testing.MELODIES)

    async def test_c_on_a_groups_tab_confirms_with_a_name_counted_up_and_copies_every_pattern_as_one_step(self):
        self.document.add_pattern(name=MELODIES_RIFF, group=ui_testing.MELODIES)
        names = self.names()
        await self.go_to_tab(self.tab_of(ui_testing.MELODIES))
        await self.press(keybindings.PatternsPage.COPY)
        dialog = self.app.screen
        self.assertIsInstance(dialog, PromptDialog)
        self.assertEqual((dialog.title, dialog.label, dialog.value), (messages.MSG_COPY_GROUP_TITLE, labels.MSG_NEW_GROUP_NAME_LABEL, MELODIES_COPY))
        self.assertIn(labels.MSG_NEW_GROUP_NAME_LABEL + MELODIES_COPY, self.text())
        await self.press(Key.ENTER)
        # The new group's name goes at the front: joined to a name that lacked the old group's, and in its place where the name began with it.
        self.assertEqual(self.document.get_setlist().patterns_in_group(MELODIES_COPY), [MELODIES_COPY + MELODIES_RIFF[len(ui_testing.MELODIES):], TUNE_IN_COPY])
        self.assertEqual(self.page.chosen(), self.tab_of(MELODIES_COPY))
        self.assertEqual(self.document.get_setlist().get_pattern(TUNE_IN_COPY).to_data(), {**self.document.get_setlist().get_pattern(ui_testing.TUNE).to_data(), **self.document.get_setlist().get_pattern(TUNE_IN_COPY).to_data()})
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.names(), names)

    async def test_a_copy_under_another_name_names_its_patterns_after_it(self):
        self.document.add_pattern(name=MELODIES_RIFF, group=ui_testing.MELODIES)
        await self.go_to_tab(self.tab_of(ui_testing.MELODIES))
        await self.press(keybindings.PatternsPage.COPY)
        await self.answer(SONGS)
        self.assertIn(SONGS_RIFF, self.document.get_setlist().patterns_in_group(SONGS))

    async def test_a_copy_whose_names_would_be_too_long_is_refused_whole_with_the_reason(self):
        names = self.names()
        await self.go_to_tab(self.tab_of(ui_testing.MELODIES))
        await self.press(keybindings.PatternsPage.COPY)
        await self.answer(LONG_GROUP)
        self.assertEqual(self.names(), names)
        self.assertIn(errors.ERR_GROUP_COPY_NAME_TOO_LONG.format(name=self.document.get_setlist().names_in_copied_group(group=ui_testing.MELODIES, new=LONG_GROUP)[ui_testing.TUNE], most=limits.MAX_NAME_LENGTH)[:40], self.text())

    async def test_a_copy_cannot_take_a_groups_name_and_esc_copies_nothing(self):
        names = self.names()
        await self.go_to_tab(self.tab_of(ui_testing.MELODIES))
        await self.press(keybindings.PatternsPage.COPY)
        await self.answer(ui_testing.RHYTHMS)
        self.assertIn(ALREADY_IN_USE, self.text())
        await self.press(keybindings.PatternsPage.COPY, Key.ESCAPE)
        self.assertEqual(self.names(), names)

    async def test_putting_the_cursor_on_a_pattern_chooses_its_groups_tab(self):
        self.page.put_cursor_on(ui_testing.BEAT)
        self.assertEqual(self.page.current(), ui_testing.BEAT)
        self.assertEqual(self.page.chosen(), self.tab_of(ui_testing.RHYTHMS))
