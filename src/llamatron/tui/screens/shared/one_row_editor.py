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
"""What the one-row editors share: a row of numbers either side of zero, one to a step, edited under a cursor.

The offsets editor (an arpeggiator's offsets) and the groove editor (a groove's cells) are each
one row, so no row lies below the cursor and Up and Down change the cursor's number. Left and
Right move along the row, digits type a number and keep its sign, I inserts a step and D removes
one. A row wider than the screen scrolls sideways like the pattern editor.
A new editor of this kind says what its values are, how one is stored, and how its grid is
drawn.
"""

from llamatron.tui import key_table, keybindings
from llamatron.tui.screens.shared.step_editor import StepEditor
from llamatron.tui.screens.shared.step_grid import StepGrid


# The fewest steps a row can have, unless a page says otherwise.
ONE_STEP = 1
# What a step that holds no number counts as when it is stepped.
NO_VALUE_COUNTS_AS = 0
# The lowest number that digits type, since the sign is kept from the number already there.
LOWEST_TYPED = 0


class OneRowEditor(StepGrid, StepEditor):
    """A page that edits one row of numbers.

    A page of this kind names CELL_WIDTH, how wide a cell is drawn; MOST, the largest number
    either side of zero; MOST_STEPS and FEWEST_STEPS, how long the row can be; and INSERT and
    REMOVE, its own bindings for inserting and removing a step. The page answers values(), and
    changes the row through set_value(value), add_step() and remove_step_here(), each at the cursor.
    """

    KEYS = keybindings.OneRowEditor
    CELL_WIDTH = None
    MOST = None
    MOST_STEPS = None
    FEWEST_STEPS = ONE_STEP
    INSERT = None
    REMOVE = None

    def values(self):
        """Return the row's values, one to a step."""
        raise NotImplementedError

    def set_value(self, value):
        """Store a value on the cursor's step."""
        raise NotImplementedError

    def add_step(self):
        """Insert a step at the cursor."""
        raise NotImplementedError

    def remove_step_here(self):
        """Remove the cursor's step."""
        raise NotImplementedError

    def most(self):
        """Return the largest number either side of zero on the row the cursor edits, MOST unless a page with several rows says otherwise."""
        return self.MOST

    def can_edit(self):
        """Return whether the row can be changed, which a page that only shows some rows answers."""
        return True

    def more_keys(self):
        """Return the keys the page has beyond the row's own."""
        return []

    def step_count(self):
        return len(self.values())

    def value_here(self):
        return self.values()[self.step]

    def keys(self):
        self.keep_step()
        result = [self.bind(self.KEYS.BACK, action=self.go_back), self.bind(self.KEYS.MOVE, action=self.move_cursor, wants_key=True)]
        if self.can_edit():
            result += [
                self.bind(self.KEYS.LESS, action=lambda: self.nudge(key_table.STEP_BACK)),
                self.bind(self.KEYS.MORE, action=lambda: self.nudge(key_table.STEP_FORWARD)),
                self.bind(self.KEYS.TYPE, action=self.type_digit, wants_key=True),
            ]
            if self.step_count() < self.MOST_STEPS:
                result.append(self.bind(self.INSERT, action=self.insert))
            if self.step_count() > self.FEWEST_STEPS:
                result.append(self.bind(self.REMOVE, action=self.remove_step))
            result += self.more_keys()
        return result

    def move_cursor(self, name):
        self.move_step(name)

    def type_digit(self, digit):
        """Build up a number in the cursor's cell, keeping its sign, and start again when the number would go out of range."""
        number = self.typed_number(digit=digit, low=LOWEST_TYPED, high=self.most())
        if number is not None:
            current = self.value_here()
            self.set_value(-number if current is not None and current < 0 else number)

    def nudge(self, offset):
        """Make the cursor's number one more or one less, stopping at the largest either side of zero."""
        current = self.value_here()
        if current is None:
            current = NO_VALUE_COUNTS_AS
        self.set_value(max(min(current + offset, self.most()), -self.most()))

    def insert(self):
        self.add_step()

    def remove_step(self):
        self.remove_step_here()
        self.keep_step()
