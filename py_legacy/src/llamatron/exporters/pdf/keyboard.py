# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A piano keyboard drawn on a PDF page, from one C to the B an octave or more above, with the keys a chord presses filled in
their colours and named, and each C marked with its octave, C4 being middle C.

Keyboards drawn over the same range line up key for key, so that a page of chords shows how the hand moves between them.
"""

from typing import NamedTuple

from llamatron.exporters.pdf import canvas, palette
from llamatron.music_theory.fundamentals import intervals
from llamatron.user_strings import printing

OCTAVE = intervals.HALF_STEPS_PER_OCTAVE
BLACK_KEYS = frozenset({1, 3, 6, 8, 10})
# The fewest keys a keyboard shows, two octaves, so that every chord's keyboard reads alike.
FEWEST_KEYS = 2 * OCTAVE
MIDDLE_C = 60
LINE_WIDTH = 0.6
BLACK_WIDTH = 0.6
BLACK_HEIGHT = 0.62
OCTAVE_LABEL_SIZE = 6
OCTAVE_LABEL_DROP = 8
LARGEST_LABEL = 8.0
LABEL_SHARE = 0.55
LABEL_RISE = 4
# The octave a MIDI number's C begins, C4 being middle C.
OCTAVE_OF_C0 = 1


class PrintedKeyboard(NamedTuple):
    """Where a keyboard is drawn, its lower left corner and its size in points, and the range of keys it shows, from a C to
    a B, as MIDI numbers."""

    x: float
    y: float
    width: float
    height: float
    low: int
    high: int


def keyboard_range(pitches):
    """Return the keys a keyboard shows for some notes: from the C at or below the lowest to the B at or above the highest,
    two octaves at least, from middle C where there are no notes."""
    pitches = list(pitches) or [MIDDLE_C]
    low = (min(pitches) // OCTAVE) * OCTAVE
    high = (max(pitches) // OCTAVE) * OCTAVE + OCTAVE - 1
    return low, max(high, low + FEWEST_KEYS - 1)


def draw_keyboard(*, page, keyboard, pressed, labels, octaves=True):
    """Draw a keyboard on a page with the keys pressed, a colour by MIDI number, filled, each label, by MIDI number, written
    on its key, and each C named under it with its octave unless told not to."""
    whites = [pitch for pitch in range(keyboard.low, keyboard.high + 1) if pitch % OCTAVE not in BLACK_KEYS]
    white_width = keyboard.width / len(whites)
    page.setLineWidth(LINE_WIDTH)
    page.setStrokeColor(palette.INK)
    lefts = {}
    for place, pitch in enumerate(whites):
        left = keyboard.x + place * white_width
        lefts[pitch] = left
        page.setFillColor(pressed.get(pitch, palette.WHITE))
        page.rect(left, keyboard.y, white_width, keyboard.height, stroke=1, fill=1)
        if octaves and pitch % OCTAVE == 0:
            _draw_octave(page=page, x=left + white_width / 2, y=keyboard.y, pitch=pitch)
        if pitch in labels:
            _draw_label(page=page, x=left + white_width / 2, y=keyboard.y, text=labels[pitch], size=min(LARGEST_LABEL, white_width * LABEL_SHARE))
    _draw_black_keys(page=page, keyboard=keyboard, lefts=lefts, pressed=pressed, labels=labels)


def _draw_black_keys(*, page, keyboard, lefts, pressed, labels):
    """Draw the black keys over the white, each between the white key below it and the next."""
    white_width = keyboard.width / len(lefts)
    width = white_width * BLACK_WIDTH
    height = keyboard.height * BLACK_HEIGHT
    bottom = keyboard.y + keyboard.height - height
    for pitch in range(keyboard.low, keyboard.high + 1):
        if pitch % OCTAVE not in BLACK_KEYS or pitch - 1 not in lefts:
            continue
        left = lefts[pitch - 1] + white_width - width / 2
        page.setFillColor(pressed.get(pitch, palette.INK))
        page.rect(left, bottom, width, height, stroke=1, fill=1)
        if pitch in labels:
            _draw_label(page=page, x=left + width / 2, y=bottom, text=labels[pitch], size=min(LARGEST_LABEL, width * LABEL_SHARE))


def _draw_octave(*, page, x, y, pitch):
    """Name a C under its key with its octave."""
    page.setFillColor(palette.MUTED)
    page.setFont(canvas.FONT, OCTAVE_LABEL_SIZE)
    page.drawCentredString(x, y - OCTAVE_LABEL_DROP, printing.MSG_OCTAVE_C.format(octave=pitch // OCTAVE - OCTAVE_OF_C0))


def _draw_label(*, page, x, y, text, size):
    """Write a key's label at its foot, in white on its colour."""
    page.setFillColor(palette.WHITE)
    page.setFont(canvas.BOLD_FONT, size)
    page.drawCentredString(x, y + LABEL_RISE, text)
