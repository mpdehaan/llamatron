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
"""The pages that list named things all rename, copy, delete, move and sort the same way (tui/screens/shared/named_list_page.py).

The same checks run on each of them: the Patterns, Scales, Chains, Grooves, Songs, Arpeggiators
and AutoRatchets pages. What a page alone does, like adding, is tested with the page.
"""

from tests.support import ui_testing
from tests.support.ui_testing import UITest, leaf_pages
from llamatron.composition import file_format
from llamatron.composition.file_format import ClipSlotSetting, Section
from llamatron.tui.screens.generators import generator_pages
from llamatron.composition import groove
from llamatron.composition.groove import FactoryGroove
from llamatron.composition import limits
from llamatron.strings import errors, labels, messages, names
from llamatron.composition import setlist
from llamatron.tui import drawing
from llamatron.tui.drawing import fit
from llamatron.tui import keybindings
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.generators.chains_page import ChainsPage
from llamatron.tui.screens.set.grooves_page import GroovesPage
from llamatron.tui.screens.set.instruments_page import InstrumentsPage
from llamatron.tui.screens.shared.named_list_page import NamedListPage
from llamatron.tui.screens.pattern import patterns_page
from llamatron.tui.screens.pattern.patterns_page import PatternsPage
from llamatron.tui.screens.set.scales_page import ScalesPage
from llamatron.tui.screens.set.songs_page import SongsPage
import unittest

RENAMED = 'renamed'
A_GROOVE = 'shuffle'
A_INSTRUMENT = 'synth'
FIRST_SCENE = 0
A_LETTER = 'a'
MORE_THAN_A_NAME_HOLDS = limits.MAX_NAME_LENGTH + 5
# A name an older file could hold, longer than the tracker now lets a person type.
A_LONG_NAME = 'a_very_long_pattern_name_from_an_older_file'
NOTHING_USES_A_SONG = 'nothing in a set names a song, so a song is never in use'
NOTHING_MOVES_ON_A_SORTED_PAGE = 'the page is always sorted, so nothing on it moves or sorts'


class NamedListChecks:
    """What every page that lists named things does with the selected one, checked on the page a test class names.

    A test class gives PAGE, the keys that open the page from the main screen as OPENING, and
    the name the cursor starts on as FIRST, which is one of the section's own.
    """

    __slots__ = ()

    PAGE = None
    OPENING = ()
    FIRST = None
    # Whether the page keeps its rows in an order of its own, so that nothing on it moves or sorts, as the Patterns page does.
    ALWAYS_SORTED = False

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.prepare()
        await self.press(*self.OPENING)
        self.assertIsInstance(self.app.screen, self.PAGE)
        self.app.screen.put_cursor_on(self.FIRST)
        await self.press(Key.DOWN, Key.UP)

    def prepare(self):
        """Give the set what the page needs before the page opens."""

    def make_used(self):
        """Make something use the first thing, and return whether anything can."""
        return True

    def page(self):
        return self.app.screen

    def own_names(self):
        """Return the names of the section's own items, in the set's order."""
        return self.document.setlist().get_item_names(self.PAGE.LISTED_SECTION)

    async def copy_the_first(self):
        """Copy the first thing with the page's key and return the copy's name."""
        before = self.own_names()
        await self.press(self.PAGE.KEYS.COPY)
        return next(name for name in self.own_names() if name not in before)

    async def test_copying_says_what_the_copy_is_called_and_selects_it(self):
        before = self.own_names()
        new = await self.copy_the_first()
        self.assertEqual(self.own_names(), [*before, new])
        self.assertIn(messages.MSG_COPIED_TO.format(name=new), self.text())
        self.assertEqual(self.page().current(), new)

    async def test_renaming_keeps_the_place_and_the_cursor(self):
        before = self.own_names()
        await self.press(self.PAGE.KEYS.RENAME)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.assertIn(self.page_under().rename_title(), self.text())
        self.app.screen.value = RENAMED
        await self.press(Key.ENTER)
        self.assertEqual(self.own_names(), [RENAMED if name == self.FIRST else name for name in before])
        self.assertEqual(self.page().current(), RENAMED)

    async def test_renaming_to_a_name_in_use_is_refused_on_the_status_line(self):
        new = await self.copy_the_first()
        before = self.own_names()
        await self.press(self.PAGE.KEYS.RENAME)
        self.app.screen.value = self.FIRST
        await self.press(Key.ENTER)
        self.assertEqual(self.own_names(), before)
        self.assertIn(errors.ERR_NAME_IN_USE.format(name=self.FIRST), self.text())
        self.assertEqual(self.page().current(), new)

    async def test_deleting_what_nothing_uses_asks_first(self):
        before = self.own_names()
        new = await self.copy_the_first()
        await self.press(self.PAGE.KEYS.DELETE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)
        self.assertIn(messages.MSG_DELETE_QUESTION.format(what=self.page_under().what_is(new)), self.text())
        await self.press(keybindings.ConfirmDialog.NO)
        self.assertEqual(self.own_names(), [*before, new])
        await self.press(self.PAGE.KEYS.DELETE, keybindings.ConfirmDialog.YES)
        self.assertEqual(self.own_names(), before)
        self.assertIsInstance(self.app.screen, self.PAGE)

    async def test_what_is_still_used_cannot_be_deleted(self):
        if not self.make_used():
            self.skipTest(NOTHING_USES_A_SONG)
        before = self.own_names()
        await self.press(Key.DOWN, Key.UP, self.PAGE.KEYS.DELETE)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(errors.ERR_STILL_USED.format(what=self.page_under().what_is(self.FIRST)), self.text())
        await self.press(Key.ENTER)
        self.assertEqual(self.own_names(), before)

    def page_under(self):
        """Return the list page a dialog is open over."""
        return next(page for page in reversed(self.app.pages()) if isinstance(page, self.PAGE))

    async def test_moving_takes_the_cursor_with_the_thing_and_stops_at_the_ends(self):
        if self.ALWAYS_SORTED:
            self.skipTest(NOTHING_MOVES_ON_A_SORTED_PAGE)
        new = await self.copy_the_first()
        before = self.own_names()
        await self.press(self.PAGE.KEYS.MOVE, Key.DOWN, Key.ENTER)
        self.assertEqual(self.own_names(), before)
        await self.press(self.PAGE.KEYS.MOVE, Key.UP, Key.ENTER)
        self.assertEqual(self.own_names(), [*before[:-2], new, before[-2]])
        self.assertEqual(self.page().current(), new)
        await self.press(self.PAGE.KEYS.MOVE, Key.DOWN, Key.ENTER)
        self.assertEqual(self.own_names(), before)
        self.assertEqual(self.page().current(), new)

    async def test_sorting_puts_the_names_in_order_and_keeps_the_cursor_on_its_thing(self):
        if self.ALWAYS_SORTED:
            self.skipTest(NOTHING_MOVES_ON_A_SORTED_PAGE)
        new = await self.copy_the_first()
        while self.own_names()[0] != new:
            await self.press(self.PAGE.KEYS.MOVE, Key.UP, Key.ENTER)
        unsorted = self.own_names()
        await self.press(Key.DOWN, Key.UP)
        self.assertEqual(self.page().current(), new)
        await self.press(self.PAGE.KEYS.SORT)
        self.assertEqual(self.own_names(), sorted(unsorted, key=str.casefold))
        self.assertEqual(self.page().current(), new)

    async def test_each_edit_is_one_step_that_undo_takes_back(self):
        before = self.own_names()
        await self.copy_the_first()
        await self.press(keybindings.Page.UNDO)
        self.assertEqual(self.own_names(), before)
        self.assertIsInstance(self.app.screen, self.PAGE)


class TestNamesAreHeldToTheirLength(UITest):
    """A name is at most MAX_NAME_LENGTH characters as typed, and a list keeps that room for names, so that the columns after them stay close on a wide console."""

    async def test_a_name_typed_stops_at_the_longest_a_name_may_be(self):
        await self.press(keybindings.MainPage.PATTERNS, keybindings.PatternsPage.RENAME)
        self.assertIsInstance(self.app.screen, PromptDialog)
        self.app.screen.value = drawing.NOTHING
        await self.type(A_LETTER * MORE_THAN_A_NAME_HOLDS)
        self.assertEqual(self.app.screen.value, A_LETTER * limits.MAX_NAME_LENGTH)
        await self.press(Key.ENTER)
        self.assertIn(A_LETTER * limits.MAX_NAME_LENGTH, self.document.setlist().get_item_names(Section.PATTERNS))

    async def test_a_new_patterns_name_stops_there_too(self):
        await self.press(keybindings.MainPage.PATTERNS, keybindings.PatternsPage.ADD, keybindings.NewPatternDialog.OK)
        self.app.screen.value = drawing.NOTHING
        await self.type(A_LETTER * MORE_THAN_A_NAME_HOLDS)
        self.assertEqual(len(self.app.screen.value), limits.MAX_NAME_LENGTH)

    async def test_an_older_files_longer_name_is_kept_in_the_prompt_and_takes_no_more(self):
        self.document.rename_named(section=Section.PATTERNS, old=ui_testing.TUNE, new=A_LONG_NAME)
        await self.press(keybindings.MainPage.PATTERNS)
        self.app.screen.put_cursor_on(A_LONG_NAME)
        await self.press(keybindings.PatternsPage.RENAME)
        self.assertEqual(self.app.screen.value, A_LONG_NAME)
        await self.type(A_LETTER)
        self.assertEqual(self.app.screen.value, A_LONG_NAME)
        await self.press(keybindings.PromptDialog.ERASE)
        self.assertEqual(self.app.screen.value, A_LONG_NAME[:-1])

    async def test_a_number_typed_is_not_held_to_a_names_length(self):
        dialog = PromptDialog(title=drawing.NOTHING, value=A_LETTER * limits.MAX_NAME_LENGTH)
        dialog.insert(A_LETTER)
        self.assertEqual(len(dialog.value), limits.MAX_NAME_LENGTH + 1)

    async def test_the_columns_after_the_names_start_right_after_the_room_a_name_has(self):
        await self.press(keybindings.MainPage.PATTERNS)
        heading = next(line for line in self.text().splitlines() if labels.Column.SELECT_PATTERN in line and labels.Column.TYPE in line)
        self.assertEqual(heading.index(labels.Column.TYPE), heading.index(labels.Column.SELECT_PATTERN) + limits.MAX_NAME_LENGTH + len(patterns_page.INDENT) + len(drawing.SPACE))

    async def test_an_older_files_longer_name_is_shown_cut_in_the_list(self):
        self.document.rename_named(section=Section.PATTERNS, old=ui_testing.TUNE, new=A_LONG_NAME)
        await self.press(keybindings.MainPage.PATTERNS)
        self.assertIn(fit(text=patterns_page.INDENT + A_LONG_NAME, width=limits.MAX_NAME_LENGTH + len(patterns_page.INDENT)), self.text())
        self.assertNotIn(A_LONG_NAME, self.text().split(labels.Column.SELECT_PATTERN)[-1])
        self.assertIn(A_LONG_NAME, self.document.setlist().get_item_names(Section.PATTERNS))


class TestPatternsPageAsANamedList(NamedListChecks, UITest):

    PAGE = PatternsPage
    OPENING = (keybindings.MainPage.PATTERNS,)
    FIRST = ui_testing.TUNE
    ALWAYS_SORTED = True


class TestScalesPageAsANamedList(NamedListChecks, UITest):

    PAGE = ScalesPage
    OPENING = (keybindings.MainPage.SCALES,)
    FIRST = setlist.DEFAULT_SCALE


class TestChainsPageAsANamedList(NamedListChecks, UITest):

    PAGE = ChainsPage
    OPENING = (keybindings.MainPage.CHAINS,)
    FIRST = ui_testing.NAMED

    def make_used(self):
        self.document.set_clip_slot_setting(index=FIRST_SCENE, track=ui_testing.LEAD, setting=ClipSlotSetting.CHAIN, value=ui_testing.NAMED)
        return True


class TestGroovesPageAsANamedList(NamedListChecks, UITest):

    PAGE = GroovesPage
    OPENING = (keybindings.MainPage.GROOVES,)
    FIRST = A_GROOVE

    def prepare(self):
        self.document.add_groove(A_GROOVE)

    def make_used(self):
        self.document.set_groove_name(A_GROOVE)
        return True

    async def test_the_factory_grooves_come_first_and_only_the_sets_own_move(self):
        self.assertEqual(self.page().names(), [*groove.FACTORY_GROOVE_NAMES, A_GROOVE])
        self.assertEqual(self.page().own_place(), 0)
        self.page().put_cursor_on(FactoryGroove.SWING_58)
        await self.press(Key.DOWN, Key.UP)
        before = self.page().names()
        await self.press(self.PAGE.KEYS.MOVE, self.PAGE.KEYS.RENAME, self.PAGE.KEYS.DELETE)
        self.assertIsInstance(self.app.screen, GroovesPage)
        self.assertEqual(self.page().names(), before)


class TestInstrumentsPageAsANamedList(NamedListChecks, UITest):

    PAGE = InstrumentsPage
    OPENING = (keybindings.MainPage.INSTRUMENTS,)
    FIRST = A_INSTRUMENT

    def prepare(self):
        self.document.add_instrument(A_INSTRUMENT)

    def make_used(self):
        self.document.set_track_instrument(name=self.document.track_names()[0], instrument=A_INSTRUMENT)
        return True


class TestSongsPageAsANamedList(NamedListChecks, UITest):

    PAGE = SongsPage
    OPENING = (keybindings.MainPage.SONGS,)
    FIRST = names.MSG_DEFAULT_SONG_NAME

    def make_used(self):
        return False


# The test class of each page that lists named things, which the rule below reads.
CHECKED = [
    TestPatternsPageAsANamedList, TestScalesPageAsANamedList, TestChainsPageAsANamedList, TestGroovesPageAsANamedList, TestInstrumentsPageAsANamedList, TestSongsPageAsANamedList,
]
# Every generator section is listed by the Generators page, every kind on one list.
EVERY_NAMED_SECTION_OF_THE_SET = [Section.PATTERNS, Section.SCALES, Section.CHAINS, Section.GROOVES, Section.INSTRUMENTS, Section.SONGS]


class TestEveryNamedListPageIsChecked(unittest.TestCase):

    def test_every_page_that_lists_named_things_has_the_checks(self):
        pages = [page for page in leaf_pages() if issubclass(page, NamedListPage)]
        self.assertEqual(sorted(page.__name__ for page in pages), sorted(checks.PAGE.__name__ for checks in CHECKED))

    def test_every_named_section_of_the_set_has_a_page(self):
        self.assertEqual(sorted(checks.PAGE.LISTED_SECTION for checks in CHECKED), sorted(EVERY_NAMED_SECTION_OF_THE_SET))
        self.assertEqual(sorted(generator_pages.GENERATOR_PAGES), sorted(file_format.NAMED_GENERATORS.values()))

    def test_every_page_says_how_it_words_a_rename_and_a_question(self):
        for checks in CHECKED:
            page = checks.PAGE
            self.assertIsNotNone(page.LISTED_SECTION, page.__name__)
            self.assertTrue(page.RENAME_PROMPT is not None or page.rename_title is not NamedListPage.rename_title, page.__name__)
            self.assertTrue(page.WHAT is not None or page.what_is is not NamedListPage.what_is, page.__name__)


if __name__ == '__main__':
    unittest.main()
