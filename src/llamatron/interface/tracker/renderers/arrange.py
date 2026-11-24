# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How the tracker draws Arrange's grid (interface/forms/arrange.py): each line's nodes put onto a Canvas line in order, later
over earlier, the grid's lines in light blue, the one use of colour the play buttons' playing mark, and the frame laid over
everything last, inside the cell it marks, so that it touches no line."""

from rich.text import Text

from llamatron.interface.forms import arrange
from llamatron.interface.tracker import themes
from llamatron.interface.tracker.components.frame import Frame
from llamatron.interface.tracker.drawing import Box, Canvas, fit, laid_over, padded, Style
from llamatron.user_strings import marks

PIECE_STYLES = {
    arrange.PLAIN: Style.PLAIN, arrange.NAME: Style.BOLD, arrange.FAINT: Style.DIM, arrange.PLAYING: Style.PLAYING,
    arrange.SOUNDING: Style.SOUNDING, arrange.STOCK: Style.DETAILS_STOCK,
}
FRAME_STYLES = {arrange.CURSOR_FRAME: Style.SELECTED_EDGE, arrange.LOCKED_FRAME: Style.DETAILS_LOCKED, arrange.PLAYING_SCENE_FRAME: Style.PLAYING_SCENE}


def arrange_lines(*, lines, width, frames=()):
    """Return the page's lines drawn: each line's nodes, then the frames over them."""
    canvases = canvas_lines(lines=lines, width=width)
    for frame in frames:
        draw_frame(canvases=canvases, frame=frame)
    return [canvas.text() for canvas in canvases]


def canvas_lines(*, lines, width):
    """Return each line's nodes put onto a Canvas line."""
    canvases = []
    for nodes in lines:
        canvas = Canvas(width)
        for node in nodes:
            DRAWERS[type(node)](canvas=canvas, node=node)
        canvases.append(canvas)
    return canvases


def draw_frame(*, canvases, frame):
    """Draw a frame over Canvas lines."""
    Frame(left=frame.left, right=frame.right, style=FRAME_STYLES[frame.kind]).draw(canvases, top=frame.top, inside=frame.inside)


def detail_style(line):
    """Return the style of a line of details: the colour of its kind's pages for a line naming a thing, or its own kind's."""
    colour = themes.target_theme(line.target.kind) if line.target else None
    if colour is not None:
        return themes.text_style(colour)
    return PIECE_STYLES[line.kind]


def _piece(*, canvas, node):
    canvas.write(column=node.column, text=node.text, style=PIECE_STYLES[node.kind])


def _dividers(*, canvas, node):
    style = Style.DIM if node.faint else Style.DETAILS_DIVIDER
    canvas.write(column=node.double_at, text=Box.DOUBLE_BAR if not node.faint else Box.BAR, style=style)
    for column in node.columns:
        canvas.write(column=column, text=Box.BAR, style=style)


def _grid_rule(*, canvas, node):
    canvas.write(column=0, text=Box.RULE * node.end, style=Style.DETAILS_DIVIDER)
    canvas.write(column=node.double_at, text=Box.DOUBLE_CROSS, style=Style.DETAILS_DIVIDER)
    for column in node.crosses:
        canvas.write(column=column, text=Box.CROSS, style=Style.DETAILS_DIVIDER)
    canvas.write(column=node.end, text=Box.RIGHT_TEE, style=Style.DETAILS_DIVIDER)


def _more_mark(*, canvas, node):
    canvas.write(column=node.column, text=Box.MORE, style=Style.DIM)


def _play_button(*, canvas, node):
    # The playing mark is the one use of colour on Arrange.
    if node.playing:
        canvas.write(column=node.column, text=marks.MSG_STOP_MARK, style=Style.PLAYING)
    else:
        canvas.write(column=node.column, text=marks.MSG_PLAY_MARK, style=Style.DIM)


def _detail(*, canvas, node):
    text = node.line.text
    if node.room is not None and len(text) > node.room:
        text = fit(text=text, width=node.room).rstrip()
    canvas.write(column=node.column, text=text, style=detail_style(node.line))
    if node.picked:
        canvas.write(column=node.column - 1, text=marks.MSG_PICKED_OPEN, style=Style.BOLD)
        canvas.write(column=node.column + len(text), text=marks.MSG_PICKED_CLOSE, style=Style.BOLD)


DRAWERS = {
    arrange.ArrangeText: _piece, arrange.Dividers: _dividers, arrange.ArrangeRule: _grid_rule, arrange.MoreMark: _more_mark,
    arrange.PlayButton: _play_button, arrange.Detail: _detail,
}


def with_name(*, lines, name, row, left):
    """Return lines with a name laid over one of them, in reverse video, centred in the room right of a column."""
    piece = Text(padded(name), style=Style.REVERSE)
    width = max(line.cell_len for line in lines)
    start = left + max((width - left - piece.cell_len) // 2, 0)
    named = list(lines)
    named[row] = laid_over(line=lines[row], start=start, piece=piece)
    return named
