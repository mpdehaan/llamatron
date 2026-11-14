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

"""The batch video's stage, drawn over the whole screen: Arrange in grey on black, the READY box, the box growing into the scene frame, the frame's pulse and the visualizer inside it.

The user's design. The READY box has a double border in blue, a track one cell inside it where a
glow, the pulse, goes round, and a black gap around READY in red block letters, two rows and four
columns, since a cell is about twice as tall as it is wide (the track down the sides is two columns
wide for the same reason). As the song starts the box grows out until its border lies in the
screen's outermost cells, where it has faded away, leaving the track one cell in from the edge, a
black gap, and the visualizer filling the rest: the scene frame. The recorder trims a pixel or two
inside the terminal's margin, so the outermost cells are black and the frame is never cut.
Everything here is Rich text and knows nothing of Textual or of time: tui/batch_stage.py says what
shows when.
"""

from typing import NamedTuple

from rich.color import Color
from rich.style import Style as RichStyle
from rich.text import Span, Text

from llamatron.tui.components.title_card import LETTER_GAP, NARROW, eased, letter_rows, words_width
from llamatron.tui.drawing import SPACE, Box, laid_over
from llamatron.strings.about import MSG_BLOCK, MSG_READY_WORD

BLACK = (0, 0, 0)
BORDER_BLUE = (60, 120, 255)
READY_RED = (235, 45, 40)
FULL = 255
# How Arrange's text in the terminal's own colour is shown in grey, out of 255: plain, bold and dim.
PLAIN_GREY = 190
BOLD_GREY = 235
DIM_GREY = 110
# The READY box: the gap around READY, in rows and in columns, and how wide the track is down the sides.
GAP_ROWS = 2
GAP_COLUMNS = 4
SIDE_TRACK = 2
# The scene frame, from the edge in: the border in the outermost cells, the track, and the black gap before the visualizer.
EDGE_COLUMNS = 1
FRAME_GAP_ROWS = 1
FRAME_GAP_COLUMNS = 2
# The pulse: how much of a lap it is long, how its tail fades behind its head (a power over one fades it sooner), and its brightest.
PULSE_SHARE = 0.25
TAIL_FADE_POWER = 1.5
PULSE_CEILING = 0.92


class Rect(NamedTuple):
    """A rectangle of cells on the screen: its border's top and bottom rows and its left and right columns."""

    top: int
    bottom: int
    left: int
    right: int


def coloured(*, colour, level, background=BLACK):
    """Return a style of a colour turned down to a level from 0 to 1, on a background."""
    red, green, blue = (max(0, min(FULL, round(channel * level))) for channel in colour)
    return RichStyle(color=Color.from_rgb(red, green, blue), bgcolor=Color.from_rgb(*background))


BLACK_STYLE = coloured(colour=BLACK, level=0)


def grey_of(style):
    """Return how bright Arrange's text of a style is shown, out of 255: bold brighter, dim darker."""
    if style.bold:
        return BOLD_GREY
    if style.dim:
        return DIM_GREY
    return PLAIN_GREY


def faded(*, line, level):
    """Return a line with every colour turned down to a level from 0 to 1 on black: a colour it has, or grey for text in the terminal's own colour, as bright as bold, plain or dim says, reverse video as dark text on its colour."""
    spans = []
    # A style the whole line has goes under its pieces' own.
    whole = [Span(0, len(line.plain), line.style)] if line.style else []
    for span in whole + list(line.spans):
        style = RichStyle.parse(span.style) if isinstance(span.style, str) else span.style
        grey = grey_of(style)
        colour = style.color.get_truecolor() if style.color is not None and not style.color.is_default else (grey, grey, grey)
        background = style.bgcolor.get_truecolor() if style.bgcolor is not None and not style.bgcolor.is_default else BLACK
        if style.reverse:
            colour, background = background, colour
        shaded_background = tuple(max(0, min(FULL, round(channel * level))) for channel in background)
        spans.append(Span(span.start, span.end, coloured(colour=colour, level=level, background=shaded_background)))
    return Text(line.plain, style=coloured(colour=(PLAIN_GREY,) * 3, level=level), spans=spans, no_wrap=True)


def black_line(width):
    return Text(SPACE * max(width, 0), style=BLACK_STYLE)


def ready_box(*, width, height):
    """Return the READY box centred on a screen: big enough for its border, the track, the gap and READY in single-width blocks."""
    across = words_width(word=MSG_READY_WORD, scale=NARROW) + 2 * (GAP_COLUMNS + SIDE_TRACK + 1)
    down = len(letter_rows(word=MSG_READY_WORD, scale=NARROW)[0]) + 2 * (GAP_ROWS + 2)
    top = max((height - down) // 2, 0)
    left = max((width - across) // 2, 0)
    return Rect(top=top, bottom=top + down - 1, left=left, right=left + across - 1)


def frame_box(*, width, height):
    """Return the scene frame's border, which lies in the screen's outermost cells, unseen, with the track one cell inside it."""
    return Rect(top=0, bottom=height - 1, left=EDGE_COLUMNS, right=width - 1 - EDGE_COLUMNS)


def grown(*, start, end, share):
    """Return the rectangle part of the way from one to another, eased, as the READY box grows into the frame."""
    share = eased(share)
    return Rect(*(round(begin + (finish - begin) * share) for begin, finish in zip(start, end)))


def inside_of(rect):
    """Return the rectangle inside a box's track and gap, where READY or the visualizer shows."""
    return Rect(
        top=rect.top + 2 + FRAME_GAP_ROWS, bottom=rect.bottom - 2 - FRAME_GAP_ROWS,
        left=rect.left + 1 + SIDE_TRACK + FRAME_GAP_COLUMNS, right=rect.right - 1 - SIDE_TRACK - FRAME_GAP_COLUMNS,
    )


def visualizer_area(*, width, height):
    """Return the rectangle the visualizer draws in once the frame is up."""
    return inside_of(frame_box(width=width, height=height))


def track_cells(rect):
    """Return the track's places round a box, one cell inside its border, clockwise from the top left, each the list of cells it covers: one on the top and bottom, SIDE_TRACK side by side down the sides."""
    top = rect.top + 1
    bottom = rect.bottom - 1
    left = rect.left + 1
    right = rect.right - 1
    places = [[(top, column)] for column in range(left, right + 1)]
    places += [[(row, right - offset) for offset in range(SIDE_TRACK)] for row in range(top + 1, bottom)]
    places += [[(bottom, column)] for column in range(right, left - 1, -1)]
    places += [[(row, left + offset) for offset in range(SIDE_TRACK)] for row in range(bottom - 1, top, -1)]
    return places


def pulse_levels(*, count, head, direction):
    """Return how bright each of count places round the track is, for a pulse whose head is at a share of the lap going the way direction says (1 clockwise, -1 not), its tail fading behind it."""
    length = max(count * PULSE_SHARE, 1.0)
    levels = []
    for place in range(count):
        behind = ((head * count - place) * direction) % count
        levels.append(PULSE_CEILING * (1.0 - behind / length) ** TAIL_FADE_POWER if behind < length else 0.0)
    return levels


def overlaid(*, lines, cells):
    """Return lines with cells laid over them, each cell a place, a character and a style, a run of neighbouring cells at a time."""
    rows = {}
    for (row, column), cell in cells.items():
        if 0 <= row < len(lines) and column >= 0:
            rows.setdefault(row, {})[column] = cell
    result = list(lines)
    for row, columns in rows.items():
        line = result[row]
        run = []
        for place in sorted(columns) + [None]:
            if run and (place is None or place != run[-1] + 1):
                piece = Text()
                for column in run:
                    character, style = columns[column]
                    piece.append(character, style=style)
                line = laid_over(line=line, start=run[0], piece=piece)
                run = []
            if place is not None:
                run.append(place)
        result[row] = line
    return result


def blacked(*, lines, rect):
    """Return lines with a rectangle filled with black."""
    result = list(lines)
    for row in range(max(rect.top, 0), min(rect.bottom + 1, len(lines))):
        result[row] = laid_over(line=result[row], start=max(rect.left, 0), piece=black_line(rect.right - max(rect.left, 0) + 1))
    return result


def border_cells(*, rect, level):
    """Return a box's double border as cells, in blue at a level."""
    style = coloured(colour=BORDER_BLUE, level=level)
    cells = {
        (rect.top, rect.left): (Box.DOUBLE_TOP_LEFT, style), (rect.top, rect.right): (Box.DOUBLE_TOP_RIGHT, style),
        (rect.bottom, rect.left): (Box.DOUBLE_BOTTOM_LEFT, style), (rect.bottom, rect.right): (Box.DOUBLE_BOTTOM_RIGHT, style),
    }
    for column in range(rect.left + 1, rect.right):
        cells[(rect.top, column)] = (Box.DOUBLE_RULE, style)
        cells[(rect.bottom, column)] = (Box.DOUBLE_RULE, style)
    for row in range(rect.top + 1, rect.bottom):
        cells[(row, rect.left)] = (Box.DOUBLE_BAR, style)
        cells[(row, rect.right)] = (Box.DOUBLE_BAR, style)
    return cells


def pulse_cells(*, rect, head, direction, colour, level):
    """Return the pulse round a box's track as cells: blocks in its colour, shaded by how far behind the head each is."""
    places = track_cells(rect)
    cells = {}
    for place, brightness in zip(places, pulse_levels(count=len(places), head=head, direction=direction)):
        if brightness > 0:
            for cell in place:
                cells[cell] = (MSG_BLOCK, coloured(colour=colour, level=brightness * level))
    return cells


def ready_cells(*, rect, level):
    """Return READY in red block letters, centred inside a box, as cells."""
    inside = inside_of(rect)
    rows = letter_rows(word=MSG_READY_WORD, scale=NARROW)
    across = words_width(word=MSG_READY_WORD, scale=NARROW)
    top = inside.top + max((inside.bottom - inside.top + 1 - len(rows[0])) // 2, 0)
    left = inside.left + max((inside.right - inside.left + 1 - across) // 2, 0)
    style = coloured(colour=READY_RED, level=level)
    cells = {}
    column = left
    for letter in rows:
        for row, text in enumerate(letter):
            for offset, character in enumerate(text):
                if character != SPACE:
                    cells[(top + row, column + offset)] = (character, style)
        column += len(letter[0]) + LETTER_GAP
    return cells


def clips_laid_in(*, lines, clips, at, inside, level):
    """Return lines with Arrange drawn at the size of the frame's inside, header and legend and all, laid in at a level with its top left at a rectangle's, where it falls inside another as the box grows."""
    result = list(lines)
    for number, line in enumerate(clips):
        row = at.top + number
        if not inside.top <= row <= inside.bottom or row >= len(result):
            continue
        start = max(inside.left - at.left, 0)
        end = min(inside.right - at.left + 1, len(line.plain))
        if end > start:
            result[row] = laid_over(line=result[row], start=at.left + start, piece=faded(line=line[start:end], level=level))
    return result


def visualizer_laid_in(*, lines, frame_lines, area, inside, level):
    """Return lines with the visualizer's frame, drawn for the whole of area, laid in at a level only where it falls inside a rectangle."""
    result = list(lines)
    for number, piece in enumerate(frame_lines):
        row = area.top + number
        if not inside.top <= row <= inside.bottom or row >= len(result):
            continue
        start = max(inside.left - area.left, 0)
        end = min(inside.right - area.left + 1, len(piece.plain))
        if end > start:
            result[row] = laid_over(line=result[row], start=area.left + start, piece=faded(line=piece[start:end], level=level))
    return result
