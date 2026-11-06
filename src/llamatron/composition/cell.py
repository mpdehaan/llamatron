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

from llamatron.composition.checks import check_keys, is_true_or_false, is_whole_number_from
from llamatron.composition.defaults import DEFAULT_REPEAT
from llamatron.composition.file_format import CellSetting, Direction
from llamatron.composition.limits import MIN_REPEAT
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.pattern import check_direction
from llamatron.composition.song_file_error import SongFileError
from llamatron.generators.blend import BlendMode

MORPH_STYLES = {member.name.lower(): member for member in BlendMode}
MSG_EXPECTED_SETTINGS = '{where}, track {track!r}: expected settings like {{ pattern: a }}, got {data!r}'
# How a cell is named in its messages: by its scene and its track.
WHERE_CELL = '{where}, track {track!r}'
MSG_NO_RHYTHM_PATTERN = '{where}: rhythm_from: no pattern called {name!r}'
MSG_NO_GRAB_TRACK = '{where}: grab_track: no track called {name!r}'
MSG_GRABS_ITSELF = "{where}: grab_track: a clip can't grab from its own track"
MSG_BAD_REPEAT = '{where}: repeat must be a positive whole number, got {value!r}'
MSG_LOOP_NOT_TRUE_OR_FALSE = '{where}: loop must be true or false, got {value!r}'
MSG_NEEDS_PATTERN = '{where}: needs a pattern'
MSG_NO_SUCH_PATTERN = '{where}: no pattern called {name!r}'
MSG_NO_SUCH_CHAIN = '{where}: no chain called {name!r}'
MSG_MORPH_NEEDS_BOTH = '{where}: a morph needs both morph_to and morph_style'
MSG_MORPH_TOO_FEW_REPEATS = '{where}: a morph needs a repeat of {lowest} or more'
MSG_BAD_MORPH_STYLE = '{where}: morph_style must be one of {styles}, got {value!r}'
# A cell's settings, in the order they're written to a file.
SETTINGS = [
    CellSetting.PATTERN, CellSetting.CHAIN, CellSetting.LOOP, CellSetting.REPEAT, CellSetting.DIRECTION,
    CellSetting.MORPH_TO, CellSetting.MORPH_STYLE, CellSetting.RHYTHM_FROM, CellSetting.GRAB_TRACK,
]
# A morph has to play its first pattern and its target, so it needs at least two repeats.
MIN_MORPH_REPEAT = 2


class Cell(LlamaData):
    """A pattern to play, and how: its chain, repeats or loop, direction, morph, rhythm and grab.

    Settings the file leaves out are kept as None, meaning their defaults. The pattern, chain and
    other patterns and tracks are kept as names, and looked up when the song renders.
    """

    def __init__(self, **settings):
        self._settings = {name: settings.get(name) for name in SETTINGS}

    @classmethod
    def from_data(cls, data, where, song=None, track=None):
        """Read the cell for a track in a scene. where names the scene, and song knows the names."""
        if not isinstance(data, dict):
            raise SongFileError(MSG_EXPECTED_SETTINGS.format(where=where, track=track, data=data))
        where = WHERE_CELL.format(where=where, track=track)
        check_keys(data, where, set(SETTINGS))
        check_direction(data.get(CellSetting.DIRECTION, Direction.FORWARD), where)
        rhythm_from = data.get(CellSetting.RHYTHM_FROM)
        if rhythm_from is not None and not song.has_pattern(rhythm_from):
            raise SongFileError(MSG_NO_RHYTHM_PATTERN.format(where=where, name=rhythm_from))
        if CellSetting.GRAB_TRACK in data:
            grab_track = data[CellSetting.GRAB_TRACK]
            if not song.has_track(grab_track):
                raise SongFileError(MSG_NO_GRAB_TRACK.format(where=where, name=grab_track))
            if grab_track == track:
                raise SongFileError(MSG_GRABS_ITSELF.format(where=where))
        repeat = data.get(CellSetting.REPEAT, DEFAULT_REPEAT)
        if not is_whole_number_from(repeat, MIN_REPEAT):
            raise SongFileError(MSG_BAD_REPEAT.format(where=where, value=repeat))
        if not is_true_or_false(data.get(CellSetting.LOOP, False)):
            raise SongFileError(MSG_LOOP_NOT_TRUE_OR_FALSE.format(where=where, value=data[CellSetting.LOOP]))
        _check_morph(data, repeat, where, song)
        if CellSetting.PATTERN not in data:
            raise SongFileError(MSG_NEEDS_PATTERN.format(where=where))
        if not song.has_pattern(data[CellSetting.PATTERN]):
            raise SongFileError(MSG_NO_SUCH_PATTERN.format(where=where, name=data[CellSetting.PATTERN]))
        if CellSetting.CHAIN in data and not song.has_chain(data[CellSetting.CHAIN]):
            raise SongFileError(MSG_NO_SUCH_CHAIN.format(where=where, name=data[CellSetting.CHAIN]))
        return cls(**data)

    def to_data(self):
        return {name: value for name, value in self._settings.items() if value is not None}

    def get_pattern_name(self):
        return self._settings[CellSetting.PATTERN]

    def get_rhythm_pattern_name(self):
        """Return the pattern its rhythm comes from, which is its own pattern unless rhythm_from names another."""
        return self._settings[CellSetting.RHYTHM_FROM] or self._settings[CellSetting.PATTERN]

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
        style = self._settings[CellSetting.MORPH_STYLE]
        return None if style is None else MORPH_STYLES[style]

    def get_grab_track(self):
        """Return the track its grab steps take notes from, or None if it doesn't grab."""
        return self._settings[CellSetting.GRAB_TRACK]


def _check_morph(data, repeat, where, song):
    """Refuse a morph without both its settings, enough repeats, a known target and a known style."""
    if (CellSetting.MORPH_TO in data) != (CellSetting.MORPH_STYLE in data):
        raise SongFileError(MSG_MORPH_NEEDS_BOTH.format(where=where))
    if CellSetting.MORPH_TO not in data:
        return
    if repeat < MIN_MORPH_REPEAT:
        raise SongFileError(MSG_MORPH_TOO_FEW_REPEATS.format(where=where, lowest=MIN_MORPH_REPEAT))
    if not song.has_pattern(data[CellSetting.MORPH_TO]):
        raise SongFileError(MSG_NO_SUCH_PATTERN.format(where=where, name=data[CellSetting.MORPH_TO]))
    if data[CellSetting.MORPH_STYLE] not in MORPH_STYLES:
        raise SongFileError(MSG_BAD_MORPH_STYLE.format(where=where, styles=sorted(MORPH_STYLES), value=data[CellSetting.MORPH_STYLE]))
