# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The colours every page of a PDF shares: one for each degree of the scale, so that a note, a key on a keyboard and a chord
built on a degree wear the same colour wherever they are drawn, a grey for a note outside the scale, and the inks of text.

No degree is yellow, which prints faintly and reads badly on a light page.
"""

from reportlab.lib import colors

from llamatron.model.values import note as note_values
from llamatron.music_theory.fundamentals import intervals

DEGREE_COLORS = (
    colors.HexColor('#E5484D'), colors.HexColor('#F76B15'), colors.HexColor('#12A594'), colors.HexColor('#30A46C'),
    colors.HexColor('#0090FF'), colors.HexColor('#8E4EC6'), colors.HexColor('#D6409F'),
)
OUTSIDE_THE_SCALE = colors.HexColor('#8B8D98')
INK = colors.HexColor('#1A1A1A')
MUTED = colors.HexColor('#6B6B6B')
WHITE = colors.white
# A tint is a colour moved this far toward white, for the fills behind text.
LIGHT_TINT = 0.75


def degree_of(*, pitch_class, scale):
    """Return the degree of a scale a pitch class is, counted from 0 for the root, or None for a note outside it or no scale."""
    if scale is None:
        return None
    above = (pitch_class - note_values.SEMITONES_ABOVE_C[scale.get_root()]) % intervals.HALF_STEPS_PER_OCTAVE
    shape = scale.get_half_steps()
    if above not in shape:
        return None
    return shape.index(above)


def color_of(*, pitch_class, scale):
    """Return the colour a pitch class is drawn in: its degree's, or the grey of a note outside the scale."""
    degree = degree_of(pitch_class=pitch_class, scale=scale)
    if degree is None:
        return OUTSIDE_THE_SCALE
    return DEGREE_COLORS[degree % len(DEGREE_COLORS)]


def tint(*, color, amount):
    """Return a colour blended toward white, 0 leaving it as it is and 1 making it white."""
    return colors.Color(color.red + (1 - color.red) * amount, color.green + (1 - color.green) * amount, color.blue + (1 - color.blue) * amount)
