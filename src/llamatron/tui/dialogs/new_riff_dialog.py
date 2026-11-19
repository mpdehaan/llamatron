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

"""The New Riff dialog: how a riff written for a player is drawn.

Up and Down move between the rows and the buttons. On a row of choices [ and ] step the choice
and ENTER writes the riff; on the toggle Space or ENTER flips it; on the buttons Left and Right
choose and ENTER presses. ESC cancels. What fills the gaps is asked only of a riff of notes and
chords, the one kind that has gaps between its accents.
"""

from rich.text import Text

from llamatron.macro_composer import riffs, wizard_choices
from llamatron.strings import labels, marks
from llamatron.tui import drawing, key_table, keybindings
from llamatron.tui.components.button_row import button_row
from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.drawing import cursor_mark, Style
from llamatron.tui.key_table import cursor_moved

# The rows in the order drawn; the last is asked only of a riff of notes and chords.
ROWS = (riffs.RIFF_BAR_COUNT, riffs.RIFF_NOTES, riffs.RIFF_WITH_CHORDS, riffs.RIFF_BETWEEN)
LABEL_WIDTH = max(len(labels.MSG_NEW_RIFF_LABELS[row]) for row in ROWS) + 4
# The buttons, in the order drawn, and the binding whose key each shows.
WRITE_BUTTON = 0
BUTTON_BINDINGS = (keybindings.NewRiffDialog.WRITE, keybindings.Dialog.CANCEL)
NO_BUTTON = -1


class NewRiffDialog(Dialog):
    """Asks how a new riff is drawn and answers the riff's settings by name, or nothing when cancelled."""

    KEYS = keybindings.NewRiffDialog

    def __init__(self, *, player):
        super().__init__()
        self.title = labels.MSG_NEW_RIFF_TITLE.format(player=player)
        # Each setting starts at what a riff has until another is chosen.
        self.settings = {row: wizard_choices.RIFF_SETTINGS[row][0] for row in ROWS}
        self.row = 0
        self.button = WRITE_BUTTON

    def rows(self):
        """Return the rows shown: what fills the gaps only for a riff of notes and chords."""
        return [row for row in ROWS if row != riffs.RIFF_BETWEEN or self.settings[riffs.RIFF_NOTES] == riffs.ACCENT_CHORDS]

    def on_buttons(self):
        return self.row >= len(self.rows())

    def keys(self):
        bound = [self.bind(self.KEYS.CANCEL, action=lambda: self.dismiss(None)), self.bind(self.KEYS.SELECT, action=self.move, wants_key=True)]
        if self.on_buttons():
            bound += [self.bind(self.KEYS.CHOOSE_BUTTON, action=self.choose_button, wants_key=True), self.bind(self.KEYS.PRESS, action=self.press)]
        elif self.rows()[self.row] == riffs.RIFF_WITH_CHORDS:
            bound.append(self.bind(self.KEYS.TOGGLE, action=self.toggle))
        else:
            bound += [self.bind(self.KEYS.LESS, action=lambda: self.step(key_table.STEP_BACK)), self.bind(self.KEYS.MORE, action=lambda: self.step(key_table.STEP_FORWARD)), self.bind(self.KEYS.WRITE, action=self.accept)]
        return self.in_order(bound)

    def move(self, name):
        self.row = cursor_moved(place=self.row, name=name, count=len(self.rows()) + 1)

    def choose_button(self, name):
        self.button = cursor_moved(place=self.button, name=name, count=len(labels.MSG_NEW_RIFF_BUTTONS))

    def step(self, direction):
        """Step the row's choice, stopping at either end."""
        row = self.rows()[self.row]
        ways = wizard_choices.RIFF_SETTINGS[row]
        self.settings[row] = ways[max(0, min(ways.index(self.settings[row]) + direction, len(ways) - 1))]

    def toggle(self):
        self.settings[riffs.RIFF_WITH_CHORDS] = riffs.STAYS_HOME if self.settings[riffs.RIFF_WITH_CHORDS] == riffs.MOVES_WHOLE else riffs.MOVES_WHOLE

    def press(self):
        if self.button == WRITE_BUTTON:
            self.accept()
        else:
            self.dismiss(None)

    def accept(self):
        self.dismiss({row: self.settings[row] for row in self.rows()})

    def shown(self, row):
        """Return a row's value as drawn: the toggle's dot, or the choice's name."""
        if row == riffs.RIFF_WITH_CHORDS:
            return marks.MSG_TOGGLE_ON if self.settings[row] == riffs.MOVES_WHOLE else drawing.NOTHING
        return labels.MSG_NEW_RIFF_VALUES[self.settings[row]]

    def lines(self, width):
        lines = []
        for place, row in enumerate(self.rows()):
            line = Text(cursor_mark(place == self.row) + labels.MSG_NEW_RIFF_LABELS[row].ljust(LABEL_WIDTH))
            line.append(self.shown(row), style=Style.BOLD if place == self.row else Style.PLAIN)
            lines.append(line)
        buttons = [(binding.name, label) for label, binding in zip(labels.MSG_NEW_RIFF_BUTTONS, BUTTON_BINDINGS)]
        return [*lines, Text(drawing.NOTHING), *button_row(buttons=buttons, selected=self.button if self.on_buttons() else NO_BUTTON)]
