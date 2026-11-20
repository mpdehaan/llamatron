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
"""Finer ways of drawing than big pixels, at the characters' own resolution and below, shared by the modes that want sharper shapes.

Half blocks give each cell two pixels, one above the other: the upper half block (`▀`) drawn in the
top pixel's colour on the bottom pixel's, so that a picture twice as tall as the area is drawn
square and four times finer than big pixels. Braille gives each cell eight dots, two across and four
down, for fine lines, the cell in the colour of its brightest dot. And cells of characters with a
colour each, for drawings made of characters. Each colour's style, or each pair's, is made once,
and each run of one style along a line is one piece of text.
"""

import numpy
from rich.text import Span, Text

from llamatron.visualizers.colour_styles import packed_style

UPPER_HALF = '▀'
SPACE = ' '
# Braille's dots, as the bits of the character after BRAILLE_BLANK, by their row and column in the cell.
BRAILLE_BLANK = 0x2800
BRAILLE_BITS = numpy.array([[0x01, 0x08], [0x02, 0x10], [0x04, 0x20], [0x40, 0x80]])
BRAILLE_ROWS = 4
BRAILLE_COLUMNS = 2
HALF_ROWS = 2


def packed(colours):
    """Return an array of colours, red, green and blue in its last place, as one whole number each, which looks a style up faster than three."""
    colours = colours.astype(numpy.int64)
    return (colours[..., 0] << 16) | (colours[..., 1] << 8) | colours[..., 2]


def styled_line(*, characters, styles):
    """Return one line of characters as text, each run of one style one span, made in one go, since appending piece by piece was most of a frame's cost."""
    spans = []
    start = 0
    count = len(characters)
    for place in range(1, count + 1):
        if place == count or styles[place] is not styles[start]:
            if styles[start] is not None:
                spans.append(Span(start, place, styles[start]))
            start = place
    return Text(''.join(characters), spans=spans, no_wrap=True)


def coloured_cells(*, characters, colours):
    """Return lines from rows of characters and their colours, an array of rows by columns by three; a black colour draws a blank."""
    lines = []
    for row, colour_row in zip(characters, packed(colours).tolist()):
        styles = [packed_style(number) if number else None for number in colour_row]
        lines.append(styled_line(characters=[character if style else SPACE for character, style in zip(row, styles)], styles=styles))
    return lines


def braille_lines(*, dots, colours, width):
    """Return lines drawing a grid of dots, four rows and two columns of them a cell, each cell in its colour, rows by columns by three."""
    rows = dots.shape[0] // BRAILLE_ROWS
    columns = dots.shape[1] // BRAILLE_COLUMNS
    cells = dots[:rows * BRAILLE_ROWS, :columns * BRAILLE_COLUMNS].reshape(rows, BRAILLE_ROWS, columns, BRAILLE_COLUMNS)
    bits = (cells * BRAILLE_BITS[None, :, None, :]).sum(axis=(1, 3))
    lines = []
    for bit_row, colour_row in zip(bits.tolist(), packed(colours[:rows, :columns]).tolist()):
        characters = [chr(BRAILLE_BLANK + bit) if bit else SPACE for bit in bit_row]
        styles = [packed_style(number) if bit else None for bit, number in zip(bit_row, colour_row)]
        text = styled_line(characters=characters, styles=styles)
        text.pad_right(max(width - text.cell_len, 0))
        lines.append(text)
    return lines
