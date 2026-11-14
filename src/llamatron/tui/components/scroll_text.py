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

"""The demo's name scrolling across the screen: what a recording of an example shows after the title, the user's design.

The words are DEMO: and the set's file name in camel case, in the title's blue on black, in the
title's block letters. A capital, a digit and the colon are drawn twice the size of a small
letter, which is its capital's shape at the size the title's letters have, so that the camel
case shows in letters that have no lower case. The words come in at the right edge, cross at one
speed and leave at the left.
"""

import os
import re

from rich.text import Text

from llamatron.strings.about import MSG_BLOCK, MSG_BLOCK_LETTERS, MSG_DEMO_SCROLL
from llamatron.tui.components.title_card import BLACK_STYLE, TITLE_BLUE, blank_line, shaded
from llamatron.tui.drawing import NOTHING, SPACE

# How many columns and rows one block of a small letter takes, a square on most consoles, and how many times larger a large letter is.
SMALL_COLUMNS = 2
SMALL_ROWS = 1
LARGE_TIMES = 2
LETTER_ROWS = 5
# How tall the words are: a large letter's rows.
BANNER_ROWS = LETTER_ROWS * SMALL_ROWS * LARGE_TIMES
# The columns between two letters.
LETTER_GAP = 2
# How fast the words cross, in columns a second.
COLUMNS_PER_SECOND = 90.0
FULL = 1.0
# What parts the words of a file's name, and the number a learning demo's name starts with, which is its place and not its name.
WORD_BREAK = re.compile(r'[^A-Za-z0-9]+')
LEADING_NUMBER = re.compile(r'^[0-9]+[^A-Za-z0-9]+(?=.)')


def camel_case(name):
    """Return a name's words run together, each starting with a capital: hocket_shanty gives HocketShanty."""
    return NOTHING.join(word[:1].upper() + word[1:] for word in WORD_BREAK.split(name) if word)


def demo_name(path):
    """Return a set's name for the scroll from its file: no folder, no ending, no number in front, in camel case."""
    name = os.path.splitext(os.path.basename(path))[0]
    return camel_case(LEADING_NUMBER.sub(NOTHING, name))


def scroll_text_for(path):
    """Return the words a recording of the set at path scrolls: DEMO: and its name."""
    return MSG_DEMO_SCROLL.format(name=demo_name(path))


def is_large(character):
    """Return whether a character is drawn large: a capital, a digit and the colon, and not a small letter or a space."""
    return not character.islower() and character != SPACE


def letter_lines(character):
    """Return one character's rows, BANNER_ROWS of them: its capital's shape, large or small, a small one standing on the bottom row. A character with no shape is a space."""
    if character.upper() not in MSG_BLOCK_LETTERS:
        character = SPACE
    shape = MSG_BLOCK_LETTERS[character.upper()]
    times = LARGE_TIMES if is_large(character) else 1
    columns = SMALL_COLUMNS * times
    drawn = []
    for row in shape:
        line = NOTHING.join((MSG_BLOCK if block != SPACE else SPACE) * columns for block in row)
        drawn.extend([line] * (SMALL_ROWS * times))
    return [SPACE * len(drawn[0])] * (BANNER_ROWS - len(drawn)) + drawn


def banner(text):
    """Return the words as BANNER_ROWS rows of blocks and spaces, every row as wide as the words."""
    letters = [letter_lines(character) for character in text]
    return [(SPACE * LETTER_GAP).join(letter[row] for letter in letters) for row in range(BANNER_ROWS)]


def scroll_seconds(*, text, width):
    """Return how long the words take to cross a screen of a width, from the first column coming in to the last going out."""
    return (width + len(banner(text)[0])) / COLUMNS_PER_SECOND


def scroll_lines(*, rows, width, height, elapsed):
    """Return the screen's lines at a moment: the banner's rows in the middle, moved left by the time gone, on black."""
    shift = max(int(elapsed * COLUMNS_PER_SECOND), 0)
    top = max((height - len(rows)) // 2, 0)
    style = shaded(colour=TITLE_BLUE, level=FULL)
    lines = [blank_line(width) for _ in range(height)]
    for place, row in enumerate(rows):
        if top + place >= height:
            break
        shown = (SPACE * width + row + SPACE * width)[shift:shift + width].ljust(width)
        lines[top + place] = drawn_row(shown=shown, style=style)
    return lines


def drawn_row(*, shown, style):
    """Return one row of the words, its blocks in the style and the rest black."""
    line = Text()
    for run in re.findall(r' +|[^ ]+', shown):
        line.append(run, style=BLACK_STYLE if run[0] == SPACE else style)
    return line
