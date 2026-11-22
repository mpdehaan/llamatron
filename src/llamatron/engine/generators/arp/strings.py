# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The words the arpeggiator generator plugin shows: what it is called beside a generator's name, the word its page's caption names it by, the word a generator named for
its kind takes, as in kick arp, its columns' headings, and its page's help."""

from llamatron.user_strings import labels

MSG_LABEL = 'Arpeggiator'
MSG_KIND_WORD = 'arp'
MSG_CAPTION_WORD = 'arpeggiator'
# What an undo or a redo of a change to one of its generators names the generator's kind.
MSG_CHANGED_WORD = 'arp'
# The heading the Generators page offers it under.
MSG_GROUP = labels.GeneratorGroup.VOICING

# The headings of its columns.
MSG_NOTES_HEADING = 'Notes'
MSG_REGISTERS_HEADING = 'Registers'

# Its page's help.
HELP_PAGE = """
Step: how long each note of the chord plays, the pattern's step size unless set.
Order: which way it goes through the chord. Random uses the seed.
Octave range: plays the chord again in up to 4 octaves. Octave jump: up after the whole chord, or after each note.
Offsets: the arp's own steps, like a groovebox's. Each moves its note along the scale, and a blank step is silent.
ENTER on Offsets opens them, and Bksp removes them. Each register's field: what every note adds to it.
"""

# The name of the tab of the built-in one every clip and track holds.
MSG_TAB_LABEL = 'Arp'
