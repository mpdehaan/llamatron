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
"""A row whose values go round a short fixed cycle, like the Dot and accidental rows."""

from llamatron.tui.components.pattern_row import PatternRow
from llamatron.tui.key_table import STEP_FORWARD
from llamatron.tui import keybindings


class CycleRow(PatternRow):
    """Space or Enter goes to the next of the row's choices, ] does the same and [ goes to the one before, and Bksp clears, which is where the choices start."""

    KEYS = keybindings.CycleRow

    __slots__ = ()
    def keys(self):
        return [
            self.bind(self.KEYS.NEXT, action=lambda: self.cycle(STEP_FORWARD)),
            *self.adjust_keys(),
            self.bind(self.KEYS.CLEAR, action=lambda: self.set_value(None)),
        ]

    def choices(self):
        """Return the values in the order + steps through them: the row's blank first, then the choices of the row's one description."""
        return [self.described().blank(), *self.described().get_choices()]

    def nudge(self, offset):
        """[ and ] go round the cycle, as they step a number on the other rows."""
        self.cycle(offset)

    def cycle(self, offset):
        choices = self.choices()
        value = self.value()
        # A row with no values yet answers None, which is the row's blank.
        place = choices.index(self.described().blank() if value is None else value)
        self.set_value(choices[(place + offset) % len(choices)])
