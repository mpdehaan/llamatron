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

"""A register: one of the song's four values, AX to DX, that pattern steps change and read as the song plays."""

from llamatron.composition.checks import check_keys, listed, reading
from llamatron.composition.defaults import (
    DEFAULT_ALLOWED_INC_MAX, DEFAULT_AT_LIMIT, DEFAULT_REGISTER_MAXIMUM, DEFAULT_REGISTER_MINIMUM, DEFAULT_REGISTER_VALUE, DEFAULT_RESET_EACH_SCENE,
)
from llamatron.composition.corrections import LEFT_OUT
from llamatron.composition.file_format import AT_LIMITS, AtLimit, RegisterSetting
from llamatron.composition.checks import is_true_or_false
from llamatron.composition.limits import MAX_REGISTER_VALUE, MIN_ALLOWED_INC_MAX, MIN_REGISTER_VALUE
from llamatron.composition.llama_data import LlamaData, written_settings
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.setting import Choice, Flag, WholeNumber, described
from llamatron.strings.errors import (
    ERR_BAD_AT_LIMIT, ERR_BAD_VALUE, ERR_OUT_OF_ORDER, ERR_REGISTER_EXPECTED_SETTINGS, ERR_REGISTER_NO_SUCH_SETTING, ERR_RESET_EACH_SCENE_NOT_TRUE_OR_FALSE,
    ERR_WRAP_NOT_TRUE_OR_FALSE,
)
from llamatron.support.revised import notes_change

# A register's settings, each described once, in the order they're written to a file.
SETTINGS = described(
    WholeNumber(name=RegisterSetting.DEFAULT, lowest=MIN_REGISTER_VALUE, highest=MAX_REGISTER_VALUE, error=ERR_BAD_VALUE),
    WholeNumber(name=RegisterSetting.MINIMUM, lowest=MIN_REGISTER_VALUE, highest=MAX_REGISTER_VALUE, error=ERR_BAD_VALUE),
    WholeNumber(name=RegisterSetting.MAXIMUM, lowest=MIN_REGISTER_VALUE, highest=MAX_REGISTER_VALUE, error=ERR_BAD_VALUE),
    Choice(name=RegisterSetting.AT_LIMIT, choices=AT_LIMITS, default=LEFT_OUT, error=ERR_BAD_AT_LIMIT),
    Flag(name=RegisterSetting.RESET_EACH_SCENE, error=ERR_RESET_EACH_SCENE_NOT_TRUE_OR_FALSE),
    WholeNumber(name=RegisterSetting.ALLOWED_INC_MAX, lowest=MIN_ALLOWED_INC_MAX, highest=MAX_REGISTER_VALUE, error=ERR_BAD_VALUE),
)
# What each setting is when the file leaves it out.
DEFAULTS = {
    RegisterSetting.DEFAULT: DEFAULT_REGISTER_VALUE, RegisterSetting.MINIMUM: DEFAULT_REGISTER_MINIMUM,
    RegisterSetting.MAXIMUM: DEFAULT_REGISTER_MAXIMUM, RegisterSetting.AT_LIMIT: DEFAULT_AT_LIMIT,
    RegisterSetting.RESET_EACH_SCENE: DEFAULT_RESET_EACH_SCENE,
    RegisterSetting.ALLOWED_INC_MAX: DEFAULT_ALLOWED_INC_MAX,
}


class Register(LlamaData):
    """A register's default, minimum and maximum, what it does at those limits, whether each scene resets it, and the most a step may add to it.

    A register starts at its default when rendering starts, whenever a scene resets it, and as each
    scene starts when it resets each scene. Adding to it never takes it past its minimum or
    maximum: what it does instead is its At limit (AtLimit). Settings the file leaves out are kept
    as None, meaning their defaults.
    """

    __slots__ = ('_settings',)

    def __init__(self, **settings):
        self.note_change()
        self._settings = {name: settings.get(name) for name in SETTINGS}

    @classmethod
    def from_data(cls, *, data, where, song=None):
        with reading(where):
            data = {} if data is None else data
            if not isinstance(data, dict):
                raise InvalidValue(ERR_REGISTER_EXPECTED_SETTINGS.format(data=data))
            check_keys(data=data, allowed={*SETTINGS, RegisterSetting.WRAP})
            _read_wrap(data)
            return _checked(data)

    def to_data(self):
        return written_settings(self._settings)

    def is_default(self):
        """Return whether every setting is at its default, so the file needn't name the register."""
        return not self.to_data()

    def copy(self):
        return Register(**self._settings)

    @notes_change
    def set_setting(self, *, name, value):
        """Change one setting, by its file name, or None to go back to its default.

        The four settings are checked together, since the default has to lie between the minimum
        and the maximum, so one generic setter keeps that check in one place.
        """
        if name not in SETTINGS:
            raise InvalidValue(ERR_REGISTER_NO_SUCH_SETTING.format(name=name, names=listed(SETTINGS)))
        self._settings = _checked({**self._settings, name: value})._settings

    def get_default(self):
        return self._setting(RegisterSetting.DEFAULT)

    def get_minimum(self):
        return self._setting(RegisterSetting.MINIMUM)

    def get_maximum(self):
        return self._setting(RegisterSetting.MAXIMUM)

    def get_at_limit(self):
        """Return what the register does when an add would take it past an end, one of AtLimit."""
        return self._setting(RegisterSetting.AT_LIMIT)

    def resets_each_scene(self):
        """Return whether the register goes back to its default as each scene first starts."""
        return bool(self._setting(RegisterSetting.RESET_EACH_SCENE))

    def get_allowed_inc_max(self):
        """Return the most a step may add to the register or take from it."""
        return self._setting(RegisterSetting.ALLOWED_INC_MAX)

    def is_in_order(self):
        """Return whether its default lies between its minimum and maximum, as it must."""
        return self.get_minimum() <= self.get_default() <= self.get_maximum()

    def added(self, *, value, amount, chooser=None):
        """Return a value with an amount added, kept between the minimum and maximum.

        Going past an end does what the register's At limit says: stop at the end, go back to the
        default, land exactly on the other end (from either end, or only past the maximum, or only
        past the minimum, stopping at the other), or land on a random value, drawn from chooser.
        What's left over is always dropped, so a jump never lands part way along.
        """
        result = value + amount
        lowest = self.get_minimum()
        highest = self.get_maximum()
        if lowest <= result <= highest:
            return result
        past_the_top = result > highest
        at_limit = self.get_at_limit()
        if at_limit == AtLimit.RESET:
            return self.get_default()
        if at_limit == AtLimit.PICK_RANDOM:
            return chooser.randint(lowest, highest)
        jumps = at_limit == AtLimit.OVERFLOW or (at_limit == AtLimit.OVERFLOW_RIGHT and past_the_top) or (at_limit == AtLimit.OVERFLOW_LEFT and not past_the_top)
        if past_the_top:
            return lowest if jumps else highest
        return highest if jumps else lowest

    def held(self, value):
        """Return a value a step sets the register to, kept between the minimum and maximum: a set is an exact value, so it stops at an end and never wraps (the user's choice of 2026-11-11)."""
        return max(min(value, self.get_maximum()), self.get_minimum())

    def _setting(self, name):
        value = self._settings[name]
        return DEFAULTS[name] if value is None else value


def _read_wrap(data):
    """Read wrap from a file saved before at_limit came, which true meant overflow, as at_limit, in the file's own data, so that a correction made after finds the data it reads."""
    if RegisterSetting.WRAP not in data:
        return
    wrap = data.pop(RegisterSetting.WRAP)
    if not is_true_or_false(wrap):
        raise InvalidValue(ERR_WRAP_NOT_TRUE_OR_FALSE.format(value=wrap))
    if wrap and RegisterSetting.AT_LIMIT not in data:
        data[RegisterSetting.AT_LIMIT] = AtLimit.OVERFLOW


def _checked(settings):
    """Return a Register from settings by name, with None meaning a default, or raise InvalidValue if they're wrong. The settings can be a file's own data, which a correction is then made in."""
    for name, value in settings.items():
        # None is a setting left at its default.
        if value is not None:
            SETTINGS[name].check_held(settings)
    register = Register(**settings)
    if not register.is_in_order():
        raise InvalidValue(ERR_OUT_OF_ORDER.format(minimum=register.get_minimum(), default=register.get_default(), maximum=register.get_maximum()))
    return register
