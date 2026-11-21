# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A register: one of the song's four values, AX to DX, that pattern steps change and read as the song plays."""

from typing import NamedTuple

from llamatron.caching.revised import notes_change
from llamatron.model.file import corrections
from llamatron.model.file.checks import listed, pass_over_unknown, reading
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.llama_data import HoldsSettings
from llamatron.model.schema import defaults, file_format, limits
from llamatron.model.schema.file_format import RegisterSetting, ResetBehavior
from llamatron.model.schema.setting import Choice, described, Flag, WholeNumber
from llamatron.user_strings import errors

# A register's settings, each described once, in the order they're written to a file.
SETTINGS = described(
    WholeNumber(name=RegisterSetting.DEFAULT, lowest=limits.MIN_REGISTER_VALUE, highest=limits.MAX_REGISTER_VALUE, error=errors.ERR_BAD_VALUE),
    WholeNumber(name=RegisterSetting.MINIMUM, lowest=limits.MIN_REGISTER_VALUE, highest=limits.MAX_REGISTER_VALUE, error=errors.ERR_BAD_VALUE),
    WholeNumber(name=RegisterSetting.MAXIMUM, lowest=limits.MIN_REGISTER_VALUE, highest=limits.MAX_REGISTER_VALUE, error=errors.ERR_BAD_VALUE),
    Choice(name=RegisterSetting.RESET_BEHAVIOR, choices=file_format.RESET_BEHAVIORS, default=corrections.LEFT_OUT, error=errors.ERR_BAD_RESET_BEHAVIOR),
    Flag(name=RegisterSetting.RESET_EACH_SCENE, error=errors.ERR_RESET_EACH_SCENE_NOT_TRUE_OR_FALSE),
    WholeNumber(name=RegisterSetting.ALLOWED_INC_MAX, lowest=limits.MIN_ALLOWED_INC_MAX, highest=limits.MAX_REGISTER_VALUE, error=errors.ERR_BAD_VALUE),
)
# What each setting is when the file leaves it out.
DEFAULTS = {
    RegisterSetting.DEFAULT: defaults.DEFAULT_REGISTER_VALUE, RegisterSetting.MINIMUM: defaults.DEFAULT_REGISTER_MINIMUM,
    RegisterSetting.MAXIMUM: defaults.DEFAULT_REGISTER_MAXIMUM, RegisterSetting.RESET_BEHAVIOR: defaults.DEFAULT_RESET_BEHAVIOR,
    RegisterSetting.RESET_EACH_SCENE: defaults.DEFAULT_RESET_EACH_SCENE,
    RegisterSetting.ALLOWED_INC_MAX: defaults.DEFAULT_ALLOWED_INC_MAX,
}


class Bounced(NamedTuple):
    """What a register that reverses comes to after an amount: its value, and whether it now counts the other way."""

    value: int
    turned: bool


class Register(HoldsSettings):
    """A register's default, minimum and maximum, what it does at those limits, whether each scene resets it, and the most a step may add to it.

    A register starts at its default when rendering starts, whenever a scene resets it, and as each
    scene starts when it resets each scene. Adding to it never takes it past its minimum or
    maximum: what it does instead is its Reset behavior (ResetBehavior). Settings the file leaves out are kept
    as None, meaning their defaults.
    """

    __slots__ = ()

    SETTINGS = SETTINGS

    def __init__(self, **settings):
        self.note_change()
        self._settings = {name: settings.get(name) for name in SETTINGS}

    @classmethod
    def from_data(cls, *, data, where, song=None):
        with reading(where):
            data = {} if data is None else data
            if not isinstance(data, dict):
                raise InvalidValue(errors.ERR_REGISTER_EXPECTED_SETTINGS.format(data=data))
            pass_over_unknown(data=data, allowed=SETTINGS)
            return _checked(data)

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
            raise InvalidValue(errors.ERR_REGISTER_NO_SUCH_SETTING.format(name=name, names=listed(SETTINGS)))
        self._settings = _checked({**self._settings, name: value})._settings

    def get_default(self):
        return self._setting(RegisterSetting.DEFAULT)

    def get_minimum(self):
        return self._setting(RegisterSetting.MINIMUM)

    def get_maximum(self):
        return self._setting(RegisterSetting.MAXIMUM)

    def get_reset_behavior(self):
        """Return what the register does when an add would take it past an end, one of ResetBehavior."""
        return self._setting(RegisterSetting.RESET_BEHAVIOR)

    def resets_each_scene(self):
        """Return whether the register goes back to its default as each scene first starts."""
        return bool(self._setting(RegisterSetting.RESET_EACH_SCENE))

    def get_allowed_inc_max(self):
        """Return the most a step may add to the register or take from it."""
        return self._setting(RegisterSetting.ALLOWED_INC_MAX)

    def is_in_order(self):
        """Return whether its default lies between its minimum and maximum, as it must."""
        return self.get_minimum() <= self.get_default() <= self.get_maximum()

    def reverses(self):
        """Return whether the register turns round at its ends, so that whoever keeps its value keeps which way it is counting too."""
        return self.get_reset_behavior() == ResetBehavior.REVERSE

    def added(self, *, value, amount, chooser=None):
        """Return a value with an amount added, kept between the minimum and maximum.

        Going past an end does what the register's Reset behavior says: hold at the end; go to
        the minimum past the maximum and hold below the minimum, or the mirror of that; go back
        to the default; roll round to the other end, keeping what is left over; or land on a
        random value, drawn from chooser. A register that reverses is asked reversed() instead,
        since which way it counts has to be kept with its value.
        """
        result = value + amount
        lowest = self.get_minimum()
        highest = self.get_maximum()
        if lowest <= result <= highest:
            return result
        past_the_top = result > highest
        behavior = self.get_reset_behavior()
        if behavior == ResetBehavior.OVERFLOW:
            return lowest + (result - lowest) % (highest - lowest + 1)
        if behavior == ResetBehavior.RESET_TO_DEFAULT:
            return self.get_default()
        if behavior == ResetBehavior.PICK_RANDOM:
            return chooser.randint(lowest, highest)
        if behavior == ResetBehavior.RESET_CLIP:
            return lowest
        if behavior == ResetBehavior.CLIP_RESET:
            return highest
        return highest if past_the_top else lowest

    def reversed(self, *, value, amount, turned):
        """Return a value with an amount added by a register that reverses, as a Bounced: the value, and whether the register then counts the other way.

        While turned, an amount counts the other way: an add takes away and a subtraction adds.
        Past an end the value bounces off it, what is left over carrying on back the other way,
        and the register is turned, or turned back, until the other end is passed.
        """
        lowest = self.get_minimum()
        highest = self.get_maximum()
        if lowest == highest:
            return Bounced(value=lowest, turned=turned)
        result = value - amount if turned else value + amount
        while not lowest <= result <= highest:
            result = 2 * highest - result if result > highest else 2 * lowest - result
            turned = not turned
        return Bounced(value=result, turned=turned)

    def held(self, value):
        """Return a value a step sets the register to, kept between the minimum and maximum: a set is an exact value, so it stops at an end and never wraps."""
        return max(min(value, self.get_maximum()), self.get_minimum())

    def _setting(self, name):
        value = self._settings[name]
        return DEFAULTS[name] if value is None else value


def _checked(settings):
    """Return a Register from settings by name, with None meaning a default, or raise InvalidValue if they're wrong. The settings can be a file's own data, which a correction is then made in."""
    for name, value in settings.items():
        # None is a setting left at its default.
        if value is not None:
            SETTINGS[name].check_held(settings)
    register = Register(**settings)
    if not register.is_in_order():
        raise InvalidValue(errors.ERR_OUT_OF_ORDER.format(minimum=register.get_minimum(), default=register.get_default(), maximum=register.get_maximum()))
    return register
