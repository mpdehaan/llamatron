# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The words the Hocket generator plugin shows: what it is called beside a generator's name, the word its page's caption names it by, and the word a generator named for
its kind takes, as in kick hocket, and its page's help."""


MSG_LABEL = 'Hocket'
MSG_KIND_WORD = 'hocket'
MSG_CAPTION_WORD = 'hocket'
# What an undo or a redo of a change to one of its generators names the generator's kind.
MSG_CHANGED_WORD = 'Hocket'
# The heading the Generators page offers it under.

# Its page's help.
HELP_PAGE = """
Source track: the track of the current song whose notes the hocketing tracks take turns at. Renaming that track renames
it here too. A track the song lacks hands out nothing.
Restart: every clip starts the turns again with the first track at each clip the source plays; on new scene and whole
song carry them on.
Each track still plays its own pattern's notes besides those it is handed.
"""
