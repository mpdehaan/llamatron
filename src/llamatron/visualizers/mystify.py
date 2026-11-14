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
"""Mystify, a visualizer mode after the Windows screensavers Mystify and Starfield at once, heavily polygons, in fine Braille dots, the user's choice of 2026-11-10, its details Claude's.

Behind, a starfield streams toward the viewer at the tempo, its stars brightening as they come near,
and each note starting tints a few stars in its track's colour as they fly. In front, a polygon for
each track (up to MOST_POLYGONS, later tracks sharing), its corners bouncing off the edges of the
area, with fading copies of where it was trailing behind, as Mystify's did. Its corners follow the
track's harmony: three for a single note, one more for each note held with it, up to MOST_CORNERS,
so that a chord turns a triangle into a pentagon; and they quicken on each note and settle back.
Everything is drawn in Braille, eight dots a cell, so that lines are fine, each cell in the colour
of its brightest dot, and nothing ever flashes: brightness only rises gently. The amounts are named
constants here, for the user to tune by eye.
"""

import math
import random

import numpy

from llamatron.visualizers.cells import BRAILLE_COLUMNS, BRAILLE_ROWS, CellPainter
from llamatron.visualizers.colour import note_colour, track_colour, vivid
from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.visualizer import Visualizer
from llamatron.strings.visualizers import MSG_MYSTIFY

SEED = 1
LONGEST_FRAME_SECONDS = 0.2
FULL_VELOCITY = 127
# The stars: how many, how fast they come, as a share of their depth a second at 120 a minute, how near they come before they start again far off, their colour, and how many a note tints.
STARS = 160
STAR_SPEED = 0.45
NEAREST = 0.05
STAR_COLOUR = (80, 86, 115)
STARS_PER_NOTE = 3
# The polygons: the most there are, the fewest and most corners, how fast the corners move as a share of the area a second, and how much a note quickens them, settling back by this much a second.
MOST_POLYGONS = 8
FEWEST_CORNERS = 3
MOST_CORNERS = 7
CORNER_SPEED = 0.25
QUICKEN_PER_NOTE = 0.6
QUICKEN_KEPT_PER_SECOND = 0.3
# The trails: how many copies trail behind, how many seconds apart, and how bright the oldest is beside the newest.
TRAIL_COPIES = 5
TRAIL_SECONDS = 0.12
OLDEST_BRIGHTNESS = 0.2
# A polygon's brightness at rest and playing, and over both, how much brighter than its colour, the user's ask of sixty percent more, how fast it may rise and how much of its energy is kept a second.
RESTING_BRIGHTNESS = 0.7
PLAYING_BRIGHTNESS = 1.0
ENERGY_PER_NOTE = 0.4
ENERGY_RISE_PER_SECOND = 2.0
ENERGY_KEPT_PER_SECOND = 0.35
# How finely the edges are drawn: points along each, for each dot of the area's height.
POINTS_PER_DOT = 0.8
COLOUR_STEP = 16
CEILING = 225


class Polygon:
    """One track's polygon: its corners and their headings, in dots, how many it shows, how quick it is, its energy, its colour and where it was."""

    __slots__ = ('corners', 'headings', 'count', 'quicken', 'energy', 'target', 'colour', 'trail', 'since_copy')

    def __init__(self, *, corners, headings, colour):
        self.corners = corners
        self.headings = headings
        self.count = FEWEST_CORNERS
        self.quicken = 0.0
        self.energy = 0.0
        self.target = 0.0
        self.colour = colour
        self.trail = []
        self.since_copy = 0.0


class Mystify(Visualizer):
    """Polygons bouncing with trails over a starfield, in Braille."""

    __slots__ = ('_rows', '_columns', '_polygons', '_stars', '_star_colours', '_chooser', '_last', '_cells')

    NAME = MSG_MYSTIFY
    OPTION = 'mystify'

    def __init__(self):
        super().__init__()
        self._polygons = {}
        self._chooser = random.Random(SEED)
        self._last = None
        self._cells = CellPainter()
        self._stars = numpy.array([[self._chooser.uniform(-1, 1), self._chooser.uniform(-1, 1), self._chooser.uniform(NEAREST, 1)] for _ in range(STARS)])
        self._star_colours = numpy.tile(numpy.array(STAR_COLOUR, dtype=float), (STARS, 1))
        self._rows = 0
        self._columns = 0

    def corners_of(self, track):
        """Return how many corners a track's polygon shows, for the tests."""
        return self.polygon_of(track).count

    def frame(self, *, width, height, now, heard=SILENCE):
        if not width or not height:
            return []
        self._rows = height * BRAILLE_ROWS
        self._columns = width * BRAILLE_COLUMNS
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        tempo = heard.tempo_factor()
        self.hear(heard)
        self.fly(seconds * tempo)
        self.bounce(seconds=seconds, tempo=tempo)
        dots = numpy.zeros((self._rows, self._columns), dtype=bool)
        colours = numpy.zeros((height, width, 3), dtype=numpy.int32)
        self.draw_stars(dots=dots, colours=colours)
        self.draw_polygons(dots=dots, colours=colours)
        colours = numpy.clip(colours, 0, CEILING) // COLOUR_STEP * COLOUR_STEP
        return self._cells.braille(dots=dots, colours=colours, width=width)

    def polygon_of(self, track):
        """Return the polygon a track draws, made the first time; past MOST_POLYGONS, tracks share."""
        place = track % MOST_POLYGONS
        if place not in self._polygons:
            corners = numpy.array([[self._chooser.uniform(0, 1), self._chooser.uniform(0, 1)] for _ in range(MOST_CORNERS)])
            headings = numpy.array([[math.sin(angle), math.cos(angle)] for angle in (self._chooser.uniform(0, math.tau) for _ in range(MOST_CORNERS))])
            self._polygons[place] = Polygon(corners=corners, headings=headings, colour=vivid(track_colour(track)))
        return self._polygons[place]

    def hear(self, heard):
        """Let each note set its polygon's colour and count its corners, three and one for each other note held with it, and each that starts quicken it and tint some stars."""
        held = {}
        for note in heard.notes:
            polygon = self.polygon_of(note.track)
            polygon.colour = vivid(note_colour(track=note.track, pitch=note.pitch, drum=note.drum))
            held[note.track % MOST_POLYGONS] = held.get(note.track % MOST_POLYGONS, 0) + 1
            if note.started:
                loudness = note.velocity / FULL_VELOCITY
                polygon.quicken += QUICKEN_PER_NOTE * loudness
                polygon.target = min(polygon.target + ENERGY_PER_NOTE * loudness, 1.0)
                for _ in range(STARS_PER_NOTE):
                    self._star_colours[self._chooser.randrange(STARS)] = polygon.colour
        for place, count in held.items():
            self._polygons[place].count = min(max(FEWEST_CORNERS + count - 1, FEWEST_CORNERS), MOST_CORNERS)

    def fly(self, seconds):
        """Bring every star nearer, starting again far off, white once more, any that has passed the nearest."""
        self._stars[:, 2] -= STAR_SPEED * seconds
        passed = self._stars[:, 2] < NEAREST
        if passed.any():
            count = int(passed.sum())
            self._stars[passed] = numpy.array([[self._chooser.uniform(-1, 1), self._chooser.uniform(-1, 1), 1.0] for _ in range(count)])
            self._star_colours[passed] = STAR_COLOUR

    def bounce(self, *, seconds, tempo):
        """Move every polygon's corners on, bouncing off the edges, quicker after its notes; keep a copy for its trail now and then; settle its energy."""
        for polygon in self._polygons.values():
            polygon.corners += polygon.headings * CORNER_SPEED * tempo * (1.0 + polygon.quicken) * seconds
            low = polygon.corners < 0
            high = polygon.corners > 1
            polygon.headings[low | high] *= -1
            polygon.corners = numpy.clip(polygon.corners, 0, 1)
            polygon.quicken *= QUICKEN_KEPT_PER_SECOND ** seconds
            rise = ENERGY_RISE_PER_SECOND * seconds
            polygon.energy += max(-rise, min(rise, polygon.target - polygon.energy))
            polygon.target *= ENERGY_KEPT_PER_SECOND ** seconds
            polygon.since_copy += seconds
            if polygon.since_copy >= TRAIL_SECONDS:
                polygon.since_copy = 0.0
                polygon.trail = (polygon.trail + [polygon.corners[:polygon.count].copy()])[-TRAIL_COPIES:]

    def draw_stars(self, *, dots, colours):
        """Draw each star where it is seen, brighter the nearer it is."""
        seen_rows = ((self._stars[:, 1] / self._stars[:, 2]) * 0.5 + 0.5) * (self._rows - 1)
        seen_columns = ((self._stars[:, 0] / self._stars[:, 2]) * 0.5 + 0.5) * (self._columns - 1)
        rows = numpy.rint(seen_rows).astype(numpy.intp)
        columns = numpy.rint(seen_columns).astype(numpy.intp)
        inside = (rows >= 0) & (rows < self._rows) & (columns >= 0) & (columns < self._columns)
        nearness = (1.0 - self._stars[:, 2])[:, None]
        self.put(dots=dots, colours=colours, rows=rows[inside], columns=columns[inside], colour=(self._star_colours * nearness)[inside])

    def draw_polygons(self, *, dots, colours):
        """Draw each polygon's trail, oldest dimmest, and the polygon itself over it, each edge as points along it."""
        scale = numpy.array([self._rows - 1, self._columns - 1])
        steps = numpy.linspace(0, 1, max(int(self._rows * POINTS_PER_DOT), 2))[:, None]
        for polygon in self._polygons.values():
            brightness = RESTING_BRIGHTNESS + (PLAYING_BRIGHTNESS - RESTING_BRIGHTNESS) * polygon.energy
            outlines = polygon.trail + [polygon.corners[:polygon.count]]
            for age, outline in enumerate(outlines):
                share = OLDEST_BRIGHTNESS + (1.0 - OLDEST_BRIGHTNESS) * (age + 1) / len(outlines)
                corners = outline * scale
                ends = numpy.roll(corners, -1, axis=0)
                points = (corners[:, None, :] + (ends - corners)[:, None, :] * steps[None, :, :]).reshape(-1, 2)
                rows = numpy.rint(points[:, 0]).astype(numpy.intp)
                columns = numpy.rint(points[:, 1]).astype(numpy.intp)
                colour = numpy.tile(polygon.colour * brightness * share, (len(rows), 1))
                self.put(dots=dots, colours=colours, rows=rows, columns=columns, colour=colour)

    @staticmethod
    def put(*, dots, colours, rows, columns, colour):
        """Set dots, and make each cell the colour of its brightest dot."""
        dots[rows, columns] = True
        numpy.maximum.at(colours, (rows // BRAILLE_ROWS, columns // BRAILLE_COLUMNS), colour.astype(numpy.int32))
