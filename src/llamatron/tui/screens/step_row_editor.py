# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""The step row editor: a Glide's, a Shorten's, a Rush's or a Drag's row of steps, each on or off, the user's design of 2026-11-11.

Left and Right move along the steps, stopping at the ends; Space or Enter turns the cursor's step on
or off, drawn as every toggle is, the dot or a blank; I inserts a step that's off before the
cursor's and D removes the cursor's, from 1 to 16 steps. The cursor's step is marked in reverse
video, as in the offsets editor, and the line above the grid says what a step that's on does.
"""

from rich.text import Text

from llamatron.composition.generator_settings import StepRowSetting
from llamatron.composition.limits import MAX_STEP_ROW, MIN_STEP_ROW
from llamatron.strings.help import HELP_STEP_ROW_EDITOR
from llamatron.strings.labels import Crumb, MSG_STEP_ROW_LABEL, MSG_STEP_ROW_NAMES
from llamatron.strings.marks import MSG_TOGGLE_OFF, MSG_TOGGLE_ON
from llamatron.strings.messages import MSG_STEP_ROW_NOTES
from llamatron.tui import keybindings
from llamatron.tui.drawing import Box, NOTHING, Style
from llamatron.tui.key_table import cursor_moved
from llamatron.tui.screens.shows_named_item import ShowsNamedItem
from llamatron.tui.screens.step_editor import StepEditor
from llamatron.tui.screens.step_grid import StepGrid

class StepRowEditor(ShowsNamedItem, StepGrid, StepEditor):
    """A row of on-or-off steps. A page of this kind names its SECTION, KIND and CRUMBS_BEFORE."""

    KEYS = keybindings.StepRowEditor
    HELP = HELP_STEP_ROW_EDITOR
    CRUMBS_AFTER = (Crumb.STEPS,)
    CELL_WIDTH = 5
    KIND = None

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def generator(self):
        return self.document().song().get_generator_settings(kind=self.KIND, name=self.item)

    def values(self):
        return self.generator().get_steps()

    def steps(self):
        return len(self.values())

    def store(self, values):
        self.document().set_generator_setting(section=self.SECTION, name=self.item, setting=StepRowSetting.STEPS, value=values)

    def keys(self):
        self.keep_step()
        result = [
            self.bind(self.KEYS.BACK, action=self.go_back), self.bind(self.KEYS.MOVE, action=self.move, wants_key=True),
            self.bind(self.KEYS.TOGGLE, action=self.toggle),
        ]
        if self.steps() < MAX_STEP_ROW:
            result.append(self.bind(self.KEYS.INSERT_STEP, action=self.insert))
        if self.steps() > MIN_STEP_ROW:
            result.append(self.bind(self.KEYS.REMOVE_STEP, action=self.remove_step))
        return result

    def move(self, name):
        self.step = cursor_moved(place=self.step, name=name, count=self.steps())

    def toggle(self):
        """Turn the cursor's step on or off."""
        values = self.values()
        values[self.step] = not values[self.step]
        self.store(values)

    def insert(self):
        values = self.values()
        self.store(values[:self.step] + [False] + values[self.step:])

    def remove_step(self):
        values = self.values()
        self.store(values[:self.step] + values[self.step + 1:])
        self.keep_step()

    def body(self, *, width, height):
        self.keep_step()
        first, last = self.scroll_to_cursor(width)
        places = range(first, last)
        values = self.values()
        return [
            self.with_steps_shown(text=MSG_STEP_ROW_NOTES[self.SECTION], style=Style.DIM, width=width, first=first, last=last),
            Text(NOTHING),
            self.grid_rule(left=Box.TOP_LEFT, middle=Box.TOP_TEE, right=Box.TOP_RIGHT, count=len(places)),
            self.grid_line(label=MSG_STEP_ROW_LABEL, cells=[(place, str(place + 1)) for place in places], selected=self.step, bold=True),
            self.grid_rule(left=Box.LEFT_TEE, middle=Box.CROSS, right=Box.RIGHT_TEE, count=len(places)),
            self.grid_line(label=MSG_STEP_ROW_NAMES[self.SECTION], cells=[(place, MSG_TOGGLE_ON if values[place] else MSG_TOGGLE_OFF) for place in places], selected=self.step),
            self.grid_rule(left=Box.BOTTOM_LEFT, middle=Box.BOTTOM_TEE, right=Box.BOTTOM_RIGHT, count=len(places)),
        ]
