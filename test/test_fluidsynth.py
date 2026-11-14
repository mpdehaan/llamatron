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

"""FluidSynth as a real-time instrument (realtime/fluidsynth.py): found where user_scripts/install_fluidsynth.sh puts it, started and waited for, and ended.

No real FluidSynth starts: a fake process and a fake list of the computer's ports stand in, and a clock that moves only
when the waiting loop sleeps.
"""

import os
import subprocess
import unittest
from unittest import mock

from llamatron.realtime import fluidsynth
from llamatron.realtime.fluidsynth import (
    AUDIO_DEVICE_SETTING, AUDIO_DEVICE_VARIABLE, FLUIDSYNTH_PORT, FLUIDSYNTH_PORT_PREFIX, GAIN, GAIN_OPTION, LOOK_SECONDS, PORT_NAME, START_SECONDS,
    FluidSynth, FluidSynthNotStarted, command,
)
from llamatron.strings.errors import ERR_FLUIDSYNTH_DID_NOT_START, ERR_FLUIDSYNTH_ENDED

OTHER_PORT = 'IAC Driver Bus 1'
BLACKHOLE = 'BlackHole 2ch'
# How many looks at the ports pass before the fake FluidSynth's port appears, and the code a process ends with.
LOOKS_BEFORE_THE_PORT = 3
FAILED = 1
FAKE_PATH = '/fake/bin/fluidsynth'
FAKE_SOUNDFONT = '/fake/soundfonts/GeneralUser-GS.sf2'


class FakeStdin:
    __slots__ = ('closed',)

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeProcess:
    """A FluidSynth that runs until its pipe closes, or ends at once with a code, or ignores its pipe until killed."""

    __slots__ = ('stdin', 'code', 'ignores_its_pipe', 'killed')

    def __init__(self, *, code=None, ignores_its_pipe=False):
        self.stdin = FakeStdin()
        self.code = code
        self.ignores_its_pipe = ignores_its_pipe
        self.killed = False

    def poll(self):
        return self.code

    def wait(self, *, timeout=None):
        if self.stdin.closed and not self.ignores_its_pipe or self.killed:
            self.code = 0
            return 0
        raise subprocess.TimeoutExpired(cmd=FAKE_PATH, timeout=timeout)

    def kill(self):
        self.killed = True


class Ports:
    """The computer's ports, where FluidSynth's appears after so many looks once a process has started."""

    __slots__ = ('looks', 'appears_after', 'started')

    def __init__(self, *, appears_after=LOOKS_BEFORE_THE_PORT):
        self.looks = 0
        self.appears_after = appears_after
        self.started = False

    def __call__(self):
        if not self.started:
            return [OTHER_PORT]
        self.looks += 1
        return [OTHER_PORT, FLUIDSYNTH_PORT] if self.appears_after is not None and self.looks > self.appears_after else [OTHER_PORT]


class TestFluidSynth(unittest.TestCase):

    def setUp(self):
        self.time = 0.0
        self.processes = []

    def sleep(self, seconds):
        self.time += seconds

    def make(self, *, ports, process=None):
        """Return a FluidSynth whose processes are process, or new ones that run, on the ports given."""
        def start(words):
            ports.started = True
            started = FakeProcess() if process is None else process
            self.processes.append((words, started))
            return started
        return FluidSynth(port_names=ports, start_process=start, now=lambda: self.time, sleep=self.sleep)

    def test_it_waits_until_its_port_is_listed_and_starts_only_once(self):
        ports = Ports()
        synth = self.make(ports=ports)
        self.assertFalse(synth.is_running())
        self.assertTrue(synth.ensure_running())
        self.assertTrue(synth.is_running())
        self.assertEqual(ports.looks, LOOKS_BEFORE_THE_PORT + 1)
        self.assertAlmostEqual(self.time, LOOKS_BEFORE_THE_PORT * LOOK_SECONDS)
        self.assertFalse(synth.ensure_running())
        self.assertEqual(len(self.processes), 1)

    def test_a_fluidsynth_that_ends_as_it_starts_is_told(self):
        synth = self.make(ports=Ports(appears_after=None), process=FakeProcess(code=FAILED))
        with self.assertRaises(FluidSynthNotStarted) as raised:
            synth.ensure_running()
        self.assertEqual(str(raised.exception), ERR_FLUIDSYNTH_ENDED.format(code=FAILED))
        self.assertFalse(synth.is_running())

    def test_a_port_that_never_appears_gives_up_and_ends_the_process(self):
        process = FakeProcess()
        synth = self.make(ports=Ports(appears_after=None), process=process)
        with self.assertRaises(FluidSynthNotStarted) as raised:
            synth.ensure_running()
        self.assertEqual(str(raised.exception), ERR_FLUIDSYNTH_DID_NOT_START.format(seconds=START_SECONDS))
        self.assertGreater(self.time, START_SECONDS)
        self.assertTrue(process.stdin.closed)
        self.assertFalse(synth.is_running())

    def test_stopping_closes_its_pipe_and_kills_one_that_will_not_quit(self):
        quits = FakeProcess()
        synth = self.make(ports=Ports(appears_after=0), process=quits)
        synth.ensure_running()
        synth.stop()
        self.assertTrue(quits.stdin.closed)
        self.assertFalse(quits.killed)
        stubborn = FakeProcess(ignores_its_pipe=True)
        synth = self.make(ports=Ports(appears_after=0), process=stubborn)
        synth.ensure_running()
        synth.stop()
        self.assertTrue(stubborn.killed)
        synth.stop()

    def test_a_fluidsynth_that_has_ended_is_started_again(self):
        ports = Ports(appears_after=0)
        synth = self.make(ports=ports)
        synth.ensure_running()
        self.processes[0][1].code = FAILED
        self.assertFalse(synth.is_running())
        self.assertTrue(synth.ensure_running())
        self.assertEqual(len(self.processes), 2)

    def test_the_command_names_its_port_its_gain_the_soundfont_and_an_audio_device_only_when_asked(self):
        with mock.patch.object(fluidsynth, 'fluidsynth_path', return_value=FAKE_PATH), mock.patch.object(fluidsynth, 'soundfont_path', return_value=FAKE_SOUNDFONT):
            plain = command()
            to_blackhole = command(audio_device=BLACKHOLE)
        self.assertEqual(plain[0], FAKE_PATH)
        self.assertEqual(plain[-1], FAKE_SOUNDFONT)
        self.assertIn(PORT_NAME.format(name=FLUIDSYNTH_PORT), plain)
        self.assertEqual(plain[plain.index(GAIN_OPTION) + 1], GAIN)
        self.assertNotIn(AUDIO_DEVICE_SETTING.format(device=BLACKHOLE), plain)
        self.assertIn(AUDIO_DEVICE_SETTING.format(device=BLACKHOLE), to_blackhole)

    def test_the_audio_device_comes_from_the_environment(self):
        ports = Ports(appears_after=0)
        synth = self.make(ports=ports)
        with mock.patch.dict(os.environ, {AUDIO_DEVICE_VARIABLE: BLACKHOLE}), \
                mock.patch.object(fluidsynth, 'fluidsynth_path', return_value=FAKE_PATH), mock.patch.object(fluidsynth, 'soundfont_path', return_value=FAKE_SOUNDFONT):
            synth.ensure_running()
        self.assertIn(AUDIO_DEVICE_SETTING.format(device=BLACKHOLE), self.processes[0][0])

    def test_its_port_is_this_trackers_own(self):
        self.assertTrue(FLUIDSYNTH_PORT.startswith(FLUIDSYNTH_PORT_PREFIX))
        self.assertIn(str(os.getpid()), FLUIDSYNTH_PORT)

    def test_installed_means_fluidsynth_and_the_soundfont_are_both_there(self):
        with mock.patch.object(fluidsynth, 'fluidsynth_path', return_value=FAKE_PATH), mock.patch.object(fluidsynth.os.path, 'isfile', return_value=True):
            self.assertTrue(fluidsynth.is_installed())
        with mock.patch.object(fluidsynth, 'fluidsynth_path', return_value=None), mock.patch.object(fluidsynth.os.path, 'isfile', return_value=True):
            self.assertFalse(fluidsynth.is_installed())
        with mock.patch.object(fluidsynth, 'fluidsynth_path', return_value=FAKE_PATH), mock.patch.object(fluidsynth.os.path, 'isfile', return_value=False):
            self.assertFalse(fluidsynth.is_installed())


if __name__ == '__main__':
    unittest.main()
