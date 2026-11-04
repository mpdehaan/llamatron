# noose6: a Python language and framework for producing MIDI clips.
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
from fractions import Fraction

import mido

from src.chord import Chord
from src.note import Degree, Note, Rest
from src.song import Song, _Validated

# A beat is a quarter note, which matches how MIDI measures both ticks and tempo.
TICKS_PER_BEAT = 480
BEATS_PER_WHOLE_NOTE = 4
VELOCITY = 100


def _check_directory(directory):
    if not isinstance(directory, (str, os.PathLike)) or not os.fspath(directory):
        raise ValueError(f'invalid directory: {directory!r}')


def _check_song(song):
    if not isinstance(song, Song):
        raise ValueError(f'expected a Song, got {song!r}')


def _degree_to_note(position, scale):
    """Return a Note for a Degree, leaving anything else as it is."""
    if not isinstance(position, Degree):
        return position
    if scale is None:
        raise ValueError(f'{position!r} needs a scale, but the clip, scene and song have none')
    return position.to_note(scale)


def _sounding_notes(position):
    """Return {MIDI number: length} for one position in a clip."""
    # A clip's list can be appended to directly, so its contents are checked again here.
    if isinstance(position, Rest):
        return {}
    if isinstance(position, Note):
        return {position.midi_number: position.length}
    if isinstance(position, Chord):
        lengths = {}
        for note in position.notes:
            lengths[note.midi_number] = max(note.length, lengths.get(note.midi_number, 0))
        return lengths
    raise ValueError(f'expected a Note, Chord or Rest, got {position!r}')


def _ticks(length):
    """Convert a fraction of a whole note into MIDI ticks."""
    return round(length * BEATS_PER_WHOLE_NOTE * TICKS_PER_BEAT)


def _filename(scene, track, clip):
    """Return <scene_id>-<track_id>-<clip_name>.mid, leaving out the name if there isn't one."""
    if not clip.name:
        return f'{scene.id}-{track.id}.mid'
    # Slashes are replaced too, because they would otherwise point to another directory.
    name = re.sub(r'[\s/\\]', '_', clip.name)
    return f'{scene.id}-{track.id}-{name}.mid'


class ClipTree:
    """Renders a Song as a directory of MIDI files, one per filled scene and track slot.

    Files are named <scene_id>-<track_id>-<clip_name>.mid, with spaces in the clip's
    name replaced by underscores. A clip without a name has no last part.
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
            (filename, self._midi_file(scene, track, clip))
            for filename, scene, track, clip in slots
        ]
        for filename, midi_file in midi_files:
            midi_file.save(os.path.join(self.directory, filename))

    def _midi_file(self, scene, track, clip):
        # This is where lengths and degrees are finally settled, as late as possible.
        scale = self.song.scale_at(scene, track)
        notes = [_degree_to_note(position, scale) for position in clip.resolved_notes()]
        positions = [(_sounding_notes(position), position.length) for position in notes]
        if clip.length is None:
            clip_length = sum((Fraction(length) for _, length in positions), Fraction(0))
        else:
            clip_length = Fraction(clip.length)

        # Each event is (tick, 0 for off or 1 for on, MIDI number). Sorting puts offs before
        # ons at the same tick, so that a note can repeat straight after itself.
        events = []
        position_start = Fraction(0)
        for sounding_notes, position_length in positions:
            start = _ticks(min(position_start, clip_length))
            for midi_number, note_length in sounding_notes.items():
                end = _ticks(min(position_start + Fraction(note_length), clip_length))
                if end > start:
                    events.append((start, 1, midi_number))
                    events.append((end, 0, midi_number))
            position_start += Fraction(position_length)

        messages = [
            mido.MetaMessage(
                'set_tempo', tempo=mido.bpm2tempo(self.song.tempo_at(scene))
            ),
        ]
        now = 0
        for tick, is_on, midi_number in sorted(events):
            if is_on:
                message = mido.Message(
                    'note_on', note=midi_number, velocity=VELOCITY, time=tick - now,
                )
            else:
                message = mido.Message('note_off', note=midi_number, time=tick - now)
            messages.append(message)
            now = tick
        messages.append(mido.MetaMessage('end_of_track', time=_ticks(clip_length) - now))

        return mido.MidiFile(
            type=0, ticks_per_beat=TICKS_PER_BEAT, tracks=[mido.MidiTrack(messages)],
        )
