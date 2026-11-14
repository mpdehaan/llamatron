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
"""A groove: a row of timing amounts that moves notes off the grid, like swing on a drum machine.

A groove is a row of cells, each a signed percentage of the cell's length: 0 leaves a note where
it is, 16 plays it 16% of a cell late and -16 plays it early. The row repeats its own length from
the start of the scene, and a note takes the amount of the cell its time falls in, whatever the
step size or direction of its pattern, so a groove follows time rather than steps. Its gate is
kept, so a delayed note ends later too, and a step's CC values move with it. The amounts are
limited so that notes can't change order. Decided with the user on 2026-11-07, after looking at
swing on the MPC, the Linn drums, Elektron's boxes and the Cirklon, where swing is timing only:
velocity shaping may be added to grooves later.

Every set has the factory grooves, defined here and never written to a file: none, four swings
on 16ths, two on 8ths, and a push. They can be looked at and copied, but not edited, renamed or
deleted, because people may not know the values to rebuild them, and a groove of the user's own
can't take a factory name.
"""

from llamatron.support.rational import Rational
from llamatron.composition.checks import check_keys, is_whole_number, is_whole_number_from, listed, reading, written_length
from llamatron.composition.defaults import DEFAULT_GROOVE_CELL_LENGTH
from llamatron.composition.file_format import GrooveSetting
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.corrections import NO_NEAREST_VALUE
from llamatron.composition.setting import Checked, Length, described
from llamatron.composition.limits import MAX_GROOVE_AMOUNT, MAX_GROOVE_CELL_LENGTH, MAX_GROOVE_CELLS, MIN_GROOVE_AMOUNT, MIN_GROOVE_CELLS
from llamatron.composition.llama_data import LlamaData, or_default
from llamatron.strings.errors import (
    ERR_BAD_GROOVE_AMOUNT, ERR_BAD_GROOVE_CELLS, ERR_FACTORY_GROOVE_NAME, ERR_GROOVE_EXPECTED_SETTINGS, ERR_GROOVE_NOT_NAME_OR_FALSE,
    ERR_NO_SUCH_GROOVE, ERR_NO_SUCH_GROOVE_CELL, ERR_WHERE_WITHIN,
)
from llamatron.support.revised import notes_change

# A groove's amounts are percentages of a cell.
PERCENT = 100
# The straight amount, which leaves a note on the grid.
STRAIGHT = 0
# How many cells a new groove, and the factory grooves, have: one bar of 16ths.
GROOVE_CELLS = 16
# Swing is the share of a pair of cells that the first takes, so 50 is straight and 66 is a
# triplet feel; the second cell is delayed by twice the percentage over 50.
STRAIGHT_SWING = 50
SWING_DELAY_PER_PERCENT = 2
THIRTY_SECOND = '1/32'
SIXTEENTH = '1/16'
EIGHTH = '1/8'
QUARTER = '1/4'
# The cell lengths the groove editor offers, from the shortest.
GROOVE_CELL_LENGTH_CHOICES = [THIRTY_SECOND, SIXTEENTH, EIGHTH, QUARTER]
# The push moves the off-beat 16ths early by this much.
PUSH_AMOUNT = -16


class FactoryGroove:
    """The names of the grooves every set has without writing them."""

    NONE = 'none'
    SWING_54 = 'swing 54'
    SWING_58 = 'swing 58'
    SWING_62 = 'swing 62'
    SWING_66 = 'swing 66'
    EIGHTH_SWING_58 = '8th swing 58'
    EIGHTH_SWING_66 = '8th swing 66'
    PUSH = 'push'


class Groove(LlamaData):
    """A row of timing amounts, each a percentage of the cell's length, and how long a cell is."""

    __slots__ = ('_cells', '_cell_length')

    def __init__(self, *, cells, cell_length=None):
        self.note_change()
        self._cells = list(cells)
        self._cell_length = cell_length

    @classmethod
    def from_data(cls, *, data, where, song=None):
        with reading(where):
            if not isinstance(data, dict):
                raise InvalidValue(ERR_GROOVE_EXPECTED_SETTINGS.format(data=data))
            check_keys(data=data, allowed=set(SETTINGS))
            # A groove needs its cells, so a file that leaves them out is refused as one that holds none.
            if GrooveSetting.CELLS not in data:
                SETTINGS[GrooveSetting.CELLS].check(None)
            SETTINGS[GrooveSetting.CELLS].check_held(data)
            if GrooveSetting.CELL_LENGTH in data:
                with reading(ERR_WHERE_WITHIN.format(where=where, part=GrooveSetting.CELL_LENGTH)):
                    SETTINGS[GrooveSetting.CELL_LENGTH].check_held(data)
            return cls(cells=data[GrooveSetting.CELLS], cell_length=data.get(GrooveSetting.CELL_LENGTH))

    def to_data(self):
        data = {GrooveSetting.CELLS: list(self._cells)}
        if self._cell_length is not None:
            data[GrooveSetting.CELL_LENGTH] = self._cell_length
        return data

    def copy(self):
        return Groove(cells=self._cells, cell_length=self._cell_length)

    def get_cells(self):
        """Return the amounts, in order, as a new list."""
        return list(self._cells)

    def get_cell_length_text(self):
        """Return how long a cell is, as the file writes it, like 1/16."""
        return or_default(value=self._cell_length, default=DEFAULT_GROOVE_CELL_LENGTH)

    def get_cell_length(self):
        """Return how long a cell is, in whole notes."""
        return Rational(written_length(value=self.get_cell_length_text(), most=MAX_GROOVE_CELL_LENGTH))

    def is_straight(self):
        """Return whether the groove moves nothing, like the factory groove none."""
        return all(amount == STRAIGHT for amount in self._cells)

    # Timing, which the exporters' timing code asks for.

    def offset_at(self, time):
        """Return how far a note at a time, in whole notes from the start of its scene, is moved: late if positive, early if negative."""
        cell_length = self.get_cell_length()
        cell = int(time / cell_length) % len(self._cells)
        return cell_length * Rational(self._cells[cell], PERCENT)

    def moved(self, time):
        """Return when a note at a time plays once the groove has moved it, never before the clip's start."""
        return max(time + self.offset_at(time), Rational(0))

    # Editing, which the groove editor does one cell at a time.

    @notes_change
    def set_cell(self, *, step, amount):
        self._check_step(step)
        if not is_whole_number_from(value=amount, lowest=MIN_GROOVE_AMOUNT, highest=MAX_GROOVE_AMOUNT):
            raise InvalidValue(ERR_BAD_GROOVE_AMOUNT.format(lowest=MIN_GROOVE_AMOUNT, highest=MAX_GROOVE_AMOUNT, value=amount))
        self._cells[step] = amount

    @notes_change
    def insert_cell(self, step):
        """Add a straight cell before a step, up to the most a groove can have."""
        if len(self._cells) >= MAX_GROOVE_CELLS:
            return
        self._check_step(step)
        self._cells.insert(step, STRAIGHT)

    @notes_change
    def remove_cell(self, step):
        """Take a cell out, leaving at least one."""
        if len(self._cells) <= MIN_GROOVE_CELLS:
            return
        self._check_step(step)
        del self._cells[step]

    @notes_change
    def set_cell_length(self, value):
        """Set how long a cell is, as the file writes it, like 1/8, or None for the default."""
        if value is not None:
            SETTINGS[GrooveSetting.CELL_LENGTH].check(value)
        self._cell_length = None if value == DEFAULT_GROOVE_CELL_LENGTH else value

    def _check_step(self, step):
        if not is_whole_number_from(value=step, lowest=0, highest=len(self._cells) - 1):
            raise InvalidValue(ERR_NO_SUCH_GROOVE_CELL.format(step=step, count=len(self._cells)))


def _is_cell_list(cells):
    """Return whether a value is a list of 1 to MAX_GROOVE_CELLS amounts, each within the limits."""
    return (
        isinstance(cells, list) and MIN_GROOVE_CELLS <= len(cells) <= MAX_GROOVE_CELLS
        and all(is_whole_number_from(value=amount, lowest=MIN_GROOVE_AMOUNT, highest=MAX_GROOVE_AMOUNT) for amount in cells)
    )


def _check_cells(cells):
    if not _is_cell_list(cells):
        raise InvalidValue(ERR_BAD_GROOVE_CELLS.format(fewest=MIN_GROOVE_CELLS, most=MAX_GROOVE_CELLS, lowest=MIN_GROOVE_AMOUNT, highest=MAX_GROOVE_AMOUNT, value=cells))


def _nearest_cells(cells):
    """Return cells with each amount outside the limits at the nearest limit, or NO_NEAREST_VALUE unless they're the right number of whole numbers."""
    if not isinstance(cells, list) or not MIN_GROOVE_CELLS <= len(cells) <= MAX_GROOVE_CELLS or not all(is_whole_number(amount) for amount in cells):
        return NO_NEAREST_VALUE
    return [min(max(amount, MIN_GROOVE_AMOUNT), MAX_GROOVE_AMOUNT) for amount in cells]


# A groove's settings, each described once, in the order they're written to a file.
SETTINGS = described(
    Checked(name=GrooveSetting.CELLS, check=_check_cells, nearest=_nearest_cells),
    Length(name=GrooveSetting.CELL_LENGTH, most=MAX_GROOVE_CELL_LENGTH),
)


def new_groove():
    """Return the groove a new one starts as: one bar of straight 16ths."""
    return Groove(cells=[STRAIGHT] * GROOVE_CELLS)


def swing_groove(*, percent, cell_length):
    """Return a swing of a percentage on cells of a length: every second cell is delayed by twice the percentage over 50."""
    delay = (percent - STRAIGHT_SWING) * SWING_DELAY_PER_PERCENT
    return Groove(cells=[STRAIGHT, delay] * (GROOVE_CELLS // 2), cell_length=None if cell_length == DEFAULT_GROOVE_CELL_LENGTH else cell_length)


def push_groove():
    """Return the push: the off-beat 16ths played early."""
    return Groove(cells=[STRAIGHT, PUSH_AMOUNT] * (GROOVE_CELLS // 2))


FACTORY_GROOVES = {
    FactoryGroove.NONE: new_groove(),
    FactoryGroove.SWING_54: swing_groove(percent=54, cell_length=SIXTEENTH),
    FactoryGroove.SWING_58: swing_groove(percent=58, cell_length=SIXTEENTH),
    FactoryGroove.SWING_62: swing_groove(percent=62, cell_length=SIXTEENTH),
    FactoryGroove.SWING_66: swing_groove(percent=66, cell_length=SIXTEENTH),
    FactoryGroove.EIGHTH_SWING_58: swing_groove(percent=58, cell_length=EIGHTH),
    FactoryGroove.EIGHTH_SWING_66: swing_groove(percent=66, cell_length=EIGHTH),
    FactoryGroove.PUSH: push_groove(),
}
FACTORY_GROOVE_NAMES = list(FACTORY_GROOVES)


def is_factory_groove(name):
    return name in FACTORY_GROOVES


def factory_groove(name):
    """Return a factory groove by name, as a copy, so that nothing can change the original."""
    return FACTORY_GROOVES[name].copy()


def check_groove_name(name):
    """Refuse a factory groove's name for a groove of the user's own."""
    if is_factory_groove(name):
        raise InvalidValue(ERR_FACTORY_GROOVE_NAME.format(name=name, names=listed(FACTORY_GROOVE_NAMES)))


def check_groove_choice(*, value, song):
    """Refuse a scene's or track's groove unless it's left out, false (no groove here) or the name of a groove the song has."""
    if value is None or value is False:
        return
    if not isinstance(value, str):
        raise InvalidValue(ERR_GROOVE_NOT_NAME_OR_FALSE.format(value=value))
    if not song.has_groove(value):
        raise InvalidValue(ERR_NO_SUCH_GROOVE.format(name=value))


def groove_for(*, choices, song):
    """Return the groove that choices, from the most specific to the least, settle on, or None for none.

    A false anywhere switches grooving off, whatever else is chosen, as the user accepted on
    2026-11-07: a kick track with groove false stays straight in a swung scene, and a scene
    with groove false stays straight for a swung hi-hat track. Otherwise the first name wins,
    so a track's groove beats its scene's, which beats its song's, and the factory groove none
    and any other straight groove move nothing.
    """
    if any(choice is False for choice in choices):
        return None
    for choice in choices:
        if choice is not None:
            groove = song.get_groove(choice)
            return None if groove.is_straight() else groove
    return None
