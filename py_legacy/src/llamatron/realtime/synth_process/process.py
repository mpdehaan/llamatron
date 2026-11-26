# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Synthesis Process: the engine played through the sound card in a process of its own.

The parent keeps a SynthesisProcess and talks to it over a pipe: instruments, notes with their times, silence, close. Notes
carry times on the clock the Realtime Sender Process uses, time.perf_counter, and the process turns each into its exact sample
from the moment PortAudio says each chunk reaches the speakers, plus the delay every instrument is held back by, so that
built-in sound and MIDI land together. Drum hits are rendered by the reader thread as notes arrive, never in the audio
callback, which only pops due notes and mixes. Garbage collection is off while it plays.

It is never orphaned or left a zombie: it exits on its own when the pipe to its parent closes, the parent's death included;
the parent closes it, joins it and kills it if it hangs; and a problem starting it, such as no sound card or no PortAudio,
comes back as its reason before anything plays. sounddevice is imported only inside the process, so that llamatron opens
on a computer without PortAudio.
"""

import atexit
import gc
import multiprocessing
import os
import sys
import traceback

from llamatron.realtime.synth_process import engine as engine_values
from llamatron.user_strings import errors

SPAWN = 'spawn'
READY = 'ready'
FAILED = 'failed'
INSTRUMENT = 'instrument'
NOTES = 'notes'
SILENCE = 'silence'
CLOSE = 'close'
STATISTICS = 'statistics'
START_TIMEOUT_SECONDS = 10.0
CLOSE_TIMEOUT_SECONDS = 2.0
CHANNELS = 2
DEFAULT_BLOCK = 128
# Built-in sound is for macOS first: elsewhere it is off unless asked for, so that it never stops llamatron loading.
TRY_ANYWAY = 'ATTEMPT_SYNTHESIS_ANYWAY'
MACOS = 'darwin'


class SynthesisNotStarted(RuntimeError):
    """The Synthesis Process could not start, with the reason why."""


def synthesis_available(*, environment=None, platform=None):
    """Return whether built-in sound may be tried here: on macOS, or anywhere with ATTEMPT_SYNTHESIS_ANYWAY=1."""
    environment = os.environ if environment is None else environment
    platform = sys.platform if platform is None else platform
    return platform == MACOS or environment.get(TRY_ANYWAY) == '1'


class SynthesisProcess:
    """The parent's handle on the Synthesis Process: start() waits until it plays or raises SynthesisNotStarted with why; the
    delay it reports is what MIDI must be held back by so that everything lands together."""

    __slots__ = ('_block', '_device', '_process', '_connection', 'rate', 'delay')

    def __init__(self, *, block=DEFAULT_BLOCK, device=None):
        self._block = block
        self._device = device
        self._process = None
        self._connection = None
        self.rate = None
        self.delay = 0.0

    def start(self):
        """Start the process and wait until its stream plays, returning the sample rate and the delay in seconds."""
        if not synthesis_available():
            raise SynthesisNotStarted(errors.ERR_SYNTHESIS_OFF)
        context = multiprocessing.get_context(SPAWN)
        parent, child = context.Pipe()
        self._process = context.Process(target=run, kwargs={'connection': child, 'block': self._block, 'device': self._device}, daemon=True)
        self._process.start()
        child.close()
        self._connection = parent
        atexit.register(self.close)
        if not parent.poll(START_TIMEOUT_SECONDS):
            self.close()
            raise SynthesisNotStarted(errors.ERR_SYNTHESIS_TOO_SLOW)
        try:
            message = parent.recv()
        except (EOFError, OSError):
            self._process.join(CLOSE_TIMEOUT_SECONDS)
            code = self._process.exitcode
            self.close()
            raise SynthesisNotStarted(errors.ERR_SYNTHESIS_ENDED.format(code=code))
        if message[0] == FAILED:
            self.close()
            raise SynthesisNotStarted(message[1])
        _, self.rate, self.delay = message
        return self.rate, self.delay

    def set_instrument(self, *, number, spec):
        self._send((INSTRUMENT, number, spec))

    def notes(self, notes):
        """Send notes, each (perf_counter seconds, kind, instrument, pitch, velocity)."""
        self._send((NOTES, notes))

    def forget(self, *, first, last, after):
        """Take back the notes still to come from a perf_counter moment on, of the instruments numbered first to last."""
        self._send((NOTES, [(after, engine_values.FORGET, first, last, 0)]))

    def silence(self):
        self._send((SILENCE,))

    def close(self):
        """End the process and wait for it, killing it if it hangs, and return its statistics, or None."""
        statistics = self._ask_to_close()
        self._end_process()
        return statistics

    def is_alive(self):
        return self._process is not None and self._process.is_alive()

    def _ask_to_close(self):
        """Tell the process to close and return the statistics it answers with, or None if it is gone or silent."""
        if self._connection is None:
            return None
        statistics = None
        try:
            self._connection.send((CLOSE,))
            if self._connection.poll(CLOSE_TIMEOUT_SECONDS):
                reply = self._connection.recv()
                if reply[0] == STATISTICS:
                    statistics = reply[1]
        except (BrokenPipeError, EOFError, OSError):
            statistics = None
        self._connection.close()
        self._connection = None
        return statistics

    def _end_process(self):
        """Wait for the process to end, killing it if it hangs, so that it is never left an orphan or a zombie."""
        if self._process is None:
            return
        self._process.join(CLOSE_TIMEOUT_SECONDS)
        if self._process.is_alive():
            self._process.kill()
            self._process.join()
        self._process = None

    def _send(self, message):
        if self._connection is not None:
            self._connection.send(message)


def run(*, connection, block, device):
    """The process: open the stream, tell the parent it plays or why not, then take messages until told to close or the
    parent goes away."""
    try:
        import sounddevice
        from llamatron.realtime.synth_process.player import SynthPlayer
        player = SynthPlayer(sounddevice=sounddevice, block=block, device=device)
        player.start()
    except Exception as problem:  # Any failure to start is told to the parent, never hidden.
        connection.send((FAILED, errors.ERR_SYNTHESIS_FAILED.format(kind=type(problem).__name__, problem=problem or traceback.format_exc(limit=1))))
        connection.close()
        return
    connection.send((READY, player.rate, player.delay))
    gc.collect()
    gc.freeze()
    gc.disable()
    try:
        _serve(connection=connection, player=player)
    finally:
        statistics = player.stop()
        try:
            connection.send((STATISTICS, statistics))
        except (BrokenPipeError, OSError):
            pass
        connection.close()


def _serve(*, connection, player):
    """Take the parent's messages until it says close or its end of the pipe closes."""
    while True:
        try:
            message = connection.recv()
        except (EOFError, OSError):
            return
        kind = message[0]
        if kind == CLOSE:
            return
        if kind == NOTES:
            player.add_notes(message[1])
        elif kind == INSTRUMENT:
            player.set_instrument(number=message[1], spec=message[2])
        elif kind == SILENCE:
            player.silence()
