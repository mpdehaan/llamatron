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
"""The Instruments page, the instrument editor, the Instrument field on the track editor and the main screen's Real Time switch."""

from unittest import mock

from ui_testing import LEAD, UITest, forward_key
from llamatron.composition.defaults import DEFAULT_CHANNEL
from llamatron.composition.file_format import FLUIDSYNTH_DEVICE, Section, SetlistSetting, TrackSetting
from llamatron.music.midi import MAX_CHANNEL, MIN_CHANNEL
from llamatron.strings.errors import ERR_NO_INSTRUMENTS_TITLE
from llamatron.strings.labels import MSG_CHANNEL_LABEL, MSG_DEVICE_LABEL, MSG_GM_SOUND_LABEL, MSG_INSTRUMENT_LABEL, PageName
from llamatron.strings.marks import MSG_AUTO_CHANNEL_SHOWN, MSG_NO_DEVICE_SHOWN, MSG_NONE_SHOWN, MSG_REAL_TIME_OFF_MARK, MSG_REAL_TIME_ON_MARK
from llamatron.strings.messages import MSG_REAL_TIME_OFF, MSG_REAL_TIME_ON
from llamatron.strings.names import MSG_NEW_INSTRUMENT_NAME
from llamatron.tui import keybindings
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.field import Heading
from llamatron.tui.screens.instrument_editor import FAMILIES_A_PAGE, InstrumentEditor, sound_text
from llamatron.tui.dialogs.grid_choice_dialog import GridChoiceDialog
from llamatron.composition.limits import GM_FAMILY_SIZE, MIN_GM_SOUND
from llamatron.realtime.fluidsynth import FLUIDSYNTH_PORT
from llamatron.tui.screens.instruments_page import InstrumentsPage
from llamatron.tui.screens.main_page import MainPage
from rendering import render_song

INSTRUMENT_1 = MSG_NEW_INSTRUMENT_NAME.format(number=1)
INSTRUMENT_2 = MSG_NEW_INSTRUMENT_NAME.format(number=2)
SYNTH = 'synth'
# The ports a computer might have, as python-rtmidi lists them, which the tests pretend are there.
PORTS = ['IAC Driver Bus 1', 'Analog Four']
GONE_PORT = 'Old Synth'
# Where the editor asks for the ports.
PORT_NAMES = 'llamatron.tui.screens.instrument_editor.output_port_names'
SEED = 1


class TestInstrumentsPage(UITest):
    """The list of instruments, with the device, channel and uses of each."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.INSTRUMENTS)
        self.assertIsInstance(self.app.screen, InstrumentsPage)

    def instruments(self):
        return self.document.setlist().get_instrument_names()

    async def test_a_adds_a_numbered_instrument_with_no_device_and_opens_it(self):
        await self.press(keybindings.InstrumentsPage.ADD)
        self.assertIsInstance(self.app.screen, InstrumentEditor)
        self.assertEqual(self.instruments(), [INSTRUMENT_1])
        instrument = self.document.setlist().get_instrument(INSTRUMENT_1)
        self.assertIsNone(instrument.get_device())
        self.assertEqual(instrument.get_channel(), DEFAULT_CHANNEL)
        await self.press(Key.ESCAPE, keybindings.InstrumentsPage.ADD, Key.ESCAPE)
        self.assertEqual(self.instruments(), [INSTRUMENT_1, INSTRUMENT_2])

    async def test_the_list_shows_each_instruments_device_channel_and_uses(self):
        self.document.add_instrument(SYNTH)
        self.document.set_instrument_device(name=SYNTH, device=PORTS[0])
        self.document.set_instrument_channel(name=SYNTH, channel=MAX_CHANNEL)
        self.document.set_track_instrument(name=LEAD, instrument=SYNTH)
        await self.press(Key.DOWN, Key.UP)
        rows = dict(self.app.screen.rows())
        self.assertEqual(rows[SYNTH], [SYNTH, PORTS[0], MAX_CHANNEL, 1])
        self.document.add_instrument(INSTRUMENT_1)
        await self.press(Key.DOWN, Key.UP)
        self.assertEqual(dict(self.app.screen.rows())[INSTRUMENT_1], [INSTRUMENT_1, MSG_NO_DEVICE_SHOWN, DEFAULT_CHANNEL, 0])

    async def test_the_first_instrument_turns_real_time_on_and_deleting_the_last_turns_it_off(self):
        self.assertFalse(self.document.setlist().is_real_time())
        await self.press(keybindings.InstrumentsPage.ADD, Key.ESCAPE, keybindings.InstrumentsPage.ADD, Key.ESCAPE)
        self.assertTrue(self.document.setlist().is_real_time())
        await self.press(keybindings.InstrumentsPage.DELETE, keybindings.ConfirmDialog.YES)
        self.assertEqual(self.instruments(), [INSTRUMENT_1])
        self.assertTrue(self.document.setlist().is_real_time())
        self.app.screen.put_cursor_on(INSTRUMENT_1)
        await self.press(keybindings.InstrumentsPage.DELETE, keybindings.ConfirmDialog.YES)
        self.assertEqual(self.instruments(), [])
        self.assertFalse(self.document.setlist().is_real_time())

    async def test_an_instrument_a_track_plays_through_cannot_be_deleted_and_a_rename_follows(self):
        self.document.add_instrument(SYNTH)
        self.document.set_track_instrument(name=LEAD, instrument=SYNTH)
        await self.press(Key.DOWN, Key.UP, keybindings.InstrumentsPage.DELETE)
        self.assertIsInstance(self.app.screen, MessageDialog)
        await self.press(Key.ESCAPE)
        self.assertEqual(self.instruments(), [SYNTH])
        await self.press(keybindings.InstrumentsPage.RENAME, *[Key.BACKSPACE] * len(SYNTH))
        await self.type(INSTRUMENT_2)
        await self.press(Key.ENTER)
        self.assertEqual(self.document.song().get_track(LEAD).get_instrument_name(), INSTRUMENT_2)
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
        return self.document.setlist().get_instrument(SYNTH)

    def field_text(self, label):
        return next(field.value() for field in self.app.screen.fields() if field.label == label)

    async def test_the_gm_sound_is_chosen_from_its_families_and_stepped(self):
        self.assertEqual(self.field_text(MSG_GM_SOUND_LABEL), MSG_NONE_SHOWN)
        await self.select_field(MSG_GM_SOUND_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, GridChoiceDialog)
        await self.press(Key.DOWN, Key.ENTER)
        self.assertEqual(self.instrument().get_gm_sound(), MIN_GM_SOUND)
        self.assertEqual(self.field_text(MSG_GM_SOUND_LABEL), sound_text(MIN_GM_SOUND))
        await self.press(keybindings.InstrumentEditor.MORE)
        self.assertEqual(self.instrument().get_gm_sound(), MIN_GM_SOUND + 1)
        await self.press(keybindings.InstrumentEditor.LESS, keybindings.InstrumentEditor.LESS)
        self.assertIsNone(self.instrument().get_gm_sound())
        await self.press(keybindings.InstrumentEditor.MORE, keybindings.FieldPage.CLEAR)
        self.assertIsNone(self.instrument().get_gm_sound())

    async def test_the_sound_pickers_next_page_holds_the_next_two_families(self):
        await self.select_field(MSG_GM_SOUND_LABEL)
        await self.press(Key.ENTER, Key.DOWN, forward_key(keybindings.GridChoiceDialog.OTHER_PAGE), Key.ENTER)
        self.assertIn(self.instrument().get_gm_sound(), range(MIN_GM_SOUND + FAMILIES_A_PAGE * GM_FAMILY_SIZE, MIN_GM_SOUND + 2 * FAMILIES_A_PAGE * GM_FAMILY_SIZE))

    async def test_the_device_is_chosen_from_fluidsynth_and_the_computers_ports_sorted_with_none_first(self):
        self.assertEqual(self.field_text(MSG_DEVICE_LABEL), MSG_NO_DEVICE_SHOWN)
        with mock.patch(PORT_NAMES, return_value=list(PORTS)):
            await self.select_field(MSG_DEVICE_LABEL)
            await self.press(Key.ENTER)
            self.assertIsInstance(self.app.screen, ChoiceDialog)
            self.assertEqual(self.app.screen.options, [MSG_NO_DEVICE_SHOWN, FLUIDSYNTH_DEVICE, *sorted(PORTS)])
            await self.press(Key.DOWN, Key.DOWN, Key.DOWN, Key.ENTER)
        self.assertEqual(self.instrument().get_device(), sorted(PORTS)[1])
        self.assertEqual(self.field_text(MSG_DEVICE_LABEL), sorted(PORTS)[1])
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertIsNone(self.instrument().get_device())

    async def test_a_device_that_has_gone_is_still_offered_so_that_it_can_be_kept(self):
        self.document.set_instrument_device(name=SYNTH, device=GONE_PORT)
        with mock.patch(PORT_NAMES, return_value=list(PORTS)):
            await self.select_field(MSG_DEVICE_LABEL)
            await self.press(Key.ENTER)
            self.assertEqual(self.app.screen.options, [MSG_NO_DEVICE_SHOWN, FLUIDSYNTH_DEVICE, *sorted([*PORTS, GONE_PORT])])
            self.assertEqual(self.app.screen.place, self.app.screen.options.index(GONE_PORT))
            await self.press(Key.ESCAPE)
        self.assertEqual(self.instrument().get_device(), GONE_PORT)

    async def test_choosing_fluidsynth_makes_the_channel_auto_with_nothing_to_change(self):
        with mock.patch(PORT_NAMES, return_value=[*PORTS, FLUIDSYNTH_PORT]):
            await self.select_field(MSG_DEVICE_LABEL)
            await self.press(Key.ENTER)
            # The tracker's own FluidSynth port is FluidSynth, chosen as itself, never offered as a port.
            self.assertNotIn(FLUIDSYNTH_PORT, self.app.screen.options)
            await self.press(Key.DOWN, Key.ENTER)
        self.assertEqual(self.instrument().get_device(), FLUIDSYNTH_DEVICE)
        self.assertTrue(self.instrument().uses_fluidsynth())
        self.assertEqual(self.field_text(MSG_CHANNEL_LABEL), MSG_AUTO_CHANNEL_SHOWN)
        await self.select_field(MSG_CHANNEL_LABEL)
        await self.press(keybindings.FieldPage.MORE, Key.ENTER)
        self.assertEqual(self.instrument().get_channel(), DEFAULT_CHANNEL)
        await self.select_field(MSG_DEVICE_LABEL)
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertNotEqual(self.field_text(MSG_CHANNEL_LABEL), MSG_AUTO_CHANNEL_SHOWN)

    async def test_the_channel_steps_and_types_between_1_and_16(self):
        await self.select_field(MSG_CHANNEL_LABEL)
        await self.press(keybindings.FieldPage.LESS)
        self.assertEqual(self.instrument().get_channel(), MIN_CHANNEL)
        for _ in range(MAX_CHANNEL + 1):
            await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.instrument().get_channel(), MAX_CHANNEL)
        await self.press(Key.ENTER, *[Key.BACKSPACE] * len(str(MAX_CHANNEL)))
        await self.type(str(DEFAULT_CHANNEL + 2))
        await self.press(Key.ENTER)
        self.assertEqual(self.instrument().get_channel(), DEFAULT_CHANNEL + 2)
        self.assertEqual(self.document.setlist().to_data()[Section.INSTRUMENTS][SYNTH], {'channel': DEFAULT_CHANNEL + 2})


class TestTrackInstrumentField(UITest):
    """The Instrument field at the bottom of the track editor."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.add_instrument(SYNTH)
        self.document.add_instrument(INSTRUMENT_1)
        await self.press(keybindings.MainPage.ARRANGE, Key.UP, Key.RIGHT, Key.ENTER)

    def track(self):
        return self.document.song().get_track(LEAD)

    async def test_it_is_chosen_from_the_sets_instruments_with_none_first_and_bksp_clears_it(self):
        await self.select_field(MSG_INSTRUMENT_LABEL)
        # Instrument is the last setting, and only the + Strum section comes after it.
        fields = self.app.screen.fields()
        first_heading = next(place for place, field in enumerate(fields) if isinstance(field, Heading))
        self.assertEqual(fields[first_heading - 1].label, MSG_INSTRUMENT_LABEL)
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(self.app.screen.options, [MSG_NONE_SHOWN, INSTRUMENT_1, SYNTH])
        await self.press(Key.DOWN, Key.DOWN, Key.ENTER)
        self.assertEqual(self.track().get_instrument_name(), SYNTH)
        self.assertEqual(self.document.setlist().to_data()[Section.SONGS][self.document.current_song_name()][Section.TRACKS][LEAD][TrackSetting.INSTRUMENT], SYNTH)
        await self.press(keybindings.FieldPage.CLEAR)
        self.assertIsNone(self.track().get_instrument_name())


class TestRealTimeSwitch(UITest):
    """The main screen's Real Time cell: a switch with a mark where a page's cell has its count."""

    def cell(self):
        page = self.app.screen
        self.assertIsInstance(page, MainPage)
        return next(item for item in page.menu_items() if item.binding is keybindings.MainPage.REAL_TIME)

    async def test_with_no_instruments_it_asks_for_one_and_stays_off(self):
        self.assertEqual(self.app.screen.count(self.cell()), MSG_REAL_TIME_OFF_MARK)
        await self.press(keybindings.MainPage.REAL_TIME)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assertIn(ERR_NO_INSTRUMENTS_TITLE, self.text())
        await self.press(Key.ESCAPE)
        self.assertFalse(self.document.setlist().is_real_time())

    def arrange_name(self):
        page = self.app.screen
        return page.shown_name(next(item for item in page.menu_items() if item.binding is keybindings.MainPage.ARRANGE))

    async def test_the_arrange_cell_reads_arrange_and_play_only_while_real_time_is_on(self):
        self.assertEqual(self.arrange_name(), PageName.ARRANGE)
        self.assertNotIn(PageName.ARRANGE_PLAY, self.text())
        self.document.add_instrument(SYNTH)
        await self.press(Key.RIGHT, Key.LEFT)
        self.assertEqual(self.arrange_name(), PageName.ARRANGE_PLAY)
        self.assertIn(PageName.ARRANGE_PLAY, self.text())
        await self.press(keybindings.MainPage.REAL_TIME)
        self.assertEqual(self.arrange_name(), PageName.ARRANGE)
        self.assertNotIn(PageName.ARRANGE_PLAY, self.text())

    async def test_it_turns_real_time_off_and_on_and_says_so(self):
        self.document.add_instrument(SYNTH)
        await self.press(Key.RIGHT, Key.LEFT)
        self.assertEqual(self.app.screen.count(self.cell()), MSG_REAL_TIME_ON_MARK)
        await self.press(keybindings.MainPage.REAL_TIME)
        self.assertFalse(self.document.setlist().is_real_time())
        self.assertEqual(self.app.screen.count(self.cell()), MSG_REAL_TIME_OFF_MARK)
        self.assertIn(MSG_REAL_TIME_OFF, self.text())
        await self.press(keybindings.MainPage.REAL_TIME)
        self.assertTrue(self.document.setlist().is_real_time())
        self.assertIn(MSG_REAL_TIME_ON, self.text())
        self.assertEqual(self.document.setlist().to_data()[SetlistSetting.REAL_TIME], True)

    async def test_the_cell_is_named_and_enter_on_it_presses_the_switch(self):
        self.document.add_instrument(SYNTH)
        page = self.app.screen
        page.place = page.menu_items().index(self.cell())
        self.assertIn(PageName.REAL_TIME, self.text())
        await self.press(Key.ENTER)
        self.assertFalse(self.document.setlist().is_real_time())
