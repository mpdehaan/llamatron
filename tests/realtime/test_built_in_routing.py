# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Built-in instruments in real-time playback (interface/tracker/transport.py, realtime/sender_process/synth_output.py,
realtime/render_process/playback.py): each built-in instrument a channel of the built-in ports, sixteen a port; a note sent to
a built-in port reaches the Synthesis Process stamped its delay earlier, and a flush takes back the port's instruments' notes;
every sound crosses once until it changes; the Synthesis Process takes back what it is told to and ends every note of an
instrument; and a sender whose Synthesis Process cannot start says why."""

import multiprocessing
import threading
import unittest
from unittest import mock

from llamatron.interface.tracker.transport import built_in_routes
from llamatron.model.objects.instrument import Instrument
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema.file_format import InstrumentKind, Section, SoundSetting
from llamatron.realtime import realtime_names
from llamatron.realtime.render_process import playback, timeline
from llamatron.realtime.render_process.timeline import Route
from llamatron.realtime.sender_process import engine as sender_engine, process as sender_process
from llamatron.realtime.sender_process.engine import PlaybackEngine, SteppedClock
from llamatron.realtime.sender_process.outputs import RecordingOutput
from llamatron.realtime.sender_process.synth_output import synth_note, SynthOutput
from llamatron.realtime.synth_process import engine as synth_engine
from llamatron.realtime.synth_process.process import SynthesisNotStarted
from tests.realtime import test_synthesis
from tests.realtime.test_synthesis import rendered, saw_patch
from tests.support import song_playing
from tests.support.rendering import render_data
from tests.support.song_playing import one_clip

DELAY = 0.008
A_MOMENT = 10.0
CHANNEL = 3
VELOCITY = 90
SECOND_GROUP = 1
WAIT_SECONDS = 5
WHY = 'no sound card'
MIDI_PORT = 'a port'
VOLUME = 55


def built_in_port(group):
    return realtime_names.BUILT_IN_PORT.format(prefix=realtime_names.BUILT_IN_PORT_PREFIX, group=group)


class FakeSynthesis:
    """Keeps what a SynthOutput hands the Synthesis Process."""

    __slots__ = ('delay', 'sent', 'forgotten', 'sounds', 'closed')

    def __init__(self):
        self.delay = DELAY
        self.sent = []
        self.forgotten = []
        self.sounds = {}
        self.closed = 0

    def notes(self, notes):
        self.sent += notes

    def forget(self, *, first, last, after):
        self.forgotten.append((first, last, after))

    def set_instrument(self, *, number, spec):
        self.sounds[number] = spec

    def close(self):
        self.closed += 1


class TestBuiltInRoutes(unittest.TestCase):

    def test_each_built_in_instrument_takes_a_channel_once_sixteen_a_port(self):
        tracks = {'track %d' % place: 'synth %d' % place for place in range(realtime_names.INSTRUMENTS_PER_PORT + 1)}
        tracks['echo'] = 'synth 0'
        routes = built_in_routes(tracks)
        self.assertEqual(routes['track 0'], Route(built_in_port(0), 0, keyswitches=False, sound='synth 0'))
        self.assertEqual(routes['echo'], routes['track 0'])
        last = routes['track %d' % realtime_names.INSTRUMENTS_PER_PORT]
        self.assertEqual((last.port, last.channel), (built_in_port(SECOND_GROUP), 0))

    def test_a_score_holds_each_built_in_routes_sound(self):
        setlist = Setlist()
        instrument = Instrument(kind=InstrumentKind.BUILT_IN)
        instrument.set_sound(name=SoundSetting.VOLUME, value=VOLUME)
        setlist.add_item(section=Section.INSTRUMENTS, name='synth', item=instrument)
        routes = {'lead': Route(built_in_port(0), CHANNEL, keyswitches=False, sound='synth'), 'bass': Route(MIDI_PORT, 0)}
        sounds = playback.built_in_sounds(setlist=setlist, routes=routes)
        self.assertEqual(sounds, {(built_in_port(0), CHANNEL): instrument.synth_spec()})


    def test_a_built_in_instruments_clip_starts_with_its_scene_and_a_midi_ones_does_not(self):
        grid = render_data(one_clip(rows={}))
        for route, expected in ((Route(built_in_port(0), CHANNEL, keyswitches=False, sound='synth'), 1), (Route(MIDI_PORT, CHANNEL), 0)):
            with self.subTest(route=route):
                events = timeline.song_timeline(grid=grid, routes={song_playing.LEAD: route})
                started = [event for event in events if event.kind == timeline.CONTROL_CHANGE and event.number == timeline.SCENE_STARTED]
                self.assertEqual(len(started), expected)

class TestSynthOutput(unittest.TestCase):

    def setUp(self):
        self.synthesis = FakeSynthesis()
        self.output = SynthOutput(synthesis=self.synthesis, group=SECOND_GROUP)
        self.first = SECOND_GROUP * realtime_names.INSTRUMENTS_PER_PORT

    def test_a_note_reaches_its_instrument_stamped_the_delay_earlier(self):
        self.output.send_at(data=[timeline.NOTE_ON | CHANNEL, test_synthesis.MIDDLE_C, VELOCITY], at=A_MOMENT)
        self.output.send_at(data=[timeline.NOTE_ON | CHANNEL, test_synthesis.MIDDLE_C, timeline.NO_VELOCITY], at=A_MOMENT + 1)
        self.output.send_at(data=[timeline.PROGRAM_CHANGE | CHANNEL, 1], at=A_MOMENT)
        self.assertEqual(self.synthesis.sent, [(A_MOMENT - DELAY, synth_engine.NOTE_ON, self.first + CHANNEL, test_synthesis.MIDDLE_C, VELOCITY),
                                               (A_MOMENT + 1 - DELAY, synth_engine.NOTE_OFF, self.first + CHANNEL, test_synthesis.MIDDLE_C, 0)])

    def test_all_notes_off_ends_every_note_of_the_instrument(self):
        note = synth_note(data=[timeline.CONTROL_CHANGE | CHANNEL, sender_engine.ALL_NOTES_OFF, 0], when=A_MOMENT, first=0)
        self.assertEqual(note, (A_MOMENT, synth_engine.ALL_OFF, CHANNEL, 0, 0))

    def test_a_scene_starting_reaches_its_instrument(self):
        note = synth_note(data=[timeline.CONTROL_CHANGE | CHANNEL, timeline.SCENE_STARTED, 0], when=A_MOMENT, first=0)
        self.assertEqual(note, (A_MOMENT, synth_engine.SCENE_STARTED, CHANNEL, 0, 0))

    def test_a_flush_takes_back_the_ports_instruments_and_a_sound_goes_to_its_instrument(self):
        self.output.flush()
        first, last, _ = self.synthesis.forgotten[0]
        self.assertEqual((first, last), (self.first, self.first + realtime_names.INSTRUMENTS_PER_PORT - 1))
        self.output.set_sound(channel=CHANNEL, spec={})
        self.assertIn(self.first + CHANNEL, self.synthesis.sounds)

    def test_the_engine_gives_sounds_to_built_in_ports_alone(self):
        engine = PlaybackEngine(clock=SteppedClock(), outputs={built_in_port(SECOND_GROUP): self.output, MIDI_PORT: RecordingOutput()})
        engine.set_sounds({(built_in_port(SECOND_GROUP), CHANNEL): {}, (MIDI_PORT, CHANNEL): {}})
        self.assertEqual(list(self.synthesis.sounds), [self.first + CHANNEL])


class TestSynthesisTakesBack(unittest.TestCase):

    def setUp(self):
        self.engine = synth_engine.SynthEngine(rate=test_synthesis.RATE)
        self.engine.set_instrument(number=CHANNEL, patch=saw_patch())

    def test_notes_still_to_come_are_taken_back_only_for_the_instruments_named(self):
        self.engine.set_instrument(number=CHANNEL + 1, patch=saw_patch())
        for instrument in (CHANNEL, CHANNEL + 1):
            self.engine.schedule(sample=test_synthesis.CHUNK * 4, kind=synth_engine.NOTE_ON, instrument=instrument, pitch=test_synthesis.MIDDLE_C)
        self.engine.forget(first=CHANNEL, last=CHANNEL, sample=test_synthesis.CHUNK)
        rendered(self.engine, chunks=8)
        self.assertEqual([voice.instrument for voice in self.engine.voices], [CHANNEL + 1])

    def test_all_off_releases_every_note_of_an_instrument(self):
        for offset in (0, 4, 7):
            self.engine.schedule(sample=0, kind=synth_engine.NOTE_ON, instrument=CHANNEL, pitch=test_synthesis.MIDDLE_C + offset)
        self.engine.schedule(sample=test_synthesis.CHUNK, kind=synth_engine.ALL_OFF, instrument=CHANNEL, pitch=0)
        rendered(self.engine, chunks=200)
        self.assertEqual(self.engine.voices, [])


class TestSenderWithoutSynthesis(unittest.TestCase):

    def test_a_sender_whose_synthesis_cannot_start_says_why(self):
        tracker_end, sender_end = multiprocessing.Pipe()
        with mock.patch.object(sender_process, sender_process.started_synthesis.__name__, side_effect=SynthesisNotStarted(WHY)):
            sender = threading.Thread(target=sender_process.run_sender, kwargs=dict(connection=sender_end, ports=[built_in_port(0)], recording=False,
                                                                                    driver=sender_process.IMMEDIATE))
            sender.start()
            self.assertEqual(tracker_end.recv(), (sender_process.NOT_STARTED, WHY))
            sender.join(timeout=WAIT_SECONDS)
        self.assertFalse(sender.is_alive())

    def test_a_recording_sender_starts_no_synthesis(self):
        self.assertIsNone(sender_process.started_synthesis(ports=[built_in_port(0)], recording=True))
        self.assertIsNone(sender_process.started_synthesis(ports=[MIDI_PORT], recording=False))
