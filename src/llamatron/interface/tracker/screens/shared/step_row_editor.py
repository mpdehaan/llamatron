# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The step row editor: one of a generator's rows of steps, each on or off, such as a Timing generator's Rush.

Left and Right move along the steps, stopping at the ends; Space or Enter turns the cursor's step on
or off, drawn as every toggle is, the dot or a blank; I inserts a step that's off before the
cursor's and D removes the cursor's, from 1 to 16 steps. The cursor's step is marked in reverse
video, as in the offsets editor, and the line above the grid says what a step that's on does.
"""

from rich.text import Text

from llamatron.interface.tracker import drawing, keybindings
from llamatron.interface.tracker.drawing import Box, Style
from llamatron.interface.tracker.screens.shared.generator_editor import GeneratorEditor
from llamatron.interface.tracker.screens.shared.step_editor import StepEditor
from llamatron.interface.tracker.screens.shared.step_grid import StepGrid
from llamatron.model.schema import limits
from llamatron.user_strings import help as help_text, labels, marks

class StepRowEditor(GeneratorEditor, StepGrid, StepEditor):
    """One of a generator's rows of on-or-off steps, given the generator's section and the row's StepsView as it opens."""

    KEYS = keybindings.StepRowEditor
    HELP = help_text.HELP_STEP_ROW_EDITOR
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    CRUMBS_AFTER = (labels.Crumb.STEPS,)
    CELL_WIDTH = 5

    def __init__(self, *, holder, name, section, steps, built_in=None):
        # The section names the generator before the page opens, since opening asks for the page's crumbs and caption.
        self.SECTION = section
        self._steps = steps
        super().__init__(holder=holder, name=name, built_in=built_in)

    def values(self):
        return self.row().get_steps()

    def row(self):
        """Return the row of steps the page edits."""
        return self.settings().step_row(self._steps.row)

    def step_count(self):
        return len(self.values())

    def keys(self):
        self.keep_step()
        result = [
            self.bind(self.KEYS.BACK, action=self.go_back), self.bind(self.KEYS.MOVE, action=self.move_cursor, wants_key=True),
            self.bind(self.KEYS.TOGGLE, action=self.toggle),
        ]
        if self.step_count() < limits.MAX_STEP_ROW:
            result.append(self.bind(self.KEYS.INSERT_STEP, action=self.insert))
        if self.step_count() > limits.MIN_STEP_ROW:
            result.append(self.bind(self.KEYS.REMOVE_STEP, action=self.remove_step))
        return result

    def move_cursor(self, name):
        self.move_step(name)

    def toggle(self):
        """Turn the cursor's step on or off."""
        self.document().change_set(self.row().set_cell, step=self.step, value=not self.values()[self.step])

    def insert(self):
        self.document().change_set(self.row().insert_cell, self.step)

    def remove_step(self):
        self.document().change_set(self.row().remove_cell, self.step)
        self.keep_step()

    def body(self, *, width, height):
        self.keep_step()
        first, last = self.scroll_to_cursor(width)
        places = range(first, last)
        values = self.values()
        return [
            self.with_steps_shown(text=self._steps.note, style=Style.DIM, width=width, first=first, last=last),
            Text(drawing.NOTHING),
            self.grid_rule(left=Box.TOP_LEFT, middle=Box.TOP_TEE, right=Box.TOP_RIGHT, count=len(places)),
            self.grid_line(label=labels.MSG_STEP_NUMBER_ROW_LABEL, cells=[(place, str(place + 1)) for place in places], selected=self.step, bold=True),
            self.grid_rule(left=Box.LEFT_TEE, middle=Box.CROSS, right=Box.RIGHT_TEE, count=len(places)),
            self.grid_line(label=self._steps.row_name, cells=[(place, marks.MSG_TOGGLE_ON if values[place] else marks.MSG_TOGGLE_OFF) for place in places], selected=self.step),
            self.grid_rule(left=Box.BOTTOM_LEFT, middle=Box.BOTTOM_TEE, right=Box.BOTTOM_RIGHT, count=len(places)),
        ]
