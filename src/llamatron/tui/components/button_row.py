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
"""A row of boxed buttons, the user's design for dialogs, drawn as the main screen draws its cells: each button's key reversed
and then its name, in a box, the selected button's box double-lined and its name bold, so that a dialog's answers look like a
real window's buttons."""

from rich.text import Text

from llamatron.tui.drawing import Box, SPACE, Style, padded

# The space between two buttons, and inside a box after its name; the key's reversed label starts against the box's side.
BUTTON_GAP = SPACE
INSIDE = SPACE
ROW_LINES = 3


def button_row(*, buttons, selected):
    """Return the three lines of a row of buttons, each (its key's name, its name), the one at selected double-lined."""
    lines = [Text(no_wrap=True) for _ in range(ROW_LINES)]
    for place, (key_name, label) in enumerate(buttons):
        double = place == selected
        top_left, top_right, bottom_left, bottom_right, rule, bar = (
            (Box.DOUBLE_TOP_LEFT, Box.DOUBLE_TOP_RIGHT, Box.DOUBLE_BOTTOM_LEFT, Box.DOUBLE_BOTTOM_RIGHT, Box.DOUBLE_RULE, Box.DOUBLE_BAR) if double
            else (Box.TOP_LEFT, Box.TOP_RIGHT, Box.BOTTOM_LEFT, Box.BOTTOM_RIGHT, Box.RULE, Box.BAR))
        key = padded(key_name)
        inner = len(key) + len(SPACE) + len(label) + len(INSIDE)
        if place:
            for line in lines:
                line.append(BUTTON_GAP)
        lines[0].append(top_left + rule * inner + top_right)
        lines[1].append(bar)
        lines[1].append(key, style=Style.REVERSE)
        lines[1].append(SPACE)
        lines[1].append(label, style=Style.BOLD if double else Style.PLAIN)
        lines[1].append(INSIDE + bar)
        lines[2].append(bottom_left + rule * inner + bottom_right)
    return lines
