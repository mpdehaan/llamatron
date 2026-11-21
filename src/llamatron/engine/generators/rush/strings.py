# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The words the Rush generator plugin shows: what it is called beside a generator's name, the word its page's caption names it by, and the word a generator named for
its kind takes, as in kick rush."""

from llamatron.user_strings import labels

MSG_LABEL = 'Rush'
MSG_KIND_WORD = 'rush'
MSG_CAPTION_WORD = 'rush'
# What an undo or a redo of a change to one of its generators names the generator's kind.
MSG_CHANGED_WORD = 'Rush'
# Its editor's row of steps: the row's name, and the line above it saying what a step that's on does.
MSG_STEP_ROW_NAME = 'Rush'
MSG_STEP_ROW_NOTE = 'a note starting on a step that is on plays early'
# The heading the Generators page offers it under.
MSG_GROUP = labels.GeneratorGroup.TIMING
