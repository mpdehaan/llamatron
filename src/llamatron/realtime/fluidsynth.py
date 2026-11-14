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

"""FluidSynth as a real-time instrument: the software synthesizer, started by the tracker when something plays through it.

An instrument whose Device is FLUIDSYNTH_DEVICE plays through FluidSynth rather than through a MIDI port
of the computer, the user's design of 2026-11-11, so that someone with no synthesizer and no DAW hears a
set at once. user_scripts/install_fluidsynth.sh puts FluidSynth in the Mac's own Homebrew and the GeneralUser GS
SoundFont in ~/soundfonts, and this module looks for them there.

The tracker starts FluidSynth only when something is played through it, with the SoundFont, the Mac's
audio and a MIDI port of its own (FLUIDSYNTH_PORT), and waits until that port is listed before anything
is sent to it, so that no note is lost while the SoundFont loads. FluidSynth reads its commands from a
pipe the tracker holds and quits when the pipe closes, so it ends with the tracker, even when the
tracker doesn't end cleanly. Its sound goes to the Mac's default output, or to the audio device that
LLAMATRON_FLUIDSYNTH_AUDIO_DEVICE names, which only the demo recorder sets, to send it to BlackHole.
"""

import os
import shutil
import subprocess
import time

from llamatron.realtime.outputs import output_port_names
from llamatron.realtime.sender_process import SenderNotStarted
from llamatron.strings.errors import ERR_FLUIDSYNTH_DID_NOT_START, ERR_FLUIDSYNTH_ENDED

# Where user_scripts/install_fluidsynth.sh puts FluidSynth: the Apple Silicon Homebrew's, which only an Apple Silicon Mac has, or an
# Intel Mac's, looked for in that order, since a Python under Rosetta reports an Intel machine on Apple Silicon.
HOMEBREW_FLUIDSYNTHS = ('/opt/homebrew/bin/fluidsynth', '/usr/local/bin/fluidsynth')
FLUIDSYNTH_COMMAND = 'fluidsynth'
SOUNDFONT = os.path.join('~', 'soundfonts', 'GeneralUser-GS.sf2')
# The MIDI port FluidSynth opens, named for this tracker alone, so that two trackers each find their own, and how
# every tracker's FluidSynth port starts, which the instrument editor leaves out of the ports it offers.
FLUIDSYNTH_PORT_PREFIX = 'llamatron FluidSynth'
FLUIDSYNTH_PORT = '{prefix} {pid}'.format(prefix=FLUIDSYNTH_PORT_PREFIX, pid=os.getpid())
# The audio device FluidSynth plays to, when something other than the Mac's default output should hear it.
AUDIO_DEVICE_VARIABLE = 'LLAMATRON_FLUIDSYNTH_AUDIO_DEVICE'
# How loud FluidSynth plays: its default of 0.2 left the loudest example at under a third of full scale,
# and 0.55 brings it to about 1 dB below, the headroom the demos' WAV files have.
GAIN = '0.55'
# How long to wait for the port, and how often to look.
START_SECONDS = 15
LOOK_SECONDS = 0.05
# How long FluidSynth has to quit once its pipe closes, before it is ended.
QUIT_SECONDS = 3
# FluidSynth's options: the Mac's audio and MIDI drivers, its port's name, its gain, and an audio device.
AUDIO_DRIVER = ['-a', 'coreaudio']
MIDI_DRIVER = ['-m', 'coremidi']
SETTING = '-o'
PORT_NAME = 'midi.portname={name}'
GAIN_OPTION = '-g'
AUDIO_DEVICE_SETTING = 'audio.coreaudio.device={device}'


class FluidSynthNotStarted(SenderNotStarted):
    """FluidSynth ended, or its port never appeared, so nothing can play through it."""


def fluidsynth_path():
    """Return where FluidSynth is: in the Mac's own Homebrew, else wherever PATH finds it, or None when it isn't installed."""
    for path in HOMEBREW_FLUIDSYNTHS:
        if os.access(path, os.X_OK):
            return path
    return shutil.which(FLUIDSYNTH_COMMAND)


def soundfont_path():
    return os.path.expanduser(SOUNDFONT)


def is_installed():
    """Return whether FluidSynth and the SoundFont it plays are both where user_scripts/install_fluidsynth.sh puts them."""
    return fluidsynth_path() is not None and os.path.isfile(soundfont_path())


def command(*, audio_device=None):
    """Return the command that starts FluidSynth as a MIDI port with the SoundFont, playing to the audio device given or the default."""
    words = [fluidsynth_path(), *AUDIO_DRIVER, *MIDI_DRIVER, SETTING, PORT_NAME.format(name=FLUIDSYNTH_PORT), GAIN_OPTION, GAIN]
    if audio_device:
        words += [SETTING, AUDIO_DEVICE_SETTING.format(device=audio_device)]
    return [*words, soundfont_path()]


class FluidSynth:
    """The tracker's FluidSynth: started when something first plays through it, and ended with the tracker."""

    __slots__ = ('_process', '_port_names', '_start_process', '_now', '_sleep')

    def __init__(self, *, port_names=output_port_names, start_process=None, now=time.monotonic, sleep=time.sleep):
        """port_names, start_process(words), now and sleep are for the tests, which start no real FluidSynth."""
        self._process = None
        self._port_names = port_names
        self._start_process = self._popen if start_process is None else start_process
        self._now = now
        self._sleep = sleep

    def is_running(self):
        return self._process is not None and self._process.poll() is None

    def ensure_running(self):
        """Start FluidSynth unless it runs, and wait until its port is listed. Return whether it was started now, so that whatever opened the old port opens the new one."""
        if self.is_running() and FLUIDSYNTH_PORT in self._port_names():
            return False
        self.stop()
        self._process = self._start_process(command(audio_device=os.environ.get(AUDIO_DEVICE_VARIABLE)))
        started = self._now()
        while FLUIDSYNTH_PORT not in self._port_names():
            code = self._process.poll()
            if code is not None:
                self._process = None
                raise FluidSynthNotStarted(ERR_FLUIDSYNTH_ENDED.format(code=code))
            if self._now() - started > START_SECONDS:
                self.stop()
                raise FluidSynthNotStarted(ERR_FLUIDSYNTH_DID_NOT_START.format(seconds=START_SECONDS))
            self._sleep(LOOK_SECONDS)
        return True

    def stop(self):
        """End FluidSynth by closing its pipe, which it quits on, and end it outright if it doesn't."""
        if self._process is None:
            return
        process = self._process
        self._process = None
        if process.stdin is not None:
            process.stdin.close()
        try:
            process.wait(timeout=QUIT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    @staticmethod
    def _popen(words):
        return subprocess.Popen(words, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
