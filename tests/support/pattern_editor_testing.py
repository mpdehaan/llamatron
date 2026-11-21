# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Helpers the tests of the pattern editor share: the class that opens the editor on a pattern, and a section's heading as drawn."""

from llamatron.tui import keybindings
from llamatron.tui.dialogs.grouped_choice_dialog import GroupedChoiceDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.pattern.pattern_editor import munges_in_order
from llamatron.user_strings import labels
from tests.support.ui_testing import UITest

TUNE = 'tune'


async def open_section(*, test, section):
    """Press Tab until the cursor is on a section's heading, and Space to open it if it's closed."""
    editor = test.app.screen
    while editor.row_name() != section:
        await test.press(Key.PAGE_DOWN)
    if not editor.rows_view.section_is_open(section):
        await test.press(Key.SPACE)


async def munge(*, test, choice):
    """Open the munge dialog in a test's editor and pick one of its ways of rearranging the steps."""
    await test.press(keybindings.PatternEditor.MUNGE)
    dialog = test.app.screen
    test.assertIsInstance(dialog, GroupedChoiceDialog)
    order = munges_in_order()
    test.assertEqual(dialog.options, [labels.MSG_MUNGE_CHOICES[place] for place in order])
    # Every heading is opened, so that the choice is reached with the arrows as a person would reach it.
    dialog.opened.update(dialog.headings)
    row = [place for _, place in dialog.rows()].index(order.index(choice))
    await test.press(*([Key.DOWN] * row), Key.ENTER)


class PatternEditorTest(UITest):
    """Opens the tune pattern in the editor, on its rows past the piano roll. Its tests are split across classes so that they run in parallel."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        self.editor = self.app.screen

    def value(self, *, row, step=None):
        return self.document.step_value(name=TUNE, row=row, step=self.editor.step if step is None else step)

    async def go_to_row(self, name):
        """Move the cursor to a row, opening the section that has it first if it's closed."""
        if name not in [row.name for row in self.editor.rows_view.reachable()]:
            await open_section(test=self, section=self.editor.rows_view.section_of(name))
        names = [row.name for row in self.editor.rows_view.reachable()]
        while self.editor.rows_view.row != names.index(name):
            await self.press(Key.DOWN if self.editor.rows_view.row < names.index(name) else Key.UP)
