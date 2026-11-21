# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A row of the grid a song renders into: one scene's clips."""

from llamatron.composition.checks import check_name, check_scale, check_tempo_override
from llamatron.strings import errors, reprs


class ClipRow:
    """A row of the grid a song renders into, which is one scene's clips. Its id is None unless it's in a grid.

    A tempo or scale of None uses the song's.
    """

    __slots__ = ('_id', '_name', '_tempo', '_scale', '_tempo_changes')

    def __init__(self, *, name=None, tempo=None, scale=None):
        check_name(name)
        check_tempo_override(tempo)
        check_scale(scale)
        self._id = None
        self._name = name
        self._tempo = tempo
        self._scale = scale
        self._tempo_changes = ()

    def get_id(self):
        return self._id

    def set_id(self, new_id):
        """Give the row its id as it joins a grid. A row joins only one grid, so a second id is refused."""
        if self._id is not None:
            raise ValueError(errors.ERR_ROW_IN_A_GRID.format(row=self))
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

    def get_tempo_changes(self):
        """Return the changes of tempo inside the row, (time in whole notes from its start, tempo) in order, none for a row that keeps one tempo."""
        return self._tempo_changes

    def set_tempo_changes(self, changes):
        """Give the row its changes of tempo after its start, each a time in whole notes and a tempo."""
        for _, tempo in changes:
            check_tempo_override(tempo)
        self._tempo_changes = tuple(changes)

    def get_scale(self):
        return self._scale

    def set_scale(self, scale):
        check_scale(scale)
        self._scale = scale

    def __repr__(self):
        return reprs.REPR_CLIP_ROW.format(name=self._name, tempo=self._tempo, scale=self._scale, id=self._id)
