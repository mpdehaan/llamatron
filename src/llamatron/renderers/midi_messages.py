# llamatron: a Python language and framework for producing MIDI clips.
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

"""What every MIDI file llamatron writes is made of: events at ticks, and the mido messages and tracks they become.

ClipTree writes a file per clip, MidiSong one file for the whole song and MidiStems a file per
track. They all turn a clip's notes and CC values into MidiEvents with this module, sort them,
and write them as a track with the gaps between them as delta times.
"""

import os
import re
from typing import NamedTuple

import mido

from llamatron.renderers.timing import BEATS_PER_WHOLE_NOTE, control_events
from llamatron.clip_grid import ClipGrid

TICKS_PER_BEAT = 480
# MIDI file types: type 0 holds a single track, and type 1 several that play together.
SINGLE_TRACK_FILE = 0
MULTI_TRACK_FILE = 1
# The kinds of event, in the order they're written when they fall on the same tick: a tempo
# change first, so that what follows plays at it, then a note off, so a note can repeat straight
# after itself, then a CC, so that a note starts with the new value, then a note on.
SET_TEMPO = 0
NOTE_OFF = 1
CONTROL_CHANGE = 2
NOTE_ON = 3
# The names mido gives MIDI's messages.
NOTE_ON_MESSAGE = 'note_on'
NOTE_OFF_MESSAGE = 'note_off'
CONTROL_CHANGE_MESSAGE = 'control_change'
TRACK_NAME_META = 'track_name'
TEMPO_META = 'set_tempo'
END_OF_TRACK_META = 'end_of_track'
# A note off carries no velocity, and a tempo change has no number.
NO_VELOCITY = 0
NO_NUMBER = 0
# Where a track starts, in ticks.
FIRST_TICK = 0
# MIDI text is latin-1, so any other characters in a name become question marks.
MIDI_TEXT_ENCODING = 'latin-1'
REPLACE_UNKNOWN_CHARACTERS = 'replace'
# Spaces and slashes in a name become underscores in a file name, since a slash would point to another directory.
UNSAFE_IN_FILE_NAMES = re.compile(r'[\s/\\]')
SAFE_REPLACEMENT = '_'
# File names, as warnings list them.
FILE_LIST_SEPARATOR = ', '

MSG_BAD_DIRECTORY = 'invalid directory: {value!r}'
MSG_NOT_A_GRID = 'expected a ClipGrid, got {value!r}'


class MidiEvent(NamedTuple):
    """One MIDI message to write: at a tick, of a kind, with its number (note or CC) and value (velocity, CC value or tempo).

    Sorting events puts them in time order, and in the kinds' order at the same tick.
    """

    tick: int
    kind: int
    number: int
    value: int


def check_directory(directory):
    if not isinstance(directory, (str, os.PathLike)) or not os.fspath(directory):
        raise ValueError(MSG_BAD_DIRECTORY.format(value=directory))


def check_grid(grid):
    if not isinstance(grid, ClipGrid):
        raise ValueError(MSG_NOT_A_GRID.format(value=grid))


def ticks(length):
    """Convert a fraction of a whole note into MIDI ticks, rounding once, so that times never drift."""
    return round(length * BEATS_PER_WHOLE_NOTE * TICKS_PER_BEAT)


def midi_text(text):
    """Return text that a MIDI file can hold, with any character latin-1 doesn't have as a question mark."""
    return text.encode(MIDI_TEXT_ENCODING, REPLACE_UNKNOWN_CHARACTERS).decode(MIDI_TEXT_ENCODING)


def safe_file_name(text):
    """Return a name with the characters a file name can't safely hold replaced by underscores."""
    return UNSAFE_IN_FILE_NAMES.sub(SAFE_REPLACEMENT, text)


def tempo_event(tick, tempo):
    """Return the event that sets the tempo, in quarter notes a minute, from a tick on."""
    return MidiEvent(tick, SET_TEMPO, NO_NUMBER, mido.bpm2tempo(tempo))


def clip_events(clip, notes, clip_length, start=FIRST_TICK):
    """Return a clip's notes (its NoteEvents) and CC values as MidiEvents, from a start tick, in no particular order."""
    events = []
    for note in notes:
        note_start, note_end = start + ticks(note.start), start + ticks(note.end)
        if note_end > note_start:
            events.append(MidiEvent(note_start, NOTE_ON, note.midi_number, note.velocity))
            events.append(MidiEvent(note_end, NOTE_OFF, note.midi_number, NO_VELOCITY))
    for event in control_events(clip, clip_length):
        events.append(MidiEvent(start + ticks(event.time), CONTROL_CHANGE, event.number, event.value))
    return events


def message(event, delay):
    """Return the mido message for one event, coming a delay in ticks after the one before."""
    if event.kind == SET_TEMPO:
        return mido.MetaMessage(TEMPO_META, tempo=event.value, time=delay)
    if event.kind == NOTE_ON:
        return mido.Message(NOTE_ON_MESSAGE, note=event.number, velocity=event.value, time=delay)
    if event.kind == CONTROL_CHANGE:
        return mido.Message(CONTROL_CHANGE_MESSAGE, control=event.number, value=event.value, time=delay)
    return mido.Message(NOTE_OFF_MESSAGE, note=event.number, time=delay)


def midi_track(name, events, end):
    """Return a mido track named name, playing events in order and ending at a tick, with each message's time the gap before it."""
    messages = [mido.MetaMessage(TRACK_NAME_META, name=midi_text(name))]
    now = FIRST_TICK
    for event in sorted(events):
        messages.append(message(event, event.tick - now))
        now = event.tick
    messages.append(mido.MetaMessage(END_OF_TRACK_META, time=end - now))
    return mido.MidiTrack(messages)
