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

"""A song as it plays: every track's notes laid end to end across the song, in beats from its start, with the tempo and the
time signature it plays at. Made from a song by rendering it, each clip's timed notes placed at its scene's start as the
exporters place them; nothing else about the set is kept, so the measures can't lean on its layout."""

from dataclasses import dataclass

from llamatron.exporters.timing import timed_events
from llamatron.playback.song_renderer import SongRenderer

# A whole note's beats when the beat is a quarter note, which every measure counts in.
QUARTERS_IN_A_WHOLE = 4


@dataclass(slots=True, kw_only=True, frozen=True)
class PlayedNote:
    """One note as it sounds: its start and end in beats from the song's start, exact, its MIDI number and its velocity, with
    the start and end as floats too (begins and ends), converted once, since the measures are statistics."""

    start: object
    end: object
    pitch: int
    velocity: int
    begins: float = None
    ends: float = None

    def __post_init__(self):
        if self.begins is None:
            object.__setattr__(self, 'begins', float(self.start))
            object.__setattr__(self, 'ends', float(self.end))

    def length(self):
        return self.ends - self.begins


@dataclass(slots=True, kw_only=True, frozen=True)
class PlayedTrack:
    """A track as it sounds: its name, whether it's drums, its General MIDI sound if it has one, and its notes in time order."""

    name: str
    drum: bool
    sound: int
    notes: tuple


@dataclass(slots=True, kw_only=True, frozen=True)
class Performance:
    """A whole song as it sounds: its tracks, its tempo (the one it plays at longest), its time signature, its beats in a bar,
    its length in beats, both exact, and the beat each scene starts on, which the render knows, for judging the changes from
    one scene to the next without guessing sections. A song read from a MIDI file also knows how long it lasts in seconds, by
    every tempo it passes through, and what was doubtful about its parts, as sentences."""

    tracks: tuple
    tempo: int
    meter: str
    beats_per_bar: object
    length: object
    scene_starts: tuple = ()
    seconds: float = None
    doubts: tuple = ()

    def bars(self):
        return max(1, round(float(self.length / self.beats_per_bar)))

    def bar_of(self, time):
        """Return the bar a time in beats falls in, counted from 0."""
        return int(time // float(self.beats_per_bar))

    def melodic(self):
        return [track for track in self.tracks if not track.drum and track.notes]

    def drums(self):
        return [track for track in self.tracks if track.drum and track.notes]


def performance_of(song, *, seed=None):
    """Return how a song plays, rendered through its objects: each unmuted track's notes, placed at their scenes' starts."""
    grid = SongRenderer(song, seed=seed).render()
    starts = grid.row_starts()
    tracks = []
    for column in grid.get_columns():
        if column.get_mute():
            continue
        notes = []
        for row, start in zip(grid.get_rows(), starts):
            clip = grid.get_clip(row=row, column=column)
            if clip is None:
                continue
            events, _ = timed_events(clip=clip, scale=grid.scale_at(row=row, column=column))
            notes += [PlayedNote(start=(start + event.start) * QUARTERS_IN_A_WHOLE, end=(start + event.end) * QUARTERS_IN_A_WHOLE,
                                 pitch=event.midi_number, velocity=event.velocity) for event in events if event.end > event.start]
        notes.sort(key=lambda note: (note.start, note.pitch))
        tracks.append(PlayedTrack(name=column.get_name(), drum=column.is_drum(), sound=column.get_gm_sound(), notes=tuple(notes)))
    signature = grid.get_time_signature()
    beats_per_bar = signature.bar_length() * QUARTERS_IN_A_WHOLE
    return Performance(tracks=tuple(tracks), tempo=longest_tempo(grid=grid, starts=starts), meter=signature.to_text(), beats_per_bar=beats_per_bar,
                       length=grid.song_length() * QUARTERS_IN_A_WHOLE, scene_starts=tuple(float(start * QUARTERS_IN_A_WHOLE) for start in starts))


def longest_tempo(*, grid, starts):
    """Return the tempo the song plays at for the longest time."""
    time_at = {}
    for row in grid.get_rows():
        tempo = grid.tempo_at(row)
        time_at[tempo] = time_at.get(tempo, 0) + float(grid.row_length(row))
    return max(time_at, key=time_at.get) if time_at else 0
