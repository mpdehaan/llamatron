# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The ports the engine sends through: a real one over python-rtmidi, and one that records what it was given and when, for the tests and the timing report."""

import time

from llamatron.realtime.devices.ports import midi_library
from llamatron.user_strings import errors



class MidiOutput:
    """What the engine needs of a port: send bytes, and close."""

    __slots__ = ()

    def send(self, data):
        raise NotImplementedError

    def set_sound(self, *, channel, spec):
        """Do nothing: only a built-in port has sounds to set (synth_output.py)."""

    def close(self):
        raise NotImplementedError


class ScheduledOutput(MidiOutput):
    """A port that also takes an event ahead of time, to be sent at a reading of time.perf_counter, and takes back every event it
    holds whose moment has not come."""

    __slots__ = ()

    def send_at(self, *, data, at):
        raise NotImplementedError

    def flush(self):
        raise NotImplementedError


class RtMidiOutput(MidiOutput):
    """A port of the computer's, opened by name through python-rtmidi, which is imported only here and only when a port is opened."""

    __slots__ = ('_port',)

    def __init__(self, *, name):
        rtmidi = midi_library()
        self._port = rtmidi.MidiOut()
        names = self._port.get_ports()
        for place, port_name in enumerate(names):
            if port_name == name or port_name.startswith(name):
                self._port.open_port(place)
                return
        raise ValueError(errors.ERR_NO_SUCH_MIDI_PORT.format(name=name))

    def send(self, data):
        self._port.send_message(data)

    def close(self):
        self._port.close_port()


class RecordingOutput(MidiOutput):
    """A port that keeps every message with the clock's reading when it was sent, so that a test or the timing report can see what went out and when."""

    __slots__ = ('sent',)

    def __init__(self):
        self.sent = []

    def send(self, data):
        self.sent.append((time.perf_counter(), list(data)))

    def close(self):
        pass


class ScheduledRecordingOutput(ScheduledOutput):
    """A scheduled port that keeps every message with the clock's reading it was to be sent at, and forgets on a flush what was still
    to come by the clock it is given, as CoreMIDI does, so that a test or the recording sender sees what would have gone out."""

    __slots__ = ('sent', '_clock')

    def __init__(self, *, clock):
        self.sent = []
        self._clock = clock

    def send(self, data):
        self.sent.append((self._clock.now(), list(data)))

    def send_at(self, *, data, at):
        self.sent.append((max(at, self._clock.now()), list(data)))

    def flush(self):
        now = self._clock.now()
        self.sent = [item for item in self.sent if item[0] <= now]

    def delivered(self):
        """Return every message whose moment has come, in the order of their moments."""
        now = self._clock.now()
        return sorted((item for item in self.sent if item[0] <= now), key=sent_moment)

    def close(self):
        self.sent = self.delivered()


def sent_moment(item):
    """Return the moment a recorded message was sent at."""
    return item[0]

