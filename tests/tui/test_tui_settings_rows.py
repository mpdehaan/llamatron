# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What list pages and settings pages share: the + row, the arrows on a setting, the mark of a field that opens a list, and a page's row of buttons."""

from fractions import Fraction

from llamatron.composition import defaults, setlist
from llamatron.composition.file_format import FollowAction, OctaveLabels, Section, SetlistSetting
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.set.grooves_page import GroovesPage
from llamatron.tui.screens.set.instruments_page import InstrumentsPage
from llamatron.tui.screens.set.scales_page import ScalesPage
from llamatron.user_strings import labels, marks
from tests.support.ui_testing import UITest

TEMPO = 'Tempo'
STEP_SIZE = 'Step size'


class TestPlusRow(UITest):
    """Every list has a + at the bottom, where ENTER does the same as pressing +."""

    async def test_every_list_has_one(self):
        for keys, page in [
            ([keybindings.MainPage.SCALES], ScalesPage), ([keybindings.MainPage.GROOVES], GroovesPage),
            ([keybindings.MainPage.INSTRUMENTS], InstrumentsPage),
        ]:
            await self.press(*keys)
            self.assertIsInstance(self.app.screen, page)
            self.assertEqual(self.app.screen.rows_with_plus()[-1][0], None, page)
            await self.press(Key.ESCAPE)

    async def test_down_past_the_last_row_goes_to_it_and_up_from_the_top_stays_there(self):
        names = self.document.get_setlist().get_scale_names()
        await self.press(keybindings.MainPage.SCALES, Key.UP)
        self.assertEqual(self.app.screen.current(), names[0])
        await self.press(*[Key.DOWN] * len(names))
        self.assertIsNone(self.app.screen.current())
        # Down on the + row stays there too.
        await self.press(Key.DOWN)
        self.assertIsNone(self.app.screen.current())

    async def test_an_empty_list_starts_on_it(self):
        self.empty_the_arrangement()
        for name in self.document.song().get_pattern_names():
            self.document.delete_named(section=Section.PATTERNS, name=name)
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER)
        self.assertIsInstance(self.app.screen, PromptDialog)

    async def test_backspace_and_copy_do_nothing_on_it(self):
        names = self.document.get_setlist().get_scale_names()
        await self.press(keybindings.MainPage.SCALES, *[Key.DOWN] * len(names), Key.BACKSPACE, keybindings.ScalesPage.COPY, keybindings.ScalesPage.MOVE)
        self.assertEqual(self.document.get_setlist().get_scale_names(), names)
        self.assertIsInstance(self.app.screen, ScalesPage)

    async def test_lists_that_cannot_add_have_none(self):
        await self.press(keybindings.MainPage.OPEN_SET_HERE)
        self.assertEqual(len(self.app.screen.rows_with_plus()), len(self.app.screen.remembered_rows()))

    async def test_arrange_has_one_for_scenes(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.DOWN, Key.DOWN)
        self.assertTrue(self.app.screen.on_plus_row())
        self.assertNotIn('« Bksp »', self.text())
        await self.press(Key.ENTER)
        self.assertEqual(len(self.document.song().get_scenes()), 3)
        self.assertEqual(self.app.screen.row, 2)
        self.assertEqual(self.document.song().get_scenes()[2].get_track_names(), [])

    async def test_arrange_with_no_scenes_starts_on_it(self):
        self.empty_the_arrangement()
        await self.press(keybindings.MainPage.ARRANGE, Key.ENTER)
        self.assertEqual(len(self.document.song().get_scenes()), 1)


class TestSettingArrows(UITest):

    async def test_left_and_right_do_the_same_as_minus_and_plus(self):
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        await self.select_field(TEMPO)
        await self.press(Key.RIGHT, Key.RIGHT, Key.LEFT)
        self.assertEqual(self.document.song().get_tempo(), 121)

    async def test_on_every_song_setting_with_a_value_to_step(self):
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        await self.select_field(labels.MSG_SCALE_LABEL)
        await self.press(Key.LEFT)
        self.assertIsNone(self.document.song().get_scale_name())
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.song().get_scale_name(), setlist.DEFAULT_SCALE)

    async def test_on_every_set_setting_with_a_value_to_step(self):
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(STEP_SIZE)
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.song().get_step_size(), Fraction(1, 8))
        await self.select_field(labels.MSG_DEFAULT_OCTAVE_LABEL)
        await self.press(Key.LEFT)
        self.assertEqual(self.document.song().get_default_octave(), defaults.DEFAULT_OCTAVE - 1)
        await self.select_field(labels.MSG_DEFAULT_DRUM_OCTAVE_LABEL)
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.song().get_default_drum_octave(), defaults.DEFAULT_DRUM_OCTAVE + 1)
        await self.select_field(labels.MSG_OCTAVE_LABELS_LABEL)
        await self.press(Key.RIGHT)
        self.assertEqual(self.document.song().get_octave_labels(), OctaveLabels.LLAMATRON)
        await self.press(Key.LEFT)
        self.assertEqual(self.document.song().get_octave_labels(), OctaveLabels.LIVE)

    async def test_default_follow_action_is_chosen_from_a_list_and_written_only_when_set(self):
        # Real-time playback alone reads it, and a set that never sets it writes nothing, so the demos stay as they are.
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(labels.MSG_DEFAULT_FOLLOW_ACTION_LABEL)
        self.assertEqual(self.document.get_setlist().get_default_follow_action(), FollowAction.WITH_SCENE)
        self.assertNotIn(SetlistSetting.DEFAULT_FOLLOW_ACTION, self.document.get_setlist().to_data())
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.press(Key.DOWN, Key.ENTER)
        self.assertEqual(self.document.get_setlist().get_default_follow_action(), FollowAction.NEXT)
        self.assertEqual(self.document.get_setlist().to_data()[SetlistSetting.DEFAULT_FOLLOW_ACTION], FollowAction.NEXT)
        await self.press(Key.ENTER, Key.DOWN, Key.ENTER)
        self.assertEqual(self.document.get_setlist().get_default_follow_action(), FollowAction.OFF)

    async def test_octave_labels_are_chosen_from_a_list(self):
        await self.press(keybindings.MainPage.FILE)
        await self.select_field(labels.MSG_OCTAVE_LABELS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.press(Key.DOWN, Key.ENTER)
        self.assertEqual(self.document.song().get_octave_labels(), OctaveLabels.LLAMATRON)


class TestPickerMark(UITest):
    """A settings field whose ENTER opens a list shows a dim mark after its value; a typed one shows none."""

    async def test_scale_shows_the_mark_and_tempo_does_not(self):
        await self.press(keybindings.MainPage.SONGS, Key.ENTER)
        lines = self.text().splitlines()
        self.assertTrue(next(line for line in lines if labels.MSG_SCALE_LABEL in line).rstrip().endswith(marks.MSG_PICKER_MARK))
        self.assertNotIn(marks.MSG_PICKER_MARK, next(line for line in lines if labels.MSG_TEMPO_LABEL in line))


class TestButtonRowOnASettingsPage(UITest):
    """A settings page's buttons are one row under its settings: Down from the last setting reaches the first, Left and Right
    move along them, Up from any goes back to the last setting, and Down on them stays."""

    async def test_the_arrows_reach_and_leave_the_buttons(self):
        await self.press(keybindings.MainPage.FILE)
        page = self.app.screen
        first_button = page.first_button_place()
        await self.press(*[Key.DOWN] * len(page.shown_fields()))
        self.assertEqual(page.cursor.get_place(), first_button)
        await self.press(Key.DOWN, Key.RIGHT)
        self.assertEqual(page.cursor.get_place(), first_button + 1)
        await self.press(Key.RIGHT, Key.RIGHT)
        self.assertEqual(page.cursor.get_place(), len(page.shown_fields()) - 1)
        await self.press(Key.UP)
        self.assertEqual(page.cursor.get_place(), first_button - 1)
