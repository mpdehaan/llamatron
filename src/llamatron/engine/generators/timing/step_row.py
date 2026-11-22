# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A row of on-or-off steps a Timing generator's part owns: steps from each clip's start, each as long as its step, the clip's
pattern's step size unless set. A Rush, a Drag, a Shorten and a Glide each own one beside an amount of their own."""

from llamatron.engine.generators.timing import parts
from llamatron.model.file.checks import in_whole_notes, is_true_or_false
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.traits import HasCells
from llamatron.model.schema import limits
from llamatron.user_strings import errors

# The row a part shows before any is written: four steps, every one off, so that the part changes nothing until a step is lit.
UNLIT_ROW = [False, False, False, False]


def check_step_row(values):
    """Check a row of steps: a list of 1 to MAX_STEP_ROW, each on or off."""
    fits = isinstance(values, list) and limits.MIN_STEP_ROW <= len(values) <= limits.MAX_STEP_ROW and all(is_true_or_false(value) for value in values)
    if not fits:
        raise InvalidValue(errors.ERR_BAD_STEP_ROW.format(name=parts.STEPS, most=limits.MAX_STEP_ROW, value=values))


class StepRow(HasCells):
    """One part's row of steps, read and edited through the Timing generator's settings: each step on or off, from each clip's
    start, each as long as its step, the clip's pattern's step size unless set. A part with no row written shows four steps, all off."""

    __slots__ = ('_owner', '_part')

    def __init__(self, *, owner, part):
        """owner is the settings that hold the row, part which of its parts the row is."""
        self._owner = owner
        self._part = part

    def get_steps(self):
        written = self._owner.get_written(parts.steps_of(self._part)) or UNLIT_ROW
        return [bool(value) for value in written]

    def is_lit(self):
        """Return whether any of its steps is on, which puts the part in force."""
        return any(self.get_steps())

    def get_step(self):
        return self._owner.get_written(parts.step_of(self._part))

    def step_length(self, *, default_step, bar):
        """Return how long each step is, in whole notes."""
        step = self.get_step()
        if step is None:
            return default_step
        return in_whole_notes(time=step, bar=bar)

    # Editing the row one step at a time, as its editor does.

    def set_cell(self, *, step, value):
        """Turn one step of the row on or off."""
        steps = self.get_steps()
        steps[step] = bool(value)
        self._owner.set_setting(name=parts.steps_of(self._part), value=steps)

    def insert_cell(self, step):
        """Add a step that is off before a step of the row."""
        steps = self.get_steps()
        self._owner.set_setting(name=parts.steps_of(self._part), value=steps[:step] + [False] + steps[step:])

    def remove_cell(self, step):
        steps = self.get_steps()
        self._owner.set_setting(name=parts.steps_of(self._part), value=steps[:step] + steps[step + 1:])
