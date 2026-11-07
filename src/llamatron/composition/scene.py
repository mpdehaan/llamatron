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

"""A scene: a row of the song, launching one cell on each track that has one."""

from fractions import Fraction

from llamatron.composition.cell import Cell
from llamatron.composition.checks import check_keys, is_whole_number_from, number, reading
from llamatron.composition.defaults import DEFAULT_REPEAT
from llamatron.composition.file_format import REGISTER_NAMES, SceneSetting
from llamatron.composition.limits import MIN_REPEAT
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.invalid_value import InvalidValue

MSG_EXPECTED_SETTINGS = 'expected settings like name and tracks'
MSG_BAD_REPEAT = 'repeat must be a positive whole number, got {value!r}'
MSG_NO_SUCH_TRACK = 'no track called {track!r}, expected one of {tracks}'
MSG_NO_SUCH_SCALE = 'no scale called {scale!r}'
MSG_RAMP_NEEDS_BOTH = 'needs both tempo_start and tempo_end'
MSG_BAD_RESET = 'reset must be a list of registers from {names}, like [AX, DX], got {value!r}'
# How far through a tempo ramp a scene that plays only once is: at its start.
NO_RAMP = 0
# A scene's settings, in the order they're written to a file, before its tracks.
SETTINGS = [
    SceneSetting.NAME, SceneSetting.REPEAT, SceneSetting.SCALE, SceneSetting.TEMPO,
    SceneSetting.TEMPO_START, SceneSetting.TEMPO_END, SceneSetting.RESET,
]


class Scene(LlamaData):
    """A name, how many times it repeats, an optional scale and tempo, and a cell for each track it plays.

    Settings the file leaves out are kept as None, meaning their defaults. Its scale is kept as
    the name of one of the song's scales.
    """

    __slots__ = ('_settings', '_cells')

    def __init__(self, cells=None, **settings):
        self._settings = {name: settings.get(name) for name in SETTINGS}
        self._cells = None if cells is None else dict(cells)

    @classmethod
    def from_data(cls, data, where, song=None):
        with reading(where):
            if not isinstance(data, dict):
                raise InvalidValue(MSG_EXPECTED_SETTINGS)
            check_keys(data, {*SETTINGS, SceneSetting.TRACKS})
            repeat = data.get(SceneSetting.REPEAT, DEFAULT_REPEAT)
            if not is_whole_number_from(repeat, MIN_REPEAT):
                raise InvalidValue(MSG_BAD_REPEAT.format(value=repeat))
            cells = {}
            for track, cell in (data.get(SceneSetting.TRACKS) or {}).items():
                if not song.has_track(track):
                    raise InvalidValue(MSG_NO_SUCH_TRACK.format(track=track, tracks=sorted(song.get_track_names())))
                cells[track] = Cell.from_data(cell, where, song, track=track)
            scale = data.get(SceneSetting.SCALE)
            if scale is not None and not song.has_scale(scale):
                raise InvalidValue(MSG_NO_SUCH_SCALE.format(scale=scale))
            _check_tempo(data)
            reset = data.get(SceneSetting.RESET, [])
            if not is_register_list(reset):
                raise InvalidValue(MSG_BAD_RESET.format(names=REGISTER_NAMES, value=reset))
            settings = {name: data[name] for name in SETTINGS if name in data}
            return cls(cells if SceneSetting.TRACKS in data else None, **settings)

    def to_data(self):
        data = {name: value for name, value in self._settings.items() if value is not None}
        if self._cells is not None:
            data[SceneSetting.TRACKS] = {track: cell.to_data() for track, cell in self._cells.items()}
        return data

    def get_name(self):
        """Return its name as the file gives it, or None if it has none."""
        return self._settings[SceneSetting.NAME]

    def get_repeat(self):
        repeat = self._settings[SceneSetting.REPEAT]
        return DEFAULT_REPEAT if repeat is None else repeat

    def get_scale_name(self):
        """Return the name of the scale it sets, or None to use the song's."""
        return self._settings[SceneSetting.SCALE]

    def get_tempo(self, place):
        """Return its tempo on one of its repeats, counted from 0, or None to use the song's.

        A scene with tempo_start and tempo_end ramps evenly between them across its repeats.
        """
        settings = self._settings
        if settings[SceneSetting.TEMPO] is not None:
            return number(settings[SceneSetting.TEMPO])
        if settings[SceneSetting.TEMPO_START] is None:
            return None
        start = number(settings[SceneSetting.TEMPO_START])
        end = number(settings[SceneSetting.TEMPO_END])
        return start + (end - start) * _ramp_fraction(place, self.get_repeat())

    def get_reset_names(self):
        """Return the registers it sets back to their defaults as it starts, in the order the registers come."""
        reset = self._settings[SceneSetting.RESET] or []
        return [name for name in REGISTER_NAMES if name in reset]

    def get_track_names(self):
        """Return the tracks it plays a cell on, in the order the file lists them."""
        return list(self._cells or {})

    def get_cell(self, track):
        """Return its cell for a track, or None if it plays nothing there."""
        return (self._cells or {}).get(track)


def is_register_list(value):
    """Return whether a value is a list of register names, each at most once."""
    return isinstance(value, list) and all(name in REGISTER_NAMES for name in value) and len(set(value)) == len(value)


def _check_tempo(data):
    """Refuse a tempo that isn't a number, or a ramp that doesn't give both its start and end."""
    if SceneSetting.TEMPO in data:
        number(data[SceneSetting.TEMPO])
    elif SceneSetting.TEMPO_START in data or SceneSetting.TEMPO_END in data:
        if SceneSetting.TEMPO_START not in data or SceneSetting.TEMPO_END not in data:
            raise InvalidValue(MSG_RAMP_NEEDS_BOTH)
        number(data[SceneSetting.TEMPO_START])
        number(data[SceneSetting.TEMPO_END])


def _ramp_fraction(place, repeat):
    """Return how far through a tempo ramp a repeat is, from 0 on the first to 1 on the last."""
    last_place = repeat - 1
    return Fraction(place, last_place) if last_place > 0 else NO_RAMP
