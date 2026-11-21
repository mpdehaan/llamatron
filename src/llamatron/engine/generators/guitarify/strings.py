# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The words the Guitarify generator plugin shows: what it is called beside a generator's name, the word its page's caption names it by, and the word a generator named for
its kind takes, as in kick guitar."""

from llamatron.user_strings import labels

MSG_LABEL = 'Guitarify'
MSG_KIND_WORD = 'guitar'
MSG_CAPTION_WORD = 'guitarify'
# What an undo or a redo of a change to one of its generators names the generator's kind.
MSG_CHANGED_WORD = 'Guitarify'
# The heading the Generators page offers it under.
MSG_GROUP = labels.GeneratorGroup.VOICING
