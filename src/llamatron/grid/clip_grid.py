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

"""The grid of finished clips that the exporters write out, one cell for each scene and track."""

from itertools import count

from llamatron.support.rational import Rational
from llamatron.composition.checks import check_scale, check_tempo, check_time_signature
from llamatron.composition.checks import time_signature as time_signature_object
from llamatron.composition.defaults import DEFAULT_TIME_SIGNATURE
from llamatron.grid.clip import Clip
from llamatron.grid.clip_column import ClipColumn
from llamatron.grid.clip_row import ClipRow
from llamatron.strings.errors import ERR_COLUMN_NOT_IN_GRID, ERR_NOT_A_CLIP, ERR_NOT_A_CLIP_COLUMN, ERR_NOT_A_CLIP_ROW, ERR_ROW_NOT_IN_GRID

# How long a row with no clips lasts.
NO_LENGTH = 0

DEFAULT_TEMPO = 120


class ClipGrid:
    """A grid of clips: a ClipRow for each scene, a ClipColumn for each track, and a cell where each pair meets."""

    __slots__ = ('_tempo', '_time_signature', '_scale', '_columns', '_rows', '_next_column_id', '_next_row_id', '_clips')

    def __init__(self, *, tempo=DEFAULT_TEMPO, scale=None, time_signature=None):
        self.set_tempo(tempo)
        self.set_time_signature(time_signature or time_signature_object(DEFAULT_TIME_SIGNATURE))
        self.set_scale(scale)
        self._columns = {}
        self._rows = {}
        self._next_column_id = count(0)
        self._next_row_id = count(0)
        # Nested as {row id: {column id: clip}}. Empty cells have no entry.
        self._clips = {}

    def get_tempo(self):
        return self._tempo

    def set_tempo(self, tempo):
        check_tempo(tempo)
        self._tempo = tempo

    def get_time_signature(self):
        """Return the song's TimeSignature, which the exporters write so that a DAW draws the right bars."""
        return self._time_signature

    def set_time_signature(self, signature):
        check_time_signature(signature)
        self._time_signature = signature

    def get_scale(self):
        return self._scale

    def set_scale(self, scale):
        check_scale(scale)
        self._scale = scale

    def get_columns(self):
        """Return a list of the columns, in the order they were added."""
        return list(self._columns.values())

    def get_rows(self):
        """Return a list of the rows, in the order they were added."""
        return list(self._rows.values())

    def add_column(self, column):
        """Add a ClipColumn to the grid, give it its id and return it."""
        if not isinstance(column, ClipColumn):
            raise ValueError(ERR_NOT_A_CLIP_COLUMN.format(value=column))
        column.set_id(next(self._next_column_id))
        self._columns[column.get_id()] = column
        return column

    def add_row(self, row):
        """Add a ClipRow to the grid, give it its id and return it."""
        if not isinstance(row, ClipRow):
            raise ValueError(ERR_NOT_A_CLIP_ROW.format(value=row))
        row.set_id(next(self._next_row_id))
        self._rows[row.get_id()] = row
        return row

    def set_clip(self, *, row, column, clip):
        """Put a Clip in a cell, replacing any clip already there, and return it."""
        self._check_clip_slot(row=row, column=column)
        if not isinstance(clip, Clip):
            raise ValueError(ERR_NOT_A_CLIP.format(value=clip))
        self._clips.setdefault(row.get_id(), {})[column.get_id()] = clip
        return clip

    def get_clip(self, *, row, column):
        """Return the Clip in a cell, or None if the cell is empty."""
        self._check_clip_slot(row=row, column=column)
        return self._clips.get(row.get_id(), {}).get(column.get_id())

    def tempo_at(self, row):
        """Return the tempo for a row: its own if it has one, else the song's."""
        self._check_row(row)
        return self._tempo if row.get_tempo() is None else row.get_tempo()

    def row_length(self, row):
        """Return how long a row lasts, in whole notes: as long as its longest clip, or 0 with no clips."""
        self._check_row(row)
        lengths = [clip.total_length() for clip in self._clips_in(row)]
        return max(lengths, default=NO_LENGTH)

    def row_starts(self):
        """Return when each row starts when the rows are laid end to end in order, in whole notes."""
        starts = []
        now = Rational(0)
        for row in self.get_rows():
            starts.append(now)
            now += self.row_length(row)
        return starts

    def song_length(self):
        """Return how long the rows last laid end to end, in whole notes."""
        return sum((self.row_length(row) for row in self.get_rows()), Rational(0))

    def _clips_in(self, row):
        """Return a row's clips, in column order."""
        return [clip for clip in (self.get_clip(row=row, column=column) for column in self.get_columns()) if clip is not None]

    def scale_at(self, *, row, column):
        """Return the scale for a cell: its clip's, else its row's, else the song's.

        Returns None if none of them has a scale.
        """
        clip = self.get_clip(row=row, column=column)
        candidates = [row.get_scale(), self._scale]
        if clip is not None:
            candidates.insert(0, clip.get_scale())
        return next((scale for scale in candidates if scale is not None), None)

    def _check_column(self, column):
        if not isinstance(column, ClipColumn) or self._columns.get(column.get_id()) is not column:
            raise ValueError(ERR_COLUMN_NOT_IN_GRID.format(column=column))

    def _check_row(self, row):
        if not isinstance(row, ClipRow) or self._rows.get(row.get_id()) is not row:
            raise ValueError(ERR_ROW_NOT_IN_GRID.format(row=row))

    def _check_clip_slot(self, *, row, column):
        self._check_row(row)
        self._check_column(column)
