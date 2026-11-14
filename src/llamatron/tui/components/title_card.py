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

"""The title on black: LLAMATRON in block letters, a scanner sweeping under it, and the address, all in blue and centred.

The user's design, after the start page of a classic video game. The letters come in by ENTRANCE,
riding sine waves and settling into the word, or fading in; then a wide glow, the scanner, sweeps
right and back left under them, shaded through many tones of the blue, entering and leaving at the
title's edges, and is gone; the address shows two lines under the word. The start screen adds its
prompt six lines under the address, pulsing slowly between dim and bright, and a title shown for a
set time fades to black over its last moments. title_lines draws it at a moment, as Rich text, and
knows nothing of Textual, so that the start screen, the recordings' splash and the batch videos draw
the same title. The letters are drawn twice as wide where the screen has room, since a terminal's
cells are about twice as tall as they are wide.
"""

import functools
import math

from rich.color import Color
from rich.style import Style as RichStyle
from rich.text import Text

from llamatron.tui.drawing import NOTHING, SPACE
from llamatron.strings.about import MSG_BLOCK, MSG_BLOCK_LETTERS, MSG_SPLASH_ADDRESS, MSG_SPLASH_WORD, MSG_START_PROMPT


class Entrance:
    """How the title's letters come in."""

    SINE_WAVES = 'sine waves'
    FADE = 'fade'


# How the letters come in, a constant so that another entrance can be tried (the user's ask).
ENTRANCE = Entrance.SINE_WAVES
# The colours, on black: the word, the address, the scanner's brightest, and the prompt at its dimmest and brightest.
BLACK = (0, 0, 0)
TITLE_BLUE = (60, 120, 255)
ADDRESS_BLUE = (80, 120, 210)
SCANNER_BLUE = (110, 165, 255)
PROMPT_DIM = (40, 80, 170)
PROMPT_BRIGHT = (110, 160, 255)
# The letters: a blank column between two, each block twice as wide where the screen has room, and room for the waves above and below.
LETTER_GAP = 1
WIDE = 2
NARROW = 1
LETTER_ROWS = 5
# The entrance: the letters fade in over FADE_IN_SECONDS, and with sine waves ride waves WAVE_ROWS high for WAVE_SECONDS, settling over SETTLE_SECONDS.
FADE_IN_SECONDS = 0.8
WAVE_ROWS = 3
WAVE_SECONDS = 1.6
SETTLE_SECONDS = 0.8
WAVES_PER_SECOND = 1.2
# The scanner, after the letters settle: a glow SCANNER_SHARE of the title wide each side of its middle, sweeping right and back left over SCAN_SECONDS.
SCAN_DELAY_SECONDS = 0.2
SCAN_SECONDS = 2.4
SCANNER_SHARE = 0.25
# The address fades in as the letters settle; the prompt fades in once the scanner is gone, and then pulses once every PULSE_SECONDS.
ADDRESS_FADE_SECONDS = 0.6
PROMPT_FADE_SECONDS = 0.5
PULSE_SECONDS = 1.6
# The lines under the word: a blank line, the scanner, a blank line, the address, and the prompt on the sixth line under the address.
SCANNER_ROW = LETTER_ROWS + 1
ADDRESS_ROW = SCANNER_ROW + 2
PROMPT_ROW = ADDRESS_ROW + 6
# A title shown for a set time fades to black over its last FADE_OUT_SECONDS.
FADE_OUT_SECONDS = 0.8
# How long the title takes to finish, its letters settled, the scanner gone, and a moment held before fading out: a batch video's title.
HOLD_SECONDS = 0.4


def settled_at():
    """Return the moment the letters have settled into the word."""
    if ENTRANCE == Entrance.SINE_WAVES:
        return WAVE_SECONDS + SETTLE_SECONDS
    return FADE_IN_SECONDS


def scan_start():
    return settled_at() + SCAN_DELAY_SECONDS


def scan_end():
    return scan_start() + SCAN_SECONDS


def whole_title_seconds():
    """Return how long the whole title takes, entrance, scanner, a moment held and the fade to black, for a title that fades out on its own."""
    return scan_end() + HOLD_SECONDS + FADE_OUT_SECONDS


def eased(share):
    """Return a share from 0 to 1 eased by a cosine, so that a fade or a settling starts and ends gently."""
    share = min(max(share, 0.0), 1.0)
    return (1 - math.cos(share * math.pi)) / 2


def scale_for(*, word, width):
    """Return how many columns a block takes: two when the word fits the width that way, else one."""
    return WIDE if words_width(word=word, scale=WIDE) <= width else NARROW


def letter_rows(*, word, scale):
    """Return, for each letter of a word, its rows drawn scale columns to a block."""
    return [[row.replace(MSG_BLOCK, MSG_BLOCK * scale).replace(SPACE, SPACE * scale) for row in MSG_BLOCK_LETTERS[letter]] for letter in word]


def words_width(*, word, scale):
    return sum(len(MSG_BLOCK_LETTERS[letter][0]) * scale for letter in word) + LETTER_GAP * scale * (len(word) - 1)


def wave_offset(*, elapsed, place, count):
    """Return how many rows a letter is above or below its place in the word at a moment, riding its wave as it comes in."""
    if ENTRANCE != Entrance.SINE_WAVES or elapsed >= settled_at():
        return 0
    height = WAVE_ROWS if elapsed <= WAVE_SECONDS else WAVE_ROWS * (1 - eased((elapsed - WAVE_SECONDS) / SETTLE_SECONDS))
    return round(height * math.sin(math.tau * (WAVES_PER_SECOND * elapsed + place / count)))


def scanner_level(*, column, width, elapsed):
    """Return how bright the scanner is at a column of a title width columns wide, at a moment: 0 outside the glow, 1 at its middle."""
    if not scan_start() <= elapsed < scan_end():
        return 0.0
    half = max(width * SCANNER_SHARE, 1.0)
    sweep = (elapsed - scan_start()) / SCAN_SECONDS * 2
    share = sweep if sweep < 1 else 2 - sweep
    middle = -half + share * (width + 2 * half)
    distance = abs(column - middle)
    if distance >= half:
        return 0.0
    return math.cos(math.pi / 2 * distance / half) ** 2


def prompt_level(elapsed):
    """Return how bright the prompt is at a moment: nothing until the scanner is gone, then fading in and pulsing."""
    since = elapsed - scan_end()
    if since < 0:
        return 0.0
    pulse = (1 + math.cos(math.tau * since / PULSE_SECONDS)) / 2
    return eased(since / PROMPT_FADE_SECONDS) * (0.4 + 0.6 * pulse)


def fade_level(*, elapsed, seconds):
    """Return how much of the title shows at a moment: all of it, or less over the last moments of a title shown for seconds."""
    if seconds is None:
        return 1.0
    return eased((seconds - elapsed) / FADE_OUT_SECONDS)


# Levels are kept to this many steps, so that each style is made once and remembered.
LEVEL_STEPS = 64


def shaded(*, colour, level):
    """Return a style of a colour turned down to a level from 0 to 1, on black."""
    return style_of(colour=colour, step=round(min(max(level, 0.0), 1.0) * LEVEL_STEPS))


@functools.lru_cache(maxsize=None)
def style_of(*, colour, step):
    """Return the style of a colour at a step of LEVEL_STEPS, on black, made once."""
    red, green, blue = (round(channel * step / LEVEL_STEPS) for channel in colour)
    return RichStyle(color=Color.from_rgb(red, green, blue), bgcolor=Color.from_rgb(*BLACK))


BLACK_STYLE = style_of(colour=BLACK, step=0)


def blank_line(width):
    return Text(SPACE * width, style=BLACK_STYLE)


def centred_text(*, text, width, colour, level):
    """Return a line with text centred in a colour at a level, or a blank line while the level is nothing."""
    if level <= 0:
        return blank_line(width)
    left = max((width - len(text)) // 2, 0)
    line = Text(SPACE * left, style=BLACK_STYLE)
    line.append(text[:width], style=shaded(colour=colour, level=level))
    line.append(SPACE * max(width - left - len(text), 0), style=BLACK_STYLE)
    return line


def title_lines(*, width, height, elapsed, prompt=False, seconds=None):
    """Return the title's lines for a screen width by height at a moment, with the prompt or without, fading out over its last moments when it is shown for seconds."""
    scale = scale_for(word=MSG_SPLASH_WORD, width=width)
    rows = letter_rows(word=MSG_SPLASH_WORD, scale=scale)
    letters_width = words_width(word=MSG_SPLASH_WORD, scale=scale)
    gap = LETTER_GAP * scale
    left = max((width - letters_width) // 2, 0)
    tall = (PROMPT_ROW if prompt else ADDRESS_ROW) + 1
    top = max((height - tall) // 2, 0)
    fade = fade_level(elapsed=elapsed, seconds=seconds)
    letters = eased(elapsed / FADE_IN_SECONDS) * fade
    cells = [[None] * width for _ in range(height)]
    column = left
    for place, letter in enumerate(rows):
        lift = wave_offset(elapsed=elapsed, place=place, count=len(rows))
        for row, text in enumerate(letter):
            line = top + row - lift
            if 0 <= line < height:
                for offset, character in enumerate(text):
                    if character != SPACE and 0 <= column + offset < width:
                        cells[line][column + offset] = (character, TITLE_BLUE, letters)
        column += len(letter[0]) + gap
    scanner_line = top + SCANNER_ROW
    if scanner_line < height:
        for offset in range(letters_width):
            level = scanner_level(column=offset, width=letters_width, elapsed=elapsed)
            if level > 0 and 0 <= left + offset < width:
                cells[scanner_line][left + offset] = (MSG_BLOCK, SCANNER_BLUE, level * fade)
    lines = [drawn_line(cells=row, width=width) for row in cells]
    address_line = top + ADDRESS_ROW
    if address_line < height:
        lines[address_line] = centred_text(text=MSG_SPLASH_ADDRESS, width=width, colour=ADDRESS_BLUE, level=eased((elapsed - settled_at()) / ADDRESS_FADE_SECONDS) * fade)
    prompt_line = top + PROMPT_ROW
    if prompt and prompt_line < height:
        level = prompt_level(elapsed)
        colour = tuple(round(dim + (bright - dim) * level) for dim, bright in zip(PROMPT_DIM, PROMPT_BRIGHT))
        lines[prompt_line] = centred_text(text=MSG_START_PROMPT, width=width, colour=colour, level=min(level * 2.5, 1.0) * fade)
    return lines


def drawn_line(*, cells, width):
    """Return one line of the title from its cells, each a character, a colour and a level, or None for black, a run of one style at a time."""
    line = Text()
    run = []
    style = None
    for cell in cells:
        if cell is None:
            cell_style = BLACK_STYLE
            character = SPACE
        else:
            character, colour, level = cell
            cell_style = shaded(colour=colour, level=level)
        if cell_style is not style and run:
            line.append(NOTHING.join(run), style=style)
            run = []
        style = cell_style
        run.append(character)
    if run:
        line.append(NOTHING.join(run), style=style)
    return line if width else Text()

