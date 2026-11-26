# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Helpers the tests of the tracker's pages share: reading the main screen's selected cell from what is drawn."""

from llamatron.interface.tracker.drawing import Box
from llamatron.interface.tracker.screens.set import main_page

# The marks the screen's text puts around anything in reverse video, and what joins a cell's lines.
REVERSED_STARTS = '«'
REVERSED_ENDS = '»'
LINE_SEPARATOR = '\n'


def boxed_line(text):
    """Return the main screen's selected cell: what is between the sides of the only double-lined box. For Arrange's cell, which has
    several lines, the lines joined; for the bar of the file's actions, whose box is double-lined while the cursor is in it, the
    selected action, the one whose name is in reverse video with its key."""
    insides = [line[line.index(Box.DOUBLE_BAR):line.rindex(Box.DOUBLE_BAR) + 1] for line in text.splitlines() if line.count(Box.DOUBLE_BAR) >= 2]
    assert insides, text
    if len(insides) == main_page.BAR_ROWS:
        reversed_pieces = [piece.split(REVERSED_ENDS)[0] for inside in insides for piece in inside.split(REVERSED_STARTS)[1:]]
        return max(reversed_pieces, key=len)
    return LINE_SEPARATOR.join(insides)
