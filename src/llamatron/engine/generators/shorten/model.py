# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Shorten plugin's model: its settings, which own a row of steps, and how much of itself a note plays."""

from llamatron.engine.generators import settings_base, step_row
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.engine.generators.shorten.generator import Shorten
from llamatron.engine.generators.step_row import StepRowSetting
from llamatron.model.objects.llama_data import or_default
from llamatron.model.schema import limits
from llamatron.model.schema.setting import described, WholeNumber
from llamatron.user_strings import errors

# How much of itself a note starting on a step that's on plays, as a percentage, unless set.
DEFAULT_SHORTEN = 70


class ShortenSettings(GeneratorSettings):
    """A Shorten's settings: the row of steps it owns, and how much of itself a note starting on a step that's on plays."""

    __slots__ = ()

    GENERATOR = Shorten
    SETTINGS = described(
        step_row.STEPS_SETTING, step_row.STEP_SETTING, WholeNumber(name=StepRowSetting.SHORTEN, lowest=limits.MIN_SHORTEN, highest=limits.MAX_SHORTEN, error=errors.ERR_BAD_SHAPE_PERCENT),
        settings_base.RESTART_SETTING,
    )
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
        return {StepRowSetting.SHORTEN: self.get_shorten()}

    def get_shorten(self):
        return or_default(value=self.get_written(StepRowSetting.SHORTEN), default=DEFAULT_SHORTEN)
