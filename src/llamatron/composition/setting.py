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
"""One description of each setting of what a set file stores, which holds the one check of its value.

A setting's value is checked in two places: when a file is read, and when the object's setter is
called. Both ask the setting's description here, so the two can't come to disagree, and a class
lists its settings once, in the order a file writes them, with `described()`.

A description also knows the allowed value nearest a wrong one, where there is one: a whole
number outside its range has the nearest end of the range, and a choice outside its fixed list
has the default. Opening a file offers those in place of what it found (composition/corrections.py).
Anything else wrong, like a name that doesn't exist or text where a number belongs, has no
nearest value and is refused.

A check that spans two settings, like a track's lowest octave not being above its highest, stays
written out in the class, after its settings have each been checked.
"""

from llamatron.composition.checks import NO_LENGTH, is_true_or_false, is_whole_number, is_written_length, listed, positive_length, written_length
from llamatron.composition.corrections import NO_NEAREST_VALUE, Correction
from llamatron.composition.invalid_value import InvalidValue
from llamatron.strings.errors import ERR_NEEDS_CHECK


def described(*settings):
    """Return settings by the names a file gives them, in the order given, which is the order a file writes them."""
    return {setting.get_name(): setting for setting in settings}


def settings_held(*, settings, data):
    """Return the described settings a file's data holds, in the order they're described, for a class that places each one's problem itself."""
    return [setting for name, setting in settings.items() if name in data]


def check_settings(*, settings, data, song=None, leaving_out=()):
    """Check every setting a file's data holds against its description, in the order the data holds them.

    Only what the data holds is looked at, so a clip that gives its pattern alone costs one
    check, not one for every setting a clip could have. A name the data holds that isn't a
    setting, like a scene's tracks, is the class's to read. leaving_out names the settings the
    class checks itself straight after, because what a file may hold in one depends on another,
    like a scene's tempo and its ramp.
    """
    for name in data:
        if name in settings and name not in leaving_out:
            settings[name].check_held(data, song=song)


class Setting:
    """One setting: the name a file gives it, and the check of its value that reading and setting share."""

    __slots__ = ('_name',)

    def __init__(self, *, name):
        self._name = name

    def get_name(self):
        return self._name

    def check(self, value, *, song=None):
        """Raise InvalidValue unless the setting can hold the value. song is the song or the set being read or changed, for a setting that names something in it."""
        raise NotImplementedError(ERR_NEEDS_CHECK.format(kind=type(self).__name__))

    def nearest(self, value):
        """Return the allowed value nearest a wrong one, LEFT_OUT when that is the setting's default, or NO_NEAREST_VALUE when nothing allowed is near it."""
        return NO_NEAREST_VALUE

    def problem_with(self, value):
        """Return what is wrong with a value, in the words the check refuses it with, or None if nothing is."""
        try:
            self.check(value)
        except InvalidValue as problem:
            return str(problem)
        return None

    def check_held(self, data, *, song=None):
        """Check the value a file's data holds under the setting's name.

        A wrong value with an allowed value near it is refused carrying the correction that
        would put the nearest value in the data, for whoever offers to open the file corrected.
        """
        try:
            self.check(data[self._name], song=song)
        except InvalidValue as problem:
            raise problem.with_correction(self.correction(data)) from None

    def correction(self, data):
        """Return the correction that puts the nearest allowed value in a file's data, or None when the value there has none."""
        found = data[self._name]
        used = self.nearest(found)
        if used is NO_NEAREST_VALUE:
            return None
        return Correction(holder=data, key=self._name, name=self._name, found=found, used=used)


class Flag(Setting):
    """A setting that is true or false."""

    __slots__ = ('_error',)

    def __init__(self, *, name, error):
        super().__init__(name=name)
        self._error = error

    def check(self, value, *, song=None):
        if not is_true_or_false(value):
            raise InvalidValue(self._error.format(name=self._name, value=value))


class Text(Setting):
    """A setting that is text of any kind, only for people to read."""

    __slots__ = ('_error',)

    def __init__(self, *, name, error):
        super().__init__(name=name)
        self._error = error

    def check(self, value, *, song=None):
        if not isinstance(value, str):
            raise InvalidValue(self._error.format(name=self._name, value=value))


class WholeNumber(Setting):
    """A setting that is a whole number from lowest to highest, with no lowest or no highest where none is given."""

    __slots__ = ('_lowest', '_highest', '_error')

    def __init__(self, *, name, lowest=None, highest=None, error):
        super().__init__(name=name)
        self._lowest = lowest
        self._highest = highest
        self._error = error

    def check(self, value, *, song=None):
        # Written out rather than asked of nearest(), since a pattern checks every step's value with this.
        if type(value) is not int or (self._lowest is not None and value < self._lowest) or (self._highest is not None and value > self._highest):
            raise InvalidValue(self._error.format(name=self._name, value=value, lowest=self._lowest, highest=self._highest, most=self._highest))

    def nearest(self, value):
        """Return the end of the range nearest a whole number outside it. Anything that isn't a whole number has no nearest value."""
        if not is_whole_number(value):
            return NO_NEAREST_VALUE
        if self._lowest is not None and value < self._lowest:
            return self._lowest
        if self._highest is not None and value > self._highest:
            return self._highest
        return value


class Choice(Setting):
    """A setting that is one of a fixed list of choices, with the default a wrong choice falls back to: a choice, or LEFT_OUT."""

    __slots__ = ('_choices', '_default', '_error')

    def __init__(self, *, name, choices, default, error):
        super().__init__(name=name)
        self._choices = list(choices)
        self._default = default
        self._error = error

    def check(self, value, *, song=None):
        if value not in self._choices:
            raise InvalidValue(self._error.format(name=self._name, value=value, choices=listed(self._choices)))

    def nearest(self, value):
        return self._default


class Length(Setting):
    """A setting that is a length written as a whole number or a fraction, like 2 or 5/16, more than nothing and at most most. blank_allowed lets a file write it as nothing, for the default."""

    __slots__ = ('_most', '_blank_allowed')

    def __init__(self, *, name, most, blank_allowed=False):
        super().__init__(name=name)
        self._most = most
        self._blank_allowed = blank_allowed

    def get_most(self):
        """Return the longest length allowed."""
        return self._most

    def check(self, value, *, song=None):
        if value is not None or not self._blank_allowed:
            written_length(value=value, most=self._most)

    def nearest(self, value):
        """Return the longest allowed length for a length that is longer. Anything that isn't a length has no nearest value, and neither has a length of nothing, since no length is the shortest."""
        if not is_written_length(value) or positive_or_nothing(value) <= NO_LENGTH:
            return NO_NEAREST_VALUE
        return self._most if positive_or_nothing(value) > self._most else value


def positive_or_nothing(value):
    """Return a written length as a number, or no length at all for one that isn't more than nothing."""
    try:
        return positive_length(value)
    except InvalidValue:
        return NO_LENGTH


class Checked(Setting):
    """A setting checked by a function of its own, which raises InvalidValue: a tempo, a list, or a name that something in the song has to have.

    nearest is a function that returns the allowed value nearest a wrong one, or
    NO_NEAREST_VALUE, for a setting that has one, like a list of amounts each within limits.
    """

    __slots__ = ('_check', '_needs_song', '_nearest')

    def __init__(self, *, name, check, needs_song=False, nearest=None):
        super().__init__(name=name)
        self._check = check
        self._needs_song = needs_song
        self._nearest = nearest

    def nearest(self, value):
        return NO_NEAREST_VALUE if self._nearest is None else self._nearest(value)

    def check(self, value, *, song=None):
        if self._needs_song:
            self._check(value=value, song=song)
        else:
            self._check(value)
