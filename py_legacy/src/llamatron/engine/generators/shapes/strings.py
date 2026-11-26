# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The words the Shapes generator plugin shows: what it is called beside a generator's name, the word its page's caption names it
by, the word a generator named for its kind takes, as in kick shapes, and its page's help."""


MSG_LABEL = 'Shapes'
MSG_KIND_WORD = 'shapes'
MSG_CAPTION_WORD = 'shapes'
# What an undo or a redo of a change to one of its generators names the generator's kind.
MSG_CHANGED_WORD = 'Shapes'
# The heading the Generators page offers it under.
# The label of a Swell's accent on its page.
MSG_SWELL_ACCENT_LABEL = 'Swell accent'

# Its page's help.
HELP_PAGE = """
Shapes a section over time: Density, how many notes play; Swell, how loud; Articulate, how long each sounds.
Each runs from its Start to its End, in percent, over its Over, then holds, repeats or bounces back by Then.
A shape whose Start and End are both blank does nothing. Swell accent makes the strong beats louder.
"""
