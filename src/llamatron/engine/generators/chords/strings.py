# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The words the Chords generator plugin shows: what it is called beside a generator's name, the word its page's caption names it
by, the word a generator named for its kind takes, as in bass chords, its Mode's words, its columns' headings and its page's help."""


MSG_LABEL = 'Chords'
MSG_KIND_WORD = 'chords'
MSG_CAPTION_WORD = 'chords'
# What an undo or a redo of a change to one of its generators names the generator's kind.
MSG_CHANGED_WORD = 'Chords'
# The heading the Generators page offers it under.

MSG_MODE_LABEL = 'Mode'
MSG_VOICING_MODE = 'Voicing'
MSG_PROGRESSION_MODE = 'Progression'
MSG_FOLLOW_MODE = 'Follow Progression'
MSG_AUTO_CHORD_MODE = 'AutoChord'
MSG_CHORD_LABEL = 'Chord'
MSG_NOTE_ON_TOP_LABEL = 'Note on top'
# AutoChord's chords, by the names auto_chord.py gives them.
MSG_CHORD_NAMES = {'from_scale': 'From scale', 'major': 'Major', 'minor': 'Minor', 'augmented': 'Augmented', 'diminished': 'Diminished', 'power': 'Power'}
MSG_VOICE_LEADING_LABEL = 'Voice leading'
# The headings of its columns.
MSG_PROGRESSION_HEADING = 'Progression'
MSG_FOLLOW_HEADING = 'Follow'
MSG_VOICING_HEADING = 'Voicing'
MSG_AUTO_CHORD_HEADING = 'AutoChord'

# Its page's help.
HELP_PAGE = """
Mode: Voicing voices a part's chords alone; Progression moves the part through chords, each lasting Every, a bar unless set,
the part taken as written over chord I, ENTER on Chords opening the chord editor; Follow Progression moves it along the chords
the track named in Chords from plays in the same scene; AutoChord turns each single note into a chord, From scale the triad
the scale builds on it, or Major, Minor, Augmented, Diminished or Power, the note on top if asked, a chord left as it is.
Voice leading voices each chord nearest the one before, within the
octaves, the root kept in the bass if asked; it is on in Voicing mode and off in the others unless set.
"""

# The name of the tab of the built-in one every clip and track holds.
MSG_TAB_LABEL = 'Chords'
