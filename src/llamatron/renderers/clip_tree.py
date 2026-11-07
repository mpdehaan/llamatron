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

import os
from typing import NamedTuple
import re

import mido

from llamatron.renderers.timing import BEATS_PER_WHOLE_NOTE, control_events, timed_events
from llamatron.clip_grid import ClipGrid, _Validated

TICKS_PER_BEAT = 480
# A MIDI file of type 0 holds a single track.
SINGLE_TRACK_FILE = 0
# The kinds of event a clip's file holds, in the order they're written when they fall on the same
# tick: a note off first, so a note can repeat straight after itself, then a CC, so that a note
# starts with the new value, then a note on.
NOTE_OFF, CONTROL_CHANGE, NOTE_ON = 0, 1, 2
# The names mido gives MIDI's messages.
NOTE_ON_MESSAGE, NOTE_OFF_MESSAGE, CONTROL_CHANGE_MESSAGE = 'note_on', 'note_off', 'control_change'
TRACK_NAME_META, TEMPO_META, END_OF_TRACK_META = 'track_name', 'set_tempo', 'end_of_track'
# A note off carries no velocity.
NO_VELOCITY = 0
# MIDI text is latin-1, so any other characters in a track's name become question marks.
MIDI_TEXT_ENCODING, REPLACE_UNKNOWN_CHARACTERS = 'latin-1', 'replace'

# A clip's file name: its scene's and track's numbers, counted from 1 like Live's and
# zero-padded so that files sort in order, then the clip's name if it has one.
FIRST_NUMBER = 1
SLOT_NAME = '{scene:03d}-{track:03d}'
NAMED_FILE = '{slot}-{name}.mid'
UNNAMED_FILE = '{slot}.mid'
# Spaces and slashes in a clip's name become underscores, since a slash would point to another directory.
UNSAFE_IN_FILE_NAMES = re.compile(r'[\s/\\]')
SAFE_REPLACEMENT = '_'

MSG_BAD_DIRECTORY = 'invalid directory: {value!r}'
MSG_NOT_A_GRID = 'expected a ClipGrid, got {value!r}'
MSG_FILES_EXIST = 'warning: stopping without writing anything, because {directory} already contains: {files}'
MSG_OTHER_FILES = 'warning: {directory} already contains {count} other item(s), which will not be deleted: {files}'
# File names, as the warnings list them.
FILE_LIST_SEPARATOR = ', '


def _check_directory(directory):
    if not isinstance(directory, (str, os.PathLike)) or not os.fspath(directory):
        raise ValueError(MSG_BAD_DIRECTORY.format(value=directory))


def _check_song(song):
    if not isinstance(song, ClipGrid):
        raise ValueError(MSG_NOT_A_GRID.format(value=song))


def _ticks(length):
    """Convert a fraction of a whole note into MIDI ticks."""
    return round(length * BEATS_PER_WHOLE_NOTE * TICKS_PER_BEAT)


def _filename(scene, track, clip):
    """Return <scene_id>-<track_id>-<clip_name>.mid, leaving out the name if there isn't one.

    Numbers count from 1, like scenes and tracks in Live, and are zero-padded to three digits,
    so that files sort in order.
    """
    slot = SLOT_NAME.format(scene=scene.id + FIRST_NUMBER, track=track.id + FIRST_NUMBER)
    if not clip.name:
        return UNNAMED_FILE.format(slot=slot)
    return NAMED_FILE.format(slot=slot, name=UNSAFE_IN_FILE_NAMES.sub(SAFE_REPLACEMENT, clip.name))


def _midi_text(text):
    """Return text that a MIDI file can hold, with any character latin-1 doesn't have as a question mark."""
    return text.encode(MIDI_TEXT_ENCODING, REPLACE_UNKNOWN_CHARACTERS).decode(MIDI_TEXT_ENCODING)


class ClipTree:
    """Renders a ClipGrid as a directory of MIDI files, one per filled scene and track slot.

    Files are named <scene_id>-<track_id>-<clip_name>.mid, such as 002-001-My_Riff.mid, with
    numbers counting from 1 and zero-padded to three digits, and spaces in the clip's name replaced by underscores.
    A clip without a name has no last part.
    """

    __slots__ = ('_directory', '_song')

    directory = _Validated(_check_directory)
    song = _Validated(_check_song)

    def __init__(self, directory, song):
        self.directory = directory
        self.song = song

    def render(self):
        """Write the song's clips, leaving any other files in the directory in place.

        If any of the files to be written already exists, this prints a warning
        and stops without writing anything.
        """
        os.makedirs(self.directory, exist_ok=True)
        existing = set(os.listdir(self.directory))
        slots = self._filled_slots()
        directory = os.fspath(self.directory)

        conflicts = sorted(existing.intersection(slot[0] for slot in slots))
        if conflicts:
            print(MSG_FILES_EXIST.format(directory=directory, files=FILE_LIST_SEPARATOR.join(conflicts)))
            return
        if existing:
            print(MSG_OTHER_FILES.format(directory=directory, count=len(existing), files=FILE_LIST_SEPARATOR.join(sorted(existing))))

        # Built before any are saved, so that an invalid clip doesn't leave some files written.
        midi_files = self._built_files(slots)
        for filename, midi_file in midi_files:
            midi_file.save(os.path.join(self.directory, filename))

    def _filled_slots(self):
        """Return (file name, scene, track, clip) for each scene and track that has a clip."""
        slots = []
        for scene in self.song.scenes:
            for track in self.song.tracks:
                clip = self.song.get_clip(scene, track)
                if clip is not None:
                    slots.append((_filename(scene, track, clip), scene, track, clip))
        return slots

    def _built_files(self, slots):
        """Return (file name, MIDI file) for each filled slot, with the file name, less .mid, as its track's name."""
        return [
            (filename, self._midi_file(os.path.splitext(filename)[0], scene, track, clip))
            for filename, scene, track, clip in slots
        ]

    def _midi_file(self, name, scene, track, clip):
        notes, clip_length = timed_events(clip, self.song.scale_at(scene, track))
        messages = [
            mido.MetaMessage(TRACK_NAME_META, name=_midi_text(name)),
            mido.MetaMessage(TEMPO_META, tempo=mido.bpm2tempo(self.song.tempo_at(scene))),
        ]
        now = 0
        for event in sorted(_events(notes, clip, clip_length)):
            messages.append(_message(event.kind, event.number, event.value, event.tick - now))
            now = event.tick
        messages.append(mido.MetaMessage(END_OF_TRACK_META, time=_ticks(clip_length) - now))
        return mido.MidiFile(type=SINGLE_TRACK_FILE, ticks_per_beat=TICKS_PER_BEAT, tracks=[mido.MidiTrack(messages)])


class MidiEvent(NamedTuple):
    """One MIDI message to write: at a tick, of a kind, with its number (note or CC) and value (velocity or CC value)."""

    tick: int
    kind: str
    number: int
    value: int


def _events(notes, clip, clip_length):
    """Return a clip's notes and CC values as MidiEvents, in no particular order."""
    events = []
    for note in notes:
        start, end = _ticks(note.start), _ticks(note.end)
        if end > start:
            events.append(MidiEvent(start, NOTE_ON, note.midi_number, note.velocity))
            events.append(MidiEvent(end, NOTE_OFF, note.midi_number, NO_VELOCITY))
    for event in control_events(clip, clip_length):
        events.append(MidiEvent(_ticks(event.time), CONTROL_CHANGE, event.number, event.value))
    return events


def _message(kind, number, value, delay):
    """Return the MIDI message for one event, coming a delay in ticks after the one before."""
    if kind == NOTE_ON:
        return mido.Message(NOTE_ON_MESSAGE, note=number, velocity=value, time=delay)
    if kind == CONTROL_CHANGE:
        return mido.Message(CONTROL_CHANGE_MESSAGE, control=number, value=value, time=delay)
    return mido.Message(NOTE_OFF_MESSAGE, note=number, time=delay)
