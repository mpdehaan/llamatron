# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The words the Guitarify generator plugin shows: what it is called beside a generator's name, the word its page's caption names it by, the word a generator named for
its kind takes, as in kick guitar, its Mode's words, its columns' headings, how some of its numbers show, and its page's help."""

from llamatron.user_strings import labels

MSG_LABEL = 'Guitarify'
MSG_KIND_WORD = 'guitar'
MSG_CAPTION_WORD = 'guitarify'
# What an undo or a redo of a change to one of its generators names the generator's kind.
MSG_CHANGED_WORD = 'Guitarify'
# The heading the Generators page offers it under.
MSG_GROUP = labels.GeneratorGroup.VOICING

MSG_MODE_LABEL = 'Mode'
MSG_GUITAR_MODE = 'Guitar'
MSG_STRUM_MODE = 'Strum'
MSG_DIRECTION_LABEL = 'Direction'
MSG_BY_THE_BEAT = 'by the beat'
MSG_DOWN = 'down'
MSG_UP = 'up'
MSG_DOWN_UP = 'down up'
# The headings of its columns: the fretting hand and the striking hand in Guitar mode, the strum in Strum mode.
MSG_LEFT_HAND_HEADING = 'Left Hand'
MSG_RIGHT_HAND_HEADING = 'Right Hand'
MSG_STRUM_HEADING = 'Strum'
# How its position and capo, its spread and its upstroke strings show.
MSG_OPEN_POSITION = 'open'
MSG_NO_CAPO = '(none)'
MSG_FRET = 'fret {number}'
MSG_MILLISECONDS = '{number} ms'
MSG_EVERY_STRING = 'all'

# Its page's help.
HELP_PAGE = """
Mode: Guitar plays a clip's chords and notes as a guitar does; Strum plays them as written and strums each chord at the very end.
Strum mode: Direction, by the beat, down, up or down up, and the Spread, Fade, Loose timing and Upstroke strings below.
Guitar mode, Left Hand: a chord is held as a hand holds it, one note a string, in the tuning, within four frets of the position,
above the capo. Single notes: leave, power chord or scale chord. Right Hand: the bar of strokes is played on whatever sounds;
ENTER on Bar edits it. Let ring: a string sounds until struck again. Each hand can be switched off.
Spread, Fade and Loose timing: the time between a strum's strings, how much quieter each is, and how uneven the gaps are.
"""
