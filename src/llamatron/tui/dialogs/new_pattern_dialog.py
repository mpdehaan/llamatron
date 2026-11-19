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
"""The New Pattern dialog: asks what kind of pattern to make, one written for a scale of so many notes or a drum pattern.

Up and Down move between the Scale length, the Drum pattern toggle and the row of buttons. On
the Scale length [ and ] step the number, any scale below the fewest notes, and Enter is OK; on the toggle Space or Enter flips
it, and a drum pattern has no scale length, so that row then shows the blocked cell's mark; on
the buttons Left and Right choose and Enter presses. Esc cancels.
"""

from rich.text import Text
from typing import NamedTuple

from llamatron.composition import limits
from llamatron.strings import labels, marks, messages
from llamatron.tui import drawing, key_table, keybindings
from llamatron.tui.components.button_row import button_row
from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.drawing import cursor_mark, Style
from llamatron.tui.key_table import cursor_moved

# The rows the cursor moves over, in the order drawn.
SCALE_LENGTH = 0
DRUM = 1
BUTTONS = 2
ROWS = 3
LABELS = (labels.MSG_SCALE_LENGTH_LABEL, labels.MSG_DRUM_PATTERN_LABEL)
LABEL_WIDTH = max(len(label) for label in LABELS) + 4
# The buttons, in the order drawn, and the binding whose key each shows.
OK_BUTTON = 0
CANCEL_BUTTON = 1
BUTTON_BINDINGS = (keybindings.NewPatternDialog.OK, keybindings.Dialog.CANCEL)
NO_BUTTON = -1
# What the Scale length steps through: any scale, then each number of notes.
SCALE_LENGTHS = (None, *range(limits.MIN_SCALE_LENGTH, limits.MAX_SCALE_LENGTH + 1))


class NewPatternKind(NamedTuple):
    """What the dialog answers: whether the pattern is a drum pattern, and the scale length of one that is not."""

    drum: bool
    scale_length: int


class NewPatternDialog(Dialog):
    """Asks for a new pattern's scale length, or whether it is a drum pattern, and answers a NewPatternKind, or nothing when cancelled."""

    KEYS = keybindings.NewPatternDialog

    def __init__(self):
        super().__init__()
        self.title = messages.MSG_NEW_PATTERN_TITLE
        self.scale_length = limits.NEW_PATTERN_SCALE_LENGTH
        self.drum = False
        self.row = SCALE_LENGTH
        self.button = OK_BUTTON

    def keys(self):
        bound = [self.bind(self.KEYS.CANCEL, action=lambda: self.dismiss(None)), self.bind(self.KEYS.SELECT, action=self.move, wants_key=True)]
        if self.row == SCALE_LENGTH:
            if not self.drum:
                bound += [self.bind(self.KEYS.LESS, action=lambda: self.step(key_table.STEP_BACK)), self.bind(self.KEYS.MORE, action=lambda: self.step(key_table.STEP_FORWARD))]
            bound.append(self.bind(self.KEYS.OK, action=self.accept))
        elif self.row == DRUM:
            bound.append(self.bind(self.KEYS.TOGGLE, action=self.toggle))
        else:
            bound += [self.bind(self.KEYS.CHOOSE_BUTTON, action=self.choose_button, wants_key=True), self.bind(self.KEYS.PRESS, action=self.press)]
        return self.in_order(bound)

    def move(self, name):
        self.row = cursor_moved(place=self.row, name=name, count=ROWS)

    def choose_button(self, name):
        self.button = cursor_moved(place=self.button, name=name, count=len(labels.MSG_NEW_PATTERN_BUTTONS))

    def step(self, direction):
        """Step the scale length, any scale below the fewest notes, stopping at either end."""
        place = SCALE_LENGTHS.index(self.scale_length) + direction
        self.scale_length = SCALE_LENGTHS[max(0, min(place, len(SCALE_LENGTHS) - 1))]

    def toggle(self):
        self.drum = not self.drum

    def press(self):
        if self.button == OK_BUTTON:
            self.accept()
        else:
            self.dismiss(None)

    def accept(self):
        self.dismiss(NewPatternKind(drum=self.drum, scale_length=None if self.drum else self.scale_length))

    def values(self):
        """Return each field's value as shown: a drum pattern's scale length is the blocked cell's mark."""
        length = marks.MSG_ANY_SCALE_LENGTH if self.scale_length is None else str(self.scale_length)
        return (marks.MSG_BLOCKED_CELL if self.drum else length, marks.MSG_TOGGLE_ON if self.drum else drawing.NOTHING)

    def lines(self, width):
        lines = []
        for row, (label, value) in enumerate(zip(LABELS, self.values())):
            line = Text(cursor_mark(row == self.row) + label.ljust(LABEL_WIDTH))
            blocked = row == SCALE_LENGTH and self.drum
            line.append(value, style=Style.DIM if blocked else Style.BOLD if row == self.row else Style.PLAIN)
            lines.append(line)
        buttons = [(binding[1], label) for label, binding in zip(labels.MSG_NEW_PATTERN_BUTTONS, BUTTON_BINDINGS)]
        return [*lines, Text(drawing.NOTHING), *button_row(buttons=buttons, selected=self.button if self.row == BUTTONS else NO_BUTTON)]
