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
"""WarpZone, a visualizer mode: a ball for each track bouncing around the box at a speed set by the tempo, sending out rings as its notes play, the user's design of 2026-11-10.

Each track that has played is a ball moving at one speed, the tempo's, with no momentum: a ball
that meets a wall or another ball bounces off and goes on at that speed. A note starting sends a
ring out from where its ball is, as strong as its velocity, at most one a track every RING_GAP_SECONDS,
which spreads slowly and fades where it was sent. Everything is drawn in Braille, eight dots a cell,
the rings as single lines of dots, so that they read as fine circles, finer than the other modes,
the user's ask after the first WarpZone was too thick, too fast and too pulsing. The balls glow in
their tracks' colours, brighter as they play, and nothing ever flashes. The amounts are named
constants here, for the user to tune by eye.
"""

import math

import numpy

from llamatron.visualizers.cells import BRAILLE_COLUMNS, BRAILLE_ROWS, CellPainter
from llamatron.visualizers.colour import note_colour, track_colour, vivid
from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.visualizer import Visualizer
from llamatron.strings.visualizers import MSG_WARPZONE

LONGEST_FRAME_SECONDS = 0.2
FULL_VELOCITY = 127
# A ball: its speed as a share of the area's height a second at 120 a minute, its radius in dots, how it starts off by track, and how bright at rest and playing.
BALL_SPEED = 0.16
BALL_RADIUS = 2
GOLDEN_TURN = 2.39996
BALL_RESTING = 0.8
BALL_PLAYING = 1.0
# A ring: how fast it spreads, as a share of the height a second, how long it lives in seconds, the least time between two rings of one track, its brightness, and the most rings at once.
RING_SPEED = 0.22
RING_SECONDS = 3.0
RING_GAP_SECONDS = 0.6
RING_BRIGHTNESS = 1.0
# How strong a ring of the softest note is, as a share of the loudest's, and how its fading eases: a power under one keeps it bright for longer.
SOFTEST_RING = 0.5
RING_FADE_POWER = 0.5
MOST_RINGS = 40
# How finely a ring is drawn: dots along it for each dot of its radius.
DOTS_PER_RADIUS = 7
# A track's energy, from its notes: how much a note at full velocity raises it, how fast it may rise and how much is kept a second.
ENERGY_PER_NOTE = 0.4
ENERGY_RISE_PER_SECOND = 2.0
ENERGY_KEPT_PER_SECOND = 0.3
COLOUR_STEP = 16
CEILING = 225


class Ball:
    """One track's ball: where it is, in dots, the way it moves as a unit vector, its energy and what that is moving toward, and when it last sent a ring."""

    __slots__ = ('place', 'heading', 'energy', 'target', 'last_ring')

    def __init__(self, *, place, heading):
        self.place = place
        self.heading = heading
        self.energy = 0.0
        self.target = 0.0
        self.last_ring = None


class Ring:
    """A ring spreading from where its ball was: its middle, when it was sent, its colour and how strong."""

    __slots__ = ('middle', 'sent', 'colour', 'strength')

    def __init__(self, *, middle, sent, colour, strength):
        self.middle = middle
        self.sent = sent
        self.colour = colour
        self.strength = strength


class WarpZone(Visualizer):
    """Balls bouncing at the tempo's speed, sending out fine rings as their tracks play, in Braille."""

    __slots__ = ('_rows', '_columns', '_balls', '_rings', '_last', '_cells', '_disc')

    NAME = MSG_WARPZONE
    OPTION = 'warpzone'

    def __init__(self):
        super().__init__()
        self._balls = {}
        self._rings = []
        self._last = None
        self._cells = CellPainter()
        self._rows = 0
        self._columns = 0
        span = numpy.arange(-BALL_RADIUS, BALL_RADIUS + 1)
        down, across = numpy.meshgrid(span, span, indexing='ij')
        inside = numpy.hypot(down, across) <= BALL_RADIUS
        self._disc = numpy.stack([down[inside], across[inside]], axis=1)

    def frame(self, *, width, height, now, heard=SILENCE):
        if not width or not height:
            return []
        rows = height * BRAILLE_ROWS
        columns = width * BRAILLE_COLUMNS
        if (rows, columns) != (self._rows, self._columns):
            self._rows, self._columns = rows, columns
            for ball in self._balls.values():
                ball.place = numpy.clip(ball.place, 0, [rows - 1, columns - 1])
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        self.hear(heard=heard, now=now)
        self.move(seconds=seconds * heard.tempo_factor(), energy_seconds=seconds)
        dots = numpy.zeros((rows, columns), dtype=bool)
        colours = numpy.zeros((height, width, 3), dtype=numpy.int32)
        self.draw_rings(dots=dots, colours=colours, now=now)
        self.draw_balls(dots=dots, colours=colours)
        colours = numpy.clip(colours, 0, CEILING) // COLOUR_STEP * COLOUR_STEP
        return self._cells.braille(dots=dots, colours=colours, width=width)

    def ball_of(self, track):
        """Return a track's ball, made where its place in the order puts it, heading off at an angle of its own."""
        if track not in self._balls:
            angle = track * GOLDEN_TURN
            place = numpy.array([(0.5 + 0.35 * math.sin(angle)) * (self._rows - 1), (0.5 + 0.35 * math.cos(angle * 1.3)) * (self._columns - 1)])
            self._balls[track] = Ball(place=place, heading=numpy.array([math.sin(angle), math.cos(angle)]))
        return self._balls[track]

    def balls(self):
        """Return the balls, by track, for the tests."""
        return dict(self._balls)

    def hear(self, *, heard, now):
        """Let each note that starts raise its track's energy, and send a ring from its ball unless the ball sent one within RING_GAP_SECONDS."""
        for note in heard.notes:
            ball = self.ball_of(note.track)
            if not note.started:
                continue
            ball.target = min(ball.target + ENERGY_PER_NOTE * note.velocity / FULL_VELOCITY, 1.0)
            if ball.last_ring is None or now - ball.last_ring >= RING_GAP_SECONDS:
                ball.last_ring = now
                colour = note_colour(track=note.track, pitch=note.pitch, drum=note.drum)
                self._rings.append(Ring(middle=ball.place.copy(), sent=now, colour=colour, strength=note.velocity / FULL_VELOCITY))
        del self._rings[:-MOST_RINGS]

    def move(self, *, seconds, energy_seconds):
        """Move every ball on at the one speed, bouncing off the walls and off each other, keeping that speed, and settle each track's energy."""
        distance = BALL_SPEED * self._rows * seconds
        limits = numpy.array([self._rows - 1, self._columns - 1], dtype=float)
        balls = list(self._balls.values())
        for ball in balls:
            ball.place = ball.place + ball.heading * distance
            for axis in range(2):
                if ball.place[axis] < 0 or ball.place[axis] > limits[axis]:
                    ball.heading[axis] = -ball.heading[axis]
                    ball.place[axis] = min(max(ball.place[axis], 0.0), limits[axis])
        touching = []
        if len(balls) > 1:
            places = numpy.array([ball.place for ball in balls])
            gaps = numpy.hypot(*(places[None, :, :] - places[:, None, :]).transpose(2, 0, 1))
            touching = numpy.argwhere(numpy.triu((gaps > 0) & (gaps < 2 * BALL_RADIUS), 1))
        for first, second in touching:
            apart = balls[second].place - balls[first].place
            gap = math.hypot(*apart)
            normal = apart / gap
            for ball, sign in ((balls[first], -1), (balls[second], 1)):
                along = float(numpy.dot(ball.heading, normal))
                if along * sign < 0:
                    ball.heading = ball.heading - 2 * along * normal
                ball.heading = ball.heading / math.hypot(*ball.heading)
                ball.place = numpy.clip(ball.place + sign * normal * (2 * BALL_RADIUS - gap) / 2, 0, limits)
        kept = ENERGY_KEPT_PER_SECOND ** energy_seconds
        rise = ENERGY_RISE_PER_SECOND * energy_seconds
        for ball in balls:
            ball.energy += max(-rise, min(rise, ball.target - ball.energy))
            ball.target *= kept

    def draw_rings(self, *, dots, colours, now):
        """Draw each ring still alive as a single line of dots around its middle, fading as it spreads."""
        living = []
        for ring in self._rings:
            age = now - ring.sent
            if age >= RING_SECONDS:
                continue
            living.append(ring)
            radius = max(age * RING_SPEED * self._rows, 1.0)
            angles = numpy.linspace(0, math.tau, max(int(radius * DOTS_PER_RADIUS), 8), endpoint=False)
            rows = numpy.rint(ring.middle[0] + radius * numpy.sin(angles)).astype(numpy.intp)
            columns = numpy.rint(ring.middle[1] + radius * numpy.cos(angles)).astype(numpy.intp)
            strength = SOFTEST_RING + (1.0 - SOFTEST_RING) * ring.strength
            colour = vivid(ring.colour) * RING_BRIGHTNESS * strength * (1.0 - age / RING_SECONDS) ** RING_FADE_POWER
            self.put(dots=dots, colours=colours, rows=rows, columns=columns, colour=colour)
        self._rings = living

    def draw_balls(self, *, dots, colours):
        """Draw each ball as a small disc of dots in its track's colour, brighter as it plays."""
        for track, ball in self._balls.items():
            brightness = BALL_RESTING + (BALL_PLAYING - BALL_RESTING) * ball.energy
            places = numpy.rint(ball.place).astype(numpy.intp) + self._disc
            self.put(dots=dots, colours=colours, rows=places[:, 0], columns=places[:, 1], colour=vivid(track_colour(track)) * brightness)

    def put(self, *, dots, colours, rows, columns, colour):
        """Set the dots that fall inside the area, and make each cell the colour of its brightest dot."""
        inside = (rows >= 0) & (rows < self._rows) & (columns >= 0) & (columns < self._columns)
        rows, columns = rows[inside], columns[inside]
        dots[rows, columns] = True
        numpy.maximum.at(colours, (rows // BRAILLE_ROWS, columns // BRAILLE_COLUMNS), numpy.tile(numpy.asarray(colour, dtype=numpy.int32), (len(rows), 1)))
