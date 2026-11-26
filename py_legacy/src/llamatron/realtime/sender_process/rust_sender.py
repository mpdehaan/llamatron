# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The real-time sender in Rust: the synth daemon run as `llamatron-backend send` (native/backend/src/daemon/sending.rs), which
sends the player's events on time through the MIDI ports, the built-in synths and FluidSynth, all in one process.

RustSender answers every call of the Python Realtime Sender Process (process.py) and speaks MessagePack to the daemon in
its place: the events cross as the same slim records, the ports each with its kind, so that the daemon knows a built-in
port and FluidSynth's without the tracker's naming rules. It is the sender every play uses wherever the daemon is built;
LLAMATRON_PYTHON_SENDER=1 keeps the Python process. The daemon ends when its input closes or its parent dies, and close
waits for it and ends it if it hangs, so that it is never left an orphan or a zombie.
"""

import atexit
import os
import subprocess
import threading

from llamatron.realtime.sender_process import process as sender_process
from llamatron.realtime.sender_process.process import records_of, SenderNotStarted
from llamatron.realtime.synth_process import daemon as synth_daemon
from llamatron.realtime.synth_process.daemon import DaemonChannel
from llamatron.realtime.synth_process.load import LoadReport
from llamatron.user_strings import errors

PYTHON_SENDER = 'LLAMATRON_PYTHON_SENDER'
SWITCHED_ON = '1'
SEND = 'send'
OPEN = 'open'
START = 'start'
ADD = 'add'
FORGET = 'forget'
STOP_TAG = 'stop_tag'
STOP_ALL = 'stop_all'
SILENCE = 'silence'
SOUNDS = 'sounds'
CLOSE = 'close'
READY = 'ready'
FAILED = 'failed'
LOAD = 'load'
CLOSED = 'closed'
PORT_PROBLEM = 'port'
MIDI = 'midi'
BUILT_IN = 'built_in'
FLUIDSYNTH = 'fluidsynth'
NO_GROUP = 0
CLOSE_TIMEOUT_SECONDS = 2.0


def uses_rust_sender(*, environment=None):
    """Return whether plays send through the Rust sender: the daemon is built, and LLAMATRON_PYTHON_SENDER=1 does not ask
    for the Python process."""
    environment = os.environ if environment is None else environment
    return environment.get(PYTHON_SENDER) != SWITCHED_ON and synth_daemon.uses_daemon(environment=environment)


def made_sender(*, ports, recording=False, driver=None, load=None):
    """Return the sender for the ports: the Rust one where the daemon is built, else the Python process."""
    if uses_rust_sender():
        return RustSender(ports=ports, recording=recording, driver=driver, load=load)
    return sender_process.RealtimeMIDISenderProcess(ports=ports, recording=recording, driver=driver, load=load)


def port_kind(name):
    """Return a port as the daemon opens it, [name, kind, group]: a built-in port with its group of sixteen instruments,
    FluidSynth's where the daemon plays FluidSynth, or a MIDI port of the computer's."""
    from llamatron.realtime.devices import fluidsynth as fluidsynth_device
    if sender_process.is_built_in_port(name):
        return [name, BUILT_IN, sender_process.built_in_group(name)]
    if sender_process.is_fluidsynth_port(name) and fluidsynth_device.plays_in_daemon():
        return [name, FLUIDSYNTH, NO_GROUP]
    return [name, MIDI, NO_GROUP]


class RustSender:
    """The tracker's side of the Rust sender, with the Python sender's calls: start, add, forget, stop_tag, stop_all,
    set_sounds, silence, close and synth_load."""

    __slots__ = ('_ports', '_recording', '_driver', '_load', '_process', '_channel', '_reader', '_closed', '_answer', '_report',
                 '_port_places', '_tag_numbers', '_sounds', '_lock')

    def __init__(self, *, ports, recording=False, driver=None, load=None):
        """ports are the names of the output ports to open; with recording, the daemon keeps what it would send, which close
        hands back. driver is TIMESTAMPED or IMMEDIATE, by default the timestamped one where CoreMIDI is. load, a SharedLoad
        or None, is where the built-in synths' load is written for the tracker."""
        self._ports = list(ports)
        self._recording = recording
        self._driver = driver or sender_process.default_driver()
        self._load = load
        self._process = None
        self._channel = None
        self._reader = None
        self._closed = threading.Event()
        self._answer = None
        self._report = None
        self._port_places = {name: place for place, name in enumerate(self._ports)}
        self._tag_numbers = {}
        self._sounds = {}
        self._lock = threading.Lock()

    def start(self, *, at=None):
        """Start the daemon, which opens the ports, and take this moment, or a reading of the clock given, as the timeline's
        zero; raise SenderNotStarted with why it could not start."""
        program = synth_daemon.daemon_path()
        if program is None:
            raise SenderNotStarted(errors.ERR_SYNTH_DAEMON_MISSING)
        self._process = subprocess.Popen([program, SEND], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self._channel = DaemonChannel(process=self._process)
        atexit.register(self.close)
        self._channel.send([OPEN, self._opening()])
        answer = self._channel.receive()
        if answer is None or answer[0] != READY:
            self.close()
            raise SenderNotStarted(refusal(answer))
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()
        self._send([START, at])

    def add(self, events):
        self._send([ADD, records_of(events=events, place_of_port=self._port_places.__getitem__, number_of_tag=self.tag_number)])

    def forget(self, *, tag, after):
        self._send([FORGET, self.tag_number(tag), after])

    def stop_tag(self, tag):
        self._send([STOP_TAG, self.tag_number(tag)])

    def tag_number(self, tag):
        """Return the number a play's tag crosses to the daemon as."""
        number = self._tag_numbers.get(tag)
        if number is None:
            number = len(self._tag_numbers)
            self._tag_numbers[tag] = number
        return number

    def stop_all(self):
        self._send([STOP_ALL])

    def set_sounds(self, sounds):
        """Give the built-in ports' channels their sounds, a mapping of (port, channel) to the sound, sending only what changed."""
        changed = []
        for (port, channel), spec in sounds.items():
            if self._sounds.get((port, channel)) != spec and port in self._port_places:
                self._sounds[(port, channel)] = spec
                changed.append([self._port_places[port], channel, spec])
        if changed:
            self._send([SOUNDS, changed])

    def silence(self, *, channels):
        """Send note offs, all notes off and all sound off on each (port, channel) given."""
        places = [[self._port_places[port], channel] for port, channel in channels if port in self._port_places]
        self._send([SILENCE, places])

    def synth_load(self):
        """Return the built-in synths' last load report, or None where none has come."""
        if self._load is not None:
            return self._load.read()
        report = self._report
        if report is None:
            return None
        return LoadReport(load=report.get('load', 0.0), peak=report.get('peak', 0.0), voices=report.get('voices', 0), dropouts=report.get('dropouts', 0),
                          late_notes=report.get('late_notes', 0))

    def close(self):
        """Stop everything, close the ports and end the daemon. With recording, return the seconds the timeline started at and
        every (seconds, bytes) sent, by port; without, the seconds and None; None when the daemon never answered."""
        if self._process is None:
            return None
        try:
            self._send([CLOSE])
        except (BrokenPipeError, OSError, ValueError):
            pass
        if self._reader is not None:
            self._closed.wait(CLOSE_TIMEOUT_SECONDS)
        self._end_process()
        return self._result()

    def _opening(self):
        """Return what the daemon is opened with: the ports with their kinds, recording, the driver, the audio device the demo
        recorder names, and FluidSynth's library, SoundFont and gain where its port is among them."""
        from llamatron.realtime.devices import fluidsynth as fluidsynth_device
        ports = [port_kind(name) for name in self._ports]
        opening = {'ports': ports, 'recording': self._recording, 'driver': self._driver, 'device': os.environ.get(fluidsynth_device.AUDIO_DEVICE_VARIABLE) or None, 'fluid': None}
        if any(port[1] == FLUIDSYNTH for port in ports):
            opening['fluid'] = [fluidsynth_device.library_path(), fluidsynth_device.soundfont_path(), float(fluidsynth_device.GAIN)]
        return opening

    def _send(self, message):
        if self._channel is not None and self._process is not None and self._process.poll() is None:
            with self._lock:
                self._channel.send(message)

    def _read(self):
        """Take the daemon's messages until its output closes: its load reports, kept and shared, and its answer as it closes."""
        while True:
            try:
                message = self._channel.receive()
            except (OSError, ValueError):
                message = None
            if message is None:
                break
            if message[0] == LOAD:
                self._report = message[1]
                if self._load is not None:
                    self._load.write(message[1])
            elif message[0] == CLOSED:
                self._answer = message
        self._closed.set()

    def _result(self):
        """Return what close hands back, as the Python sender hands it back."""
        if self._answer is None:
            return None
        started, recordings = self._answer[1], self._answer[2]
        if not self._recording:
            return started, None
        sent = {}
        for name, items in recordings.items():
            sent[name] = [(seconds, list(data)) for seconds, data in items]
        return started, sent

    def _end_process(self):
        """Close the daemon's input, wait for it to end, killing it if it hangs."""
        process = self._process
        self._process = None
        try:
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        try:
            process.wait(CLOSE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        process.stdout.close()


def refusal(answer):
    """Return why the daemon did not start, as the tracker says it: a MIDI port that could not be opened, or what stopped
    the sound."""
    if answer is None or answer[0] != FAILED:
        return errors.ERR_SENDER_DID_NOT_START
    if answer[1] == PORT_PROBLEM:
        return errors.ERR_SENDER_DID_NOT_START
    return errors.ERR_SYNTHESIS_FAILED.format(kind=answer[1], problem=answer[2])
