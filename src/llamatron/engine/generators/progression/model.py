# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the progression generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.engine.generators import settings_base
from llamatron.engine.generators.progression.generator import Progression
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.model.file.checks import Bars, is_whole_number_from, listed, time_length
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.named_scale import scale_type_names
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import Accidental
from llamatron.model.schema.setting import Checked, described
from llamatron.user_strings import errors

class ProgressionSetting:
    """A Progression's settings, as a file names them: its chords as degrees, a sharp or flat and an inversion for each, and how long each chord lasts."""

    RESTART = file_format.GENERATOR_RESTART

    EVERY = 'every'
    CHORDS = 'chords'
    ACCIDENTALS = 'accidentals'
    INVERSIONS = 'inversions'
    # The scale type each chord borrows, its named quality, and the tensions on top, each beside the chords.
    SCALES = 'scales'
    QUALITIES = 'qualities'
    TENSIONS = 'tensions'


def _check_progression_chords(chords):
    """Check a progression's chords: a list of 1 to MAX_PROGRESSION_CHORDS degrees."""
    fits = isinstance(chords, list) and limits.MIN_PROGRESSION_CHORDS <= len(chords) <= limits.MAX_PROGRESSION_CHORDS and all(
        is_whole_number_from(value=degree, lowest=limits.MIN_PROGRESSION_DEGREE, highest=limits.MAX_PROGRESSION_DEGREE) for degree in chords)
    if not fits:
        raise InvalidValue(errors.ERR_BAD_PROGRESSION_CHORDS.format(most=limits.MAX_PROGRESSION_CHORDS, lowest=limits.MIN_PROGRESSION_DEGREE, highest=limits.MAX_PROGRESSION_DEGREE, value=chords))


def _row_of(*, name, allowed):
    """Return a check of a list beside the chords, each step one of the allowed values or nothing."""
    def check(values):
        if not isinstance(values, list) or not all(value is None or value in allowed for value in values):
            raise InvalidValue(errors.ERR_BAD_PROGRESSION_ROW.format(name=name, choices=listed(allowed), value=values))
    return check


def _tensions_row(values):
    """Check a progression's tensions: a list beside the chords, each step a list of some of the tensions, each once, or nothing."""
    def is_tensions(value):
        return isinstance(value, (list, tuple)) and len(value) > 0 and len(set(value)) == len(value) and all(tension in file_format.TENSIONS for tension in value)
    if not isinstance(values, list) or not all(value is None or is_tensions(value) for value in values):
        raise InvalidValue(errors.ERR_BAD_PROGRESSION_TENSIONS.format(name=ProgressionSetting.TENSIONS, choices=listed(file_format.TENSIONS), value=values))


# What a progression's sharp-or-flat and inversion rows may hold beside nothing.
PROGRESSION_ACCIDENTALS = [Accidental.SHARP, Accidental.FLAT]


PROGRESSION_INVERSIONS = list(range(1, limits.MAX_PROGRESSION_INVERSION + 1))


# A new progression's one chord, I, which moves nothing until it's edited.
NEW_PROGRESSION_CHORDS = [1]


# The rows beside a progression's chords, each as long as the chords.
PROGRESSION_ROWS = (
    ProgressionSetting.ACCIDENTALS, ProgressionSetting.INVERSIONS, ProgressionSetting.SCALES, ProgressionSetting.QUALITIES, ProgressionSetting.TENSIONS,
)


class ProgressionSettings(GeneratorSettings):
    """A Progression's settings: its chords, each with a sharp or flat and an inversion, and how long each lasts, a bar when left out."""

    __slots__ = ()

    GENERATOR = Progression
    SETTINGS = described(
        Checked(name=ProgressionSetting.EVERY, check=time_length),
        Checked(name=ProgressionSetting.CHORDS, check=_check_progression_chords),
        Checked(name=ProgressionSetting.ACCIDENTALS, check=_row_of(name=ProgressionSetting.ACCIDENTALS, allowed=PROGRESSION_ACCIDENTALS)),
        Checked(name=ProgressionSetting.INVERSIONS, check=_row_of(name=ProgressionSetting.INVERSIONS, allowed=PROGRESSION_INVERSIONS)),
        Checked(name=ProgressionSetting.SCALES, check=_row_of(name=ProgressionSetting.SCALES, allowed=scale_type_names())),
        Checked(name=ProgressionSetting.QUALITIES, check=_row_of(name=ProgressionSetting.QUALITIES, allowed=list(file_format.FIXED_CHORDS))),
        Checked(name=ProgressionSetting.TENSIONS, check=_tensions_row),
        settings_base.RESTART_SETTING,
    )
    REQUIRED = [ProgressionSetting.CHORDS]
    TAKEN_AS = {ProgressionSetting.EVERY: time_length}

    @classmethod
    def new(cls):
        """Return the settings a new progression starts with: the one chord I."""
        return cls({ProgressionSetting.CHORDS: list(NEW_PROGRESSION_CHORDS)})

    def _with_defaults(self, *, values, default_seed, default_step, bar):
        every = values.get(ProgressionSetting.EVERY, Bars(1))
        values[ProgressionSetting.EVERY] = bar * every.count if isinstance(every, Bars) else every
        chords = values[ProgressionSetting.CHORDS]
        for row in PROGRESSION_ROWS:
            values[row] = _lined_up(values=values.get(row), count=len(chords))
        return values

    def get_every(self):
        return self.get_written(ProgressionSetting.EVERY)

    def get_chords(self):
        return list(self.get_written(ProgressionSetting.CHORDS) or NEW_PROGRESSION_CHORDS)

    def get_accidentals(self):
        return _lined_up(values=self.get_written(ProgressionSetting.ACCIDENTALS), count=len(self.get_chords()))

    def get_inversions(self):
        return _lined_up(values=self.get_written(ProgressionSetting.INVERSIONS), count=len(self.get_chords()))

    def get_scales(self):
        """Return the scale type each chord borrows, or None for the clip's own."""
        return _lined_up(values=self.get_written(ProgressionSetting.SCALES), count=len(self.get_chords()))

    def get_qualities(self):
        """Return each chord's named quality, a chord symbol, or None for the chord its scale builds."""
        return _lined_up(values=self.get_written(ProgressionSetting.QUALITIES), count=len(self.get_chords()))

    def get_tensions(self):
        """Return each chord's tensions as a tuple, lowest first, or None for none."""
        return [_tensions_in_order(value) for value in _lined_up(values=self.get_written(ProgressionSetting.TENSIONS), count=len(self.get_chords()))]


def _lined_up(*, values, count):
    """Return a row beside the chords as long as the chords, a missing step being nothing."""
    values = list(values or [])
    return (values + [None] * count)[:count]


def _tensions_in_order(value):
    """Return the tensions a chord's value holds, in the order the tensions come, as a tuple, or None for none."""
    return None if value is None else tuple(tension for tension in file_format.TENSIONS if tension in value)
