# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""Measure how tightly MIDI arrives from the Realtime Sender Process with each of its drivers: the immediate one, which sends each
event as its moment comes, and the timestamped one, which hands each event to CoreMIDI ahead of time, stamped with its moment, so
that the system's MIDI driver delivers it on time however late the sender's process wakes (macOS only).

Both drivers are fed alike: a grid of sixteenth notes at TEMPO, in windows of the next WINDOW_SECONDS added every FEED_SECONDS,
as the player feeds the sender. One receiver notes when each note arrives on its own clock, the same for both, and the report
gives each driver's offset, the constant part of its arrival error, and then with the offset taken out the 99th and 99.9th percentiles, the worst,
and how many notes were later than LATE_SECONDS. --load starts that many busy processes for the length of each run, to measure
under load.

By default everything goes to a virtual port the tool makes, which nothing else listens to, so nothing is heard. --port names
another destination, such as the IAC bus, whose notes would reach whatever listens to it; the tool measures there only where the
port loops back to an input of the same name, as the IAC bus does.

    .venv/bin/python internal_tools/coremidi_timing.py                     # 30 seconds each, at rest
    .venv/bin/python internal_tools/coremidi_timing.py --seconds 600 --load 8
"""

import argparse
import multiprocessing
import rtmidi
import statistics
import sys
import threading
import time

from llamatron.realtime import sender_process
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
# The clock's own zero, which the sender is given as its timeline's, so that its events are timed by readings of the clock.
CLOCK_ZERO = 0.0
TAG = Tag(0, 'probe')
SPAWN = 'spawn'
MACOS = 'darwin'
MILLISECONDS = 1000
PERCENT = 100
P99 = 99
P999 = 99.9
REPORT = '{sender:12} notes {count:6}  offset {median:7.3f} ms  p99 {p99:7.3f} ms  p99.9 {p999:7.3f} ms  worst {worst:7.3f} ms  late {late}'
RUN = 'running {sender} for {seconds} s with {load} busy processes'
MISSING = '{sender}: {missing} notes never arrived'


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


def started_sender(*, kind, port):
    """Return the Realtime Sender Process running with a driver, taking the clock's own zero as its timeline's, so that an event's
    seconds are a reading of the clock, as the receiver's are."""
    sender = RealtimeMIDISenderProcess(ports=[port], driver=kind)
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
    for kind in (sender_process.IMMEDIATE, sender_process.TIMESTAMPED):
        print(RUN.format(sender=kind, seconds=arguments.seconds, load=arguments.load), flush=True)
        errors, missing = measure(kind=kind, port=arguments.port, seconds=arguments.seconds, load=arguments.load)
        report(kind=kind, errors=errors, missing=missing)


if __name__ == '__main__':
    main()
