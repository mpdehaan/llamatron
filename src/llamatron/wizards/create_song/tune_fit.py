# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Fits a tune written by hand to chords that changed under it.

A long note is heard against its chord: held over a chord it is no note of, it clashes. A short
note is a passing note, on its way between two others, and is heard as movement. So when the
chords under a tune change, each long note that is no note of its new chord moves to the
nearest note of that chord, and every short note stays as written, as do the rhythm and the
shape of the tune.
"""

from fractions import Fraction

from llamatron.model.schema.file_format import PatternSetting, Row

DEGREE = 'degree'
# How many notes a scale has, and the notes of a chord counted up its scale from its root: the root, the third and the fifth.
NOTES_IN_SCALE = 7
CHORD_STEPS = (0, 2, 4)
# A note at least this long, in whole notes, is heard against its chord; a shorter one passes.
LONG_NOTE = Fraction(1, 4)


def fitted(*, pattern, chords, bar):
    """Return a tune's pattern with each long note that is no note of its chord moved to the nearest note of the chord.

    pattern is a pattern's data, chords the chord of each bar in order, each a mapping with its
    degree, played round again when the tune is longer, and bar how long a bar lasts in whole
    notes. A pattern with no degrees, or chords with none, comes back as it was.
    """
    degrees = list(pattern.get(Row.DEGREE) or [])
    if not degrees or not chords:
        return dict(pattern)
    step = Fraction(pattern[PatternSetting.STEP_SIZE])
    ties = list(pattern.get(Row.TIE) or [False] * len(degrees))
    octaves = list(pattern.get(Row.OCTAVE) or [None] * len(degrees))
    for place, degree in enumerate(degrees):
        if degree is None or steps_held(ties=ties, degrees=degrees, place=place) * step < LONG_NOTE:
            continue
        chord = chord_at(chords=chords, bar=int(place * step // bar))
        move = move_to_chord(degree=degree, root=chord)
        if move:
            octaves_up, at = divmod(degree - 1 + move, NOTES_IN_SCALE)
            degrees[place] = at + 1
            if octaves_up and octaves[place] is not None:
                octaves[place] += octaves_up
    moved = {**pattern, Row.DEGREE: degrees}
    if Row.OCTAVE in pattern:
        moved[Row.OCTAVE] = octaves
    return moved


def steps_held(*, ties, degrees, place):
    """Return how many steps the note at a place lasts: its own, and each step after it that ties on with no note of its own."""
    held = 1
    while place + held < len(degrees) and ties[place + held] and degrees[place + held] is None:
        held += 1
    return held


def chord_at(*, chords, bar):
    """Return the degree of the root of the chord a bar hears, the first of a bar that two chords share."""
    chord = chords[bar % len(chords)]
    while isinstance(chord, list):
        chord = chord[0]
    return chord[DEGREE] if isinstance(chord, dict) else chord


def move_to_chord(*, degree, root):
    """Return how many notes of the scale a degree moves, up or down, to reach the nearest note of a chord: nothing for a note of
    the chord, and down where a note above and a note below are as near."""
    notes = [(root - 1 + steps) % NOTES_IN_SCALE for steps in CHORD_STEPS]
    at = (degree - 1) % NOTES_IN_SCALE
    moves = []
    for note in notes:
        up = (note - at) % NOTES_IN_SCALE
        moves += [up, up - NOTES_IN_SCALE]
    return min(moves, key=lambda move: (abs(move), move))
