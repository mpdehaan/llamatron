# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later



"""Takes as a song plays (realtime/render_process/playback.py, LocalPlayback): a scene launched again by hand during a play plays another take of
its clips, new random choices, and a looping clip plays another take each time round, on a stepped clock into a recording sender."""

import unittest

from llamatron.model.schema.file_format import ClipSlotSetting, Row, SceneSetting, Section
from llamatron.realtime.render_process import playback as playback_values, timeline
from llamatron.realtime.render_process.playback import LocalPlayback, PlayRequest, Wanted
from llamatron.realtime.render_process.timeline import Route
from llamatron.realtime.sender_process.engine import SteppedClock
from tests.support import song_testing
from tests.support.rendering import setlist_from_data

LEAD = 'lead'
CHANCE = 'chance'
FIRST = 'one'
STEPS = 32
SIXTEENTH = '1/16'
HALF_THE_TIME = 50
SEED = 1
REVISION = 1
PORT = 'a port'
FIRST_SCENE = 0
NO_LEAD = 0.0
TICK_SECONDS = 0.05
# How long the test lets the song play: past three laps of the scene, two bars of four seconds each at the song's tempo.
PLAYED_SECONDS = 15.0
LAPS = 3


class RecordingSender:
    """Stands in for the Realtime Sender Process, keeping every event it is handed."""

    __slots__ = ('events',)

    def __init__(self):
        self.events = []

    def start(self, *, at):
        pass

    def add(self, events):
        self.events.extend(events)

    def forget(self, *, tag, after):
        pass

    def stop_tag(self, tag):
        pass

    def stop_all(self):
        pass

    def silence(self, *, channels):
        pass

    def close(self):
        return None


def a_set(*, loops):
    """Return a set of one song of one scene, whose lead plays two bars of sixteenths every one of which plays half the time."""
    steps = [[1 + place % 7, SIXTEENTH] for place in range(STEPS)]
    return setlist_from_data(song_testing.with_parts(
        patterns={CHANCE: song_testing.pat(*steps, **{Row.PROBABILITY: [HALF_THE_TIME] * STEPS})},
        tracks={LEAD: {}},
        scenes=[{SceneSetting.NAME: FIRST, Section.TRACKS: {LEAD: {ClipSlotSetting.PATTERNS: [CHANCE], ClipSlotSetting.LOOP: loops}}}],
    ))


def notes_by_play(events):
    """Return the notes each play of the lead sent, in order, as their MIDI numbers, by the play's tag."""
    plays = {}
    for event in events:
        if event.kind == timeline.NOTE_ON:
            plays.setdefault(event.tag, []).append(event.number)
    return list(plays.values())


class TakesTest(unittest.TestCase):

    def play(self, *, loops):
        """Start the song's scene from silence and return the playback, its clock and its sender."""
        setlist = a_set(loops=loops)
        self.clock = SteppedClock()
        self.sender = RecordingSender()
        self.playback = LocalPlayback(make_sender=lambda ports: self.sender, clock=self.clock, lead=NO_LEAD, at_once=True)
        self.playback.take_set(setlist.kept_data())
        self.wanted = Wanted(REVISION, setlist.first_song_name(), ((LEAD, Route(PORT, 0)),), SEED)
        self.playback.launch(wanted=self.wanted, launch=PlayRequest(playback_values.LAUNCH_SCENE, FIRST_SCENE), ports=[PORT])

    def run_for(self, seconds):
        for _ in range(round(seconds / TICK_SECONDS)):
            self.clock.advance(TICK_SECONDS)
            self.playback.tick()


class TestTakesWhilePlaying(TakesTest):

    def test_a_scene_launched_again_by_hand_plays_another_take(self):
        self.play(loops=True)
        self.run_for(TICK_SECONDS)
        self.playback.launch(wanted=self.wanted, launch=PlayRequest(playback_values.LAUNCH_SCENE, FIRST_SCENE), ports=[PORT])
        self.run_for(PLAYED_SECONDS)
        plays = notes_by_play(self.sender.events)
        self.assertGreater(len(plays), 1)
        self.assertNotEqual(plays[1], plays[0])

    def test_a_looping_clip_plays_another_take_each_time_round(self):
        self.play(loops=True)
        self.run_for(PLAYED_SECONDS)
        plays = notes_by_play(self.sender.events)
        self.assertGreaterEqual(len(plays), LAPS)
        self.assertEqual(len({tuple(notes) for notes in plays[:LAPS]}), LAPS)


if __name__ == '__main__':
    unittest.main()
