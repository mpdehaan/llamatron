# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The words the Phrasing generator plugin shows: what it is called beside a generator's name, the word its page's caption names it by, and the word a generator named for
its kind takes, as in kick phrasing."""

from llamatron.user_strings import labels

MSG_LABEL = 'Phrasing'
MSG_KIND_WORD = 'phrasing'
MSG_CAPTION_WORD = 'phrasing'
# What an undo or a redo of a change to one of its generators names the generator's kind.
MSG_CHANGED_WORD = 'Phrasing'
# The heading the Generators page offers it under.
MSG_GROUP = labels.GeneratorGroup.ARTICULATION

# Its page's fields, and how a line's length in bars is shown.
MSG_LINE_LABEL = 'Line'
MSG_LINE_NAMES = {1: '1 bar', 2: '2 bars', 4: '4 bars'}
MSG_BREATH_LABEL = 'Breath'
MSG_RISE_LABEL = 'Rise and fall'
MSG_NOTES_LABEL = 'Notes'

# Its page's help.
HELP_PAGE = """
Plays a tune as a singer would deliver it, in lines. The pattern stays as written, and no note is left out.
Line: how long a line of the tune is, a sentence of it.
Breath: the silence after each line, taken from the line's last note: none, quick or deep.
Rise and fall: each line grows louder toward its main note, a long note late in the line, and falls away.
Notes: choppy, each note short with space after; as written; or flowing, each note held until the next.
"""
