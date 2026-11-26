# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A MIDI note as its name and octave, shown and typed: C3 is note 36, as a drum pattern writes its notes."""

from llamatron.model.values import note as note_values
from llamatron.music_theory.fundamentals import intervals
from llamatron.user_strings import marks

LOWEST_NOTE = 0
HIGHEST_NOTE = 127
SHARP = '#'
FLAT = 'b'
HALF_STEPS_OF_LETTER = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
HALF_STEPS_OF_MARK = {SHARP: 1, FLAT: -1}


def note_shown(note):
    """Return a MIDI note as its name and octave, a black key as a sharp."""
    return marks.MSG_NOTE_NAME_SHOWN.format(name=note_values.SHARP_NAMES[note % intervals.HALF_STEPS_PER_OCTAVE], octave=note // intervals.HALF_STEPS_PER_OCTAVE)


def note_typed(text):
    """Return the MIDI note typed as a letter, a sharp or a flat where there is one, and an octave, such as C3, f#4 or Bb2, or None for
    text that is no note there is."""
    text = text.strip()
    if not text or text[0].upper() not in HALF_STEPS_OF_LETTER:
        return None
    rest = text[1:]
    mark = 0
    if rest[:1] in HALF_STEPS_OF_MARK and not rest[:1].isdigit():
        mark = HALF_STEPS_OF_MARK[rest[0]]
        rest = rest[1:]
    if not rest.isdigit():
        return None
    note = int(rest) * intervals.HALF_STEPS_PER_OCTAVE + HALF_STEPS_OF_LETTER[text[0].upper()] + mark
    return note if LOWEST_NOTE <= note <= HIGHEST_NOTE else None
