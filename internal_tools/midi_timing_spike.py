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

"""Measure how tightly Python can send a song's MIDI in real time, before real-time playback is built into the tracker.

Run from the top folder, with python-rtmidi installed in the virtual environment:

    .venv/bin/python internal_tools/midi_timing_spike.py                                   # minimal_techno's first 20 seconds, sent from a separate process
    .venv/bin/python internal_tools/midi_timing_spike.py examples/learning/11_ode_to_joy_ratchet.yml --seconds 30
    .venv/bin/python internal_tools/midi_timing_spike.py --sender thread                   # the same from a thread in this process, the baseline
    .venv/bin/python internal_tools/midi_timing_spike.py --sender thread --busy            # while this process renders the song over and over, as the tracker draws
    .venv/bin/python internal_tools/midi_timing_spike.py --port "IAC Driver Bus 1"         # send to a real port as well, to hear it

The spike renders the set's first song the way the exporters do, turns the grid into one time-ordered list of note
events with absolute times in seconds, and hands the list to a sender, which plays it into a MIDI port. The receiver is
a virtual input port opened in a process of its own, which records when each message arrives. The report compares the spacing of
what arrived with the spacing that was scheduled, so no clock has to be shared between the two processes, and says how
many events were late or early by more than a millisecond, five and ten. A few milliseconds is inaudible, and tens of
milliseconds starts to be heard on drums. Nothing here touches the tracker or the exports: it answers one question, which
of the senders in dev_notes/IDEAS.md ("Previewing with real-time MIDI") is tight enough, and it is kept so that the answer can be
checked again on another computer.
"""

import argparse
import importlib.util
import multiprocessing
import statistics
import sys
import threading
import time

from llamatron.composition.setlist import Setlist
from llamatron.exporters.timing import timed_events
from llamatron.playback.song_renderer import SongRenderer

DEFAULT_EXAMPLE = 'examples/by_genre/electronic/minimal_techno.yml'
DEFAULT_SECONDS = 20.0
# The seed every spike uses, so that the same notes are sent each time.
SEED = 1
RECEIVER_PORT_NAME = 'llamatron timing spike'
RTMIDI_MODULE = 'rtmidi'
SPAWN = 'spawn'
SENDER_PROCESS = 'process'
SENDER_THREAD = 'thread'
SENDERS = (SENDER_PROCESS, SENDER_THREAD)
# A quarter note per beat, which is what a tempo counts, and the seconds in a minute.
QUARTERS_PER_WHOLE = 4
SECONDS_PER_MINUTE = 60
MIDI_CHANNELS = 16
NOTE_ON = 0x90
NOTE_OFF = 0x80
CONTROL_CHANGE = 0xB0
ALL_SOUND_OFF = 120
ALL_NOTES_OFF = 123
# How long before an event's time the sender stops sleeping and spins, and how long it sleeps at a time until then.
SPIN_SECONDS = 0.0015
SLEEP_SLICE_SECONDS = 0.0005
# How long the receiver waits after the last event should have arrived, and after sending for the port to appear.
SETTLE_SECONDS = 0.5
PORT_WAIT_SECONDS = 0.5
MILLISECONDS = 1000
THRESHOLDS_MS = (1, 5, 10)
# The percentile of the deviations that the report shows beside the largest.
PERCENTILE = 99
PERCENTILES = 100

HEADING = 'sent {count} events of {path} over {seconds:.1f} s from a {sender}{busy}, received {received}'
BUSY_NOTE = ' while the process rendered'
LINE = '  deviation from the scheduled spacing: mean {mean:.2f} ms, {percentile}th percentile {high:.2f} ms, worst {worst:.2f} ms'
OVER = '  events more than {threshold} ms off: {count} ({share:.1f}%)'
VERDICT_TIGHT = '  verdict: tight (nothing over {threshold} ms, which nobody can hear)'
VERDICT_LOOSE = '  verdict: loose (events over {threshold} ms off would be heard on drums)'
MISSING = 'the receiver got {received} events but {count} were sent'
NO_RTMIDI = 'python-rtmidi is not installed: .venv/bin/python -m pip install python-rtmidi'
NO_PORT = 'no MIDI output port called ({name}); the ports are: {names}'


class Event:
    """One MIDI message to send at a time, in seconds from the start."""

    __slots__ = ('seconds', 'data')

    def __init__(self, *, seconds, data):
        self.seconds = seconds
        self.data = data


def seconds_per_whole(tempo):
    """Return how long a whole note lasts at a tempo in quarter notes per minute."""
    return QUARTERS_PER_WHOLE * SECONDS_PER_MINUTE / tempo


def song_events(*, path, seconds):
    """Return the first song's notes as events with absolute times, the scenes laid end to end as the MIDI export lays them, up to a number of seconds."""
    setlist = Setlist.read_file(path)
    song = setlist.get_song(setlist.first_song_name())
    grid = SongRenderer(song, seed=SEED).render()
    events = []
    scene_start = 0.0
    for scene in grid.get_rows():
        whole = seconds_per_whole(grid.tempo_at(scene))
        for number, track in enumerate(grid.get_columns()):
            clip = grid.get_clip(row=scene, column=track)
            if clip is None or track.get_mute():
                continue
            channel = number % MIDI_CHANNELS
            notes, clip_length = timed_events(clip=clip, scale=grid.scale_at(row=scene, column=track))
            for note in notes:
                start = scene_start + float(note.start) * whole
                end = scene_start + float(note.end) * whole
                if start >= seconds:
                    continue
                events.append(Event(seconds=start, data=[NOTE_ON | channel, note.midi_number, note.velocity]))
                events.append(Event(seconds=min(end, seconds), data=[NOTE_OFF | channel, note.midi_number, 0]))
        scene_start += float(grid.row_length(scene)) * whole
        if scene_start >= seconds:
            break
    # Note offs before note ons at the same moment, so that a repeated pitch is never cut by its own predecessor's off.
    events.sort(key=lambda event: (event.seconds, event.data[0] & 0xF0 != NOTE_OFF))
    return events


def keep_busy(*, path, stop):
    """Render the set's first song again and again until told to stop, holding the interpreter's lock the way the tracker's drawing does."""
    setlist = Setlist.read_file(path)
    song = setlist.get_song(setlist.first_song_name())
    while not stop.is_set():
        SongRenderer(song, seed=SEED).render()


def silence(*, channels):
    """Return the messages that silence every channel that was used: all notes off, then all sound off."""
    return [[CONTROL_CHANGE | channel, number, 0] for channel in sorted(channels) for number in (ALL_NOTES_OFF, ALL_SOUND_OFF)]


def open_output(name):
    """Return an rtmidi output opened on the port of that name, or raise if there is none."""
    import rtmidi
    out = rtmidi.MidiOut()
    names = out.get_ports()
    for place, port_name in enumerate(names):
        if port_name == name or port_name.startswith(name):
            out.open_port(place)
            return out
    raise SystemExit(NO_PORT.format(name=name, names=', '.join(names)))


def send_all(*, port_names, scheduled):
    """Send every (seconds, bytes) pair at its time to every named port, sleeping until just before each and then spinning, and silence the channels at the end."""
    outs = [open_output(name) for name in port_names]
    channels = {data[0] & 0x0F for _, data in scheduled}
    start = time.perf_counter()
    for seconds, data in scheduled:
        due = start + seconds
        while True:
            left = due - time.perf_counter()
            if left <= 0:
                break
            if left > SPIN_SECONDS:
                time.sleep(min(left - SPIN_SECONDS, SLEEP_SLICE_SECONDS))
        for out in outs:
            out.send_message(data)
    for data in silence(channels=channels):
        for out in outs:
            out.send_message(data)
    for out in outs:
        out.close_port()


def receive(*, ready, done, results):
    """Open the virtual input port in a process of its own, so that nothing this program does can delay the timestamps, and send the arrivals back when told."""
    import rtmidi
    port = rtmidi.MidiIn()
    port.open_virtual_port(RECEIVER_PORT_NAME)
    arrivals = []

    def arrived(event, data=None):
        message, _ = event
        arrivals.append((time.perf_counter(), list(message)))
    port.set_callback(arrived)
    ready.set()
    done.wait()
    port.close_port()
    # The silencing messages at the end are not scheduled events.
    results.put([(at, message) for at, message in arrivals if message[0] & 0xF0 != CONTROL_CHANGE])


def deviations_ms(*, scheduled, arrivals):
    """Return how far each arrival's spacing from the first arrival was from the scheduled spacing, in milliseconds, signed, late positive."""
    first_due = scheduled[0][0]
    first_at = arrivals[0][0]
    return [((at - first_at) - (due - first_due)) * MILLISECONDS for (due, _), (at, _) in zip(scheduled, arrivals)]


def report(*, path, sender, busy, seconds, scheduled, arrivals):
    print(HEADING.format(count=len(scheduled), path=path, seconds=seconds, sender=sender, busy=BUSY_NOTE if busy else '', received=len(arrivals)))
    if len(arrivals) != len(scheduled):
        print(MISSING.format(received=len(arrivals), count=len(scheduled)))
    pairs = min(len(arrivals), len(scheduled))
    if pairs < 2:
        return
    offsets = [abs(value) for value in deviations_ms(scheduled=scheduled[:pairs], arrivals=arrivals[:pairs])]
    high = statistics.quantiles(offsets, n=PERCENTILES)[PERCENTILE - 1] if len(offsets) > 1 else offsets[0]
    print(LINE.format(mean=statistics.fmean(offsets), percentile=PERCENTILE, high=high, worst=max(offsets)))
    for threshold in THRESHOLDS_MS:
        over = sum(1 for value in offsets if value > threshold)
        print(OVER.format(threshold=threshold, count=over, share=over * 100 / len(offsets)))
    loose = THRESHOLDS_MS[1]
    if max(offsets) <= loose:
        print(VERDICT_TIGHT.format(threshold=loose))
    else:
        print(VERDICT_LOOSE.format(threshold=loose))


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('path', nargs='?', default=DEFAULT_EXAMPLE)
    parser.add_argument('--seconds', type=float, default=DEFAULT_SECONDS)
    parser.add_argument('--sender', choices=SENDERS, default=SENDER_PROCESS)
    parser.add_argument('--port', default=None, help='a real output port to send to as well, to hear it')
    parser.add_argument('--busy', action='store_true', help='keep this process busy rendering the song meanwhile, which is what the tracker does to a thread')
    arguments = parser.parse_args(argv)
    if importlib.util.find_spec(RTMIDI_MODULE) is None:
        raise SystemExit(NO_RTMIDI)
    events = song_events(path=arguments.path, seconds=arguments.seconds)
    scheduled = [(event.seconds, event.data) for event in events]
    context = multiprocessing.get_context(SPAWN)
    ready = context.Event()
    done = context.Event()
    results = context.Queue()
    receiver = context.Process(target=receive, kwargs={'ready': ready, 'done': done, 'results': results})
    receiver.start()
    ready.wait()
    time.sleep(PORT_WAIT_SECONDS)
    port_names = [RECEIVER_PORT_NAME] + ([arguments.port] if arguments.port else [])
    if arguments.sender == SENDER_PROCESS:
        worker = context.Process(target=send_all, kwargs={'port_names': port_names, 'scheduled': scheduled})
    else:
        worker = threading.Thread(target=send_all, kwargs={'port_names': port_names, 'scheduled': scheduled})
    stop_busy = threading.Event()
    busy = threading.Thread(target=keep_busy, kwargs={'path': arguments.path, 'stop': stop_busy}) if arguments.busy else None
    worker.start()
    if busy:
        busy.start()
    worker.join()
    stop_busy.set()
    if busy:
        busy.join()
    time.sleep(SETTLE_SECONDS)
    done.set()
    arrivals = results.get()
    receiver.join()
    report(path=arguments.path, sender=arguments.sender, busy=arguments.busy, seconds=arguments.seconds, scheduled=scheduled, arrivals=arrivals)
    return 0


if __name__ == '__main__':
    sys.exit(main())
