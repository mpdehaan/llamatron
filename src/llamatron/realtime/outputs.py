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

"""The ports the engine sends through: a real one over python-rtmidi, and one that records what it was given and when, for the tests and the timing report."""

import importlib.util
import time

from llamatron.strings.errors import ERR_NO_MIDI_LIBRARY, ERR_NO_SUCH_MIDI_PORT

RTMIDI_MODULE = 'rtmidi'


class MidiOutput:
    """What the engine needs of a port: send bytes, and close."""

    __slots__ = ()

    def send(self, data):
        raise NotImplementedError

    def close(self):
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
        raise ValueError(ERR_NO_SUCH_MIDI_PORT.format(name=name))

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


def has_midi_library():
    """Return whether python-rtmidi is installed, without importing it."""
    return importlib.util.find_spec(RTMIDI_MODULE) is not None


def midi_library():
    """Return the rtmidi module, or raise ImportError in the program's words when it isn't installed."""
    if not has_midi_library():
        raise ImportError(ERR_NO_MIDI_LIBRARY)
    import rtmidi
    return rtmidi


def output_port_names():
    """Return the names of the computer's MIDI output ports, and an empty list when there are none or no library."""
    if not has_midi_library():
        return []
    return list(midi_library().MidiOut().get_ports())
