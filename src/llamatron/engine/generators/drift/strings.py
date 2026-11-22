# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The words the Drift generator plugin shows: what it is called beside a generator's name, the word its page's caption names it by, and the word a generator named for
its kind takes, as in kick drift, and its page's help."""

from llamatron.user_strings import labels

MSG_LABEL = 'Drift'
MSG_KIND_WORD = 'drift'
MSG_CAPTION_WORD = 'drift'
# What an undo or a redo of a change to one of its generators names the generator's kind.
MSG_CHANGED_WORD = 'drift'
# The heading the Generators page offers it under.
MSG_GROUP = labels.GeneratorGroup.TRANSITIONS

# Its page's help.
HELP_PAGE = """
Every: how often it triggers and picks new amounts. Steps to B: how many triggers it takes to reach the second version.
Direction: forward stays at the second, loop starts again at the first, pendulum goes back and forth, brownian wanders.
Below, each value has two versions side by side. Left and Right move between them, [ and ] change one, ENTER types or picks,
Bksp clears. Vel+= and Prob are added to every note's; Degree + moves notes along the scale, and Degree random by a random
amount. Scale and Root take over the clip's scale with their prob. AX+= to DX+= add to the registers at each trigger.
"""
