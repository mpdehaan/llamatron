# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How a settings page's fields are drawn: a setting as its label and value on one line, the cursor's mark before it.

A kind not yet moved to the forms (interface/forms/nodes.py) still draws itself, by its own lines().
"""

from rich.text import Text

from llamatron.interface.forms import nodes
from llamatron.interface.tracker.drawing import cursor_mark, padded, Style
from llamatron.user_strings import legends, marks


def field_lines(field, *, page, here, label_width, width):
    """Return the lines a field is drawn as, the cursor on it where here is true, its label as wide as label_width."""
    if field.DRAWN_AS == nodes.OWN_LINES:
        return field.lines(page=page, here=here, label_width=label_width, width=width)
    return setting_line(field, page=page, here=here, label_width=label_width)


def setting_line(field, *, page, here, label_width):
    """Return a setting's line: the cursor's mark, the label, bold under the cursor, and the value, with the picker's dim mark
    after a value whose Enter opens a list of choices, so that it isn't taken for one that's typed."""
    line = Text(no_wrap=True)
    line.append(cursor_mark(here))
    line.append(field.get_drawn_label(page).ljust(label_width), style=Style.BOLD if here else Style.PLAIN)
    line.append(padded(field.value()))
    if field.enter_what == legends.What.CHOOSE:
        line.append(marks.MSG_PICKER_MARK, style=Style.DIM)
    return [line]
