# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The words the Musician generator plugin shows: what it is called beside a generator's name, the word its page's caption names it by, and the word a generator named for
its kind takes, as in kick player."""

from llamatron.user_strings import labels

MSG_LABEL = 'Musician'
MSG_KIND_WORD = 'player'
MSG_CAPTION_WORD = 'musician'
# What an undo or a redo of a change to one of its generators names the generator's kind.
MSG_CHANGED_WORD = 'Musician'
# The heading the Generators page offers it under.
MSG_GROUP = labels.GeneratorGroup.BAND
