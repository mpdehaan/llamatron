# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The demo's name scrolling across the screen: what a recording shows after the title.

The words are DEMO: and the set's file name as words, like DEMO: HOCKET SHANTY, or whatever the
recorder was told to show instead, in light orange on black (where the title is blue) and in the title's block letters,
which are capitals, drawn large. The words come in at the right edge, cross at one speed and
leave at the left.
"""

import os
import re
from rich.text import Text

from llamatron.strings import about
from llamatron.tui import drawing
from llamatron.tui.components import title_card
from llamatron.tui.components.title_card import blank_line, shaded

# The words' colour, a light orange.
SCROLL_ORANGE = (255, 180, 100)
# How many columns and rows one block of a letter takes, a square on most consoles and twice the size of the title's.
BLOCK_COLUMNS = 4
BLOCK_ROWS = 2
LETTER_ROWS = 5
# How tall the words are.
BANNER_ROWS = LETTER_ROWS * BLOCK_ROWS
# The columns between two letters.
LETTER_GAP = 4
# How fast the words cross, in columns a second.
COLUMNS_PER_SECOND = 120.0
FULL = 1.0
# What parts the words of a file's name, and the number a learning demo's name starts with, which is its place and not its name.
WORD_BREAK = re.compile(r'[^A-Za-z0-9]+')
LEADING_NUMBER = re.compile(r'^[0-9]+[^A-Za-z0-9]+(?=.)')


def words_of(name):
    """Return a name's words with a space between them, each starting with a capital: hocket_shanty gives Hocket Shanty."""
    return drawing.SPACE.join(word[:1].upper() + word[1:] for word in WORD_BREAK.split(name) if word)


def demo_name(path):
    """Return a set's name for the scroll from its file: no folder, no ending, no number in front, as words."""
    name = os.path.splitext(os.path.basename(path))[0]
    return words_of(LEADING_NUMBER.sub(drawing.NOTHING, name))


def scroll_text_for(path):
    """Return the words a recording of the set at path scrolls: DEMO: and its name."""
    return about.MSG_DEMO_SCROLL.format(name=demo_name(path))


def letter_lines(character):
    """Return one character's rows, BANNER_ROWS of them, in its capital's shape. A character with no shape is a space."""
    shape = about.MSG_BLOCK_LETTERS.get(character.upper(), about.MSG_BLOCK_LETTERS[drawing.SPACE])
    drawn = []
    for row in shape:
        line = drawing.NOTHING.join((about.MSG_BLOCK if block != drawing.SPACE else drawing.SPACE) * BLOCK_COLUMNS for block in row)
        drawn.extend([line] * BLOCK_ROWS)
    return drawn


def banner(text):
    """Return the words as BANNER_ROWS rows of blocks and spaces, every row as wide as the words."""
    letters = [letter_lines(character) for character in text]
    return [banner_row(letters=letters, row=row) for row in range(BANNER_ROWS)]


def scroll_seconds(*, text, width):
    """Return how long the words take to cross a screen of a width, from the first column coming in to the last going out."""
    return (width + len(banner(text)[0])) / COLUMNS_PER_SECOND


def scroll_lines(*, rows, width, height, elapsed):
    """Return the screen's lines at a moment: the banner's rows in the middle, moved left by the time gone, on black."""
    shift = max(int(elapsed * COLUMNS_PER_SECOND), 0)
    top = max((height - len(rows)) // 2, 0)
    style = shaded(colour=SCROLL_ORANGE, level=FULL)
    lines = [blank_line(width) for _ in range(height)]
    for place, row in enumerate(rows):
        if top + place >= height:
            break
        shown = (drawing.SPACE * width + row + drawing.SPACE * width)[shift:shift + width].ljust(width)
        lines[top + place] = drawn_row(shown=shown, style=style)
    return lines


def drawn_row(*, shown, style):
    """Return one row of the words, its blocks in the style and the rest black."""
    line = Text()
    for run in re.findall(r' +|[^ ]+', shown):
        line.append(run, style=title_card.BLACK_STYLE if run[0] == drawing.SPACE else style)
    return line


def banner_row(*, letters, row):
    """Return one row of the banner: that row of every letter, with a gap between letters."""
    return (drawing.SPACE * LETTER_GAP).join(letter[row] for letter in letters)
