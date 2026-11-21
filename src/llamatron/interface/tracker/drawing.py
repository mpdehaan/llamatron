# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What every screen draws with: the styles, the box characters, and the helpers that fit text to a width.

Everything is drawn with bold, dim, reverse video and box characters instead of color, so that it suits
any terminal background.
"""

from rich.text import Text

from llamatron.user_strings import legends


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
    # The piano roll's thin lines of a chord's other notes, in green so that they stand apart from the notes written.
    CHORD_NOTE = 'green'
    # The Chord dialog's keyboard: a key of the chord filled, a key of the scale in an outline's colour, the rest dim.
    CHORD_KEY = 'bold green'
    SCALE_KEY = 'cyan'
    # The piano roll's read head while the pattern plays, a thin light yellow line.
    READ_HEAD = 'khaki1'
    # The light on a piano roll's step that has keyswitches: magenta, which nothing else in the pattern editor uses.
    KEYSWITCH_LIGHT = 'bold magenta'
    # The slot each draw last took its value from while a song plays, on the Draws page: bright violet, the draws' colour.
    DRAW_LIGHT = 'bold #be5aff'
    DRAW_LIGHT_REVERSED = 'bold reverse #be5aff'
    # Arrange's details view: its dividers between the tracks in blue, so that the view shows itself, and
    # each line naming a thing in its kind's theme colour (themes.text_style), the colours allowed for it.
    # The status line's refusals and problems, in amber, and the title of a dialog that deletes, in red.
    REFUSAL = 'rgb(255,176,0)'
    DELETE_TITLE = 'bold red'
    DETAILS_DIVIDER = 'blue'
    # The box around the playing scene's name on Arrange in a recording nobody performs.
    PLAYING_SCENE = 'bold blue'
    # The box around a cell Tab has locked into, so that the lock shows, and the word for a cell with no details of its own.
    DETAILS_LOCKED = 'bold green'
    DETAILS_STOCK = 'red'
    # A key's label on the main screen's cells, bold as well as reversed.
    KEY = 'bold reverse'


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
        label = legends.MSG_LEGEND_LABEL.format(label=item.shown_label())
        what = legends.MSG_LEGEND_WHAT.format(what=item.what)
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
