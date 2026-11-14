# llamatron: a music program
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

"""A row of the grid a song renders into: one scene's clips."""

from llamatron.composition.checks import check_name, check_scale, check_tempo_override
from llamatron.strings.errors import ERR_ROW_IN_A_GRID
from llamatron.strings.reprs import REPR_CLIP_ROW


class ClipRow:
    """A row of the grid a song renders into, which is one scene's clips. Its id is None unless it's in a grid.

    A tempo or scale of None uses the song's.
    """

    __slots__ = ('_id', '_name', '_tempo', '_scale')

    def __init__(self, *, name=None, tempo=None, scale=None):
        check_name(name)
        check_tempo_override(tempo)
        check_scale(scale)
        self._id = None
        self._name = name
        self._tempo = tempo
        self._scale = scale

    def get_id(self):
        return self._id

    def set_id(self, new_id):
        """Give the row its id as it joins a grid. A row joins only one grid, so a second id is refused."""
        if self._id is not None:
            raise ValueError(ERR_ROW_IN_A_GRID.format(row=self))
        self._id = new_id

    def get_name(self):
        return self._name

    def set_name(self, name):
        check_name(name)
        self._name = name

    def get_tempo(self):
        return self._tempo

    def set_tempo(self, tempo):
        check_tempo_override(tempo)
        self._tempo = tempo

    def get_scale(self):
        return self._scale

    def set_scale(self, scale):
        check_scale(scale)
        self._scale = scale

    def __repr__(self):
        return REPR_CLIP_ROW.format(name=self._name, tempo=self._tempo, scale=self._scale, id=self._id)
