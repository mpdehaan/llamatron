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
"""Big pixels as lines of coloured text: each pixel of an array of colours, two terminal columns wide and one row tall so that it comes out square, drawn as full blocks in its colour.

Runs of the same colour along a line are one piece of text, and each colour's style is made once,
since a frame draws thousands of pixels many times a second. Rich draws the colours in as many as
the terminal shows, full colour where it can and the nearest of 256 or 16 where it can't, so a
visualizer needn't know.
"""

from rich.color import Color
from rich.style import Style
from rich.text import Text

# How many terminal columns and rows one big pixel takes: a terminal's cell is about twice as tall as it is wide.
PIXEL_COLUMNS = 2
PIXEL_ROWS = 1
FULL_BLOCK = '█'
NOTHING = ''


class PixelPainter:
    """Draws arrays of big pixels as text, keeping the style of each colour it has drawn."""

    __slots__ = ('_styles',)

    def __init__(self):
        self._styles = {}

    def style_of(self, colour):
        """Return the style that draws a colour, an (r, g, b) of whole numbers from 0 to 255, made the first time it's asked for."""
        if colour not in self._styles:
            red, green, blue = colour
            self._styles[colour] = Style(color=Color.from_rgb(red, green, blue))
        return self._styles[colour]

    def lines(self, *, pixels, width, height):
        """Return the text lines that draw an array of pixels, rows by columns by three channels of 0 to 255, in an area width columns by height rows, any columns left over blank."""
        rows = pixels.tolist()
        lines = []
        for row in rows[:height // PIXEL_ROWS]:
            line = Text(no_wrap=True)
            run_colour = None
            run_length = 0
            for colour in row:
                colour = tuple(colour)
                if colour == run_colour:
                    run_length += 1
                    continue
                if run_length:
                    line.append(FULL_BLOCK * (run_length * PIXEL_COLUMNS), style=self.style_of(run_colour))
                run_colour = colour
                run_length = 1
            if run_length:
                line.append(FULL_BLOCK * (run_length * PIXEL_COLUMNS), style=self.style_of(run_colour))
            line.pad_right(max(width - line.cell_len, 0))
            for _ in range(PIXEL_ROWS):
                lines.append(line)
        return lines


def pixel_size(*, width, height):
    """Return how many big pixels fit an area of terminal columns and rows, as (columns, rows)."""
    return width // PIXEL_COLUMNS, height // PIXEL_ROWS
