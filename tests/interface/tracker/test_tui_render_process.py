# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""The tracker playing through a real render process (realtime/render_process/playback_process.py), on the real clock, its Realtime Sender
Process recording what it would send so that nothing is heard: a song played from Arrange, an edit made while it plays heard on
it, and the dialog shown when the render process ends as a crash would end it."""

import os
import signal

from llamatron.interface.tracker import keybindings, transport as transport_values
from llamatron.interface.tracker.app import LlamatronApp
from llamatron.interface.tracker.dialogs.message_dialog import MessageDialog
from llamatron.interface.tracker.transport import Transport
from llamatron.model.schema.file_format import ClipSlotSetting, LiveResponsiveness, Row
from llamatron.realtime.render_process import timeline
from llamatron.realtime.render_process.playback_process import PlaybackProcess
from llamatron.user_strings import errors
from tests.interface.tracker import test_tui_playback
from tests.interface.tracker.test_tui_playback import FakeFluidSynth, PlaybackTest
from tests.support import ui_testing

# How long the tests wait on the real clock for what plays to end, and how often they look.
WAIT_SECONDS = 8.0
LOOK_SECONDS = 0.05
# A moment into the song at which an edit is made, and the passes the lead's tune plays, each about a second long.
EDIT_AT_SECONDS = 0.2
PASSES = 3
# The lead's tune plays two notes a pass.
NOTES_A_PASS = 2


class TestRenderProcessPlayback(PlaybackTest):
    """A tracker whose transport plays through a render process with a recording sender."""

    def make_app(self):
        app = LlamatronApp(document=self.document)
        self.fluidsynth = FakeFluidSynth()
        self.playback = PlaybackProcess(lead=transport_values.LAUNCH_LEAD_SECONDS, recording=True)
        app.transport = Transport(document_holder=app, set_timer=app.playback_timer, playback=self.playback, fluidsynth=self.fluidsynth, fluidsynth_installed=lambda: True)
        self.addCleanup(self.playback.close)
        return app

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.give_lead_an_instrument()
        await self.press(keybindings.MainPage.ARRANGE)

    async def wait_for(self, done):
        """Let the real clock run, the tracker's timers ticking, until done() answers yes, and fail when it never does."""
        for _ in range(round(WAIT_SECONDS / LOOK_SECONDS)):
            if done():
                return
            await self.pilot.pause(LOOK_SECONDS)
        self.fail(done.__doc__)

    def is_quiet(self):
        """the song still played after the wait"""
        return not self.transport().is_playing()

    def plays_the_first_scene(self):
        """the first scene never showed as playing"""
        return self.transport().playing_scenes() == [test_tui_playback.FIRST_INDEX]

    def note_ons_sent(self):
        """Return the pitches of the note ons the recording sender sent on the lead's port, ending the render process."""
        _start, by_port = self.playback.close()
        return [data[1] for _seconds, data in by_port[test_tui_playback.SYNTH_PORT] if data[0] & test_tui_playback.KIND_MASK == timeline.NOTE_ON and data[2] > 0]

    async def test_a_song_played_from_arrange_plays_every_note_through_the_render_process(self):
        await self.press(*test_tui_playback.CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        self.assertTrue(self.transport().is_playing())
        # The launch starts its lead ahead of now, so the scene shows from the render process's next status on.
        await self.wait_for(self.plays_the_first_scene)
        await self.wait_for(self.is_quiet)
        self.assertEqual(len(self.note_ons_sent()), NOTES_A_PASS)

    async def test_an_edit_made_while_it_plays_is_heard(self):
        self.document.set_clip_slot_setting(index=test_tui_playback.FIRST_INDEX, track=ui_testing.LEAD, setting=ClipSlotSetting.REPEAT, value=PASSES)
        self.document.change_set(self.document.song().set_live_responsiveness, LiveResponsiveness.ASAP)
        await self.press(*test_tui_playback.CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        await self.pilot.pause(EDIT_AT_SECONDS)
        self.document.change_pattern(self.document.pattern(ui_testing.TUNE).set_value, row=Row.DEGREE, step=1, value=test_tui_playback.EDITED_DEGREE)
        await self.wait_for(self.is_quiet)
        self.assertIn(test_tui_playback.FIFTH, self.note_ons_sent())

    async def test_a_render_process_that_ends_unasked_is_told_in_a_dialog(self):
        self.document.set_clip_slot_setting(index=test_tui_playback.FIRST_INDEX, track=ui_testing.LEAD, setting=ClipSlotSetting.REPEAT, value=PASSES)
        await self.press(*test_tui_playback.CORNER_KEYS, keybindings.ArrangePage.PLAY_SONG)
        os.kill(self.playback.get_process_id(), signal.SIGKILL)
        await self.wait_for(self.shows_the_dialog)

    def shows_the_dialog(self):
        """the dialog saying the render process ended never showed"""
        return isinstance(self.app.screen, MessageDialog) and errors.ERR_PLAYBACK_ENDED_TITLE in self.text()
