# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Phrasing plugin's schema: the choices its settings may hold, which its model checks and its editor offers."""

# How long the breath after a line is.
NO_BREATH = 'none'
QUICK_BREATH = 'quick'
DEEP_BREATH = 'deep'
BREATHS = (NO_BREATH, QUICK_BREATH, DEEP_BREATH)
# How far a line's loudness rises to its main note and falls away.
NO_RISE = 'none'
LITTLE_RISE = 'a little'
BIG_RISE = 'a lot'
RISES = (NO_RISE, LITTLE_RISE, BIG_RISE)
# How the notes inside a line are joined.
CHOPPY_NOTES = 'choppy'
NOTES_AS_WRITTEN = 'as written'
FLOWING_NOTES = 'flowing'
JOINS = (CHOPPY_NOTES, NOTES_AS_WRITTEN, FLOWING_NOTES)
