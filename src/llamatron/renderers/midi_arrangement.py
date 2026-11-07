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

"""Writes a ClipGrid as an arrangement in MIDI files, for DAWs that have no session grid.

The scenes are laid end to end in order, as Live's Arrangement View lays them, and each track's
clips are placed at their scenes' starts, so a track that plays nothing in the first scenes
starts with silence and every track lines up with the others. Muted tracks are left out, since
they're silent in Live and a MIDI file has no mute. Tempo changes come at the scenes' starts.

MidiSong writes the whole song as one file of type 1, a tempo track and a track per llamatron
track, which most DAWs import as aligned tracks with the tempo map in one drop. MidiStems writes
a file per track, each the full length of the song and each carrying the tempo changes, for
hardware and samplers that take one file at a time.
"""

import glob
import os

import mido

from llamatron.renderers.midi_messages import (
    FILE_LIST_SEPARATOR, MULTI_TRACK_FILE, SINGLE_TRACK_FILE, TICKS_PER_BEAT, check_directory, check_grid,
    clip_events, midi_track, safe_file_name, tempo_event, ticks,
)
from llamatron.renderers.timing import timed_events

# The song's files are named after the directory, like the Live set: <directory>/<name>.mid for the
# whole song, and <directory>/<name>-<track number>-<track name>.mid for each stem, with the
# track number counted from 1 like Live's and zero-padded so that the stems sort in track order.
SONG_FILE = '{name}.mid'
STEM_FILE = '{name}-{number:03d}-{track}.mid'
UNNAMED_STEM_FILE = '{name}-{number:03d}.mid'
# A pattern that matches every stem of a song, and nothing a clip tree writes.
STEM_FILES = '{name}-[0-9][0-9][0-9]*.mid'
FIRST_NUMBER = 1
# What a track with no name is called in a MIDI file.
NO_NAME = ''

MSG_FILE_EXISTS = 'warning: stopping without writing anything, because {path} already exists'
MSG_FILES_EXIST = 'warning: stopping without writing anything, because {directory} already contains: {files}'
MSG_OTHER_FILES = 'warning: {directory} already contains {count} other item(s), which will not be deleted: {files}'


class _Arrangement:
    """What the two arrangement writers share: where they write, and the events of each track laid end to end."""

    __slots__ = ('_directory', '_grid')

    def __init__(self, directory, grid):
        check_directory(directory)
        check_grid(grid)
        self._directory = directory
        self._grid = grid

    def song_name(self):
        """Return the song's name, which is the directory's, like the Live set's."""
        return os.path.basename(os.path.normpath(os.fspath(self._directory)))

    def end_tick(self):
        """Return the tick the song ends at, which every file ends at, so that they're all the same length."""
        return ticks(self._grid.song_length())

    def sounding_tracks(self):
        """Return the tracks that play, in order: every track that isn't muted."""
        return [track for track in self._grid.tracks if not track.mute]

    def tempo_events(self):
        """Return a tempo change at the start of each scene whose tempo differs from the one before, and always at the start."""
        events = []
        tempo = None
        for scene, start in zip(self._grid.scenes, self._grid.scene_starts()):
            if self._grid.tempo_at(scene) != tempo:
                tempo = self._grid.tempo_at(scene)
                events.append(tempo_event(ticks(start), tempo))
        return events

    def track_events(self, track):
        """Return a track's notes and CC values across the whole song, with each clip placed at its scene's start."""
        events = []
        for scene, start in zip(self._grid.scenes, self._grid.scene_starts()):
            clip = self._grid.get_clip(scene, track)
            if clip is not None:
                notes, clip_length = timed_events(clip, self._grid.scale_at(scene, track))
                events.extend(clip_events(clip, notes, clip_length, ticks(start)))
        return events

    def _prepare_directory(self, filenames):
        """Make the directory, and return whether the files can be written: none of them exists yet.

        Prints a warning and answers no if any exists, and prints a warning about other files,
        which are never deleted.
        """
        os.makedirs(self._directory, exist_ok=True)
        existing = set(os.listdir(self._directory))
        directory = os.fspath(self._directory)
        conflicts = sorted(existing.intersection(filenames))
        if conflicts:
            print(MSG_FILES_EXIST.format(directory=directory, files=FILE_LIST_SEPARATOR.join(conflicts)))
            return False
        if existing:
            print(MSG_OTHER_FILES.format(directory=directory, count=len(existing), files=FILE_LIST_SEPARATOR.join(sorted(existing))))
        return True


class MidiSong(_Arrangement):
    """Writes a ClipGrid as one MIDI file of type 1: a tempo track named after the song, then a track per unmuted track."""

    __slots__ = ()

    def path(self):
        """Return the file this writes: <directory>/<directory name>.mid."""
        return os.path.join(self._directory, SONG_FILE.format(name=self.song_name()))

    def render(self):
        """Write the song as one file, unless it already exists, in which case this prints a warning and writes nothing."""
        path = self.path()
        if not self._prepare_directory([os.path.basename(path)]):
            return
        self.midi_file().save(path)

    def midi_file(self):
        """Return the whole song as a mido file: the tempo track and a track per unmuted track, all ending together."""
        end = self.end_tick()
        tracks = [midi_track(self.song_name(), self.tempo_events(), end)]
        for track in self.sounding_tracks():
            tracks.append(midi_track(track.name or NO_NAME, self.track_events(track), end))
        return mido.MidiFile(type=MULTI_TRACK_FILE, ticks_per_beat=TICKS_PER_BEAT, tracks=tracks)


class MidiStems(_Arrangement):
    """Writes a ClipGrid as one MIDI file per unmuted track, each the full length of the song and carrying its tempo changes."""

    __slots__ = ()

    def filenames(self):
        """Return the files this writes, in track order: <song>-<track number>-<track name>.mid."""
        names = []
        for number, track in enumerate(self.sounding_tracks(), FIRST_NUMBER):
            if track.name:
                names.append(STEM_FILE.format(name=self.song_name(), number=number, track=safe_file_name(track.name)))
            else:
                names.append(UNNAMED_STEM_FILE.format(name=self.song_name(), number=number))
        return names

    def render(self):
        """Write a file per track, unless any already exists, in which case this prints a warning and writes nothing."""
        filenames = self.filenames()
        if not self._prepare_directory(filenames):
            return
        # Built before any are saved, so that an invalid clip doesn't leave some files written.
        files = [self.midi_file(track) for track in self.sounding_tracks()]
        for filename, midi_file in zip(filenames, files):
            midi_file.save(os.path.join(self._directory, filename))

    def midi_file(self, track):
        """Return one track as a mido file of type 0, with the tempo changes, its notes and CC values, ending at the song's end."""
        events = self.tempo_events() + self.track_events(track)
        midi = midi_track(track.name or NO_NAME, events, self.end_tick())
        return mido.MidiFile(type=SINGLE_TRACK_FILE, ticks_per_beat=TICKS_PER_BEAT, tracks=[midi])


def stem_files_pattern(directory):
    """Return a glob pattern matching the stems a song's directory holds, which --replace removes."""
    name = os.path.basename(os.path.normpath(os.fspath(directory)))
    return os.path.join(glob.escape(os.fspath(directory)), STEM_FILES.format(name=glob.escape(name)))
