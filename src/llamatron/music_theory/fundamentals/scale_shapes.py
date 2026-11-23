# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Scale shapes: each scale as one octave of half steps above its root.

A scale is a choice of pitches from the twelve of the octave, always starting on its root, 0. Its shape is the same in every
key: C major and A-flat major are both (0, 2, 4, 5, 7, 9, 11), steps of whole, whole, half, whole, whole, whole and half. Most
scales here have seven notes, one for each letter name; the pentatonic scales have five, the blues scales six, and the
symmetric scales repeat a small pattern, so that the whole-tone scale is whole steps all the way round. A mode is the same
notes started from another of them: dorian is major's notes from its second, which is why the modes are listed with major.
"""

# Major and its modes. IONIAN is another name for MAJOR, and AEOLIAN and
# NATURAL_MINOR are other names for MINOR.
MAJOR = (0, 2, 4, 5, 7, 9, 11)
IONIAN = MAJOR
DORIAN = (0, 2, 3, 5, 7, 9, 10)
PHRYGIAN = (0, 1, 3, 5, 7, 8, 10)
LYDIAN = (0, 2, 4, 6, 7, 9, 11)
MIXOLYDIAN = (0, 2, 4, 5, 7, 9, 10)
MINOR = (0, 2, 3, 5, 7, 8, 10)
AEOLIAN = MINOR
NATURAL_MINOR = MINOR
LOCRIAN = (0, 1, 3, 5, 6, 8, 10)

# Other major and minor scales. MELODIC_MINOR is the ascending form.
HARMONIC_MINOR = (0, 2, 3, 5, 7, 8, 11)
MELODIC_MINOR = (0, 2, 3, 5, 7, 9, 11)
HARMONIC_MAJOR = (0, 2, 4, 5, 7, 8, 11)

# Pentatonic and blues
MAJOR_PENTATONIC = (0, 2, 4, 7, 9)
MINOR_PENTATONIC = (0, 3, 5, 7, 10)
BLUES = (0, 3, 5, 6, 7, 10)
MAJOR_BLUES = (0, 2, 3, 4, 7, 9)

# Symmetric scales
CHROMATIC = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
WHOLE_TONE = (0, 2, 4, 6, 8, 10)
WHOLE_HALF_DIMINISHED = (0, 2, 3, 5, 6, 8, 9, 11)
HALF_WHOLE_DIMINISHED = (0, 1, 3, 4, 6, 7, 9, 10)
AUGMENTED = (0, 3, 4, 7, 8, 11)

# The modes of melodic minor, after melodic minor itself. Flat and natural are spelled
# out, so DORIAN_FLAT2 is dorian b2.
DORIAN_FLAT2 = (0, 1, 3, 5, 7, 9, 10)
LYDIAN_AUGMENTED = (0, 2, 4, 6, 8, 9, 11)
LYDIAN_DOMINANT = (0, 2, 4, 6, 7, 9, 10)
MIXOLYDIAN_FLAT6 = (0, 2, 4, 5, 7, 8, 10)
LOCRIAN_NATURAL2 = (0, 2, 3, 5, 6, 8, 10)
ALTERED = (0, 1, 3, 4, 6, 8, 10)

# Jazz
BEBOP_DOMINANT = (0, 2, 4, 5, 7, 9, 10, 11)
BEBOP_MAJOR = (0, 2, 4, 5, 7, 8, 9, 11)
PROMETHEUS = (0, 2, 4, 6, 9, 10)

# The Middle East and Europe
PHRYGIAN_DOMINANT = (0, 1, 4, 5, 7, 8, 10)
DOUBLE_HARMONIC = (0, 1, 4, 5, 7, 8, 11)
HUNGARIAN_MINOR = (0, 2, 3, 6, 7, 8, 11)
HUNGARIAN_MAJOR = (0, 3, 4, 6, 7, 9, 10)
UKRAINIAN_DORIAN = (0, 2, 3, 6, 7, 9, 10)
PERSIAN = (0, 1, 4, 5, 6, 8, 11)
NEAPOLITAN_MINOR = (0, 1, 3, 5, 7, 8, 11)
NEAPOLITAN_MAJOR = (0, 1, 3, 5, 7, 9, 11)
ENIGMATIC = (0, 1, 4, 6, 8, 10, 11)

# Egypt and East Asia. RYUKYU is the Okinawan scale.
EGYPTIAN = (0, 2, 5, 7, 10)
HIRAJOSHI = (0, 2, 3, 7, 8)
IN_SEN = (0, 1, 5, 7, 10)
IWATO = (0, 1, 5, 6, 10)
KUMOI = (0, 2, 3, 7, 9)
YO = (0, 2, 5, 7, 9)
RYUKYU = (0, 4, 5, 7, 11)

# Indian ragas, in twelve notes to the octave
TODI = (0, 1, 3, 6, 7, 8, 11)
MARWA = (0, 1, 4, 6, 7, 9, 11)
PURVI = (0, 1, 4, 6, 7, 8, 11)
