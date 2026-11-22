# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A MIDI port opened through CoreMIDI, macOS's MIDI system, which takes each event ahead of time stamped with the moment it should
sound and delivers it then, however late the Realtime Sender Process is woken, and which can take back what it holds.

CoreMIDI is reached through ctypes, with no library to install. The stamps are on the system's mach clock, which CoreMIDI times by;
the engine's times are readings of time.perf_counter, and the two are tied by reading both at one moment as the port opens.
Measured with internal_tools/coremidi_timing.sh under twenty busy processes for ten minutes, the latest note was 0.27 ms off,
where sending each event as it comes was 10 ms off at worst.

What the port holds is taken back by giving the port up and opening another, which drops everything the old one had scheduled, in
about a quarter of a millisecond. CoreMIDI's own MIDIFlushOutput is never called: it reaches a destination that another program
made, as FluidSynth's is, as a byte 0xFF, MIDI's system reset, which FluidSynth answers by resetting its programs and controls.
"""

import ctypes
import functools
import sys
import time

from llamatron.realtime.sender_process.outputs import ScheduledOutput
from llamatron.user_strings import errors

MACOS = 'darwin'
COREMIDI = '/System/Library/Frameworks/CoreMIDI.framework/CoreMIDI'
CORE_FOUNDATION = '/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation'
CLIENT_NAME = 'llamatron'
# Core Foundation's run loop mode for running a thread's run loop once, and the time it waits, none.
DEFAULT_RUN_LOOP_MODE = 'kCFRunLoopDefaultMode'
NO_WAIT = 0.0
# CoreMIDI's names of the properties holding a destination's own name, like Bus 1, and the name shown for it, like IAC Driver Bus 1,
# which is the name python-rtmidi lists and the set's instruments use.
NAME_PROPERTIES = ('kMIDIPropertyName', 'kMIDIPropertyDisplayName')
SHOWN_NAME = 1
UTF8 = 0x08000100
NAME_BYTES = 256
# Room for one packet of one event, with plenty to spare.
PACKET_LIST_BYTES = 256
NANOSECONDS = 1_000_000_000
NO_ERROR = 0
# The stamp that tells CoreMIDI to send at once.
NOW = 0
CREATE_CLIENT = 'MIDIClientCreate'
CREATE_PORT = 'MIDIOutputPortCreate'


@functools.cache
def is_available():
    """Return whether CoreMIDI can be used: on macOS, where its framework loads. Asked once a run."""
    if sys.platform != MACOS:
        return False
    try:
        ctypes.CDLL(COREMIDI)
    except OSError:
        return False
    return True


class CoreMidi:
    """The CoreMIDI and Core Foundation calls the port makes, declared once a process, with the process's one CoreMIDI client."""

    __slots__ = ('midi', 'foundation', 'client', 'mach_per_second', 'mach_time')

    def __init__(self):
        self.midi = ctypes.CDLL(COREMIDI)
        self.foundation = ctypes.CDLL(CORE_FOUNDATION)
        system = ctypes.CDLL(None)
        self.foundation.CFStringCreateWithCString.restype = ctypes.c_void_p
        self.foundation.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        self.foundation.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
        self.foundation.CFRunLoopRunInMode.argtypes = [ctypes.c_void_p, ctypes.c_double, ctypes.c_ubyte]
        self.foundation.CFRunLoopRunInMode.restype = ctypes.c_int32
        for call in (self.midi.MIDIClientCreate, self.midi.MIDIOutputPortCreate, self.midi.MIDISend, self.midi.MIDIPortDispose):
            call.restype = ctypes.c_int32
        self.midi.MIDIGetDestination.restype = ctypes.c_uint32
        self.midi.MIDIPacketListInit.restype = ctypes.c_void_p
        self.midi.MIDIPacketListAdd.restype = ctypes.c_void_p
        self.midi.MIDIPacketListAdd.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_uint64, ctypes.c_size_t, ctypes.c_char_p]
        system.mach_absolute_time.restype = ctypes.c_uint64
        self.mach_time = system.mach_absolute_time
        timebase = (ctypes.c_uint32 * 2)()
        system.mach_timebase_info(timebase)
        self.mach_per_second = NANOSECONDS * timebase[1] / timebase[0]
        self.client = ctypes.c_uint32()
        checked(call=CREATE_CLIENT, status=self.midi.MIDIClientCreate(self.text(CLIENT_NAME), None, None, ctypes.byref(self.client)))

    def text(self, value):
        """Return a Core Foundation string of a Python one."""
        return ctypes.c_void_p(self.foundation.CFStringCreateWithCString(None, value.encode(), UTF8))

    def names_of(self, destination):
        """Return a destination's own name and the name shown for it."""
        names = []
        for property_name in NAME_PROPERTIES:
            found = ctypes.c_void_p()
            self.midi.MIDIObjectGetStringProperty(destination, ctypes.c_void_p.in_dll(self.midi, property_name), ctypes.byref(found))
            text = ctypes.create_string_buffer(NAME_BYTES)
            self.foundation.CFStringGetCString(found, text, NAME_BYTES, UTF8)
            names.append(text.value.decode())
        return names

    def destination_called(self, name):
        """Return the destination a name picks as RtMidiOutput would pick it, the first whose name is it or starts with it."""
        for place in range(self.midi.MIDIGetNumberOfDestinations()):
            destination = self.midi.MIDIGetDestination(place)
            if _named_like(names=self.names_of(destination), name=name):
                return destination
        raise ValueError(errors.ERR_NO_SUCH_MIDI_PORT.format(name=name))


@functools.cache
def core_midi():
    """Return the process's CoreMIDI calls and client, made the first time a port opens."""
    return CoreMidi()


def destination_names():
    """Return the name shown for each of the computer's MIDI destinations, the names python-rtmidi lists, or raise OSError when
    CoreMIDI refuses its client, which python-rtmidi answers by ending the process. The thread's run loop is run once, at once,
    first, as RtMidi does: CoreMIDI tells a process of a destination another program makes later through a notification the run
    loop delivers, and without it a destination made after the first listing, such as FluidSynth's, is never seen."""
    core = core_midi()
    core.foundation.CFRunLoopRunInMode(ctypes.c_void_p.in_dll(core.foundation, DEFAULT_RUN_LOOP_MODE), NO_WAIT, False)
    return [core.names_of(core.midi.MIDIGetDestination(place))[SHOWN_NAME] for place in range(core.midi.MIDIGetNumberOfDestinations())]


def checked(*, call, status):
    """Raise when a CoreMIDI call answers with an error."""
    if status != NO_ERROR:
        raise OSError(errors.ERR_COREMIDI_CALL_FAILED.format(call=call, status=status))


class CoreMidiOutput(ScheduledOutput):
    """A destination of the computer's, opened by name through CoreMIDI, which sends an event at once or at a moment ahead, and takes
    back every event it holds for a moment not yet come."""

    __slots__ = ('_midi', '_client', '_port_name', '_port', '_destination', '_buffer', '_mach_per_second', '_mach_zero', '_clock_zero')

    def __init__(self, *, name):
        core = core_midi()
        self._midi = core.midi
        self._client = core.client
        self._port_name = core.text(name)
        self._destination = core.destination_called(name)
        self._port = self._opened_port()
        self._buffer = ctypes.create_string_buffer(PACKET_LIST_BYTES)
        self._mach_per_second = core.mach_per_second
        # One moment on the two clocks: the mach clock CoreMIDI stamps by, and the clock the engine times events by.
        self._mach_zero = core.mach_time()
        self._clock_zero = time.perf_counter()

    def send(self, data):
        self._send_stamped(data=data, stamp=NOW)

    def send_at(self, *, data, at):
        """Hand an event to CoreMIDI now, to be sent at a reading of time.perf_counter: at once when that moment has passed."""
        self._send_stamped(data=data, stamp=max(NOW, self._mach_zero + int((at - self._clock_zero) * self._mach_per_second)))

    def flush(self):
        """Take back every event handed to CoreMIDI for this destination whose moment has not come, by giving the port up and
        opening another."""
        self._midi.MIDIPortDispose(self._port)
        self._port = self._opened_port()

    def close(self):
        self._midi.MIDIPortDispose(self._port)

    def _opened_port(self):
        port = ctypes.c_uint32()
        checked(call=CREATE_PORT, status=self._midi.MIDIOutputPortCreate(self._client, self._port_name, ctypes.byref(port)))
        return port

    def _send_stamped(self, *, data, stamp):
        packet = self._midi.MIDIPacketListInit(self._buffer)
        message = bytes(data)
        self._midi.MIDIPacketListAdd(self._buffer, PACKET_LIST_BYTES, packet, stamp, len(message), message)
        self._midi.MIDISend(self._port, self._destination, self._buffer)


def _named_like(*, names, name):
    """Return whether any of a destination's names is a name, or starts with it."""
    for found in names:
        if found == name or found.startswith(name):
            return True
    return False
