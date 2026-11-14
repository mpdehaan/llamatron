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

"""The Realtime Sender Process: the playback engine run in a process of its own, so that the tracker's drawing never delays a note.

A thread in the tracker's process drifts by up to five milliseconds, the interpreter's switch interval, while the
screen draws; a separate process measured within a tenth of a millisecond (internal_tools/midi_timing_spike.py). The tracker
keeps a RealtimeMIDISenderProcess and talks to it in a few messages over a pipe: start, add events, drop a clip's
events from a time, stop a clip, stop everything, close. The process sleeps in short slices until just before the
next event is due and then spins on the clock, since sleep alone is loose on macOS, and polls the pipe between.
"""

import contextlib
import multiprocessing
import sys
import time

from llamatron.realtime.engine import MonotonicClock, PlaybackEngine
from llamatron.realtime.outputs import RecordingOutput, RtMidiOutput
from llamatron.strings.errors import ERR_SENDER_DID_NOT_START

SPAWN = 'spawn'
# How long before an event is due the process stops sleeping and spins, and how long it sleeps at a time until then.
SPIN_SECONDS = 0.0015
SLEEP_SLICE_SECONDS = 0.0005
# The messages the tracker sends the process.
READY = 'ready'
START = 'start'
ADD = 'add'
DROP = 'drop'
STOP_TAG = 'stop_tag'
STOP_ALL = 'stop_all'
SILENCE = 'silence'
CLOSE = 'close'
# How long the tracker waits for the process to end before ending it itself.
CLOSE_TIMEOUT_SECONDS = 2.0
# How long the process may take to import and open its ports before start gives up on it.
START_TIMEOUT_SECONDS = 10.0


class SenderNotStarted(RuntimeError):
    """The process ended before it had opened its ports, which it does when a port cannot be opened."""


class RealtimeMIDISenderProcess:
    """The tracker's side of the sender: starts the process on the ports named, and sends it the messages above."""

    __slots__ = ('_ports', '_recording', '_connection', '_process')

    def __init__(self, *, ports, recording=False):
        """ports are the names of the output ports to open. With recording, the process opens RecordingOutputs in their place and hands back what it sent on close."""
        self._ports = list(ports)
        self._recording = recording
        self._connection = None
        self._process = None

    def start(self, *, at=None):
        """Start the process, which opens the ports, and take this moment, or a reading of the clock given, as the timeline's zero."""
        context = multiprocessing.get_context(SPAWN)
        self._connection, far_end = context.Pipe()
        self._process = context.Process(target=run_sender, kwargs=dict(connection=far_end, ports=self._ports, recording=self._recording))
        with real_standard_error():
            self._process.start()
        # Wait until the process has opened its ports, so that the first event is not sent late while it starts up, which measured about 150 ms on the IAC bus.
        if not self._connection.poll(START_TIMEOUT_SECONDS) or self._connection.recv() != READY:
            self.close()
            raise SenderNotStarted(ERR_SENDER_DID_NOT_START)
        self._connection.send((START, at))

    def add(self, events):
        self._connection.send((ADD, list(events)))

    def drop(self, *, tag, after):
        self._connection.send((DROP, tag, after))

    def stop_tag(self, tag):
        self._connection.send((STOP_TAG, tag))

    def stop_all(self):
        self._connection.send((STOP_ALL,))

    def silence(self, *, channels):
        self._connection.send((SILENCE, list(channels)))

    def close(self):
        """Stop everything, close the ports and end the process. With recording, return the seconds the timeline started at and every (seconds, bytes) sent, by port, or None when the process never answered."""
        result = None
        if self._process is None:
            return result
        if self._process.is_alive():
            self._connection.send((CLOSE,))
            if self._connection.poll(CLOSE_TIMEOUT_SECONDS):
                result = self._connection.recv()
        self._process.join(CLOSE_TIMEOUT_SECONDS)
        if self._process.is_alive():
            self._process.terminate()
        self._connection.close()
        return result


@contextlib.contextmanager
def real_standard_error():
    """Put the interpreter's own standard error back while a process is spawned, since spawn's resource tracker passes sys.stderr's file descriptor to its child and Textual's capture, in place while the tracker runs, answers -1 for it, which failed the spawn with "bad value(s) in fds_to_keep" on 2026-11-10."""
    captured = sys.stderr
    sys.stderr = sys.__stderr__
    try:
        yield
    finally:
        sys.stderr = captured


def run_sender(*, connection, ports, recording):
    """The process: an engine on the real clock, fed by the pipe, sending each event when its time comes."""
    try:
        outputs = {name: (RecordingOutput() if recording else RtMidiOutput(name=name)) for name in ports}
    except Exception:  # noqa: BLE001, the process boundary: a port that cannot be opened, for whatever reason the library gives, ends the process quietly, and the tracker's side raises SenderNotStarted when the pipe closes without READY, rather than a traceback written over the tracker's screen.
        return
    engine = PlaybackEngine(clock=MonotonicClock(), outputs=outputs)
    connection.send(READY)
    started = None
    while True:
        due = engine.next_due()
        if due is None or not engine.is_started():
            wait = None
        else:
            left = due - engine.elapsed()
            if left <= SPIN_SECONDS:
                while engine.elapsed() < due:
                    pass
                engine.send_due()
                continue
            wait = min(left - SPIN_SECONDS, SLEEP_SLICE_SECONDS)
        if connection.poll(wait):
            message = connection.recv()
            kind = message[0]
            if kind == START:
                engine.start(at=message[1])
                started = time.perf_counter() if message[1] is None else message[1]
            elif kind == ADD:
                engine.add(message[1])
            elif kind == DROP:
                engine.drop(tag=message[1], after=message[2])
            elif kind == STOP_TAG:
                engine.stop_tag(message[1])
            elif kind == STOP_ALL:
                engine.stop_all()
            elif kind == SILENCE:
                engine.silence(channels=message[1])
            elif kind == CLOSE:
                engine.close()
                sent = {name: output.sent for name, output in outputs.items()} if recording else None
                connection.send((started, sent))
                return
