# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The picker of a new generator's type: the types under headings that open and close, searched by typing, on the Generators page."""

from llamatron.engine.generators import arp as arp_plugin, chords as chords_plugin, hocket as hocket_plugin
from llamatron.engine.generators.arp import strings as arp_strings
from llamatron.engine.generators.chords import strings as chords_strings
from llamatron.engine.generators.hocket import strings as hocket_strings
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.grouped_choice_dialog import GroupedChoiceDialog
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.generators import generator_pages
from llamatron.interface.tracker.screens.generators.generators_page import GeneratorsPage
from llamatron.interface.tracker.screens.shared.plugin_editor import PluginEditor
from llamatron.user_strings import labels, marks, messages
from tests.support.ui_testing import back_key, forward_key, UITest

HEADINGS = sorted([labels.GeneratorGroup.ARRANGEMENT, labels.GeneratorGroup.ARTICULATION, labels.GeneratorGroup.BAND, labels.GeneratorGroup.CHAINS, labels.GeneratorGroup.HARMONY, labels.GeneratorGroup.TIMING, labels.GeneratorGroup.TRANSITIONS, labels.GeneratorGroup.VOICING])
HARMONY_PLACE = HEADINGS.index(labels.GeneratorGroup.HARMONY)
# The test song's Chords generators, one in each mode.
CHORDS_IN_THE_TEST_SONG = 3
# What is typed to search for Hocket: its name in small letters, since a search ignores case.
SEARCHED = hocket_strings.MSG_LABEL.lower()


# How wide the picker's lines are drawn when a test reads them.
PICKER_WIDTH = 60


def heading(*, name, is_open):
    return marks.MSG_GROUP_OF_CHOICES.format(mark=marks.MSG_SECTION_OPEN_MARK if is_open else marks.MSG_SECTION_CLOSED_MARK, name=name)


class TestGeneratorTypePicker(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.GENERATORS, keybindings.ListPage.ADD)
        self.dialog = self.app.screen
        self.assertIsInstance(self.dialog, GroupedChoiceDialog)

    def shown_choices(self):
        # The picker's own rows, since the screen's text holds the Generators page behind it too.
        return [row for row in self.dialog.rows() if row[1] is not None]

    async def test_it_opens_on_closed_headings_in_order_under_its_title(self):
        shown = self.text()
        self.assertIn(messages.MSG_NEW_GENERATOR_KIND_TITLE, shown)
        # The picker's own lines, since the screen's lines hold the Generators page behind it, with headings of its own, too.
        drawn = [line.plain for line in self.dialog.lines(PICKER_WIDTH)]
        places = [_line_holding(lines=drawn, text=heading(name=name, is_open=False)) for name in HEADINGS]
        self.assertEqual(places, sorted(places))
        self.assertEqual(self.shown_choices(), [])

    async def test_every_type_is_under_a_heading_once_by_name(self):
        self.assertEqual(sorted(self.dialog.options), sorted(listing.label for listing in generator_pages.LISTED_PAGES.values()))
        self.assertIn(labels.MSG_CHAIN_LABEL, self.dialog.options)
        self.assertEqual(self.dialog.headings, HEADINGS)
        in_harmony = [listing.label for listing in generator_pages.GENERATOR_PAGES.values() if listing.group == labels.GeneratorGroup.HARMONY]
        self.assertEqual(in_harmony, [chords_strings.MSG_LABEL])
        self.assertEqual(generator_pages.GENERATOR_PAGES[hocket_plugin.SECTION].group, labels.GeneratorGroup.ARRANGEMENT)
        self.assertEqual(generator_pages.GENERATOR_PAGES[arp_plugin.SECTION].group, labels.GeneratorGroup.VOICING)

    async def test_space_or_enter_opens_a_heading_and_closes_it_again(self):
        await self.press(*[Key.DOWN] * HARMONY_PLACE, Key.SPACE)
        self.assertIn(heading(name=labels.GeneratorGroup.HARMONY, is_open=True), self.text())
        self.assertIn(chords_strings.MSG_LABEL, self.text())
        await self.press(Key.ENTER)
        self.assertIn(heading(name=labels.GeneratorGroup.HARMONY, is_open=False), self.text())
        self.assertEqual(self.shown_choices(), [])
        self.assertIsInstance(self.app.screen, GroupedChoiceDialog)

    async def test_enter_on_a_type_makes_one_and_opens_it(self):
        await self.press(*[Key.DOWN] * HARMONY_PLACE, Key.SPACE, Key.DOWN, Key.ENTER)
        self.assertIsInstance(self.app.screen, PluginEditor)
        self.assertEqual(self.app.screen.SECTION, chords_plugin.SECTION)
        self.assertEqual(len(self.document.names_of(chords_plugin.SECTION)), CHORDS_IN_THE_TEST_SONG + 1)

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
        self.assertIn(hocket_strings.MSG_LABEL, shown)
        self.assertNotIn(heading(name=labels.GeneratorGroup.ARRANGEMENT, is_open=False), shown)
        await self.press(Key.ENTER)
        self.assertEqual(len(self.document.names_of(hocket_plugin.SECTION)), 2)

    async def test_erasing_the_search_shows_the_headings_again_on_the_found_types_heading(self):
        await self.type(arp_strings.MSG_LABEL)
        await self.press(*[keybindings.ChoiceDialog.ERASE] * len(arp_strings.MSG_LABEL))
        self.assertEqual(self.dialog.headings[self.dialog.rows()[self.dialog.row][0]], labels.GeneratorGroup.VOICING)
        self.assertIn(heading(name=labels.GeneratorGroup.VOICING, is_open=False), self.text())


def _line_holding(*, lines, text):
    """Return the number of the first of some lines that holds a text."""
    for number, line in enumerate(lines):
        if text in line:
            return number
    raise AssertionError(text)
