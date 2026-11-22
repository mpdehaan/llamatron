# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The row of steps a plugin's model may own: on-or-off steps from each clip's start, each as long as its step, which a Glide,
a Shorten, a Rush and a Drag each hold beside an amount of their own. The part is composed into a model, never inherited."""

from llamatron.model.file.checks import in_whole_notes, is_true_or_false, time_length
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.traits import HasCells
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.setting import Checked, WholeNumber
from llamatron.user_strings import errors

class StepRowSetting:
    """A Glide's, a Shorten's, a Rush's or a Drag's settings, as a file names them: its row of steps, each on or off, how long each step is, and how much a step that's on changes its note."""

    RESTART = file_format.GENERATOR_RESTART
    STEPS = 'steps'
    STEP = 'step'
    GLIDE_AMOUNT = 'glide_amount'
    SHORTEN = 'shorten'
    AMOUNT = 'amount'








NEW_STEP_ROW = [True, False, False, False]


NO_RUSH_OR_DRAG = 0


def _check_step_row(values):
    """Check a row of steps: a list of 1 to MAX_STEP_ROW, each on or off."""
    fits = isinstance(values, list) and limits.MIN_STEP_ROW <= len(values) <= limits.MAX_STEP_ROW and all(is_true_or_false(value) for value in values)
    if not fits:
        raise InvalidValue(errors.ERR_BAD_STEP_ROW.format(name=StepRowSetting.STEPS, most=limits.MAX_STEP_ROW, value=values))



# The row and its step, which every model owning a row of steps describes among its settings, with its own amount and its Restart.
STEPS_SETTING = Checked(name=StepRowSetting.STEPS, check=_check_step_row)
STEP_SETTING = Checked(name=StepRowSetting.STEP, check=time_length)
# How far a note starting on a step that's on moves, as a share of a step, for a model whose row moves notes early or late.
MOVING_AMOUNT_SETTING = WholeNumber(name=StepRowSetting.AMOUNT, lowest=NO_RUSH_OR_DRAG, highest=limits.MAX_RUSH_OR_DRAG, error=errors.ERR_BAD_SHAPE_PERCENT)


def new_row_data():
    """Return the settings a new model owning a row starts with: four steps, the first on."""
    return {StepRowSetting.STEPS: list(NEW_STEP_ROW)}


class StepRow(HasCells):
    """The row of steps a plugin's model owns, read and edited through the model's settings: each step on or off, from each
    clip's start, each as long as its step, the clip's pattern's step size unless set."""

    __slots__ = ('_owner',)

    def __init__(self, owner):
        """owner is the model whose settings hold the row."""
        self._owner = owner

    def get_steps(self):
        return [bool(value) for value in (self._owner.get_written(StepRowSetting.STEPS) or NEW_STEP_ROW)]

    def get_step(self):
        return self._owner.get_written(StepRowSetting.STEP)

    def step_length(self, *, default_step, bar):
        """Return how long each step is, in whole notes."""
        step = self.get_step()
        if step is None:
            return default_step
        return in_whole_notes(time=step, bar=bar)

    def generator_values(self, *, default_step, bar):
        """Return the row and its step as the generator that runs takes them."""
        return {StepRowSetting.STEPS: self.get_steps(), StepRowSetting.STEP: self.step_length(default_step=default_step, bar=bar)}

    # Editing the row one step at a time, as its editor does.

    def set_cell(self, *, step, value):
        """Turn one step of the row on or off."""
        steps = self.get_steps()
        steps[step] = bool(value)
        self._owner.set_setting(name=StepRowSetting.STEPS, value=steps)

    def insert_cell(self, step):
        """Add a step that is off before a step of the row."""
        steps = self.get_steps()
        self._owner.set_setting(name=StepRowSetting.STEPS, value=steps[:step] + [False] + steps[step:])

    def remove_cell(self, step):
        steps = self.get_steps()
        self._owner.set_setting(name=StepRowSetting.STEPS, value=steps[:step] + steps[step + 1:])
