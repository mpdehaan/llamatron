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

import yaml

from llamatron.composition.chain import Chain
from llamatron.composition.checks import check_keys, live_octave, number, positive_length
from llamatron.composition.defaults import (
    DEFAULT_DRUM_OCTAVE, DEFAULT_GRANULARITY, DEFAULT_LENGTH, DEFAULT_OCTAVE, DEFAULT_SEED, DEFAULT_TEMPO, GRANULARITIES,
)
from llamatron.composition.file_format import NAMED_GENERATORS, Section, SongSetting
from llamatron.composition.generator_settings import GENERATOR_SETTINGS
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.named_scale import NamedScale
from llamatron.composition.pattern import Pattern
from llamatron.composition.scene import Scene
from llamatron.composition.song_file_error import SongFileError
from llamatron.composition.track import Track
from llamatron.version import is_version

# The song's own settings, in the order they're written to a file.
SETTINGS = [
    SongSetting.VERSION, SongSetting.TITLE, SongSetting.AUTHOR, SongSetting.DESCRIPTION, SongSetting.TEMPO, SongSetting.SCALE,
    SongSetting.SEED, SongSetting.DEFAULT_LENGTH, SongSetting.GRANULARITY, SongSetting.DEFAULT_OCTAVE,
    SongSetting.DEFAULT_DRUM_OCTAVE,
]
# Settings that are only text for people, like the title.
TEXT_SETTINGS = (SongSetting.TITLE, SongSetting.AUTHOR, SongSetting.DESCRIPTION)
# Its sections of named objects, in the order they're written to a file, before its scenes.
SECTIONS = [Section.SCALES, Section.PATTERNS, Section.TRACKS, *NAMED_GENERATORS.values(), Section.CHAINS]
# How error messages name the file as a whole, and one object in each section of named objects.
THE_FILE = 'the file'
ITEM_LABELS = {Section.PATTERNS: 'pattern', Section.CHAINS: 'chain'}
MSG_CANT_READ = "can't read {path}: {reason}"
MSG_NOT_YAML = "{path} isn't valid YAML: {problem}"
FILE_ENCODING = 'utf-8'
MSG_NOT_A_SONG = 'a song file must have settings like tempo, scale and scenes'
MSG_NOT_TEXT = '{name} must be text, got {value!r}'
MSG_BAD_VERSION = 'version: expected three whole numbers separated by dots, like 1.0.2, got {value!r}'
MSG_SCALES_NOT_NAMED = 'scales: expected named scales like main: { root: F, type: minor }'
MSG_NO_SUCH_SCALE = 'scale: no scale called {scale!r}'
MSG_BAD_GRANULARITY = 'granularity must be one of {choices}, got {value!r}'
MSG_TRACKS_NOT_NAMED = 'tracks: expected named tracks with their settings, like lead: { transpose: 2 }'
MSG_GENERATORS_NOT_NAMED = '{section}: expected named settings, like bells: {{ step: 1/8 }}'
MSG_SCENES_NOT_A_LIST = 'scenes: expected a list of scenes'
# How messages name an object in the file: a named one by its kind and name, and a scene by its place.
WHERE_NAMED = '{label} {name!r}'
WHERE_SCENE_ENTRY = 'scene entry {number}'
SCALE_LABEL, TRACK_LABEL = 'scale', 'track'
# Scenes are counted from 1 in messages, as they're shown.
FIRST_SCENE_NUMBER = 1
# What a text setting is when the file leaves it out.
NO_TEXT = ''


class Song(LlamaData):
    """The song the user composes: its settings, named scales, patterns, tracks, generators, chains and scenes.

    Settings the file leaves out are kept as None and mean their defaults, and so do sections it
    leaves out, so that saving writes back only what was there. Objects refer to each other by
    name, and the song looks the names up.
    """

    __slots__ = ('_settings', '_sections', '_scenes')

    def __init__(self):
        self._settings = {name: None for name in SETTINGS}
        self._sections = {name: None for name in SECTIONS}
        self._scenes = None

    @classmethod
    def read_file(cls, path):
        """Return the song in a song file, or raise SongFileError if it can't be read or something's wrong with it.

        The file is read with yaml.safe_load, which only ever makes plain data, so reading a file
        can never run code.
        """
        try:
            with open(path, encoding=FILE_ENCODING) as file:
                data = yaml.safe_load(file)
        except OSError as error:
            raise SongFileError(MSG_CANT_READ.format(path=path, reason=error.strerror)) from error
        except yaml.YAMLError as error:
            raise SongFileError(MSG_NOT_YAML.format(path=path, problem=error)) from error
        return cls.from_data(data)

    @classmethod
    def from_data(cls, data, where=THE_FILE, song=None):
        """Read a whole song file's data, checking every part of it, in the order the file is read."""
        # Every setting has a default, so an empty file is an empty song.
        data = {} if data is None else data
        if not isinstance(data, dict):
            raise SongFileError(MSG_NOT_A_SONG)
        check_keys(data, where, {*SETTINGS, *SECTIONS, Section.SCENES})
        song = cls()
        song._read_settings(data)
        song._read_section(data, Section.PATTERNS, Pattern)
        song._read_tracks(data)
        for kind, section in NAMED_GENERATORS.items():
            song._read_generators(data, kind, section)
        song._read_section(data, Section.CHAINS, Chain)
        song._read_scenes(data)
        return song

    def _read_settings(self, data):
        # The title, author and description are only for people reading or sharing the file.
        for name in TEXT_SETTINGS:
            if not isinstance(data.get(name, NO_TEXT), str):
                raise SongFileError(MSG_NOT_TEXT.format(name=name, value=data[name]))
        # The version of llamatron that wrote the file. Nothing depends on it yet, but it has to be one.
        if SongSetting.VERSION in data and not is_version(data[SongSetting.VERSION]):
            raise SongFileError(MSG_BAD_VERSION.format(value=data[SongSetting.VERSION]))
        number(data.get(SongSetting.TEMPO, DEFAULT_TEMPO), SongSetting.TEMPO)
        scales = data.get(Section.SCALES) or {}
        if not isinstance(scales, dict):
            raise SongFileError(MSG_SCALES_NOT_NAMED)
        self._sections[Section.SCALES] = None if Section.SCALES not in data else {
            name: NamedScale.from_data(scale, WHERE_NAMED.format(label=SCALE_LABEL, name=name), self) for name, scale in scales.items()
        }
        scale = data.get(SongSetting.SCALE)
        if scale is not None and not self.has_scale(scale):
            raise SongFileError(MSG_NO_SUCH_SCALE.format(scale=scale))
        positive_length(data.get(SongSetting.DEFAULT_LENGTH, DEFAULT_LENGTH), SongSetting.DEFAULT_LENGTH)
        granularity = data.get(SongSetting.GRANULARITY, DEFAULT_GRANULARITY)
        if granularity not in GRANULARITIES:
            raise SongFileError(MSG_BAD_GRANULARITY.format(choices=GRANULARITIES, value=granularity))
        live_octave(data.get(SongSetting.DEFAULT_OCTAVE, DEFAULT_OCTAVE), SongSetting.DEFAULT_OCTAVE)
        live_octave(data.get(SongSetting.DEFAULT_DRUM_OCTAVE, DEFAULT_DRUM_OCTAVE), SongSetting.DEFAULT_DRUM_OCTAVE)
        self._settings = {name: data.get(name) for name in SETTINGS}

    def _read_section(self, data, section, kind):
        """Read a section of named objects, like patterns, naming each one in any error."""
        if section in data:
            label = ITEM_LABELS[section]
            self._sections[section] = {
                name: kind.from_data(item, WHERE_NAMED.format(label=label, name=name), self) for name, item in (data[section] or {}).items()
            }

    def _read_tracks(self, data):
        tracks = data.get(Section.TRACKS) or {}
        if not isinstance(tracks, dict):
            raise SongFileError(MSG_TRACKS_NOT_NAMED)
        if Section.TRACKS in data:
            self._sections[Section.TRACKS] = {name: Track.from_data(settings, WHERE_NAMED.format(label=TRACK_LABEL, name=name), self) for name, settings in tracks.items()}

    def _read_generators(self, data, kind, section):
        generators = data.get(section) or {}
        if not isinstance(generators, dict):
            raise SongFileError(MSG_GENERATORS_NOT_NAMED.format(section=section))
        if section in data:
            self._sections[section] = {
                name: GENERATOR_SETTINGS[kind].from_data(settings, WHERE_NAMED.format(label=kind, name=name), self) for name, settings in generators.items()
            }

    def _read_scenes(self, data):
        scenes = data.get(Section.SCENES) or []
        if not isinstance(scenes, list):
            raise SongFileError(MSG_SCENES_NOT_A_LIST)
        self._scenes = None if Section.SCENES not in data else [
            Scene.from_data(scene, WHERE_SCENE_ENTRY.format(number=number), self)
            for number, scene in enumerate(scenes, start=FIRST_SCENE_NUMBER)
        ]

    def to_data(self):
        data = {name: value for name, value in self._settings.items() if value is not None}
        for section, items in self._sections.items():
            if items is not None:
                data[section] = {name: item.to_data() for name, item in items.items()}
        if self._scenes is not None:
            data[Section.SCENES] = [scene.to_data() for scene in self._scenes]
        return data

    # The song's settings, with their defaults.

    def get_tempo(self):
        """Return the song's tempo in quarter notes a minute, as an exact number."""
        return number(self._setting(SongSetting.TEMPO, DEFAULT_TEMPO), SongSetting.TEMPO)

    def get_seed(self):
        return self._setting(SongSetting.SEED, DEFAULT_SEED)

    def get_default_length(self):
        """Return how long a step with no duration lasts, in whole notes."""
        return positive_length(self._setting(SongSetting.DEFAULT_LENGTH, DEFAULT_LENGTH), SongSetting.DEFAULT_LENGTH)

    def get_default_octave(self):
        return self._setting(SongSetting.DEFAULT_OCTAVE, DEFAULT_OCTAVE)

    def get_default_drum_octave(self):
        return self._setting(SongSetting.DEFAULT_DRUM_OCTAVE, DEFAULT_DRUM_OCTAVE)

    def get_scale_name(self):
        """Return the name of the song's scale, or None if it has none."""
        return self._settings[SongSetting.SCALE]

    def _setting(self, name, default):
        """Return one of the song's settings, or its default if the file leaves it out."""
        value = self._settings[name]
        return default if value is None else value

    # Looking up the song's named objects.

    def _named(self, section):
        return self._sections[section] or {}

    def has_scale(self, name):
        return name in self._named(Section.SCALES)

    def get_named_scale(self, name):
        return self._named(Section.SCALES)[name]

    def has_pattern(self, name):
        return name in self._named(Section.PATTERNS)

    def get_pattern(self, name):
        return self._named(Section.PATTERNS)[name]

    def has_track(self, name):
        return name in self._named(Section.TRACKS)

    def get_track(self, name):
        return self._named(Section.TRACKS)[name]

    def get_track_names(self):
        """Return the names of the tracks, in the song's order."""
        return list(self._named(Section.TRACKS))

    def has_generator(self, kind, name):
        """Return whether there's a generator of a kind, like arp, with this name."""
        return name in self._named(NAMED_GENERATORS[kind])

    def get_generator_settings(self, kind, name):
        return self._named(NAMED_GENERATORS[kind])[name]

    def has_chain(self, name):
        return name in self._named(Section.CHAINS)

    def get_chain(self, name):
        return self._named(Section.CHAINS)[name]

    def get_scenes(self):
        """Return the scenes in the order they play."""
        return list(self._scenes or [])
