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
"""What every editor of steps shares: the cursor's step, the window of steps on screen, and the digits typed into a cell.

The pattern editor and the two one-row editors (one_row_editor.py) each edit a row or rows of
steps, with a cursor that Left and Right move along them. Three things were written out in each:
the digits typed so far into the cursor's cell, so that 1 and then 2 makes 12 as one edit, the
window of steps that scrolls sideways so that the cursor's step is always shown, and the words
that say which steps are on screen. They are here once.
"""

from llamatron.strings.marks import MSG_MORE_AFTER, MSG_MORE_BEFORE, MSG_STEPS_SHOWN
from llamatron.tui import keybindings
from llamatron.tui.drawing import NOTHING
from llamatron.tui.key_table import pressed_key
from llamatron.tui.screens.page import Page


class StepEditor(Page):
    """A page that edits steps under a cursor. A page of this kind says how many steps there are, with steps()."""

    KEYS = keybindings.StepEditor
    # How the page says which steps are on screen, which a page of cells words its own way.
    STEPS_SHOWN = MSG_STEPS_SHOWN

    def __init__(self, holder):
        super().__init__(holder)
        # The cursor's step, and the first step on screen, which the drawing moves so that the cursor's step is always shown.
        self.step = 0
        self.first_step = 0
        # The digits typed so far into the cursor's cell, so that 1 and then 2 makes 12.
        self.typed = NOTHING

    def steps(self):
        """Return how many steps there are."""
        raise NotImplementedError

    def on_key(self, event):
        # Any key but a digit ends the number being typed, so that the next digit starts a new one.
        name = pressed_key(event)
        if not (name and name.isdigit()):
            self.typed = NOTHING
        super().on_key(event)

    def keep_step(self):
        """Keep the cursor on a step there is, since a removed step or an undo can leave the cursor past the last."""
        self.step = max(min(self.step, self.steps() - 1), 0)

    def typed_number(self, *, digit, low, high):
        """Return the number made by another digit, or just that digit if the number would be out of range, or None if neither fits.

        A digit that extends the number already typed continues the same edit, so that typing 12
        into a cell is one undo step rather than two, as the user asked.
        """
        for text in (self.typed + digit, digit):
            if low <= int(text) <= high:
                if self.typed and text != digit:
                    self.document().continue_edit()
                self.typed = text
                return int(text)
        self.typed = NOTHING
        return None

    def window_of_steps(self, shown):
        """Move the window of steps so that the cursor's step is in it, and return its first and last steps (the last excluded).

        shown is how many steps fit across the screen.
        """
        count = self.steps()
        self.first_step = max(min(self.first_step, count - shown), 0)
        if self.step < self.first_step:
            self.first_step = self.step
        elif self.step >= self.first_step + shown:
            self.first_step = self.step - shown + 1
        return self.first_step, min(self.first_step + shown, count)

    def steps_shown_text(self, *, first, last):
        """Return which steps are on screen, with a mark on each side that has more, or nothing when every step is on screen."""
        count = self.steps()
        if last - first >= count:
            return NOTHING
        return self.STEPS_SHOWN.format(before=MSG_MORE_BEFORE if first > 0 else NOTHING, first=first + 1, last=last, after=MSG_MORE_AFTER if last < count else NOTHING)
