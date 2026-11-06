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

from llamatron.composition.checks import check_keys
from llamatron.composition.file_format import FORWARD
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.pattern import check_direction
from llamatron.composition.song_file_error import SongFileError
from llamatron.generators.blend import BlendMode

MORPH_STYLES = {member.name.lower(): member for member in BlendMode}
# A cell's settings, in the order they're written to a file.
SETTINGS = ['pattern', 'chain', 'loop', 'repeat', 'direction', 'morph_to', 'morph_style', 'rhythm_from', 'grab_track']


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
            raise SongFileError(f'{where}, track {track!r}: expected settings like {{ pattern: a }}, got {data!r}')
        where = f'{where}, track {track!r}'
        check_keys(data, where, set(SETTINGS))
        check_direction(data.get('direction', FORWARD), where)
        if 'rhythm_from' in data and not song.has_pattern(data['rhythm_from']):
            raise SongFileError(f'{where}: rhythm_from: no pattern called {data["rhythm_from"]!r}')
        if 'grab_track' in data:
            if not song.has_track(data['grab_track']):
                raise SongFileError(f'{where}: grab_track: no track called {data["grab_track"]!r}')
            if data['grab_track'] == track:
                raise SongFileError(f'{where}: grab_track: a clip can\'t grab from its own track')
        repeat = data.get('repeat', 1)
        if type(repeat) is not int or repeat < 1:
            raise SongFileError(f'{where}: repeat must be a positive whole number, got {repeat!r}')
        if not isinstance(data.get('loop', False), bool):
            raise SongFileError(f'{where}: loop must be true or false, got {data["loop"]!r}')
        if ('morph_to' in data) != ('morph_style' in data):
            raise SongFileError(f'{where}: a morph needs both morph_to and morph_style')
        if 'morph_to' in data:
            if repeat < 2:
                raise SongFileError(f'{where}: a morph needs a repeat of 2 or more')
            if not song.has_pattern(data['morph_to']):
                raise SongFileError(f'{where}: no pattern called {data["morph_to"]!r}')
            if data['morph_style'] not in MORPH_STYLES:
                raise SongFileError(f'{where}: morph_style must be one of {sorted(MORPH_STYLES)}, got {data["morph_style"]!r}')
        if 'pattern' not in data:
            raise SongFileError(f'{where}: needs a pattern')
        if not song.has_pattern(data['pattern']):
            raise SongFileError(f'{where}: no pattern called {data["pattern"]!r}')
        if 'chain' in data and not song.has_chain(data['chain']):
            raise SongFileError(f'{where}: no chain called {data["chain"]!r}')
        return cls(**data)

    def to_data(self):
        return {name: value for name, value in self._settings.items() if value is not None}

    def get_pattern_name(self):
        return self._settings['pattern']

    def get_rhythm_pattern_name(self):
        """Return the pattern its rhythm comes from, which is its own pattern unless rhythm_from names another."""
        return self._settings['rhythm_from'] or self._settings['pattern']

    def get_chain_name(self):
        """Return the name of its chain, or None if it has none."""
        return self._settings['chain']

    def loops(self):
        return bool(self._settings['loop'])

    def get_repeat(self):
        return self._settings['repeat'] or 1

    def get_direction(self):
        """Return the direction it overrides its patterns with, or None to use theirs."""
        return self._settings['direction']

    def get_morph_target(self):
        """Return the pattern it morphs to across its repeats, or None if it doesn't morph."""
        return self._settings['morph_to']

    def get_morph_style(self):
        """Return how it morphs, as a BlendMode, or None if it doesn't morph."""
        style = self._settings['morph_style']
        return None if style is None else MORPH_STYLES[style]

    def get_grab_track(self):
        """Return the track its grab steps take notes from, or None if it doesn't grab."""
        return self._settings['grab_track']
