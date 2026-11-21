# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The scale types in categories, for the Chord dialog's flyout: each category a name and its scale
types in a logical order, the commonest borrowed from first, the modes by the degree each starts on, the melodic minor's
modes after their parent, and the rest as the Scale page's picker groups them. Common repeats six that also sit in their own
categories; every scale type is in one of the others exactly once."""

from llamatron.model.schema.file_format import ScaleKind
from llamatron.user_strings import labels

COMMON_SCALE_TYPES = [ScaleKind.MINOR, ScaleKind.MAJOR, ScaleKind.HARMONIC_MINOR, ScaleKind.MELODIC_MINOR, ScaleKind.MIXOLYDIAN, ScaleKind.DORIAN]
# The categories after Common, which between them hold every scale type once.
SORTED_SCALE_CATEGORIES = [
    (labels.MSG_SCALE_CATEGORY_MODES, [
        ScaleKind.MAJOR, ScaleKind.DORIAN, ScaleKind.PHRYGIAN, ScaleKind.LYDIAN, ScaleKind.MIXOLYDIAN, ScaleKind.MINOR, ScaleKind.LOCRIAN,
    ]),
    (labels.MSG_SCALE_CATEGORY_HARMONIC_AND_MELODIC, [
        ScaleKind.HARMONIC_MINOR, ScaleKind.HARMONIC_MAJOR, ScaleKind.MELODIC_MINOR, ScaleKind.DORIAN_FLAT2, ScaleKind.LYDIAN_AUGMENTED,
        ScaleKind.LYDIAN_DOMINANT, ScaleKind.MIXOLYDIAN_FLAT6, ScaleKind.LOCRIAN_NATURAL2, ScaleKind.ALTERED,
    ]),
    (labels.MSG_SCALE_CATEGORY_PENTATONIC_AND_BLUES, [
        ScaleKind.MAJOR_PENTATONIC, ScaleKind.MINOR_PENTATONIC, ScaleKind.BLUES, ScaleKind.MAJOR_BLUES, ScaleKind.EGYPTIAN,
    ]),
    (labels.MSG_SCALE_CATEGORY_SYMMETRIC, [
        ScaleKind.WHOLE_TONE, ScaleKind.WHOLE_HALF_DIMINISHED, ScaleKind.HALF_WHOLE_DIMINISHED, ScaleKind.AUGMENTED, ScaleKind.CHROMATIC,
    ]),
    (labels.MSG_SCALE_CATEGORY_JAZZ, [ScaleKind.BEBOP_DOMINANT, ScaleKind.BEBOP_MAJOR, ScaleKind.PROMETHEUS]),
    (labels.MSG_SCALE_CATEGORY_MIDDLE_EAST_AND_EUROPE, [
        ScaleKind.PHRYGIAN_DOMINANT, ScaleKind.DOUBLE_HARMONIC, ScaleKind.HUNGARIAN_MINOR, ScaleKind.HUNGARIAN_MAJOR, ScaleKind.UKRAINIAN_DORIAN,
        ScaleKind.PERSIAN, ScaleKind.NEAPOLITAN_MINOR, ScaleKind.NEAPOLITAN_MAJOR, ScaleKind.ENIGMATIC,
    ]),
    (labels.MSG_SCALE_CATEGORY_EAST_ASIA, [ScaleKind.HIRAJOSHI, ScaleKind.IN_SEN, ScaleKind.IWATO, ScaleKind.KUMOI, ScaleKind.YO, ScaleKind.RYUKYU]),
    (labels.MSG_SCALE_CATEGORY_INDIA, [ScaleKind.TODI, ScaleKind.MARWA, ScaleKind.PURVI]),
]
SCALE_CATEGORIES = [(labels.MSG_SCALE_CATEGORY_COMMON, COMMON_SCALE_TYPES), *SORTED_SCALE_CATEGORIES]
# Every scale type once, in the categories' order, which a Scale row steps through.
SCALE_TYPES_IN_ORDER = [kind for _, kinds in SORTED_SCALE_CATEGORIES for kind in kinds]
