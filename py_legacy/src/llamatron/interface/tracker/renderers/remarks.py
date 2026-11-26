# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How the lines under a page's settings are drawn: a remark of the forms (interface/forms/remarks.py) as its words, dim where it
is said in passing; a line a page still draws itself passes as it is."""

from rich.text import Text

from llamatron.interface.forms.remarks import Remark
from llamatron.interface.tracker.drawing import Style


def remark_lines(remarks):
    """Return the lines of a page's remarks, each drawn."""
    return [remark_line(line) for line in remarks]


def remark_line(line):
    """Return one remark drawn: its words, dim where it is said in passing; a line already drawn as it is."""
    if not isinstance(line, Remark):
        return line
    if line.dim:
        return Text(line.text, style=Style.DIM)
    return Text(line.text)
