# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The words the Timing generator plugin shows: what it is called beside a generator's name, the word its page's caption names it
by, the word a generator named for its kind takes, as in hat timing, each part's words, and its page's help."""

from llamatron.user_strings import labels

MSG_LABEL = 'Timing'
MSG_KIND_WORD = 'timing'
MSG_CAPTION_WORD = 'timing'
# What an undo or a redo of a change to one of its generators names the generator's kind.
MSG_CHANGED_WORD = 'Timing'
# The heading the Generators page offers it under.
MSG_GROUP = labels.GeneratorGroup.TIMING

# Each part's name, which heads its section on the page and names its row on its steps page.
MSG_RUSH = 'Rush'
MSG_DRAG = 'Drag'
MSG_SHORTEN = 'Shorten'
MSG_GLIDE = 'Glide'
# What a lit step of each part does, the line above its row of steps.
MSG_RUSH_NOTE = 'a note starting on a step that is on plays early'
MSG_DRAG_NOTE = 'a note starting on a step that is on plays late'
MSG_SHORTEN_NOTE = 'a note starting on a step that is on plays short'
MSG_GLIDE_NOTE = 'a note starting on a step that is on glides into the next note'
MSG_STEP_LABEL = '{part} step'
MSG_AMOUNT_LABEL = '{part} amount'
MSG_STEPS_LABEL = '{part} steps'

# Its page's help.
HELP_PAGE = """
Rush plays notes early and Drag plays them late, by a share of a step; Shorten plays them short; Glide runs them into the next.
Each is a row of steps from each clip's start, at its own Step, the pattern's step size unless set; a note starting on a
step that is on is changed. ENTER on Steps opens the row. A part with no step on does nothing.
"""
