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

"""A cell: what one track plays in one scene, which is a clip in Live.

It's called a cell here, as in the file format, to keep it apart from the finished Clip that
it renders into.
"""

from llamatron.composition.checks import check_keys, reading, is_true_or_false, is_whole_number_from
from llamatron.composition.defaults import DEFAULT_REPEAT
from llamatron.composition.file_format import CellSetting, Direction
from llamatron.composition.limits import MIN_REPEAT
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.pattern import check_direction
from llamatron.composition.invalid_value import InvalidValue
from llamatron.generators.blend import BlendMode

MORPH_STYLES = {member.name.lower(): member for member in BlendMode}
MSG_EXPECTED_SETTINGS = 'expected settings like {{ pattern: a }}, got {data!r}'
# How a cell is named in its messages: by its scene and its track.
WHERE_CELL = '{where}, track {track!r}'
MSG_NO_GRAB_TRACK = 'grab_track: no track called {name!r}'
MSG_GRABS_ITSELF = "grab_track: a clip can't grab from its own track"
MSG_BAD_REPEAT = 'repeat must be a positive whole number, got {value!r}'
MSG_LOOP_NOT_TRUE_OR_FALSE = 'loop must be true or false, got {value!r}'
MSG_NEEDS_PATTERN = 'needs a pattern'
MSG_NO_SUCH_PATTERN = 'no pattern called {name!r}'
MSG_NO_SUCH_CHAIN = 'no chain called {name!r}'
MSG_MORPH_NEEDS_BOTH = 'a morph needs both morph_to and morph_style'
MSG_MORPH_TOO_FEW_REPEATS = 'a morph needs a repeat of {lowest} or more'
MSG_BAD_MORPH_STYLE = 'morph_style must be one of {styles}, got {value!r}'
# A cell's settings, in the order they're written to a file.
SETTINGS = [
    CellSetting.PATTERN, CellSetting.CHAIN, CellSetting.LOOP, CellSetting.REPEAT, CellSetting.DIRECTION,
    CellSetting.MORPH_TO, CellSetting.MORPH_STYLE, CellSetting.GRAB_TRACK,
]
# A morph has to play its first pattern and its target, so it needs at least two repeats.
MIN_MORPH_REPEAT = 2


class Cell(LlamaData):
    """A pattern to play, and how: its chain, repeats or loop, direction, morph and grab.

    Settings the file leaves out are kept as None, meaning their defaults. The pattern, chain and
    other patterns and tracks are kept as names, and looked up when the song renders.
    """

    __slots__ = ('_settings',)

    def __init__(self, **settings):
        self._settings = {name: settings.get(name) for name in SETTINGS}

    @classmethod
    def from_data(cls, data, where, song=None, track=None):
        """Read the cell for a track in a scene. where names the scene, and song knows the names."""
        where = WHERE_CELL.format(where=where, track=track)
        with reading(where):
            if not isinstance(data, dict):
                raise InvalidValue(MSG_EXPECTED_SETTINGS.format(data=data))
            check_keys(data, set(SETTINGS))
            check_direction(data.get(CellSetting.DIRECTION, Direction.FORWARD))
            if CellSetting.GRAB_TRACK in data:
                grab_track = data[CellSetting.GRAB_TRACK]
                if not song.has_track(grab_track):
                    raise InvalidValue(MSG_NO_GRAB_TRACK.format(name=grab_track))
                if grab_track == track:
                    raise InvalidValue(MSG_GRABS_ITSELF)
            repeat = data.get(CellSetting.REPEAT, DEFAULT_REPEAT)
            if not is_whole_number_from(repeat, MIN_REPEAT):
                raise InvalidValue(MSG_BAD_REPEAT.format(value=repeat))
            if not is_true_or_false(data.get(CellSetting.LOOP, False)):
                raise InvalidValue(MSG_LOOP_NOT_TRUE_OR_FALSE.format(value=data[CellSetting.LOOP]))
            _check_morph(data, repeat, song)
            if CellSetting.PATTERN not in data:
                raise InvalidValue(MSG_NEEDS_PATTERN)
            if not song.has_pattern(data[CellSetting.PATTERN]):
                raise InvalidValue(MSG_NO_SUCH_PATTERN.format(name=data[CellSetting.PATTERN]))
            if CellSetting.CHAIN in data and not song.has_chain(data[CellSetting.CHAIN]):
                raise InvalidValue(MSG_NO_SUCH_CHAIN.format(name=data[CellSetting.CHAIN]))
            return cls(**data)

    def to_data(self):
        return {name: value for name, value in self._settings.items() if value is not None}

    def get_pattern_name(self):
        return self._settings[CellSetting.PATTERN]

    def get_chain_name(self):
        """Return the name of its chain, or None if it has none."""
        return self._settings[CellSetting.CHAIN]

    def loops(self):
        return bool(self._settings[CellSetting.LOOP])

    def get_repeat(self):
        repeat = self._settings[CellSetting.REPEAT]
        return DEFAULT_REPEAT if repeat is None else repeat

    def get_direction(self):
        """Return the direction it overrides its patterns with, or None to use theirs."""
        return self._settings[CellSetting.DIRECTION]

    def get_morph_target(self):
        """Return the pattern it morphs to across its repeats, or None if it doesn't morph."""
        return self._settings[CellSetting.MORPH_TO]

    def get_morph_style(self):
        """Return how it morphs, as a BlendMode, or None if it doesn't morph."""
        style = self.get_morph_style_name()
        return None if style is None else MORPH_STYLES[style]

    def get_morph_style_name(self):
        """Return how it morphs as the file writes it, like 'left', or None if it doesn't morph."""
        return self._settings[CellSetting.MORPH_STYLE]

    def get_grab_track(self):
        """Return the track its grab steps take notes from, or None if it doesn't grab."""
        return self._settings[CellSetting.GRAB_TRACK]


def _check_morph(data, repeat, song):
    """Refuse a morph without both its settings, enough repeats, a known target and a known style."""
    if (CellSetting.MORPH_TO in data) != (CellSetting.MORPH_STYLE in data):
        raise InvalidValue(MSG_MORPH_NEEDS_BOTH)
    if CellSetting.MORPH_TO not in data:
        return
    if repeat < MIN_MORPH_REPEAT:
        raise InvalidValue(MSG_MORPH_TOO_FEW_REPEATS.format(lowest=MIN_MORPH_REPEAT))
    if not song.has_pattern(data[CellSetting.MORPH_TO]):
        raise InvalidValue(MSG_NO_SUCH_PATTERN.format(name=data[CellSetting.MORPH_TO]))
    if data[CellSetting.MORPH_STYLE] not in MORPH_STYLES:
        raise InvalidValue(MSG_BAD_MORPH_STYLE.format(styles=sorted(MORPH_STYLES), value=data[CellSetting.MORPH_STYLE]))
