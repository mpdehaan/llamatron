# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Chord shapes: each chord as its notes above the root, in half steps, the root itself left out.

A chord is notes sounded together, built up from a root. Stacking thirds gives the triads: a major third (4) then a minor
third gives major, (4, 7); a minor third then a major, minor, (3, 7); two minor thirds, diminished; two major, augmented. A
suspended chord puts a second or a fourth in place of the third. Another third on top makes a seventh chord, and more thirds
past the octave the ninths, elevenths and thirteenths, counted from the root as 14, 17 and 21. A power chord is root and fifth
alone, neither major nor minor.
"""


# What a chord's note is to the chord, by its half steps above the root within an octave: the root, the 3rd (a minor or a
# major 3rd) and the 5th (diminished, perfect or augmented), which a chord voiced with a note left out names; a 2nd or a 4th
# of a suspended chord, a 6th or a 7th has no such role.
ROOT = 'root'
THIRD = 'third'
FIFTH = 'fifth'
ROLES_BY_HALF_STEPS = {0: ROOT, 3: THIRD, 4: THIRD, 6: FIFTH, 7: FIFTH, 8: FIFTH}
HALF_STEPS_PER_OCTAVE = 12


def role_of(half_steps):
    """Return what a chord's note some half steps above its root is to the chord: ROOT, THIRD, FIFTH, or None."""
    return ROLES_BY_HALF_STEPS.get(half_steps % HALF_STEPS_PER_OCTAVE)


# Two notes: the power chord, and the intervals a pianist doubles a line in, the octave, the thirds, the fourth and the sixths
POWER = (7,)
OCTAVE = (12,)
MINOR_THIRD = (3,)
MAJOR_THIRD = (4,)
FOURTH = (5,)
MINOR_SIXTH = (8,)
MAJOR_SIXTH = (9,)

# Triads
MAJOR = (4, 7)
MINOR = (3, 7)
DIMINISHED = (3, 6)
AUGMENTED = (4, 8)
SUS2 = (2, 7)
SUS4 = (5, 7)

# Sixths
MAJOR6 = (4, 7, 9)
MINOR6 = (3, 7, 9)

# Sevenths
DOMINANT7 = (4, 7, 10)
MAJOR7 = (4, 7, 11)
MINOR7 = (3, 7, 10)
MINOR_MAJOR7 = (3, 7, 11)
DIMINISHED7 = (3, 6, 9)
HALF_DIMINISHED7 = (3, 6, 10)
AUGMENTED7 = (4, 8, 10)
AUGMENTED_MAJOR7 = (4, 8, 11)
DOMINANT7_SUS4 = (5, 7, 10)

# Added notes
ADD9 = (4, 7, 14)
MINOR_ADD9 = (3, 7, 14)

# Extended chords
DOMINANT9 = (4, 7, 10, 14)
MAJOR9 = (4, 7, 11, 14)
MINOR9 = (3, 7, 10, 14)
DOMINANT11 = (4, 7, 10, 14, 17)
MAJOR11 = (4, 7, 11, 14, 17)
MINOR11 = (3, 7, 10, 14, 17)
DOMINANT13 = (4, 7, 10, 14, 17, 21)
MAJOR13 = (4, 7, 11, 14, 17, 21)
MINOR13 = (3, 7, 10, 14, 17, 21)
