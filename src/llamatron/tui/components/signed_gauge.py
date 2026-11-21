# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A gauge of signed values around a zero line, designed for the arp's offsets.

Each value is a bar from the zero line, up for a positive value and down for a negative one, so
many levels either side, and a value past the edge fills to it and carries a mark after its
number, like +7▲, rather than an arrow in the end block. The cursor's column is marked at both
ends, <<4>> around the step number and <+7▲> around the value. It returns plain cell texts and
knows nothing of any toolkit, so the offsets editor draws the rules and styles around them.
"""

from llamatron.tui import drawing
from llamatron.user_strings import marks


class SignedGauge:
    """The cells of a row of signed values drawn as bars either side of a zero line."""

    __slots__ = ('values', 'levels', 'cursor')

    def __init__(self, *, values, levels, cursor):
        self.values = values
        self.levels = levels
        self.cursor = cursor

    def levels_above(self):
        """Return the levels above the zero line, from the top down."""
        return range(self.levels, 0, -1)

    def levels_below(self):
        """Return the levels below the zero line, from the line down."""
        return range(-1, -self.levels - 1, -1)

    def cell(self, *, place, level):
        """Return a cell of the gauge: a bar where the value at a place reaches the level, and nothing where it doesn't."""
        value = self.values[place]
        if value is None:
            return drawing.NOTHING
        if level > 0:
            return marks.MSG_GAUGE_BAR if value >= level else drawing.NOTHING
        return marks.MSG_GAUGE_BAR if value <= level else drawing.NOTHING

    def value_text(self, place):
        """Return a value as the row under the gauge shows it: signed, marked when the gauge is too short to reach it, and bracketed under the cursor."""
        value = self.values[place]
        if value is None:
            text = drawing.NOTHING
        else:
            mark = drawing.NOTHING
            if value > self.levels:
                mark = marks.MSG_OVER_THE_TOP_MARK
            elif value < -self.levels:
                mark = marks.MSG_UNDER_THE_BOTTOM_MARK
            text = (marks.MSG_POSITIVE_VALUE if value > 0 else marks.MSG_OTHER_VALUE).format(value=value, mark=mark)
        return marks.MSG_CURSOR_VALUE_MARKS.format(text=text) if place == self.cursor else text

    def step_text(self, place):
        """Return a step's number, bracketed under the cursor."""
        text = str(place + 1)
        return marks.MSG_CURSOR_STEP_MARKS.format(text=text) if place == self.cursor else text
