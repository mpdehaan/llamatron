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

import re
from dataclasses import dataclass, replace
from fractions import Fraction
from itertools import count
from math import isfinite

from llamatron.chord import Chord
from llamatron.note import Degree, Note, Rest, _check_length
from llamatron.scale import Scale

MIN_TEMPO = 10
DEFAULT_TEMPO = 120

# The objects that a clip's list of notes can hold.
POSITION_TYPES = (Note, Chord, Rest, Degree)

_QUARTER_NOTE = 0.25
_NOTE_TEXT = re.compile(r'([A-G][#b]?)(\d+)')

_next_clip_id = count(0)


def exact_length(length):
    """Return a length as an exact fraction.

    Lengths like 1/12 are slightly inexact as floats, so without this, three of them
    would fall just short of a quarter note and leave a tiny extra note or rest.
    """
    return Fraction(length).limit_denominator(1_000_000)


def cut_position(position, length):
    """Return a position that lasts no longer than length."""
    if exact_length(position.length) <= length:
        return position
    if isinstance(position, Chord):
        return Chord([cut_position(note, length) for note in position.notes])
    return replace(position, length=length)


def fit_to_length(positions, length):
    """Return positions that last exactly length, cutting notes off or adding a final rest."""
    result = []
    remaining = exact_length(length)
    for position in positions:
        if remaining <= 0:
            break
        result.append(cut_position(position, remaining))
        remaining -= min(exact_length(position.length), remaining)
    if remaining > 0:
        result.append(Rest(remaining))
    return result


def _piece_of(position, offset, length):
    """Return the part of a position that starts offset into it and lasts length."""
    if isinstance(position, Rest):
        return Rest(length)
    if isinstance(position, Chord):
        pieces = [
            _piece_of(note, offset, length) for note in position.notes
            if exact_length(note.length) > offset
        ]
        return Chord(pieces) if pieces else Rest(length)
    return replace(position, length=min(exact_length(position.length) - offset, length))


def _to_position(value):
    """Turn shorthand for a clip into an object: 'E4' is a Note, 3 is a Degree and '--' is a Rest."""
    if isinstance(value, POSITION_TYPES):
        return value
    # bool is a subclass of int, but True is not a real degree.
    if type(value) is int:
        return Degree(value)
    if isinstance(value, str):
        if value and set(value) == {'-'}:
            return Rest(len(value) * _QUARTER_NOTE)
        match = _NOTE_TEXT.fullmatch(value)
        if match:
            return Note(match[1], int(match[2]))
    raise ValueError(f'expected a Note, Chord, Rest, Degree or shorthand for one, got {value!r}')


def _check_name(name):
    if name is not None and not isinstance(name, str):
        raise ValueError(f'invalid name: {name!r}')


def _check_tempo(tempo):
    # bool is a subclass of int, but True is not a real tempo.
    if type(tempo) not in (int, float) or not isfinite(tempo) or tempo < MIN_TEMPO:
        raise ValueError(f'invalid tempo: {tempo!r} (must be a number of at least {MIN_TEMPO})')


def _check_tempo_override(tempo):
    if tempo is not None:
        _check_tempo(tempo)


def _check_scale(scale):
    if scale is not None and not isinstance(scale, Scale):
        raise ValueError(f'expected a Scale, got {scale!r}')


def _check_loop(loop):
    if type(loop) is not bool:
        raise ValueError(f'invalid loop: {loop!r} (must be True or False)')


def _check_mute(mute):
    if type(mute) is not bool:
        raise ValueError(f'invalid mute: {mute!r} (must be True or False)')


def _check_clip_length(length):
    if length is not None:
        _check_length(length)


class _Validated:
    """An editable attribute that runs a check every time it's assigned."""

    def __init__(self, check):
        self._check = check

    def __set_name__(self, owner, name):
        self._storage_name = f'_{name}'

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return getattr(instance, self._storage_name)

    def __set__(self, instance, value):
        self._check(value)
        setattr(instance, self._storage_name, value)


class Track:
    """A column of the song's grid. Its id is None unless it's in a song.

    A muted track still has its clips, so a renderer writes them, but Live starts with the
    track switched off. It's for tracks that other tracks grab notes from.
    """

    name = _Validated(_check_name)
    mute = _Validated(_check_mute)

    def __init__(self, name=None, mute=False):
        self._id = None
        self.name = name
        self.mute = mute

    @property
    def id(self):
        return self._id

    def __repr__(self):
        return f'Track(name={self.name!r}, mute={self.mute!r}, id={self.id!r})'


class Scene:
    """A row of the song's grid. Its id is None unless it's in a song.

    A tempo or scale of None uses the song's.
    """

    name = _Validated(_check_name)
    tempo = _Validated(_check_tempo_override)
    scale = _Validated(_check_scale)

    def __init__(self, name=None, tempo=None, scale=None):
        self._id = None
        self.name = name
        self.tempo = tempo
        self.scale = scale

    @property
    def id(self):
        return self._id

    def __repr__(self):
        return (
            f'Scene(name={self.name!r}, tempo={self.tempo!r}, '
            f'scale={self.scale!r}, id={self.id!r})'
        )


@dataclass(frozen=True)
class Control:
    """A MIDI CC value sent at a time in a clip, in fractions of a whole note from its start.

    With slide, the value ramps to the next value for the same number instead of holding.
    """

    time: Fraction
    number: int
    value: int
    slide: bool = False

    def __post_init__(self):
        if exact_length(self.time) < 0:
            raise ValueError(f'invalid time: {self.time!r} (must not be negative)')
        for name in ('number', 'value'):
            item = getattr(self, name)
            if type(item) is not int or not 0 <= item <= 127:
                raise ValueError(f'invalid {name}: {item!r} (must be a whole number from 0 to 127)')
        if type(self.slide) is not bool:
            raise ValueError(f'invalid slide: {self.slide!r} (must be True or False)')


class Clip:
    """One cell of the song's grid: a list of notes, chords, rests and degrees played in order.

    The list can use shorthand: 'E4' is a Note, 3 is a Degree, and each dash is a
    quarter note of rest, so '--' is a half rest. Notes and degrees without their own
    length use note_length, and degrees use whichever scale applies when rendered.

    A length of None ends the clip after the last position. Otherwise the clip is
    exactly that long, adding silence or cutting off notes to fit. Like note
    lengths, it's a fraction of a whole note, so 1 is a whole note or four quarters.
    A scale of None uses the scene's or song's. Clips have no tempo of their own. Loop
    is whether Live plays the clip again when it reaches its end. Controls are the MIDI CC
    values it sends, which generators keep, and sections and repeats cut and repeat with the
    notes.
    """

    name = _Validated(_check_name)
    scale = _Validated(_check_scale)
    length = _Validated(_check_clip_length)
    note_length = _Validated(_check_clip_length)
    loop = _Validated(_check_loop)

    def __init__(self, name=None, notes=None, scale=None, length=None, note_length=None, loop=True, controls=None):
        self._id = next(_next_clip_id)
        self.name = name
        self.notes = [] if notes is None else notes
        self.scale = scale
        self.length = length
        self.note_length = note_length
        self.loop = loop
        self.controls = [] if controls is None else controls

    @property
    def controls(self):
        return self._controls

    @controls.setter
    def controls(self, controls):
        if not isinstance(controls, (list, tuple)) or not all(isinstance(item, Control) for item in controls):
            raise ValueError(f'expected a list of Controls, got {controls!r}')
        self._controls = sorted(controls, key=lambda item: item.time)

    @property
    def id(self):
        return self._id

    @property
    def notes(self):
        return self._notes

    @notes.setter
    def notes(self, notes):
        if not isinstance(notes, (list, tuple)):
            raise ValueError(f'expected a list of notes, chords and rests, got {notes!r}')
        # This makes a new list, so that clips built from the same list don't share it.
        self._notes = [_to_position(position) for position in notes]

    def resolved_notes(self):
        """Return the notes with every missing length filled in from note_length.

        Raises ValueError if a length is missing and there's no note_length. Degrees
        stay as degrees, because they don't become notes until they're rendered.
        """
        return [self._with_length(position) for position in self._notes]

    def _with_length(self, position):
        if isinstance(position, Chord):
            return Chord([self._with_length(note) for note in position.notes])
        if not isinstance(position, (Note, Degree)) or position.length is not None:
            return position
        if self.note_length is None:
            raise ValueError(f'{position!r} has no length, and the clip has no note_length')
        return replace(position, length=self.note_length)

    def played_notes(self):
        """Return resolved notes that fill the clip's set length, if it has one."""
        positions = self.resolved_notes()
        return positions if self.length is None else fit_to_length(positions, self.length)

    def total_length(self):
        """Return how long the clip lasts, as an exact fraction of a whole note."""
        if self.length is not None:
            return exact_length(self.length)
        return sum((exact_length(position.length) for position in self.resolved_notes()), Fraction(0))

    def section(self, start, end):
        """Return a new Clip of the part from start to end, in fractions of a whole note.

        A note that crosses either edge is cut, so its second half plays as a new note.
        Anything past the end of the clip becomes silence, so the result always lasts
        exactly end minus start.
        """
        start, end = exact_length(start), exact_length(end)
        if start < 0 or end <= start:
            raise ValueError(f'invalid section: from {start} to {end}')
        notes = []
        position_start = Fraction(0)
        for position in self.played_notes():
            position_end = position_start + exact_length(position.length)
            piece_start, piece_end = max(position_start, start), min(position_end, end)
            if piece_end > piece_start:
                notes.append(_piece_of(position, piece_start - position_start, piece_end - piece_start))
            position_start = position_end
        if position_start < end:
            notes.append(Rest(end - max(position_start, start)))
        controls = [replace(item, time=item.time - start) for item in self._controls if start <= item.time < end]
        return Clip(name=self.name, notes=notes, scale=self.scale, note_length=self.note_length, controls=controls)

    def repeated(self, times):
        """Return a new Clip that plays this one times in a row, so it lasts times as long."""
        if type(times) is not int or times < 1:
            raise ValueError(f'invalid times: {times!r} (must be a positive integer)')
        length = self.total_length()
        controls = [replace(item, time=item.time + length * place) for place in range(times) for item in self._controls]
        return Clip(
            name=self.name, notes=self.played_notes() * times, scale=self.scale,
            note_length=self.note_length, controls=controls,
        )

    def __repr__(self):
        return (
            f'Clip(name={self.name!r}, notes={self.notes!r}, scale={self.scale!r}, '
            f'length={self.length!r}, note_length={self.note_length!r}, id={self.id!r})'
        )


class Song:
    """A grid of clips, with one cell for each combination of scene and track."""

    tempo = _Validated(_check_tempo)
    scale = _Validated(_check_scale)

    def __init__(self, tempo=DEFAULT_TEMPO, scale=None):
        self.tempo = tempo
        self.scale = scale
        self._tracks = {}
        self._scenes = {}
        self._next_track_id = count(0)
        self._next_scene_id = count(0)
        # Nested as {scene id: {track id: clip}}. Empty cells have no entry.
        self._clips = {}

    @property
    def tracks(self):
        """A list of the tracks, in the order they were added."""
        return list(self._tracks.values())

    @property
    def scenes(self):
        """A list of the scenes, in the order they were added."""
        return list(self._scenes.values())

    def add_track(self, track):
        """Add a Track to the song, give it its id and return it."""
        if not isinstance(track, Track):
            raise ValueError(f'expected a Track, got {track!r}')
        if track.id is not None:
            raise ValueError(f'track is already in a song: {track!r}')
        track._id = next(self._next_track_id)
        self._tracks[track.id] = track
        return track

    def add_scene(self, scene):
        """Add a Scene to the song, give it its id and return it."""
        if not isinstance(scene, Scene):
            raise ValueError(f'expected a Scene, got {scene!r}')
        if scene.id is not None:
            raise ValueError(f'scene is already in a song: {scene!r}')
        scene._id = next(self._next_scene_id)
        self._scenes[scene.id] = scene
        return scene

    def set_clip(self, scene, track, clip):
        """Put a Clip in a cell, replacing any clip already there, and return it."""
        self._check_cell(scene, track)
        if not isinstance(clip, Clip):
            raise ValueError(f'expected a Clip, got {clip!r}')
        self._clips.setdefault(scene.id, {})[track.id] = clip
        return clip

    def get_clip(self, scene, track):
        """Return the Clip in a cell, or None if the cell is empty."""
        self._check_cell(scene, track)
        return self._clips.get(scene.id, {}).get(track.id)

    def tempo_at(self, scene):
        """Return the tempo for a scene: its own if it has one, else the song's."""
        self._check_scene(scene)
        return self.tempo if scene.tempo is None else scene.tempo

    def scale_at(self, scene, track):
        """Return the scale for a cell: its clip's, else its scene's, else the song's.

        Returns None if none of them has a scale.
        """
        # An empty cell has no clip, and getattr then gives None for that step.
        for part in (self.get_clip(scene, track), scene, self):
            scale = getattr(part, 'scale', None)
            if scale is not None:
                return scale
        return None

    def _check_track(self, track):
        if not isinstance(track, Track) or self._tracks.get(track.id) is not track:
            raise ValueError(f'track is not in this song: {track!r}')

    def _check_scene(self, scene):
        if not isinstance(scene, Scene) or self._scenes.get(scene.id) is not scene:
            raise ValueError(f'scene is not in this song: {scene!r}')

    def _check_cell(self, scene, track):
        self._check_scene(scene)
        self._check_track(track)
