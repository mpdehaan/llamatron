# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The chord chart of a packet: a card for each chord the song plays, in the order the song first plays them, so that a
learner practises the first and most used chords first.

Each card names its chord and its Roman numerals, every key the chord is heard in giving its own, says how many bars the
chord lasts across the song, and draws it on a keyboard in its closest voicing, the inversion nearest the middle of the hand,
named as fingering: E G C, 1st inversion. The keys wear their degrees' colours in the song's main key.
"""

from reportlab.lib.units import inch
from typing import NamedTuple

from llamatron.exporters.pdf import canvas, palette
from llamatron.exporters.pdf.canvas import draw_heading
from llamatron.exporters.pdf.keyboard import draw_keyboard, keyboard_range, PrintedKeyboard
from llamatron.model.schema.file_format import ChordSymbol
from llamatron.music_theory.fundamentals import intervals
from llamatron.music_theory.harmony.heard_chords import chord_shapes, chord_tone_names
from llamatron.user_strings import printing

OCTAVE = intervals.HALF_STEPS_PER_OCTAVE
MARGIN = 0.6 * inch
COLUMNS = 2
GUTTER = 0.35 * inch
CARD_HEIGHT = 2.05 * inch
KEYBOARD_HEIGHT = 1.0 * inch
# Where a card's lines sit below its top, and where its keyboard starts.
NAME_DROP = 16
NOTES_DROP = 30
KEYBOARD_DROP = 40
NAME_SIZE = 16
NUMERAL_SIZE = 15
NOTES_SIZE = 8.5
NUMERAL_FONT = 'Times-Bold'
CONTENT_GAP = 10
# The middle of the hand a voicing is chosen around, E above middle C.
HAND_MIDDLE = 64
# The note a chord's root is placed from, before its inversion is chosen: the octave of middle C.
ROOT_OCTAVE = 60


class ChartCard(NamedTuple):
    """A chord on the chart: its name, its root's pitch class and its symbol, its Roman numerals in the keys it is heard in,
    its voicing as MIDI numbers, lowest first, its inversion, 0 for root position, and how many bars it lasts across the
    song."""

    name: str
    root: int
    symbol: str
    numerals: tuple
    voicing: tuple
    inversion: int
    bars: object


def chart_cards(printed):
    """Return a card for each chord name of a printed song, in the order the song first plays them."""
    cards = {}
    for chord in printed.chords:
        bars = (chord.end - chord.start) / printed.bar_length()
        if chord.name in cards:
            card = cards[chord.name]
            numerals = card.numerals
            if chord.numeral and chord.numeral not in numerals:
                numerals = numerals + (chord.numeral,)
            cards[chord.name] = card._replace(numerals=numerals, bars=card.bars + bars)
            continue
        voicing, inversion = closest_voicing(root=chord.root, symbol=chord.symbol)
        cards[chord.name] = ChartCard(name=chord.name, root=chord.root, symbol=chord.symbol, numerals=(chord.numeral,) if chord.numeral else (), voicing=voicing, inversion=inversion, bars=bars)
    return list(cards.values())


def closest_voicing(*, root, symbol):
    """Return a chord's notes in the inversion whose middle is nearest the middle of the hand, as MIDI numbers lowest first,
    and the inversion, 0 for root position."""
    steps = sorted(chord_shapes()[symbol])
    close = [ROOT_OCTAVE + root + step for step in steps]
    best = None
    for inversion in range(len(close)):
        notes = close[inversion:] + [note + OCTAVE for note in close[:inversion]]
        for shift in (-OCTAVE, 0):
            placed = tuple(note + shift for note in notes)
            distance = abs(sum(placed) / len(placed) - HAND_MIDDLE)
            if best is None or distance < best[0]:
                best = (distance, placed, inversion)
    return best[1], best[2]


def draw_chord_chart(*, page, printed):
    """Draw a printed song's chord chart from the page's start, as many pages as its cards take, each with its heading."""
    cards = chart_cards(printed)
    width, height = page.get_page_size()
    low, high = keyboard_range(pitch for card in cards for pitch in card.voicing)
    card_width = (width - 2 * MARGIN - GUTTER * (COLUMNS - 1)) / COLUMNS
    top = height - MARGIN - CONTENT_GAP
    rows = max(1, int((top - MARGIN) // CARD_HEIGHT))
    per_page = rows * COLUMNS
    pages = max(1, -(-len(cards) // per_page))
    scale = printed.main_key()
    for place, card in enumerate(cards):
        if place % per_page == 0:
            if place:
                page.showPage()
            top = draw_heading(page=page, title=printed.title, detail=printing.MSG_PAGE_OF.format(page=printing.MSG_CHORD_CHART, index=place // per_page + 1, total=pages)) - CONTENT_GAP
        row, column = divmod(place % per_page, COLUMNS)
        _draw_card(page=page, card=card, corner=(MARGIN + column * (card_width + GUTTER), top - row * CARD_HEIGHT, card_width), keys=(low, high), scale=scale)
    page.showPage()


def card_notes(*, card, scale):
    """Return a card's line under its name: its notes as spelled, its inversion, a power chord's missing third, and how many
    bars it lasts."""
    names = chord_tone_names(root=card.root, symbol=card.symbol, scale=scale)
    notes = printing.MSG_NOTES_JOIN.join(names[pitch % OCTAVE] for pitch in card.voicing)
    shape = printing.MSG_INVERSIONS[min(card.inversion, len(printing.MSG_INVERSIONS) - 1)]
    if card.symbol == ChordSymbol.POWER:
        shape = printing.MSG_NO_THIRD
    bars = round(card.bars)
    lasting = printing.MSG_BARS.format(bars=bars)
    if bars <= 1:
        lasting = printing.MSG_ONE_BAR
    return printing.MSG_CARD_NOTES.format(notes=notes, inversion=shape, lasting=lasting)


def _draw_card(*, page, card, corner, keys, scale):
    """Draw one card, its top left corner and width given, on a keyboard of the chart's range."""
    left, top, width = corner
    page.setFillColor(palette.INK)
    page.setFont(canvas.BOLD_FONT, NAME_SIZE)
    page.drawString(left, top - NAME_DROP, card.name)
    page.setFont(NUMERAL_FONT, NUMERAL_SIZE)
    page.drawRightString(left + width, top - NAME_DROP, printing.MSG_NUMERALS_JOIN.join(card.numerals))
    page.setFont(canvas.FONT, NOTES_SIZE)
    page.setFillColor(palette.MUTED)
    page.drawString(left, top - NOTES_DROP, card_notes(card=card, scale=scale))
    pressed = {pitch: palette.color_of(pitch_class=pitch % OCTAVE, scale=scale) for pitch in card.voicing}
    names = chord_tone_names(root=card.root, symbol=card.symbol, scale=scale)
    labels = {pitch: names[pitch % OCTAVE] for pitch in card.voicing}
    keyboard = PrintedKeyboard(x=left, y=top - KEYBOARD_DROP - KEYBOARD_HEIGHT, width=width, height=KEYBOARD_HEIGHT, low=keys[0], high=keys[1])
    draw_keyboard(page=page, keyboard=keyboard, pressed=pressed, labels=labels)
