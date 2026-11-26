# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Big pixels as lines of coloured text: each pixel of an array of colours, two terminal columns wide and one row tall so that it comes out square, drawn as full blocks in its colour.

Runs of the same colour along a line are one piece of text, and each colour's style is made once,
since a frame draws thousands of pixels many times a second. Rich draws the colours in as many as
the terminal shows, full colour where it can and the nearest of 256 or 16 where it can't, so a
visualizer needn't know.
"""

from rich.text import Text

from llamatron.interface.visualizers.colour_styles import rgb_style

# How many terminal columns and rows one big pixel takes: a terminal's cell is about twice as tall as it is wide.
PIXEL_COLUMNS = 2
PIXEL_ROWS = 1
FULL_BLOCK = '█'
NOTHING = ''


def pixel_lines(*, pixels, width, height):
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
                line.append(FULL_BLOCK * (run_length * PIXEL_COLUMNS), style=rgb_style(run_colour))
            run_colour = colour
            run_length = 1
        if run_length:
            line.append(FULL_BLOCK * (run_length * PIXEL_COLUMNS), style=rgb_style(run_colour))
        line.pad_right(max(width - line.cell_len, 0))
        for _ in range(PIXEL_ROWS):
            lines.append(line)
    return lines


def pixel_size(*, width, height):
    """Return how many big pixels fit an area of terminal columns and rows, as (columns, rows)."""
    return width // PIXEL_COLUMNS, height // PIXEL_ROWS
