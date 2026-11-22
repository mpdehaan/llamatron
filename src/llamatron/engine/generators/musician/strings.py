# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The words the Musician generator plugin shows: what it is called beside a generator's name, the word its page's caption names it by, and the word a generator named for
its kind takes, as in kick player, its columns' headings, and its page's help."""


MSG_LABEL = 'Musician'
MSG_KIND_WORD = 'player'
MSG_CAPTION_WORD = 'musician'
# What an undo or a redo of a change to one of its generators names the generator's kind.
MSG_CHANGED_WORD = 'Musician'
# The heading the Generators page offers it under.

# The headings of its columns, and the caption of its table of the kinds of section.
MSG_PLAYER_HEADING = 'Player'
MSG_TOUCH_HEADING = 'Touch'
MSG_SECTIONS_CAPTION = 'Sections'

# Its page's help.
HELP_PAGE = """
Plays a clip as a player of the band would. Every note is one the clip wrote: moved, left out, held or made softer.
Chords from: the track whose chords the notes follow. Tune from: the track with the tune, which the musician plays round.
Activity: fewer of the notes, or long notes struck again. Loudness and Looseness: how loud, and how evenly.
Gives way: softer under the tune, or silent until the tune rests. Accents: the notes of the bar leaned on.
Notes: as written, each held until the next, or short. Range: an octave lower or higher, inside the instrument.
Sections: a row for each kind of section the song's scenes have: whether the musician plays there, and how.
"""
