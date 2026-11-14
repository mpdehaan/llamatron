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

"""Real-time playback from the tracker: Space on Arrange, Ctrl+T everywhere, L on the clip page and in the pattern editor.

The tracker's transport is given a stepped clock and an engine with recording outputs in place of the
Realtime Sender Process, and the computer's MIDI ports are two names of the test's own, so that
nothing sleeps and nothing opens a port.
"""

import asyncio
import unittest
from unittest import mock

from rich.text import Text

from llamatron.composition.file_format import FLUIDSYNTH_DEVICE, ClipSlotSetting, Direction, LiveResponsiveness, Row, Section
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.message_dialog import MessageDialog
from llamatron.tui.screens.arrange_page import SCENE_COLUMN
from llamatron.exporters.midi_arrangement import DRUM_CHANNEL_BYTE, MELODIC_CHANNEL_BYTES
from llamatron.realtime.fluidsynth import FLUIDSYNTH_PORT
from llamatron.realtime.engine import PlaybackEngine, SteppedClock
from llamatron.realtime.outputs import RecordingOutput
from llamatron.realtime.timeline import NOTE_ON, PROGRAM_CHANGE
from llamatron.composition.checks import listed
from llamatron.tui.uses import looping_scenes
from llamatron.strings.errors import (
    ERR_SCENE_PLAYING_SHOWN, ERR_TRACK_PLAYING_SHOWN,
    ERR_ADD_INSTRUMENT_FIRST, ERR_CANT_PLAY_TITLE, ERR_DEVICE_NOT_CONNECTED, ERR_FLUIDSYNTH_NOT_INSTALLED, ERR_NO_INSTRUMENTS_TITLE, ERR_NO_TRACK_HAS_A_DEVICE, ERR_NO_TRACK_HAS_AN_INSTRUMENT,
    ERR_LOOP_SCENES_TITLE, ERR_PREVIEW_DEVICE_NOT_CONNECTED, ERR_PREVIEW_FLUIDSYNTH_NOT_INSTALLED, ERR_PREVIEW_INSTRUMENT_HAS_NO_DEVICE, ERR_REAL_TIME_OFF, ERR_RECORDING_SONG_LOOPS,
)
from llamatron.strings.labels import MSG_PLAY_LABEL, MSG_STOP_LABEL
from llamatron.strings.legends import MSG_LISTEN_WHAT, MSG_PLAY_CLIP_WHAT, MSG_PLAY_SONG_WHAT, MSG_STOP_CLIP_WHAT, MSG_STOP_WHAT
from llamatron.strings.marks import MSG_NOTE_EDGE, MSG_READ_HEAD, MSG_PLAY_MARK, MSG_SAVED_MARK, MSG_SONG_BUTTON, MSG_SOUNDING_MARK, MSG_STOP_MARK, MSG_UNSAVED_CHANGES_MARK, MSG_UNSAVED_MARK
from llamatron.strings.messages import MSG_REAL_TIME_OFF_STOPPED
from llamatron.strings.messages import (
    MSG_LIVE_EDIT_NOT_HEARD,
    MSG_CLIP_ON_TRACK, MSG_LISTEN_INSTRUMENT_TITLE, MSG_LISTENING, MSG_LISTENING_GENERAL_MIDI, MSG_LISTENING_IN_SCALE, MSG_LISTENING_TO_PATTERN, MSG_NOTHING_TO_SILENCE, MSG_PLAYING_CLIP, MSG_PLAYING_FROM, MSG_SCENE_NUMBER,
    MSG_SILENCED, MSG_STARTS_AT_NEXT_BAR, MSG_STOPPED, MSG_STOPPED_TRACK,
)
from llamatron.tui import keybindings
from llamatron.tui.app import LlamatronApp
from llamatron.tui.drawing import Style
from llamatron.tui.pattern_preview import CHOSEN_PASSES, PIANO_PROGRAM, PREVIEW_CHANNEL_BYTE, passes_to_come_round
from llamatron.tui.screens.pattern_editor import PatternEditor
from llamatron.tui.batch_stage import GROW_SECONDS
from llamatron.tui.launch import FINISHED_CHECK_SECONDS, Launch, recording_problem
from llamatron.tui.screens.arrange_page import ArrangePage
from llamatron.tui.screens.splash import Splash
from llamatron.tui.drawing import Box
from llamatron.tui.keys import Key
from llamatron.tui.transport import Transport
from ui_testing import a_song, BEAT, DRUMS, LEAD, OTHER, TUNE, UITest, fixed_text, key_name
from llamatron.visualizers.modes import MODES

SYNTH = 'synth'
SYNTH_PORT = 'IAC Driver Bus 1'
DRUM_MACHINE = 'drum machine'
DRUM_PORT = 'Drum Port'
UNPLUGGED_PORT = 'Unplugged'
CONNECTED_PORTS = [SYNTH_PORT, DRUM_PORT]
PORT_NAMES = 'llamatron.tui.transport.output_port_names'
KIND_MASK = 0xF0
SPACE = ' '
NOTHING = ''
A_MOMENT = 0.1
# Enough real time for a timer of A_MOMENT to have fired, and a timer that never fires within a test.
LEAD_IN_PASSED = 0.3
# A lead-in long enough that starting the tracker can't use it up on a busy machine, for the test that checks nothing plays before it ends, and a wait past it.
LONG_LEAD_IN = 1.0
# The live editing tests: a slow tempo, the tune played three times, the seconds a pass lasts and its second note sounds, the pitches of degrees 3 and 5 in C major, and the clock's step.
SLOW_TEMPO = 60
THREE_PASSES = 3
PASS_SECONDS = 2.0
SECOND_NOTE_AT = 0.5
SONG_SECONDS = 6.5
LIVE_STEP = 0.05
THIRD_DEGREE = 3
EDITED_DEGREE = 5
THIRD = 64
FIFTH = 67
HALF_CHANCE = 50
NEW_SCENE = 'new scene'
RENAMED_LEAD = 'lead 2'
OTHER_SONG = 'other song'
# For the take that checks the splash and then the playing, a splash a busy machine can't see the end of before the first check, and a lead-out that keeps the tracker from quitting while the test still reads it.
RECORDING_SPLASH = 1.5
LONG_LEAD_OUT = 60.0
LONG_LEAD_IN_PASSED = 1.3
A_LONG_TIME = 60.0
# A splash long enough to be seen before the test looks, and waited out after.
SPLASH_IN_TEST = 0.6
# A batch video's title long enough that starting the tracker under the suite's load can't use it up before the test looks.
TITLE_ON_A_BUSY_MACHINE = 2.0
# The longest a test waits in real time for a launch's next stage before failing.
LONGEST_WAIT_SECONDS = 10
# READY long enough that the test sees Arrange before the song starts, however busy the machine.
READY_ON_A_BUSY_MACHINE = 3.0
SCENE_ONE_NUMBER = 1
FIRST_INDEX = 0
SECOND_INDEX = 1
CORNER_KEYS = (Key.UP, Key.LEFT)
# The song's first scene lasts one second: the tune's four eighth notes, with the looping drums cut there.
SCENE_ONE_SECONDS = 1.0
TUNE_NOTE_ONS = 2
# Past the tune's second eighth note, a quarter of a second in at 120 a minute, the first having sounded from the start.
PAST_THE_SECOND_NOTE = 0.3
ONE_CHANNEL = 1
ONE_DEVICE = 1
# A General MIDI sound for the FluidSynth tests, numbered as people number them, and the program byte it sends.
VIOLIN = 41
VIOLIN_PROGRAM = VIOLIN - 1
FLUID = 'fluid'
DRUM_KIT = 'drum kit'
# The pattern preview's tests: how long the tune lasts, four eighth notes at 120 a minute, how many passes a test hears and the clock's steps in each, the tune's last step, and what a pattern is renamed to.
TUNE_SECONDS = 1.0
PASSES_HEARD = 3
TICKS_A_PASS = 10
LAST_TUNE_STEP = 3
RENAMED_PATTERN = 'another'


class FakeFluidSynth:
    """Stands in for FluidSynth: starts nothing, and counts how often it was asked to run and to stop."""

    __slots__ = ('running', 'starts', 'stops')

    def __init__(self):
        self.running = False
        self.starts = 0
        self.stops = 0

    def is_running(self):
        return self.running

    def ensure_running(self):
        if self.running:
            return False
        self.running = True
        self.starts += 1
        return True

    def stop(self):
        self.running = False
        self.stops += 1


# A moment into the test song, which lasts about a second.
BRIEFLY = 0.1


class PlaybackTest(UITest):
    """A tracker whose transport plays into a recording engine on a stepped clock, with two connected ports."""

    def make_app(self):
        app = LlamatronApp(document=self.document)
        self.clock = SteppedClock()
        self.outputs = {}

        def make_sender(ports):
            for port in ports:
                self.outputs.setdefault(port, RecordingOutput())
            return PlaybackEngine(clock=self.clock, outputs={port: self.outputs[port] for port in ports})
        self.fluidsynth = FakeFluidSynth()
        self.fluidsynth_installed = True
        app.transport = Transport(document_holder=app, clock=self.clock, make_sender=make_sender, set_timer=app.playback_timer,
                                  fluidsynth=self.fluidsynth, fluidsynth_installed=lambda: self.fluidsynth_installed)
        return app

    async def asyncSetUp(self):
        patcher = mock.patch(PORT_NAMES, return_value=list(CONNECTED_PORTS))
        patcher.start()
        self.addCleanup(patcher.stop)
        await super().asyncSetUp()

    def give_lead_an_instrument(self, *, device=SYNTH_PORT):
        """Add an instrument on a device, which turns Real Time on, and give the lead track it."""
        self.document.add_instrument(SYNTH)
        self.document.set_instrument_device(name=SYNTH, device=device)
        self.document.set_track_instrument(name=LEAD, instrument=SYNTH)

    def transport(self):
        return self.app.transport

    async def let_time_pass(self, seconds):
        """Move the clock on, tick the transport as its timer would, send what is due and redraw the page."""
        self.clock.advance(seconds)
        self.transport().tick()
        self.transport().player().sender().send_due()
        self.app.screen.draw()
        await self.pilot.pause()

    def note_ons(self, port):
        return [data for _, data in self.outputs[port].sent if data[0] & KIND_MASK == NOTE_ON]

    def words_shown(self):
        """Return the screen's text as one line of single spaces, with the dialogs' sides taken out, since a dialog wraps a long message."""
        return SPACE.join(self.text().replace(Box.HEAVY_BAR, SPACE).split())

    def assert_told(self, message):
        self.assertIn(SPACE.join(message.split()), self.words_shown())


class TestFluidSynthPlayback(PlaybackTest):
    """Instruments whose Device is FluidSynth: started when something plays, channels as the General MIDI export gives them, and each track's sound sent first."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document.add_instrument(FLUID)
        self.document.set_instrument_device(name=FLUID, device=FLUIDSYNTH_DEVICE)
        self.document.set_instrument_gm_sound(name=FLUID, sound=VIOLIN)
        self.document.add_instrument(DRUM_KIT)
        self.document.set_instrument_device(name=DRUM_KIT, device=FLUIDSYNTH_DEVICE)
        self.document.set_track_instrument(name=LEAD, instrument=FLUID)
        self.document.set_track_instrument(name=DRUMS, instrument=DRUM_KIT)
        self.document.set_track_drum(name=DRUMS, drum=True)
        await self.press(keybindings.MainPage.ARRANGE)

    def test_a_drum_track_plays_on_channel_10_and_the_others_in_turn_with_their_sound(self):
        routes = self.transport().routes()
        self.assertEqual(routes[DRUMS].port, FLUIDSYNTH_PORT)
        self.assertEqual(routes[DRUMS].channel, DRUM_CHANNEL_BYTE)
        self.assertIsNone(routes[DRUMS].program)
        self.assertEqual(routes[LEAD].channel, MELODIC_CHANNEL_BYTES[0])
        self.assertEqual(routes[LEAD].program, VIOLIN_PROGRAM)

    def test_the_instruments_own_channel_is_ignored_and_a_muted_track_takes_no_channel(self):
        self.document.set_instrument_channel(name=FLUID, channel=MELODIC_CHANNEL_BYTES[5] + 1)
        self.assertEqual(self.transport().routes()[LEAD].channel, MELODIC_CHANNEL_BYTES[0])
        self.document.set_track_drum(name=DRUMS, drum=False)
        self.document.set_instrument_gm_sound(name=DRUM_KIT, sound=None)
        routes = self.transport().routes()
        self.assertEqual([routes[LEAD].channel, routes[DRUMS].channel], MELODIC_CHANNEL_BYTES[:2])
        self.assertIsNone(routes[DRUMS].program)
        self.document.set_track_mute(name=LEAD, muted=True)
        self.assertNotIn(LEAD, self.transport().routes())
        self.assertEqual(self.transport().routes()[DRUMS].channel, MELODIC_CHANNEL_BYTES[0])

    async def test_playing_starts_fluidsynth_first_and_sends_each_tracks_sound_before_its_notes(self):
        self.assertFalse(self.fluidsynth.running)
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        self.assertTrue(self.transport().is_playing())
        self.assertEqual(self.fluidsynth.starts, 1)
        await self.let_time_pass(A_MOMENT)
        sent = [data for _, data in self.outputs[FLUIDSYNTH_PORT].sent]
        lead = MELODIC_CHANNEL_BYTES[0]
        self.assertEqual(sent[0], [PROGRAM_CHANGE | lead, VIOLIN_PROGRAM])
        self.assertIn([NOTE_ON | DRUM_CHANNEL_BYTE], [data[:1] for data in sent if data[0] & KIND_MASK == NOTE_ON])
        self.assertNotIn(PROGRAM_CHANGE | DRUM_CHANNEL_BYTE, [data[0] for data in sent])
        # Playing again uses the FluidSynth already running.
        await self.press(keybindings.ArrangePage.STOP_PLAYING, keybindings.ArrangePage.PLAY_SONG)
        self.assertEqual(self.fluidsynth.starts, 1)

    async def test_fluidsynth_not_installed_is_told_and_nothing_starts(self):
        self.fluidsynth_installed = False
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        self.assertIn(ERR_CANT_PLAY_TITLE, self.text())
        self.assert_told(ERR_FLUIDSYNTH_NOT_INSTALLED)
        self.assertFalse(self.fluidsynth.running)
        self.assertFalse(self.transport().is_playing())

    async def test_ctrl_t_silences_fluidsynths_channels_while_it_runs_and_quitting_ends_it(self):
        self.assertEqual(self.transport().channels_in_use(), [])
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        self.assertEqual(self.transport().channels_in_use(), sorted([(FLUIDSYNTH_PORT, DRUM_CHANNEL_BYTE), (FLUIDSYNTH_PORT, MELODIC_CHANNEL_BYTES[0])]))
        self.transport().close()
        self.assertFalse(self.fluidsynth.running)
        self.assertEqual(self.fluidsynth.stops, 1)


class TestArrangePlayback(PlaybackTest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.press(keybindings.MainPage.ARRANGE)
        self.page = self.app.screen

    async def go_to_clip(self, *, index, track):
        self.page.row = index
        self.page.column = self.page.tracks().index(track) + 1
        self.page.draw()
        await self.pilot.pause()

    async def test_turning_real_time_off_while_the_song_plays_stops_it(self):
        # A bug the user found: with Real Time off Arrange shows no stop, so the song went on with only Ctrl+T to stop it.
        self.give_lead_an_instrument()
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        await self.let_time_pass(BRIEFLY)
        self.assertTrue(self.transport().is_playing())
        await self.press(Key.ESCAPE, keybindings.MainPage.REAL_TIME)
        self.assertFalse(self.transport().is_playing())
        self.assertIn(MSG_REAL_TIME_OFF_STOPPED, self.text())

    async def test_deleting_the_last_instrument_while_the_song_plays_stops_it_at_the_next_tick(self):
        self.give_lead_an_instrument()
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        await self.let_time_pass(BRIEFLY)
        self.document.set_real_time(False)
        await self.let_time_pass(BRIEFLY)
        self.assertFalse(self.transport().is_playing())

    async def test_with_real_time_off_the_corner_is_out_of_reach_and_space_is_not_a_key(self):
        await self.press(*CORNER_KEYS)
        self.assertFalse(self.page.on_corner())
        self.assertNotIn(MSG_PLAY_SONG_WHAT.strip(), self.text())
        self.assertNotIn(MSG_SONG_BUTTON.format(mark=MSG_PLAY_MARK), self.text())

    async def test_with_real_time_on_but_no_instrument_space_tells_what_is_missing(self):
        self.document.set_real_time(True)
        await self.press(*CORNER_KEYS)
        self.assertTrue(self.page.on_corner())
        self.assertIn(MSG_SONG_BUTTON.format(mark=MSG_PLAY_MARK), self.text())
        await self.press(keybindings.ArrangePage.PLAY_SONG)
        self.assertIn(ERR_NO_INSTRUMENTS_TITLE, self.text())
        self.assert_told(ERR_ADD_INSTRUMENT_FIRST)
        await self.press(Key.ENTER)
        self.assertFalse(self.transport().is_playing())

    async def test_an_instrument_no_track_uses_and_a_device_not_connected_are_told_too(self):
        self.document.add_instrument(SYNTH)
        self.document.set_instrument_device(name=SYNTH, device=SYNTH_PORT)
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        self.assertIn(ERR_CANT_PLAY_TITLE, self.text())
        self.assert_told(ERR_NO_TRACK_HAS_AN_INSTRUMENT)
        await self.press(Key.ENTER)
        self.document.set_track_instrument(name=LEAD, instrument=SYNTH)
        self.document.set_instrument_device(name=SYNTH, device=None)
        await self.press(keybindings.ArrangePage.PLAY_SONG)
        self.assert_told(ERR_NO_TRACK_HAS_A_DEVICE)
        await self.press(Key.ENTER)
        self.document.set_instrument_device(name=SYNTH, device=UNPLUGGED_PORT)
        await self.press(keybindings.ArrangePage.PLAY_SONG)
        self.assert_told(ERR_DEVICE_NOT_CONNECTED.format(instrument=SYNTH, device=UNPLUGGED_PORT))
        await self.press(Key.ENTER)
        self.assertFalse(self.transport().is_playing())

    async def test_real_time_off_is_told_when_a_page_plays_without_the_switch(self):
        # The main screen's switch is checked first, so a set whose instruments are ready still says to turn it on.
        self.give_lead_an_instrument()
        self.document.set_real_time(False)
        self.page.draw()
        await self.pilot.pause()
        self.assertIsNotNone(self.transport().problem())
        self.assertEqual(self.transport().problem().lines, [ERR_REAL_TIME_OFF])

    async def test_space_on_the_corner_plays_the_song_lights_the_page_and_stops_it_again(self):
        self.give_lead_an_instrument()
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        self.assertIn(MSG_PLAYING_FROM.format(scene=MSG_SCENE_NUMBER.format(number=SCENE_ONE_NUMBER)), self.text())
        self.assertTrue(self.transport().is_playing())
        self.assertIn(MSG_SONG_BUTTON.format(mark=MSG_STOP_MARK), self.text())
        self.assertIn(MSG_STOP_WHAT.strip(), self.text())
        await self.let_time_pass(A_MOMENT)
        # The lead sounds, so its name carries the mark; the drums have no instrument, so their clip runs silently and their name carries none.
        self.assertIn(LEAD + MSG_SOUNDING_MARK, self.text().replace(SPACE, NOTHING))
        self.assertNotIn(DRUMS + MSG_SOUNDING_MARK, self.text().replace(SPACE, NOTHING))
        self.assertTrue(self.transport().is_clip_playing(index=FIRST_INDEX, track=LEAD))
        self.assertTrue(self.transport().is_clip_playing(index=FIRST_INDEX, track=DRUMS))
        self.assertFalse(self.transport().is_track_sounding(DRUMS))
        self.assertEqual(len(self.note_ons(SYNTH_PORT)), 1)
        await self.press(keybindings.ArrangePage.STOP_PLAYING)
        self.assertIn(MSG_STOPPED, self.text())
        self.assertFalse(self.transport().is_playing())
        self.assertIn(MSG_SONG_BUTTON.format(mark=MSG_PLAY_MARK), self.text())

    async def test_the_song_ends_on_its_own_and_the_lights_go_out(self):
        # The drums loop in the first scene, which would hold the song there for the human, so they're taken out: the song is the lead's tune and then an empty scene.
        self.document.set_clip_slot_setting(index=FIRST_INDEX, track=DRUMS, setting=ClipSlotSetting.LOOP, value=False)
        self.give_lead_an_instrument()
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        await self.let_time_pass(SCENE_ONE_SECONDS + A_MOMENT)
        self.assertFalse(self.transport().is_playing())
        self.assertEqual(len(self.note_ons(SYNTH_PORT)), TUNE_NOTE_ONS)
        self.assertIn(MSG_SONG_BUTTON.format(mark=MSG_PLAY_MARK), self.text())

    async def test_a_scene_whose_every_clip_loops_is_refused_with_the_loop_errors_as_an_export_is(self):
        self.document.set_clip_slot_setting(index=FIRST_INDEX, track=LEAD, setting=ClipSlotSetting.LOOP, value=True)
        self.give_lead_an_instrument()
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        self.assertIn(ERR_LOOP_SCENES_TITLE, self.text())
        await self.press(Key.ENTER)
        self.assertFalse(self.transport().is_playing())

    async def test_a_looping_clip_beside_one_that_finishes_is_cut_where_the_scene_below_starts(self):
        # The drums loop in the first scene and the lead's tune doesn't, so the scene is done with the tune and the empty scene below takes over, cutting the drums (the user's rule of 2026-11-10).
        self.give_lead_an_instrument()
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        await self.let_time_pass(SCENE_ONE_SECONDS + A_MOMENT)
        self.assertFalse(self.transport().is_clip_playing(index=FIRST_INDEX, track=DRUMS))
        self.assertFalse(self.transport().is_playing())

    async def test_a_launch_by_hand_while_something_plays_says_it_starts_at_the_next_bar(self):
        self.give_lead_an_instrument()
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        await self.let_time_pass(A_MOMENT)
        await self.press(Key.DOWN, Key.DOWN, Key.LEFT, keybindings.ArrangePage.PLAY_SCENE)
        self.assertIn(MSG_STARTS_AT_NEXT_BAR.format(what=MSG_SCENE_NUMBER.format(number=SECOND_INDEX + 1)), self.text())
        self.assertEqual(self.transport().playing_scenes(), [FIRST_INDEX])
        await self.let_time_pass(SCENE_ONE_SECONDS)
        self.assertEqual(self.transport().playing_scenes(), [])

    async def test_space_on_a_scene_name_plays_from_that_scene_and_space_again_stops_everything(self):
        self.give_lead_an_instrument()
        await self.press(keybindings.ArrangePage.PLAY_SCENE)
        self.assertIn(MSG_PLAYING_FROM.format(scene=MSG_SCENE_NUMBER.format(number=SCENE_ONE_NUMBER)), self.text())
        self.assertEqual(self.transport().playing_scenes(), [FIRST_INDEX])
        self.assertIn(MSG_STOP_WHAT.strip(), self.text())
        await self.press(keybindings.ArrangePage.STOP_PLAYING)
        self.assertIn(MSG_STOPPED, self.text())
        self.assertFalse(self.transport().is_playing())

    async def test_space_on_a_clip_plays_it_alone_and_space_again_stops_its_track(self):
        self.give_lead_an_instrument()
        await self.go_to_clip(index=FIRST_INDEX, track=LEAD)
        self.assertIn(MSG_PLAY_CLIP_WHAT.strip(), self.text())
        await self.press(keybindings.ArrangePage.PLAY_CLIP)
        self.assertIn(MSG_PLAYING_CLIP.format(clip=MSG_CLIP_ON_TRACK.format(name=TUNE, track=LEAD)), self.text())
        self.assertTrue(self.transport().is_clip_playing(index=FIRST_INDEX, track=LEAD))
        self.assertIn(MSG_STOP_CLIP_WHAT.strip(), self.text())
        await self.press(keybindings.ArrangePage.STOP_CLIP)
        self.assertIn(MSG_STOPPED_TRACK.format(track=LEAD), self.text())
        self.assertFalse(self.transport().is_clip_playing(index=FIRST_INDEX, track=LEAD))

    async def test_a_clip_on_a_track_with_no_instrument_plays_silently_but_still_runs(self):
        # The drums have no instrument, so their clip sends nothing, while the lights still follow it.
        self.give_lead_an_instrument()
        await self.go_to_clip(index=FIRST_INDEX, track=DRUMS)
        await self.press(keybindings.ArrangePage.PLAY_CLIP)
        self.assertIn(MSG_PLAYING_CLIP.format(clip=MSG_CLIP_ON_TRACK.format(name=BEAT, track=DRUMS)), self.text())
        await self.let_time_pass(A_MOMENT)
        self.assertNotIn(DRUM_PORT, self.outputs)
        self.assertTrue(self.transport().is_clip_playing(index=FIRST_INDEX, track=DRUMS))

    async def test_the_song_plays_on_when_esc_leaves_arrange_and_when_a_page_opens_over_it(self):
        # The user's rule: a song played from Arrange plays on through every page, so that it can be edited as it plays.
        self.give_lead_an_instrument()
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        self.assertTrue(self.transport().is_playing())
        await self.press(Key.DOWN, Key.RIGHT, Key.ENTER)
        self.assertNotIsInstance(self.app.screen, ArrangePage)
        self.assertTrue(self.transport().is_playing())
        await self.press(Key.ESCAPE, Key.ESCAPE)
        self.assertTrue(self.transport().is_playing())

    async def test_a_track_or_scene_with_clips_is_not_deleted_while_the_song_plays_and_an_empty_one_is(self):
        self.give_lead_an_instrument()
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG, Key.RIGHT, keybindings.ArrangePage.DELETE_TRACK)
        self.assertIsInstance(self.app.screen, MessageDialog)
        self.assert_told(ERR_TRACK_PLAYING_SHOWN)
        await self.press(Key.ENTER)
        await self.go_to_clip(index=FIRST_INDEX, track=LEAD)
        self.page.column = SCENE_COLUMN
        self.page.draw()
        await self.press(keybindings.ArrangePage.DELETE_SCENE)
        self.assert_told(ERR_SCENE_PLAYING_SHOWN)
        await self.press(Key.ENTER)
        await self.go_to_clip(index=SECOND_INDEX, track=LEAD)
        self.page.column = SCENE_COLUMN
        self.page.draw()
        await self.press(keybindings.ArrangePage.DELETE_SCENE)
        self.assertIsInstance(self.app.screen, ConfirmDialog)

    async def test_ctrl_t_silences_every_channel_in_use_and_says_so(self):
        self.give_lead_an_instrument()
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        await self.let_time_pass(A_MOMENT)
        await self.press(keybindings.Page.SILENCE)
        self.assertIn(MSG_SILENCED.format(channels=ONE_CHANNEL, devices=ONE_DEVICE), self.text())
        self.assertFalse(self.transport().is_playing())
        self.assertEqual(self.transport().player().sender().sounding(), [])

    async def test_ctrl_t_with_no_connected_device_says_there_is_nothing_to_silence(self):
        self.give_lead_an_instrument(device=UNPLUGGED_PORT)
        await self.press(keybindings.Page.SILENCE)
        self.assertIn(MSG_NOTHING_TO_SILENCE, self.text())

    async def test_ctrl_t_works_on_the_main_screen_too(self):
        self.give_lead_an_instrument()
        await self.press(Key.ESCAPE, keybindings.Page.SILENCE)
        self.assertIn(MSG_SILENCED.format(channels=ONE_CHANNEL, devices=ONE_DEVICE), self.text())


class TestLiveEditing(PlaybackTest):
    """An edit made while the song plays is heard on what plays, at the moment the song's Live response says, the user's design.

    The song plays at 60 beats a minute, so the lead's tune, four eighths with notes on the first two, lasts two seconds a pass and
    plays three passes, its second note half a second into each; a bar of 4/4 is four seconds. The edit moves that second note from
    degree 3 to degree 5, so the notes say when it was heard.
    """

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.give_lead_an_instrument()
        self.document.set_tempo(SLOW_TEMPO)
        self.document.set_clip_slot_setting(index=FIRST_INDEX, track=LEAD, setting=ClipSlotSetting.REPEAT, value=THREE_PASSES)
        await self.press(keybindings.MainPage.ARRANGE)
        self.heard = []

    async def play_for(self, seconds):
        """Let the clock run on in small steps, ticking and sending as the tracker would, and keep each lead note sent with the second it went out."""
        for _ in range(round(seconds / LIVE_STEP)):
            self.clock.advance(LIVE_STEP)
            self.transport().tick()
            if self.transport().player() is not None:
                self.transport().player().sender().send_due()
            sent = self.note_ons(SYNTH_PORT)
            self.heard += [(round(self.clock.now() - self.started, 2), data[1]) for data in sent[len(self.counted):]]
            self.counted = sent
        await self.pilot.pause()

    async def start_and_edit(self, responsiveness):
        """Play the song from the top, and a tenth of a second in, move the tune's second note to degree 5."""
        self.document.set_live_responsiveness(responsiveness)
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        self.started = self.clock.now()
        self.counted = []
        await self.play_for(LIVE_STEP)
        self.document.set_step_value(name=TUNE, row=Row.DEGREE, step=1, value=EDITED_DEGREE)

    def second_notes(self):
        """Return the pitch of the second note of each pass, by the pass: the note heard from half a second into the pass on, each noted at the clock's step after it fell due."""
        return [pitch for at, pitch in self.heard if at % PASS_SECONDS >= SECOND_NOTE_AT]

    async def test_asap_is_heard_from_the_next_note(self):
        await self.start_and_edit(LiveResponsiveness.ASAP)
        await self.play_for(SONG_SECONDS)
        self.assertEqual(self.second_notes(), [FIFTH, FIFTH, FIFTH])

    async def test_clip_restart_is_heard_from_the_clips_next_pass(self):
        await self.start_and_edit(LiveResponsiveness.CLIP_RESTART)
        await self.play_for(SONG_SECONDS)
        self.assertEqual(self.second_notes(), [THIRD, FIFTH, FIFTH])

    async def test_next_bar_is_heard_from_the_next_bar(self):
        await self.start_and_edit(LiveResponsiveness.NEXT_BAR)
        await self.play_for(SONG_SECONDS)
        self.assertEqual(self.second_notes(), [THIRD, THIRD, FIFTH])

    async def test_digits_typed_one_after_another_are_heard_once_they_settle(self):
        await self.start_and_edit(LiveResponsiveness.ASAP)
        self.document.set_step_value(name=TUNE, row=Row.DEGREE, step=1, value=THIRD_DEGREE)
        await self.play_for(LIVE_STEP)
        self.document.set_step_value(name=TUNE, row=Row.DEGREE, step=1, value=EDITED_DEGREE)
        await self.play_for(SONG_SECONDS)
        self.assertEqual(self.second_notes(), [FIFTH, FIFTH, FIFTH])

    async def test_a_clip_made_to_loop_while_it_plays_keeps_its_scene_playing(self):
        self.document.set_clip_slot_setting(index=FIRST_INDEX, track=LEAD, setting=ClipSlotSetting.REPEAT, value=1)
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        self.started = self.clock.now()
        self.counted = []
        self.document.set_clip_slot_setting(index=FIRST_INDEX, track=LEAD, setting=ClipSlotSetting.LOOP, value=True)
        await self.play_for(SONG_SECONDS)
        self.assertTrue(self.transport().is_playing())
        self.assertEqual(self.transport().playing_scenes(), [FIRST_INDEX])

    async def test_a_scene_inserted_above_and_a_track_renamed_change_nothing_that_plays(self):
        await self.start_and_edit(LiveResponsiveness.ASAP)
        self.document.add_scene(index=FIRST_INDEX, name=NEW_SCENE)
        self.document.rename_named(section=Section.TRACKS, old=LEAD, new=RENAMED_LEAD)
        await self.play_for(SONG_SECONDS)
        self.assertEqual(self.second_notes(), [FIFTH, FIFTH, FIFTH])
        self.assertEqual(self.transport().playing_scenes(), [])

    async def test_an_edit_that_cannot_be_played_leaves_what_plays_as_it_was_and_says_why(self):
        await self.start_and_edit(LiveResponsiveness.ASAP)
        self.document.set_scale_name(None)
        await self.play_for(SONG_SECONDS)
        self.assertEqual(self.second_notes(), [THIRD, THIRD, THIRD])
        # The tracker's own timer may have shown the message already; otherwise it's shown here, as the timer would.
        message = self.transport().take_live_message()
        if message is not None:
            self.app.screen.say(message)
            self.app.screen.draw()
        await self.pilot.pause()
        self.assertIn(fixed_text(MSG_LIVE_EDIT_NOT_HEARD), self.text())

    async def test_another_song_made_current_stops_what_plays(self):
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        self.started = self.clock.now()
        self.counted = []
        self.document.add_song(OTHER_SONG)
        self.document.select_song(OTHER_SONG)
        await self.play_for(LIVE_STEP * 3)
        self.assertFalse(self.transport().is_playing())

    async def test_the_plays_random_parts_are_kept_through_an_edit(self):
        self.document.set_step_value(name=TUNE, row=Row.PROBABILITY, step=0, value=HALF_CHANCE)
        await self.press(*CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        before = self.transport().player().score().events(scene=FIRST_INDEX, track=LEAD)
        self.started = self.clock.now()
        self.counted = []
        self.document.set_step_value(name=OTHER, row=Row.DEGREE, step=0, value=EDITED_DEGREE)
        await self.play_for(LIVE_STEP * 3)
        after = self.transport().player().score().events(scene=FIRST_INDEX, track=LEAD)
        self.assertEqual([(event.seconds, event.number) for event in before], [(event.seconds, event.number) for event in after])


class TestClipPagePlayback(PlaybackTest):

    async def open_clip(self, *, track_steps):
        await self.press(keybindings.MainPage.ARRANGE, *([Key.RIGHT] * track_steps), Key.ENTER)
        self.page = self.app.screen

    async def test_l_listens_to_the_clip_again_and_again_and_l_again_stops(self):
        self.give_lead_an_instrument()
        await self.open_clip(track_steps=1)
        await self.press(keybindings.ClipPage.LISTEN)
        self.assertIn(MSG_LISTENING.format(name=TUNE, track=LEAD), self.text())
        self.assertTrue(self.page.is_listening())
        await self.let_time_pass(SCENE_ONE_SECONDS + A_MOMENT)
        # A clip listened to plays on past its scene's length, as a looping clip does.
        self.assertTrue(self.page.is_listening())
        self.assertGreater(len(self.note_ons(SYNTH_PORT)), TUNE_NOTE_ONS)
        await self.press(keybindings.ClipPage.STOP_LISTENING)
        self.assertIn(MSG_STOPPED, self.text())
        self.assertFalse(self.page.is_listening())

    async def test_a_preview_stops_when_its_page_is_left(self):
        self.give_lead_an_instrument()
        await self.open_clip(track_steps=1)
        await self.press(keybindings.ClipPage.LISTEN)
        self.assertTrue(self.transport().is_previewing())
        await self.press(Key.ESCAPE)
        self.assertFalse(self.transport().is_playing())

    async def test_the_play_and_stop_buttons_do_the_same(self):
        self.give_lead_an_instrument()
        await self.open_clip(track_steps=1)
        await self.select_field(MSG_PLAY_LABEL)
        await self.press(Key.ENTER)
        self.assertTrue(self.page.is_listening())
        await self.select_field(MSG_STOP_LABEL)
        await self.press(Key.ENTER)
        self.assertFalse(self.page.is_listening())
        self.assertIn(MSG_STOPPED, self.text())

    async def test_a_track_without_an_instrument_asks_which_to_listen_through(self):
        self.give_lead_an_instrument()
        self.document.add_instrument(DRUM_MACHINE)
        self.document.set_instrument_device(name=DRUM_MACHINE, device=DRUM_PORT)
        await self.open_clip(track_steps=2)
        await self.press(keybindings.ClipPage.LISTEN)
        self.assertIn(MSG_LISTEN_INSTRUMENT_TITLE, self.text())
        await self.type(DRUM_MACHINE)
        await self.press(Key.ENTER)
        self.assertIn(MSG_LISTENING.format(name=BEAT, track=DRUMS), self.text())
        await self.let_time_pass(A_MOMENT)
        self.assertEqual(len(self.note_ons(DRUM_PORT)), 1)
        self.assertFalse(self.document.song().get_track(DRUMS).get_instrument_name())

    async def test_real_time_off_is_told_in_a_dialog_where_fluidsynth_is_not_installed(self):
        self.fluidsynth_installed = False
        await self.open_clip(track_steps=1)
        await self.press(keybindings.ClipPage.LISTEN)
        self.assertIn(ERR_CANT_PLAY_TITLE, self.text())
        self.assert_told(ERR_REAL_TIME_OFF)

    async def test_with_real_time_off_the_clip_plays_through_general_midi_and_l_again_stops(self):
        self.assertFalse(self.document.setlist().is_real_time())
        await self.open_clip(track_steps=1)
        await self.press(keybindings.ClipPage.LISTEN)
        self.assertIn(MSG_LISTENING_GENERAL_MIDI.format(name=TUNE), self.text())
        self.assertTrue(self.page.is_listening())
        preview = self.app.pattern_preview()
        self.clock.advance(A_MOMENT)
        preview.tick()
        preview.player().sender().send_due()
        # The lead's clip plays General MIDI's piano, on the preview's channel.
        sent = [list(data) for _, data in self.outputs[FLUIDSYNTH_PORT].sent]
        self.assertIn([PROGRAM_CHANGE | PREVIEW_CHANNEL_BYTE, PIANO_PROGRAM], sent)
        self.assertEqual([data[0] for data in self.note_ons(FLUIDSYNTH_PORT)], [NOTE_ON | PREVIEW_CHANNEL_BYTE])
        await self.press(keybindings.ClipPage.STOP_LISTENING)
        self.assertFalse(self.page.is_listening())
        self.assertIn(MSG_STOPPED, self.text())

    async def test_with_real_time_off_a_drum_patterns_clip_plays_general_midis_drum_kit_and_leaving_stops_it(self):
        await self.open_clip(track_steps=2)
        await self.press(keybindings.ClipPage.LISTEN)
        preview = self.app.pattern_preview()
        self.clock.advance(A_MOMENT)
        preview.tick()
        preview.player().sender().send_due()
        self.assertEqual([data[0] for data in self.note_ons(FLUIDSYNTH_PORT)], [NOTE_ON | DRUM_CHANNEL_BYTE])
        await self.press(Key.ESCAPE)
        self.assertIsNone(preview.playing_clip())


class PatternPreviewTest(PlaybackTest):
    """The pattern preview, which plays beside the transport: its own clock steps and its own sender."""

    def preview(self):
        return self.app.pattern_preview()

    def name_a_preview_instrument(self, *, device=SYNTH_PORT):
        """Add an instrument on a device, which turns Real Time on, and make it the song's Preview instrument."""
        self.document.add_instrument(SYNTH)
        self.document.set_instrument_device(name=SYNTH, device=device)
        self.document.set_preview_instrument_name(SYNTH)

    async def let_the_preview_play(self, seconds):
        """Move the clock on, tick the preview as its timer would, send what is due and redraw the page."""
        self.clock.advance(seconds)
        self.preview().tick()
        if self.preview().player() is not None:
            self.preview().player().sender().send_due()
        self.app.screen.draw()
        await self.pilot.pause()

    async def open_pattern(self, name):
        await self.press(keybindings.MainPage.PATTERNS)
        await self.type_search(name)
        await self.press(Key.ENTER)
        self.page = self.app.screen

    async def type_search(self, name):
        await self.press(keybindings.ListPage.SEARCH)
        await self.type(name)
        await self.press(Key.ENTER)

    def pitches_on(self, port):
        return [data[1] for data in self.note_ons(port)]


class TestPatternEditorPlayback(PatternPreviewTest):

    async def test_l_plays_the_pattern_at_once_through_the_preview_instrument_and_l_again_stops(self):
        self.name_a_preview_instrument()
        revision_before = self.document.revision()
        await self.open_pattern(TUNE)
        await self.press(keybindings.PatternEditor.LISTEN)
        # Nothing is asked: the status line says the scale, the first of the scales the pattern's clips play in.
        self.assertIsInstance(self.app.screen, PatternEditor)
        self.assertIn(MSG_LISTENING_IN_SCALE.format(name=TUNE, scale=self.document.scales_of_pattern(TUNE)[0]), self.text())
        self.assertEqual(self.preview().playing_pattern(), TUNE)
        await self.let_the_preview_play(A_MOMENT)
        self.assertEqual(len(self.note_ons(SYNTH_PORT)), 1)
        # The clip it plays belongs to a copy of the set: the set is untouched, and the song's transport plays nothing.
        self.assertEqual(self.document.revision(), revision_before)
        self.assertFalse(self.transport().is_playing())
        await self.press(keybindings.PatternEditor.STOP_LISTENING)
        self.assertIn(MSG_STOPPED, self.text())
        self.assertIsNone(self.preview().playing_pattern())

    async def test_it_plays_again_and_again(self):
        self.name_a_preview_instrument()
        await self.open_pattern(TUNE)
        await self.press(keybindings.PatternEditor.LISTEN)
        for _ in range(PASSES_HEARD * TICKS_A_PASS):
            await self.let_the_preview_play(TUNE_SECONDS / TICKS_A_PASS)
        self.assertGreaterEqual(len(self.note_ons(SYNTH_PORT)), PASSES_HEARD * TUNE_NOTE_ONS)
        self.assertEqual(self.preview().playing_pattern(), TUNE)

    async def test_with_no_preview_instrument_it_plays_general_midis_piano_through_fluidsynth(self):
        await self.open_pattern(TUNE)
        await self.press(keybindings.PatternEditor.LISTEN)
        await self.let_the_preview_play(A_MOMENT)
        self.assertEqual(self.fluidsynth.starts, 1)
        sent = [data for _, data in self.outputs[FLUIDSYNTH_PORT].sent]
        self.assertIn([PROGRAM_CHANGE | PREVIEW_CHANNEL_BYTE, PIANO_PROGRAM], [list(data) for data in sent])
        self.assertEqual([data[0] for data in self.note_ons(FLUIDSYNTH_PORT)], [NOTE_ON | PREVIEW_CHANNEL_BYTE])

    async def test_a_preview_instrument_through_fluidsynth_sends_its_sound(self):
        self.document.add_instrument(FLUID)
        self.document.set_instrument_device(name=FLUID, device=FLUIDSYNTH_DEVICE)
        self.document.set_instrument_gm_sound(name=FLUID, sound=VIOLIN)
        self.document.set_preview_instrument_name(FLUID)
        await self.open_pattern(TUNE)
        await self.press(keybindings.PatternEditor.LISTEN)
        await self.let_the_preview_play(A_MOMENT)
        sent = [list(data) for _, data in self.outputs[FLUIDSYNTH_PORT].sent]
        self.assertIn([PROGRAM_CHANGE | PREVIEW_CHANNEL_BYTE, VIOLIN_PROGRAM], sent)

    async def test_a_drum_pattern_plays_general_midis_drum_kit_whatever_the_preview_instrument(self):
        self.name_a_preview_instrument()
        await self.open_pattern(BEAT)
        await self.press(keybindings.PatternEditor.LISTEN)
        # A drum pattern has no scale to say.
        self.assertIn(MSG_LISTENING_TO_PATTERN.format(name=BEAT), self.text())
        await self.let_the_preview_play(A_MOMENT)
        self.assertEqual([data[0] for data in self.note_ons(FLUIDSYNTH_PORT)], [NOTE_ON | DRUM_CHANNEL_BYTE])
        self.assertNotIn(SYNTH_PORT, self.outputs)

    async def test_without_a_preview_instrument_or_fluidsynth_listen_is_not_offered(self):
        self.fluidsynth_installed = False
        await self.open_pattern(TUNE)
        self.assertFalse(self.preview().can_sound(TUNE))
        self.assertNotIn(key_name(keybindings.PatternEditor.LISTEN) + SPACE + MSG_LISTEN_WHAT, self.words_shown())
        await self.press(keybindings.PatternEditor.LISTEN)
        self.assertIsNone(self.preview().playing_pattern())
        self.assertIsInstance(self.app.screen, PatternEditor)
        # A Preview instrument on a device needs no FluidSynth, so Listen is offered again.
        self.name_a_preview_instrument()
        await self.press(keybindings.PatternEditor.LISTEN)
        self.assertEqual(self.preview().playing_pattern(), TUNE)

    async def test_a_preview_instrument_that_cannot_sound_is_refused_on_the_status_line(self):
        self.name_a_preview_instrument(device=UNPLUGGED_PORT)
        await self.open_pattern(TUNE)
        await self.press(keybindings.PatternEditor.LISTEN)
        self.assertIn(ERR_PREVIEW_DEVICE_NOT_CONNECTED.format(name=SYNTH, device=UNPLUGGED_PORT), self.words_shown())
        self.assertIsNone(self.preview().playing_pattern())
        # General MIDI is no silent substitute: FluidSynth was never started.
        self.assertEqual(self.fluidsynth.starts, 0)
        self.document.set_instrument_device(name=SYNTH, device=None)
        await self.press(keybindings.PatternEditor.LISTEN)
        self.assertIn(ERR_PREVIEW_INSTRUMENT_HAS_NO_DEVICE.format(name=SYNTH), self.words_shown())
        self.document.set_instrument_device(name=SYNTH, device=FLUIDSYNTH_DEVICE)
        self.fluidsynth_installed = False
        await self.press(keybindings.PatternEditor.LISTEN)
        self.assertIn(ERR_PREVIEW_FLUIDSYNTH_NOT_INSTALLED.format(name=SYNTH), self.words_shown())

    async def test_it_plays_with_real_time_off(self):
        self.assertFalse(self.document.setlist().is_real_time())
        await self.open_pattern(TUNE)
        await self.press(keybindings.PatternEditor.LISTEN)
        await self.let_the_preview_play(A_MOMENT)
        self.assertEqual(len(self.note_ons(FLUIDSYNTH_PORT)), 1)
        self.assertEqual(self.preview().playing_pattern(), TUNE)

    async def test_the_preview_plays_beside_a_song_played_from_arrange_and_stopping_it_leaves_the_song(self):
        self.give_lead_an_instrument()
        self.document.add_instrument(DRUM_MACHINE)
        self.document.set_instrument_device(name=DRUM_MACHINE, device=DRUM_PORT)
        self.document.set_preview_instrument_name(DRUM_MACHINE)
        await self.press(keybindings.MainPage.ARRANGE, *CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        await self.let_time_pass(BRIEFLY)
        self.assertTrue(self.transport().is_playing())
        await self.press(Key.ESCAPE)
        await self.open_pattern(OTHER)
        await self.press(keybindings.PatternEditor.LISTEN)
        await self.let_the_preview_play(A_MOMENT)
        # The pattern is heard at once on the Preview instrument, and the song plays on.
        self.assertEqual(len(self.note_ons(DRUM_PORT)), 1)
        self.assertTrue(self.transport().is_playing())
        await self.press(keybindings.PatternEditor.STOP_LISTENING)
        self.assertIsNone(self.preview().playing_pattern())
        self.assertTrue(self.transport().is_playing())

    async def test_an_edit_made_while_it_plays_is_heard_at_the_next_pass(self):
        self.name_a_preview_instrument()
        await self.open_pattern(TUNE)
        await self.press(keybindings.PatternEditor.LISTEN)
        await self.let_the_preview_play(A_MOMENT)
        self.document.set_step_value(name=TUNE, row=Row.DEGREE, step=FIRST_INDEX, value=EDITED_DEGREE)
        heard_before = len(self.note_ons(SYNTH_PORT))
        for _ in range(PASSES_HEARD * TICKS_A_PASS):
            await self.let_the_preview_play(TUNE_SECONDS / TICKS_A_PASS)
        self.assertEqual(self.preview().playing_pattern(), TUNE)
        self.assertIn(FIFTH, self.pitches_on(SYNTH_PORT)[heard_before:])

    async def test_leaving_the_editor_and_ctrl_t_and_renaming_the_pattern_each_stop_it(self):
        self.name_a_preview_instrument()
        await self.open_pattern(TUNE)
        await self.press(keybindings.PatternEditor.LISTEN)
        await self.press(keybindings.Page.SILENCE)
        self.assertIsNone(self.preview().playing_pattern())
        await self.press(keybindings.PatternEditor.LISTEN)
        self.document.rename_named(section=Section.PATTERNS, old=OTHER, new=RENAMED_PATTERN)
        await self.let_the_preview_play(A_MOMENT)
        self.assertEqual(self.preview().playing_pattern(), TUNE)
        await self.press(Key.ESCAPE)
        self.assertIsNone(self.preview().playing_pattern())

    async def test_the_pattern_plays_in_its_own_direction_and_the_read_head_follows(self):
        self.name_a_preview_instrument()
        await self.open_pattern(TUNE)
        self.assertIsNone(self.page.playing_step())
        await self.press(keybindings.PatternEditor.LISTEN)
        # An eighth note lasts a quarter of a second, so past the second note the second step sounds.
        await self.let_the_preview_play(PAST_THE_SECOND_NOTE)
        self.assertEqual(self.page.playing_step(), SECOND_INDEX)
        await self.press(keybindings.PatternEditor.STOP_LISTENING)
        # Played backward, the last step comes first: the tune's first note, on its first step, is not heard at the start, and the read head runs right to left.
        self.document.set_direction(name=TUNE, direction=Direction.REVERSE_B)
        heard_before = len(self.note_ons(SYNTH_PORT))
        await self.press(keybindings.PatternEditor.LISTEN)
        await self.let_the_preview_play(A_MOMENT)
        self.assertEqual(len(self.note_ons(SYNTH_PORT)), heard_before)
        self.assertEqual(self.page.playing_step(), LAST_TUNE_STEP)
        await self.let_the_preview_play(PAST_THE_SECOND_NOTE)
        self.assertEqual(self.page.playing_step(), LAST_TUNE_STEP - 1)
        # A direction that chooses its steps as it goes has no read head.
        await self.press(keybindings.PatternEditor.STOP_LISTENING)
        self.document.set_direction(name=TUNE, direction=Direction.RANDOM)
        await self.press(keybindings.PatternEditor.LISTEN)
        await self.let_the_preview_play(A_MOMENT)
        self.assertIsNone(self.page.playing_step())

    async def test_the_roll_draws_the_read_head_as_a_thin_line_and_never_over_a_notes_bar(self):
        self.name_a_preview_instrument()
        await self.open_pattern(TUNE)
        before = self.read_head_cells()
        self.assertEqual(before, 0)
        await self.press(keybindings.PatternEditor.LISTEN)
        await self.let_the_preview_play(PAST_THE_SECOND_NOTE)
        self.assertGreater(self.read_head_cells(), 0)
        drawing = self.page.roll_drawing
        self.assertEqual(drawing.read_head_on(line=Text(MSG_NOTE_EDGE), column=FIRST_INDEX).plain, MSG_NOTE_EDGE)
        self.assertEqual(drawing.read_head_on(line=Text(SPACE), column=FIRST_INDEX).plain, MSG_READ_HEAD)

    def read_head_cells(self):
        """Return how many cells of the roll, as drawn now, are in the read head's style."""
        drawing = self.page.roll_drawing
        lines = drawing.body(width=self.SIZE[0], height=self.SIZE[1])
        return sum(1 for line in lines if isinstance(line, Text) for span in line.spans if span.style == Style.READ_HEAD)

    async def test_the_read_head_follows_a_clip_of_the_song_played_from_arrange(self):
        self.give_lead_an_instrument()
        await self.press(keybindings.MainPage.ARRANGE, *CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        await self.let_time_pass(PAST_THE_SECOND_NOTE)
        await self.press(Key.ESCAPE)
        await self.open_pattern(TUNE)
        self.assertEqual(self.page.playing_step(), SECOND_INDEX)
        # A pattern no playing clip plays has no read head.
        await self.press(Key.ESCAPE)
        await self.open_pattern(OTHER)
        self.assertIsNone(self.page.playing_step())


class TestPatternsPagePlayback(PatternPreviewTest):

    async def test_l_plays_the_selected_pattern_and_l_on_another_row_plays_that_one_and_leaving_stops(self):
        self.name_a_preview_instrument()
        await self.press(keybindings.MainPage.PATTERNS)
        await self.type_search(TUNE)
        await self.press(keybindings.PatternsPage.LISTEN)
        self.assertEqual(self.preview().playing_pattern(), TUNE)
        await self.let_the_preview_play(A_MOMENT)
        self.assertEqual(len(self.note_ons(SYNTH_PORT)), 1)
        await self.press(keybindings.PatternsPage.STOP_LISTENING)
        self.assertIsNone(self.preview().playing_pattern())
        await self.press(keybindings.PatternsPage.LISTEN)
        await self.type_search(OTHER)
        await self.press(keybindings.PatternsPage.LISTEN)
        self.assertEqual(self.preview().playing_pattern(), OTHER)
        await self.press(Key.ESCAPE)
        self.assertIsNone(self.preview().playing_pattern())


class TestDirectionsComeRound(unittest.TestCase):

    def test_a_loop_plays_as_many_passes_as_the_direction_takes_to_come_round(self):
        self.assertEqual(passes_to_come_round(steps=LAST_TUNE_STEP + 1, direction=Direction.FORWARD), 1)
        self.assertEqual(passes_to_come_round(steps=LAST_TUNE_STEP + 1, direction=Direction.ALTERNATE), 2)
        # Four steps as a pendulum are six long, 0 1 2 3 2 1, which comes round after three passes of four.
        self.assertEqual(passes_to_come_round(steps=LAST_TUNE_STEP + 1, direction=Direction.PENDULUM), 3)
        self.assertEqual(passes_to_come_round(steps=LAST_TUNE_STEP + 1, direction=Direction.RANDOM), CHOSEN_PASSES)


class TestHeard(PlaybackTest):
    """What the visualizer hears from the transport: each note as it starts, and while it is held, by its track's place, never a note still to come."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.give_lead_an_instrument()

    async def test_nothing_is_heard_while_nothing_plays(self):
        now, heard = self.transport().heard(since=None)
        self.assertIsNone(now)
        self.assertEqual(heard.notes, ())

    async def test_a_note_is_heard_once_as_it_starts_then_as_held_and_never_before(self):
        lead = self.document.song().get_track_names().index(LEAD)
        self.transport().play_song()
        since, heard = self.transport().heard(since=None)
        self.assertTrue(all(not note.started for note in heard.notes))
        await self.let_time_pass(PAST_THE_SECOND_NOTE)
        since, heard = self.transport().heard(since=since)
        started = [note for note in heard.notes if note.started]
        self.assertTrue(started)
        self.assertTrue(all(note.track == lead for note in started))
        self.assertGreater(heard.seconds_per_beat, 0)
        since, heard = self.transport().heard(since=since)
        self.assertFalse([note for note in heard.notes if note.started])


class LaunchTest(PlaybackTest):
    """A tracker launched with the command line's flags, with the splash and the leads cut to moments so that the tests needn't wait."""

    LAUNCH = Launch()
    # Whether the first scene's looping drums are turned off, so that the song ends on its own.
    DRUMS_LOOP = True

    def make_app(self):
        if not self.DRUMS_LOOP:
            self.document.set_clip_slot_setting(index=FIRST_INDEX, track=DRUMS, setting=ClipSlotSetting.LOOP, value=False)
        self.document.add_instrument(SYNTH)
        self.document.set_instrument_device(name=SYNTH, device=SYNTH_PORT)
        self.document.set_track_instrument(name=LEAD, instrument=SYNTH)
        app = super().make_app()
        app.launch = self.LAUNCH
        self.exited = False
        quit_for_real = app.exit

        def exit_noted(*arguments, **named):
            self.exited = True
            quit_for_real(*arguments, **named)
        app.exit = exit_noted
        return app

    async def wait_until(self, happened):
        """Let real time pass until something has happened, checking every moment, and fail if it hasn't within LONGEST_WAIT_SECONDS."""
        waited = 0
        while not happened():
            self.assertLess(waited, LONGEST_WAIT_SECONDS)
            await self.wait_a_moment()
            waited += A_MOMENT

    async def wait_a_moment(self, seconds=A_MOMENT):
        """Let real time pass, since the launch runs on Textual's timers, and redraw."""
        await asyncio.sleep(seconds)
        await self.pilot.pause()


class TestAutoplayLaunch(LaunchTest):
    """--autoplay: the tracker opens on Arrange and plays the song from the top by itself."""

    LAUNCH = Launch(autoplay=True, lead_in_seconds=LONG_LEAD_IN)

    async def test_it_opens_on_arrange_and_plays_after_the_lead_in(self):
        self.assertIsInstance(self.app.screen, ArrangePage)
        self.assertFalse(self.transport().is_playing())
        await self.wait_a_moment(LONG_LEAD_IN_PASSED)
        self.assertTrue(self.transport().is_playing())
        self.assertTrue(self.app.autoplay_started())
        self.assertIn(MSG_SONG_BUTTON.format(mark=MSG_STOP_MARK), self.text())
        # The header keeps its save mark, unsaved for a test's song with no file: only a launch for recording leaves it off.
        self.assertIn(MSG_UNSAVED_MARK, self.text())


class TestAutoplayQuitLaunch(LaunchTest):
    """--autoplay-quit-when-finished: the tracker quits by itself once the song has ended, after the lead-out."""

    LAUNCH = Launch(quit_when_finished=True, lead_in_seconds=A_MOMENT, lead_out_seconds=A_MOMENT)

    DRUMS_LOOP = False

    async def test_it_quits_once_the_song_has_ended(self):
        await self.wait_a_moment(LEAD_IN_PASSED)
        self.assertTrue(self.transport().is_playing())
        self.assertFalse(self.exited)
        await self.let_time_pass(SCENE_ONE_SECONDS + A_MOMENT)
        self.assertFalse(self.transport().is_playing())
        await self.wait_a_moment(FINISHED_CHECK_SECONDS + LEAD_IN_PASSED)
        self.assertTrue(self.exited)


class TestVisualizerLaunch(LaunchTest):
    """--visualizer: the tracker opens on Arrange with that visualizer mode over the clip area, and plays the song from the top, the one way Arrange opens on one."""

    LAUNCH = Launch(visualizer=MODES[0].OPTION, lead_in_seconds=A_MOMENT)

    async def test_it_opens_on_arrange_with_the_mode_showing_and_plays(self):
        page = self.app.screen
        self.assertIsInstance(page, ArrangePage)
        self.assertIsInstance(page.visualizer, MODES[0])
        await self.wait_a_moment(LEAD_IN_PASSED)
        self.assertTrue(self.transport().is_playing())


class TestRecordingLaunch(LaunchTest):
    """--launch-for-recording: the splash first, then Arrange with no save mark, and the time limit."""

    LAUNCH = Launch(quit_when_finished=True, for_recording=True, splash_seconds=RECORDING_SPLASH, lead_in_seconds=A_MOMENT, lead_out_seconds=LONG_LEAD_OUT)

    DRUMS_LOOP = False

    async def test_the_splash_shows_the_title_then_arrange_plays_with_no_save_mark(self):
        self.assertIsInstance(self.app.screen, Splash)
        self.assertNotIn(MSG_UNSAVED_MARK, self.text())
        await self.wait_a_moment(RECORDING_SPLASH)
        self.assertIsInstance(self.app.screen, ArrangePage)
        await self.wait_a_moment(LEAD_IN_PASSED)
        self.assertTrue(self.transport().is_playing())
        self.assertNotIn(MSG_SAVED_MARK, self.text())
        self.assertNotIn(MSG_UNSAVED_CHANGES_MARK, self.text())


class TestInteractiveRecordingLaunch(LaunchTest):
    """An interactive take: after the splash Arrange waits on its corner, playing nothing, until the person recording starts it, and stopping from the corner ends the take on the splash."""

    LAUNCH = Launch(for_recording=True, interactive=True, splash_seconds=RECORDING_SPLASH, lead_out_seconds=A_MOMENT, hold_seconds=A_MOMENT)

    async def wait_out_the_splash(self):
        self.assertIsInstance(self.app.screen, Splash)
        await self.wait_a_moment(RECORDING_SPLASH)
        self.assertIsInstance(self.app.screen, ArrangePage)

    async def test_nothing_plays_until_space_on_the_corner_and_stopping_there_ends_the_take(self):
        await self.wait_out_the_splash()
        self.assertTrue(self.app.screen.on_corner())
        await self.wait_a_moment(LEAD_IN_PASSED)
        self.assertFalse(self.transport().is_playing())
        await self.press(keybindings.ArrangePage.PLAY_SONG)
        self.assertTrue(self.transport().is_playing())
        # The take goes on while the song plays, however long the performance.
        await self.wait_a_moment(LEAD_IN_PASSED)
        self.assertIsInstance(self.app.screen, ArrangePage)
        await self.press(keybindings.ArrangePage.STOP_PLAYING)
        self.assertFalse(self.transport().is_playing())
        await self.wait_a_moment(LEAD_IN_PASSED)
        self.assertIsInstance(self.app.screen, Splash)
        self.assertFalse(self.exited)
        await self.wait_a_moment(RECORDING_SPLASH + LEAD_IN_PASSED)
        self.assertTrue(self.exited)

    async def test_esc_ends_the_take_on_the_splash_and_never_shows_the_main_screen(self):
        await self.wait_out_the_splash()
        await self.press(keybindings.Page.BACK)
        self.assertIsInstance(self.app.screen, ArrangePage)
        await self.wait_a_moment(LEAD_IN_PASSED)
        self.assertIsInstance(self.app.screen, Splash)
        await self.wait_a_moment(RECORDING_SPLASH + LEAD_IN_PASSED)
        self.assertTrue(self.exited)


class TestStoppingFromTheCornerOutsideATake(PlaybackTest):
    """Stopping from the corner ends only an interactive take: the tracker launched as ever stays on Arrange."""

    async def test_the_tracker_stays_on_arrange(self):
        self.give_lead_an_instrument()
        await self.press(keybindings.MainPage.ARRANGE, *CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG, keybindings.ArrangePage.STOP_PLAYING)
        await asyncio.sleep(LEAD_IN_PASSED)
        await self.pilot.pause()
        self.assertIsInstance(self.app.screen, ArrangePage)


class TestRecordingLaunchEnding(LaunchTest):
    """A take ends on the splash: once the song has ended and rung out, the splash shows again for its seconds and the hold, then the tracker quits."""

    LAUNCH = Launch(
        quit_when_finished=True, for_recording=True, splash_seconds=SPLASH_IN_TEST, lead_in_seconds=A_MOMENT, lead_out_seconds=A_MOMENT, hold_seconds=A_MOMENT,
    )

    DRUMS_LOOP = False

    async def test_the_splash_comes_back_after_the_song_and_then_the_tracker_quits(self):
        await self.wait_a_moment(SPLASH_IN_TEST)
        await self.wait_a_moment(LEAD_IN_PASSED)
        self.assertTrue(self.transport().is_playing())
        await self.let_time_pass(SCENE_ONE_SECONDS + A_MOMENT)
        await self.wait_a_moment(FINISHED_CHECK_SECONDS + LEAD_IN_PASSED)
        self.assertIsInstance(self.app.screen, Splash)
        self.assertFalse(self.exited)
        await self.wait_a_moment(SPLASH_IN_TEST + A_MOMENT + LEAD_IN_PASSED)
        self.assertTrue(self.exited)


class TestBatchVideoLaunch(LaunchTest):
    """A batch video: the title, then Arrange under the stage with READY, then the song with the visualizer in the frame, and black at the end with no splash, then the tracker quits."""

    LAUNCH = Launch(
        batch_video=True, visualizer=MODES[0].OPTION, title_seconds=TITLE_ON_A_BUSY_MACHINE, ready_seconds=READY_ON_A_BUSY_MACHINE, alternate=False, lead_out_seconds=A_MOMENT,
        hold_seconds=A_MOMENT,
    )

    DRUMS_LOOP = False

    async def test_the_title_then_ready_then_the_song_in_the_frame_then_black(self):
        self.assertIsInstance(self.app.screen, Splash)
        # Each change is waited for as it happens, since fixed waits overshoot on a machine busy with the rest of the suite.
        await self.wait_until(lambda: isinstance(self.app.screen, ArrangePage))
        page = self.app.screen
        self.assertIs(self.app.staged(), page)
        self.assertIn(Box.DOUBLE_TOP_LEFT, self.text())
        self.assertFalse(self.transport().is_playing())
        await self.wait_until(self.transport().is_playing)
        await self.wait_a_moment(GROW_SECONDS)
        self.assertNotIn(Box.DOUBLE_TOP_LEFT, self.text())
        await self.let_time_pass(SCENE_ONE_SECONDS + A_MOMENT)
        await self.wait_a_moment(FINISHED_CHECK_SECONDS + A_MOMENT * 3 + LEAD_IN_PASSED)
        self.assertTrue(self.exited)


class TestRecordingVisualizerLaunch(LaunchTest):
    """A take of a visualizer mode: the splash first, then Arrange with the mode over the clip area, playing."""

    LAUNCH = Launch(
        quit_when_finished=True, for_recording=True, visualizer=MODES[-1].OPTION, splash_seconds=SPLASH_IN_TEST, lead_in_seconds=A_MOMENT,
        lead_out_seconds=A_MOMENT,
    )

    DRUMS_LOOP = False

    async def test_after_the_splash_arrange_shows_the_mode_and_plays(self):
        self.assertIsInstance(self.app.screen, Splash)
        await self.wait_a_moment(SPLASH_IN_TEST)
        page = self.app.screen
        self.assertIsInstance(page, ArrangePage)
        self.assertIsInstance(page.visualizer, MODES[-1])
        await self.wait_a_moment(LEAD_IN_PASSED)
        self.assertTrue(self.transport().is_playing())


class TestRecordingLaunchTimeLimit(LaunchTest):
    """--max-seconds: the tracker quits when the limit is reached, whatever plays."""

    LAUNCH = Launch(autoplay=True, max_seconds=A_MOMENT, lead_in_seconds=A_LONG_TIME)

    async def test_it_quits_at_the_limit(self):
        await self.wait_a_moment(LEAD_IN_PASSED)
        self.assertTrue(self.exited)


class TestRecordingProblem(unittest.TestCase):
    """What a launch for recording refuses: a scene whose every clip loops, which would wait there forever."""

    def test_a_scene_whose_every_clip_loops_is_refused_and_a_looping_clip_beside_one_that_ends_is_not(self):
        document = a_song()
        self.assertIsNone(recording_problem(document.song()))
        document.set_clip_slot_setting(index=FIRST_INDEX, track=LEAD, setting=ClipSlotSetting.LOOP, value=True)
        self.assertEqual(recording_problem(document.song()), ERR_RECORDING_SONG_LOOPS.format(scenes=listed(looping_scenes(document.song()))))
        self.assertIn(MSG_SCENE_NUMBER.format(number=FIRST_INDEX + 1), recording_problem(document.song()))

