# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A row of boxed buttons, for dialogs, drawn as the main screen draws its cells: each button's key reversed
and then its name, in a box, the selected button's box double-lined and its name bold, so that a dialog's answers look like a
real window's buttons."""

from rich.text import Text

from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.drawing import Box, padded, Style

# The space between two buttons, and inside a box before its key's reversed label and after its name, so that the label stands clear of the box's side as on the
# main screen.
BUTTON_GAP = drawing.SPACE
INSIDE = drawing.SPACE
ROW_LINES = 3


def button_row(*, buttons, selected):
    """Return the three lines of a row of buttons, each (its key's name, its name), the one at selected double-lined."""
    lines = [Text(no_wrap=True) for _ in range(ROW_LINES)]
    for place, (key_name, label) in enumerate(buttons):
        double = place == selected
        top_left, top_right, bottom_left, bottom_right, rule, bar = (
            (Box.DOUBLE_TOP_LEFT, Box.DOUBLE_TOP_RIGHT, Box.DOUBLE_BOTTOM_LEFT, Box.DOUBLE_BOTTOM_RIGHT, Box.DOUBLE_RULE, Box.DOUBLE_BAR) if double
            else (Box.TOP_LEFT, Box.TOP_RIGHT, Box.BOTTOM_LEFT, Box.BOTTOM_RIGHT, Box.RULE, Box.BAR))
        # A button with no key of its own shows its name alone.
        key = padded(key_name) if key_name else drawing.NOTHING
        inner = len(INSIDE) + len(key) + (len(drawing.SPACE) if key else 0) + len(label) + len(INSIDE)
        if place:
            for line in lines:
                line.append(BUTTON_GAP)
        lines[0].append(top_left + rule * inner + top_right)
        lines[1].append(bar + INSIDE)
        if key:
            lines[1].append(key, style=Style.REVERSE)
            lines[1].append(drawing.SPACE)
        lines[1].append(label, style=Style.BOLD if double else Style.PLAIN)
        lines[1].append(INSIDE + bar)
        lines[2].append(bottom_left + rule * inner + bottom_right)
    return lines
