# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Chord Changes pages of a packet: every move from one chord to the next the song makes, in the order it first makes
it, with how many times, each chord on a small keyboard; the second voiced as near the first as it can be, so that the
picture shows the smallest move of the hand: the keys that stay under the fingers blue, the keys that move red, and the same
in words, "stay: E, G" and "move: C→B", with "add B" or "lift E" where the second chord has more notes or fewer.
"""

from reportlab.lib import colors
from reportlab.lib.units import inch
from typing import NamedTuple

from llamatron.exporters.pdf import canvas, palette
from llamatron.exporters.pdf.canvas import draw_heading
from llamatron.exporters.pdf.chord_chart import closest_voicing
from llamatron.exporters.pdf.keyboard import draw_keyboard, keyboard_range, PrintedKeyboard
from llamatron.music_theory.fundamentals import intervals, voice_leading
from llamatron.music_theory.harmony.heard_chords import chord_shapes, chord_tone_names
from llamatron.user_strings import printing

OCTAVE = intervals.HALF_STEPS_PER_OCTAVE
STAY = colors.HexColor('#0090FF')
MOVE = colors.HexColor('#E5484D')
MARGIN = 0.6 * inch
ROW_HEIGHT = 1.05 * inch
KEYBOARD_WIDTH = 1.9 * inch
KEYBOARD_HEIGHT = 0.62 * inch
FIRST_KEYBOARD = 2.1 * inch
ARROW_GAP = 0.5 * inch
INTRODUCTION_GAP = 22
INTRODUCTION_DROP = 8
INTRODUCTION_SIZE = 9
NAMES_SIZE = 13
NAMES_DROP = 14
NUMERALS_DROP = 27
NUMERALS_SIZE = 9
WORDS_SIZE = 8
STAY_DROP = 40
MOVE_DROP = 51
ARROW_SIZE = 16
KEYBOARD_DROP = 4
# The middle of the hand the first chord of a change is voiced around, E above middle C.
HAND_MIDDLE = 64


class ChordChange(NamedTuple):
    """A move the song makes from one chord to the next: the two chords as printed, and how many times the song makes it."""

    before: object
    after: object
    times: int


def chord_changes(printed):
    """Return every move a printed song makes from one chord to another, in the order it first makes each, with how many
    times; chords of one name back to back are one."""
    played = []
    for chord in printed.chords:
        if not played or played[-1].name != chord.name:
            played.append(chord)
    changes = {}
    for before, after in zip(played, played[1:]):
        key = (before.name, after.name)
        if key in changes:
            changes[key] = changes[key]._replace(times=changes[key].times + 1)
        else:
            changes[key] = ChordChange(before=before, after=after, times=1)
    return list(changes.values())


def nearest_voicing(*, chord, before):
    """Return a chord's notes voiced to move least from the notes before it, as MIDI numbers lowest first: every inversion
    in the octaves around them tried, the one nearer the middle of the hand winning a tie."""
    close = sorted(intervals_from(chord=chord))
    best = None
    for inversion in voice_leading.inversions(close):
        for shift in (-OCTAVE, 0, OCTAVE):
            placed = tuple(pitch + shift for pitch in inversion)
            rank = (voice_leading.movement(pitches=placed, before=list(before)), abs(sum(placed) / len(placed) - HAND_MIDDLE))
            if best is None or rank < best[0]:
                best = (rank, placed)
    return best[1]


def intervals_from(*, chord):
    """Return a chord's notes in root position from the octave of middle C, as MIDI numbers."""
    return [HAND_MIDDLE - HAND_MIDDLE % OCTAVE + chord.root + step for step in sorted(chord_shapes()[chord.symbol])]


def draw_chord_changes(*, page, printed):
    """Draw a printed song's Chord Changes pages from the page's start, or nothing for a song of fewer than two chords;
    return whether anything was drawn."""
    changes = chord_changes(printed)
    if not changes:
        return False
    _, height = page.get_page_size()
    top = height - MARGIN - INTRODUCTION_GAP
    per_page = max(1, int((top - MARGIN) // ROW_HEIGHT))
    pages = -(-len(changes) // per_page)
    scale = printed.main_key()
    for place, change in enumerate(changes):
        if place % per_page == 0:
            if place:
                page.showPage()
            top = _draw_page_heading(page=page, printed=printed, index=place // per_page + 1, total=pages)
        _draw_change(page=page, change=change, top=top - (place % per_page) * ROW_HEIGHT, scale=scale)
    page.showPage()
    return True


def change_words(*, change, first, second, scale):
    """Return a change's two lines of words: the notes that stay, and each note that moves with where it goes, a note the
    second chord adds, and a note it lifts."""
    names_before = chord_tone_names(root=change.before.root, symbol=change.before.symbol, scale=scale)
    names_after = chord_tone_names(root=change.after.root, symbol=change.after.symbol, scale=scale)
    stay = [names_after[pitch % OCTAVE] for pitch in second if pitch in first]
    leaving = [pitch for pitch in first if pitch not in second]
    arriving = [pitch for pitch in second if pitch not in first]
    moves = [printing.MSG_MOVE_TO.format(before=names_before[old % OCTAVE], after=names_after[new % OCTAVE]) for old, new in zip(leaving, arriving)]
    moves += [printing.MSG_ADD_NOTE.format(note=names_after[new % OCTAVE]) for new in arriving[len(leaving):]]
    moves += [printing.MSG_LIFT_NOTE.format(note=names_before[old % OCTAVE]) for old in leaving[len(arriving):]]
    kept = printing.MSG_NAMES_JOIN.join(stay) or printing.MSG_NOTHING_STAYS
    moved = printing.MSG_NAMES_JOIN.join(moves) or printing.MSG_NOTHING_MOVES
    return printing.MSG_STAY.format(notes=kept), printing.MSG_MOVE.format(notes=moved)


def _draw_page_heading(*, page, printed, index, total):
    """Draw a Chord Changes page's heading and the line saying how to read it, and return where the changes start."""
    below = draw_heading(page=page, title=printed.title, detail=printing.MSG_PAGE_OF.format(page=printing.MSG_CHORD_CHANGES, index=index, total=total))
    page.setFont(canvas.FONT, INTRODUCTION_SIZE)
    page.setFillColor(palette.MUTED)
    page.drawString(MARGIN, below - INTRODUCTION_DROP, printing.MSG_CHORD_CHANGES_INTRODUCTION)
    return below - INTRODUCTION_GAP


def _draw_change(*, page, change, top, scale):
    """Draw one change: its chords' names and numerals, how many times, its two keyboards and its words."""
    first, _ = closest_voicing(root=change.before.root, symbol=change.before.symbol)
    second = nearest_voicing(chord=change.after, before=first)
    page.setFillColor(palette.INK)
    page.setFont(canvas.BOLD_FONT, NAMES_SIZE)
    page.drawString(MARGIN, top - NAMES_DROP, printing.MSG_CHANGE.format(before=change.before.name, after=change.after.name))
    page.setFont(canvas.FONT, NUMERALS_SIZE)
    page.setFillColor(palette.MUTED)
    page.drawString(MARGIN, top - NUMERALS_DROP, printing.MSG_CHANGE_NUMERALS.format(before=change.before.numeral, after=change.after.numeral, times=change.times))
    stay, move = change_words(change=change, first=first, second=second, scale=scale)
    page.setFont(canvas.FONT, WORDS_SIZE)
    page.drawString(MARGIN, top - STAY_DROP, stay)
    page.drawString(MARGIN, top - MOVE_DROP, move)
    low, high = keyboard_range([*first, *second])
    for left, chord, notes, other in ((FIRST_KEYBOARD, change.before, first, second), (FIRST_KEYBOARD + KEYBOARD_WIDTH + ARROW_GAP, change.after, second, first)):
        names = chord_tone_names(root=chord.root, symbol=chord.symbol, scale=scale)
        keyboard = PrintedKeyboard(x=MARGIN + left, y=top - KEYBOARD_HEIGHT - KEYBOARD_DROP, width=KEYBOARD_WIDTH, height=KEYBOARD_HEIGHT, low=low, high=high)
        pressed = {pitch: STAY if pitch in other else MOVE for pitch in notes}
        draw_keyboard(page=page, keyboard=keyboard, pressed=pressed, labels={pitch: names[pitch % OCTAVE] for pitch in notes})
    page.setFillColor(palette.INK)
    page.setFont(canvas.BOLD_FONT, ARROW_SIZE)
    page.drawCentredString(MARGIN + FIRST_KEYBOARD + KEYBOARD_WIDTH + ARROW_GAP / 2, top - KEYBOARD_HEIGHT / 2 - NAMES_DROP / 2, printing.MSG_ARROW)
