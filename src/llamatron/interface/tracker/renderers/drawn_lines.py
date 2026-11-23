# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The lines a page draws, as they are added, with the place of the one the cursor is on."""

from rich.text import Text

from llamatron.interface.tracker import drawing


class DrawnLines:
    """The lines a page draws, as they are added top to bottom, and the place of the one the cursor is on, which the page is
    scrolled to keep in sight."""

    __slots__ = ('_lines', '_selected')

    def __init__(self):
        self._lines = []
        self._selected = 0

    def get_lines(self):
        return self._lines

    def get_selected(self):
        return self._selected

    def blank(self):
        self._lines.append(Text(drawing.NOTHING))

    def add(self, lines, *, selected_at=None):
        """Add lines, the cursor's being the one at selected_at among them where it is given."""
        if selected_at is not None:
            self._selected = len(self._lines) + selected_at
        self._lines += lines
