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

"""A scale the song names, like main: { root: F, type: minor }, for the song and scenes to use."""

import re

from llamatron.composition.llama_data import LlamaData
from llamatron.composition.song_file_error import SongFileError
from llamatron.note import Note
from llamatron.scale import Scale, ScaleType


class NamedScale(LlamaData):
    """A root note and a kind of scale, which the song keeps under a name of the user's choosing.

    The root and the kind are kept as the file writes them, like 'F' and 'minor', so that saving
    writes them back the same way.
    """

    def __init__(self, root, kind):
        self._root = root
        self._kind = kind

    @classmethod
    def from_data(cls, data, where, song=None):
        if not isinstance(data, dict) or set(data) != {'root', 'type'}:
            raise SongFileError(f'{where}: expected a root and a type, like {{ root: F, type: minor }}, got {data!r}')
        root, kind = data['root'], data['type']
        if not isinstance(root, str) or not re.fullmatch(r'[A-G][#b]?', root):
            raise SongFileError(f'{where}: expected a root note like F or Bb, got {root!r}')
        if _kind_name(kind) not in ScaleType.__members__:
            names = ', '.join(sorted(name.lower() for name in ScaleType.__members__))
            raise SongFileError(f'{where}: unknown scale type {kind!r}, expected one of: {names}')
        return cls(root, kind)

    def to_data(self):
        return {'root': self._root, 'type': self._kind}

    def scale_at(self, octave):
        """Return this scale with its root in an octave, in this project's numbering."""
        return Scale(Note(self._root, octave), ScaleType[_kind_name(self._kind)])


def _kind_name(kind):
    """Return the ScaleType name a file's scale type means, so that 'natural minor' is NATURAL_MINOR."""
    return str(kind).strip().upper().replace(' ', '_')
