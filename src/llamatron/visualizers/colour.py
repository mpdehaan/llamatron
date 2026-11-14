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
"""Colour for the visualizer's modes: each track's colour, moved by a note's pitch and octave, and the limiter that keeps a picture from ever flashing.

The colours are primaries and their neighbours, saturated but never full, so that blobs read apart
and mix into clean secondaries rather than mud. A note's pitch leans its track's colour toward the
next in the cycle a little, and its octave sets how bright it is. The limiter holds the picture's
mean brightness under a level, changing its gain only slowly, and caps every channel below white,
the user's rule that the visualizer never strobes or flashes brightly (.claude/UX.md, "Drawing").
"""

import numpy

# The tracks' colours, in the order tracks take them, going round after the last.
TRACK_COLOURS = (
    (226, 42, 48), (36, 96, 232), (246, 196, 36), (36, 186, 92), (186, 56, 216), (36, 196, 206), (240, 118, 30), (118, 80, 236),
)
# A drum's hits are pale rather than coloured.
DRUM_COLOUR = (200, 200, 210)
# How far a note's pitch leans its track's colour toward the next, at most, as a share of the way.
PITCH_LEAN = 0.35
# How a note's octave sets its brightness: the dimmest share at the lowest octave, rising to the brightest at the highest.
DIMMEST = 0.55
BRIGHTEST = 1.15
LOWEST_PITCH = 24
HIGHEST_PITCH = 96
HALF_STEPS = 12


def track_colour(track):
    return TRACK_COLOURS[track % len(TRACK_COLOURS)]


def note_colour(*, track, pitch, drum):
    """Return the colour a note paints, as red, green and blue from 0 to 255: its track's, leaning toward the next by its pitch in the octave, brighter for a higher octave."""
    if drum:
        return numpy.array(DRUM_COLOUR, dtype=numpy.int32)
    base = numpy.array(track_colour(track), dtype=numpy.float32)
    lean = numpy.array(track_colour(track + 1), dtype=numpy.float32)
    mixed = base + (lean - base) * PITCH_LEAN * (pitch % HALF_STEPS) / HALF_STEPS
    height = min(max((pitch - LOWEST_PITCH) / (HIGHEST_PITCH - LOWEST_PITCH), 0.0), 1.0)
    return (mixed * (DIMMEST + (BRIGHTEST - DIMMEST) * height)).astype(numpy.int32)


# How bright a colour vivid makes is, at least, as luminance from 0 to 255, so that the dark hues, blue, red and purple, read on a phone or a tablet.
LEAST_LUMINANCE = 130.0
FULL = 255.0
# The luminance of red, green and blue, by Rec. 709.
LUMINANCE_WEIGHTS = (0.2126, 0.7152, 0.0722)


def luminance(colour):
    """Return how bright a colour looks, from 0 to 255."""
    return float(sum(weight * channel for weight, channel in zip(LUMINANCE_WEIGHTS, colour)))


def vivid(colour, *, least=LEAST_LUMINANCE):
    """Return a colour at its full value, its hue kept, with just enough white mixed in to look at least as bright as least, as floats from 0 to 255.

    The user found several modes too dim to read on an iPad or iPhone, where a saturated blue or
    red at full value still looks dark; this lifts such a colour the least that reads, rather than
    turning every colour pale.
    """
    channels = numpy.array(colour, dtype=numpy.float64)
    top = channels.max()
    if top <= 0:
        return numpy.full(3, least)
    channels = channels * (FULL / top)
    bright = luminance(channels)
    if bright < least:
        share = (least - bright) / (FULL - bright)
        channels = channels + (FULL - channels) * share
    return channels


class Limiter:
    """Holds a picture's mean brightness under a level, lets it rise and fall only so fast, and caps every channel under a ceiling, so that nothing ever flashes or strobes.

    However suddenly the picture underneath brightens, as when every track hits at once, what is
    shown brightens by at most rise_per_second, and darkens by at most fall_per_second, by a gain
    on the whole picture of at most most_gain.
    """

    __slots__ = ('_shown', '_mean_level', '_ceiling', '_rise_per_second', '_fall_per_second', '_most_gain')

    def __init__(self, *, mean_level, ceiling, rise_per_second, fall_per_second, most_gain):
        self._shown = None
        self._mean_level = mean_level
        self._ceiling = ceiling
        self._rise_per_second = rise_per_second
        self._fall_per_second = fall_per_second
        self._most_gain = most_gain

    def limited(self, *, picture, seconds):
        """Return a picture whose mean brightness is held under the level and within the rise and fall allowed over the seconds since the last, every channel under the ceiling."""
        mean = float(picture.mean())
        wanted = min(mean, self._mean_level)
        if self._shown is not None:
            wanted = max(self._shown - self._fall_per_second * seconds, min(self._shown + self._rise_per_second * seconds, wanted))
        gain = min(wanted / mean, self._most_gain) if mean > 0 else 1.0
        shown = numpy.clip((picture * gain).astype(numpy.int32), 0, self._ceiling)
        self._shown = mean * gain
        return shown
