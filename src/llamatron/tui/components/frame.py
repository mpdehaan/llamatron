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
"""A double-lined box drawn around what the cursor is on, over the lines of a grid.

The Arrange page draws one around the clip, scene or track under the cursor, as the user chose
over reverse video, so that the selection stands out on a grid of bars. The frame's top and
bottom edges go on the lines above and below what it frames, and its sides on each line between.
"""

from llamatron.tui.drawing import Box, Style


class Frame:
    """The edges of a double-lined box between two columns, drawn onto a Canvas line by line."""

    __slots__ = ('_left', '_right', '_style')

    def __init__(self, *, left, right, style=Style.BOLD):
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
