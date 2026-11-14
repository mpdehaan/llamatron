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

import os

import mido

from llamatron.exporters.exporter import Exporter, ExportKind, WritesManyFiles, WritesOneFile
from llamatron.exporters.midi_messages import (
    FIRST_TICK, MULTI_TRACK_FILE, SINGLE_TRACK_FILE, TICKS_PER_BEAT, clip_events, midi_track, safe_file_name, tempo_event, ticks, time_signature_event,
)
from llamatron.exporters.timing import timed_events
from llamatron.composition.limits import MIN_GM_SOUND
from llamatron.strings.names import MSG_GENERAL_MIDI_EXPORT_LABEL, MSG_MIDI_FILE_EXPORT_LABEL, MSG_STEMS_EXPORT_LABEL

# The song's files are named after the song, like the Live set: <directory>/<name>.mid for the
# whole song, and <directory>/<name>_stem_<track number>-<track name>.mid for each stem, with the
# track number counted from 1 like Live's and zero-padded so that the stems sort in track order.
# The name is the directory's unless one is given, which the tracker and the command line do.
SONG_FILE = '{name}.mid'
# The General MIDI file, beside the plain one, so that neither writes over the other.
GENERAL_MIDI_FILE = '{name}_gm.mid'
# General MIDI's channels as bytes: drums on channel 10, and every other track on the others in turn, starting again after 16.
DRUM_CHANNEL_BYTE = 9
MELODIC_CHANNEL_BYTES = [channel for channel in range(16) if channel != DRUM_CHANNEL_BYTE]
STEM_FILE = '{name}_stem_{number:03d}-{track}.mid'
UNNAMED_STEM_FILE = '{name}_stem_{number:03d}.mid'
# The stems of a song, as a glob pattern that matches nothing a clip export writes, and as shown to people.
STEM_FILES = '{name}_stem_[0-9][0-9][0-9]*.mid'
STEM_FILES_SHOWN = '{name}_stem_*.mid'
FIRST_NUMBER = 1
# What a track with no name is called in a MIDI file.
NO_NAME = ''


class _Arrangement(Exporter):
    """What the two arrangement exporters share: the events of each track laid end to end."""

    __slots__ = ()

    def end_tick(self):
        """Return the tick the song ends at, which every file ends at, so that they're all the same length."""
        return ticks(self._grid.song_length())

    def sounding_tracks(self):
        """Return the tracks that play, in order: every track that isn't muted."""
        return [track for track in self._grid.get_columns() if not track.get_mute()]

    def conductor_events(self):
        """Return what every file starts with: the song's time signature, then the tempo and its changes."""
        return [time_signature_event(tick=FIRST_TICK, signature=self._grid.get_time_signature()), *self.tempo_events()]

    def tempo_events(self):
        """Return a tempo change at the start of each scene whose tempo differs from the one before, and always at the start."""
        events = []
        tempo = None
        for scene, start in zip(self._grid.get_rows(), self._grid.row_starts()):
            if self._grid.tempo_at(scene) != tempo:
                tempo = self._grid.tempo_at(scene)
                events.append(tempo_event(tick=ticks(start), tempo=tempo))
        return events

    def track_events(self, track):
        """Return a track's notes and CC values across the whole song, with each clip placed at its scene's start."""
        events = []
        for scene, start in zip(self._grid.get_rows(), self._grid.row_starts()):
            clip = self._grid.get_clip(row=scene, column=track)
            if clip is not None:
                notes, clip_length = timed_events(clip=clip, scale=self._grid.scale_at(row=scene, column=track))
                events.extend(clip_events(clip=clip, notes=notes, clip_length=clip_length, start=ticks(start)))
        return events

class MidiSong(WritesOneFile, _Arrangement):
    """Exports a ClipGrid as one MIDI file of type 1, <directory>/<name>.mid: a tempo track named after the song, then a track per unmuted track."""

    __slots__ = ()

    KIND = ExportKind.MIDI_FILE
    LABEL = MSG_MIDI_FILE_EXPORT_LABEL
    FILE = SONG_FILE

    def export(self):
        """Write the song as one file, unless it already exists, in which case this prints a warning and writes nothing."""
        path = self.path()
        if not self.can_write([os.path.basename(path)]):
            return
        self.midi_file().save(path)

    def midi_file(self):
        """Return the whole song as a mido file: the tempo track and a track per unmuted track, all ending together."""
        end = self.end_tick()
        tracks = [midi_track(name=self.get_name(), events=self.conductor_events(), end=end)]
        for track in self.sounding_tracks():
            tracks.append(midi_track(name=track.get_name() or NO_NAME, events=self.track_events(track), end=end))
        return mido.MidiFile(type=MULTI_TRACK_FILE, ticks_per_beat=TICKS_PER_BEAT, tracks=tracks)


class MidiGeneralMidi(WritesOneFile, _Arrangement):
    """Exports a ClipGrid as one General MIDI file, <directory>/<name>_gm.mid, for any player with General MIDI's sounds, the user's design of 2026-11-11.

    It is the single file of MidiSong with each track on a channel of its own: drums on channel 10,
    every other unmuted track on the others in turn, and a program change first that gives a
    track its instrument's General MIDI sound. A track whose instrument has no sound sends none, so
    a player plays its first sound, a piano, there.
    """

    __slots__ = ()

    KIND = ExportKind.GENERAL_MIDI
    LABEL = MSG_GENERAL_MIDI_EXPORT_LABEL
    FILE = GENERAL_MIDI_FILE

    def export(self):
        """Write the song as one file, unless it already exists, in which case this prints a warning and writes nothing."""
        path = self.path()
        if not self.can_write([os.path.basename(path)]):
            return
        self.midi_file().save(path)

    def channels(self):
        """Return each unmuted track's channel byte, by the track: 9 for drums, and the other channels in turn for the rest."""
        channels = {}
        melodic = 0
        for track in self.sounding_tracks():
            if track.is_drum():
                channels[track] = DRUM_CHANNEL_BYTE
            else:
                channels[track] = MELODIC_CHANNEL_BYTES[melodic % len(MELODIC_CHANNEL_BYTES)]
                melodic += 1
        return channels

    def midi_file(self):
        """Return the whole song as a mido file: the tempo track and a track per unmuted track on its channel with its sound, all ending together."""
        end = self.end_tick()
        tracks = [midi_track(name=self.get_name(), events=self.conductor_events(), end=end)]
        for track, channel in self.channels().items():
            sound = track.get_gm_sound()
            # A drum track's sound is the drum kit channel 10 plays, so no program change is sent there.
            program = None if sound is None or track.is_drum() else sound - MIN_GM_SOUND
            tracks.append(midi_track(name=track.get_name() or NO_NAME, events=self.track_events(track), end=end, channel=channel, program=program))
        return mido.MidiFile(type=MULTI_TRACK_FILE, ticks_per_beat=TICKS_PER_BEAT, tracks=tracks)


class MidiStems(WritesManyFiles, _Arrangement):
    """Exports a ClipGrid as one MIDI file per unmuted track, each the full length of the song and carrying its tempo changes."""

    __slots__ = ()

    KIND = ExportKind.STEMS
    LABEL = MSG_STEMS_EXPORT_LABEL
    FILES = STEM_FILES
    FILES_SHOWN = STEM_FILES_SHOWN

    def filenames(self):
        """Return the files this writes, in track order: <name>_stem_<track number>-<track name>.mid."""
        names = []
        for number, track in enumerate(self.sounding_tracks(), FIRST_NUMBER):
            if track.get_name():
                names.append(STEM_FILE.format(name=self.get_name(), number=number, track=safe_file_name(track.get_name())))
            else:
                names.append(UNNAMED_STEM_FILE.format(name=self.get_name(), number=number))
        return names

    def export(self):
        """Write a file per track, unless any already exists, in which case this prints a warning and writes nothing."""
        filenames = self.filenames()
        if not self.can_write(filenames):
            return
        # Built before any are saved, so that an invalid clip doesn't leave some files written.
        files = [self.midi_file(track) for track in self.sounding_tracks()]
        for filename, midi_file in zip(filenames, files):
            midi_file.save(os.path.join(self._directory, filename))

    def midi_file(self, track):
        """Return one track as a mido file of type 0, with the tempo changes, its notes and CC values, ending at the song's end."""
        events = self.conductor_events() + self.track_events(track)
        midi = midi_track(name=track.get_name() or NO_NAME, events=events, end=self.end_tick())
        return mido.MidiFile(type=SINGLE_TRACK_FILE, ticks_per_beat=TICKS_PER_BEAT, tracks=[midi])

