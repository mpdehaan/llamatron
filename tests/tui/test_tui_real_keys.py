# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Keys as a terminal sends them, and the function keys."""

from llamatron.composition.file_format import Row
from llamatron.tui import keybindings
from llamatron.tui.dialogs.about_dialog import AboutDialog
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.help_dialog import HelpDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.dialogs.quit_dialog import QuitDialog
from llamatron.tui.key_table import first_key
from llamatron.tui.keys import Key, RowSection
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor
from llamatron.tui.screens.pattern.patterns_page import PatternsPage
from llamatron.tui.screens.set.main_page import MainPage
from llamatron.user_strings import labels
from tests.support.ui_testing import key_of, UITest

SET_FILE = 'my_set.yml'
QUARTER = '1/4'
EIGHTH = '1/8'
DESCRIPTION_KEY = 'd'
TUNE = 'tune'
SCENE_ONE = 'one'
SCENE_TWO = 'two'
LEAD = 'lead'
DRUMS = 'drums'


class TestRealKeys(UITest):
    """Presses keys the slow way, through the same path that a terminal's keys take."""

    async def test_keys_arrive_with_the_names_the_screens_expect(self):
        await self.pilot.press(first_key(keybindings.MainPage.PATTERNS).upper())
        self.assertIsInstance(self.app.screen, PatternsPage)
        await self.pilot.press(Key.ENTER)
        editor = self.app.screen
        self.assertIsInstance(editor, PatternEditor)
        # The roll comes first, with the cursor on the first note's row: Space a row up places the second degree, then Tab reaches the rows and their digits.
        await self.pilot.press(Key.RIGHT, Key.UP, Key.SPACE)
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.DEGREE, step=1), 2)
        await self.pilot.press(first_key(keybindings.PatternEditor.TO_EDITOR), '5')
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.DEGREE, step=1), 5)
        # PgDn reaches the first section's heading, and Down from Degree reaches Gate, in the Timing section, which is open at the start; placing the note left it blank, one step.
        await self.pilot.press(Key.PAGE_DOWN)
        self.assertEqual(editor.row_name(), RowSection.BASICS)
        names = [row.name for row in editor.rows_view.reachable()]
        self.assertIn(Row.GATE, names)
        await self.pilot.press(*[Key.DOWN] * (names.index(Row.GATE) - names.index(editor.row_name())), key_of(binding=keybindings.GateRow.MORE, key=Key.PLUS))
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.GATE, step=1), QUARTER)
        await self.pilot.press(key_of(binding=keybindings.GateRow.LESS, key=Key.MINUS))
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.GATE, step=1), EIGHTH)
        await self.pilot.press(Key.DOWN, Key.SPACE)
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.DOT, step=1), DESCRIPTION_KEY)
        # Up to #/b, in the Basics section above.
        await self.pilot.press(*[Key.UP] * (names.index(Row.DOT) - names.index(Row.ACCIDENTAL)), Key.SPACE)
        self.assertEqual(self.document.step_value(name=TUNE, row=Row.ACCIDENTAL, step=1), '#')
        await self.pilot.press(Key.BACKSPACE)
        self.assertIsNone(self.document.step_value(name=TUNE, row=Row.ACCIDENTAL, step=1))
        await self.pilot.press(Key.ESCAPE, Key.ESCAPE)
        self.assertIsInstance(self.app.screen, MainPage)
        await self.pilot.press(first_key(keybindings.MainPage.PATTERNS))
        self.assertIsInstance(self.app.screen, PatternsPage)
        await self.pilot.press(Key.ESCAPE)
        self.assertIsInstance(self.app.screen, MainPage)

    async def test_the_plain_keys_that_move_scenes_and_tracks_arrive_from_a_terminal(self):
        # Textual's own key handling delivers M and the arrows, which need no modifier a terminal might keep.
        await self.pilot.press(first_key(keybindings.MainPage.ARRANGE), first_key(keybindings.ArrangePage.MOVE_SCENE), Key.DOWN, Key.ENTER)
        self.assertEqual([scene.get_name() for scene in self.document.song().get_scenes()], [SCENE_TWO, SCENE_ONE])
        await self.pilot.press(Key.UP, Key.UP)
        while self.app.screen.track() != LEAD:
            await self.pilot.press(Key.LEFT)
        await self.pilot.press(first_key(keybindings.ArrangePage.MOVE_TRACK), Key.RIGHT, Key.ENTER)
        self.assertEqual(self.document.song().get_track_names(), [DRUMS, LEAD])
        await self.pilot.press(first_key(keybindings.ArrangePage.MOVE_TRACK), Key.LEFT, Key.ENTER)
        self.assertEqual(self.document.song().get_track_names(), [LEAD, DRUMS])

    async def test_q_asks_too(self):
        self.document.changed()
        await self.pilot.press(first_key(keybindings.MainPage.QUIT))
        await self.pilot.pause()
        self.assertIsInstance(self.app.screen, QuitDialog)

    async def test_the_global_control_and_function_keys_work_from_a_terminal(self):
        # A terminal sends a control key with an unprintable character and a function key with none,
        # so these can only be matched by name: a shortcut through the test helper once hid that.
        await self.pilot.press(first_key(keybindings.MainPage.PATTERNS), Key.CTRL_S)
        await self.pilot.pause()
        self.assertIsInstance(self.app.screen, PromptDialog)
        # Exports need a saved set, so the set is saved before X is tried.
        self.document.save(path=SET_FILE)
        await self.pilot.press(Key.ESCAPE, Key.CTRL_X)
        await self.pilot.pause()
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, labels.MSG_EXPORT_CHOICES)
        await self.pilot.press(Key.ESCAPE, Key.F1)
        await self.pilot.pause()
        self.assertIsInstance(self.app.screen, HelpDialog)


class TestFunctionKeys(UITest):
    """F2 renames, as on Windows, and F3 opens About; N still renames, since a stock Mac needs fn for F2."""

    async def test_f2_renames_on_a_list_and_on_a_page_with_a_name_and_f3_opens_about(self):
        await self.press(keybindings.MainPage.PATTERNS)
        await self.pilot.press(Key.F2)
        await self.settle()
        self.assertIsInstance(self.app.screen, PromptDialog)
        await self.press(Key.ESCAPE, Key.ESCAPE, keybindings.MainPage.SONGS, Key.ENTER, Key.DOWN, Key.DOWN)
        await self.pilot.press(Key.F2)
        await self.settle()
        self.assertIsInstance(self.app.screen, PromptDialog)
        await self.press(Key.ESCAPE)
        await self.pilot.press(Key.F3)
        await self.settle()
        self.assertIsInstance(self.app.screen, AboutDialog)
