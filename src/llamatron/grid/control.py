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

"""A MIDI CC value sent at a time in a clip."""

from llamatron.grid.positions import exact_length
from llamatron.music.midi import MAX_CC_VALUE, MIN_CC_VALUE
from llamatron.strings.errors import ERR_INVALID_CONTROL_NUMBER, ERR_INVALID_SLIDE, ERR_INVALID_TIME
from llamatron.strings.reprs import REPR_CONTROL

# What the two CC numbers are called when one is out of range.
NUMBER_WORD = 'number'
VALUE_WORD = 'value'


def _check_cc(*, what, value):
    """Check that a CC number or value is an integer in MIDI's range."""
    if type(value) is not int or not MIN_CC_VALUE <= value <= MAX_CC_VALUE:
        raise ValueError(ERR_INVALID_CONTROL_NUMBER.format(name=what, value=value, lowest=MIN_CC_VALUE, highest=MAX_CC_VALUE))


class Control:
    """A MIDI CC value sent at a time in a clip, in fractions of a whole note from its start.

    With slide, the value ramps to the next value for the same number instead of holding.
    Controls are immutable: at_time, moved_by and with_number return new ones.
    """

    __slots__ = ('_time', '_number', '_value', '_slide')

    def __init__(self, *, time, number, value, slide=False):
        if exact_length(time) < 0:
            raise ValueError(ERR_INVALID_TIME.format(time=time))
        _check_cc(what=NUMBER_WORD, value=number)
        _check_cc(what=VALUE_WORD, value=value)
        if type(slide) is not bool:
            raise ValueError(ERR_INVALID_SLIDE.format(slide=slide))
        self._time = time
        self._number = number
        self._value = value
        self._slide = slide

    def get_time(self):
        return self._time

    def get_number(self):
        return self._number

    def get_value(self):
        return self._value

    def get_slide(self):
        return self._slide

    def at_time(self, time):
        """Return the same value sent at another time."""
        return Control(time=time, number=self._number, value=self._value, slide=self._slide)

    def moved_by(self, offset):
        """Return the same value sent offset later, or earlier if offset is negative."""
        return Control(time=self._time + offset, number=self._number, value=self._value, slide=self._slide)

    def with_number(self, number):
        """Return the same value sent on another CC number."""
        return Control(time=self._time, number=number, value=self._value, slide=self._slide)

    def _as_tuple(self):
        return (self._time, self._number, self._value, self._slide)

    def __eq__(self, other):
        if not isinstance(other, Control):
            return NotImplemented
        return self._as_tuple() == other._as_tuple()

    def __hash__(self):
        return hash(self._as_tuple())

    def __repr__(self):
        return REPR_CONTROL.format(time=self._time, number=self._number, value=self._value, slide=self._slide)
