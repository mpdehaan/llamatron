# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The WAV export's built-in half: the tracks whose instrument is built in, each read as notes in seconds from the song's
start, rendered offline by the synth daemon, and mixed with FluidSynth's half.

A track's notes are timed exactly as the MIDI file times them: its events and the song's tempo changes are laid in a MIDI
file, which mido reads back in seconds, so that the built-in tracks and the FluidSynth tracks keep one tempo map. Each clip's
start is marked the way the real-time player marks it, so that an LFO that restarts each scene restarts there too.
"""

import mido
import numpy
import os
import wave

from llamatron.exporters import midi_messages
from llamatron.exporters.midi_messages import midi_track, ticks
from llamatron.user_strings import errors

RATE = 44100
TAIL_SECONDS = 3.0
BUILT_IN_FILE = 'built_in.wav'
NOTE_ON = 'note_on'
NOTE_OFF = 'note_off'
CONTROL_CHANGE = 'control_change'
SCENE_STARTED = 102
ENDING_CONTROLS = (120, 123)
FLOAT_SAMPLE = numpy.float32
WHOLE_SAMPLE = numpy.int16
HIGHEST_SAMPLE = 32767
READ = 'rb'
WRITE = 'wb'
CHANNELS = 2
SAMPLE_BYTES = 2
FLOAT_BYTES = 4
LITTLE_ENDIAN = 'little'


class BuiltInTrack:
    """A track a WAV export renders on the built-in synths: its instrument's spec, its notes as (seconds, pitch, velocity),
    a velocity of 0 ending a note, the moments its clips start, and the moments every note of it ends."""

    __slots__ = ('spec', 'notes', 'scene_starts', 'endings')

    def __init__(self, *, spec):
        self.spec = spec
        self.notes = []
        self.scene_starts = []
        self.endings = []


class BuiltInHalf:
    """The built-in tracks of a WAV export, read from its arrangement (midi_arrangement._Arrangement)."""

    __slots__ = ('_arrangement',)

    def __init__(self, *, arrangement):
        self._arrangement = arrangement

    def tracks(self):
        """Return the unmuted tracks whose instrument is built in, in order, as BuiltInTracks."""
        found = []
        for column in self._arrangement.sounding_tracks():
            spec = column.built_in_spec()
            if spec is not None:
                found.append(self._read(column=column, spec=spec))
        return found

    def render(self, *, renderer, directory):
        """Render the built-in tracks into a WAV file of floats in a directory, and return its path, or None when there are
        none."""
        tracks = self.tracks()
        if not tracks:
            return None
        path = os.path.join(directory, BUILT_IN_FILE)
        seconds = self._song_seconds() + TAIL_SECONDS
        renderer(tracks=tracks, seconds=seconds, path=path, rate=RATE)
        return path

    def _read(self, *, column, spec):
        """Return a track's notes in seconds, read back from a MIDI file of the song's tempo map, its events and its clip
        starts."""
        arrangement = self._arrangement
        end = arrangement.end_tick()
        events = list(arrangement.track_events(column))
        conductor = midi_track(name='', events=arrangement.conductor_events(), end=end)
        notes = midi_track(name='', events=events, end=end)
        starts = self._clip_start_ticks(column)
        file = mido.MidiFile(type=midi_messages.MULTI_TRACK_FILE, ticks_per_beat=midi_messages.TICKS_PER_BEAT, tracks=[conductor, notes, marks_track(starts)])
        track = BuiltInTrack(spec=spec)
        now = 0.0
        for message in file:
            now += message.time
            take_message(track=track, message=message, now=now)
        return track

    def _clip_start_ticks(self, column):
        grid = self._arrangement.get_grid()
        found = []
        for scene, start in zip(grid.get_rows(), grid.row_starts()):
            if grid.get_clip(row=scene, column=column) is not None:
                found.append(ticks(start))
        return found

    def _song_seconds(self):
        arrangement = self._arrangement
        conductor = midi_track(name='', events=arrangement.conductor_events(), end=arrangement.end_tick())
        return mido.MidiFile(type=midi_messages.MULTI_TRACK_FILE, ticks_per_beat=midi_messages.TICKS_PER_BEAT, tracks=[conductor]).length


def marks_track(starts):
    """Return a MIDI track marking each clip start with the controller the real-time player marks it with."""
    track = mido.MidiTrack()
    last = 0
    for tick in sorted(starts):
        track.append(mido.Message(CONTROL_CHANGE, control=SCENE_STARTED, value=0, time=tick - last))
        last = tick
    return track


def take_message(*, track, message, now):
    """Add one message read back in seconds to a track: a note's start or end, an ending of every note, or a clip's start."""
    if message.type == NOTE_ON and message.velocity > 0:
        track.notes.append((now, message.note, message.velocity))
    elif message.type in (NOTE_ON, NOTE_OFF):
        track.notes.append((now, message.note, 0))
    elif message.type == CONTROL_CHANGE and message.control == SCENE_STARTED:
        track.scene_starts.append(now)
    elif message.type == CONTROL_CHANGE and message.control in ENDING_CONTROLS:
        track.endings.append(now)


def mixed_into(*, path, fluidsynth=None, built_in=None):
    """Write the mix of FluidSynth's 16-bit WAV and the built-in tracks' float WAV, either of which may be None, into a
    16-bit WAV at path, each at full level, so that the normalizing after it decides the whole's level."""
    read = []
    if fluidsynth is not None:
        read.append(read_wave(fluidsynth))
    if built_in is not None:
        read.append(read_wave(built_in))
    rate = read[0][0]
    parts = [samples for _, samples in read]
    length = max(len(part) for part in parts)
    mix = numpy.zeros((length, CHANNELS))
    for part in parts:
        mix[:len(part)] += part
    loudest = float(numpy.max(numpy.abs(mix))) if mix.size else 0.0
    if loudest > 1.0:
        mix /= loudest
    with wave.open(path, WRITE) as file:
        file.setnchannels(CHANNELS)
        file.setsampwidth(SAMPLE_BYTES)
        file.setframerate(rate)
        file.writeframes(numpy.round(mix * HIGHEST_SAMPLE).astype(WHOLE_SAMPLE).tobytes())


def read_wave(path):
    """Return a WAV file's rate and its samples as floats from -1 to 1, a row a frame and a column a channel: 16-bit PCM, as FluidSynth
    writes, or 32-bit float, as the synth daemon writes, which the wave module cannot read, so its data is found by hand."""
    with open(path, READ) as file:
        data = file.read()
    format_at = data.find(b'fmt ')
    channels = int.from_bytes(data[format_at + 10:format_at + 12], LITTLE_ENDIAN)
    rate = int.from_bytes(data[format_at + 12:format_at + 16], LITTLE_ENDIAN)
    width = int.from_bytes(data[format_at + 22:format_at + 24], LITTLE_ENDIAN) // 8
    body_at = data.find(b'data') + 8
    if width == FLOAT_BYTES:
        samples = numpy.frombuffer(data[body_at:], dtype=FLOAT_SAMPLE).astype(numpy.float64)
    elif width == SAMPLE_BYTES:
        samples = numpy.frombuffer(data[body_at:], dtype=WHOLE_SAMPLE).astype(numpy.float64) / HIGHEST_SAMPLE
    else:
        raise ValueError(errors.ERR_NOT_16_BIT_WAVE.format(path=path, bits=width * 8))
    usable = len(samples) - len(samples) % channels
    return rate, samples[:usable].reshape(-1, channels)
