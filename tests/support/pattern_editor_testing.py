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

"""Helpers the tests of the pattern editor share: the class that opens the editor on a pattern, and a section's heading as drawn."""

from tests.support.ui_testing import UITest
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.pattern_editor import Reconfigure
from llamatron.strings.labels import MSG_MUNGE_CHOICES
from llamatron.tui import keybindings

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
    await test.reconfigure(Reconfigure.MUNGE)
    test.assertIsInstance(test.app.screen, ChoiceDialog)
    test.assertEqual(test.app.screen.options, MSG_MUNGE_CHOICES)
    await test.press(*([Key.DOWN] * choice), Key.ENTER)


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
