# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Glide plugin's model: its settings, which own a row of steps, and how far a note glides."""

from llamatron.engine.generators import settings_base, step_row
from llamatron.engine.generators.glide.generator import Glide
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.engine.generators.step_row import StepRowSetting
from llamatron.math.rational import Rational
from llamatron.model.file.checks import number
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.schema.setting import Checked, described
from llamatron.user_strings import errors

# How far a note starting on a step that's on runs into the next, in whole notes, unless set, and the least and most it can.
DEFAULT_GLIDE_AMOUNT = Rational(1, 128)
LEAST_GLIDE_AMOUNT = Rational(1, 256)
MOST_GLIDE_AMOUNT = Rational(1, 16)


def _check_glide_amount(value):
    amount = number(value)
    if not LEAST_GLIDE_AMOUNT <= amount <= MOST_GLIDE_AMOUNT:
        raise InvalidValue(errors.ERR_BAD_GLIDE_AMOUNT.format(least=LEAST_GLIDE_AMOUNT, most=MOST_GLIDE_AMOUNT, value=value))


class GlideSettings(GeneratorSettings):
    """A Glide's settings: the row of steps it owns, and how far a note starting on a step that's on runs into the next."""

    __slots__ = ()

    GENERATOR = Glide
    SETTINGS = described(step_row.STEPS_SETTING, step_row.STEP_SETTING, Checked(name=StepRowSetting.GLIDE_AMOUNT, check=_check_glide_amount), settings_base.RESTART_SETTING)
    REQUIRED = [StepRowSetting.STEPS]

    @classmethod
    def new(cls):
        """Return the settings a new one starts with: four steps, the first on."""
        return cls(step_row.new_row_data())

    def step_row(self):
        """Return the row of steps it owns."""
        return step_row.StepRow(self)

    def _with_defaults(self, *, values, default_seed, default_step, bar):
        return {**self.step_row().generator_values(default_step=default_step, bar=bar), **self.amounts()}

    def amounts(self):
        """Return its amount as its generator takes it."""
        return {StepRowSetting.GLIDE_AMOUNT: self.get_glide_amount()}

    def get_written_glide_amount(self):
        """Return the glide amount as the file writes it, or None when it's left out."""
        return self.get_written(StepRowSetting.GLIDE_AMOUNT)

    def get_glide_amount(self):
        written = self.get_written(StepRowSetting.GLIDE_AMOUNT)
        if written is None:
            return DEFAULT_GLIDE_AMOUNT
        return number(written)
