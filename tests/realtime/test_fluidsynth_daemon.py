# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""FluidSynth inside the synth daemon (native/backend/src/fluid.rs, realtime/devices/fluidsynth.py, sender_process/synth_output.py):
where its library is found, when it plays in the daemon, NO_FLUIDSYNTH, and what its port sends the daemon. The test of the
real library runs only with LLAMATRON_TEST_REAL_FLUIDSYNTH=1, since it reads FluidSynth and its SoundFont where installed.
"""

import os
import tempfile
import unittest

import numpy

from llamatron.exporters.built_in_wave import read_wave
from llamatron.realtime import realtime_names
from llamatron.realtime.devices import fluidsynth
from llamatron.realtime.sender_process import process as sender_process
from llamatron.realtime.sender_process.synth_output import FluidSynthDaemonOutput
from llamatron.realtime.synth_process import daemon

NOTE_ON = 0x90
NOTE_OFF = 0x80
PROGRAM_CHANGE = 0xC0
MIDDLE_C = 60
HARD = 110
VIOLIN = 40
DELAY = 0.25
MOMENT = 10.0
REAL = 'LLAMATRON_TEST_REAL_FLUIDSYNTH'
RATE = 44100
WAV = 'fluid.wav'


class StandInDaemon:
    """Keeps what a FluidSynth port sends the daemon."""

    __slots__ = ('delay', 'sent', 'forgotten')

    def __init__(self):
        self.delay = DELAY
        self.sent = []
        self.forgotten = None

    def midi(self, messages):
        self.sent.extend(messages)

    def forget_midi(self, *, after):
        self.forgotten = after


class TestFluidSynthPort(unittest.TestCase):

    def test_a_message_goes_to_the_daemon_its_delay_early_and_a_short_one_is_padded(self):
        stand_in = StandInDaemon()
        port = FluidSynthDaemonOutput(synthesis=stand_in)
        port.send_at(data=[NOTE_ON, MIDDLE_C, HARD], at=MOMENT)
        port.send_at(data=[PROGRAM_CHANGE, VIOLIN], at=MOMENT)
        self.assertEqual(stand_in.sent, [(MOMENT - DELAY, NOTE_ON, MIDDLE_C, HARD), (MOMENT - DELAY, PROGRAM_CHANGE, VIOLIN, 0)])

    def test_fluidsynth_s_port_is_known_whichever_process_named_it(self):
        # The tracker names the port after its own process, and the sender, another process, must still know it.
        other_process = realtime_names.FLUIDSYNTH_PORT_PREFIX + ' 1'
        self.assertTrue(sender_process.is_fluidsynth_port(other_process))
        self.assertFalse(sender_process.is_fluidsynth_port(realtime_names.BUILT_IN_PORT_PREFIX))

    def test_a_flush_takes_back_what_is_still_to_come(self):
        stand_in = StandInDaemon()
        FluidSynthDaemonOutput(synthesis=stand_in).flush()
        self.assertIsNotNone(stand_in.forgotten)


class TestWhereFluidSynthPlays(unittest.TestCase):

    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.library = os.path.join(scratch.name, 'libfluidsynth.dylib')
        self.program = os.path.join(scratch.name, 'synth')
        for path in (self.library, self.program):
            with open(path, 'w') as file:
                file.write('')

    def test_the_library_given_is_used_and_a_missing_one_is_none(self):
        self.assertEqual(fluidsynth.library_path(environment={fluidsynth.LIBRARY_VARIABLE: self.library}), self.library)
        self.assertIsNone(fluidsynth.library_path(environment={fluidsynth.LIBRARY_VARIABLE: self.library + 'x'}))

    def test_no_fluidsynth_turns_it_off_and_the_process_variable_keeps_its_own_process(self):
        given = {fluidsynth.LIBRARY_VARIABLE: self.library, daemon.DAEMON_PATH: self.program}
        self.assertTrue(fluidsynth.is_disabled(environment={fluidsynth.DISABLED_VARIABLE: fluidsynth.SWITCHED_ON}))
        self.assertFalse(fluidsynth.is_disabled(environment={}))
        self.assertFalse(fluidsynth.plays_in_daemon(environment={**given, fluidsynth.DISABLED_VARIABLE: fluidsynth.SWITCHED_ON}))
        self.assertFalse(fluidsynth.plays_in_daemon(environment={**given, fluidsynth.PROCESS_VARIABLE: fluidsynth.SWITCHED_ON}))

    def test_without_the_daemon_fluidsynth_plays_in_its_own_process(self):
        self.assertFalse(fluidsynth.plays_in_daemon(environment={fluidsynth.LIBRARY_VARIABLE: self.library, daemon.DAEMON_PATH: self.program + 'x'}))


@unittest.skipUnless(os.environ.get(REAL) == '1' and daemon.daemon_path() is not None, 'reads the installed FluidSynth: set LLAMATRON_TEST_REAL_FLUIDSYNTH=1')
class TestRealFluidSynthInTheDaemon(unittest.TestCase):

    def test_a_note_renders_offline_through_the_installed_library_and_soundfont(self):
        library = fluidsynth.library_path()
        self.assertIsNotNone(library)
        with tempfile.TemporaryDirectory() as scratch:
            path = os.path.join(scratch, WAV)
            process = daemon.subprocess.Popen([daemon.daemon_path(), daemon.RENDER, daemon.RATE_OPTION, str(RATE)], stdin=daemon.subprocess.PIPE, stdout=daemon.subprocess.PIPE)
            channel = daemon.DaemonChannel(process=process)
            channel.send([daemon.SOUNDFONT, library, fluidsynth.soundfont_path(), float(fluidsynth.GAIN)])
            self.assertEqual(channel.receive()[0], daemon.SOUNDFONT_READY)
            channel.send([daemon.MIDI, [[0.0, PROGRAM_CHANGE, VIOLIN, 0], [0.1, NOTE_ON, MIDDLE_C, HARD], [0.8, NOTE_OFF, MIDDLE_C, 0]]])
            channel.send([daemon.RENDER_MESSAGE, path, 1.5])
            self.assertEqual(channel.receive()[0], daemon.RENDERED)
            channel.send([daemon.CLOSE])
            process.stdin.close()
            process.wait()
            process.stdout.close()
            _, samples = read_wave(path)
        place = int(0.1 * RATE)
        self.assertFalse(numpy.any(samples[:place - 64]))
        self.assertGreater(float(numpy.max(numpy.abs(samples))), 0.01)
