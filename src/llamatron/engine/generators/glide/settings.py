# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the glide generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.engine.generators import step_row_settings
from llamatron.engine.generators.glide.generator import Glide
from llamatron.engine.generators.step_row_settings import _check_glide_amount, StepRowSetting, StepRowSettings
from llamatron.model.file.checks import number
from llamatron.model.schema.setting import Checked, described

class GlideSettings(StepRowSettings):
    """A Glide's settings: its row, and how far a note starting on a step that's on runs into the next."""

    __slots__ = ()

    GENERATOR = Glide
    SETTINGS = described(step_row_settings.STEP_ROW_SETTINGS[0], step_row_settings.STEP_ROW_SETTINGS[1], Checked(name=StepRowSetting.GLIDE_AMOUNT, check=_check_glide_amount), step_row_settings.STEP_ROW_SETTINGS[2])

    def amounts(self):
        return {StepRowSetting.GLIDE_AMOUNT: self.get_glide_amount()}

    def get_written_glide_amount(self):
        """Return the glide amount as the file writes it, or None when it's left out."""
        return self.get_written(StepRowSetting.GLIDE_AMOUNT)

    def get_glide_amount(self):
        written = self.get_written(StepRowSetting.GLIDE_AMOUNT)
        return step_row_settings.DEFAULT_GLIDE_AMOUNT if written is None else number(written)
