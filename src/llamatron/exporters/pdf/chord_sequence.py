# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Chord Sequence page of a packet: the whole song's chords on as few pages as they fit, section by section, each section
once with how many times it plays, a cell for each bar holding the chords that start in it with their numerals, and the key
marked wherever it changes, with what it is in the song's main key: Key: F major (IV of C major).
"""

from reportlab.lib.units import inch

from llamatron.exporters.pdf import canvas, palette
from llamatron.exporters.pdf.canvas import draw_heading
from llamatron.exporters.pdf.piano_roll import printed_spans
from llamatron.model.schema.file_format import ChordSymbol
from llamatron.model.values import note as note_values
from llamatron.music_theory.fundamentals import intervals
from llamatron.music_theory.harmony.heard_chords import chord_texts
from llamatron.user_strings import printing

MARGIN = 0.6 * inch
CELL_HEIGHT = 0.5 * inch
# The most beats a line of cells holds, so that a line of 2/4 holds eight bars and a line of 4/4 four.
LINE_BEATS = 16
SECTION_HEIGHT = 22
SECTION_SIZE = 11
KEY_SIZE = 8.5
NAME_SIZE = 11
NUMERAL_SIZE = 7
LINE_WIDTH = 0.6
INSET = 4
NAME_DROP = 14
NUMERAL_DROP = 25
HEADING_GAP = 10
CHORD_GAP = 6
MINOR_THIRD = 3
MAJOR_THIRD = 4
# A scale kind's name joins its words with an underscore, printed as a space.
KIND_JOIN = '_'
WORD_SPACE = ' '


def section_bars(*, printed, start, end):
    """Return a stretch's bars, each the chords that start in it, as (bar's start, chords)."""
    bars = []
    place = start
    while place < end:
        bar_end = place + printed.bar_length()
        bars.append((place, [chord for chord in printed.chords if place <= chord.start < bar_end]))
        place = bar_end
    return bars


def key_line(*, scale, main):
    """Return how a section's key is written: its name, and what its root's chord is in the song's main key where that
    differs, Key: F major (IV of C major)."""
    text = printing.MSG_KEY.format(key=key_name(scale))
    if main is None or scale == main:
        return text
    symbol = ChordSymbol.MAJOR
    if MINOR_THIRD in scale.get_half_steps() and MAJOR_THIRD not in scale.get_half_steps():
        symbol = ChordSymbol.MINOR
    root = note_values.SEMITONES_ABOVE_C[scale.get_root()] % intervals.HALF_STEPS_PER_OCTAVE
    _, numeral = chord_texts(root=root, symbol=symbol, scale=main)
    return printing.MSG_KEY_IN.format(key=text, numeral=numeral, main=key_name(main))


def key_name(scale):
    """Return a key's name as printed: its root and its kind, F major."""
    return printing.MSG_KEY_NAME.format(root=scale.get_root(), kind=scale.get_kind().replace(KIND_JOIN, WORD_SPACE))


def draw_chord_sequence(*, page, printed):
    """Draw a printed song's Chord Sequence from the page's start, as many pages as it takes."""
    width, height = page.get_page_size()
    per_line = max(1, LINE_BEATS // printed.signature.get_beats())
    cell = (width - 2 * MARGIN) / per_line
    top = draw_heading(page=page, title=printed.title, detail=printing.MSG_CHORD_SEQUENCE) - HEADING_GAP
    key = None
    for start, end in printed_spans(printed):
        bars = section_bars(printed=printed, start=start, end=end)
        lines = -(-len(bars) // per_line)
        if top - SECTION_HEIGHT - lines * CELL_HEIGHT < MARGIN:
            page.showPage()
            top = draw_heading(page=page, title=printed.title, detail=printing.MSG_CHORD_SEQUENCE) - HEADING_GAP
        scale = printed.key_at(start)
        top = _draw_section_heading(page=page, printed=printed, start=start, key_text=_key_text(scale=scale, before=key, main=printed.main_key()), top=top)
        key = scale
        for place, (_, chords) in enumerate(bars):
            row, column = divmod(place, per_line)
            _draw_cell(page=page, chords=chords, corner=(MARGIN + column * cell, top - row * CELL_HEIGHT), width=cell)
        top -= lines * CELL_HEIGHT
    page.showPage()


def _key_text(*, scale, before, main):
    """Return the key a section's heading names: its key where it differs from the section before's, else nothing."""
    if scale is None or scale == before:
        return printing.MSG_NO_KEY_CHANGE
    return key_line(scale=scale, main=main)


def _draw_section_heading(*, page, printed, start, key_text, top):
    """Write a section's name, with how many times it plays, and the key where it changes; return where its bars start."""
    name = printing.MSG_NO_SECTION_NAME
    for section in printed.sections:
        if section.start == start:
            name = section.name
            if section.times > 1:
                name = printing.MSG_SECTION_TIMES.format(section=section.name, times=section.times)
    page.setFillColor(palette.INK)
    page.setFont(canvas.BOLD_FONT, SECTION_SIZE)
    page.drawString(MARGIN, top - SECTION_SIZE, name)
    page.setFillColor(palette.MUTED)
    page.setFont(canvas.FONT, KEY_SIZE)
    page.drawRightString(page.get_page_size()[0] - MARGIN, top - SECTION_SIZE, key_text)
    return top - SECTION_HEIGHT


def _draw_cell(*, page, chords, corner, width):
    """Draw a bar's cell, its chords' names side by side with their numerals under them, or a dot for a bar that holds on."""
    left, top = corner
    page.setStrokeColor(palette.MUTED)
    page.setLineWidth(LINE_WIDTH)
    page.rect(left, top - CELL_HEIGHT, width, CELL_HEIGHT, stroke=1, fill=0)
    if not chords:
        page.setFillColor(palette.MUTED)
        page.setFont(canvas.FONT, NAME_SIZE)
        page.drawString(left + INSET, top - NAME_DROP, printing.MSG_HOLDS)
        return
    x = left + INSET
    for chord in chords:
        page.setFillColor(palette.INK)
        page.setFont(canvas.BOLD_FONT, NAME_SIZE)
        page.drawString(x, top - NAME_DROP, chord.name)
        page.setFillColor(palette.MUTED)
        page.setFont(canvas.FONT, NUMERAL_SIZE)
        page.drawString(x, top - NUMERAL_DROP, chord.numeral)
        x += max(page.stringWidth(chord.name, canvas.BOLD_FONT, NAME_SIZE), page.stringWidth(chord.numeral, canvas.FONT, NUMERAL_SIZE)) + CHORD_GAP
