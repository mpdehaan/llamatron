# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the generators that act on chosen steps share: Glide, Shorten, Rush and Drag each hold a row of steps and an
amount."""

from llamatron.engine.generators import settings_base
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.math.rational import Rational
from llamatron.model.file.checks import in_whole_notes, is_true_or_false, number, time_length
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.llama_data import or_default
from llamatron.model.objects.traits import HasCells
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.setting import Checked, described, WholeNumber
from llamatron.user_strings import errors

class StepRowSetting:
    """A Glide's, a Shorten's, a Rush's or a Drag's settings, as a file names them: its row of steps, each on or off, how long each step is, and how much a step that's on changes its note."""

    RESTART = file_format.GENERATOR_RESTART
    STEPS = 'steps'
    STEP = 'step'
    GLIDE_AMOUNT = 'glide_amount'
    SHORTEN = 'shorten'
    AMOUNT = 'amount'


# A gliding note runs 1/128 into the next unless set, as the pattern's Glide row has always had it, from 1/256 to 1/16; a shortened note plays 70%; a rush moves a note 15% of a step early and a drag 20% late.
DEFAULT_GLIDE_AMOUNT = Rational(1, 128)


LEAST_GLIDE_AMOUNT = Rational(1, 256)


MOST_GLIDE_AMOUNT = Rational(1, 16)


DEFAULT_SHORTEN = 70


DEFAULT_RUSH = 15


DEFAULT_DRAG = 20


NEW_STEP_ROW = [True, False, False, False]


NO_RUSH_OR_DRAG = 0


def _check_step_row(values):
    """Check a row of steps: a list of 1 to MAX_STEP_ROW, each on or off."""
    fits = isinstance(values, list) and limits.MIN_STEP_ROW <= len(values) <= limits.MAX_STEP_ROW and all(is_true_or_false(value) for value in values)
    if not fits:
        raise InvalidValue(errors.ERR_BAD_STEP_ROW.format(name=StepRowSetting.STEPS, most=limits.MAX_STEP_ROW, value=values))


def _check_glide_amount(value):
    amount = number(value)
    if not LEAST_GLIDE_AMOUNT <= amount <= MOST_GLIDE_AMOUNT:
        raise InvalidValue(errors.ERR_BAD_GLIDE_AMOUNT.format(least=LEAST_GLIDE_AMOUNT, most=MOST_GLIDE_AMOUNT, value=value))


# What every row of steps holds besides its amount: the row, its step and its Restart.
STEP_ROW_SETTINGS = (Checked(name=StepRowSetting.STEPS, check=_check_step_row), Checked(name=StepRowSetting.STEP, check=time_length), settings_base.RESTART_SETTING)


class StepRowSettings(HasCells, GeneratorSettings):
    """What a Glide's, a Shorten's, a Rush's and a Drag's settings share: a row of on-or-off steps from each clip's start, each step as long as its step, the clip's pattern's step size unless set."""

    __slots__ = ()

    REQUIRED = [StepRowSetting.STEPS]

    @classmethod
    def new(cls):
        """Return the settings a new one starts with: four steps, the first on."""
        return cls({StepRowSetting.STEPS: list(NEW_STEP_ROW)})

    def get_steps(self):
        return [bool(value) for value in (self.get_written(StepRowSetting.STEPS) or NEW_STEP_ROW)]

    def get_step(self):
        return self.get_written(StepRowSetting.STEP)

    # Editing the row one step at a time, as its editor does.

    def set_cell(self, *, step, value):
        """Turn one step of the row on or off."""
        steps = self.get_steps()
        steps[step] = bool(value)
        self.set_setting(name=StepRowSetting.STEPS, value=steps)

    def insert_cell(self, step):
        """Add a step that is off before a step of the row."""
        steps = self.get_steps()
        self.set_setting(name=StepRowSetting.STEPS, value=steps[:step] + [False] + steps[step:])

    def remove_cell(self, step):
        steps = self.get_steps()
        self.set_setting(name=StepRowSetting.STEPS, value=steps[:step] + steps[step + 1:])

    def step_length(self, *, default_step, bar):
        """Return how long each step is, in whole notes."""
        step = self.get_step()
        return default_step if step is None else in_whole_notes(time=step, bar=bar)

    def _with_defaults(self, *, values, default_seed, default_step, bar):
        return {StepRowSetting.STEPS: self.get_steps(), StepRowSetting.STEP: self.step_length(default_step=default_step, bar=bar), **self.amounts()}

    def amounts(self):
        """Return the generator's amount, as its generator takes it."""
        return {}


class MovingRowSettings(StepRowSettings):
    """A Rush's or a Drag's settings: its row, and how far a note starting on a step that's on moves, as a share of a step.

    It runs on no clip's notes itself: the renderer reads it for each clip that names it, and the
    exporters' timing moves the notes, on top of the groove (engine/timing/timing.py), so GENERATOR is None.
    """

    __slots__ = ()

    GENERATOR = None
    DEFAULT_AMOUNT = None
    SETTINGS = described(
        STEP_ROW_SETTINGS[0], STEP_ROW_SETTINGS[1], WholeNumber(name=StepRowSetting.AMOUNT, lowest=NO_RUSH_OR_DRAG, highest=limits.MAX_RUSH_OR_DRAG, error=errors.ERR_BAD_SHAPE_PERCENT),
        STEP_ROW_SETTINGS[2],
    )

    def get_amount(self):
        return or_default(value=self.get_written(StepRowSetting.AMOUNT), default=self.DEFAULT_AMOUNT)
