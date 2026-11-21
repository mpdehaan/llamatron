# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""What a progression's chords are in a scale, with no tracker needed: each chord's quality, Roman numeral and name, and the named progressions matched to a scale.

A chord on a plain degree is the triad the scale builds there,
so the scale decides whether it's major or minor; a chord with a sharp or a flat keeps the sound
of the figure written on degree 1, moved by exact half steps. The named progressions are written
against a major key, and are matched to a scale when picked: a chord whose root is a note of the
scale becomes that plain degree, any other the degree a half step above it with a flat, or below
it with a sharp, and plain degrees then follow later edits of the scale, as a pattern's do.
"""

from llamatron.composition import file_format
from llamatron.composition.file_format import Accidental, NamedProgression, Quality
from llamatron.music.scale import ScaleType
from llamatron.strings import marks

HALF_STEPS_PER_OCTAVE = 12
# The half steps without a scale: the major scale's, as a song with no scale places degrees.
SHAPE_WITHOUT_A_SCALE = ScaleType.MAJOR.value


# Each triad's third and fifth above its root, and the quality they make.
QUALITIES = {(4, 7): Quality.MAJOR, (3, 7): Quality.MINOR, (3, 6): Quality.DIMINISHED, (4, 8): Quality.AUGMENTED}
# A chord the scale can't build as a triad, like one of a pentatonic's, reads as major.
OTHER_QUALITY = Quality.MAJOR
UPPER_CASE_QUALITIES = (Quality.MAJOR, Quality.AUGMENTED)
ROMAN_NUMERALS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']


def shape_of(scale):
    """Return a scale's half steps from its root, or the major scale's when there's none."""
    return SHAPE_WITHOUT_A_SCALE if scale is None else scale.get_half_steps()


def half_steps_to(*, scale, degree, accidental=None):
    """Return how many half steps a chord's root is above the scale's root: its degree's, and one more for a sharp or one less for a flat."""
    shape = shape_of(scale)
    octaves, place = divmod(degree - 1, len(shape))
    return octaves * HALF_STEPS_PER_OCTAVE + shape[place] + file_format.ACCIDENTALS.get(accidental, 0)


def quality_of(*, scale, degree, accidental=None):
    """Return a chord's quality: the scale's triad on a plain degree, the figure's own, on degree 1, for one with a sharp or flat."""
    shape = shape_of(scale)
    place = 0 if accidental else (degree - 1) % len(shape)
    root = shape[place]
    third = (shape[(place + 2) % len(shape)] - root) % HALF_STEPS_PER_OCTAVE
    fifth = (shape[(place + 4) % len(shape)] - root) % HALF_STEPS_PER_OCTAVE
    return QUALITIES.get((third, fifth), OTHER_QUALITY)


def roman_numeral(*, scale, degree, accidental=None):
    """Return a chord's Roman numeral: upper case major, lower case minor, a mark for diminished or augmented, a sharp or flat in front."""
    quality = quality_of(scale=scale, degree=degree, accidental=accidental)
    numeral = ROMAN_NUMERALS[(degree - 1) % len(ROMAN_NUMERALS)]
    numeral = numeral if quality in UPPER_CASE_QUALITIES else numeral.lower()
    return marks.MSG_ACCIDENTAL_MARKS.get(accidental, '') + numeral + marks.MSG_QUALITY_MARKS[quality]


def matched_to(*, scale, chords):
    """Return a named progression's chords, each (half steps above the key's root), as (degrees, accidentals) in a scale.

    A chord on a note of the scale is that plain degree; any other is the degree a half step
    above it with a flat, or, past the scale's last note, the one below it with a sharp.
    """
    shape = list(shape_of(scale))
    degrees = []
    accidentals = []
    for half_steps in chords:
        within = half_steps % HALF_STEPS_PER_OCTAVE
        if within in shape:
            degrees.append(shape.index(within) + 1)
            accidentals.append(None)
        elif within + 1 in shape:
            degrees.append(shape.index(within + 1) + 1)
            accidentals.append(Accidental.FLAT)
        else:
            degrees.append(max(index for index, step in enumerate(shape) if step < within) + 1)
            accidentals.append(Accidental.SHARP)
    return degrees, accidentals


# The named progressions, in the picker's two columns, each written in Roman numerals against a
# major key, a flat in front as b: upper case major, lower case minor.
NAMED_PROGRESSIONS = [
    [
        (NamedProgression.POP, 'I V vi IV'),
        (NamedProgression.FIFTIES, 'I vi IV V'),
        (NamedProgression.SAD_POP, 'vi IV I V'),
        (NamedProgression.EPIC, 'vi IV I V'),
        (NamedProgression.HOPEFUL, 'I IV vi V'),
        (NamedProgression.ROCK, 'I bVII IV'),
        (NamedProgression.MIXOLYDIAN_ROCK, 'I bVII IV I'),
        (NamedProgression.POWER_BALLAD, 'I V vi iii IV'),
        (NamedProgression.GRUNGE, 'i bVI bIII bVII'),
        (NamedProgression.PUNK, 'I IV V'),
        (NamedProgression.ROYAL_ROAD, 'IV V iii vi'),
        (NamedProgression.HIP_HOP_LOOP, 'i bVI'),
    ],
    [
        (NamedProgression.TWELVE_BAR_BLUES, 'I I I I IV IV I I V IV I V'),
        (NamedProgression.QUICK_CHANGE_BLUES, 'I IV I I IV IV I I V IV I V'),
        (NamedProgression.EIGHT_BAR_BLUES, 'I V IV IV I V I V'),
        (NamedProgression.JAZZ_TURNAROUND, 'ii V I'),
        (NamedProgression.LONG_TURNAROUND, 'I vi ii V'),
        (NamedProgression.CIRCLE_OF_FIFTHS, 'vi ii V I'),
        (NamedProgression.RHYTHM_CHANGES, 'I vi ii V I vi ii V'),
        (NamedProgression.FOLK, 'I IV V I'),
        (NamedProgression.GOSPEL, 'I IV I V'),
        (NamedProgression.PACHELBEL, 'I V vi iii IV I IV V'),
        (NamedProgression.ANDALUSIAN, 'i bVII bVI V'),
        (NamedProgression.MINOR, 'i iv v i'),
    ],
]
FLAT_WRITTEN = 'b'
SHARP_WRITTEN = '#'


def numeral_half_steps(numeral):
    """Return how many half steps a numeral of a named progression, like bVII, is above the key's root."""
    shift = 0
    if numeral.startswith(FLAT_WRITTEN):
        shift = file_format.ACCIDENTALS[Accidental.FLAT]
        numeral = numeral[len(FLAT_WRITTEN):]
    elif numeral.startswith(SHARP_WRITTEN):
        shift = file_format.ACCIDENTALS[Accidental.SHARP]
        numeral = numeral[len(SHARP_WRITTEN):]
    return SHAPE_WITHOUT_A_SCALE[ROMAN_NUMERALS.index(numeral.upper())] + shift


def named_progression(key):
    """Return a named progression's numerals, as written."""
    return next(written for column in NAMED_PROGRESSIONS for name, written in column if name == key).split()


def named_progression_in(*, key, scale):
    """Return a named progression as (degrees, accidentals) in a scale."""
    return matched_to(scale=scale, chords=[numeral_half_steps(numeral) for numeral in named_progression(key)])


def shown_numerals(key):
    """Return a named progression's numerals as the picker shows them, with flat signs."""
    return marks.MSG_PRESET_NUMERALS_SEPARATOR.join(marks.MSG_ACCIDENTAL_MARKS[Accidental.FLAT] + numeral[len(FLAT_WRITTEN):] if numeral.startswith(FLAT_WRITTEN) else numeral for numeral in named_progression(key))
