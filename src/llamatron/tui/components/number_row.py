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
"""A row of numbers in a range, like Velocity, Prob and Ratchet: typed, nudged or asked for."""

from llamatron.strings.errors import ERR_ROW_OUT_OF_RANGE, ERR_TYPED_NOT_AN_INTEGER
from llamatron.tui.components.pattern_row import PatternRow
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.drawing import NOTHING
from llamatron.strings.labels import MSG_ROW_LABELS
from llamatron.strings.marks import MSG_UNSET_MARK
from llamatron.strings.messages import MSG_NUMBER_PROMPT
from llamatron.tui import keybindings

# Where a nudge or Enter starts from on a row whose blank step plays as no number at all, which is a CC row: 0, since the
# CC most often used is the mod wheel, which the user wants to start from nothing (2026-11-09).
START_WITHOUT_A_DEFAULT = 0


class NumberRow(PatternRow):
    """Digits type a number, + and - nudge it, Enter asks for one, and Bksp goes back to the default.

    The row's limits, what a blank step plays as and whether a blank step changes nothing come
    from the row's one description, which is what a file's values are checked against too.
    """

    KEYS = keybindings.NumberRow

    __slots__ = ()

    def range(self):
        """Return the lowest and the highest number a step can hold on the row."""
        return self.described().get_lowest(), self.described().get_highest()

    def default(self):
        """Return the number a blank step plays as, which is where a nudge starts from."""
        default = self.described().get_default()
        return START_WITHOUT_A_DEFAULT if default is None else default

    def keys(self):
        low, high = self.range()
        return [
            self.bind(self.KEYS.TYPE, action=lambda digit: self.type_number(digit=digit, low=low, high=high), wants_key=True),
            *self.adjust_keys(),
            self.bind(self.KEYS.ASK, action=self.ask),
            self.bind(self.KEYS.DEFAULT, action=lambda: self.set_value(None)),
        ]

    def type_number(self, *, digit, low, high):
        number = self.editor.typed_number(digit=digit, low=low, high=high)
        if number is not None:
            self.set_value(number)

    def number_now(self):
        current = self.value()
        return self.default() if current is None else current

    def nudge(self, offset):
        low, high = self.range()
        self.set_value(max(min(self.number_now() + offset, high), low))

    def ask(self):
        low, high = self.range()
        label = MSG_ROW_LABELS[self.name]

        def answered(text):
            try:
                number = int(text.strip())
            except ValueError:
                self.editor.refuse(ERR_TYPED_NOT_AN_INTEGER.format(text=text))
                return
            if low <= number <= high:
                self.set_value(number)
            else:
                self.editor.refuse(ERR_ROW_OUT_OF_RANGE.format(row=label, low=low, high=high))
        self.editor.ask(dialog=PromptDialog(title=MSG_NUMBER_PROMPT.format(row=label, low=low, high=high), value=self.number_now()), then=answered)

    def cell_text(self, *, step):
        """A value that isn't set shows the default, or a dot where the default means nothing happens."""
        if not self.is_note(step=step) and not self.on_rests():
            return NOTHING
        value = self.value(step=step)
        if value is None:
            return MSG_UNSET_MARK if self.described().is_quiet() else str(self.default())
        return str(value)
