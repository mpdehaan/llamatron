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

"""The playback engine: holds the events still to send, sends each when its time comes, and knows which notes are sounding so that stopping anything silences it.

The engine reads a clock and writes to outputs, and nothing else, so that a test drives it with a SteppedClock and
RecordingOutputs and no time passes, while the Realtime Sender Process drives it with the real clock and real ports.
Every event is tagged with its scene and track, so that one clip's events can be dropped from a time on, which is how
an edit while playing replaces the passes that have not started, or stopped, with note offs for its sounding notes.
"""

import heapq
import time

from llamatron.music.midi import MAX_MIDI_NUMBER, MIN_MIDI_NUMBER
from llamatron.realtime.timeline import CONTROL_CHANGE, NOTE_OFF, NOTE_ON, NO_VELOCITY, sort_key

# The two controls that silence a channel, sent in this order when anything stops: all notes off, then all sound off, since the user has hardware that gets stuck.
ALL_NOTES_OFF = 123
ALL_SOUND_OFF = 120
SILENCING_CONTROLS = (ALL_NOTES_OFF, ALL_SOUND_OFF)
CONTROL_OFF_VALUE = 0
# Earlier than any event, so that dropping from here forgets a tag's every queued event.
BEFORE_EVERYTHING = float('-inf')


class Clock:
    """What the engine asks the time of."""

    __slots__ = ()

    def now(self):
        raise NotImplementedError


class MonotonicClock(Clock):
    """The computer's high-resolution clock, in seconds from an arbitrary start."""

    __slots__ = ()

    def now(self):
        return time.perf_counter()


class SteppedClock(Clock):
    """A clock a test moves by hand, so that nothing sleeps."""

    __slots__ = ('_now',)

    def __init__(self):
        self._now = 0.0

    def now(self):
        return self._now

    def advance(self, seconds):
        self._now += seconds


class PlaybackEngine:
    """Sends a timeline's events on time through named outputs, and silences what it started when told to stop."""

    __slots__ = ('_clock', '_outputs', '_pending', '_count', '_started', '_sounding', '_channels_used')

    def __init__(self, *, clock, outputs):
        """outputs maps a port's name to its MidiOutput."""
        self._clock = clock
        self._outputs = outputs
        # A heap of (seconds, order, count, event): order puts note offs first at one instant and count keeps the heap stable.
        self._pending = []
        self._count = 0
        self._started = None
        # Each sounding note, by (port, channel, number), with the tag of the event that started it.
        self._sounding = {}
        self._channels_used = set()

    def start(self, *, at=None):
        """Take this moment as the timeline's zero, or a reading of the clock given from outside, so that the tracker and the process count from one moment."""
        self._started = self._clock.now() if at is None else at

    def is_started(self):
        return self._started is not None

    def elapsed(self):
        """Return how many seconds the timeline has run."""
        return self._clock.now() - self._started

    def add(self, events):
        """Queue events, in any order, to be sent at their seconds."""
        for event in events:
            self._count += 1
            heapq.heappush(self._pending, (event.seconds, sort_key(event)[1], self._count, event))

    def pending(self):
        """Return the queued events in the order they will be sent."""
        return [item[3] for item in sorted(self._pending)]

    def next_due(self):
        """Return the seconds of the next event, or None when nothing is queued."""
        return self._pending[0][0] if self._pending else None

    def send_due(self):
        """Send every event whose time has come, and return how many were sent."""
        sent = 0
        now = self.elapsed()
        while self._pending and self._pending[0][0] <= now:
            event = heapq.heappop(self._pending)[3]
            self._send(event)
            sent += 1
        return sent

    def drop(self, *, tag, after):
        """Forget the queued events of a tag from a time on, leaving what is sounding alone."""
        self._pending = [item for item in self._pending if not (item[3].tag == tag and item[0] >= after)]
        heapq.heapify(self._pending)

    def stop_tag(self, tag):
        """Forget a tag's queued events and silence its sounding notes."""
        self.drop(tag=tag, after=BEFORE_EVERYTHING)
        for key, sounding_tag in list(self._sounding.items()):
            if sounding_tag == tag:
                self._note_off(key)

    def stop_all(self):
        """Forget every queued event, silence every sounding note, and send all notes off and all sound off on every channel used."""
        self._pending = []
        for key in list(self._sounding):
            self._note_off(key)
        for port, channel in sorted(self._channels_used):
            for number in SILENCING_CONTROLS:
                self._outputs[port].send([CONTROL_CHANGE | channel, number, CONTROL_OFF_VALUE])
        self._channels_used = set()

    def silence(self, *, channels):
        """Send a note off for every note, then all notes off and all sound off, on each (port, channel) given: the emergency stop, for a note stuck on hardware that nothing here knows is sounding."""
        for port, channel in channels:
            output = self._outputs[port]
            for number in range(MIN_MIDI_NUMBER, MAX_MIDI_NUMBER + 1):
                self._sounding.pop((port, channel, number), None)
                output.send([NOTE_OFF | channel, number, NO_VELOCITY])
            for number in SILENCING_CONTROLS:
                output.send([CONTROL_CHANGE | channel, number, CONTROL_OFF_VALUE])

    def sounding(self):
        """Return the (port, channel, number) of every note that has started and not ended."""
        return sorted(self._sounding)

    def close(self):
        """Stop everything and close the outputs."""
        self.stop_all()
        for output in self._outputs.values():
            output.close()

    def _send(self, event):
        key = (event.port, event.channel, event.number)
        if event.kind == NOTE_ON:
            self._sounding[key] = event.tag
        elif event.kind == NOTE_OFF:
            self._sounding.pop(key, None)
        self._channels_used.add((event.port, event.channel))
        self._outputs[event.port].send(event.data())

    def _note_off(self, key):
        port, channel, number = key
        self._sounding.pop(key, None)
        self._outputs[port].send([NOTE_OFF | channel, number, NO_VELOCITY])
