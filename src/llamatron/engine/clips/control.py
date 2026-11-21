# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A MIDI CC value sent at a time in a clip."""

from llamatron.engine.clips.positions import exact_length
from llamatron.model.values import midi
from llamatron.user_strings import errors, reprs

# What the two CC numbers are called when one is out of range.
NUMBER_WORD = 'number'
VALUE_WORD = 'value'


def _check_cc(*, what, value):
    """Check that a CC number or value is an integer in MIDI's range."""
    if type(value) is not int or not midi.MIN_CC_VALUE <= value <= midi.MAX_CC_VALUE:
        raise ValueError(errors.ERR_INVALID_CONTROL_NUMBER.format(name=what, value=value, lowest=midi.MIN_CC_VALUE, highest=midi.MAX_CC_VALUE))


class Control:
    """A MIDI CC value sent at a time in a clip, in fractions of a whole note from its start.

    With slide, the value ramps to the next value for the same number instead of holding.
    Controls are immutable: at_time, moved_by and with_number return new ones.
    """

    __slots__ = ('_time', '_number', '_value', '_slide')

    def __init__(self, *, time, number, value, slide=False):
        if exact_length(time) < 0:
            raise ValueError(errors.ERR_INVALID_TIME.format(time=time))
        _check_cc(what=NUMBER_WORD, value=number)
        _check_cc(what=VALUE_WORD, value=value)
        if type(slide) is not bool:
            raise ValueError(errors.ERR_INVALID_SLIDE.format(slide=slide))
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
        return reprs.REPR_CONTROL.format(time=self._time, number=self._number, value=self._value, slide=self._slide)
