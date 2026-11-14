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
"""An Inset Window, the user's design and name: a window over the page, INSET cells in from every edge, inside a solid band of colour outlined in white, for looking inside something without leaving the page.

It is read-only. Inside the band, one cell in on every side, comes its title in reverse video and
then the view's lines. The page keeps its keys and says which close it, the key that opened it and
no other (the user's rule), and the band's bottom edge names that key in its corner. The band's
colour is the view's to choose, as Scene View's says which of its views shows. The band is made of
spaces on a coloured background, which joins from line to line where full blocks leave gaps.
"""

from rich.color import Color
from rich.style import Style as RichStyle
from rich.text import Text

from llamatron.tui.drawing import Box, Style, fit, laid_over

# How far in from every edge of the screen the band is, with the white outline one cell further out; how thick the band is,
# the space inside it on every side, and the title's line above the view.
INSET = 4
BORDER = 1
PADDING = 1
TITLE_LINES = 1
SPACE = ' '
OUTLINE = RichStyle(color=Color.from_rgb(255, 255, 255))
# How far in from the band's corner the closing key's name sits.
LABEL_GAP = 2


def inside_size(*, width, height):
    """Return how wide and tall the view inside an Inset Window is on a screen width columns by height rows, within the band, the space inside it and the title."""
    edge = INSET + BORDER + PADDING
    return max(width - 2 * edge, 0), max(height - 2 * edge - TITLE_LINES, 0)


def drawn_over(*, screen, width, height, title, inside, colour, closing):
    """Return the screen's lines with an Inset Window laid over them: a white outline, a band of colour with the closing key's name in its bottom corner, and within it, one cell in, the title in reverse video and the view's lines."""
    view_width, view_height = inside_size(width=width, height=height)
    if not view_width or not view_height:
        return screen
    lines = list(screen) + [Text()] * max(height - len(screen), 0)
    band_style = RichStyle(bgcolor=Color.from_rgb(*colour))
    band_width = width - 2 * INSET
    band_height = height - 2 * INSET
    top = INSET
    bottom = top + band_height - 1
    inner_width = band_width - 2 * BORDER
    lines[top - 1] = laid_over(line=lines[top - 1], start=INSET - 1, piece=Text(Box.TOP_LEFT + Box.RULE * band_width + Box.TOP_RIGHT, style=OUTLINE))
    lines[bottom + 1] = laid_over(line=lines[bottom + 1], start=INSET - 1, piece=Text(Box.BOTTOM_LEFT + Box.RULE * band_width + Box.BOTTOM_RIGHT, style=OUTLINE))
    contents = [Text()] * PADDING + [Text(fit(text=title, width=view_width).rstrip(), style=Style.REVERSE)] + list(inside[:view_height])
    for row in range(top, bottom + 1):
        piece = Text()
        piece.append(Box.BAR, style=OUTLINE)
        if row in (top, bottom):
            piece.append(SPACE * band_width, style=band_style)
        else:
            piece.append(SPACE * BORDER, style=band_style)
            body = Text(SPACE * PADDING)
            place = row - top - BORDER
            if place < len(contents):
                line = contents[place].copy()
                line.truncate(view_width, pad=True)
                body.append_text(line)
            body.truncate(inner_width, pad=True)
            piece.append_text(body)
            piece.append(SPACE * BORDER, style=band_style)
        piece.append(Box.BAR, style=OUTLINE)
        lines[row] = laid_over(line=lines[row], start=INSET - 1, piece=piece)
    lines[bottom] = laid_over(line=lines[bottom], start=INSET + band_width - LABEL_GAP - len(closing), piece=Text(closing, style=Style.REVERSE))
    return lines
