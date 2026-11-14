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
"""Laser Llama, a visualizer mode after the synthwave and chillwave backgrounds of the user's own videos: a neon sunset over a purple grid floor, and a llama with a laser cannon on its back firing lasers to punctuate the music, the user's design of 2026-11-10.

The scene is drawn finely in half blocks, two pixels a cell: a sky from deep purple to magenta with
a few still stars, a striped sun from yellow to pink setting on the horizon, its stripes sliding
down slowly, and below it a floor of dark purple with a neon grid in perspective, its lines rushing
toward the viewer at the tempo, dimmer in the distance. In front, the llama, drawn in characters,
roams the floor and turns at the edges, its cannon firing a beam in a track's colour each time a
note of that track starts, up into the sky at an angle set by the pitch, which fades in a moment.
Everything is held under the limiter, so the beams never flash. The amounts are named constants
here, for the user to tune by eye.
"""

import math
import random

import numpy

from llamatron.visualizers.cells import HALF_ROWS, SPACE, UPPER_HALF, CellPainter
from llamatron.visualizers.colour import Limiter, note_colour
from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.visualizer import Visualizer
from llamatron.strings.visualizers import MSG_LASER_LLAMA, MSG_LASER_LLAMA_DRAWING

SEED = 1
LONGEST_FRAME_SECONDS = 0.2
FULL_VELOCITY = 127
LOWEST_PITCH = 28
HIGHEST_PITCH = 100
# The sky: its colour at the top and at the horizon, where the horizon is as a share of the height, and how many still stars, how bright.
SKY_TOP = (14, 4, 40)
SKY_HORIZON = (120, 20, 110)
HORIZON_SHARE = 0.58
STARS = 40
STAR_COLOUR = (170, 150, 220)
# The sun: its radius as a share of the height, its colour at the top and bottom, and its stripes: how many, how thick as a share of a stripe's spacing at the bottom, and how fast they slide, in stripes a second.
SUN_RADIUS_SHARE = 0.42
SUN_TOP = (255, 214, 70)
SUN_BOTTOM = (240, 50, 140)
SUN_STRIPES = 7
STRIPE_GAP = 0.45
STRIPE_SPEED = 0.25
# The floor: its colour, the grid's colour, how many lines across, how far apart the lines are in depth, how fast the grid comes toward the viewer at 120 a minute, in lines a second, and how thick a line is.
FLOOR = (20, 4, 34)
GRID = (230, 60, 230)
GRID_LINES_ACROSS = 12
DEPTH_SPACING = 1.0
GRID_SPEED = 2.0
LINE_THICKNESS = 0.06
# Far off, the lines would come closer than a pixel, so they stop at FINEST_LINE and the floor fades into a haze from HAZE_FROM over HAZE_OVER of depth.
FINEST_LINE = 0.3
HAZE = (110, 24, 100)
HAZE_FROM = 3.0
HAZE_OVER = 6.0
# The llama: its colour, how fast it roams as a share of the width a second at 120 a minute, where its cannon's mouth is in its drawing, and how its beams fan out by pitch, in radians either side of straight up, how long one lasts, and the most at once.
LLAMA_COLOUR = (120, 240, 255)
ROAM_SPEED = 0.08
CANNON_MOUTH = (0, 11)
BEAM_FAN = 1.1
BEAM_SECONDS = 0.5
MOST_BEAMS = 24
BEAM_BRIGHTNESS = 1.0
# The limiter: the scene is bright, as synthwave is, and still never flashes.
MEAN_LEVEL = 95.0
CEILING = 235
MEAN_RISE_PER_SECOND = 45.0
MEAN_FALL_PER_SECOND = 45.0
MOST_GAIN = 1.0
COLOUR_STEP_SHIFT = 4


def mirrored_drawing(drawing):
    width = max(len(line) for line in drawing)
    return tuple(line.ljust(width)[::-1].translate(str.maketrans('()/\\', ')(\\/')) for line in drawing)


class Beam:
    """A laser beam: from where, its angle, when it was fired and its colour."""

    __slots__ = ('start', 'angle', 'fired', 'colour')

    def __init__(self, *, start, angle, fired, colour):
        self.start = start
        self.angle = angle
        self.fired = fired
        self.colour = colour


class LaserLlama(Visualizer):
    """A neon sunset over a rushing grid, and a llama firing lasers to the notes."""

    __slots__ = ('_rows', '_columns', '_grid', '_backdrop', '_stars', '_scroll', '_llama', '_facing', '_beams', '_last', '_limiter', '_cells', '_chooser')

    NAME = MSG_LASER_LLAMA
    OPTION = 'laser_llama'
    DARK_IN_SILENCE = False

    def __init__(self):
        super().__init__()
        self._chooser = random.Random(SEED)
        self._cells = CellPainter()
        self._limiter = Limiter(
            mean_level=MEAN_LEVEL, ceiling=CEILING, rise_per_second=MEAN_RISE_PER_SECOND, fall_per_second=MEAN_FALL_PER_SECOND, most_gain=MOST_GAIN,
        )
        self._scroll = 0.0
        self._llama = 0.2
        self._facing = 1
        self._beams = []
        self._last = None
        self._rows = 0
        self._columns = 0

    def sized(self, *, width, height):
        rows = height * HALF_ROWS
        if (rows, width) != (self._rows, self._columns):
            self._rows = rows
            self._columns = width
            self._grid = numpy.mgrid[0:rows, 0:width].astype(numpy.float32)
            self._stars = [(self._chooser.randrange(max(int(rows * HORIZON_SHARE) - 1, 1)), self._chooser.randrange(max(width, 1))) for _ in range(STARS)]

    def beam_count(self):
        """Return how many beams are alive, for the tests."""
        return len(self._beams)

    def frame(self, *, width, height, now, heard=SILENCE):
        if not width or not height:
            return []
        self.sized(width=width, height=height)
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        tempo = heard.tempo_factor()
        self._scroll += GRID_SPEED * tempo * seconds
        drawing = MSG_LASER_LLAMA_DRAWING if self._facing > 0 else mirrored_drawing(MSG_LASER_LLAMA_DRAWING)
        drawing_width = max(len(line) for line in drawing)
        self._llama += self._facing * ROAM_SPEED * tempo * seconds
        if self._llama < 0 or self._llama * width + drawing_width > width:
            self._facing = -self._facing
            self._llama = min(max(self._llama, 0.0), max((width - drawing_width) / max(width, 1), 0.0))
        left = int(self._llama * width)
        top = max(height - len(drawing), 0)
        self.fire(heard=heard, now=now, mouth=((top + CANNON_MOUTH[0]) * HALF_ROWS, left + (CANNON_MOUTH[1] if self._facing > 0 else drawing_width - 1 - CANNON_MOUTH[1])))
        picture = self.scene(now=now)
        self.draw_beams(picture=picture, now=now)
        held = self._limiter.limited(picture=picture, seconds=seconds)
        held = (held >> COLOUR_STEP_SHIFT) << COLOUR_STEP_SHIFT
        return self.lines(picture=held, drawing=drawing, top=top, left=left, width=width, height=height)

    def fire(self, *, heard, now, mouth):
        """Fire a beam from the cannon's mouth for each note that starts, in its track's colour, up into the sky at an angle by its pitch."""
        for note in heard.notes:
            if note.started:
                share = (min(max(note.pitch, LOWEST_PITCH), HIGHEST_PITCH) - LOWEST_PITCH) / (HIGHEST_PITCH - LOWEST_PITCH)
                angle = (share - 0.5) * 2 * BEAM_FAN * self._facing
                colour = note_colour(track=note.track, pitch=note.pitch, drum=note.drum) * note.velocity / FULL_VELOCITY
                self._beams.append(Beam(start=mouth, angle=angle, fired=now, colour=colour))
        del self._beams[:-MOST_BEAMS]

    def scene(self, *, now):
        """Return the backdrop: the sky with its stars, the striped sun on the horizon, and the floor with its grid rushing toward the viewer."""
        rows, columns = self._grid
        horizon = self._rows * HORIZON_SHARE
        height_share = numpy.clip(rows / max(horizon, 1), 0, 1)[:, :, None]
        picture = numpy.array(SKY_TOP) * (1 - height_share) + numpy.array(SKY_HORIZON) * height_share
        for row, column in self._stars:
            picture[row, column] = STAR_COLOUR
        radius = SUN_RADIUS_SHARE * self._rows
        middle_column = (self._columns - 1) / 2
        from_middle = numpy.hypot(rows - horizon, (columns - middle_column) * 0.5)
        down_the_sun = numpy.clip((rows - (horizon - radius)) / max(radius, 1), 0, 1)
        stripe = ((down_the_sun * SUN_STRIPES + now * STRIPE_SPEED) % 1.0) < STRIPE_GAP * down_the_sun
        sun = (from_middle < radius) & (rows < horizon) & ~stripe
        sun_colour = numpy.array(SUN_TOP) * (1 - down_the_sun[:, :, None]) + numpy.array(SUN_BOTTOM) * down_the_sun[:, :, None]
        picture = numpy.where(sun[:, :, None], sun_colour, picture)
        below = rows >= horizon
        depth = DEPTH_SPACING * self._rows / numpy.maximum(rows - horizon, 1.0)
        across = (columns - middle_column) / max(self._columns, 1) * depth * GRID_LINES_ACROSS / 4
        along = depth + self._scroll
        thickness = LINE_THICKNESS * depth
        line = ((numpy.abs(across - numpy.round(across)) < thickness) | (numpy.abs(along - numpy.round(along)) < thickness)) & (thickness < FINEST_LINE)
        fade = numpy.clip(1.5 / depth, 0.2, 1.0)[:, :, None]
        floor = numpy.where(line[:, :, None], numpy.array(GRID) * fade, numpy.array(FLOOR))
        haze = numpy.clip((depth - HAZE_FROM) / HAZE_OVER, 0, 1)[:, :, None]
        floor = floor * (1 - haze) + numpy.array(HAZE) * haze
        picture = numpy.where(below[:, :, None], floor, picture)
        return picture.astype(numpy.int32)

    def draw_beams(self, *, picture, now):
        """Draw each beam still alive as a line from the cannon to the top, fading as it ages."""
        living = []
        for beam in self._beams:
            age = now - beam.fired
            if age >= BEAM_SECONDS:
                continue
            living.append(beam)
            length = max(self._rows, self._columns)
            steps = numpy.linspace(0, length, length * 2)
            rows = numpy.rint(beam.start[0] - steps * math.cos(beam.angle)).astype(numpy.intp)
            columns = numpy.rint(beam.start[1] + steps * math.sin(beam.angle) * 2).astype(numpy.intp)
            inside = (rows >= 0) & (rows < self._rows) & (columns >= 0) & (columns < self._columns)
            colour = (beam.colour * BEAM_BRIGHTNESS * (1.0 - age / BEAM_SECONDS)).astype(numpy.int32)
            picture[rows[inside], columns[inside]] = numpy.maximum(picture[rows[inside], columns[inside]], colour)
        self._beams = living

    def lines(self, *, picture, drawing, top, left, width, height):
        """Return the lines: the picture in half blocks, with the llama's drawing laid over it in its colour on the picture beneath."""
        listed = picture.tolist()
        lines = []
        for row in range(height):
            upper = listed[HALF_ROWS * row]
            lower = listed[HALF_ROWS * row + 1]
            characters = [UPPER_HALF] * width
            styles = [self._cells.style_of(colour=tuple(high), background=tuple(low)) for high, low in zip(upper, lower)]
            down = row - top
            if 0 <= down < len(drawing):
                for across, character in enumerate(drawing[down]):
                    column = left + across
                    if character != SPACE and 0 <= column < width:
                        characters[column] = character
                        styles[column] = self._cells.style_of(colour=LLAMA_COLOUR, background=tuple(lower[column]))
            lines.append(self._cells.line(characters=characters, styles=styles))
        return lines
