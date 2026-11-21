# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The words the Articulate generator plugin shows: what it is called beside a generator's name, the word its page's caption names it by, and the word a generator named for
its kind takes, as in kick articulation."""

from llamatron.model.schema.file_format import Shape
from llamatron.user_strings import labels

MSG_LABEL = labels.MSG_SHAPE_NAMES[Shape.ARTICULATE]
MSG_KIND_WORD = 'articulation'
MSG_CAPTION_WORD = 'articulate'
# What an undo or a redo of a change to one of its generators names the generator's kind.
MSG_CHANGED_WORD = 'Articulate'
# The heading the Generators page offers it under.
MSG_GROUP = labels.GeneratorGroup.TRANSITIONS
