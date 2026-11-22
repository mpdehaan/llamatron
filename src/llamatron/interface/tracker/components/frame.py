# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A double-lined box drawn around what the cursor is on, over the lines of a grid.

The Arrange page draws one around the clip, scene or track under the cursor,
over reverse video, so that the selection stands out on a grid of bars. The frame's top and
bottom edges go on the lines above and below what it frames, and its sides on each line between.
"""

from llamatron.interface.tracker.drawing import Box, Style


class Frame:
    """The edges of a double-lined box between two columns, drawn onto a Canvas line by line."""

    __slots__ = ('_left', '_right', '_style')

    def __init__(self, *, left, right, style=Style.SELECTED_EDGE):
        self._left = left
        self._right = right
        self._style = style

    def styled(self, style):
        """Return the same frame drawn in another style, as Arrange draws a cell Tab has locked into."""
        return Frame(left=self._left, right=self._right, style=style)

    def inner_width(self):
        return self._right - self._left - 1

    def top(self, canvas):
        canvas.write(column=self._left, text=Box.DOUBLE_TOP_LEFT + Box.DOUBLE_RULE * self.inner_width() + Box.DOUBLE_TOP_RIGHT, style=self._style)

    def sides(self, canvas):
        canvas.write(column=self._left, text=Box.DOUBLE_BAR, style=self._style)
        canvas.write(column=self._right, text=Box.DOUBLE_BAR, style=self._style)

    def bottom(self, canvas):
        canvas.write(column=self._left, text=Box.DOUBLE_BOTTOM_LEFT + Box.DOUBLE_RULE * self.inner_width() + Box.DOUBLE_BOTTOM_RIGHT, style=self._style)

    def bottom_on_rule(self, canvas):
        """Draw the frame's sides ending in a rule already drawn on its bottom line, each meeting the rule in a joint, so that the rule
        runs on unbroken under what the frame holds, as under a track's name on Arrange."""
        canvas.write(column=self._left, text=Box.DOUBLE_BOTTOM_TEE, style=self._style)
        canvas.write(column=self._right, text=Box.DOUBLE_BOTTOM_TEE, style=self._style)
