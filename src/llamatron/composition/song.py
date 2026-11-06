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

"""The song: everything a song file holds, as objects that save and load themselves."""

from llamatron.composition.chain import Chain
from llamatron.composition.checks import check_keys, live_octave, number, positive_length
from llamatron.composition.file_format import (
    DEFAULT_DRUM_OCTAVE, DEFAULT_LENGTH, DEFAULT_OCTAVE, DEFAULT_SEED, DEFAULT_TEMPO, GRANULARITIES, NAMED_GENERATORS,
)
from llamatron.composition.generator_settings import GENERATOR_SETTINGS
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.named_scale import NamedScale
from llamatron.composition.pattern import Pattern
from llamatron.composition.scene import Scene
from llamatron.composition.song_file_error import SongFileError
from llamatron.composition.track import Track

# The song's own settings, in the order they're written to a file.
SETTINGS = [
    'title', 'author', 'description', 'tempo', 'scale', 'seed', 'default_length', 'granularity',
    'default_octave', 'default_drum_octave',
]
# Its sections of named objects, in the order they're written to a file, before its scenes.
SECTIONS = ['scales', 'patterns', 'tracks', *NAMED_GENERATORS.values(), 'chains']


class Song(LlamaData):
    """The song the user composes: its settings, named scales, patterns, tracks, generators, chains and scenes.

    Settings the file leaves out are kept as None and mean their defaults, and so do sections it
    leaves out, so that saving writes back only what was there. Objects refer to each other by
    name, and the song looks the names up.
    """

    def __init__(self):
        self._settings = {name: None for name in SETTINGS}
        self._sections = {name: None for name in SECTIONS}
        self._scenes = None

    @classmethod
    def from_data(cls, data, where='the file', song=None):
        """Read a whole song file's data, checking every part of it, in the order the file is read."""
        # Every setting has a default, so an empty file is an empty song.
        data = {} if data is None else data
        if not isinstance(data, dict):
            raise SongFileError('a song file must have settings like tempo, scale and scenes')
        check_keys(data, where, {*SETTINGS, *SECTIONS, 'scenes'})
        song = cls()
        song._read_settings(data)
        song._read_section(data, 'patterns', Pattern, 'pattern')
        song._read_tracks(data)
        for section in NAMED_GENERATORS.values():
            song._read_generators(data, section)
        song._read_section(data, 'chains', Chain, 'chain')
        song._read_scenes(data)
        return song

    def _read_settings(self, data):
        # The title, author and description are only for people reading or sharing the file.
        for key in ('title', 'author', 'description'):
            if not isinstance(data.get(key, ''), str):
                raise SongFileError(f'{key} must be text, got {data[key]!r}')
        number(data.get('tempo', DEFAULT_TEMPO), 'tempo')
        scales = data.get('scales') or {}
        if not isinstance(scales, dict):
            raise SongFileError('scales: expected named scales like main: { root: F, type: minor }')
        self._sections['scales'] = None if 'scales' not in data else {
            name: NamedScale.from_data(scale, f'scale {name!r}', self) for name, scale in scales.items()
        }
        if data.get('scale') is not None and not self.has_scale(data['scale']):
            raise SongFileError(f'scale: no scale called {data["scale"]!r}')
        positive_length(data.get('default_length', DEFAULT_LENGTH), 'default_length')
        granularity = data.get('granularity', GRANULARITIES[0])
        if granularity not in GRANULARITIES:
            raise SongFileError(f'granularity must be one of {GRANULARITIES}, got {granularity!r}')
        live_octave(data.get('default_octave', DEFAULT_OCTAVE), 'default_octave')
        live_octave(data.get('default_drum_octave', DEFAULT_DRUM_OCTAVE), 'default_drum_octave')
        self._settings = {name: data.get(name) for name in SETTINGS}

    def _read_section(self, data, section, kind, label):
        """Read a section of named objects, like patterns, naming each one in any error."""
        if section in data:
            self._sections[section] = {
                name: kind.from_data(item, f'{label} {name!r}', self) for name, item in (data[section] or {}).items()
            }

    def _read_tracks(self, data):
        tracks = data.get('tracks') or {}
        if not isinstance(tracks, dict):
            raise SongFileError('tracks: expected named tracks with their settings, like lead: { transpose: 2 }')
        if 'tracks' in data:
            self._sections['tracks'] = {name: Track.from_data(settings, f'track {name!r}', self) for name, settings in tracks.items()}

    def _read_generators(self, data, section):
        kind = next(kind for kind, named in NAMED_GENERATORS.items() if named == section)
        generators = data.get(section) or {}
        if not isinstance(generators, dict):
            raise SongFileError(f'{section}: expected named settings, like bells: {{ step: 1/8 }}')
        if section in data:
            self._sections[section] = {
                name: GENERATOR_SETTINGS[kind].from_data(settings, f'{kind} {name!r}', self) for name, settings in generators.items()
            }

    def _read_scenes(self, data):
        scenes = data.get('scenes') or []
        if not isinstance(scenes, list):
            raise SongFileError('scenes: expected a list of scenes')
        self._scenes = None if 'scenes' not in data else [
            Scene.from_data(scene, f'scene entry {index}', self) for index, scene in enumerate(scenes, start=1)
        ]

    def to_data(self):
        data = {name: value for name, value in self._settings.items() if value is not None}
        for section, items in self._sections.items():
            if items is not None:
                data[section] = {name: item.to_data() for name, item in items.items()}
        if self._scenes is not None:
            data['scenes'] = [scene.to_data() for scene in self._scenes]
        return data

    # The song's settings, with their defaults.

    def get_tempo(self):
        """Return the song's tempo in quarter notes a minute, as an exact number."""
        return number(self._settings['tempo'] if self._settings['tempo'] is not None else DEFAULT_TEMPO, 'tempo')

    def get_seed(self):
        return DEFAULT_SEED if self._settings['seed'] is None else self._settings['seed']

    def get_default_length(self):
        """Return how long a step with no duration lasts, in whole notes."""
        length = self._settings['default_length']
        return positive_length(DEFAULT_LENGTH if length is None else length, 'default_length')

    def get_default_octave(self):
        octave = self._settings['default_octave']
        return DEFAULT_OCTAVE if octave is None else octave

    def get_default_drum_octave(self):
        octave = self._settings['default_drum_octave']
        return DEFAULT_DRUM_OCTAVE if octave is None else octave

    def get_scale_name(self):
        """Return the name of the song's scale, or None if it has none."""
        return self._settings['scale']

    # Looking up the song's named objects.

    def _named(self, section):
        return self._sections[section] or {}

    def has_scale(self, name):
        return name in self._named('scales')

    def get_named_scale(self, name):
        return self._named('scales')[name]

    def has_pattern(self, name):
        return name in self._named('patterns')

    def get_pattern(self, name):
        return self._named('patterns')[name]

    def has_track(self, name):
        return name in self._named('tracks')

    def get_track(self, name):
        return self._named('tracks')[name]

    def get_track_names(self):
        """Return the names of the tracks, in the song's order."""
        return list(self._named('tracks'))

    def has_generator(self, kind, name):
        """Return whether there's a generator of a kind, like arp, with this name."""
        return name in self._named(NAMED_GENERATORS[kind])

    def get_generator_settings(self, kind, name):
        return self._named(NAMED_GENERATORS[kind])[name]

    def has_chain(self, name):
        return name in self._named('chains')

    def get_chain(self, name):
        return self._named('chains')[name]

    def get_scenes(self):
        """Return the scenes in the order they play."""
        return list(self._scenes or [])
