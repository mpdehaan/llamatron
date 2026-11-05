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
from src.note import Note, Rest
from src.renderers.clip_tree import BEATS_PER_WHOLE_NOTE, _check_directory
from src.song import Clip, Scene, Song, Track, _Validated

_FILENAME = re.compile(r'(\d+)-(\d+)(?:-(.+))?\.mid')


def _played_notes(midi_file):
    """Return a file's notes as (start tick, end tick, MIDI number), and its last tick and tempo."""
    notes = []
    started = {}
    tick = 0
    tempo = None
    for message in mido.merge_tracks(midi_file.tracks):
        tick += message.time
        if message.type == 'set_tempo' and tempo is None:
            tempo = round(mido.tempo2bpm(message.tempo), 3)
        elif message.type == 'note_on' and message.velocity > 0:
            if message.note in started:
                raise ValueError(f'note {message.note} starts again at tick {tick} before it ends')
            started[message.note] = tick
        elif message.type in ('note_on', 'note_off'):
            if message.note not in started:
                raise ValueError(f'note {message.note} ends at tick {tick} without starting')
            notes.append((started.pop(message.note), tick, message.note))
    if started:
        raise ValueError(f'these notes never end: {sorted(started)}')
    return sorted(notes), tick, tempo


def _load_clip(path, name):
    """Return a Clip from a MIDI file, and the file's tempo."""
    midi_file = mido.MidiFile(path)
    ticks_per_whole_note = midi_file.ticks_per_beat * BEATS_PER_WHOLE_NOTE
    notes, last_tick, tempo = _played_notes(midi_file)

    def length_of(ticks):
        return Fraction(ticks, ticks_per_whole_note)

    positions = []
    now = 0
    for start in sorted({note[0] for note in notes}):
        if start < now:
            raise ValueError(f'{path} has notes that overlap, which a clip cannot hold')
        if start > now:
            positions.append(Rest(length_of(start - now)))
        together = [
            Note.from_midi_number(midi_number, length_of(end - start))
            for note_start, end, midi_number in notes
            if note_start == start
        ]
        positions.append(together[0] if len(together) == 1 else Chord(together))
        now = max(note[1] for note in notes if note[0] == start)

    # Only silence after the last note needs a set length.
    length = length_of(last_tick) if last_tick != now and last_tick > 0 else None
    return Clip(name, notes=positions, length=length), tempo


class ClipTreeImporter:
    """Loads a directory of MIDI files written by the ClipTree renderer back into a Song.

    Scenes and tracks come from the <scene_id>-<track_id>-<clip_name>.mid file names, and
    get new ids counted from 0, so gaps in the numbering aren't kept. A file's tempo goes
    on its scene. MIDI doesn't store note spellings or the names of scenes and tracks, so
    notes are spelled with sharps and only clips have names. Notes that overlap without
    starting together raise ValueError, because a clip can't hold them.
    """

    directory = _Validated(_check_directory)

    def __init__(self, directory):
        self.directory = directory

    def load(self):
        """Return a new Song, ignoring anything in the directory not named like a clip."""
        slots = {}
        for filename in os.listdir(self.directory):
            match = _FILENAME.fullmatch(filename)
            if match:
                slot = (int(match[1]), int(match[2]))
                if slot in slots:
                    raise ValueError(f'{self.directory} has more than one file for slot {slot}')
                slots[slot] = (filename, match[3])

        song = Song()
        scenes = {scene_id: song.add_scene(Scene()) for scene_id in sorted({s for s, _ in slots})}
        tracks = {track_id: song.add_track(Track()) for track_id in sorted({t for _, t in slots})}

        for (scene_id, track_id), (filename, name) in sorted(slots.items()):
            path = os.path.join(self.directory, filename)
            clip, tempo = _load_clip(path, name)
            song.set_clip(scenes[scene_id], tracks[track_id], clip)
            if tempo is not None and scenes[scene_id].tempo is None:
                scenes[scene_id].tempo = tempo
        return song
