# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""FluidSynth as a real-time instrument: the software synthesizer, started by the tracker when something plays through it.

An instrument whose Device is FLUIDSYNTH_DEVICE plays through FluidSynth rather than through a MIDI port
of the computer, so that someone with no synthesizer and no DAW hears a
set at once. user_scripts/install_fluidsynth.sh puts FluidSynth in the Mac's own Homebrew and the GeneralUser GS
SoundFont in ~/soundfonts, and this module looks for them there.

The tracker starts FluidSynth only when something is played through it, with the SoundFont, the Mac's
audio and a MIDI port of its own (realtime_names.FLUIDSYNTH_PORT), and waits until that port is listed before anything
is sent to it, so that no note is lost while the SoundFont loads. FluidSynth reads its commands from a
pipe the tracker holds and quits when the pipe closes, so it ends with the tracker, even when the
tracker doesn't end cleanly. Its sound goes to the Mac's default output, or to the audio device that
LLAMATRON_FLUIDSYNTH_AUDIO_DEVICE names, which only the demo recorder sets, to send it to BlackHole.
"""

import functools
import os
import shutil
import subprocess
import time
from typing import NamedTuple

from llamatron.realtime import realtime_names
from llamatron.realtime.devices.ports import output_port_names_now
from llamatron.realtime.sender_process.process import SenderNotStarted
from llamatron.realtime.synth_process import daemon as synth_daemon
from llamatron.user_strings import errors

# Where user_scripts/install_fluidsynth.sh puts FluidSynth: the Apple Silicon Homebrew's, which only an Apple Silicon Mac has, or an
# Intel Mac's, looked for in that order, since a Python under Rosetta reports an Intel machine on Apple Silicon.
HOMEBREW_FLUIDSYNTHS = ('/opt/homebrew/bin/fluidsynth', '/usr/local/bin/fluidsynth')
FLUIDSYNTH_COMMAND = 'fluidsynth'
SOUNDFONT = os.path.join('~', 'soundfonts', 'GeneralUser-GS.sf2')
# The audio device FluidSynth plays to, when something other than the Mac's default output should hear it.
AUDIO_DEVICE_VARIABLE = 'LLAMATRON_FLUIDSYNTH_AUDIO_DEVICE'
LIBRARY_VARIABLE = 'LLAMATRON_FLUIDSYNTH_LIBRARY'
PROCESS_VARIABLE = 'LLAMATRON_FLUIDSYNTH_PROCESS'
DISABLED_VARIABLE = 'NO_FLUIDSYNTH'
IN_DAEMON_VARIABLE = 'LLAMATRON_FLUIDSYNTH_IN_DAEMON'
SWITCHED_ON = '1'
LIBRARY_FOLDER = 'lib'
LIBRARY_NAMES = ('libfluidsynth.dylib', 'libfluidsynth.3.dylib', 'libfluidsynth.so.3', 'libfluidsynth.so')
SYSTEM_LIBRARY_FOLDERS = ('/opt/homebrew/lib', '/usr/local/lib', '/usr/lib/x86_64-linux-gnu', '/usr/lib/aarch64-linux-gnu', '/usr/lib64', '/usr/lib')
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
# FluidSynth's audio buffer, set rather than left to its defaults, so that its latency is known and the same every run: a
# period of 128 frames, the built-in synths' own chunk, and two periods. A note reaches FluidSynth at the start of its next
# period, so its timing is held to a period (.claude/notes/synthesis/ENGINE_ARCHITECTURE.md, "The User's Constraints").
PERIOD_FRAMES = 128
PERIODS = 2
PERIOD_SIZE_OPTION = '-z'
PERIODS_OPTION = '-c'


class FluidSynthNotStarted(SenderNotStarted):
    """FluidSynth ended, or its port never appeared, so nothing can play through it."""


def fluidsynth_path():
    """Return where FluidSynth is: in the Mac's own Homebrew, else wherever PATH finds it, or None when it isn't installed."""
    for path in HOMEBREW_FLUIDSYNTHS:
        if os.access(path, os.X_OK):
            return path
    return shutil.which(FLUIDSYNTH_COMMAND)


def library_path(*, environment=None):
    """Return FluidSynth's library, which the synth daemon loads to play FluidSynth itself: LLAMATRON_FLUIDSYNTH_LIBRARY where
    set, else the one installed beside the fluidsynth program (its folder's lib/), else one in the system's library folders,
    or None where there is none."""
    environment = os.environ if environment is None else environment
    given = environment.get(LIBRARY_VARIABLE)
    if given:
        return given if os.path.isfile(given) else None
    program = fluidsynth_path()
    folders = list(SYSTEM_LIBRARY_FOLDERS)
    if program is not None:
        folders.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(program))), LIBRARY_FOLDER))
    for folder in folders:
        for name in LIBRARY_NAMES:
            path = os.path.join(folder, name)
            if os.path.isfile(path):
                return path
    return None


def plays_in_daemon(*, environment=None):
    """Return whether FluidSynth plays inside the synth daemon, sharing its stream and clock with the built-in synths: the
    daemon is built, FluidSynth's library and the SoundFont are installed, LLAMATRON_FLUIDSYNTH_IN_DAEMON=1 asks for it, and
    LLAMATRON_FLUIDSYNTH_PROCESS=1 does not ask for FluidSynth's own process, as before."""
    environment = os.environ if environment is None else environment
    if is_disabled(environment=environment) or environment.get(PROCESS_VARIABLE) == SWITCHED_ON:
        return False
    # Asked for by name until it has played through the installed library on the user's computer, then the default.
    if environment.get(IN_DAEMON_VARIABLE) != SWITCHED_ON:
        return False
    if not synth_daemon.uses_daemon(environment=environment):
        return False
    return library_path(environment=environment) is not None and os.path.isfile(soundfont_path())


def soundfont_path():
    return os.path.expanduser(SOUNDFONT)


def is_disabled(*, environment=None):
    """Return whether NO_FLUIDSYNTH=1 turns FluidSynth off, for a computer where it does not work: nothing then plays or
    exports through it, wherever it is installed."""
    environment = os.environ if environment is None else environment
    return environment.get(DISABLED_VARIABLE) == SWITCHED_ON


def is_installed():
    """Return whether FluidSynth and the SoundFont it plays are both where user_scripts/install_fluidsynth.sh puts them, and
    FluidSynth is not turned off (is_disabled)."""
    if is_disabled():
        return False
    return fluidsynth_path() is not None and os.path.isfile(soundfont_path())


@functools.cache
class FluidSynthInstallation(NamedTuple):
    """Where FluidSynth's program and its SoundFont are, which a WAV export plays through."""

    program: str
    soundfont: str


def installation():
    """Return where FluidSynth and its SoundFont are installed, or None where they aren't."""
    if not installed():
        return None
    return FluidSynthInstallation(fluidsynth_path(), soundfont_path())


def installed():
    """Return whether FluidSynth and its SoundFont are installed, looked for once a run (is_installed), since every launch,
    listening page and WAV export asks, and the files do not come and go while the tracker runs."""
    return is_installed()


def command(*, audio_device=None):
    """Return the command that starts FluidSynth as a MIDI port with the SoundFont, playing to the audio device given or the default."""
    words = [fluidsynth_path(), *AUDIO_DRIVER, *MIDI_DRIVER, SETTING, PORT_NAME.format(name=realtime_names.FLUIDSYNTH_PORT), GAIN_OPTION, GAIN,
             PERIOD_SIZE_OPTION, str(PERIOD_FRAMES), PERIODS_OPTION, str(PERIODS)]
    if audio_device:
        words += [SETTING, AUDIO_DEVICE_SETTING.format(device=audio_device)]
    return [*words, soundfont_path()]


class FluidSynth:
    """The tracker's FluidSynth: started when something first plays through it, and ended with the tracker."""

    __slots__ = ('_process', '_port_names', '_start_process', '_now', '_sleep', '_in_daemon')

    def __init__(self, *, port_names=output_port_names_now, start_process=None, now=time.monotonic, sleep=time.sleep, in_daemon=plays_in_daemon):
        """port_names, start_process(words), now, sleep and in_daemon() are for the tests, which start no real FluidSynth."""
        self._process = None
        self._in_daemon = in_daemon
        self._port_names = port_names
        if start_process is None:
            start_process = self._popen
        self._start_process = start_process
        self._now = now
        self._sleep = sleep

    def is_running(self):
        """Return whether FluidSynth plays: its own process runs, or the synth daemon plays it, which is never stopped here."""
        if self._in_daemon():
            return True
        return self._process is not None and self._process.poll() is None

    def ensure_running(self):
        """Start FluidSynth unless it runs, and wait until its port is listed. Return whether it was started now, so that whatever opened the old port opens the new one.

        A FluidSynth that runs has its port, which it made as it started, so the ports are listed again only while a new one starts.
        """
        if self.is_running():
            return False
        self.stop()
        self._process = self._start_process(command(audio_device=os.environ.get(AUDIO_DEVICE_VARIABLE)))
        started = self._now()
        while realtime_names.FLUIDSYNTH_PORT not in self._port_names():
            code = self._process.poll()
            if code is not None:
                self._process = None
                raise FluidSynthNotStarted(errors.ERR_FLUIDSYNTH_ENDED.format(code=code))
            if self._now() - started > START_SECONDS:
                self.stop()
                raise FluidSynthNotStarted(errors.ERR_FLUIDSYNTH_DID_NOT_START.format(seconds=START_SECONDS))
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
