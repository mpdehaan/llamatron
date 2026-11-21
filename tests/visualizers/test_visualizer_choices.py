# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests the visualizer modes a set and a song choose: the mode Arrange's visualizer key shows first, the song's over the set's, the modes the set hides, [ and ] stepping through the rest, and every visualizer setting that makes no sense made sensible as it's read."""

import unittest

from llamatron.model.objects.setlist import new_setlist, Setlist
from llamatron.model.vocabulary import file_format
from llamatron.model.vocabulary.file_format import sensible_hidden_visualizers, sensible_visualizer, SetlistSetting, SongSetting
from llamatron.tui import keybindings
from llamatron.tui.dialogs.pick_many_dialog import PickManyDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.set.file_page import FilePage
from llamatron.user_strings import labels, messages
from llamatron.visualizers import modes
from llamatron.visualizers.cycle import Cycle
from llamatron.visualizers.modes import mode_called, mode_options
from tests.support.ui_testing import back_key, forward_key, UITest

GONE = 'tunnel'
NOT_A_LIST = 'plasma'
SPECTRUM = 'spectrum'
PIANO_ROLL = 'piano_roll'
PLASMA = 'plasma'
INSTRUMENT = 'synth'


class TestVisualizerSettings(unittest.TestCase):
    """The set's and the song's visualizer settings, as a file holds them."""

    def test_the_formats_names_are_the_modes_in_order(self):
        self.assertEqual(file_format.VISUALIZER_NAMES, mode_options())

    def test_a_setting_that_makes_no_sense_is_made_sensible_never_refused(self):
        data = new_setlist()
        data[SetlistSetting.VISUALIZER] = GONE
        data[SetlistSetting.HIDDEN_VISUALIZERS] = [GONE, PLASMA, 5]
        next(iter(data['songs'].values()))[SongSetting.VISUALIZER] = [GONE]
        setlist = Setlist.from_data(data=data)
        self.assertIsNone(setlist.get_visualizer())
        self.assertEqual(setlist.get_hidden_visualizers(), [PLASMA])
        self.assertIsNone(setlist.get_songs()[0].get_visualizer())
        self.assertIsNone(sensible_hidden_visualizers(NOT_A_LIST))
        self.assertIsNone(sensible_visualizer(GONE))
        setlist.set_visualizer(GONE)
        self.assertIsNone(setlist.get_visualizer())

    def test_the_song_wins_over_the_set_and_both_are_written_and_read_back(self):
        setlist = Setlist.new()
        song = setlist.get_songs()[0]
        self.assertIsNone(setlist.visualizer_for(song))
        setlist.set_visualizer(SPECTRUM)
        self.assertEqual(setlist.visualizer_for(song), SPECTRUM)
        song.set_visualizer(PIANO_ROLL)
        self.assertEqual(setlist.visualizer_for(song), PIANO_ROLL)
        setlist.set_visualizer_hidden(name=PLASMA, hidden=True)
        again = Setlist.from_data(data=setlist.to_data())
        self.assertEqual(again.get_visualizer(), SPECTRUM)
        self.assertEqual(again.get_songs()[0].get_visualizer(), PIANO_ROLL)
        self.assertEqual(again.get_hidden_visualizers(), [PLASMA])
        again.set_visualizer_hidden(name=PLASMA, hidden=False)
        self.assertNotIn(SetlistSetting.HIDDEN_VISUALIZERS, again.to_data())

    def test_cycle_leaves_out_the_hidden_modes_unless_that_leaves_none(self):
        self.assertNotIn(mode_called(PLASMA), Cycle(hidden=[PLASMA]).order())
        self.assertTrue(Cycle(hidden=file_format.VISUALIZER_NAMES).order())


class TestArrangeVisualizerChoices(UITest):
    """Arrange's visualizer key shows the chosen mode first and leaves out the hidden ones, and [ and ] step through the rest, going round."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.add_instrument(INSTRUMENT)
        self.document.record_edit()
        await self.press(keybindings.MainPage.ARRANGE)
        self.page = self.app.screen

    def showing(self):
        return type(self.page.visualizer)

    async def test_the_key_shows_the_songs_choice_first_else_the_sets_else_the_first(self):
        await self.press(keybindings.ArrangePage.VISUALIZER)
        self.assertIs(self.showing(), modes.MODES[0])
        await self.press(Key.ESCAPE)
        self.document.change(self.document.get_setlist().set_visualizer, SPECTRUM)
        await self.press(keybindings.ArrangePage.VISUALIZER)
        self.assertIs(self.showing(), mode_called(SPECTRUM))
        await self.press(Key.ESCAPE)
        self.document.change(self.document.song().set_visualizer, PIANO_ROLL)
        await self.press(keybindings.ArrangePage.VISUALIZER)
        self.assertIs(self.showing(), mode_called(PIANO_ROLL))

    async def test_brackets_step_through_the_modes_going_round_and_skip_the_hidden(self):
        self.document.change(self.document.get_setlist().set_visualizer_hidden, name=modes.MODES[1].OPTION, hidden=True)
        await self.press(keybindings.ArrangePage.VISUALIZER)
        self.assertIs(self.showing(), modes.MODES[0])
        await self.press(forward_key(keybindings.ArrangePage.STEP_VISUALIZER))
        self.assertIs(self.showing(), modes.MODES[2])
        await self.press(back_key(keybindings.ArrangePage.STEP_VISUALIZER))
        await self.press(back_key(keybindings.ArrangePage.STEP_VISUALIZER))
        self.assertIs(self.showing(), modes.MODES[-1])

    async def test_a_hidden_choice_is_passed_over_and_with_every_mode_hidden_the_key_says_so(self):
        self.document.change(self.document.get_setlist().set_visualizer, SPECTRUM)
        self.document.change(self.document.get_setlist().set_visualizer_hidden, name=SPECTRUM, hidden=True)
        await self.press(keybindings.ArrangePage.VISUALIZER)
        self.assertIs(self.showing(), modes.MODES[0])
        await self.press(Key.ESCAPE)
        for name in file_format.VISUALIZER_NAMES:
            self.document.change(self.document.get_setlist().set_visualizer_hidden, name=name, hidden=True)
        await self.press(keybindings.ArrangePage.VISUALIZER)
        self.assertIsNone(self.page.visualizer)
        self.assertIn(messages.MSG_EVERY_VISUALIZER_HIDDEN, self.text())


class TestHideVisualizersSection(UITest):
    """The File/Global page's Hide Visualizers field opens a list where each mode can be picked."""

    async def test_picking_modes_hides_them_and_esc_changes_nothing(self):
        await self.press(keybindings.MainPage.FILE)
        self.assertIsInstance(self.app.screen, FilePage)
        await self.select_field(labels.MSG_HIDE_VISUALIZERS_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, PickManyDialog)
        place = list(file_format.VISUALIZER_NAMES).index(PLASMA)
        await self.press(*[Key.DOWN] * place, keybindings.PickManyDialog.FLIP, keybindings.PickManyDialog.DONE)
        self.assertEqual(self.document.get_setlist().get_hidden_visualizers(), [PLASMA])
        self.assertIn(mode_called(PLASMA).NAME, self.text())
        await self.press(Key.ENTER, keybindings.PickManyDialog.FLIP, Key.ESCAPE)
        self.assertEqual(self.document.get_setlist().get_hidden_visualizers(), [PLASMA])
        await self.press(Key.ENTER, *[Key.DOWN] * place, keybindings.PickManyDialog.FLIP, keybindings.PickManyDialog.DONE)
        self.assertEqual(self.document.get_setlist().get_hidden_visualizers(), [])


if __name__ == '__main__':
    unittest.main()
