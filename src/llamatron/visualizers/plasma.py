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
"""Plasma, a visualizer mode after the demo scene's: smooth fields of sine waves drifting in colour, coloured by the tracks that play, the user's choice of 2026-11-10.

The classic plasma adds four sine waves over the area, one across, one down, one on the diagonal
and one in rings about a point that wanders, each moving with time, and turns the sum into a colour
through a palette. Here the palette is made from the colours of the tracks playing, blended round a
cycle, so the plasma takes the song's colours; time runs faster for a faster song and swells a
little as the tracks play; each note starting nudges the waves' frequencies, and the brightness
rises gently with the playing. It is worked out at SUPERSAMPLE times the big pixels each way and
averaged down, and held under the limiter so that it never flashes. In silence it glows dimly in
the colours of the tracks heard last. The amounts are named constants here, for the user to tune.
"""

import colorsys
import math

import numpy

from llamatron.visualizers.colour import TRACK_COLOURS, Limiter, note_colour
from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.lava_lamp import derezzed
from llamatron.visualizers.visualizer import Visualizer
from llamatron.strings.visualizers import MSG_PLASMA

SUPERSAMPLE = 2
COLOUR_STEP_SHIFT = 3
LONGEST_FRAME_SECONDS = 0.2
FULL_VELOCITY = 127
# The waves: how many waves fit across the area for each, and how fast each moves, in radians a second at 120 a minute.
ACROSS_WAVES = 1.6
DOWN_WAVES = 1.2
DIAGONAL_WAVES = 1.0
RING_WAVES = 2.2
ACROSS_SPEED = 0.9
DOWN_SPEED = 0.7
DIAGONAL_SPEED = 0.5
RING_SPEED = 1.1
# How the rings' middle wanders, as a share of the area, and how fast.
WANDER = 0.3
WANDER_SPEED = 0.23
# How notes stir it: how much a note at full velocity nudges the waves' frequencies, how fast the nudge settles, how much the playing speeds time, and how bright it is at rest and playing.
NUDGE_PER_NOTE = 0.08
NUDGE_KEPT_PER_SECOND = 0.4
ENERGY_SPEED = 0.6
RESTING_BRIGHTNESS = 0.55
PLAYING_BRIGHTNESS = 1.0
ENERGY_PER_NOTE = 0.25
ENERGY_RISE_PER_SECOND = 1.5
ENERGY_KEPT_PER_SECOND = 0.35
# The palette: how many colours it has round its cycle, how saturated, and the colours it starts with before any track plays.
PALETTE_SIZE = 256
SATURATION = 1.0
WHOLE = 255
# The edges are brighter than the middle, by this share at the corners, the user's ask so that it doesn't look like the lava lamp.
EDGE_BOOST = 0.6
QUIET_COLOURS = (TRACK_COLOURS[1], TRACK_COLOURS[4], TRACK_COLOURS[5])
# The limiter: bright, as the user asked, and still never flashing.
MEAN_LEVEL = 130.0
CEILING = 235
MEAN_RISE_PER_SECOND = 40.0
MEAN_FALL_PER_SECOND = 40.0
MOST_GAIN = 1.2


def palette_of(colours):
    """Return a palette of PALETTE_SIZE colours going round the hues of the colours given and back to the first, each at full saturation and brightness, so that it stays vivid rather than passing through pastels, as an array of rows by three."""
    hues = [colorsys.rgb_to_hsv(*(channel / WHOLE for channel in colour))[0] for colour in colours]
    hues = hues + [hues[0] + 1.0]
    for place in range(1, len(hues)):
        while hues[place] < hues[place - 1]:
            hues[place] += 1.0
    places = numpy.linspace(0, len(colours), PALETTE_SIZE, endpoint=False)
    lower = numpy.floor(places).astype(int)
    share = places - lower
    hues = numpy.array(hues)
    between = (hues[lower] * (1 - share) + hues[lower + 1] * share) % 1.0
    return numpy.array([colorsys.hsv_to_rgb(hue, SATURATION, 1.0) for hue in between]) * WHOLE


class Plasma(Visualizer):
    """Sine waves drifting in the playing tracks' colours."""

    __slots__ = ('_rows', '_columns', '_grid', '_edges', '_time', '_last', '_nudge', '_energy', '_target', '_colours', '_palette', '_limiter')

    NAME = MSG_PLASMA
    OPTION = 'plasma'
    DARK_IN_SILENCE = False

    def __init__(self):
        super().__init__()
        self._time = 0.0
        self._last = None
        self._nudge = 0.0
        self._energy = 0.0
        self._target = 0.0
        self._colours = {}
        self._palette = palette_of(QUIET_COLOURS)
        self._limiter = Limiter(
            mean_level=MEAN_LEVEL, ceiling=CEILING, rise_per_second=MEAN_RISE_PER_SECOND, fall_per_second=MEAN_FALL_PER_SECOND, most_gain=MOST_GAIN,
        )
        self.resized(columns=0, rows=0)

    def resized(self, *, columns, rows):
        self._rows = rows * SUPERSAMPLE
        self._columns = columns * SUPERSAMPLE
        down, across = numpy.mgrid[0:max(self._rows, 1), 0:max(self._columns, 1)].astype(numpy.float32)
        self._grid = (down / max(self._rows, 1), across / max(self._columns, 1))
        # How much brighter each cell is for being near the edges: nothing in the middle, EDGE_BOOST at the corners.
        reach = numpy.hypot(self._grid[0] - 0.5, self._grid[1] - 0.5) / math.hypot(0.5, 0.5)
        self._edges = (1.0 + EDGE_BOOST * reach)[:, :, None]

    def pixels(self, *, now, heard=SILENCE):
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        self.hear(heard)
        rise = ENERGY_RISE_PER_SECOND * seconds
        self._energy += max(-rise, min(rise, self._target - self._energy))
        self._target *= ENERGY_KEPT_PER_SECOND ** seconds
        self._nudge *= NUDGE_KEPT_PER_SECOND ** seconds
        self._time += seconds * heard.tempo_factor() * (1.0 + ENERGY_SPEED * self._energy)
        down, across = self._grid
        stretch = 1.0 + self._nudge
        time = self._time
        middle_down = 0.5 + WANDER * math.sin(time * WANDER_SPEED)
        middle_across = 0.5 + WANDER * math.cos(time * WANDER_SPEED * 1.3)
        value = (
            numpy.sin(math.tau * ACROSS_WAVES * stretch * across + time * ACROSS_SPEED)
            + numpy.sin(math.tau * DOWN_WAVES * stretch * down + time * DOWN_SPEED)
            + numpy.sin(math.tau * DIAGONAL_WAVES * (across + down) + time * DIAGONAL_SPEED)
            + numpy.sin(math.tau * RING_WAVES * stretch * numpy.hypot(down - middle_down, (across - middle_across) * 2) - time * RING_SPEED)
        )
        places = ((value + 4) / 8 * (PALETTE_SIZE - 1)).astype(numpy.intp)
        brightness = RESTING_BRIGHTNESS + (PLAYING_BRIGHTNESS - RESTING_BRIGHTNESS) * self._energy
        picture = (self._palette[places] * brightness * self._edges).astype(numpy.int32)
        small = derezzed(fine=picture, factor=SUPERSAMPLE)
        held = self._limiter.limited(picture=small, seconds=seconds)
        return (held >> COLOUR_STEP_SHIFT) << COLOUR_STEP_SHIFT

    def hear(self, heard):
        """Let each note heard colour the palette with its track's colour, and each that starts nudge the waves and raise the energy."""
        changed = False
        for note in heard.notes:
            colour = tuple(int(channel) for channel in note_colour(track=note.track, pitch=note.pitch, drum=note.drum))
            if self._colours.get(note.track) != colour:
                self._colours[note.track] = colour
                changed = True
            if note.started:
                loudness = note.velocity / FULL_VELOCITY
                self._nudge += NUDGE_PER_NOTE * loudness
                self._target = min(self._target + ENERGY_PER_NOTE * loudness, 1.0)
        if changed:
            colours = [self._colours[track] for track in sorted(self._colours)]
            self._palette = palette_of(colours if len(colours) > 1 else colours + list(QUIET_COLOURS[:1]))
