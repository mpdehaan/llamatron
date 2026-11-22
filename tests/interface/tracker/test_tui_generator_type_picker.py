# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The picker of a new generator's type, on the Generators page: every type once, a chain among them, sorted by name, searched by
typing, ENTER making one of the type and opening it."""

from llamatron.engine.generators import chords as chords_plugin, hocket as hocket_plugin
from llamatron.engine.generators.chords import strings as chords_strings
from llamatron.engine.generators.hocket import strings as hocket_strings
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.generators import generator_pages
from llamatron.interface.tracker.screens.shared.plugin_editor import PluginEditor
from llamatron.user_strings import labels, messages
from tests.support.ui_testing import UITest

# The test song's Chords generators, one in each mode, and its Hocket.
CHORDS_IN_THE_TEST_SONG = 3
HOCKETS_IN_THE_TEST_SONG = 1
# What is typed to search for Hocket: its name in small letters, since a search ignores case.
SEARCHED = hocket_strings.MSG_LABEL.lower()


class TestGeneratorTypePicker(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.GENERATORS, keybindings.ListPage.ADD)
        self.dialog = self.app.screen
        self.assertIsInstance(self.dialog, ChoiceDialog)

    async def test_every_type_is_listed_once_sorted_by_name_under_its_title(self):
        self.assertIn(messages.MSG_NEW_GENERATOR_KIND_TITLE, self.text())
        names = [listing.label for listing in generator_pages.LISTED_PAGES.values()]
        self.assertEqual(list(self.dialog.options), sorted(names, key=str.casefold))
        self.assertIn(labels.MSG_CHAIN_LABEL, self.dialog.options)

    async def test_enter_on_a_type_makes_one_and_opens_it(self):
        await self.pick(chords_strings.MSG_LABEL)
        self.assertIsInstance(self.app.screen, PluginEditor)
        self.assertEqual(self.app.screen.SECTION, chords_plugin.SECTION)
        self.assertEqual(len(self.document.names_of(chords_plugin.SECTION)), CHORDS_IN_THE_TEST_SONG + 1)

    async def test_typing_searches_the_types_and_enter_picks(self):
        await self.type(SEARCHED)
        self.assertEqual(self.dialog.options[self.dialog.cursor.get_place()], hocket_strings.MSG_LABEL)
        await self.press(Key.ENTER)
        self.assertEqual(len(self.document.names_of(hocket_plugin.SECTION)), HOCKETS_IN_THE_TEST_SONG + 1)
