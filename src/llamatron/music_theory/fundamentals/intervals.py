# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Intervals: the distances between pitches, counted in half steps.

The octave is the interval at which a pitch comes round to the same note name, twice the frequency: C to the next C. Western
music divides it into twelve equal half steps, which MIDI numbers one apart, so that a note an octave up is twelve higher and
every pitch class, the note with its octave set aside, is its number modulo twelve.
"""

# The half steps in an octave, which every count of notes round the octave, every pitch class and every MIDI octave rests on.
HALF_STEPS_PER_OCTAVE = 12
