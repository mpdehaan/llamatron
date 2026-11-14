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
"""Reading a MIDI file into what the import works from: the notes of each part, and the tempos, time signatures and keys.

A part is what one channel of one MIDI track plays, so that a file of type 0, which holds every
channel in one track, still comes apart into its instruments. Times are whole notes from the
start of the song, exact, worked out from the file's ticks, as every length in llamatron is.
A note the file starts and never ends lasts until its track ends, and is counted. A part keeps its
channel's CC messages, which the import may bring in (voices.py).
"""

from dataclasses import dataclass
from typing import NamedTuple

from llamatron.support.rational import Rational
from llamatron.strings.importing import MSG_UNNAMED_MIDI_TRACK

# mido's names for the messages the import reads.
NOTE_ON = 'note_on'
NOTE_OFF = 'note_off'
TRACK_NAME = 'track_name'
SET_TEMPO = 'set_tempo'
TIME_SIGNATURE = 'time_signature'
KEY_SIGNATURE = 'key_signature'
# A CC message, which a part keeps, and the messages that change how a note sounds that llamatron has no
# way to send, which the import leaves out and counts: pitch bend is a message of its own, not a CC.
CONTROL_CHANGE = 'control_change'
LEFT_OUT_MESSAGES = ('pitchwheel', 'aftertouch', 'polytouch')
# Channel 10 as people count, General MIDI's drums; mido counts channels from 0.
DRUM_CHANNEL = 9
QUARTER_NOTES_PER_WHOLE_NOTE = 4
FIRST_TICK = 0
FIRST_TRACK_NUMBER = 1
# A note on with no velocity is how many files end a note.
SILENT_VELOCITY = 0
# What a track's name loses at either end: spaces, and the colon LilyPond puts after a staff's name, like up:.
NAME_TRIMMINGS = ' \t:'
# MIDI's tempo when a file sets none, 120 quarter notes a minute, in microseconds a quarter note.
DEFAULT_TEMPO = 500000
# MIDI's time signature when a file sets none, as beats and the note that is a beat.
DEFAULT_TIME_SIGNATURE = (4, 4)


class HeardNote(NamedTuple):
    """One note a part plays: when it starts and ends, in whole notes from the song's start, its MIDI number and its velocity."""

    start: Rational
    end: Rational
    pitch: int
    velocity: int


class HeardControl(NamedTuple):
    """One CC message a part sends: when, in whole notes from the song's start, its CC number and its value."""

    time: Rational
    number: int
    value: int


class Change(NamedTuple):
    """Something the file sets from a time on: a tempo in microseconds a quarter note, a time signature as beats and unit, or a key as mido writes it, like Bbm."""

    time: Rational
    value: object


@dataclass(slots=True, kw_only=True)
class MidiPart:
    """The notes one channel of one MIDI track plays, in the order they start, its CC messages in time order, and the track's name."""

    name: str
    channel: int
    notes: list
    controls: list

    def is_drums(self):
        return self.channel == DRUM_CHANNEL


@dataclass(slots=True, kw_only=True)
class MidiContents:
    """Everything the import reads from a MIDI file: its parts, and its tempos, time signatures and keys in time order, each starting at the song's start."""

    parts: list
    tempos: list
    time_signatures: list
    keys: list
    # How many notes the file never ended, how many messages that change a sound llamatron can't send, and how many CC
    # messages were sent on a channel that plays no notes, which no track takes.
    unended: int
    left_out: int
    controls_without_notes: int

    def end(self):
        """Return when the last note ends, in whole notes, or nothing for a file with no notes."""
        return max((note.end for part in self.parts for note in part.notes), default=Rational(0))

    def note_count(self):
        return sum(len(part.notes) for part in self.parts)


def whole_notes(*, tick, ticks_per_beat):
    """Return a time in ticks as whole notes, exactly."""
    return Rational(tick, ticks_per_beat * QUARTER_NOTES_PER_WHOLE_NOTE)


def trimmed_name(name):
    """Return a MIDI track's name without the spaces and colons round it."""
    return name.strip(NAME_TRIMMINGS)


def from_the_start(*, changes, default):
    """Return changes in time order, with no change repeating the one before, starting at the song's start with the default if the file set nothing there."""
    ordered = sorted(changes, key=lambda change: change.time)
    if not ordered or ordered[0].time != 0:
        ordered.insert(0, Change(Rational(0), default))
    kept = []
    for change in ordered:
        if kept and kept[-1].time == change.time:
            kept[-1] = change
        elif not kept or kept[-1].value != change.value:
            kept.append(change)
    return kept


def read_midi(midi_file):
    """Return what a mido file holds, as MidiContents: a part for each channel of each track that plays notes."""
    ticks_per_beat = midi_file.ticks_per_beat
    parts = []
    tempos = []
    time_signatures = []
    keys = []
    unended = 0
    left_out = 0
    controls_without_notes = 0
    numbered = FIRST_TRACK_NUMBER
    for track in midi_file.tracks:
        tick = FIRST_TICK
        name = None
        held = {}
        notes_by_channel = {}
        controls_by_channel = {}
        for message in track:
            tick += message.time
            time = whole_notes(tick=tick, ticks_per_beat=ticks_per_beat)
            if message.type == TRACK_NAME and name is None:
                name = trimmed_name(message.name)
            elif message.type == SET_TEMPO:
                tempos.append(Change(time, message.tempo))
            elif message.type == TIME_SIGNATURE:
                time_signatures.append(Change(time, (message.numerator, message.denominator)))
            elif message.type == KEY_SIGNATURE:
                keys.append(Change(time, message.key))
            elif message.type in LEFT_OUT_MESSAGES:
                left_out += 1
            elif message.type == CONTROL_CHANGE:
                controls_by_channel.setdefault(message.channel, []).append(HeardControl(time, message.control, message.value))
            elif message.type == NOTE_ON and message.velocity > SILENT_VELOCITY:
                held.setdefault((message.channel, message.note), []).append((time, message.velocity))
            elif message.type in (NOTE_ON, NOTE_OFF) and held.get((message.channel, message.note)):
                start, velocity = held[(message.channel, message.note)].pop(0)
                if time > start:
                    notes_by_channel.setdefault(message.channel, []).append(HeardNote(start, time, message.note, velocity))
        end = whole_notes(tick=tick, ticks_per_beat=ticks_per_beat)
        for (channel, pitch), starts in held.items():
            for start, velocity in starts:
                unended += 1
                if end > start:
                    notes_by_channel.setdefault(channel, []).append(HeardNote(start, end, pitch, velocity))
        controls_without_notes += sum(len(controls) for channel, controls in controls_by_channel.items() if channel not in notes_by_channel)
        if not notes_by_channel:
            continue
        name = name or MSG_UNNAMED_MIDI_TRACK.format(number=numbered)
        numbered += 1
        for channel in sorted(notes_by_channel):
            parts.append(MidiPart(name=name, channel=channel, notes=sorted(notes_by_channel[channel]), controls=controls_by_channel.get(channel, [])))
    return MidiContents(
        parts=parts, tempos=from_the_start(changes=tempos, default=DEFAULT_TEMPO),
        time_signatures=from_the_start(changes=time_signatures, default=DEFAULT_TIME_SIGNATURE),
        keys=sorted(keys, key=lambda change: change.time), unended=unended, left_out=left_out, controls_without_notes=controls_without_notes,
    )


def value_at(*, changes, time):
    """Return what a list of changes in time order sets at a time: the last change at or before it."""
    value = changes[0].value
    for change in changes:
        if change.time > time:
            break
        value = change.value
    return value
