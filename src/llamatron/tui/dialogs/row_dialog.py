# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Row dialog: one row of numbers, each cell a bar over its number, for a row dealt to a player's notes in turn.

Left and Right move along the row and stop at its ends, [ and ] make the number under the cursor
less and more between the row's lowest and highest, I inserts a cell like the cursor's and D removes
the cursor's, Bksp puts back the row the dialog was told is the usual one, Enter is OK, answering
with the row, and Esc is CANCEL, changing nothing. A row whose numbers go either side of zero is
drawn around a zero line."""

from rich.text import Text

from llamatron.strings import labels, marks
from llamatron.tui import drawing, key_table, keybindings
from llamatron.tui.components.button_row import button_row
from llamatron.tui.cursor import Cursor
from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.drawing import legend, Style

# The OK button is the one Enter presses, so it is the one drawn selected.
OK = 0
BUTTON_BINDINGS = (keybindings.RowDialog.DONE, keybindings.RowDialog.CANCEL)
# The most levels a bar is drawn with either side of zero: a row with a wider range has several numbers to a level.
MOST_LEVELS = 8
# A cell is wide enough for the longest number and a space, so that the longest row fits an 80 by 24 console.
CELL_WIDTH = 4
ZERO = 0


class RowDialog(Dialog):
    """Answers with the row as edited, a list of numbers, or None when cancelled."""

    KEYS = keybindings.RowDialog

    def __init__(self, *, title, values, lowest, highest, fewest, most, usual):
        super().__init__()
        self.title = title
        self.values = list(values)
        self.lowest = lowest
        self.highest = highest
        self.fewest = fewest
        self.most = most
        # The row Bksp puts back.
        self.usual = list(usual)
        self.cursor = Cursor(place=0)

    def keys(self):
        result = [
            self.bind(self.KEYS.CANCEL, action=lambda: self.dismiss(None)),
            self.bind(self.KEYS.MOVE, action=self.move_cursor, wants_key=True),
            self.bind(self.KEYS.LESS, action=lambda: self.nudge(key_table.STEP_BACK)),
            self.bind(self.KEYS.MORE, action=lambda: self.nudge(key_table.STEP_FORWARD)),
        ]
        if len(self.values) < self.most:
            result.append(self.bind(self.KEYS.INSERT_CELL, action=self.insert_cell))
        if len(self.values) > self.fewest:
            result.append(self.bind(self.KEYS.REMOVE_CELL, action=self.remove_cell))
        return [*result, self.bind(self.KEYS.USUAL, action=self.put_back), self.bind(self.KEYS.DONE, action=lambda: self.dismiss(list(self.values)))]

    def move_cursor(self, name):
        self.cursor.move(name=name, count=len(self.values))

    def nudge(self, offset):
        """Make the cursor's number one more or one less, stopping at the row's lowest and highest."""
        self.values[self.cursor.get_place()] = max(min(self.values[self.cursor.get_place()] + offset, self.highest), self.lowest)

    def insert_cell(self):
        """Insert a cell like the cursor's after it, and move onto it."""
        self.values.insert(self.cursor.get_place() + 1, self.values[self.cursor.get_place()])
        self.cursor.shift(1)

    def remove_cell(self):
        del self.values[self.cursor.get_place()]
        self.cursor.set_place(min(self.cursor.get_place(), len(self.values) - 1))

    def put_back(self):
        self.values = list(self.usual)
        self.cursor.set_place(min(self.cursor.get_place(), len(self.values) - 1))

    def legend_lines(self, width):
        """Return the keys listed under the row, leaving out OK and CANCEL, which the buttons name."""
        return legend(keys=[item for item in self.keys() if item.shown], width=width)

    def wanted_width(self):
        return max(super().wanted_width(), self.most * CELL_WIDTH + len(self.level_label(self.highest)) + CELL_WIDTH)

    # Drawing.

    def numbers_to_a_level(self):
        """Return how many numbers one level of a bar stands for, so that the widest range fits the most levels."""
        return -(-max(self.highest, -self.lowest) // MOST_LEVELS)

    def levels(self):
        """Return the levels drawn, the highest first, each the number a bar must reach to fill it; those under zero are negative."""
        size = self.numbers_to_a_level()
        above = [level * size for level in range(-(-self.highest // size), 0, -1)]
        below = [-level * size for level in range(1, -(-(-self.lowest) // size) + 1)] if self.lowest < ZERO else []
        return above, below

    def level_label(self, level):
        return marks.MSG_ROW_DIALOG_LEVEL.format(level=level)

    def bar_line(self, level):
        """Return one level of every cell's bar: filled where the cell's number reaches the level, on the level's side of zero."""
        size = self.numbers_to_a_level()
        line = Text(self.level_label(level), style=Style.DIM)
        for value in self.values:
            reaches = value > level - size if level > ZERO else value < level + size
            line.append((marks.MSG_ROW_DIALOG_BAR if reaches and (value > ZERO) == (level > ZERO) and value != ZERO else drawing.NOTHING).center(CELL_WIDTH))
        return line

    def number_line(self):
        line = Text(drawing.SPACE * len(self.level_label(ZERO)))
        for place, value in enumerate(self.values):
            if place == self.cursor.get_place():
                # The cursor's number is in reverse video, as the cursor's cell of the pattern and groove editors is.
                line.append(str(value).center(CELL_WIDTH), style=Style.REVERSE)
            else:
                line.append(str(value).center(CELL_WIDTH))
        return line

    def lines(self, width):
        above, below = self.levels()
        buttons = [(binding.name, label) for label, binding in zip(labels.MSG_OK_CANCEL_BUTTONS, BUTTON_BINDINGS)]
        zero = [Text(self.level_label(ZERO) + marks.MSG_ROW_DIALOG_ZERO * (len(self.values) * CELL_WIDTH), style=Style.DIM)] if below else []
        return [*[self.bar_line(level) for level in above], *zero, *[self.bar_line(level) for level in below], self.number_line(),
                Text(drawing.NOTHING), *button_row(buttons=buttons, selected=OK)]
