# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Composing: how a part is written down and made to play like a musician, which the song wizard asks for every part it writes.

- notation: a tune as sung lines of notes and a drum's bar as a list of hits, each note a mapping that says only what is not
  plain, turned into a pattern's rows and back, with the loudness levels and the drums a bar may name.
- loudness: a part's levels, ghost to accent, as velocities.
- shaping: velocity shaped by rhythm and a style's feel, which places in the bar it leans on.
- phrasing: a tune's line made to breathe.
- joins: how the last bar of a section hands over to the next.
"""
