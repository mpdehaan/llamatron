# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""What the PDF export prints: page numbers, page headings and the words on each page of a packet or sheet of music.

The PDF export (exporters/pdf/) draws its pages with these.
"""

# exporters/pdf/canvas.py
# Every page's number in its lower right corner, and its heading: the song's title, then what the page is.
MSG_PAGE_NUMBER = 'page {number}/{total}'
MSG_PAGE_OF = '{page} ({index} of {total})'

# exporters/pdf/keyboard.py
# Each C under a keyboard, with its octave, C4 being middle C.
MSG_OCTAVE_C = 'C{octave}'

# exporters/pdf/chord_chart.py
# The chord chart's pages, and the line under each card's name: its notes, its inversion and how long it lasts in the song.
MSG_CHORD_CHART = 'Chord Chart'
MSG_NOTES_JOIN = ' '
MSG_NUMERALS_JOIN = ', '
MSG_CARD_NOTES = '{notes}, {inversion}    {lasting}'
MSG_INVERSIONS = ('root position', '1st inversion', '2nd inversion', '3rd inversion')
MSG_ONE_BAR = '1 bar'
MSG_BARS = '{bars} bars'
MSG_NO_THIRD = 'no third'

# exporters/pdf/chord_changes.py
# The Chord Changes pages: each move between chords, its numerals and how often the song makes it, and which notes stay
# under the fingers and which move.
MSG_CHORD_CHANGES = 'Chord Changes'
MSG_CHORD_CHANGES_INTRODUCTION = ('Each move between chords, in the order the song first makes it. Blue keys stay under your '
                                  'fingers; red keys move to the next chord.')
MSG_CHANGE = '{before}  →  {after}'
MSG_CHANGE_NUMERALS = '{before} → {after}   ·   {times}× in the song'
MSG_ARROW = '→'
MSG_STAY = 'stay: {notes}'
MSG_MOVE = 'move: {notes}'
MSG_MOVE_TO = '{before}→{after}'
MSG_NAMES_JOIN = ', '
MSG_NOTHING_STAYS = 'none'
MSG_NOTHING_MOVES = 'nothing'
MSG_ADD_NOTE = 'add {note}'
MSG_LIFT_NOTE = 'lift {note}'
