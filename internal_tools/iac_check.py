#!/usr/bin/env python3
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

"""Play a scale run out of a real MIDI port, an IAC bus, through the Realtime Sender Process, saying each message as it goes, and read it back.

Run from the top folder, on a Mac with an IAC bus turned on in Audio MIDI Setup:

    .venv/bin/python internal_tools/iac_check.py                                   # a C major scale up and down, one note a beat, on channel 1
    .venv/bin/python internal_tools/iac_check.py examples/by_genre/electronic/minimal_techno.yml --seconds 20   # the first seconds of a set instead
    internal_tools/iac_check.sh                                                        # the same as the first

This is the one tool that touches real MIDI hardware, by the user's leave of 2026-11-10, and it only ever
opens a port whose name holds "IAC": the macOS IAC driver, a bus from one program to another on the same
computer, which no instrument hangs off. Every track goes down channel 1. The suite never runs it, and it
is not part of setting real-time playback up: it is for hearing, in whatever listens on the bus, and for
proving on a real port what test/test_realtime.py proves on recording outputs. With no set named it builds
one in memory, a new set whose starter pattern is made a scale run, so that what should be heard is plain.
As each message's time comes the tool prints it, the device, the channel as people number it and the note,
so that what the listener should be hearing at that moment is on the screen. An IAC bus hands back what is
sent to it, so the tool opens the same bus as an input too, through python-rtmidi, and reports what came
back: how many of the events sent arrived, in order, and how late each was against its scheduled second,
the clock being shared with the process, as the least, the mean, the most and the standard deviation. At
the end the process silences the channel as the tracker does on stop, and the tool checks the silencing
arrived. Anything else that was on the bus, from another program sending to it, is listed, the first ten
messages decoded, since another sender makes the order and the times meaningless.

docs/MIDI_SETUP.md says how to set the bus up and how to read this tool's report.
"""

import argparse
import statistics
import sys
import threading
import time

from llamatron.composition.file_format import Row
from llamatron.composition.setlist import Setlist
from llamatron.music.midi import HALF_STEPS_PER_OCTAVE
from llamatron.music.note import SHARP_NAMES
from llamatron.playback.song_renderer import SongRenderer
from llamatron.realtime.engine import ALL_NOTES_OFF, ALL_SOUND_OFF
from llamatron.realtime.outputs import midi_library, output_port_names
from llamatron.realtime.sender_process import RealtimeMIDISenderProcess
from llamatron.realtime.timeline import CONTROL_CHANGE, NOTE_OFF, NOTE_ON, Route, song_timeline

DEFAULT_SECONDS = 10.0
# The scale run: the degrees of one octave up and back down, a note a beat, in the new set's C major.
SCALE_RUN_DEGREES = [1, 2, 3, 4, 5, 6, 7, 8, 7, 6, 5, 4, 3, 2, 1]
SCALE_RUN_STEPS = 16
# A quarter note, so that a note a step is a note a beat.
SCALE_RUN_STEP_SIZE = '1/4'
# Only the IAC driver's buses, which go from one program to another on this computer, are ever opened.
ALLOWED_PORT_WORD = 'IAC'
# Channel 1 as people number it, sent as 0.
CHANNEL = 0
SEED = 1
SETTLE_SECONDS = 1.0
MILLISECONDS = 1000
PERCENTILE = 99
PERCENTILES = 100
SUCCESS = 0
FAILURE = 1

NO_PORT = 'no MIDI output port with {word} in its name: turn an IAC bus on in Audio MIDI Setup (the ports are: {ports})'
HEADING = 'sending {count} events of {path}, {seconds:.1f} s, out of ({port}) on channel {channel} through the Realtime Sender Process'
SCALE_RUN = 'a C major scale up and down, a note a beat'
EVENT_LINE = '  {seconds:6.2f} s  {device}  channel {channel:2}  {what}'
NOTE_ON_WHAT = 'note on  {note} ({number}) velocity {velocity}'
NOTE_OFF_WHAT = 'note off {note} ({number})'
CONTROL_WHAT = 'control change {number} = {value}'
OTHER_WHAT = 'bytes {data}'
NOTE_NAME = '{name}{octave}'
CHANNEL_WHAT = 'channel {channel}: {what}'
PROGRAM_WHAT = 'program change to {number}'
PITCH_BEND_WHAT = 'pitch bend'
AFTERTOUCH_WHAT = 'aftertouch'
CLOCK_WHAT = 'MIDI clock tick, which a DAW sends 24 times a beat while it plays'
ACTIVE_SENSING_WHAT = 'active sensing, a keep-alive some keyboards send'
START_STOP_WHAT = 'transport start, continue or stop'
UNKNOWN_WHAT = 'unknown'
CONTROL_NAMES = {1: 'mod wheel', 7: 'volume', 10: 'pan', 11: 'expression', 64: 'sustain pedal', ALL_SOUND_OFF: 'all sound off', ALL_NOTES_OFF: 'all notes off', 121: 'reset all controllers'}
NAMED_CONTROL_WHAT = 'control change {number} ({name}) = {value}'
PROGRAM_CHANGE = 0xC0
CHANNEL_PRESSURE = 0xD0
POLY_PRESSURE = 0xA0
PITCH_BEND = 0xE0
STATUS_MASK = 0xF0
CHANNEL_MASK = 0x0F
SYSTEM_STATUS = 0xF0
MIDI_CLOCK = 0xF8
MIDI_START = 0xFA
MIDI_CONTINUE = 0xFB
MIDI_STOP = 0xFC
ACTIVE_SENSING = 0xFE
ARRIVED = '  {arrived} of {count} events came back on the bus{order}'
OUT_OF_ORDER = ', NOT in the order sent'
OTHERS = '  {count} other messages were on the bus too, from something else sending to it, such as the tracker playing{shown}:'
OTHERS_SHOWN = ' (the first {shown})'
OTHER_LINE = '    {data}  {what}'
SHARED_BUS = '  so the order and the lateness cannot be judged this run: stop whatever else sends to the bus and run again'
MOST_OTHERS_SHOWN = 10
# Lateness a listener may hear, which is also what the suite allows the process on a loaded machine.
AUDIBLE_MS = 10.0
LATE = '  lateness against the schedule: least {least:.3f} ms, mean {mean:.3f} ms, most {most:.3f} ms, standard deviation {deviation:.3f} ms, {percentile}th percentile {high:.3f} ms'
TIMING_GOOD = '  timing: good, nothing more than {threshold:.0f} ms off'
TIMING_POOR = '  timing: {count} of {total} events more than {threshold:.0f} ms off, which a listener may hear'
SILENCED = '  the channel was silenced on close: all notes off and all sound off arrived'
NOT_SILENCED = '  the silencing on close did NOT arrive'
NOTHING_BACK = '  nothing came back: is the bus turned on in Audio MIDI Setup, and does nothing else hold its input?'
VERDICT_GOOD = 'verdict: the real port plays what the export holds'
VERDICT_BAD = 'verdict: the real port does NOT play what the export holds'
SHOWN_CHANNEL = 1


class BusReceiver:
    """The IAC bus opened as an input, keeping each message with the clock's reading when it arrived."""

    __slots__ = ('_port', '_lock', 'received')

    def __init__(self, *, name):
        rtmidi = midi_library()
        self._port = rtmidi.MidiIn()
        names = self._port.get_ports()
        self._port.open_port(names.index(name))
        self._port.ignore_types(sysex=True, timing=True, active_sense=True)
        self._lock = threading.Lock()
        self.received = []

        def arrived(event, data=None):
            """What python-rtmidi calls, positionally, on its own thread: the message and how long since the last one."""
            message, _ = event
            with self._lock:
                self.received.append((time.perf_counter(), list(message)))

        self._port.set_callback(arrived)

    def close(self):
        self._port.close_port()


def iac_port():
    """Return the first output port with the allowed word in its name, or None."""
    for name in output_port_names():
        if ALLOWED_PORT_WORD in name:
            return name
    return None


def scale_run_setlist():
    """Return a new set whose starter pattern is the scale run: one degree a step, a step a beat."""
    setlist = Setlist.new()
    pattern = setlist.get_pattern(setlist.get_pattern_names()[0])
    pattern.set_steps(SCALE_RUN_STEPS)
    pattern.set_step_size(SCALE_RUN_STEP_SIZE)
    for step in range(SCALE_RUN_STEPS):
        degree = SCALE_RUN_DEGREES[step] if step < len(SCALE_RUN_DEGREES) else None
        pattern.set_value(row=Row.DEGREE, step=step, value=degree)
    return setlist


def first_song_events(*, path, seconds):
    """Return the first seconds of the timeline of a set's first song, or of the scale run with no set named, every track on the one channel of the one port."""
    setlist = scale_run_setlist() if path is None else Setlist.read_file(path)
    song = setlist.get_song(setlist.first_song_name())
    grid = SongRenderer(song, seed=SEED).render()
    routes = {track.get_name(): Route(iac_port(), CHANNEL) for track in grid.get_columns()}
    return [event for event in song_timeline(grid=grid, routes=routes) if event.seconds < seconds]


def note_name(number):
    """Return a MIDI number as a note name in llamatron's own octaves, where C0 is 0, spelled with sharps."""
    return NOTE_NAME.format(name=SHARP_NAMES[number % HALF_STEPS_PER_OCTAVE], octave=number // HALF_STEPS_PER_OCTAVE)


def said(event):
    """Return what one event does, in words."""
    return decoded(event.data(), with_channel=False)


def decoded(data, *, with_channel=True):
    """Return what a MIDI message's bytes mean, in words, with its channel as people number it unless told not to."""
    status = data[0]
    if status >= SYSTEM_STATUS:
        if status == MIDI_CLOCK:
            return CLOCK_WHAT
        if status == ACTIVE_SENSING:
            return ACTIVE_SENSING_WHAT
        if status in (MIDI_START, MIDI_CONTINUE, MIDI_STOP):
            return START_STOP_WHAT
        return OTHER_WHAT.format(data=data)
    kind = status & STATUS_MASK
    number = data[1] if len(data) > 1 else 0
    value = data[2] if len(data) > 2 else 0
    if kind == NOTE_ON and value > 0:
        what = NOTE_ON_WHAT.format(note=note_name(number), number=number, velocity=value)
    elif kind in (NOTE_ON, NOTE_OFF):
        what = NOTE_OFF_WHAT.format(note=note_name(number), number=number)
    elif kind == CONTROL_CHANGE and number in CONTROL_NAMES:
        what = NAMED_CONTROL_WHAT.format(number=number, name=CONTROL_NAMES[number], value=value)
    elif kind == CONTROL_CHANGE:
        what = CONTROL_WHAT.format(number=number, value=value)
    elif kind == PROGRAM_CHANGE:
        what = PROGRAM_WHAT.format(number=number)
    elif kind == PITCH_BEND:
        what = PITCH_BEND_WHAT
    elif kind in (CHANNEL_PRESSURE, POLY_PRESSURE):
        what = AFTERTOUCH_WHAT
    else:
        what = UNKNOWN_WHAT
    if not with_channel:
        return what
    return CHANNEL_WHAT.format(channel=(status & CHANNEL_MASK) + SHOWN_CHANNEL, what=what)


def narrate(*, events, zero):
    """Print each event as its time comes, on the clock the process is sending by, so that the screen says what should be heard now."""
    for event in events:
        wait = (zero + event.seconds) - time.perf_counter()
        if wait > 0:
            time.sleep(wait)
        print(EVENT_LINE.format(seconds=event.seconds, device=event.port, channel=event.channel + SHOWN_CHANNEL, what=said(event)), flush=True)


def check(*, path, seconds):
    port = iac_port()
    if port is None:
        print(NO_PORT.format(word=ALLOWED_PORT_WORD, ports=', '.join(output_port_names())))
        return FAILURE
    events = first_song_events(path=path, seconds=seconds)
    length = events[-1].seconds if events else 0.0
    print(HEADING.format(count=len(events), path=SCALE_RUN if path is None else path, seconds=length, port=port, channel=SHOWN_CHANNEL))
    receiver = BusReceiver(name=port)
    sender = RealtimeMIDISenderProcess(ports=[port])
    zero = time.perf_counter()
    sender.start(at=zero)
    # As the tracker's player does, the events are scheduled from the moment after the process is up, not from the zero taken before it.
    launch = time.perf_counter() - zero
    events = [event._replace(seconds=event.seconds + launch) for event in events]
    sender.add(events)
    narrate(events=events, zero=zero)
    time.sleep(SETTLE_SECONDS)
    sender.close()
    time.sleep(SETTLE_SECONDS)
    receiver.close()
    return report(events=events, started=zero, received=receiver.received)


def silencing_on(channel):
    """Return the two messages the process sends on close to silence a channel, which are expected and not another sender's."""
    return [[CONTROL_CHANGE | channel, ALL_NOTES_OFF, 0], [CONTROL_CHANGE | channel, ALL_SOUND_OFF, 0]]


def cut_off_on_close(sent):
    """Return the note offs the process sends on close for the notes still sounding, when the seconds cut the run between a note on and its note off."""
    sounding = []
    for data in sent:
        if data[0] & STATUS_MASK == NOTE_ON:
            sounding.append(data[1])
        elif data[0] & STATUS_MASK == NOTE_OFF and data[1] in sounding:
            sounding.remove(data[1])
    return [[NOTE_OFF | CHANNEL, number, 0] for number in sounding]


def sort_out(*, sent, received):
    """Return the received messages that are the sent ones, in the order they arrived, and the rest, which something else put on the bus: each sent message, each note off the close sends and each silencing message is matched to the first arrival of it not yet matched."""
    waiting = list(sent) + cut_off_on_close(sent) + silencing_on(CHANNEL)
    ours = []
    others = []
    for at, data in received:
        if data in waiting:
            waiting.remove(data)
            ours.append((at, data))
        else:
            others.append(data)
    return ours, others


def report(*, events, started, received):
    if not received:
        print(NOTHING_BACK)
        print(VERDICT_BAD)
        return FAILURE
    sent = [event.data() for event in events]
    ours, others = sort_out(sent=sent, received=received)
    arrived = [data for _, data in ours]
    in_order = arrived[:len(sent)] == sent
    matched = sum(1 for data in sent if data in arrived)
    print(ARRIVED.format(arrived=matched, count=len(sent), order='' if in_order or others else OUT_OF_ORDER))
    timing_good = True
    if others:
        # Another sender's messages can be the same bytes as ours, so which arrival was ours can't be told, and the order and the times mean nothing.
        shown = others[:MOST_OTHERS_SHOWN]
        print(OTHERS.format(count=len(others), shown=OTHERS_SHOWN.format(shown=len(shown)) if len(others) > len(shown) else ''))
        for data in shown:
            print(OTHER_LINE.format(data=data, what=decoded(data)))
        print(SHARED_BUS)
    elif in_order:
        lateness = [((at - started) - event.seconds) * MILLISECONDS for event, (at, _) in zip(events, ours)]
        if len(lateness) >= 2:
            high = statistics.quantiles(lateness, n=PERCENTILES)[PERCENTILE - 1]
            print(LATE.format(least=min(lateness), mean=statistics.fmean(lateness), most=max(lateness), deviation=statistics.stdev(lateness), percentile=PERCENTILE, high=high))
            audible = [value for value in lateness if abs(value) > AUDIBLE_MS]
            timing_good = not audible
            print(TIMING_GOOD.format(threshold=AUDIBLE_MS) if timing_good else TIMING_POOR.format(count=len(audible), total=len(lateness), threshold=AUDIBLE_MS))
    silenced = all(message in arrived for message in silencing_on(CHANNEL))
    print(SILENCED if silenced else NOT_SILENCED)
    good = (in_order or bool(others)) and matched == len(sent) and silenced and timing_good
    print(VERDICT_GOOD if good else VERDICT_BAD)
    return SUCCESS if good else FAILURE


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('path', nargs='?', default=None, help='a set to play the first seconds of, in place of the scale run')
    parser.add_argument('--seconds', type=float, default=DEFAULT_SECONDS, help='play only the first seconds')
    arguments = parser.parse_args(argv)
    return check(path=arguments.path, seconds=arguments.seconds)


if __name__ == '__main__':
    sys.exit(main())
