# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the shorten generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.engine.generators import step_row_settings
from llamatron.engine.generators.shorten.generator import Shorten
from llamatron.engine.generators.step_row_settings import StepRowSetting, StepRowSettings
from llamatron.model.objects.llama_data import or_default
from llamatron.model.schema import limits
from llamatron.model.schema.setting import described, WholeNumber
from llamatron.user_strings import errors

class ShortenSettings(StepRowSettings):
    """A Shorten's settings: its row, and how much of itself a note starting on a step that's on plays."""

    __slots__ = ()

    GENERATOR = Shorten
    SETTINGS = described(
        step_row_settings.STEP_ROW_SETTINGS[0], step_row_settings.STEP_ROW_SETTINGS[1], WholeNumber(name=StepRowSetting.SHORTEN, lowest=limits.MIN_SHORTEN, highest=limits.MAX_SHORTEN, error=errors.ERR_BAD_SHAPE_PERCENT),
        step_row_settings.STEP_ROW_SETTINGS[2],
    )

    def amounts(self):
        return {StepRowSetting.SHORTEN: self.get_shorten()}

    def get_shorten(self):
        return or_default(value=self.get_written(StepRowSetting.SHORTEN), default=step_row_settings.DEFAULT_SHORTEN)
