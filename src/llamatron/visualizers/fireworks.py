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
"""Fireworks, a visualizer mode: a rocket for each note, in its track's colour, bursting into sparks that fall and fade, the user's design of 2026-11-10.

A note starting launches a rocket from the bottom of the area, across at its pitch, low at the left;
the rockets burst around BURST_HEIGHT of the way up, a little higher for a louder note, into sparks,
more for a louder note, which fly out, slow, fall and fade, leaving trails, since the picture fades a
little each frame rather than clearing. The rockets take ROCKET_COLOURS in turn, seven strongly different colours, so that
each has an equal share and two bursts side by side read apart, the user's ask. A drum's note is a small pale crackle
where its rocket would burst. The sparks are numpy arrays, at most MOST_SPARKS of them, each one
fine pixel, drawn at SUPERSAMPLE times the big pixels each way and taken down by the brightest of
each block rather than the average, with no blur, so that they stay crisp points, the user's ask
after the first ones were blurry; the limiter holds the whole under its level, so that a sky full of
bursts never flashes. The amounts are named constants here, for the user to tune by eye.
"""

import math
import random

import numpy

from llamatron.visualizers.colour import Limiter
from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.visualizer import Visualizer
from llamatron.strings.visualizers import MSG_FIREWORKS

SUPERSAMPLE = 2
COLOUR_STEP_SHIFT = 3
LONGEST_FRAME_SECONDS = 0.2
REFERENCE_FRAME_SECONDS = 0.05
SEED = 1
LOWEST_PITCH = 28
HIGHEST_PITCH = 100
FULL_VELOCITY = 127
# A rocket: how long it climbs, in seconds, where its bursts gather, as a share of the area's height, how much higher the loudest note goes than the softest, the spread of heights about that, held within the lowest and highest, and how far either way the place across varies.
CLIMB_SECONDS = 0.6
BURST_HEIGHT = 0.6
LOUDNESS_LIFT = 0.08
HEIGHT_SPREAD = 0.06
LOWEST_BURST = 0.45
HIGHEST_BURST = 0.78
ACROSS_SPREAD = 0.06
# The rockets' colours, taken in turn so that each has an equal share: red, gold, green, cyan, blue, magenta and white, as far apart as colours go.
ROCKET_COLOURS = ((255, 50, 40), (255, 190, 30), (40, 235, 70), (30, 220, 255), (80, 120, 255), (240, 60, 230), (235, 235, 235))
# A burst: how many sparks for the softest and the loudest note, how fast they fly out as a share of the height a second, and how long they live, in seconds; a drum's crackle has fewer, slower, shorter.
FEWEST_SPARKS = 22
MOST_SPARKS_PER_BURST = 70
SPARK_SPEED = 0.45
SPARK_SECONDS = 1.3
CRACKLE_SPARKS = 10
CRACKLE_SPEED = 0.25
CRACKLE_SECONDS = 0.6
CRACKLE_COLOUR = (210, 205, 190)
# How sparks move: gravity as a share of the height a second a second, and how much of their speed they keep a second.
GRAVITY = 0.16
DRAG_KEPT_PER_SECOND = 0.5
# The most sparks alive at once, the oldest giving way; a rocket's brightness while it climbs; and how much of the picture each frame keeps, out of 256, for the trails.
MOST_SPARKS = 2400
ROCKET_BRIGHTNESS = 0.6
KEPT = 175
KEPT_SHIFT = 8
WHOLE_KEPT = 256
# The limiter: the mean brightness held under, the ceiling, how fast the mean may rise and fall, out of 255 a second, and the most it may lift a dim picture.
MEAN_LEVEL = 80.0
CEILING = 235
MEAN_RISE_PER_SECOND = 45.0
MEAN_FALL_PER_SECOND = 40.0
MOST_GAIN = 1.4


class Rocket:
    """A rocket climbing: where it set off, across as a share of the area, when, how high it bursts, its colour, how loud, and whether it is a drum's."""

    __slots__ = ('across', 'launched', 'height', 'colour', 'loudness', 'drum')

    def __init__(self, *, across, launched, height, colour, loudness, drum):
        self.across = across
        self.launched = launched
        self.height = height
        self.colour = colour
        self.loudness = loudness
        self.drum = drum


class Fireworks(Visualizer):
    """Rockets for notes, bursting into sparks that fall and fade with trails."""

    __slots__ = ('_rows', '_columns', '_picture', '_rockets', '_places', '_speeds', '_colours', '_ages', '_lives', '_last', '_chooser', '_limiter', '_launched')

    NAME = MSG_FIREWORKS
    OPTION = 'fireworks'

    def __init__(self):
        super().__init__()
        self._rockets = []
        self._launched = 0
        self._last = None
        self._chooser = random.Random(SEED)
        self._limiter = Limiter(
            mean_level=MEAN_LEVEL, ceiling=CEILING, rise_per_second=MEAN_RISE_PER_SECOND, fall_per_second=MEAN_FALL_PER_SECOND, most_gain=MOST_GAIN,
        )
        self.resized(columns=0, rows=0)

    def resized(self, *, columns, rows):
        self._rows = rows * SUPERSAMPLE
        self._columns = columns * SUPERSAMPLE
        self._picture = numpy.zeros((self._rows, self._columns, 3), dtype=numpy.int32)
        self._places = numpy.zeros((0, 2))
        self._speeds = numpy.zeros((0, 2))
        self._colours = numpy.zeros((0, 3))
        self._ages = numpy.zeros(0)
        self._lives = numpy.zeros(0)

    def spark_count(self):
        """Return how many sparks are alive, for the tests."""
        return len(self._ages)

    def pixels(self, *, now, heard=SILENCE):
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        self.launch(heard=heard, now=now)
        kept = int(WHOLE_KEPT * (KEPT / WHOLE_KEPT) ** (seconds / REFERENCE_FRAME_SECONDS)) if seconds else KEPT
        self._picture = (self._picture * kept) >> KEPT_SHIFT
        self.climb(now)
        self.fly(seconds)
        small = brightest_of_blocks(fine=self._picture, factor=SUPERSAMPLE)
        held = self._limiter.limited(picture=small, seconds=seconds)
        return (held >> COLOUR_STEP_SHIFT) << COLOUR_STEP_SHIFT

    def launch(self, *, heard, now):
        """Launch a rocket for each note that starts, across at its pitch, as high as it is loud."""
        for note in heard.notes:
            if not note.started:
                continue
            loudness = note.velocity / FULL_VELOCITY
            across = (min(max(note.pitch, LOWEST_PITCH), HIGHEST_PITCH) - LOWEST_PITCH) / (HIGHEST_PITCH - LOWEST_PITCH)
            across = min(max(across + self._chooser.uniform(-ACROSS_SPREAD, ACROSS_SPREAD), 0.0), 1.0)
            height = BURST_HEIGHT + LOUDNESS_LIFT * (loudness - 0.5) + self._chooser.gauss(0.0, HEIGHT_SPREAD)
            height = min(max(height, LOWEST_BURST), HIGHEST_BURST)
            if note.drum:
                self.burst(row=self._rows * (1 - height), column=across * (self._columns - 1), colour=numpy.array(CRACKLE_COLOUR), count=CRACKLE_SPARKS,
                           speed=CRACKLE_SPEED, seconds=CRACKLE_SECONDS)
            else:
                colour = numpy.array(self.next_colour(), dtype=float)
                self._rockets.append(Rocket(across=across, launched=now, height=height, colour=colour, loudness=loudness, drum=note.drum))

    def next_colour(self):
        """Return the next rocket's colour, going round ROCKET_COLOURS so that each has an equal share."""
        colour = ROCKET_COLOURS[self._launched % len(ROCKET_COLOURS)]
        self._launched += 1
        return colour

    def climb(self, now):
        """Draw each rocket still climbing at its place, and burst each that has reached the top of its climb."""
        climbing = []
        for rocket in self._rockets:
            share = (now - rocket.launched) / CLIMB_SECONDS
            row = self._rows - 1 - share * rocket.height * self._rows
            column = rocket.across * (self._columns - 1)
            if share >= 1.0:
                count = int(FEWEST_SPARKS + (MOST_SPARKS_PER_BURST - FEWEST_SPARKS) * rocket.loudness)
                self.burst(row=row, column=column, colour=rocket.colour, count=count, speed=SPARK_SPEED, seconds=SPARK_SECONDS)
                continue
            climbing.append(rocket)
            if 0 <= int(row) < self._rows and 0 <= int(column) < self._columns:
                self._picture[int(row), int(column)] = numpy.maximum(self._picture[int(row), int(column)], (rocket.colour * ROCKET_BRIGHTNESS).astype(numpy.int32))
        self._rockets = climbing

    def burst(self, *, row, column, colour, count, speed, seconds):
        """Add count sparks flying out from a place in every direction, each a little different in speed, living for about seconds."""
        angles = numpy.array([self._chooser.uniform(0, math.tau) for _ in range(count)])
        speeds = numpy.array([self._chooser.uniform(0.5, 1.0) for _ in range(count)]) * speed * self._rows
        places = numpy.tile([row, column], (count, 1)).astype(float)
        velocities = numpy.stack([numpy.sin(angles) * speeds, numpy.cos(angles) * speeds * 2], axis=1)
        self._places = numpy.concatenate([self._places, places])[-MOST_SPARKS:]
        self._speeds = numpy.concatenate([self._speeds, velocities])[-MOST_SPARKS:]
        self._colours = numpy.concatenate([self._colours, numpy.tile(colour, (count, 1))])[-MOST_SPARKS:]
        self._ages = numpy.concatenate([self._ages, numpy.zeros(count)])[-MOST_SPARKS:]
        self._lives = numpy.concatenate([self._lives, numpy.array([self._chooser.uniform(0.7, 1.0) * seconds for _ in range(count)])])[-MOST_SPARKS:]

    def fly(self, seconds):
        """Move every spark on, slowing and falling, forget those that have lived out their lives, and draw the rest, dimming as they age."""
        if not len(self._ages):
            return
        self._speeds *= DRAG_KEPT_PER_SECOND ** seconds
        self._speeds[:, 0] += GRAVITY * self._rows * seconds
        self._places += self._speeds * seconds
        self._ages += seconds
        alive = self._ages < self._lives
        self._places, self._speeds, self._colours, self._ages, self._lives = (
            self._places[alive], self._speeds[alive], self._colours[alive], self._ages[alive], self._lives[alive])
        rows = numpy.rint(self._places[:, 0]).astype(numpy.intp)
        columns = numpy.rint(self._places[:, 1]).astype(numpy.intp)
        inside = (rows >= 0) & (rows < self._rows) & (columns >= 0) & (columns < self._columns)
        brightness = (1.0 - self._ages / self._lives)[:, None]
        colours = (self._colours * brightness).astype(numpy.int32)[inside]
        rows, columns = rows[inside], columns[inside]
        numpy.maximum.at(self._picture, (rows, columns), colours)


def brightest_of_blocks(*, fine, factor):
    """Return a picture taken down by factor each way, each big pixel the brightest of its block, so that a point stays a crisp, bright point rather than being averaged away."""
    rows = fine.shape[0] // factor
    columns = fine.shape[1] // factor
    return fine[:rows * factor, :columns * factor].reshape(rows, factor, columns, factor, 3).max(axis=(1, 3))
