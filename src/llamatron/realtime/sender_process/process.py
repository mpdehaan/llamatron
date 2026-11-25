# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Realtime Sender Process: the playback engine run in a process of its own, so that the tracker's drawing never delays a note.

A thread in the tracker's process drifts by up to five milliseconds, the interpreter's switch interval, while the
screen draws; a separate process measured within a tenth of a millisecond (internal_tools/midi_timing_spike.py). The tracker
keeps a RealtimeMIDISenderProcess and talks to it in a few messages over a pipe: start, add events, forget a clip's
events from a time, stop a clip, stop everything, close. The process sleeps in short slices until just before the
next event is due and then spins on the clock, since sleep alone is loose on macOS, and polls the pipe between.

Two drivers send, chosen once as the process starts. On macOS the timestamped driver hands each event to CoreMIDI a tenth of a
second ahead, stamped with its moment (realtime/sender_process/coremidi.py, realtime/sender_process/scheduled_engine.py), so that the system delivers it on time
however late the process wakes, and the process sleeps until the next event is to be handed rather than spinning. Elsewhere the
immediate driver sends each event as its moment comes, through python-rtmidi. Both are tested on the Mac.
"""

import contextlib
import ctypes
import gc
import multiprocessing
import struct
import sys
import time
from typing import NamedTuple

from llamatron.realtime import realtime_names
from llamatron.realtime.render_process import timeline
from llamatron.realtime.sender_process import coremidi
from llamatron.realtime.sender_process.coremidi import CoreMidiOutput
from llamatron.realtime.sender_process.engine import MonotonicClock, PlaybackEngine
from llamatron.realtime.sender_process.outputs import RecordingOutput, RtMidiOutput, ScheduledRecordingOutput
from llamatron.realtime.sender_process.scheduled_engine import ScheduledPlaybackEngine
from llamatron.realtime.sender_process.synth_output import SynthOutput
from llamatron.realtime.synth_process import daemon as synth_daemon
from llamatron.realtime.synth_process.daemon import SynthDaemon
from llamatron.realtime.synth_process.process import SynthesisNotStarted, SynthesisProcess
from llamatron.user_strings import errors

SPAWN = 'spawn'
# The two ways of sending: each event handed to CoreMIDI ahead of time with its moment, or each sent as its moment comes.
TIMESTAMPED = 'timestamped'
IMMEDIATE = 'immediate'
# How long before an event is due the process stops sleeping and spins, and how long it sleeps at a time until then.
SPIN_SECONDS = 0.0015
SLEEP_SLICE_SECONDS = 0.0005
# The messages the tracker sends the process.
READY = 'ready'
START = 'start'
# Events crossing the pipe as slim records, which the process reads many times faster than whole events, each holding a Rational and
# a Tag, and at about a third of the size: a record's seconds, its play's tag as a number, and its port's place among the ports, its
# channel, kind, number and value. The version comes first, so that a sender of another make can tell what it is sent.
ADD_RECORDS = 'add_records'
RECORDS_VERSION = 1
RECORD = struct.Struct('<dIBBBBB')
NO_VALUE = 0
FORGET = 'forget'
STOP_TAG = 'stop_tag'
STOP_ALL = 'stop_all'
SILENCE = 'silence'
SOUNDS = 'sounds'
CLOSE = 'close'
# What the process answers in place of READY when the Synthesis Process its built-in ports need could not start, with why.
NOT_STARTED = 'not_started'
# How long the tracker waits for the process to end before ending it itself.
CLOSE_TIMEOUT_SECONDS = 2.0
# How long the process may take to import and open its ports before start gives up on it.
START_TIMEOUT_SECONDS = 10.0
# Garbage is collected only while no event is due for at least this long, a young collection at a time, and only once this many
# new objects wait, so that no collection ever stands in front of a note.
COLLECT_WHEN_FREE_SECONDS = 0.02
YOUNG_OBJECTS_TO_COLLECT = 700
YOUNGEST = 0
# macOS's most urgent quality of service for a thread, which keeps the process on the performance cores (pthread/qos.h).
DARWIN = 'darwin'
SYSTEM_LIBRARY = 'libSystem.dylib'
QOS_CLASS_USER_INTERACTIVE = 0x21


class Sent(NamedTuple):
    """One event as the process holds it once read from a record: what the engine asks of an event, and no more."""

    seconds: float
    port: str
    channel: int
    kind: int
    number: int
    value: int
    tag: int
    # What the timeline orders an event by within an instant needs only its kind, so the whole notes are not carried.
    whole: object = None

    def data(self):
        """Return the event's bytes: two for a program change, which has no value, and three for the rest."""
        if self.kind == timeline.PROGRAM_CHANGE:
            return [self.kind | self.channel, self.number]
        return [self.kind | self.channel, self.number, self.value]


def records_of(*, events, place_of_port, number_of_tag):
    """Return events as slim records, the version first, each tag and port given as numbers by the two functions."""
    records = bytearray((RECORDS_VERSION,))
    for event in events:
        records += RECORD.pack(event.seconds, number_of_tag(event.tag), place_of_port(event.port), event.channel, event.kind, event.number, event.value or NO_VALUE)
    return bytes(records)


def events_of(*, records, ports):
    """Return the events slim records hold, each port named again by its place among the ports."""
    return [Sent(seconds, ports[port], channel, kind, number, value, tag) for seconds, tag, port, channel, kind, number, value in RECORD.iter_unpack(records[1:])]


class SenderNotStarted(RuntimeError):
    """The process ended before it had opened its ports, which it does when a port cannot be opened."""


class RealtimeMIDISenderProcess:
    """The tracker's side of the sender: starts the process on the ports named, and sends it the messages above."""

    __slots__ = ('_ports', '_recording', '_driver', '_connection', '_process', '_port_places', '_tag_numbers', '_sounds')

    def __init__(self, *, ports, recording=False, driver=None):
        """ports are the names of the output ports to open. With recording, the process opens recording outputs in their place and
        hands back what it sent on close. driver is TIMESTAMPED or IMMEDIATE, by default the timestamped one where CoreMIDI is."""
        self._ports = list(ports)
        self._recording = recording
        if driver is None:
            driver = default_driver()
        self._driver = driver
        self._connection = None
        self._process = None
        self._port_places = {name: place for place, name in enumerate(self._ports)}
        # Each play's tag as the number its records carry, given the first time the tag is sent.
        self._tag_numbers = {}
        # The sound last sent for each built-in (port, channel), so that only a changed one crosses again.
        self._sounds = {}

    def start(self, *, at=None):
        """Start the process, which opens the ports, and take this moment, or a reading of the clock given, as the timeline's zero."""
        context = multiprocessing.get_context(SPAWN)
        self._connection, far_end = context.Pipe()
        self._process = context.Process(target=run_sender, kwargs=dict(connection=far_end, ports=self._ports, recording=self._recording, driver=self._driver))
        with real_standard_error():
            self._process.start()
        # Wait until the process has opened its ports, so that the first event is not sent late while it starts up, which measured about 150 ms on the IAC bus.
        answer = self._answer_to_starting()
        if answer != READY:
            self.close()
            reason = errors.ERR_SENDER_DID_NOT_START
            if isinstance(answer, tuple) and answer[0] == NOT_STARTED:
                reason = answer[1]
            raise SenderNotStarted(reason)
        self._connection.send((START, at))

    def _answer_to_starting(self):
        """Return what the process answered as it started, or None when it ended or said nothing in time."""
        try:
            if self._connection.poll(START_TIMEOUT_SECONDS):
                return self._connection.recv()
        except (EOFError, OSError):
            return None
        return None

    def add(self, events):
        self._connection.send((ADD_RECORDS, records_of(events=events, place_of_port=self._port_places.__getitem__, number_of_tag=self.tag_number)))

    def forget(self, *, tag, after):
        self._connection.send((FORGET, self.tag_number(tag), after))

    def stop_tag(self, tag):
        self._connection.send((STOP_TAG, self.tag_number(tag)))

    def tag_number(self, tag):
        """Return the number a play's tag crosses the pipe as."""
        number = self._tag_numbers.get(tag)
        if number is None:
            number = len(self._tag_numbers)
            self._tag_numbers[tag] = number
        return number

    def stop_all(self):
        self._connection.send((STOP_ALL,))

    def set_sounds(self, sounds):
        """Give the built-in ports' channels their sounds, a mapping of (port, channel) to the sound, sending only what changed."""
        changed = []
        for (port, channel), spec in sounds.items():
            if self._sounds.get((port, channel)) != spec and port in self._port_places:
                self._sounds[(port, channel)] = spec
                changed.append((self._port_places[port], channel, spec))
        if changed:
            self._connection.send((SOUNDS, changed))

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


def default_driver():
    """Return the driver that sends best here: the timestamped one where CoreMIDI is, on macOS, and the immediate one elsewhere."""
    if coremidi.is_available():
        return TIMESTAMPED
    return IMMEDIATE


def engine_for(*, driver, ports, recording, synthesis=None):
    """Return the engine a driver sends through, on the real clock, with its outputs opened: recording ones with recording,
    and a built-in port's through the Synthesis Process given."""
    clock = MonotonicClock()
    if driver == TIMESTAMPED:
        outputs = {}
        for name in ports:
            if recording:
                outputs[name] = ScheduledRecordingOutput(clock=clock)
            elif is_built_in_port(name):
                outputs[name] = SynthOutput(synthesis=synthesis, group=built_in_group(name))
            else:
                outputs[name] = CoreMidiOutput(name=name)
        return ScheduledPlaybackEngine(clock=clock, outputs=outputs)
    outputs = {}
    for name in ports:
        if recording:
            outputs[name] = RecordingOutput()
        elif is_built_in_port(name):
            outputs[name] = SynthOutput(synthesis=synthesis, group=built_in_group(name))
        else:
            outputs[name] = RtMidiOutput(name=name)
    return PlaybackEngine(clock=clock, outputs=outputs)


def is_built_in_port(name):
    """Return whether a port is a built-in one, whose notes go to the Synthesis Process."""
    return name.startswith(realtime_names.BUILT_IN_PORT_PREFIX)


def built_in_group(name):
    """Return which sixteen built-in instruments a built-in port carries, from the number its name ends with."""
    return int(name.rsplit(' ', 1)[-1])


def started_synthesis(*, ports, recording):
    """Return the Synthesis Process the built-in ports among the ports play through, started, or None where there are none
    or the sender records; raise SynthesisNotStarted with why it could not start."""
    if recording or not any(is_built_in_port(name) for name in ports):
        return None
    synthesis = SynthesisProcess()
    if synth_daemon.uses_daemon():
        synthesis = SynthDaemon()
    synthesis.start()
    return synthesis


@contextlib.contextmanager
def real_standard_error():
    """Put the interpreter's own standard error back while a process is spawned, since spawn's resource tracker passes sys.stderr's file descriptor to its child and Textual's capture, in place while the tracker runs, answers -1 for it, which failed the spawn with "bad value(s) in fds_to_keep"."""
    captured = sys.stderr
    sys.stderr = sys.__stderr__
    try:
        yield
    finally:
        sys.stderr = captured


def _add_records(*, engine, message, ports):
    engine.add(events_of(records=message[1], ports=ports))


def _forget(*, engine, message):
    engine.forget(tag=message[1], after=message[2])


def _stop_tag(*, engine, message):
    engine.stop_tag(message[1])


def _stop_all(*, engine, message):
    engine.stop_all()


def _silence(*, engine, message):
    engine.silence(channels=message[1])


def _set_sounds(*, engine, message, ports):
    engine.set_sounds({(ports[place], channel): spec for place, channel, spec in message[1]})


# The messages that only hand the engine something: each kind, and what passes it on.
FORWARDED = {FORGET: _forget, STOP_TAG: _stop_tag, STOP_ALL: _stop_all, SILENCE: _silence}


def hold_garbage_back():
    """Freeze every object the process has made so far, its imports and its ports, so that no collection walks them again, and
    stop Python collecting on its own: the sending loop collects young objects only while no note is due soon."""
    gc.collect()
    gc.freeze()
    gc.disable()


def ask_to_be_urgent():
    """Ask macOS to run the process at its most urgent quality of service, which keeps it on the performance cores under load.
    Asked once as the process starts; elsewhere, and where the call fails, the process runs as it was."""
    if sys.platform != DARWIN:
        return
    try:
        ctypes.CDLL(SYSTEM_LIBRARY).pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0)
    except (OSError, AttributeError):
        return


def run_sender(*, connection, ports, recording, driver):
    """The process: an engine on the real clock, fed by the pipe, sending each event when its time comes."""
    try:
        synthesis = started_synthesis(ports=ports, recording=recording)
    except SynthesisNotStarted as problem:
        connection.send((NOT_STARTED, str(problem)))
        return
    # Every port's timeline starts the Synthesis Process's delay later, so that MIDI waits for built-in sound (synth_output.py).
    delay = 0.0
    if synthesis is not None:
        delay = synthesis.delay
    try:
        engine = engine_for(driver=driver, ports=ports, recording=recording, synthesis=synthesis)
    except Exception:  # noqa: BLE001, the process boundary: a port that cannot be opened, for whatever reason the library gives, ends the process quietly, and the tracker's side raises SenderNotStarted when the pipe closes without READY, rather than a traceback written over the tracker's screen.
        return
    hold_garbage_back()
    ask_to_be_urgent()
    connection.send(READY)
    started = None
    while True:
        due = engine.next_action()
        if due is None or not engine.is_started():
            wait = None
        elif not engine.spins():
            # The timestamped driver needs no precision of its own: it wakes to hand what comes into the horizon, and the pipe's poll
            # wakes it sooner for a message.
            wait = due - engine.elapsed()
            if wait <= 0:
                engine.send_due()
                continue
        else:
            left = due - engine.elapsed()
            if left <= SPIN_SECONDS:
                while engine.elapsed() < due:
                    pass
                engine.send_due()
                continue
            wait = min(left - SPIN_SECONDS, SLEEP_SLICE_SECONDS)
        if (wait is None or wait >= COLLECT_WHEN_FREE_SECONDS) and gc.get_count()[YOUNGEST] >= YOUNG_OBJECTS_TO_COLLECT:
            gc.collect(YOUNGEST)
        try:
            if not connection.poll(wait):
                continue
            message = connection.recv()
        except (EOFError, OSError):
            # The tracker's end of the pipe is gone, as when the tracker dies: every note still sounding is stopped before the
            # process ends, so that nothing is left stuck on a synthesizer.
            engine.close()
            return
        kind = message[0]
        if kind == START:
            started = message[1]
            if started is None:
                started = time.perf_counter()
            engine.start(at=started + delay)
        elif kind == ADD_RECORDS:
            _add_records(engine=engine, message=message, ports=ports)
        elif kind == SOUNDS:
            _set_sounds(engine=engine, message=message, ports=ports)
        elif kind in FORWARDED:
            FORWARDED[kind](engine=engine, message=message)
        elif kind == CLOSE:
            engine.close()
            sent = None
            if recording:
                sent = engine.recordings()
            connection.send((started, sent))
            return
