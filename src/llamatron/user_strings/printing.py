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
