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
"""The hypercube, a visualizer mode: a tesseract turning in four dimensions, seen through a derezzed view, bright rather than dark, its edges shared out among the tracks, the user's design of 2026-11-10.

Its sixteen corners are every combination of plus and minus one in four dimensions, and its
thirty-two edges join the corners that differ in one. Each frame it turns in two planes at once,
the one through its first and fourth dimensions and the one through its second and third, with a
slower turn in a third plane, faster for a faster song and a little faster as the tracks play; it is
seen in perspective down to three dimensions and again down to two, and pulses gently with the
beat. The tracks that have played share out its edges in turn, each lighting its edges in the
colour of its last note, brighter as it plays. The edges are drawn as points along their lengths at
SUPERSAMPLE times the big pixels each way, blurred into a glow and drawn sharp again over it, so
that they bloom across their neighbours when averaged down, over a wash of the playing colours that
keeps the picture from going dark, and the limiter keeps it from ever flashing. The amounts are
named constants here, for the user to tune by eye.
"""

import itertools
import math

import numpy

from llamatron.visualizers.colour import Limiter, note_colour
from llamatron.visualizers.fields import blurred
from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.lava_lamp import derezzed
from llamatron.visualizers.visualizer import Visualizer
from llamatron.strings.visualizers import MSG_HYPERCUBE

SUPERSAMPLE = 2
COLOUR_STEP_SHIFT = 3
LONGEST_FRAME_SECONDS = 0.2
DIMENSIONS = 4
# The turning: radians a second at 120 a minute in each of the three planes, as pairs of dimensions, and how much the tracks' playing speeds it.
PLANES = (((0, 3), 0.55), ((1, 2), 0.37), ((0, 1), 0.13))
ENERGY_SPIN = 0.8
# The view: how far the eye is from the middle in the fourth dimension and in the third, and how big the cube is as a share of the area's height, pulsing by this share on each beat, as sharp as this.
FOURTH_DISTANCE = 3.0
THIRD_DISTANCE = 4.0
SIZE_SHARE = 0.95
BEAT_PULSE = 0.04
PULSE_SHARPNESS = 4
# The edges: points along each, for each cell of the simulation's height, how brightly a resting track's edges glow and how much brighter at full energy, and the glow's blur passes.
POINTS_PER_CELL = 1.5
RESTING_GLOW = 0.35
PLAYING_GLOW = 1.0
GLOW_PASSES = 3
GLOW_WEIGHT = 2
CORE_WEIGHT = 1
# Before any track has played, the edges are this colour.
QUIET_COLOUR = (120, 120, 150)
# The wash behind it all: how much of the playing tracks' colours, so that the picture isn't dark.
WASH = 0.22
# A track's energy: how much a note at full velocity raises its target, how fast the energy may rise toward it, and how much of the target is kept a second.
ENERGY_PER_NOTE = 0.4
ENERGY_RISE_PER_SECOND = 2.5
ENERGY_KEPT_PER_SECOND = 0.3
FULL_VELOCITY = 127
# The limiter: brighter than the other modes, as the user asked, and still never flashing.
MEAN_LEVEL = 105.0
CEILING = 230
MEAN_RISE_PER_SECOND = 50.0
MEAN_FALL_PER_SECOND = 40.0
MOST_GAIN = 1.6
FULL_TURN = 2 * math.pi
HALF = 0.5


def corners():
    """Return the tesseract's sixteen corners, each a combination of plus and minus one in four dimensions, as a 16 by 4 array."""
    return numpy.array(list(itertools.product((-1.0, 1.0), repeat=DIMENSIONS)))


def edges(points):
    """Return the tesseract's thirty-two edges, as pairs of corners' places that differ in one dimension."""
    return [(first, second) for first in range(len(points)) for second in range(first + 1, len(points))
            if numpy.count_nonzero(points[first] != points[second]) == 1]


class Hypercube(Visualizer):
    """A tesseract turning in four dimensions, its edges glowing in the colours of the tracks that share them."""

    __slots__ = ('_rows', '_columns', '_corners', '_edges', '_angles', '_last', '_energies', '_targets', '_colours', '_limiter', '_along')

    NAME = MSG_HYPERCUBE
    OPTION = 'hypercube'
    # Its quiet edges glow even before a track has played, since the user wants it bright rather than dark.
    DARK_IN_SILENCE = False

    def __init__(self):
        super().__init__()
        self._corners = corners()
        self._edges = edges(self._corners)
        self._angles = [0.0] * len(PLANES)
        self._last = None
        self._energies = {}
        self._targets = {}
        self._colours = {}
        self._limiter = Limiter(
            mean_level=MEAN_LEVEL, ceiling=CEILING, rise_per_second=MEAN_RISE_PER_SECOND, fall_per_second=MEAN_FALL_PER_SECOND, most_gain=MOST_GAIN,
        )
        self.resized(columns=0, rows=0)

    def resized(self, *, columns, rows):
        self._rows = rows * SUPERSAMPLE
        self._columns = columns * SUPERSAMPLE
        # How far along an edge each of its points is, from 0 to 1, as many as the height asks for.
        self._along = numpy.linspace(0.0, 1.0, max(int(self._rows * POINTS_PER_CELL), 2))[:, None]

    def pixels(self, *, now, heard=SILENCE):
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        self.hear(heard)
        self.settle(seconds)
        energy = max(self._energies.values(), default=0.0)
        for place, (_, speed) in enumerate(PLANES):
            self._angles[place] += speed * seconds * heard.tempo_factor() * (1.0 + ENERGY_SPIN * energy)
        pulse = (HALF + HALF * math.cos(FULL_TURN * (heard.beats % 1.0))) ** PULSE_SHARPNESS
        projected = self.projected(scale=self._rows * SIZE_SHARE * (1.0 + BEAT_PULSE * pulse) / 2)
        picture = self.drawn_edges(projected)
        small = derezzed(fine=picture, factor=SUPERSAMPLE)
        held = self._limiter.limited(picture=small, seconds=seconds)
        return (held >> COLOUR_STEP_SHIFT) << COLOUR_STEP_SHIFT

    def hear(self, heard):
        """Let each note that starts raise its track's energy target, and remember the colour of each track's latest note."""
        for note in heard.notes:
            self._colours[note.track] = note_colour(track=note.track, pitch=note.pitch, drum=note.drum)
            self._energies.setdefault(note.track, 0.0)
            if note.started:
                self._targets[note.track] = min(self._targets.get(note.track, 0.0) + ENERGY_PER_NOTE * note.velocity / FULL_VELOCITY, 1.0)

    def settle(self, seconds):
        """Move each track's energy toward its target no faster than it may rise, and let the target fade."""
        kept = ENERGY_KEPT_PER_SECOND ** seconds
        rise = ENERGY_RISE_PER_SECOND * seconds
        for track in self._energies:
            target = self._targets.get(track, 0.0)
            self._energies[track] += max(-rise, min(rise, target - self._energies[track]))
            self._targets[track] = target * kept

    def projected(self, *, scale):
        """Return the corners turned and seen in perspective, as rows and columns of the simulation."""
        points = self._corners.copy()
        for ((first, second), _), angle in zip(PLANES, self._angles):
            cosine = math.cos(angle)
            sine = math.sin(angle)
            points[:, first], points[:, second] = points[:, first] * cosine - points[:, second] * sine, points[:, first] * sine + points[:, second] * cosine
        three = points[:, :3] / (FOURTH_DISTANCE - points[:, 3:4])
        flat = three[:, :2] / (THIRD_DISTANCE - three[:, 2:3]) * THIRD_DISTANCE
        rows = (self._rows - 1) / 2 + flat[:, 1] * scale
        columns = (self._columns - 1) / 2 + flat[:, 0] * scale
        return numpy.stack([rows, columns], axis=1)

    def drawn_edges(self, projected):
        """Return the edges drawn in their tracks' colours over the wash: points along each, a blurred glow of them and the sharp points again over it."""
        tracks = sorted(self._energies)
        lines = numpy.zeros((self._rows, self._columns, 3), dtype=numpy.int32)
        starts = projected[[first for first, _ in self._edges]]
        ends = projected[[second for _, second in self._edges]]
        for place, (start, end) in enumerate(zip(starts, ends)):
            if tracks:
                track = tracks[place % len(tracks)]
                colour = self._colours[track] * (RESTING_GLOW + PLAYING_GLOW * self._energies[track])
            else:
                colour = numpy.array(QUIET_COLOUR) * RESTING_GLOW
            points = start + (end - start) * self._along
            rows = numpy.clip(numpy.rint(points[:, 0]).astype(numpy.intp), 0, self._rows - 1)
            columns = numpy.clip(numpy.rint(points[:, 1]).astype(numpy.intp), 0, self._columns - 1)
            lines[rows, columns] = numpy.maximum(lines[rows, columns], colour.astype(numpy.int32))
        glow = lines
        for _ in range(GLOW_PASSES):
            glow = blurred(glow)
        picture = glow * GLOW_WEIGHT + lines * CORE_WEIGHT
        if tracks:
            wash = sum(self._colours[track] * (RESTING_GLOW + self._energies[track]) for track in tracks) / len(tracks)
            picture = picture + (wash * WASH).astype(numpy.int32)
        return picture
