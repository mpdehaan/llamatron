# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Timing plugin's model: four rows of steps, a Rush's, a Drag's, a Shorten's and a Glide's, each with its own step and
amount, in one generator's settings, named rush_steps, rush_step, rush_amount and the like. A part changes nothing until one of
its steps is lit."""

from llamatron.engine.generators import settings_base
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.engine.generators.timing import parts
from llamatron.engine.generators.timing.step_row import check_step_row, StepRow
from llamatron.math.rational import Rational
from llamatron.model.file.checks import number, time_length
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.schema import limits
from llamatron.model.schema.setting import Checked, described, WholeNumber
from llamatron.user_strings import errors

DEFAULT_RUSH = 15
DEFAULT_DRAG = 20
DEFAULT_SHORTEN = 70
DEFAULT_GLIDE = Rational(1, 128)
LEAST_GLIDE = Rational(1, 256)
MOST_GLIDE = Rational(1, 16)
# How far each part moves or changes a note on a lit step when its amount is left out.
DEFAULT_AMOUNTS = {parts.RUSH: DEFAULT_RUSH, parts.DRAG: DEFAULT_DRAG, parts.SHORTEN: DEFAULT_SHORTEN, parts.GLIDE: DEFAULT_GLIDE}
NO_RUSH_OR_DRAG = 0


def _check_glide(value):
    """Check a Glide's amount: a length from LEAST_GLIDE to MOST_GLIDE of a whole note."""
    amount = number(value)
    if not LEAST_GLIDE <= amount <= MOST_GLIDE:
        raise InvalidValue(errors.ERR_BAD_GLIDE_AMOUNT.format(least=LEAST_GLIDE, most=MOST_GLIDE, value=value))


def _amount_setting(part):
    """Return the description of a part's amount: a share of a step for a Rush and a Drag, a share of the note for a Shorten, a
    length for a Glide."""
    name = parts.amount_of(part)
    if part == parts.GLIDE:
        return Checked(name=name, check=_check_glide)
    if part == parts.SHORTEN:
        return WholeNumber(name=name, lowest=limits.MIN_SHORTEN, highest=limits.MAX_SHORTEN, error=errors.ERR_BAD_SHAPE_PERCENT)
    return WholeNumber(name=name, lowest=NO_RUSH_OR_DRAG, highest=limits.MAX_RUSH_OR_DRAG, error=errors.ERR_BAD_SHAPE_PERCENT)


def _every_part_setting():
    """Return the descriptions of every part's row, step and amount, in the order a file writes them."""
    settings = []
    for part in parts.PARTS:
        settings.append(Checked(name=parts.steps_of(part), check=check_step_row))
        settings.append(Checked(name=parts.step_of(part), check=time_length))
        settings.append(_amount_setting(part))
    return settings


class TimingSettings(GeneratorSettings):
    """A Timing generator's settings: a Rush, a Drag, a Shorten and a Glide, each a row of steps with its step and amount."""

    __slots__ = ()

    SETTINGS = described(*_every_part_setting(), settings_base.RESTART_SETTING)

    @classmethod
    def new(cls):
        """Return the settings a new one starts with: nothing set, every step of every part off, which changes nothing."""
        return cls({})

    def step_row(self, part):
        """Return one part's row of steps."""
        return StepRow(owner=self, part=part)

    def get_amount(self, part):
        """Return a part's amount, its default where the file leaves it out: a Glide's as a length of a whole note."""
        written = self.get_written(parts.amount_of(part))
        if written is None:
            return DEFAULT_AMOUNTS[part]
        if part == parts.GLIDE:
            return number(written)
        return written
