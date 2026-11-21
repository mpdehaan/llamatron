# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Rush plugin's model: its settings, which own a row of steps, and how far a note moves early."""

from llamatron.engine.generators import settings_base, step_row
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.engine.generators.step_row import StepRowSetting
from llamatron.model.objects.llama_data import or_default
from llamatron.model.schema.setting import described

# How far a note starting on a step that's on moves early, as a percentage of a step, unless set.
DEFAULT_RUSH = 15


class RushSettings(GeneratorSettings):
    """A Rush's settings: the row of steps it owns, and how far a note starting on a step that's on plays early, as a share of a step.

    It runs on no clip's notes itself: its controller hands the Realizer a row that moves the notes in their timing, on top
    of the groove (engine/timing/timing.py), so GENERATOR is None.
    """

    __slots__ = ()

    SETTINGS = described(step_row.STEPS_SETTING, step_row.STEP_SETTING, step_row.MOVING_AMOUNT_SETTING, settings_base.RESTART_SETTING)
    REQUIRED = [StepRowSetting.STEPS]

    @classmethod
    def new(cls):
        """Return the settings a new one starts with: four steps, the first on."""
        return cls(step_row.new_row_data())

    def step_row(self):
        """Return the row of steps it owns."""
        return step_row.StepRow(self)

    def get_amount(self):
        return or_default(value=self.get_written(StepRowSetting.AMOUNT), default=DEFAULT_RUSH)
