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

"""Writes a ClipGrid as a directory of MIDI files, one per clip, named after their scene, track and pattern."""

import os

import mido

from llamatron.renderers.midi_messages import (
    FILE_LIST_SEPARATOR, SINGLE_TRACK_FILE, TICKS_PER_BEAT, check_directory, check_grid, clip_events,
    midi_track, safe_file_name, tempo_event, ticks,
)
from llamatron.renderers.timing import timed_events
from llamatron.clip_grid import _Validated

# A clip's file name: its scene's and track's numbers, counted from 1 like Live's and
# zero-padded so that files sort in order, then the clip's name if it has one.
FIRST_NUMBER = 1
SLOT_NAME = '{scene:03d}-{track:03d}'
NAMED_FILE = '{slot}-{name}.mid'
UNNAMED_FILE = '{slot}.mid'
MIDI_SUFFIX = '.mid'
# The tempo is set as the clip starts.
AT_THE_START = 0

MSG_FILES_EXIST = 'warning: stopping without writing anything, because {directory} already contains: {files}'
MSG_OTHER_FILES = 'warning: {directory} already contains {count} other item(s), which will not be deleted: {files}'


def _filename(scene, track, clip):
    """Return <scene_id>-<track_id>-<clip_name>.mid, leaving out the name if there isn't one.

    Numbers count from 1, like scenes and tracks in Live, and are zero-padded to three digits,
    so that files sort in order.
    """
    slot = SLOT_NAME.format(scene=scene.id + FIRST_NUMBER, track=track.id + FIRST_NUMBER)
    if not clip.name:
        return UNNAMED_FILE.format(slot=slot)
    return NAMED_FILE.format(slot=slot, name=safe_file_name(clip.name))


class ClipTree:
    """Renders a ClipGrid as a directory of MIDI files, one per filled scene and track slot.

    Files are named <scene_id>-<track_id>-<clip_name>.mid, such as 002-001-My_Riff.mid, with
    numbers counting from 1 and zero-padded to three digits, and spaces in the clip's name replaced by underscores.
    A clip without a name has no last part.
    """

    __slots__ = ('_directory', '_song')

    directory = _Validated(check_directory)
    song = _Validated(check_grid)

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
            (filename, self._midi_file(filename.removesuffix(MIDI_SUFFIX), scene, track, clip))
            for filename, scene, track, clip in slots
        ]

    def _midi_file(self, name, scene, track, clip):
        notes, clip_length = timed_events(clip, self.song.scale_at(scene, track))
        events = [tempo_event(AT_THE_START, self.song.tempo_at(scene))]
        events.extend(clip_events(clip, notes, clip_length))
        midi = midi_track(name, events, ticks(clip_length))
        return mido.MidiFile(type=SINGLE_TRACK_FILE, ticks_per_beat=TICKS_PER_BEAT, tracks=[midi])
