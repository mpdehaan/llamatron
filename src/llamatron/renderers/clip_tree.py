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
import re

import mido

from llamatron.renderers.timing import BEATS_PER_WHOLE_NOTE, VELOCITY, timed_events
from llamatron.song import Song, _Validated

TICKS_PER_BEAT = 480


def _check_directory(directory):
    if not isinstance(directory, (str, os.PathLike)) or not os.fspath(directory):
        raise ValueError(f'invalid directory: {directory!r}')


def _check_song(song):
    if not isinstance(song, Song):
        raise ValueError(f'expected a Song, got {song!r}')


def _ticks(length):
    """Convert a fraction of a whole note into MIDI ticks."""
    return round(length * BEATS_PER_WHOLE_NOTE * TICKS_PER_BEAT)


def _filename(scene, track, clip):
    """Return <scene_id>-<track_id>-<clip_name>.mid, leaving out the name if there isn't one.

    Numbers count from 1, like scenes and tracks in Live, and are zero-padded to three digits,
    so that files sort in order.
    """
    slot = f'{scene.id + 1:03d}-{track.id + 1:03d}'
    if not clip.name:
        return f'{slot}.mid'
    # Slashes are replaced too, because they would otherwise point to another directory.
    name = re.sub(r'[\s/\\]', '_', clip.name)
    return f'{slot}-{name}.mid'


class ClipTree:
    """Renders a Song as a directory of MIDI files, one per filled scene and track slot.

    Files are named <scene_id>-<track_id>-<clip_name>.mid, such as 002-001-My_Riff.mid, with
    numbers counting from 1 and zero-padded to three digits, and spaces in the clip's name replaced by underscores.
    A clip without a name has no last part.
    """

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
        slots = [
            (_filename(scene, track, clip), scene, track, clip)
            for scene in self.song.scenes
            for track in self.song.tracks
            if (clip := self.song.get_clip(scene, track)) is not None
        ]

        conflicts = sorted(existing.intersection(slot[0] for slot in slots))
        if conflicts:
            print(
                f'warning: stopping without writing anything, because '
                f'{os.fspath(self.directory)} already contains: {", ".join(conflicts)}'
            )
            return
        if existing:
            print(
                f'warning: {os.fspath(self.directory)} already contains '
                f'{len(existing)} other item(s), which will not be deleted: '
                f'{", ".join(sorted(existing))}'
            )

        # Built before any are saved, so that an invalid clip doesn't leave some files written.
        midi_files = [
            (filename, self._midi_file(os.path.splitext(filename)[0], scene, track, clip))
            for filename, scene, track, clip in slots
        ]
        for filename, midi_file in midi_files:
            midi_file.save(os.path.join(self.directory, filename))

    def _midi_file(self, name, scene, track, clip):
        notes, clip_length = timed_events(clip, self.song.scale_at(scene, track))

        # Each event is (tick, 0 for off or 1 for on, MIDI number, velocity). Sorting puts offs before
        # ons at the same tick, so that a note can repeat straight after itself.
        events = []
        for note_start, note_end, midi_number, velocity in notes:
            start, end = _ticks(note_start), _ticks(note_end)
            if end > start:
                events.append((start, 1, midi_number, velocity))
                events.append((end, 0, midi_number, 0))

        messages = [
            # MIDI text is latin-1, so any other characters become question marks here.
            mido.MetaMessage(
                'track_name', name=name.encode('latin-1', 'replace').decode('latin-1'),
            ),
            mido.MetaMessage(
                'set_tempo', tempo=mido.bpm2tempo(self.song.tempo_at(scene))
            ),
        ]
        now = 0
        for tick, is_on, midi_number, velocity in sorted(events):
            if is_on:
                message = mido.Message(
                    'note_on', note=midi_number, velocity=velocity, time=tick - now,
                )
            else:
                message = mido.Message('note_off', note=midi_number, time=tick - now)
            messages.append(message)
            now = tick
        messages.append(mido.MetaMessage('end_of_track', time=_ticks(clip_length) - now))

        return mido.MidiFile(
            type=0, ticks_per_beat=TICKS_PER_BEAT, tracks=[mido.MidiTrack(messages)],
        )
