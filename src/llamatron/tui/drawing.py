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

"""What every screen draws with: the styles, the box characters, and the helpers that fit text to a width.

Everything is drawn with bold, dim, reverse video and box characters instead of color, so that it suits
any terminal background.
"""

from rich.text import Text

from llamatron.strings.legends import MSG_LEGEND_LABEL, MSG_LEGEND_WHAT


# How Textual's queries name a widget by its id.
SELECTOR = '#{id}'
ELLIPSIS = '…'
NOTHING = ''
SPACE = ' '
INDENT = SPACE * 2
# The mark at the left of the selected row on every page and dialog with a row cursor, as wide as the
# indent it takes the place of, so that the arrows show themselves without anyone knowing a key.
SELECTED_MARK = '▶' + SPACE


def cursor_mark(selected):
    """Return what a row starts with: the mark when the cursor is on it, and the indent otherwise."""
    return SELECTED_MARK if selected else INDENT
LINE_BREAK = '\n'


class Style:
    """The only styles the tracker draws with, so that it suits any terminal background."""

    BOLD = 'bold'
    DIM = 'dim'
    REVERSE = 'reverse'
    PLAIN = ''
    # The one use of colour, for the lights of real-time playback, whose shapes change too, so that the state shows without it.
    PLAYING = 'bold red'
    SOUNDING = 'bold green'
    # The piano roll's thin lines of a chord's other notes, in green so that they stand apart from the notes written (the user's design).
    CHORD_NOTE = 'green'
    # Arrange's details view, the user's design: its dividers between the tracks in blue, so that the view shows itself, and
    # each line naming a thing in its kind's theme colour (themes.text_style), the colours the user allowed for it.
    # The status line's refusals and problems, in amber, and the title of a dialog that deletes, in red, the user's design.
    REFUSAL = 'rgb(255,176,0)'
    DELETE_TITLE = 'bold red'
    DETAILS_DIVIDER = 'blue'
    # The box around a cell Tab has locked into, so that the lock shows, and the word for a cell with no details of its own.
    DETAILS_LOCKED = 'bold green'
    DETAILS_STOCK = 'red'


class Align:
    """Which way text is lined up when fitted to a width."""

    LEFT = 'left'
    RIGHT = 'right'
    CENTER = 'center'


class Box:
    """The box-drawing characters the pages draw with."""

    HEAVY_RULE = '━'
    RULE = '─'
    BAR = '│'
    # A beat's edge in the pattern editor: a double line down through single rules.
    DOUBLE_BAR = '║'
    DOUBLE_TOP_TEE = '╥'
    DOUBLE_BOTTOM_TEE = '╨'
    CROSS = '┼'
    LEFT_TEE = '├'
    RIGHT_TEE = '┤'
    # Where a bold beat line crosses a rule inside the grid.
    DOUBLE_CROSS = '╫'
    # A double bar meeting the right end of a single rule, as the piano roll's cursor bars do on the last step shown.
    DOUBLE_TOP_RIGHT_TEE = '╖'
    DOUBLE_RIGHT_TEE = '╢'
    DOUBLE_BOTTOM_RIGHT_TEE = '╜'
    DOUBLE_RULE_DOUBLE_RIGHT_TEE = '╣'
    TOP_LEFT = '┌'
    TOP_TEE = '┬'
    TOP_RIGHT = '┐'
    BOTTOM_LEFT = '└'
    BOTTOM_TEE = '┴'
    BOTTOM_RIGHT = '┘'
    HEAVY_TOP_LEFT = '┏'
    HEAVY_TOP_RIGHT = '┓'
    HEAVY_BOTTOM_LEFT = '┗'
    HEAVY_BOTTOM_RIGHT = '┛'
    HEAVY_BAR = '┃'
    DOUBLE_RULE = '═'
    # The double rule under the piano roll's step numbers, and where single and double bars cross it.
    DOUBLE_RULE_LEFT_TEE = '╞'
    DOUBLE_RULE_RIGHT_TEE = '╡'
    DOUBLE_RULE_CROSS = '╪'
    DOUBLE_RULE_DOUBLE_CROSS = '╬'
    DOUBLE_RULE_DOUBLE_BOTTOM_TEE = '╩'
    DOUBLE_TOP_LEFT = '╔'
    DOUBLE_TOP_RIGHT = '╗'
    DOUBLE_BOTTOM_LEFT = '╚'
    DOUBLE_BOTTOM_RIGHT = '╝'
    MORE = '›'


def padded(text):
    """Return text with a space on each side, as a key label or a selected value is shown."""
    return f'{SPACE}{text}{SPACE}'


def wrapped(*, text, width):
    """Return text as lines of at most width characters, broken between words, as a dialog shows a message."""
    lines = []
    line = NOTHING
    for word in str(text).split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(Text(line))
            line = word
        else:
            line = line + SPACE + word if line else word
    lines.append(Text(line))
    return lines


def fit(*, text, width, align=Align.LEFT):
    """Return text cut or padded to exactly a width."""
    text = str(text)
    if len(text) > width:
        return text[:max(width - 1, 0)] + ELLIPSIS if width > 0 else NOTHING
    if align == Align.RIGHT:
        return text.rjust(width)
    if align == Align.CENTER:
        return text.center(width)
    return text.ljust(width)


def legend(*, keys, width):
    """Return lines showing every key, each as a reversed label followed by what it does."""
    lines = []
    line = Text(SPACE)
    for item in keys:
        label = MSG_LEGEND_LABEL.format(label=item.shown_label())
        what = MSG_LEGEND_WHAT.format(what=item.what)
        size = len(label) + len(what)
        if line.cell_len + size > width and line.cell_len > 1:
            lines.append(line)
            line = Text(SPACE)
        line.append(label, style=Style.REVERSE)
        line.append(what)
    lines.append(line)
    return lines


class Canvas:
    """One line of a screen, drawn in pieces that can overlap, for pages that lay a frame over a grid.

    A page writes each part of the line where it goes, with its style, and later writes can cover
    earlier ones, so a frame's edges can be drawn over a grid already laid out. text() gives the
    finished line as Rich text, one span per run of the same style.
    """

    __slots__ = ('_characters', '_styles')

    def __init__(self, width):
        self._characters = [SPACE] * width
        self._styles = [Style.PLAIN] * width

    def write(self, *, column, text, style=Style.PLAIN):
        """Put text on the line from a column, cutting whatever runs past either edge."""
        for offset, character in enumerate(text):
            place = column + offset
            if 0 <= place < len(self._characters):
                self._characters[place] = character
                self._styles[place] = style

    def text(self):
        result = Text(no_wrap=True)
        start = 0
        for place in range(1, len(self._characters) + 1):
            if place == len(self._characters) or self._styles[place] != self._styles[start]:
                result.append(NOTHING.join(self._characters[start:place]), style=self._styles[start])
                start = place
        return result


def laid_over(*, line, start, piece):
    """Return a screen line with a piece of text laid over it from a column, the line's text either side kept."""
    under = line.copy()
    end = start + piece.cell_len
    if under.cell_len < end:
        under.append(SPACE * (end - under.cell_len))
    result = under[:start]
    result.append_text(piece)
    result.append_text(under[end:])
    return result
