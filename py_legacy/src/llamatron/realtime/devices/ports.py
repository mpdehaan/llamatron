# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The MIDI output ports this computer has: found once, and watched only while a port that is coming, such as FluidSynth's, is
awaited; and whether python-rtmidi, which lists them where CoreMIDI does not, is installed."""

import importlib
import importlib.util
import queue
import threading

from llamatron.user_strings import errors

# The library that lists the ports where CoreMIDI does not.
RTMIDI_MODULE = 'rtmidi'

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
    from llamatron.realtime.sender_process.process import coremidi
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

