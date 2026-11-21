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


"""Measure how tightly MIDI arrives from today's Realtime Sender Process against a prototype that hands each event to CoreMIDI
ahead of time, stamped with the moment it should sound, so that the system's MIDI driver delivers it on time however late the
sender's process wakes (macOS only).

Both senders are fed alike: a grid of sixteenth notes at TEMPO, in windows of the next WINDOW_SECONDS added every FEED_SECONDS,
as the player feeds the sender. One receiver notes when each note arrives on its own clock, the same for both, and the report
gives each sender's arrival error after the constant part is taken out: the median, the 99th and 99.9th percentiles, the worst,
and how many notes were later than LATE_SECONDS. --load starts that many busy processes for the length of each run, to measure
under load.

By default everything goes to a virtual port the tool makes, which nothing else listens to, so nothing is heard. --port names
another destination, such as the IAC bus, whose notes would reach whatever listens to it; the tool measures there only where the
port loops back to an input of the same name, as the IAC bus does.

    .venv/bin/python internal_tools/coremidi_timing.py                     # 30 seconds each, at rest
    .venv/bin/python internal_tools/coremidi_timing.py --seconds 600 --load 8
"""

import argparse
import ctypes
import multiprocessing
import rtmidi
import statistics
import sys
import threading
import time

from llamatron.realtime.sender_process import RealtimeMIDISenderProcess
from llamatron.realtime.timeline import Playing, Tag

PROBE_PORT = 'llamatron timing probe'
TEMPO = 130
SECONDS_PER_MINUTE = 60
SIXTEENTHS_PER_BEAT = 4
WINDOW_SECONDS = 0.5
FEED_SECONDS = 0.02
# How long before the first note the run starts, for the processes to settle, and after the last for the last to arrive.
SETTLE_SECONDS = 1.0
LATE_SECONDS = 0.001
DEFAULT_SECONDS = 30
DEFAULT_LOAD = 0
# The probe's notes: the top channel, the lowest note, the quietest velocity, so that a listener that does hear them hears little.
CHANNEL = 15
NOTE = 1
VELOCITY = 1
NOTE_ON = 0x90
NOTE_OFF = 0x80
KIND_MASK = 0xF0
GATE_SECONDS = 0.05
# The clock's own zero, which today's sender is given as its timeline's, so that its events are timed by readings of the clock.
CLOCK_ZERO = 0.0
TAG = Tag(0, 'probe')
TODAY = 'today'
TIMESTAMPED = 'timestamped'
SPAWN = 'spawn'
MACOS = 'darwin'
# CoreMIDI's name of the property that holds an endpoint's name.
NAME_PROPERTY = 'kMIDIPropertyName'
COREMIDI = '/System/Library/Frameworks/CoreMIDI.framework/CoreMIDI'
CORE_FOUNDATION = '/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation'
UTF8 = 0x08000100
NAME_BYTES = 256
PACKET_LIST_BYTES = 1024
NANOSECONDS = 1_000_000_000
MILLISECONDS = 1000
PERCENT = 100
P99 = 99
P999 = 99.9
REPORT = '{sender:12} notes {count:6}  median {median:7.3f} ms  p99 {p99:7.3f} ms  p99.9 {p999:7.3f} ms  worst {worst:7.3f} ms  late {late}'
RUN = 'running {sender} for {seconds} s with {load} busy processes'
MISSING = '{sender}: {missing} notes never arrived'
NO_DESTINATION = 'no MIDI destination called {port}'


def note_times(seconds):
    """Return the moment of every note of the grid, in seconds from the first."""
    step = SECONDS_PER_MINUTE / TEMPO / SIXTEENTHS_PER_BEAT
    return [place * step for place in range(int(seconds / step))]


def events_of(*, times, port, zero):
    """Return the grid's note ons and note offs as the sender's events, each at its moment after zero, a reading of the clock."""
    events = []
    for moment in times:
        events.append(Playing(None, zero + moment, port, CHANNEL, NOTE_ON, NOTE, VELOCITY, TAG))
        events.append(Playing(None, zero + moment + GATE_SECONDS, port, CHANNEL, NOTE_OFF, NOTE, 0, TAG))
    return events


def busy():
    """Keep a core busy, as other programs would."""
    while True:
        pass


class CoreMidiSender:
    """The prototype: a CoreMIDI output port that hands each event to the system ahead of time, stamped with its moment."""

    __slots__ = ('_midi', '_port', '_destination', '_buffer', '_mach_per_second', '_mach_zero', '_clock_zero')

    def __init__(self, port_name):
        self._midi = ctypes.CDLL(COREMIDI)
        foundation = ctypes.CDLL(CORE_FOUNDATION)
        system = ctypes.CDLL(None)
        foundation.CFStringCreateWithCString.restype = ctypes.c_void_p
        foundation.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        foundation.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
        self._midi.MIDIGetDestination.restype = ctypes.c_uint32
        self._midi.MIDIPacketListInit.restype = ctypes.c_void_p
        self._midi.MIDIPacketListAdd.restype = ctypes.c_void_p
        self._midi.MIDIPacketListAdd.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_uint64, ctypes.c_size_t, ctypes.c_char_p]
        system.mach_absolute_time.restype = ctypes.c_uint64
        timebase = (ctypes.c_uint32 * 2)()
        system.mach_timebase_info(timebase)
        self._mach_per_second = NANOSECONDS * timebase[1] / timebase[0]
        client = ctypes.c_uint32()
        self._port = ctypes.c_uint32()
        self._midi.MIDIClientCreate(ctypes.c_void_p(foundation.CFStringCreateWithCString(None, PROBE_PORT.encode(), UTF8)), None, None, ctypes.byref(client))
        self._midi.MIDIOutputPortCreate(client, ctypes.c_void_p(foundation.CFStringCreateWithCString(None, PROBE_PORT.encode(), UTF8)), ctypes.byref(self._port))
        self._destination = self._find(foundation=foundation, name=port_name)
        self._buffer = ctypes.create_string_buffer(PACKET_LIST_BYTES)
        # The same moment on the two clocks, the system's mach clock that CoreMIDI stamps with and the clock the events are timed by.
        self._mach_zero = system.mach_absolute_time()
        self._clock_zero = time.perf_counter()

    def _find(self, *, foundation, name):
        names = ctypes.c_void_p.in_dll(self._midi, NAME_PROPERTY)
        for place in range(self._midi.MIDIGetNumberOfDestinations()):
            destination = self._midi.MIDIGetDestination(place)
            found = ctypes.c_void_p()
            self._midi.MIDIObjectGetStringProperty(destination, names, ctypes.byref(found))
            text = ctypes.create_string_buffer(NAME_BYTES)
            foundation.CFStringGetCString(found, text, NAME_BYTES, UTF8)
            if text.value == name.encode():
                return destination
        raise ValueError(NO_DESTINATION.format(port=name))

    def send(self, event):
        """Hand an event to CoreMIDI now, stamped with the moment it should sound."""
        packet = self._midi.MIDIPacketListInit(self._buffer)
        stamp = self._mach_zero + int((event.seconds - self._clock_zero) * self._mach_per_second)
        data = bytes(event.data())
        self._midi.MIDIPacketListAdd(self._buffer, PACKET_LIST_BYTES, packet, stamp, len(data), data)
        self._midi.MIDISend(self._port, self._destination, self._buffer)


def run_timestamped(*, connection, port):
    """The prototype's process: each window of events is handed to CoreMIDI the moment it comes."""
    sender = CoreMidiSender(port)
    connection.send(True)
    while True:
        events = connection.recv()
        if events is None:
            return
        for event in events:
            sender.send(event)


class TimestampedProcess:
    """The prototype in a process of its own, fed as the Realtime Sender Process is."""

    __slots__ = ('_connection', '_process')

    def __init__(self, port):
        context = multiprocessing.get_context(SPAWN)
        self._connection, far_end = context.Pipe()
        self._process = context.Process(target=run_timestamped, kwargs=dict(connection=far_end, port=port))
        self._process.start()
        self._connection.recv()

    def add(self, events):
        self._connection.send(list(events))

    def close(self):
        self._connection.send(None)
        self._process.join()


def started_sender(*, kind, port):
    """Return a running sender of a kind, both timing events by the same system clock: today's takes the clock's own zero as its
    timeline's, so that an event's seconds are a reading of the clock, as the prototype's are."""
    if kind == TIMESTAMPED:
        return TimestampedProcess(port)
    sender = RealtimeMIDISenderProcess(ports=[port])
    sender.start(at=CLOCK_ZERO)
    return sender


def feed(*, sender, events):
    """Add each event to the sender as its window comes, the next WINDOW_SECONDS every FEED_SECONDS, as the player does."""
    fed = 0
    pause = threading.Event()
    while fed < len(events):
        due = time.perf_counter() + WINDOW_SECONDS
        window = []
        while fed < len(events) and events[fed].seconds <= due:
            window.append(events[fed])
            fed += 1
        if window:
            sender.add(window)
        pause.wait(FEED_SECONDS)


def measure(*, kind, port, seconds, load):
    """Run one sender over the grid and return each note's arrival error, in seconds, and how many never arrived."""
    arrived = []
    listener = rtmidi.MidiIn()
    if port == PROBE_PORT:
        listener.open_virtual_port(PROBE_PORT)
    else:
        listener.open_port(listener.get_ports().index(port))
    listener.set_callback(lambda message, data: arrived.append((time.perf_counter(), message[0][0])))
    workers = [multiprocessing.get_context(SPAWN).Process(target=busy, daemon=True) for _ in range(load)]
    for worker in workers:
        worker.start()
    time.sleep(SETTLE_SECONDS / 2)
    times = note_times(seconds)
    sender = started_sender(kind=kind, port=port)
    zero = time.perf_counter() + SETTLE_SECONDS
    feed(sender=sender, events=events_of(times=times, port=port, zero=zero))
    time.sleep(SETTLE_SECONDS)
    sender.close()
    for worker in workers:
        worker.terminate()
    listener.close_port()
    ons = [moment for moment, status in arrived if status & KIND_MASK == NOTE_ON]
    errors = [moment - (zero + intended) for moment, intended in zip(ons, times)]
    return errors, len(times) - len(ons)


def report(*, kind, errors, missing):
    """Print a sender's arrival errors with the constant part taken out, in milliseconds."""
    middle = statistics.median(errors)
    spread = sorted(abs(error - middle) for error in errors)
    print(REPORT.format(
        sender=kind, count=len(errors), median=middle * MILLISECONDS, p99=percentile(ordered=spread, percent=P99) * MILLISECONDS,
        p999=percentile(ordered=spread, percent=P999) * MILLISECONDS, worst=spread[-1] * MILLISECONDS, late=sum(1 for error in spread if error > LATE_SECONDS),
    ))
    if missing:
        print(MISSING.format(sender=kind, missing=missing))


def percentile(*, ordered, percent):
    """Return the value a share of the ordered values lie at or below, by percent."""
    return ordered[min(int(len(ordered) * percent / PERCENT), len(ordered) - 1)]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--seconds', type=float, default=DEFAULT_SECONDS)
    parser.add_argument('--load', type=int, default=DEFAULT_LOAD)
    parser.add_argument('--port', default=PROBE_PORT)
    arguments = parser.parse_args()
    if sys.platform != MACOS:
        raise SystemExit(__doc__.splitlines()[0])
    for kind in (TODAY, TIMESTAMPED):
        print(RUN.format(sender=kind, seconds=arguments.seconds, load=arguments.load), flush=True)
        errors, missing = measure(kind=kind, port=arguments.port, seconds=arguments.seconds, load=arguments.load)
        report(kind=kind, errors=errors, missing=missing)


if __name__ == '__main__':
    main()
