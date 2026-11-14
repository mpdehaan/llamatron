# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""The theme colours, the user's design: each kind of page has a colour of its own, drawn as a stripe under the header in place of its rule, so that you can tell what kind of page you're on at a glance.

A page takes the colour of the section it shows or lists (an editor and its list share one), or
the one it names; the main screen's is white, and Arrange has none and keeps the rule.
"""

from llamatron.composition.file_format import NAMED_GENERATORS, Section

SONGS = (0, 90, 255)
PATTERNS = (0, 200, 0)
CHAINS = (150, 0, 255)
GENERATORS = (220, 0, 220)
SCALES = (0, 170, 170)
GROOVES = (255, 128, 0)
INSTRUMENTS = (230, 200, 0)
REGISTERS = (220, 0, 0)
SET_FILE = (128, 128, 128)
# The main screen's, the user's choice, white and no other page's.
MAIN_SCREEN = (255, 255, 255)
FROM_ARRANGE = (0, 200, 230)
# The colour of each section's pages, every generator section's the generators' one.
SECTION_THEMES = {
    Section.SONGS: SONGS, Section.PATTERNS: PATTERNS, Section.CHAINS: CHAINS, Section.SCALES: SCALES, Section.GROOVES: GROOVES,
    Section.INSTRUMENTS: INSTRUMENTS, Section.TRACKS: FROM_ARRANGE, **{section: GENERATORS for section in NAMED_GENERATORS.values()},
}


def target_theme(kind):
    """Return the colour of what a line of Arrange's details names, a section or a generator's kind, the user's rule that a kind of thing has one colour everywhere, or None."""
    if kind in NAMED_GENERATORS:
        return GENERATORS
    return SECTION_THEMES.get(kind)


def theme_of(section):
    """Return the colour of a section's pages, or None for a section with none."""
    return SECTION_THEMES.get(section)


# How bright a theme's edge colour is, as relative luminance from 0 to 1, the same for every theme, the user's ask that no colour look
# stronger than another, and the steps a search for it takes.
EDGE_LUMINANCE = 0.22
BALANCE_STEPS = 24
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
# The sRGB curve, which relative luminance is worked out through.
LINEAR_BELOW = 0.04045
LINEAR_SLOPE = 12.92
CURVE_OFFSET = 0.055
CURVE_SCALE = 1.055
CURVE_POWER = 2.4
CHANNEL_WEIGHTS = (0.2126, 0.7152, 0.0722)


def luminance(colour):
    """Return a colour's relative luminance, from 0 for black to 1 for white, as the eye weighs red, green and blue."""
    linear = []
    for channel in colour:
        value = channel / 255
        linear.append(value / LINEAR_SLOPE if value <= LINEAR_BELOW else ((value + CURVE_OFFSET) / CURVE_SCALE) ** CURVE_POWER)
    return sum(weight * value for weight, value in zip(CHANNEL_WEIGHTS, linear))


def mixed(*, low, high, share):
    return tuple(int(round(a + (b - a) * share)) for a, b in zip(low, high))


def balanced(colour, *, target=EDGE_LUMINANCE):
    """Return a colour of the same hue moved toward black or toward white until its luminance is the target, so that every theme's edge looks as strong as the others."""
    low, high = (BLACK, colour) if luminance(colour) >= target else (colour, WHITE)
    start, end = 0.0, 1.0
    for _ in range(BALANCE_STEPS):
        middle = (start + end) / 2
        if luminance(mixed(low=low, high=high, share=middle)) < target:
            start = middle
        else:
            end = middle
    return mixed(low=low, high=high, share=(start + end) / 2)


# How bright text in a theme's colour is, as relative luminance, so that every kind reads as strongly as the others.
TEXT_LUMINANCE = 0.3


def text_style(colour):
    """Return a Rich style naming a theme's colour toned for text, the hue kept."""
    return 'rgb({},{},{})'.format(*balanced(colour, target=TEXT_LUMINANCE))
