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

# exporters/pdf/piano_roll.py
# The piano roll's pages, a section's name with how many times it plays, the counting's "and", and the strip of chord
# changes along each page's foot.
MSG_PIANO_ROLL = 'Piano Roll'
MSG_SECTION_TIMES = '{section} ×{times}'
MSG_AND = '&'
MSG_STRIP_HEADING = 'Chord changes'
MSG_STRIP_KEY = 'blue stays, red moves'

# exporters/pdf/chord_sequence.py
# The Chord Sequence page: each section's key where it changes, with what it is in the main key, and a bar that holds on.
MSG_CHORD_SEQUENCE = 'Chord Sequence'
MSG_KEY = 'Key: {key}'
MSG_KEY_IN = '{key} ({numeral} of {main})'
MSG_KEY_NAME = '{root} {kind}'
MSG_HOLDS = '·'
MSG_NO_KEY_CHANGE = ''
MSG_NO_SECTION_NAME = ''

# exporters/pdf/pdf_export.py
# The title a packet's file carries, which a PDF reader shows.
MSG_PACKET_TITLE = '{song} - learning packet'

# exporters/pdf/pdf_script.py
# The PDF export from the command line: what it says it does, its options' help, and what it says it wrote.
MSG_SCRIPT_DESCRIPTION = 'Make a song of a set into its learning packet, a PDF beside the set.'
MSG_SCRIPT_HELP_SET = 'the set file'
MSG_SCRIPT_HELP_SONG = "the song's name; the set's first song if not given"
MSG_SCRIPT_HELP_OUTPUT = "the folder the PDF goes in; the set's folder if not given"
MSG_SCRIPT_HELP_PAGES = "the packet's pages, comma-separated, from: {pages}; all of them if not given"
MSG_SCRIPT_HELP_TRACKS = 'the tracks merged and read as a lead sheet, comma-separated; every track playing pitched notes if not given'
MSG_SCRIPT_HELP_LEVEL = 'how simply the chords are printed'
MSG_SCRIPT_BAD_PAGE = 'no packet page called ({page}), expected one of: {pages}'
MSG_SCRIPT_NO_SONG = 'no song called ({song})'
MSG_SCRIPT_WROTE = 'wrote {path}'
