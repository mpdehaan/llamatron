# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later



"""The engine for a scheduled port (realtime/sender_process/scheduled_engine.py) on a stepped clock, against a recording port that forgets on a
flush what was still to come, as CoreMIDI does: events handed a horizon ahead and heard at their moments, and every way of taking
events back, a forget, a stopped clip, a stop of everything and Ctrl+T, heard as the engine that sends each event as it comes would
send it; then the uncertain instant at a flush; and the same random plays on both engines, heard alike."""

import random
import unittest

from llamatron.realtime.render_process import timeline
from llamatron.realtime.render_process.timeline import ClipTag, Playing
from llamatron.realtime.sender_process import engine as engine_values, scheduled_engine
from llamatron.realtime.sender_process.engine import PlaybackEngine, SteppedClock
from llamatron.realtime.sender_process.outputs import ScheduledRecordingOutput
from llamatron.realtime.sender_process.scheduled_engine import ScheduledPlaybackEngine

PORT = 'a port'
OTHER_PORT = 'another port'
LEAD = ClipTag(0, 'lead')
BASS = ClipTag(0, 'bass')
CHANNEL = 0
OTHER_CHANNEL = 1
MIDDLE_C = 60
E = 64
G = 67
VELOCITY = 100
# Moments that are exact in binary, so that a stepped clock lands on them exactly: a step of 1/1024 s, about a millisecond.
TICK = 1 / 1024
# A moment of the hand-written plays, 16 ticks, about 16 ms.
MOMENT = 1 / 64
# The random plays: events on a grid, the engines acting between them, never within GUARD_SECONDS of one, where the scheduled
# engine is uncertain on purpose.
GRID_TICKS = 8
HALF_GRID_TICKS = 4
PLAY_TICKS = 2048
NOTE_CHANCE = 0.2
ACTION_CHANCE = 0.05
LONGEST_NOTE_GRIDS = 12
FURTHEST_START_GRIDS = 60
SEEDS = range(12)
ADD = 'add'
FORGET = 'forget'
STOP_TAG = 'stop tag'
STOP_ALL = 'stop all'
SILENCE = 'silence'
ACTIONS = (ADD, ADD, ADD, FORGET, FORGET, STOP_TAG, STOP_ALL, SILENCE)


def note_on(*, seconds, number=MIDDLE_C, tag=LEAD, port=PORT, channel=CHANNEL):
    return Playing(None, seconds, port, channel, timeline.NOTE_ON, number, VELOCITY, tag)


def note_off(*, seconds, number=MIDDLE_C, tag=LEAD, port=PORT, channel=CHANNEL):
    return Playing(None, seconds, port, channel, timeline.NOTE_OFF, number, timeline.NO_VELOCITY, tag)


def note(*, start, end, number=MIDDLE_C, tag=LEAD, port=PORT, channel=CHANNEL):
    """Return a note's note on and note off."""
    return [note_on(seconds=start, number=number, tag=tag, port=port, channel=channel), note_off(seconds=end, number=number, tag=tag, port=port, channel=channel)]


def off_data(*, number=MIDDLE_C, channel=CHANNEL):
    return [timeline.NOTE_OFF | channel, number, timeline.NO_VELOCITY]


def on_data(*, number=MIDDLE_C, channel=CHANNEL):
    return [timeline.NOTE_ON | channel, number, VELOCITY]


class Engines:
    """An engine of a kind on a stepped clock, with a recording scheduled port for each of two ports."""

    __slots__ = ('clock', 'outputs', 'engine')

    def __init__(self, engine_class):
        self.clock = SteppedClock()
        self.outputs = {PORT: ScheduledRecordingOutput(clock=self.clock), OTHER_PORT: ScheduledRecordingOutput(clock=self.clock)}
        self.engine = engine_class(clock=self.clock, outputs=self.outputs)
        self.engine.start()

    def run_to(self, seconds):
        """Move the clock on to a moment a tick at a time, the engine sending what is due now and at each tick."""
        self.engine.send_due()
        while self.clock.now() < seconds:
            self.clock.advance(TICK)
            self.engine.send_due()

    def heard(self, *, port=PORT):
        """Return every message whose moment has come on a port, with its moment, as heard."""
        return self.outputs[port].delivered()


class TestHanding(unittest.TestCase):

    def setUp(self):
        self.engines = Engines(ScheduledPlaybackEngine)

    def test_events_are_handed_a_horizon_ahead_and_heard_at_their_moments(self):
        self.engines.engine.add(note(start=MOMENT * 16, end=MOMENT * 32))
        self.engines.engine.send_due()
        self.assertEqual(self.engines.engine.handed(), [])
        self.assertEqual(self.engines.engine.next_action(), MOMENT * 16 - scheduled_engine.HORIZON_SECONDS)
        self.engines.run_to(MOMENT * 16 - scheduled_engine.HORIZON_SECONDS)
        self.assertEqual(self.engines.engine.handed(), note(start=MOMENT * 16, end=MOMENT * 32)[:1])
        self.assertEqual(self.engines.heard(), [])
        self.engines.run_to(MOMENT * 32)
        self.assertEqual(self.engines.heard(), [(MOMENT * 16, on_data()), (MOMENT * 32, off_data())])

    def test_the_scheduled_engine_does_not_spin_and_the_immediate_one_does(self):
        self.assertFalse(self.engines.engine.spins())
        self.assertTrue(Engines(PlaybackEngine).engine.spins())

    def test_events_long_gone_out_are_let_go(self):
        self.engines.engine.add(note(start=0.0, end=MOMENT * 20))
        self.engines.run_to(MOMENT * 16)
        self.assertEqual(self.engines.engine.handed(), note(start=0.0, end=MOMENT * 20)[1:])


class TestTakingBack(unittest.TestCase):
    """Each way of taking events back, with every moment well apart from the moment it is taken."""

    def setUp(self):
        self.engines = Engines(ScheduledPlaybackEngine)
        self.engine = self.engines.engine

    def test_a_forget_takes_back_a_clips_handed_events_from_a_moment_and_hands_back_what_it_keeps(self):
        self.engine.add(note(start=0.0, end=MOMENT * 4, tag=LEAD) + note(start=MOMENT * 2, end=MOMENT * 5, number=E, tag=BASS))
        self.engines.run_to(MOMENT)
        self.engine.forget(tag=LEAD, after=MOMENT * 3)
        self.engines.run_to(MOMENT * 12)
        # The lead's note off is forgotten, as a forget leaves what sounds alone, and the bass's note, handed again after the flush, is heard whole.
        self.assertEqual(self.engines.heard(), [(0.0, on_data()), (MOMENT * 2, on_data(number=E)), (MOMENT * 5, off_data(number=E))])

    def test_a_forget_of_nothing_handed_flushes_nothing(self):
        self.engine.add(note(start=0.0, end=MOMENT * 4) + note(start=MOMENT * 32, end=MOMENT * 36, number=E))
        self.engines.run_to(MOMENT)
        self.engine.forget(tag=LEAD, after=MOMENT * 32)
        self.engines.run_to(MOMENT * 64)
        self.assertEqual(self.engines.heard(), [(0.0, on_data()), (MOMENT * 4, off_data())])

    def test_a_stopped_clip_ends_a_note_whose_note_off_was_handed_and_keeps_another_clips(self):
        self.engine.add(note(start=0.0, end=MOMENT * 4, tag=LEAD) + note(start=0.0, end=MOMENT * 5, number=E, tag=BASS))
        self.engines.run_to(MOMENT * 2)
        self.engine.stop_tag(LEAD)
        self.engines.run_to(MOMENT * 12)
        self.assertEqual(self.engines.heard(), [(0.0, on_data()), (0.0, on_data(number=E)), (MOMENT * 2, off_data()), (MOMENT * 5, off_data(number=E))])
        self.assertEqual(self.engine.sounding(), [])

    def test_a_stopped_clip_hears_nothing_of_a_note_still_to_come(self):
        self.engine.add(note(start=MOMENT * 4, end=MOMENT * 5))
        self.engines.run_to(MOMENT)
        self.engine.stop_tag(LEAD)
        self.engines.run_to(MOMENT * 12)
        self.assertEqual(self.engines.heard(), [])
        self.assertEqual(self.engine.sounding(), [])

    def test_stopping_everything_takes_back_every_port_and_silences_every_channel_used(self):
        self.engine.add(note(start=0.0, end=MOMENT * 4) + note(start=0.0, end=MOMENT * 5, number=E, port=OTHER_PORT, channel=OTHER_CHANNEL) + note(start=MOMENT * 4, end=MOMENT * 5, channel=OTHER_CHANNEL))
        self.engines.run_to(MOMENT * 2)
        self.engine.stop_all()
        self.engines.run_to(MOMENT * 12)
        # The note still to come on the first port's other channel is not heard, and that channel, never played, is not silenced.
        silencing = [[timeline.CONTROL_CHANGE | CHANNEL, number, engine_values.CONTROL_OFF_VALUE] for number in engine_values.SILENCING_CONTROLS]
        self.assertEqual(self.engines.heard(), [(0.0, on_data())] + [(MOMENT * 2, data) for data in [off_data()] + silencing])
        self.assertEqual([moment for moment, _data in self.engines.heard(port=OTHER_PORT)][1:], [MOMENT * 2] * 3)

    def test_ctrl_t_silences_now_and_leaves_the_notes_to_come_as_the_other_engine_does(self):
        self.engine.add(note(start=MOMENT * 4, end=MOMENT * 6))
        self.engines.run_to(MOMENT)
        self.engine.silence(channels=[(PORT, CHANNEL)])
        self.engines.run_to(MOMENT * 8)
        self.assertEqual(self.engines.heard()[-2:], [(MOMENT * 4, on_data()), (MOMENT * 6, off_data())])
        self.assertEqual(self.engine.sounding(), [])

    def test_a_note_handed_to_start_after_ctrl_t_is_still_counted_as_sounding_once_it_starts(self):
        self.engine.add(note(start=MOMENT * 4, end=MOMENT * 8))
        self.engines.run_to(MOMENT)
        self.engine.silence(channels=[(PORT, CHANNEL)])
        self.engines.run_to(MOMENT * 5)
        self.engine.stop_all()
        self.assertEqual(self.engines.heard()[-3][1], off_data())


class TestTheUncertainInstant(unittest.TestCase):
    """Events whose moments fall within GUARD_SECONDS of a flush, which may have gone out or not."""

    def setUp(self):
        self.engines = Engines(ScheduledPlaybackEngine)
        self.engine = self.engines.engine
        # At the flush: the lead's note off has just gone out, the bass's is a half tick away, and the lead's next note starts.
        self.engine.add(note(start=0.0, end=MOMENT * 4, tag=LEAD) + note(start=0.0, end=MOMENT * 4 + TICK / 2, number=G, tag=BASS) + note(start=MOMENT * 4, end=MOMENT * 5, number=E, tag=LEAD))
        self.engines.run_to(MOMENT * 4)

    def test_a_note_off_kept_is_handed_again_heard_twice_if_it_had_gone_out_and_once_if_it_had_not(self):
        self.engine.forget(tag=LEAD, after=MOMENT * 4 + TICK * 4)
        self.engines.run_to(MOMENT * 8)
        heard = [data for _moment, data in self.engines.heard()]
        self.assertEqual(heard.count(off_data()), 2)
        self.assertEqual(heard.count(off_data(number=G)), 1)
        self.assertEqual(self.engine.sounding(), [(PORT, CHANNEL, E)])

    def test_a_note_on_forgotten_that_may_have_gone_out_is_ended(self):
        self.engine.forget(tag=LEAD, after=MOMENT * 4)
        self.engines.run_to(MOMENT * 8)
        heard = [data for _moment, data in self.engines.heard()]
        self.assertEqual(heard.count(off_data(number=E)), 1)
        # The lead's note off that had just gone out is sent again rather than counted as forgotten, so nothing is left sounding.
        self.assertEqual(heard.count(off_data()), 2)
        self.assertEqual(self.engine.sounding(), [])


class TestBothEnginesHearAlike(unittest.TestCase):
    """Random plays of adds, forgets, stopped clips, stops of everything and Ctrl+T, on both engines: what is heard is the same,
    moment for moment, wherever nothing falls within GUARD_SECONDS of a flush."""

    def test_random_plays_are_heard_alike(self):
        for seed in SEEDS:
            with self.subTest(seed=seed):
                immediate = Engines(PlaybackEngine)
                scheduled = Engines(ScheduledPlaybackEngine)
                choose = random.Random(seed)
                for tick in range(GRID_TICKS, PLAY_TICKS, GRID_TICKS):
                    if choose.random() < NOTE_CHANCE:
                        self.act(choose=choose, now=tick * TICK, engines=(immediate, scheduled))
                    immediate.run_to(tick * TICK)
                    scheduled.run_to(tick * TICK)
                for port in (PORT, OTHER_PORT):
                    self.assertEqual(sorted(scheduled.heard(port=port)), sorted(immediate.heard(port=port)))

    def act(self, *, choose, now, engines):
        """Do one random thing to both engines alike: add a note, forget a clip's events from a moment, stop a clip, stop
        everything or silence a channel."""
        action = choose.choice(ACTIONS)
        tag = choose.choice((LEAD, BASS))
        port = choose.choice((PORT, OTHER_PORT))
        if action == ADD:
            start = now + (choose.randrange(FURTHEST_START_GRIDS) * GRID_TICKS + HALF_GRID_TICKS) * TICK
            events = note(start=start, end=start + choose.randrange(1, LONGEST_NOTE_GRIDS) * GRID_TICKS * TICK, number=choose.choice((MIDDLE_C, E)), tag=tag, port=port)
        after = now + choose.randrange(FURTHEST_START_GRIDS) * GRID_TICKS * TICK
        for engines_of_a_kind in engines:
            if action == ADD:
                engines_of_a_kind.engine.add(events)
            elif action == FORGET:
                engines_of_a_kind.engine.forget(tag=tag, after=after)
            elif action == STOP_TAG:
                engines_of_a_kind.engine.stop_tag(tag)
            elif action == STOP_ALL:
                engines_of_a_kind.engine.stop_all()
            else:
                engines_of_a_kind.engine.silence(channels=[(port, CHANNEL)])


if __name__ == '__main__':
    unittest.main()
