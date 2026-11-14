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
"""One row of the pattern editor: what each of its cells shows, and what its keys do when the cursor is on it."""

from llamatron.composition.row_descriptions import ROW_DESCRIPTIONS
from llamatron.tui.drawing import NOTHING
from llamatron.tui.key_table import STEP_BACK, STEP_FORWARD, BindsKeys
from llamatron.strings.labels import MSG_ROW_LABELS
from llamatron.strings.marks import MSG_BLOCKED_CELL, MSG_UNSET_MARK
from llamatron.tui import keybindings


class PatternRow(BindsKeys):
    """A row of the step grid, which the editor builds once for each row name.

    A row reads and writes its values through the editor, which knows the pattern and the cursor,
    so a row holds no data of its own. Subclasses say what a cell shows, which keys work on the
    row, and whether a rest can hold its value.
    """

    KEYS = keybindings.PatternRow

    __slots__ = ('editor', 'name')

    def described(self):
        """Return the row's one description, which says what a step may hold on the row: its limits, its choices and what a blank step plays as (composition/row_descriptions.py)."""
        return ROW_DESCRIPTIONS[self.name]

    def __init__(self, *, editor, name):
        self.editor = editor
        self.name = name

    def label(self):
        return MSG_ROW_LABELS[self.name]

    def labels(self):
        """Return the label of each line the row takes, top to bottom, which is one line unless a subclass draws more."""
        return [self.label()]

    def height(self):
        """Return how many lines the row takes on screen."""
        return len(self.labels())

    def cursor_line(self):
        """Return which of the row's lines the cursor sits on, which is the last: the one with the value."""
        return self.height() - 1

    def rule_before(self):
        """Return whether a rule is drawn over the row, unless one was just drawn, which a section's row asks for."""
        return False

    def rule_after(self):
        """Return whether a rule is drawn under the row, to set it apart from the rows beneath."""
        return False

    def marks_label(self):
        """Return whether the cursor on this row is shown on its label rather than on a cell, which a section's row does, since it has no cells of its own."""
        return False

    def edge_text(self, *, step):
        """Return what takes the place of the divider before a step's cell, or None to draw the divider, which a bar can run through."""
        return None

    def on_rests(self):
        """Return whether a rest can hold this row's value, so that its keys work on an empty step and a cell there shows it."""
        return False

    def value(self, *, step=None):
        return self.editor.value(row=self.name, step=step)

    def set_value(self, value):
        self.editor.set_value(value=value, row=self.name)

    def is_note(self, *, step=None):
        return self.editor.is_note(step=step)

    def blocked(self, *, step=None):
        """Return whether a step can't take a value on this row, which its cell shows as (X) and which takes the row's keys off the legend: an empty step on a row only notes hold."""
        return not (self.is_note(step=step) or self.on_rests())

    def editable(self):
        """Return whether the cursor's step can take a value on this row."""
        return not self.blocked()

    def adjust_keys(self):
        """Return the keys that nudge the cursor's value: [ for less and ] for more on the legend and in the help, with -, + and = working too."""
        return [
            self.bind(self.KEYS.LESS, action=lambda: self.nudge(STEP_BACK)),
            self.bind(self.KEYS.MORE, action=lambda: self.nudge(STEP_FORWARD)),
        ]

    def keys(self):
        """Return the row's keys when the cursor is on it, which the editor lists after its own."""
        return []

    def cell_text(self, *, step):
        """Return what a cell shows: nothing on a rest unless rests hold this row, and a dot for a value that isn't set."""
        if not self.is_note(step=step) and not self.on_rests():
            return NOTHING
        value = self.value(step=step)
        return MSG_UNSET_MARK if value is None else str(value)

    def cell_lines(self, *, step):
        """Return what a step's cell shows on each of the row's lines, top to bottom: its text, or the blocked mark on the value's line where the step can't take one."""
        if self.blocked(step=step):
            return [NOTHING] * (self.height() - 1) + [MSG_BLOCKED_CELL]
        return [self.cell_text(step=step)]
