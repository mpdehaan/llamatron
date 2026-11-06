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
from llamatron.composition.checks import check_keys, number
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.song_file_error import SongFileError

# A scene's settings, in the order they're written to a file, before its tracks.
SETTINGS = ['name', 'repeat', 'scale', 'tempo', 'tempo_start', 'tempo_end']


class Scene(LlamaData):
    """A name, how many times it repeats, an optional scale and tempo, and a cell for each track it plays.

    Settings the file leaves out are kept as None, meaning their defaults. Its scale is kept as
    the name of one of the song's scales.
    """

    def __init__(self, cells=None, **settings):
        self._settings = {name: settings.get(name) for name in SETTINGS}
        self._cells = None if cells is None else dict(cells)

    @classmethod
    def from_data(cls, data, where, song=None):
        if not isinstance(data, dict):
            raise SongFileError(f'{where}: expected settings like name and tracks')
        check_keys(data, where, {*SETTINGS, 'tracks'})
        repeat = data.get('repeat', 1)
        if type(repeat) is not int or repeat < 1:
            raise SongFileError(f'{where}: repeat must be a positive whole number, got {repeat!r}')
        cells = {}
        for track, cell in (data.get('tracks') or {}).items():
            if not song.has_track(track):
                raise SongFileError(f'{where}: no track called {track!r}, expected one of {sorted(song.get_track_names())}')
            cells[track] = Cell.from_data(cell, where, song, track=track)
        if data.get('scale') is not None and not song.has_scale(data['scale']):
            raise SongFileError(f'{where}: no scale called {data["scale"]!r}')
        if 'tempo' in data:
            number(data['tempo'], where)
        elif 'tempo_start' in data or 'tempo_end' in data:
            if 'tempo_start' not in data or 'tempo_end' not in data:
                raise SongFileError(f'{where}: needs both tempo_start and tempo_end')
            number(data['tempo_start'], where)
            number(data['tempo_end'], where)
        settings = {name: data[name] for name in SETTINGS if name in data}
        return cls(cells if 'tracks' in data else None, **settings)

    def to_data(self):
        data = {name: value for name, value in self._settings.items() if value is not None}
        if self._cells is not None:
            data['tracks'] = {track: cell.to_data() for track, cell in self._cells.items()}
        return data

    def get_name(self):
        """Return its name as the file gives it, or None if it has none."""
        return self._settings['name']

    def get_repeat(self):
        return self._settings['repeat'] or 1

    def get_scale_name(self):
        """Return the name of the scale it sets, or None to use the song's."""
        return self._settings['scale']

    def get_tempo(self, place):
        """Return its tempo on one of its repeats, counted from 0, or None to use the song's.

        A scene with tempo_start and tempo_end ramps evenly between them across its repeats.
        """
        settings = self._settings
        if settings['tempo'] is not None:
            return number(settings['tempo'], 'tempo')
        if settings['tempo_start'] is None:
            return None
        start, end = number(settings['tempo_start'], 'tempo'), number(settings['tempo_end'], 'tempo')
        repeat = self.get_repeat()
        return start + (end - start) * (Fraction(place, repeat - 1) if repeat > 1 else 0)

    def get_track_names(self):
        """Return the tracks it plays a cell on, in the order the file lists them."""
        return list(self._cells or {})

    def get_cell(self, track):
        """Return its cell for a track, or None if it plays nothing there."""
        return (self._cells or {}).get(track)
