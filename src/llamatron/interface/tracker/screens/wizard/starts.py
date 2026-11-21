# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The four ways a run of the song wizard starts when the current song was made by the wizard."""

NEW_FROM_LAST = 'new from last'
NEW_FROM_SCRATCH = 'new from scratch'
REPLACE_FROM_LAST = 'replace from last'
REPLACE_FROM_SCRATCH = 'replace from scratch'
# In the order they are offered.
STARTS = [NEW_FROM_LAST, NEW_FROM_SCRATCH, REPLACE_FROM_LAST, REPLACE_FROM_SCRATCH]
# The starts that begin with the choices the current song kept, and the starts that replace the current song.
FROM_LAST = (NEW_FROM_LAST, REPLACE_FROM_LAST)
REPLACING = (REPLACE_FROM_LAST, REPLACE_FROM_SCRATCH)
