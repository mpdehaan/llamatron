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

"""A register: one of the song's four values, AX to DX, that pattern steps change and read as the song plays."""

from llamatron.composition.checks import reading, check_keys, is_true_or_false, is_whole_number_from
from llamatron.composition.defaults import (
    DEFAULT_REGISTER_MAXIMUM, DEFAULT_REGISTER_MINIMUM, DEFAULT_REGISTER_VALUE, DEFAULT_REGISTER_WRAP,
)
from llamatron.composition.file_format import RegisterSetting
from llamatron.composition.limits import MAX_REGISTER_VALUE, MIN_REGISTER_VALUE
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.invalid_value import InvalidValue

MSG_EXPECTED_SETTINGS = 'expected settings like {{ minimum: 0, maximum: 3, wrap: true }}, got {data!r}'
MSG_BAD_VALUE = '{name} must be a whole number from {lowest} to {highest}, got {value!r}'
MSG_WRAP_NOT_TRUE_OR_FALSE = 'wrap must be true or false, got {value!r}'
MSG_OUT_OF_ORDER = 'needs minimum ({minimum}) <= default ({default}) <= maximum ({maximum})'
# The settings that are numbers, in the order they're written to a file.
NUMBER_SETTINGS = [RegisterSetting.DEFAULT, RegisterSetting.MINIMUM, RegisterSetting.MAXIMUM]
SETTINGS = [*NUMBER_SETTINGS, RegisterSetting.WRAP]
# What each setting is when the file leaves it out.
DEFAULTS = {
    RegisterSetting.DEFAULT: DEFAULT_REGISTER_VALUE, RegisterSetting.MINIMUM: DEFAULT_REGISTER_MINIMUM,
    RegisterSetting.MAXIMUM: DEFAULT_REGISTER_MAXIMUM, RegisterSetting.WRAP: DEFAULT_REGISTER_WRAP,
}


class Register(LlamaData):
    """A register's default, minimum and maximum, and whether it wraps past them.

    A register starts at its default when rendering starts and whenever a scene resets it. Adding
    to it never takes it past its minimum or maximum: it stops at the end it reached, or, if it
    wraps, jumps to the other end. Settings the file leaves out are kept as None, meaning their
    defaults.
    """

    __slots__ = ('_settings',)

    def __init__(self, **settings):
        self._settings = {name: settings.get(name) for name in SETTINGS}

    @classmethod
    def from_data(cls, data, where, song=None):
        with reading(where):
            data = {} if data is None else data
            if not isinstance(data, dict):
                raise InvalidValue(MSG_EXPECTED_SETTINGS.format(data=data))
            check_keys(data, set(SETTINGS))
            for name in NUMBER_SETTINGS:
                value = data.get(name, DEFAULTS[name])
                if not is_whole_number_from(value, MIN_REGISTER_VALUE, MAX_REGISTER_VALUE):
                    raise InvalidValue(MSG_BAD_VALUE.format(name=name, lowest=MIN_REGISTER_VALUE, highest=MAX_REGISTER_VALUE, value=value))
            if not is_true_or_false(data.get(RegisterSetting.WRAP, DEFAULT_REGISTER_WRAP)):
                raise InvalidValue(MSG_WRAP_NOT_TRUE_OR_FALSE.format(value=data[RegisterSetting.WRAP]))
            register = cls(**{name: data[name] for name in SETTINGS if name in data})
            if not register.is_in_order():
                raise InvalidValue(MSG_OUT_OF_ORDER.format(minimum=register.get_minimum(), default=register.get_default(), maximum=register.get_maximum()))
            return register

    def to_data(self):
        return {name: value for name, value in self._settings.items() if value is not None}

    def get_default(self):
        return self._setting(RegisterSetting.DEFAULT)

    def get_minimum(self):
        return self._setting(RegisterSetting.MINIMUM)

    def get_maximum(self):
        return self._setting(RegisterSetting.MAXIMUM)

    def wraps(self):
        return self._setting(RegisterSetting.WRAP)

    def is_in_order(self):
        """Return whether its default lies between its minimum and maximum, as it must."""
        return self.get_minimum() <= self.get_default() <= self.get_maximum()

    def added(self, value, amount):
        """Return a value with an amount added, kept between the minimum and maximum.

        Going past an end stops at that end, or, if the register wraps, jumps straight to the
        other end. What's left over is dropped, so a jump never lands part way along.
        """
        result = value + amount
        lowest, highest = self.get_minimum(), self.get_maximum()
        if result > highest:
            return lowest if self.wraps() else highest
        if result < lowest:
            return highest if self.wraps() else lowest
        return result

    def _setting(self, name):
        value = self._settings[name]
        return DEFAULTS[name] if value is None else value
