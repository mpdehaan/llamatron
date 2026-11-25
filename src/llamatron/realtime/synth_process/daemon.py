# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The built-in synths' native daemon, llamatron-synth (native/synth/), started and watched by the parent.

The daemon plays the sound card itself, from notes timed on the very clock time.perf_counter reads, so that a note is
placed on its exact sample without conversion. The parent speaks MessagePack to it over its standard input and output,
each message an array framed by its length (native/synth/src/protocol.rs), behind the same calls as the Python
Synthesis Process (process.py): start, set_instrument, notes, forget, silence, close. A reader thread takes the daemon's
load reports as they come, the last kept for the screen, and its statistics as it closes.

It is never orphaned or left a zombie: it exits when its input closes or its parent dies, and the parent closes it, waits
for it and kills it if it hangs. Rendering offline, for the WAV export, runs a daemon of its own (render_offline).
LLAMATRON_PYTHON_SYNTH=1 plays the Python engine instead, while that engine is kept.
"""

import atexit
import msgpack
import os
import struct
import subprocess
import threading

from llamatron.realtime.synth_process import engine as engine_values
from llamatron.realtime.synth_process.process import SynthesisNotStarted
from llamatron.user_strings import errors

DAEMON_NAME = 'llamatron-synth'
DAEMON_PATH = 'LLAMATRON_SYNTH_DAEMON'
PYTHON_SYNTH = 'LLAMATRON_PYTHON_SYNTH'
SWITCHED_ON = '1'
BUILT_FOLDER = ('native', 'synth', 'target', 'release')
PLAY = 'play'
RENDER = 'render'
BLOCK_OPTION = '--block'
DEVICE_OPTION = '--device'
RATE_OPTION = '--rate'
READY = 'ready'
FAILED = 'failed'
LOAD = 'load'
STATISTICS = 'statistics'
RENDERED = 'rendered'
INSTRUMENT = 'instrument'
NOTES = 'notes'
SILENCE = 'silence'
CLOSE = 'close'
RENDER_MESSAGE = 'render'
LENGTH = struct.Struct('>I')
CLOSE_TIMEOUT_SECONDS = 2.0
DEFAULT_BLOCK = 128


def daemon_path(*, environment=None):
    """Return the daemon's program: LLAMATRON_SYNTH_DAEMON where set, else the one built in the source tree, or None if
    there is none."""
    environment = os.environ if environment is None else environment
    given = environment.get(DAEMON_PATH)
    if given:
        return given if os.path.isfile(given) else None
    top = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    built = os.path.join(top, *BUILT_FOLDER, DAEMON_NAME)
    return built if os.path.isfile(built) else None


def uses_daemon(*, environment=None):
    """Return whether built-in sound plays through the native daemon: it is built, and the Python engine is not asked for."""
    environment = os.environ if environment is None else environment
    return environment.get(PYTHON_SYNTH) != SWITCHED_ON and daemon_path(environment=environment) is not None


class DaemonChannel:
    """The two pipes to a running daemon: messages written whole under a lock, since several threads send, and read one at a
    time."""

    __slots__ = ('_process', '_lock')

    def __init__(self, *, process):
        self._process = process
        self._lock = threading.Lock()

    def send(self, message):
        body = msgpack.packb(message, use_bin_type=True)
        with self._lock:
            self._process.stdin.write(LENGTH.pack(len(body)) + body)
            self._process.stdin.flush()

    def receive(self):
        """Return the daemon's next message, or None once its output has closed."""
        head = self._process.stdout.read(LENGTH.size)
        if len(head) < LENGTH.size:
            return None
        body = self._process.stdout.read(LENGTH.unpack(head)[0])
        return msgpack.unpackb(body, raw=False)


class SynthDaemon:
    """The playing daemon, behind the calls of the Python Synthesis Process: its process and channel, the rate and delay its
    stream reported, its last load report and its statistics once closed."""

    __slots__ = ('_block', '_device', '_process', '_channel', '_reader', '_closed', 'rate', 'delay', 'load', 'statistics')

    def __init__(self, *, block=DEFAULT_BLOCK, device=None):
        self._block = block
        self._device = device
        self._process = None
        self._channel = None
        self._reader = None
        self._closed = threading.Event()
        self.rate = None
        self.delay = 0.0
        self.load = None
        self.statistics = None

    def start(self):
        """Start the daemon and wait until its stream plays, returning the sample rate and the delay in seconds."""
        program = daemon_path()
        if program is None:
            raise SynthesisNotStarted(errors.ERR_SYNTH_DAEMON_MISSING)
        command = [program, PLAY, BLOCK_OPTION, str(self._block)]
        if self._device is not None:
            command += [DEVICE_OPTION, str(self._device)]
        self._process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self._channel = DaemonChannel(process=self._process)
        atexit.register(self.close)
        message = self._channel.receive()
        if message is None:
            code = self._end_process()
            raise SynthesisNotStarted(errors.ERR_SYNTHESIS_ENDED.format(code=code))
        if message[0] == FAILED:
            self.close()
            raise SynthesisNotStarted(errors.ERR_SYNTHESIS_FAILED.format(kind=message[1], problem=message[2]))
        _, self.rate, self.delay = message
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()
        return self.rate, self.delay

    def set_instrument(self, *, number, spec):
        self._send([INSTRUMENT, number, spec])

    def notes(self, notes):
        """Send notes, each (perf_counter seconds, kind, instrument, pitch, velocity)."""
        self._send([NOTES, [list(note) for note in notes]])

    def forget(self, *, first, last, after):
        """Take back the notes still to come from a perf_counter moment on, of the instruments numbered first to last."""
        self._send([NOTES, [[after, engine_values.FORGET, first, last, 0]]])

    def silence(self):
        self._send([SILENCE])

    def close(self):
        """End the daemon and wait for it, killing it if it hangs, and return its statistics, or None."""
        if self._process is None:
            return self.statistics
        try:
            self._send([CLOSE])
        except (BrokenPipeError, OSError, ValueError):
            pass
        if self._reader is not None:
            self._closed.wait(CLOSE_TIMEOUT_SECONDS)
        self._end_process()
        return self.statistics

    def is_alive(self):
        return self._process is not None and self._process.poll() is None

    def _send(self, message):
        if self._channel is not None and self.is_alive():
            self._channel.send(message)

    def _read(self):
        """Take the daemon's messages until its output closes: its load reports, kept, and its statistics as it closes."""
        while True:
            try:
                message = self._channel.receive()
            except (OSError, ValueError, msgpack.UnpackException):
                message = None
            if message is None:
                break
            if message[0] == LOAD:
                self.load = message[1]
            elif message[0] == STATISTICS:
                self.statistics = message[1]
        self._closed.set()

    def _end_process(self):
        """Close the daemon's input, wait for it to end, killing it if it hangs, and return its exit code."""
        process = self._process
        if process is None:
            return None
        try:
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        try:
            process.wait(CLOSE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        process.stdout.close()
        self._process = None
        return process.returncode


def built_in_renderer():
    """Return what renders built-in instruments offline for the WAV export, render_offline, or None where the daemon is not
    built."""
    if daemon_path() is None:
        return None
    return render_offline


def render_offline(*, tracks, seconds, path, rate):
    """Render tracks on the built-in instruments into a WAV file of 32-bit floats at a rate, through the daemon's own engine
    and safety guard, as fast as it can: each track an instrument's spec, its notes as (seconds, pitch, velocity), a
    velocity of 0 ending a note, its clips' starts and the moments every note of it ends (exporters/built_in_wave.py).
    Return the daemon's report."""
    program = daemon_path()
    if program is None:
        raise SynthesisNotStarted(errors.ERR_SYNTH_DAEMON_MISSING)
    process = subprocess.Popen([program, RENDER, RATE_OPTION, str(rate)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    channel = DaemonChannel(process=process)
    try:
        for number, track in enumerate(tracks):
            channel.send([INSTRUMENT, number, track.spec])
            channel.send([NOTES, offline_notes(number=number, track=track)])
        channel.send([RENDER_MESSAGE, path, seconds])
        answer = channel.receive()
        channel.send([CLOSE])
    finally:
        process.stdin.close()
        process.wait()
        process.stdout.close()
    if answer is None or answer[0] != RENDERED:
        raise SynthesisNotStarted(errors.ERR_SYNTH_DAEMON_RENDER_FAILED.format(answer=answer))
    return answer[1]


def offline_notes(*, number, track):
    """Return a track's notes, clip starts and endings as the daemon takes notes, [seconds, kind, instrument, pitch,
    velocity]."""
    notes = []
    for when in track.scene_starts:
        notes.append([when, engine_values.SCENE_STARTED, number, 0, 0])
    for when, pitch, velocity in track.notes:
        kind = engine_values.NOTE_ON
        if velocity == 0:
            kind = engine_values.NOTE_OFF
        notes.append([when, kind, number, pitch, velocity])
    for when in track.endings:
        notes.append([when, engine_values.ALL_OFF, number, 0, 0])
    return notes
