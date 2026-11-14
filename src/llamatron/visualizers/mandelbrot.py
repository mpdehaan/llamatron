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
"""Mandelbrot, a visualizer mode: the Mandelbrot set, turning slowly about a point on its edge and zooming gently in and out, its colours changing with the tracks that play, the user's design of 2026-11-10.

Each fine pixel is a point of the plane, seen through a view that turns slowly and breathes between
the whole set and a close look at the seahorse valley on its edge; the point is iterated until it
escapes or MOST_ITERATIONS pass, only the points still in the running being worked on each round,
and its escape, smoothed, picks a colour from a palette going round the hues of the tracks heard,
vivid like the plasma's, which drifts round with time and turns a little with each note. The set
itself is dark. It is worked out at SUPERSAMPLE times the big pixels each way and averaged down,
and held under the limiter. The amounts are named constants here, for the user to tune by eye.
"""

import math

import numpy

from llamatron.visualizers.colour import Limiter, TRACK_COLOURS, note_colour
from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.lava_lamp import derezzed
from llamatron.visualizers.plasma import PALETTE_SIZE, palette_of
from llamatron.visualizers.visualizer import Visualizer
from llamatron.strings.visualizers import MSG_MANDELBROT

SUPERSAMPLE = 2
COLOUR_STEP_SHIFT = 3
LONGEST_FRAME_SECONDS = 0.2
FULL_VELOCITY = 127
# The view: the point it turns about, how fast it turns, in radians a second at 120 a minute, and how it breathes between seeing the whole set and a close look, as the plane's height across the area, over this many seconds.
FOCUS = complex(-0.7453, 0.1127)
TURN_SPEED = 0.06
WIDEST = 2.6
CLOSEST = 0.02
BREATH_SECONDS = 60.0
# How far the points are iterated, and past what size one has escaped.
MOST_ITERATIONS = 56
ESCAPE = 4.0
# The colours: how many times the palette goes round across the escapes, how fast it drifts round, in turns a second, how much a note turns it, and how bright at rest and playing.
PALETTE_REPEATS = 3.0
DRIFT_PER_SECOND = 0.03
TURN_PER_NOTE = 0.015
RESTING_BRIGHTNESS = 0.6
PLAYING_BRIGHTNESS = 1.0
ENERGY_PER_NOTE = 0.3
ENERGY_RISE_PER_SECOND = 1.5
ENERGY_KEPT_PER_SECOND = 0.35
QUIET_COLOURS = (TRACK_COLOURS[1], TRACK_COLOURS[4], TRACK_COLOURS[0], TRACK_COLOURS[2])
# The limiter.
MEAN_LEVEL = 110.0
CEILING = 235
MEAN_RISE_PER_SECOND = 45.0
MEAN_FALL_PER_SECOND = 45.0
MOST_GAIN = 1.3
LOG_TWO = math.log(2.0)


class Mandelbrot(Visualizer):
    """The Mandelbrot set, turning and breathing, coloured by the tracks."""

    __slots__ = ('_rows', '_columns', '_offsets', '_time', '_phase', '_energy', '_target', '_colours', '_palette', '_last', '_limiter')

    NAME = MSG_MANDELBROT
    OPTION = 'mandelbrot'
    DARK_IN_SILENCE = False

    def __init__(self):
        super().__init__()
        self._time = 0.0
        self._phase = 0.0
        self._energy = 0.0
        self._target = 0.0
        self._colours = {}
        self._palette = palette_of(QUIET_COLOURS)
        self._last = None
        self._limiter = Limiter(
            mean_level=MEAN_LEVEL, ceiling=CEILING, rise_per_second=MEAN_RISE_PER_SECOND, fall_per_second=MEAN_FALL_PER_SECOND, most_gain=MOST_GAIN,
        )
        self.resized(columns=0, rows=0)

    def resized(self, *, columns, rows):
        self._rows = rows * SUPERSAMPLE
        self._columns = columns * SUPERSAMPLE
        down, across = numpy.mgrid[0:max(self._rows, 1), 0:max(self._columns, 1)].astype(numpy.float64)
        # Each fine pixel's place from the middle, as a share of the area's height, pixels being square.
        self._offsets = ((across - (self._columns - 1) / 2) + 1j * (down - (self._rows - 1) / 2)) / max(self._rows, 1)

    def pixels(self, *, now, heard=SILENCE):
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        self.hear(heard)
        rise = ENERGY_RISE_PER_SECOND * seconds
        self._energy += max(-rise, min(rise, self._target - self._energy))
        self._target *= ENERGY_KEPT_PER_SECOND ** seconds
        self._time += seconds * heard.tempo_factor()
        self._phase += DRIFT_PER_SECOND * seconds
        breath = 0.5 - 0.5 * math.cos(math.tau * self._time / BREATH_SECONDS)
        height = math.exp(math.log(WIDEST) + (math.log(CLOSEST) - math.log(WIDEST)) * breath)
        turn = complex(math.cos(TURN_SPEED * self._time), math.sin(TURN_SPEED * self._time))
        escapes = escape_times(self._offsets * height * turn + FOCUS)
        outside = escapes >= 0
        places = ((escapes / MOST_ITERATIONS * PALETTE_REPEATS + self._phase) % 1.0 * (PALETTE_SIZE - 1)).astype(numpy.intp)
        brightness = RESTING_BRIGHTNESS + (PLAYING_BRIGHTNESS - RESTING_BRIGHTNESS) * self._energy
        picture = numpy.where(outside[:, :, None], self._palette[places] * brightness, 0).astype(numpy.int32)
        small = derezzed(fine=picture, factor=SUPERSAMPLE)
        held = self._limiter.limited(picture=small, seconds=seconds)
        return (held >> COLOUR_STEP_SHIFT) << COLOUR_STEP_SHIFT

    def hear(self, heard):
        """Let each note heard bring its track's colour into the palette, and each that starts turn the palette a little and raise the energy."""
        changed = False
        for note in heard.notes:
            colour = tuple(int(channel) for channel in note_colour(track=note.track, pitch=note.pitch, drum=note.drum))
            if self._colours.get(note.track) != colour:
                self._colours[note.track] = colour
                changed = True
            if note.started:
                self._phase += TURN_PER_NOTE * note.velocity / FULL_VELOCITY
                self._target = min(self._target + ENERGY_PER_NOTE * note.velocity / FULL_VELOCITY, 1.0)
        if changed:
            colours = [self._colours[track] for track in sorted(self._colours)]
            self._palette = palette_of(colours if len(colours) > 1 else colours + list(QUIET_COLOURS[:2]))


def escape_times(points):
    """Return how many rounds each point of the plane takes to escape, smoothed, or -1 for a point that stays within MOST_ITERATIONS, working only on the points still in the running."""
    escapes = numpy.full(points.shape, -1.0)
    flat_points = points.ravel()
    flat_escapes = escapes.ravel()
    running = numpy.arange(flat_points.size)
    values = numpy.zeros(flat_points.size, dtype=numpy.complex128)
    starts = flat_points.copy()
    for round_number in range(MOST_ITERATIONS):
        values = values * values + starts
        sizes = values.real * values.real + values.imag * values.imag
        escaped = sizes > ESCAPE
        if escaped.any():
            smooth = round_number + 1 - numpy.log(numpy.log(numpy.sqrt(sizes[escaped]))) / LOG_TWO
            flat_escapes[running[escaped]] = numpy.maximum(smooth, 0.0)
            keep = ~escaped
            running, values, starts = running[keep], values[keep], starts[keep]
            if not running.size:
                break
    return escapes
