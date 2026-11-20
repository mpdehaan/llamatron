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

"""A modulator: one of the song's four values, XMod, WMod, YMod and ZMod, that trace a wave over time by themselves, which pattern
steps read and may set, but never add to."""

from fractions import Fraction
import math
import random

from llamatron.composition import defaults, file_format, limits
from llamatron.composition.checks import check_keys, listed, reading
from llamatron.composition.file_format import ModulatorSetting, RateIn, WaveShape
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.llama_data import HoldsSettings
from llamatron.composition.setting import Checked, Choice, described, Flag, WholeNumber
from llamatron.strings import errors
from llamatron.support.revised import notes_change

# What a sample and hold draws each cycle's value from: the render's seed, the modulator, when its wave started and the cycle.
SAMPLE_SEED = '{seed}/modulator/{name}/{origin}/{cycle}'
# Half a cycle, where a wave turns, and the share of a cycle a square holds each level.
HALF = Fraction(1, 2)


def check_hertz(value):
    """Refuse a rate in hertz unless it is a number from MIN_HERTZ to MAX_HERTZ in whole hundredths."""
    is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    if not is_number or not limits.MIN_HERTZ <= value <= limits.MAX_HERTZ or abs(value * limits.HERTZ_STEPS - round(value * limits.HERTZ_STEPS)) > 1e-9:
        raise InvalidValue(errors.ERR_BAD_HERTZ.format(lowest=limits.MIN_HERTZ, highest=limits.MAX_HERTZ, value=value))


# A modulator's settings, each described once, in the order they're written to a file.
SETTINGS = described(
    Choice(name=ModulatorSetting.SHAPE, choices=file_format.WAVE_SHAPES, default=defaults.DEFAULT_WAVE_SHAPE, error=errors.ERR_BAD_RESET_BEHAVIOR),
    Flag(name=ModulatorSetting.INVERT, error=errors.ERR_INVERT_NOT_TRUE_OR_FALSE),
    Choice(name=ModulatorSetting.RATE_IN, choices=file_format.RATES_IN, default=defaults.DEFAULT_RATE_IN, error=errors.ERR_BAD_RESET_BEHAVIOR),
    Choice(name=ModulatorSetting.BARS, choices=file_format.BAR_RATES, default=defaults.DEFAULT_BAR_RATE, error=errors.ERR_BAD_RESET_BEHAVIOR),
    Checked(name=ModulatorSetting.HERTZ, check=check_hertz),
    WholeNumber(name=ModulatorSetting.MINIMUM, lowest=limits.MIN_REGISTER_VALUE, highest=limits.MAX_REGISTER_VALUE, error=errors.ERR_BAD_VALUE),
    WholeNumber(name=ModulatorSetting.START, lowest=limits.MIN_REGISTER_VALUE, highest=limits.MAX_REGISTER_VALUE, error=errors.ERR_BAD_VALUE),
    WholeNumber(name=ModulatorSetting.MAXIMUM, lowest=limits.MIN_REGISTER_VALUE, highest=limits.MAX_REGISTER_VALUE, error=errors.ERR_BAD_VALUE),
)
# What each setting is when the file leaves it out.
DEFAULTS = {
    ModulatorSetting.SHAPE: defaults.DEFAULT_WAVE_SHAPE, ModulatorSetting.INVERT: False, ModulatorSetting.RATE_IN: defaults.DEFAULT_RATE_IN,
    ModulatorSetting.BARS: defaults.DEFAULT_BAR_RATE, ModulatorSetting.HERTZ: defaults.DEFAULT_HERTZ, ModulatorSetting.MINIMUM: defaults.DEFAULT_MODULATOR_VALUE,
    ModulatorSetting.START: defaults.DEFAULT_MODULATOR_VALUE, ModulatorSetting.MAXIMUM: defaults.DEFAULT_MODULATOR_VALUE,
}


def rising_level(*, shape, phase):
    """Return where a wave of a shape stands, from 0 at its lowest to 1 at its highest, a share of the way through a cycle that starts
    at its lowest and rises: a sine and a triangle rise and fall, a square holds its highest for the first half, a saw rises and drops,
    and a reverse saw starts at its highest, falls and jumps back."""
    if shape == WaveShape.SINE:
        return (1 - math.cos(2 * math.pi * phase)) / 2
    if shape == WaveShape.TRIANGLE:
        return float(2 * phase if phase < HALF else 2 - 2 * phase)
    if shape == WaveShape.SQUARE:
        return 1.0 if phase < HALF else 0.0
    if shape == WaveShape.SAW:
        return float(phase)
    return float(1 - phase)


def phase_from(*, shape, level):
    """Return the share of a cycle at which a wave of a shape, rising, first stands at a level from 0 to 1, so that it can start there."""
    if shape == WaveShape.SINE:
        return Fraction(math.acos(1 - 2 * level) / (2 * math.pi)).limit_denominator(10 ** 6)
    if shape == WaveShape.TRIANGLE:
        return Fraction(level).limit_denominator(10 ** 6) / 2
    if shape == WaveShape.SAW:
        return Fraction(level).limit_denominator(10 ** 6)
    if shape == WaveShape.REVERSE_SAW:
        return 1 - Fraction(level).limit_denominator(10 ** 6)
    return Fraction(0)


def nearest_whole(value):
    """Return a value rounded to the nearest whole number, a half rounding up."""
    return math.floor(value + HALF)


class Modulator(HoldsSettings):
    """A modulator's wave: its shape, whether it is turned upside down, how many bars or how many hertz one whole cycle takes, and
    the values it swings between and starts on.

    The wave starts at Start, rising toward Maximum first, or falling toward Minimum first when inverted, and a step that sets the
    modulator starts the wave again from the value it sets. What it is at a moment is value_at(), given how many cycles have passed
    since it started; a sample and hold holds a value drawn at random for each cycle, its first cycle holding Start. Settings the file
    leaves out are kept as None, meaning their defaults.
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
                raise InvalidValue(errors.ERR_MODULATOR_EXPECTED_SETTINGS.format(data=data))
            check_keys(data=data, allowed=set(SETTINGS))
            return _checked(data)

    def is_default(self):
        """Return whether every setting is at its default, so the file needn't name the modulator."""
        return not self.to_data()

    def copy(self):
        return Modulator(**self._settings)

    @notes_change
    def set_setting(self, *, name, value):
        """Change one setting, by its file name, or None to go back to its default; Start is held between the minimum and the maximum."""
        if name not in SETTINGS:
            raise InvalidValue(errors.ERR_MODULATOR_NO_SUCH_SETTING.format(name=name, names=listed(SETTINGS)))
        self._settings = _checked({**self._settings, name: value})._settings

    def get_setting(self, name):
        """Return a setting's value, its default where the file leaves it out."""
        held = self._settings[name]
        return DEFAULTS[name] if held is None else held

    def get_shape(self):
        return self.get_setting(ModulatorSetting.SHAPE)

    def is_inverted(self):
        return bool(self.get_setting(ModulatorSetting.INVERT))

    def get_rate_in(self):
        return self.get_setting(ModulatorSetting.RATE_IN)

    def get_minimum(self):
        return self.get_setting(ModulatorSetting.MINIMUM)

    def get_start(self):
        return self.get_setting(ModulatorSetting.START)

    def get_maximum(self):
        return self.get_setting(ModulatorSetting.MAXIMUM)

    def counts_bars(self):
        return self.get_rate_in() == RateIn.BARS

    def cycle_length(self):
        """Return how long one whole cycle is: in bars, a Fraction, for a rate in bars, and in seconds for a rate in hertz."""
        if self.counts_bars():
            return Fraction(self.get_setting(ModulatorSetting.BARS))
        return 1 / Fraction(round(self.get_setting(ModulatorSetting.HERTZ) * limits.HERTZ_STEPS), limits.HERTZ_STEPS)

    def is_in_order(self):
        return self.get_minimum() <= self.get_start() <= self.get_maximum()

    def value_at(self, *, cycles, start=None, seed=None, name=None, origin=None):
        """Return the modulator's whole value a number of cycles after its wave started from start, Start unless a step set another.

        A sample and hold draws each cycle's value from the render's seed, the modulator's name and when its wave started, origin,
        so that one seed makes one song.
        """
        start = self.get_start() if start is None else start
        lowest = self.get_minimum()
        swing = self.get_maximum() - lowest
        if swing == 0:
            return lowest
        shape = self.get_shape()
        whole, phase = divmod(Fraction(cycles), 1)
        if shape == WaveShape.SAMPLE_AND_HOLD:
            if whole == 0:
                return start
            return random.Random(SAMPLE_SEED.format(seed=seed, name=name, origin=origin, cycle=whole)).randint(lowest, self.get_maximum())
        held = min(max(start, lowest), self.get_maximum())
        if cycles == 0 and shape != WaveShape.SQUARE:
            # A wave starts where it is set, even a saw whose start is the top it jumps from.
            return held
        level = Fraction(held - lowest, swing)
        if self.is_inverted():
            # Turned upside down, the wave falls from Start: the upright wave rises from Start's mirror, and is read upside down.
            begun = phase_from(shape=shape, level=1 - level)
            standing = 1 - rising_level(shape=shape, phase=(phase + begun) % 1)
        else:
            begun = phase_from(shape=shape, level=level)
            standing = rising_level(shape=shape, phase=(phase + begun) % 1)
        return nearest_whole(lowest + standing * swing)


def _checked(settings):
    """Return a Modulator from settings by name, with None meaning a default, or raise InvalidValue if they're wrong."""
    for name, value in settings.items():
        if value is not None:
            SETTINGS[name].check_held(settings)
    modulator = Modulator(**settings)
    if not modulator.is_in_order():
        raise InvalidValue(errors.ERR_MODULATOR_OUT_OF_ORDER.format(minimum=modulator.get_minimum(), start=modulator.get_start(), maximum=modulator.get_maximum()))
    return modulator
