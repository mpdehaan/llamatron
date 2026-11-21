# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The player hands the sender windows of what is due, every play's events in one message a tick, rather than a whole clip's events
as each clip starts; and a launch from silence starts its given lead ahead of now, so that every track's first note leaves at once."""

import pathlib
import unittest

from llamatron.realtime import player as player_values
from llamatron.realtime.engine import PlaybackEngine, SteppedClock
from llamatron.realtime.outputs import RecordingOutput
from llamatron.realtime.player import Player
from llamatron.realtime.score import Score
from llamatron.realtime.timeline import Route
from tests.support.rendering import song_from_file

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
# A demo of several tracks whose first scene lasts longer than a window.
DEMO = ROOT / 'examples' / 'by_genre' / 'electronic' / 'edm_density.yml'
PORT = 'test port'
CHANNEL = 0
SEED = 1
LEAD_SECONDS = 0.003
# A step of the clock shorter than a window, as the tracker's ticks are.
STEP_SECONDS = 0.1
STEPS = 30


class Sender(PlaybackEngine):
    """An engine that keeps every message the player hands it, as the pipe to the Realtime Sender Process carries them."""

    __slots__ = ('messages',)

    def __init__(self, **named):
        super().__init__(**named)
        self.messages = []

    def add(self, events):
        self.messages.append(list(events))
        super().add(events)


class TestWindows(unittest.TestCase):

    def setUp(self):
        song = song_from_file(str(DEMO))
        routes = {track: Route(PORT, CHANNEL) for track in song.get_track_names()}
        self.clock = SteppedClock()
        self.sender = Sender(clock=self.clock, outputs={PORT: RecordingOutput()})
        self.sender.start()
        self.score = Score(song=song, routes=routes, seed=SEED)
        self.player = Player(score=self.score, sender=self.sender, now=self.sender.elapsed, lead=LEAD_SECONDS)

    def test_a_launch_hands_over_one_window_of_every_track_in_one_message(self):
        self.player.play_song()
        self.assertEqual(len(self.sender.messages), 1)
        first = self.sender.messages[0]
        self.assertGreater(len({event.tag.track for event in first}), 1)
        self.assertTrue(all(event.seconds <= LEAD_SECONDS + player_values.WINDOW_SECONDS for event in first))
        self.assertLess(len(first), sum(len(self.score.clip_events(scene=0, track=track)) for track in self.score.get_tracks()))

    def test_a_launch_from_silence_starts_its_lead_ahead(self):
        self.assertEqual(self.player.play_song(), LEAD_SECONDS)
        self.assertGreaterEqual(min(event.seconds for event in self.sender.messages[0]), LEAD_SECONDS)

    def test_ticks_hand_over_the_rest_once_each_and_in_order(self):
        self.player.play_song()
        for _ in range(STEPS):
            self.clock.advance(STEP_SECONDS)
            self.player.tick()
        handed = [event for message in self.sender.messages for event in message]
        self.assertEqual(len(handed), len(set(handed)))
        firsts = [min(event.seconds for event in message) for message in self.sender.messages]
        self.assertEqual(firsts, sorted(firsts))


if __name__ == '__main__':
    unittest.main()
