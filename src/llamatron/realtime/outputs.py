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
import queue
import threading
import time

from llamatron.strings import errors

RTMIDI_MODULE = 'rtmidi'


class MidiOutput:
    """What the engine needs of a port: send bytes, and close."""

    __slots__ = ()

    def send(self, data):
        raise NotImplementedError

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


def has_midi_library():
    """Return whether python-rtmidi is installed, without importing it."""
    return importlib.util.find_spec(RTMIDI_MODULE) is not None


def midi_library():
    """Return the rtmidi module, or raise ImportError in the program's words when it isn't installed."""
    if not has_midi_library():
        raise ImportError(errors.ERR_NO_MIDI_LIBRARY)
    import rtmidi
    return rtmidi


class PortWatcher:
    """Lists the computer's MIDI output ports once, as llamatron starts, and again only when asked, as while FluidSynth's port is
    awaited: a device connected later is used after a restart. Every listing goes through a thread of its own that lives as long
    as the process, the first in the process to make a MIDI client, since CoreMIDI tells only the thread that made a process's
    first client of ports other programs make later, as FluidSynth's is: a client of any other thread, the main one included, never
    saw them. On macOS the thread lists through CoreMIDI (coremidi.destination_names), which answers a refused client with an
    error; python-rtmidi, which lists elsewhere, ends the whole process when CoreMIDI refuses its client under load."""

    __slots__ = ('_asks', '_answers', '_lock', '_thread', '_listing', '_names')

    def __init__(self, *, listing=None):
        """listing returns the port names when called on the thread, by default CoreMIDI's on macOS and python-rtmidi's elsewhere."""
        self._asks = queue.Queue()
        self._answers = queue.Queue()
        self._lock = threading.Lock()
        self._thread = None
        self._listing = listing
        self._names = None

    def names(self):
        """Return the names of the MIDI output ports as first listed, an empty list when there were none or no way to list them."""
        if self._names is None:
            return self.names_now()
        return list(self._names)

    def names_now(self):
        """List the MIDI output ports again, keep the listing for names(), and return it."""
        with self._lock:
            if self._thread is None:
                self._thread = threading.Thread(target=self._serve, daemon=True)
                self._thread.start()
            self._asks.put(True)
            self._names = self._answers.get()
        return list(self._names)

    def _serve(self):
        listing = self._listing or default_listing()
        while True:
            self._asks.get()
            try:
                names = list(listing())
            except Exception:  # noqa: BLE001, the MIDI library can fail in any way; the thread lives on and answers no ports, so that no caller waits for ever.
                names = []
            self._answers.put(names)


def default_listing():
    """Return what lists the ports here: CoreMIDI's names on macOS, python-rtmidi's elsewhere, and nothing without either."""
    # Imported here, since the CoreMIDI port is a ScheduledOutput of this module.
    from llamatron.realtime import coremidi
    if coremidi.is_available():
        return coremidi.destination_names
    if has_midi_library():
        return rtmidi_names
    return list


def rtmidi_names():
    """Return the port names python-rtmidi lists, through a fresh client."""
    return midi_library().MidiOut().get_ports()


# The one watcher of the process's MIDI ports, whose thread every listing goes through.
PORTS = PortWatcher()


def output_port_names():
    """Return the names of the computer's MIDI output ports as llamatron first listed them, and an empty list when there were none
    or no way to list them (PortWatcher)."""
    return PORTS.names()


def output_port_names_now():
    """List the computer's MIDI output ports again, as FluidSynth's port is awaited, and return their names (PortWatcher)."""
    return PORTS.names_now()
