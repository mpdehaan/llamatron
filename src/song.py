from itertools import count
from math import isfinite

from src.chord import Chord
from src.note import Note, Rest, _check_length
from src.scale import Scale

MIN_TEMPO = 10
DEFAULT_TEMPO = 120

_next_clip_id = count(0)


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
    """A column of the song's grid. Its id is None unless it's in a song."""

    name = _Validated(_check_name)

    def __init__(self, name=None):
        self._id = None
        self.name = name

    @property
    def id(self):
        return self._id

    def __repr__(self):
        return f'Track(name={self.name!r}, id={self.id!r})'


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


class Clip:
    """One cell of the song's grid: a list of notes, chords and rests played in order.

    A length of None ends the clip after the last position. Otherwise the clip is
    exactly that long, adding silence or cutting off notes to fit. Like note
    lengths, it's a fraction of a whole note, so 1 is a whole note or four quarters.
    A scale of None uses the scene's or song's. Clips have no tempo of their own.
    """

    name = _Validated(_check_name)
    scale = _Validated(_check_scale)
    length = _Validated(_check_clip_length)

    def __init__(self, name=None, notes=None, scale=None, length=None):
        self._id = next(_next_clip_id)
        self.name = name
        self.notes = [] if notes is None else notes
        self.scale = scale
        self.length = length

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
        for position in notes:
            if not isinstance(position, (Note, Chord, Rest)):
                raise ValueError(f'expected a Note, Chord or Rest, got {position!r}')
        # Copied so that clips built from the same list don't share it.
        self._notes = list(notes)

    def __repr__(self):
        return (
            f'Clip(name={self.name!r}, notes={self.notes!r}, scale={self.scale!r}, '
            f'length={self.length!r}, id={self.id!r})'
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

    def remove_track(self, track):
        """Remove a Track and its clips. Its id isn't reused, and its own id becomes None."""
        self._check_track(track)
        for scene_id in list(self._clips):
            self._clips[scene_id].pop(track.id, None)
            if not self._clips[scene_id]:
                del self._clips[scene_id]
        del self._tracks[track.id]
        track._id = None

    def remove_scene(self, scene):
        """Remove a Scene and its clips. Its id isn't reused, and its own id becomes None."""
        self._check_scene(scene)
        self._clips.pop(scene.id, None)
        del self._scenes[scene.id]
        scene._id = None

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

    def remove_clip(self, scene, track):
        """Empty a cell. Does nothing if the cell is already empty."""
        self._check_cell(scene, track)
        clips_in_scene = self._clips.get(scene.id, {})
        clips_in_scene.pop(track.id, None)
        if not clips_in_scene:
            self._clips.pop(scene.id, None)

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
