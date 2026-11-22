# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The words the Chords generator plugin shows: what it is called beside a generator's name, the word its page's caption names it
by, the word a generator named for its kind takes, as in bass chords, its Mode's words, its columns' headings and its page's help."""

from llamatron.user_strings import labels

MSG_LABEL = 'Chords'
MSG_KIND_WORD = 'chords'
MSG_CAPTION_WORD = 'chords'
# What an undo or a redo of a change to one of its generators names the generator's kind.
MSG_CHANGED_WORD = 'Chords'
# The heading the Generators page offers it under.
MSG_GROUP = labels.GeneratorGroup.HARMONY

MSG_MODE_LABEL = 'Mode'
MSG_VOICING_MODE = 'Voicing'
MSG_PROGRESSION_MODE = 'Progression'
MSG_FOLLOW_MODE = 'Follow Progression'
MSG_VOICE_LEADING_LABEL = 'Voice leading'
# The headings of its columns.
MSG_PROGRESSION_HEADING = 'Progression'
MSG_FOLLOW_HEADING = 'Follow'
MSG_VOICING_HEADING = 'Voicing'

# Its page's help.
HELP_PAGE = """
Mode: Voicing voices a part's chords alone; Progression moves the part through chords, each lasting Every, a bar unless set,
the part taken as written over chord I, ENTER on Chords opening the chord editor; Follow Progression moves it along the chords
the track named in Chords from plays in the same scene. Voice leading voices each chord nearest the one before, within the
octaves, the root kept in the bass if asked; it is on in Voicing mode and off in the others unless set.
"""

# The name of the tab of the built-in one every clip and track holds.
MSG_TAB_LABEL = 'Chords'
