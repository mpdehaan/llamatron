# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""llamatron's musicianship: what the program understands about music, apart from how it stores, plays or shows it.

The package is read as a book, chapter by chapter, each a subpackage whose own opening says what it holds. It grows by moving
real code up from the song wizard, the generators and the model, each move deleting the old copy, so that every piece of
musical knowledge is written once. It comes in two tiers:

- fundamentals: the facts every other part of the program needs, pitch and intervals first, as plain values and numbers that
  know nothing of llamatron's objects, so that the model and the render can use them. It sits just above math.
- the chapters above the model, which understand patterns, clips, scenes and songs, and which the generators, the song
  wizard and later features ask: added as code moves into them.

The chapters so far:

- hooks: the short figures a song is known by, its hook and its tag, written from a behavior and gauges.

What a musician decides, and the reasons a principle holds, are written in Claude's notes (.claude/music_theory_notes/); the
code says what it knows plainly, and the notes keep what is not built yet.
"""
