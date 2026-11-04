from dataclasses import dataclass, field
from itertools import count
from math import isfinite

DEFAULT_TEMPO = 120

_next_id = count(1)


def _new_id():
    return next(_next_id)


def _check_name(name):
    if name is not None and not isinstance(name, str):
        raise ValueError(f'invalid name: {name!r}')


def _check_tempo(tempo):
    # bool is a subclass of int, but True is not a real tempo.
    if type(tempo) not in (int, float) or not isfinite(tempo) or tempo <= 0:
        raise ValueError(f'invalid tempo: {tempo!r} (must be a positive number)')


@dataclass(frozen=True, eq=False)
class Track:
    """A column of the song's grid. Names don't have to be unique, but ids are."""

    name: str = None
    id: int = field(init=False, default_factory=_new_id)

    def __post_init__(self):
        _check_name(self.name)


@dataclass(frozen=True, eq=False)
class Scene:
    """A row of the song's grid. A tempo of None means it uses the song's tempo."""

    name: str = None
    tempo: float = None
    id: int = field(init=False, default_factory=_new_id)

    def __post_init__(self):
        _check_name(self.name)
        if self.tempo is not None:
            _check_tempo(self.tempo)


@dataclass(frozen=True, eq=False)
class Clip:
    """One cell of the song's grid. A tempo of None means it doesn't override the tempo."""

    name: str = None
    tempo: float = None

    def __post_init__(self):
        _check_name(self.name)
        if self.tempo is not None:
            _check_tempo(self.tempo)


class Song:
    """A grid of clips, with one cell for each combination of scene and track."""

    def __init__(self, tempo=DEFAULT_TEMPO):
        _check_tempo(tempo)
        self._tempo = tempo
        self._tracks = {}
        self._scenes = {}
        # Nested as {scene id: {track id: clip}}. Empty cells have no entry.
        self._clips = {}

    @property
    def tempo(self):
        return self._tempo

    @property
    def tracks(self):
        """A list of the tracks, in the order they were added."""
        return list(self._tracks.values())

    @property
    def scenes(self):
        """A list of the scenes, in the order they were added."""
        return list(self._scenes.values())

    def add_track(self, track):
        """Add a Track to the song and return it."""
        if not isinstance(track, Track):
            raise ValueError(f'expected a Track, got {track!r}')
        if track.id in self._tracks:
            raise ValueError(f'track is already in this song: {track!r}')
        self._tracks[track.id] = track
        return track

    def add_scene(self, scene):
        """Add a Scene to the song and return it."""
        if not isinstance(scene, Scene):
            raise ValueError(f'expected a Scene, got {scene!r}')
        if scene.id in self._scenes:
            raise ValueError(f'scene is already in this song: {scene!r}')
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

    def remove_clip(self, scene, track):
        """Empty a cell. Does nothing if the cell is already empty."""
        self._check_cell(scene, track)
        clips_in_scene = self._clips.get(scene.id, {})
        clips_in_scene.pop(track.id, None)
        if not clips_in_scene:
            self._clips.pop(scene.id, None)

    def tempo_at(self, scene, track):
        """Return the tempo for a cell: its clip's, else its scene's, else the song's."""
        self._check_cell(scene, track)
        clip = self.get_clip(scene, track)
        if clip is not None and clip.tempo is not None:
            return clip.tempo
        if scene.tempo is not None:
            return scene.tempo
        return self._tempo

    def _check_cell(self, scene, track):
        if not isinstance(scene, Scene) or self._scenes.get(scene.id) is not scene:
            raise ValueError(f'scene is not in this song: {scene!r}')
        if not isinstance(track, Track) or self._tracks.get(track.id) is not track:
            raise ValueError(f'track is not in this song: {track!r}')
