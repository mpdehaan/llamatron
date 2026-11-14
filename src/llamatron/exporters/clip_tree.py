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

"""Writes a ClipGrid as MIDI files, one per clip, named after the song and the clip's scene and track."""

import os

import mido

from llamatron.exporters.exporter import Exporter, ExportKind, WritesManyFiles
from llamatron.exporters.midi_messages import SINGLE_TRACK_FILE, TICKS_PER_BEAT, clip_events, midi_track, safe_file_name, tempo_event, ticks, time_signature_event
from llamatron.exporters.timing import timed_events
from llamatron.strings.names import MSG_CLIP_TREE_EXPORT_LABEL

# A clip's file name: the song's name, then its scene and track, each as a number counted from 1
# like Live's and zero-padded so that files sort in order, followed by the scene's or track's name if
# it has one: <name>_clip_s_001-verse-t_002-bass.mid. The clip's own name isn't used, since the
# scene and track say which clip it is.
FIRST_NUMBER = 1
CLIP_FILE = '{name}_clip_{scene}-{track}.mid'
SCENE_PART = 's_{number:03d}'
TRACK_PART = 't_{number:03d}'
NAMED_PART = '{part}-{name}'
# The files a clip export leaves beside a set, as a glob pattern and as shown to people.
CLIP_FILES = '{name}_clip_s_[0-9]*.mid'
CLIP_FILES_SHOWN = '{name}_clip_*.mid'
MIDI_SUFFIX = '.mid'
# The tempo is set as the clip starts.
AT_THE_START = 0


def _part(*, part, number, name):
    """Return one part of a clip's file name, like s_001-verse, or just s_001 when the scene or track has no name."""
    numbered = part.format(number=number + FIRST_NUMBER)
    return NAMED_PART.format(part=numbered, name=safe_file_name(name)) if name else numbered


def clip_file_name(*, name, scene, track):
    """Return <name>_clip_s_<scene>-<scene name>-t_<track>-<track name>.mid, with numbers counted from 1 and zero-padded."""
    scene_part = _part(part=SCENE_PART, number=scene.get_id(), name=scene.get_name())
    track_part = _part(part=TRACK_PART, number=track.get_id(), name=track.get_name())
    return CLIP_FILE.format(name=name, scene=scene_part, track=track_part)


class ClipTree(WritesManyFiles, Exporter):
    """Exports a ClipGrid as MIDI files in a directory, one per filled scene and track slot.

    Files are named <name>_clip_s_<scene>-<scene name>-t_<track>-<track name>.mid, such as
    foo_bar_clip_s_002-chorus-t_001-lead.mid, with numbers counting from 1 and zero-padded to
    three digits, and spaces and slashes in the names replaced by underscores. The name is the
    directory's unless one is given, which the tracker and the command line do.
    """

    __slots__ = ()

    KIND = ExportKind.CLIP_TREE
    LABEL = MSG_CLIP_TREE_EXPORT_LABEL
    FILES = CLIP_FILES
    FILES_SHOWN = CLIP_FILES_SHOWN

    def export(self):
        """Write the song's clips, leaving any other files in the directory in place.

        If any of the files to be written already exists, this prints a warning
        and stops without writing anything.
        """
        slots = self._filled_slots()
        if not self.can_write([slot[0] for slot in slots]):
            return

        # Built before any are saved, so that an invalid clip doesn't leave some files written.
        midi_files = self._built_files(slots)
        for filename, midi_file in midi_files:
            midi_file.save(os.path.join(self._directory, filename))

    def _filled_slots(self):
        """Return (file name, scene, track, clip) for each scene and track that has a clip."""
        slots = []
        for scene in self._grid.get_rows():
            for track in self._grid.get_columns():
                clip = self._grid.get_clip(row=scene, column=track)
                if clip is not None:
                    slots.append((clip_file_name(name=self.get_name(), scene=scene, track=track), scene, track, clip))
        return slots

    def _built_files(self, slots):
        """Return (file name, MIDI file) for each filled slot, with the file name, less .mid, as its track's name."""
        return [
            (filename, self._midi_file(name=filename.removesuffix(MIDI_SUFFIX), scene=scene, track=track, clip=clip))
            for filename, scene, track, clip in slots
        ]

    def _midi_file(self, *, name, scene, track, clip):
        notes, clip_length = timed_events(clip=clip, scale=self._grid.scale_at(row=scene, column=track))
        signature = clip.get_time_signature() or self._grid.get_time_signature()
        events = [time_signature_event(tick=AT_THE_START, signature=signature), tempo_event(tick=AT_THE_START, tempo=self._grid.tempo_at(scene))]
        events.extend(clip_events(clip=clip, notes=notes, clip_length=clip_length))
        midi = midi_track(name=name, events=events, end=ticks(clip_length))
        return mido.MidiFile(type=SINGLE_TRACK_FILE, ticks_per_beat=TICKS_PER_BEAT, tracks=[midi])
