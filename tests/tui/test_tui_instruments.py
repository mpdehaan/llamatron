# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Instruments page, the instrument editor, the Instrument field on the track editor and the main screen's Real Time switch."""

from unittest import mock

from llamatron.composition import defaults, file_format, limits
from llamatron.composition.file_format import Section, SetlistSetting, TrackSetting
from llamatron.music import midi
from llamatron.realtime import fluidsynth
from llamatron.strings import errors, labels, marks, messages, names
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.dialogs.sound_dialog import SoundDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.set.instrument_editor import InstrumentEditor, sound_text
from llamatron.tui.screens.set.instruments_page import InstrumentsPage
from llamatron.tui.screens.set.main_page import MainPage
from llamatron.tui.screens.shared.field import Heading
from tests.support import ui_testing
from tests.support.rendering import render_song
from tests.support.ui_testing import UITest

INSTRUMENT_1 = names.MSG_NUMBERED_NAME.format(base=names.MSG_NEW_INSTRUMENT_WORD, number=1)
INSTRUMENT_2 = names.MSG_NUMBERED_NAME.format(base=names.MSG_NEW_INSTRUMENT_WORD, number=2)
SYNTH = 'synth'
# The ports a computer might have, as python-rtmidi lists them, which the tests pretend are there.
PORTS = ['IAC Driver Bus 1', 'Analog Four']
GONE_PORT = 'Old Synth'
# Where the editor asks for the ports.
PORT_NAMES = 'llamatron.tui.transport.output_port_names'
SEED = 1


class TestInstrumentsPage(UITest):
    """The list of instruments, with the device, channel and uses of each."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.INSTRUMENTS)
        self.assertIsInstance(self.app.screen, InstrumentsPage)

    def instruments(self):
        return self.document.get_setlist().get_instrument_names()

    async def test_a_adds_a_numbered_instrument_with_no_device_and_opens_it(self):
        await self.press(keybindings.InstrumentsPage.ADD)
        self.assertIsInstance(self.app.screen, InstrumentEditor)
        self.assertEqual(self.instruments(), [INSTRUMENT_1])
        instrument = self.document.get_setlist().get_instrument(INSTRUMENT_1)
        self.assertIsNone(instrument.get_device())
        self.assertEqual(instrument.get_channel(), defaults.DEFAULT_CHANNEL)
        await self.press(Key.ESCAPE, keybindings.InstrumentsPage.ADD, Key.ESCAPE)
        self.assertEqual(self.instruments(), [INSTRUMENT_1, INSTRUMENT_2])

    async def test_the_list_shows_each_instruments_device_channel_and_uses(self):
        self.document.add_instrument(SYNTH)
        self.document.change(self.document.get_setlist().get_instrument(SYNTH).set_device, PORTS[0])
        self.document.change(self.document.get_setlist().get_instrument(SYNTH).set_channel, midi.MAX_CHANNEL)
        self.document.set_track_instrument(name=ui_testing.LEAD, instrument=SYNTH)
        await self.press(Key.DOWN, Key.UP)
        rows = dict(self.app.screen.rows())
        self.assertEqual(rows[SYNTH], [SYNTH, PORTS[0], midi.MAX_CHANNEL, 1])
        self.document.add_instrument(INSTRUMENT_1)
        await self.press(Key.DOWN, Key.UP)
        self.assertEqual(dict(self.app.screen.rows())[INSTRUMENT_1], [INSTRUMENT_1, marks.MSG_NO_DEVICE_SHOWN, defaults.DEFAULT_CHANNEL, 0])

    async def test_the_first_instrument_turns_real_time_on_and_deleting_the_last_turns_it_off(self):
        self.assertFalse(self.document.get_setlist().is_real_time())
        await self.press(keybindings.InstrumentsPage.ADD, Key.ESCAPE, keybindings.InstrumentsPage.ADD, Key.ESCAPE)
        self.assertTrue(self.document.get_setlist().is_real_time())
        await self.press(keybindings.InstrumentsPage.DELETE, keybindings.ConfirmDialog.YES)
        self.assertEqual(self.instruments(), [INSTRUMENT_1])
        self.assertTrue(self.document.get_setlist().is_real_time())
        self.app.screen.put_cursor_on(INSTRUMENT_1)
        await self.press(keybindings.InstrumentsPage.DELETE, keybindings.ConfirmDialog.YES)
        self.assertEqual(self.instruments(), [])
        self.assertFalse(self.document.get_setlist().is_real_time())

    async def test_an_instrument_a_track_plays_through_cannot_be_deleted_and_a_rename_follows(self):
        self.document.add_instrument(SYNTH)
        self.document.set_track_instrument(name=ui_testing.LEAD, instrument=SYNTH)
        await self.press(Key.DOWN, Key.UP, keybindings.InstrumentsPage.DELETE)
        self.assertIsInstance(self.app.screen, MessageDialog)
        await self.press(Key.ESCAPE)
        self.assertEqual(self.instruments(), [SYNTH])
        await self.press(keybindings.InstrumentsPage.RENAME, *[Key.BACKSPACE] * len(SYNTH))
        await self.type(INSTRUMENT_2)
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_track(ui_testing.LEAD).get_instrument_name(), INSTRUMENT_2)
        # No export reads an instrument, so the song still renders with one.
        self.assertTrue(render_song(self.document.song(), seed=SEED).get_rows())


class TestInstrumentEditor(UITest):
    """One instrument's name, device and channel."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.add_instrument(SYNTH)
        await self.press(keybindings.MainPage.INSTRUMENTS, Key.ENTER)
        self.assertIsInstance(self.app.screen, InstrumentEditor)

    def instrument(self):
        return self.document.get_setlist().get_instrument(SYNTH)

    def field_text(self, label):
        return next(field.value() for field in self.app.screen.fields() if field.label == label)

    async def test_the_default_velocity_and_the_accent_are_stepped_and_cleared(self):
        self.assertEqual(self.field_text(labels.MSG_DEFAULT_VELOCITY_LABEL), defaults.DEFAULT_VELOCITY)
        await self.select_field(labels.MSG_DEFAULT_VELOCITY_LABEL)
        await self.press(keybindings.InstrumentEditor.LESS)
        self.assertEqual(self.instrument().get_default_velocity(), defaults.DEFAULT_VELOCITY - 1)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.instrument().get_default_velocity())
        self.assertEqual(self.field_text(labels.MSG_ACCENT_LABEL), marks.MSG_ACCENT_SHOWN.format(accent=defaults.DEFAULT_INSTRUMENT_ACCENT))
        await self.select_field(labels.MSG_ACCENT_LABEL)
        await self.press(keybindings.InstrumentEditor.MORE)
        self.assertEqual(self.instrument().get_accent(), defaults.DEFAULT_INSTRUMENT_ACCENT + 1)
        await self.press(Key.BACKSPACE)
        self.assertIsNone(self.instrument().get_written_accent())

    async def test_the_gm_sound_is_chosen_from_its_families_and_stepped(self):
        self.assertEqual(self.field_text(labels.MSG_GM_SOUND_LABEL), marks.MSG_NONE_SHOWN)
        await self.select_field(labels.MSG_GM_SOUND_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, SoundDialog)
        await self.press(Key.DOWN, Key.ENTER, Key.ENTER)
        self.assertEqual(self.instrument().get_gm_sound(), limits.MIN_GM_SOUND)
        self.assertEqual(self.field_text(labels.MSG_GM_SOUND_LABEL), sound_text(limits.MIN_GM_SOUND))
        await self.press(keybindings.InstrumentEditor.MORE)
        self.assertEqual(self.instrument().get_gm_sound(), limits.MIN_GM_SOUND + 1)
        await self.press(keybindings.InstrumentEditor.LESS, keybindings.InstrumentEditor.LESS)
        self.assertIsNone(self.instrument().get_gm_sound())
        await self.press(keybindings.InstrumentEditor.MORE, keybindings.FieldPage.CLEAR)
        self.assertIsNone(self.instrument().get_gm_sound())

    async def test_the_device_is_chosen_from_fluidsynth_and_the_computers_ports_sorted_with_none_first(self):
        self.assertEqual(self.field_text(labels.MSG_DEVICE_LABEL), marks.MSG_NO_DEVICE_SHOWN)
        with mock.patch(PORT_NAMES, return_value=list(PORTS)):
            await self.select_field(labels.MSG_DEVICE_LABEL)
            await self.press(Key.ENTER)
            self.assertIsInstance(self.app.screen, ChoiceDialog)
            self.assertEqual(self.app.screen.options, [marks.MSG_NO_DEVICE_SHOWN, file_format.FLUIDSYNTH_DEVICE, *sorted(PORTS)])
            await self.press(Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER)
        self.assertEqual(self.instrument().get_device(), sorted(PORTS)[1])
        self.assertEqual(self.field_text(labels.MSG_DEVICE_LABEL), sorted(PORTS)[1])
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertIsNone(self.instrument().get_device())

    async def test_a_device_that_has_gone_is_still_offered_so_that_it_can_be_kept(self):
        self.document.change(self.document.get_setlist().get_instrument(SYNTH).set_device, GONE_PORT)
        with mock.patch(PORT_NAMES, return_value=list(PORTS)):
            await self.select_field(labels.MSG_DEVICE_LABEL)
            await self.press(Key.ENTER)
            self.assertEqual(self.app.screen.options, [marks.MSG_NO_DEVICE_SHOWN, file_format.FLUIDSYNTH_DEVICE, *sorted([*PORTS, GONE_PORT])])
            self.assertEqual(self.app.screen.cursor.get_place(), self.app.screen.options.index(GONE_PORT))
            await self.press(Key.ESCAPE)
        self.assertEqual(self.instrument().get_device(), GONE_PORT)

    async def test_choosing_fluidsynth_makes_the_channel_auto_with_nothing_to_change(self):
        with mock.patch(PORT_NAMES, return_value=[*PORTS, fluidsynth.FLUIDSYNTH_PORT]):
            await self.select_field(labels.MSG_DEVICE_LABEL)
            await self.press(Key.ENTER)
            # The tracker's own FluidSynth port is FluidSynth, chosen as itself, never offered as a port.
            self.assertNotIn(fluidsynth.FLUIDSYNTH_PORT, self.app.screen.options)
            await self.press(Key.DOWN, Key.ENTER)
        self.assertEqual(self.instrument().get_device(), file_format.FLUIDSYNTH_DEVICE)
        self.assertTrue(self.instrument().uses_fluidsynth())
        self.assertEqual(self.field_text(labels.MSG_CHANNEL_LABEL), marks.MSG_AUTO_CHANNEL_SHOWN)
        await self.select_field(labels.MSG_CHANNEL_LABEL)
        await self.press(keybindings.FieldPage.MORE, Key.ENTER)
        self.assertEqual(self.instrument().get_channel(), defaults.DEFAULT_CHANNEL)
        await self.select_field(labels.MSG_DEVICE_LABEL)
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertNotEqual(self.field_text(labels.MSG_CHANNEL_LABEL), marks.MSG_AUTO_CHANNEL_SHOWN)

    async def test_the_channel_steps_and_types_between_1_and_16(self):
        await self.select_field(labels.MSG_CHANNEL_LABEL)
        await self.press(keybindings.FieldPage.LESS)
        self.assertEqual(self.instrument().get_channel(), midi.MIN_CHANNEL)
        for _ in range(midi.MAX_CHANNEL + 1):
            await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.instrument().get_channel(), midi.MAX_CHANNEL)
        await self.press(Key.ENTER, *[Key.BACKSPACE] * len(str(midi.MAX_CHANNEL)))
        await self.type(str(defaults.DEFAULT_CHANNEL + 2))
        await self.press(Key.ENTER)
        self.assertEqual(self.instrument().get_channel(), defaults.DEFAULT_CHANNEL + 2)
        self.assertEqual(self.document.get_setlist().to_data()[Section.INSTRUMENTS][SYNTH], {'channel': defaults.DEFAULT_CHANNEL + 2})


class TestTrackInstrumentField(UITest):
    """The Instrument field at the bottom of the track editor."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.add_instrument(SYNTH)
        self.document.add_instrument(INSTRUMENT_1)
        await self.press(keybindings.MainPage.ARRANGE, Key.UP, Key.RIGHT, Key.ENTER)

    def track(self):
        return self.document.song().get_track(ui_testing.LEAD)

    async def test_it_is_chosen_from_the_sets_instruments_with_none_first_and_bksp_clears_it(self):
        await self.select_field(labels.MSG_INSTRUMENT_LABEL)
        # Instrument is the last setting, and only the + Strum section comes after it.
        fields = self.app.screen.fields()
        first_heading = next(place for place, field in enumerate(fields) if isinstance(field, Heading))
        self.assertEqual(fields[first_heading - 1].label, labels.MSG_INSTRUMENT_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, [marks.MSG_NONE_SHOWN, INSTRUMENT_1, SYNTH])
        await self.press(Key.DOWN, Key.DOWN, Key.ENTER)
        self.assertEqual(self.track().get_instrument_name(), SYNTH)
        self.assertEqual(self.document.get_setlist().to_data()[Section.SONGS][self.document.get_current_song_name()][Section.TRACKS][ui_testing.LEAD][TrackSetting.INSTRUMENT], SYNTH)
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertIsNone(self.track().get_instrument_name())


class TestRealTimeSwitch(UITest):
    """The main screen's Real Time cell: a switch with a mark where a page's cell has its count."""

    def cell(self):
        page = self.app.screen
        self.assertIsInstance(page, MainPage)
        return next(item for item in page.menu_items() if item.binding is keybindings.MainPage.REAL_TIME)

    async def test_with_no_instruments_it_asks_for_one_and_stays_off(self):
        self.assertEqual(self.app.screen.count(self.cell()), marks.MSG_REAL_TIME_OFF_MARK)
        await self.press(keybindings.MainPage.REAL_TIME)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(errors.ERR_NO_INSTRUMENTS_TITLE, self.text())
        await self.press(Key.ESCAPE)
        self.assertFalse(self.document.get_setlist().is_real_time())

    def arrange_name(self):
        page = self.app.screen
        return page.shown_name(next(item for item in page.menu_items() if item.binding is keybindings.MainPage.ARRANGE))

    async def test_the_arrange_cell_reads_arrange_and_play_only_while_real_time_is_on(self):
        self.assertEqual(self.arrange_name(), labels.PageName.ARRANGE)
        self.assertNotIn(labels.PageName.ARRANGE_PLAY, self.text())
        self.document.add_instrument(SYNTH)
        await self.press(Key.RIGHT, Key.LEFT)
        self.assertEqual(self.arrange_name(), labels.PageName.ARRANGE_PLAY)
        self.assertIn(labels.PageName.ARRANGE_PLAY, self.text())
        await self.press(keybindings.MainPage.REAL_TIME)
        self.assertEqual(self.arrange_name(), labels.PageName.ARRANGE)
        self.assertNotIn(labels.PageName.ARRANGE_PLAY, self.text())

    async def test_it_turns_real_time_off_and_on_and_says_so(self):
        self.document.add_instrument(SYNTH)
        await self.press(Key.RIGHT, Key.LEFT)
        self.assertEqual(self.app.screen.count(self.cell()), marks.MSG_REAL_TIME_ON_MARK)
        await self.press(keybindings.MainPage.REAL_TIME)
        self.assertFalse(self.document.get_setlist().is_real_time())
        self.assertEqual(self.app.screen.count(self.cell()), marks.MSG_REAL_TIME_OFF_MARK)
        self.assertIn(messages.MSG_REAL_TIME_OFF, self.text())
        await self.press(keybindings.MainPage.REAL_TIME)
        self.assertTrue(self.document.get_setlist().is_real_time())
        self.assertIn(messages.MSG_REAL_TIME_ON, self.text())
        self.assertEqual(self.document.get_setlist().to_data()[SetlistSetting.REAL_TIME], True)

    async def test_the_cell_is_named_and_enter_on_it_presses_the_switch(self):
        self.document.add_instrument(SYNTH)
        page = self.app.screen
        page.select(self.cell().binding)
        self.assertIn(labels.PageName.REAL_TIME, self.text())
        await self.press(Key.ENTER)
        self.assertFalse(self.document.get_setlist().is_real_time())
