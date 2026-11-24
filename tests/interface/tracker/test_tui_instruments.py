# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Instruments page, the instrument editor, the Instrument field on the track editor and the main screen's Real Time switch."""

from unittest import mock

from llamatron.interface.pages.instrument import sound_text
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.dialogs.message_dialog import MessageDialog
from llamatron.interface.tracker.dialogs.sound_dialog import SoundDialog
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.set.instrument_editor import InstrumentEditor
from llamatron.interface.tracker.screens.set.instruments_page import InstrumentsPage
from llamatron.interface.tracker.screens.set.main_page import MainPage
from llamatron.model.schema import defaults, file_format, limits
from llamatron.model.schema.file_format import Effect, EffectSetting, FilterType, InstrumentKind, InstrumentSetting, LfoSetting, OscillatorSetting, Section, SetlistSetting, SoundEngine, SoundSetting, TrackSetting
from llamatron.model.values import midi
from llamatron.realtime import realtime_names
from llamatron.user_strings import errors, labels, marks, messages, names
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
PORT_NAMES = 'llamatron.interface.tracker.transport.output_port_names'
SEED = 1
ARPEGGIO = [0, 4, 7]
ARPEGGIO_TYPED = '0 4 7'
# How far ] steps a time of 300 ms.
# How far ] steps the default cutoff, 1200 Hz, which steps by 50 between 1000 and 2000.
CUTOFF_STRIDE = 50
# How far ] steps the default LFO rate, 5 Hz, stored as 50 tenths, which steps by 5 tenths between 50 and 100.
LFO_RATE_STRIDE = 5
DECAY_STRIDE = 10


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
        self.document.change_set(self.document.get_setlist().get_instrument(SYNTH).set_device, PORTS[0])
        self.document.change_set(self.document.get_setlist().get_instrument(SYNTH).set_kind, InstrumentKind.MIDI)
        self.document.change_set(self.document.get_setlist().get_instrument(SYNTH).set_channel, midi.MAX_CHANNEL)
        self.document.set_track_instrument(name=ui_testing.LEAD, instrument=SYNTH)
        await self.press(Key.DOWN, Key.UP)
        rows = dict(self.app.screen.rows())
        self.assertEqual(rows[SYNTH], [SYNTH, PORTS[0], midi.MAX_CHANNEL, 1])
        # A new instrument is off, with no channel; one made built in shows its engine.
        self.document.add_instrument(INSTRUMENT_1)
        await self.press(Key.DOWN, Key.UP)
        self.assertEqual(dict(self.app.screen.rows())[INSTRUMENT_1], [INSTRUMENT_1, marks.MSG_INSTRUMENT_OFF_SHOWN, marks.MSG_NO_CHANNEL_SHOWN, 0])
        self.document.change_set(self.document.get_setlist().get_instrument(INSTRUMENT_1).set_kind, InstrumentKind.BUILT_IN)
        await self.press(Key.DOWN, Key.UP)
        engine = labels.MSG_ENGINE_NAMES[SoundEngine.BASIC]
        self.assertEqual(dict(self.app.screen.rows())[INSTRUMENT_1][1], labels.MSG_BUILT_IN_SHOWN.format(engine=engine))

    async def test_the_first_instrument_turns_real_time_on_and_deleting_the_last_turns_it_off(self):
        self.assertFalse(self.document.get_setlist().is_real_time())
        await self.press(keybindings.InstrumentsPage.ADD, Key.ESCAPE, keybindings.InstrumentsPage.ADD, Key.ESCAPE)
        self.assertTrue(self.document.get_setlist().is_real_time())
        await self.press(keybindings.InstrumentsPage.DELETE, *ui_testing.ANSWER_YES)
        self.assertEqual(self.instruments(), [INSTRUMENT_1])
        self.assertTrue(self.document.get_setlist().is_real_time())
        self.app.screen.put_cursor_on(INSTRUMENT_1)
        await self.press(keybindings.InstrumentsPage.DELETE, *ui_testing.ANSWER_YES)
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
        return next(field.value() for field in self.app.screen.shown_fields() if field.label == label)

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
        self.document.change_set(self.document.get_setlist().get_instrument(SYNTH).set_device, GONE_PORT)
        self.document.change_set(self.document.get_setlist().get_instrument(SYNTH).set_kind, InstrumentKind.MIDI)
        with mock.patch(PORT_NAMES, return_value=list(PORTS)):
            await self.select_field(labels.MSG_DEVICE_LABEL)
            await self.press(Key.ENTER)
            self.assertEqual(self.app.screen.options, [marks.MSG_NO_DEVICE_SHOWN, file_format.FLUIDSYNTH_DEVICE, *sorted([*PORTS, GONE_PORT])])
            self.assertEqual(self.app.screen.cursor.get_place(), self.app.screen.options.index(GONE_PORT))
            await self.press(Key.ESCAPE)
        self.assertEqual(self.instrument().get_device(), GONE_PORT)

    async def test_choosing_fluidsynth_makes_the_channel_auto_with_nothing_to_change(self):
        with mock.patch(PORT_NAMES, return_value=[*PORTS, realtime_names.FLUIDSYNTH_PORT]):
            await self.select_field(labels.MSG_DEVICE_LABEL)
            await self.press(Key.ENTER)
            # The tracker's own FluidSynth port is FluidSynth, chosen as itself, never offered as a port.
            self.assertNotIn(realtime_names.FLUIDSYNTH_PORT, self.app.screen.options)
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
        # A new instrument starts switched off, neither MIDI nor built in, until one is chosen.
        self.assertEqual(self.document.get_setlist().to_data()[Section.INSTRUMENTS][SYNTH], {InstrumentSetting.CHANNEL: defaults.DEFAULT_CHANNEL + 2, InstrumentSetting.KIND: InstrumentKind.OFF})


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
        # Instrument is the first setting of the Basics tab's General column.
        general = self.app.screen.tab_box().tabs[0].columns[0]
        self.assertEqual(general.fields[0].label, labels.MSG_INSTRUMENT_LABEL)
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


class TestInstrumentTabs(UITest):
    """An instrument's MIDI, Synth and Effects tabs: each On switches the other off, the engine chosen shows its own settings, a
    gauge steps its setting, an oscillator and an effect block are chosen, and a typed arpeggio out of range is refused."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.add_instrument(SYNTH)
        await self.press(keybindings.MainPage.INSTRUMENTS, Key.ENTER)

    def instrument(self):
        return self.document.get_setlist().get_instrument(SYNTH)

    def shown_labels(self):
        return [field.label for field in self.app.screen.shown_fields()]

    async def test_a_new_instrument_is_off_and_each_tabs_on_switches_the_other_off(self):
        self.assertEqual(self.instrument().get_kind(), InstrumentKind.OFF)
        await self.select_field(labels.MSG_MIDI_ON_LABEL)
        await self.press(Key.ENTER)
        self.assertEqual(self.instrument().get_kind(), InstrumentKind.MIDI)
        await self.select_field(labels.MSG_SYNTH_ON_LABEL)
        await self.press(Key.ENTER)
        self.assertEqual(self.instrument().get_kind(), InstrumentKind.BUILT_IN)
        self.assertFalse(self.instrument().has_device())
        await self.press(Key.ENTER)
        self.assertEqual(self.instrument().get_kind(), InstrumentKind.OFF)

    async def test_the_engine_chosen_shows_its_own_settings(self):
        await self.select_field(labels.MSG_ENGINE_LABEL)
        self.assertIn(labels.MSG_OSCILLATOR_LABEL.format(number=1), self.shown_labels())
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.instrument().get_sound(SoundSetting.ENGINE), SoundEngine.DRUM)
        self.assertIn(labels.MSG_MACHINE_LABEL, self.shown_labels())
        self.assertNotIn(labels.MSG_OSCILLATOR_LABEL.format(number=1), self.shown_labels())

    async def test_a_gauge_steps_its_setting_and_a_time_steps_by_more_as_it_grows(self):
        await self.select_field(labels.MSG_VOLUME_LABEL)
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.instrument().get_sound(SoundSetting.VOLUME), defaults.DEFAULT_SOUND_VOLUME + 1)
        await self.select_field(labels.MSG_DECAY_LABEL)
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.instrument().get_sound(SoundSetting.DECAY), defaults.DEFAULT_DECAY_MS + DECAY_STRIDE)

    async def test_an_oscillator_and_an_effect_block_are_chosen(self):
        await self.select_field(labels.MSG_OSCILLATOR_LABEL.format(number=2))
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.instrument().get_oscillator(number=2, name=OscillatorSetting.WAVEFORM), file_format.WAVEFORMS[0])
        await self.select_field(labels.MSG_EFFECT_BLOCK_LABEL.format(number=3))
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.instrument().get_effect(number=3, name=EffectSetting.EFFECT), Effect.BITCRUSH)
        self.assertIn(labels.MSG_EFFECT_BITS_LABEL.format(number=3), self.shown_labels())

    async def test_a_filter_block_shows_its_mode_only_where_its_type_has_several_and_its_cutoff_steps_by_hertz(self):
        self.document.change_set(self.instrument().set_effect, number=1, name=EffectSetting.EFFECT, value=Effect.FILTER)
        await self.select_field(labels.MSG_EFFECT_BLOCK_LABEL.format(number=1))
        self.assertIn(labels.MSG_EFFECT_CUTOFF_LABEL.format(number=1), self.shown_labels())
        self.assertIn(labels.MSG_EFFECT_MIX_LABEL.format(number=1), self.shown_labels())
        self.assertNotIn(labels.MSG_EFFECT_FILTER_MODE_LABEL.format(number=1), self.shown_labels())
        await self.select_field(labels.MSG_EFFECT_FILTER_TYPE_LABEL.format(number=1))
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.instrument().get_effect(number=1, name=EffectSetting.FILTER_TYPE), FilterType.MULTIMODE)
        self.assertIn(labels.MSG_EFFECT_FILTER_MODE_LABEL.format(number=1), self.shown_labels())
        await self.select_field(labels.MSG_EFFECT_CUTOFF_LABEL.format(number=1))
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.instrument().get_effect(number=1, name=EffectSetting.CUTOFF), defaults.DEFAULT_CUTOFF + CUTOFF_STRIDE)

    async def test_an_lfo_offers_its_engines_controls_and_its_rate_steps_in_tenths_of_a_hertz(self):
        await self.select_field(labels.MSG_LFO_LABEL.format(number=1))
        self.assertNotIn(labels.MSG_LFO_RATE_LABEL.format(number=1), self.shown_labels())
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.instrument().get_lfo(number=1, name=LfoSetting.TARGET), file_format.LFO_TARGETS[SoundEngine.BASIC][1])
        await self.select_field(labels.MSG_LFO_RATE_LABEL.format(number=1))
        await self.press(keybindings.FieldPage.MORE)
        self.assertEqual(self.instrument().get_lfo(number=1, name=LfoSetting.RATE), defaults.DEFAULT_LFO_RATE + LFO_RATE_STRIDE)
        self.document.change_set(self.instrument().set_sound, name=SoundSetting.ENGINE, value=SoundEngine.DRUM)
        await self.select_field(labels.MSG_LFO_LABEL.format(number=1))
        self.assertNotIn(labels.MSG_LFO_RATE_LABEL.format(number=1), self.shown_labels())

    async def test_an_arpeggio_is_typed_and_one_out_of_range_refused(self):
        await self.select_field(labels.MSG_ENGINE_LABEL)
        self.document.change_set(self.instrument().set_sound, name=SoundSetting.ENGINE, value=SoundEngine.SID)
        await self.select_field(labels.MSG_ARPEGGIO_LABEL)
        await self.press(Key.ENTER)
        await self.type(ARPEGGIO_TYPED)
        await self.press(Key.ENTER)
        self.assertEqual(self.instrument().get_sound(SoundSetting.ARPEGGIO), ARPEGGIO)
        await self.press(Key.ENTER, *[Key.BACKSPACE] * len(ARPEGGIO_TYPED))
        await self.type(str(limits.MAX_INTERVAL + 1))
        await self.press(Key.ENTER)
        self.assertEqual(self.instrument().get_sound(SoundSetting.ARPEGGIO), ARPEGGIO)
