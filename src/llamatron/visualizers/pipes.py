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
"""Pipes, a visualizer mode in homage to the Windows screensaver: a pipe for each track, growing across the area in heavy box characters as its notes play, the user's choice of 2026-11-10.

Each track that has played lays a pipe from a free place of its own: each note starting adds a few
cells to it, more for a louder note, which it lays at a pace set by the tempo, so that a busy track
grows quickly and a quiet one waits. A pipe goes straight, turns now and then and always when the
way ahead is taken, and its corners join properly; when it has nowhere to go it starts again from a
free place. Its head is the brightest, and what it laid dims a little with age. When most of the
area is pipe, everything fades over FADE_SECONDS and the area starts again empty, never at once.
It draws at the characters' own resolution. The amounts are named constants here, for the user to
tune by eye.
"""

import random

import numpy

from llamatron.visualizers.cells import SPACE, CellPainter
from llamatron.visualizers.colour import track_colour, vivid
from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.visualizer import Visualizer
from llamatron.strings.visualizers import MSG_PIPES

SEED = 1
LONGEST_FRAME_SECONDS = 0.2
FULL_VELOCITY = 127
# How a note grows a pipe: the cells it adds for the softest and the loudest note, and how many cells a pipe lays a second at 120 a minute.
FEWEST_CELLS = 1
MOST_CELLS = 5
CELLS_PER_SECOND = 24.0
# How a pipe turns: the chance it turns at each cell when it could go on.
TURN_CHANCE = 0.12
# How bright: the head, a fresh cell, and how much a cell dims a second, down to its dimmest.
HEAD_BRIGHTNESS = 1.0
LAID_BRIGHTNESS = 0.9
DIM_PER_SECOND = 0.02
DIMMEST = 0.55
# How full the area may get before it fades and starts again, as a share of its cells, and how long the fade takes.
FULL_SHARE = 0.6
FADE_SECONDS = 3.0
# The ways a pipe can go, as steps of rows and columns, and the heavy box character for each pair of sides a cell joins.
UP = (-1, 0)
DOWN = (1, 0)
LEFT = (0, -1)
RIGHT = (0, 1)
WAYS = (UP, DOWN, LEFT, RIGHT)
JOINS = {
    frozenset((LEFT, RIGHT)): '━', frozenset((UP, DOWN)): '┃', frozenset((DOWN, RIGHT)): '┏', frozenset((DOWN, LEFT)): '┓',
    frozenset((UP, RIGHT)): '┗', frozenset((UP, LEFT)): '┛',
}
# A pipe's end, before it has gone anywhere, and its head.
END = '╸'
COLOUR_STEP = 16


def opposite(way):
    return (-way[0], -way[1])


class Pipe:
    """One track's pipe: where its head is, which way it goes, the side it came in by, and the cells it still has to lay."""

    __slots__ = ('head', 'way', 'came_from', 'owed', 'progress')

    def __init__(self, *, head, way):
        self.head = head
        self.way = way
        self.came_from = None
        self.owed = 0.0
        # How far along the next cell the pipe's pace has brought it, so that a slow pace still lays cells over several frames.
        self.progress = 0.0


class Pipes(Visualizer):
    """A pipe for each track, laid in box characters as its notes play."""

    __slots__ = ('_rows', '_columns', '_pipes', '_characters', '_owners', '_ages', '_last', '_chooser', '_fading', '_cells')

    NAME = MSG_PIPES
    OPTION = 'pipes'

    def __init__(self):
        super().__init__()
        self._pipes = {}
        self._last = None
        self._chooser = random.Random(SEED)
        self._fading = None
        self._cells = CellPainter()
        self._rows = 0
        self._columns = 0

    def cleared(self, *, rows, columns):
        """Start the area empty at a size, every pipe to start again."""
        self._rows = rows
        self._columns = columns
        self._characters = [[SPACE] * columns for _ in range(rows)]
        self._owners = numpy.full((rows, columns), -1, dtype=numpy.int32)
        self._ages = numpy.zeros((rows, columns))
        self._pipes = {}
        self._fading = None

    def is_fading(self):
        """Return whether the area is fading to start again, for the tests."""
        return self._fading is not None

    def frame(self, *, width, height, now, heard=SILENCE):
        if not width or not height:
            return []
        if (height, width) != (self._rows, self._columns):
            self.cleared(rows=height, columns=width)
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        if self._fading is not None:
            self._fading += seconds
            if self._fading >= FADE_SECONDS:
                self.cleared(rows=height, columns=width)
        else:
            self.hear(heard)
            self.lay(seconds * heard.tempo_factor())
            if numpy.count_nonzero(self._owners >= 0) > FULL_SHARE * width * height:
                self._fading = 0.0
        self._ages += seconds
        return self.drawn()

    def free_place(self):
        """Return a free cell chosen at random, or None when there is none."""
        free = numpy.argwhere(self._owners < 0)
        if not len(free):
            return None
        row, column = free[self._chooser.randrange(len(free))]
        return int(row), int(column)

    def hear(self, heard):
        """Give each track that plays a pipe, and let each note that starts owe its pipe cells to lay, more for a louder note."""
        for note in heard.notes:
            if note.track not in self._pipes:
                place = self.free_place()
                if place is None:
                    continue
                self._pipes[note.track] = Pipe(head=place, way=self._chooser.choice(WAYS))
                self.put(place=place, track=note.track, character=END)
            if note.started:
                self._pipes[note.track].owed += FEWEST_CELLS + (MOST_CELLS - FEWEST_CELLS) * note.velocity / FULL_VELOCITY

    def lay(self, seconds):
        """Let each pipe lay the cells it owes, as many as its pace allows in the time."""
        for track, pipe in self._pipes.items():
            if pipe.owed < 1:
                pipe.progress = 0.0
                continue
            pipe.progress += CELLS_PER_SECOND * seconds
            steps = int(min(pipe.progress, pipe.owed))
            for _ in range(steps):
                self.step(track=track, pipe=pipe)
            pipe.progress -= steps
            pipe.owed -= steps

    def open_ways(self, head):
        """Return the ways a pipe can go from a cell: those whose next cell is inside the area and free."""
        ways = []
        for way in WAYS:
            row, column = head[0] + way[0], head[1] + way[1]
            if 0 <= row < self._rows and 0 <= column < self._columns and self._owners[row, column] < 0:
                ways.append(way)
        return ways

    def step(self, *, track, pipe):
        """Lay one cell: go on, or turn now and then and always when blocked, joining the cell left behind; start again elsewhere when there's nowhere to go."""
        ways = self.open_ways(pipe.head)
        if not ways:
            place = self.free_place()
            if place is not None:
                pipe.head, pipe.came_from = place, None
                self.put(place=place, track=track, character=END)
            return
        way = pipe.way if pipe.way in ways and self._chooser.random() >= TURN_CHANCE else self._chooser.choice(ways)
        sides = {way} if pipe.came_from is None else {way, pipe.came_from}
        self.put(place=pipe.head, track=track, character=JOINS.get(frozenset(sides), JOINS[frozenset((way, opposite(way)))]))
        pipe.head = (pipe.head[0] + way[0], pipe.head[1] + way[1])
        pipe.way = way
        pipe.came_from = opposite(way)
        self.put(place=pipe.head, track=track, character=JOINS[frozenset((way, opposite(way)))])

    def put(self, *, place, track, character):
        row, column = place
        self._characters[row][column] = character
        self._owners[row, column] = track
        self._ages[row, column] = 0.0

    def drawn(self):
        """Return the area as lines: each cell of pipe in its track's colour, dimming with age, the heads brightest, everything fading together when the area starts again."""
        brightness = numpy.maximum(LAID_BRIGHTNESS - DIM_PER_SECOND * self._ages, DIMMEST)
        for pipe in self._pipes.values():
            brightness[pipe.head] = HEAD_BRIGHTNESS
        if self._fading is not None:
            brightness = brightness * (1.0 - self._fading / FADE_SECONDS)
        palette = numpy.array([vivid(track_colour(track)) for track in range(max(int(self._owners.max()) + 1, 1))])
        colours = numpy.where((self._owners >= 0)[:, :, None], palette[numpy.maximum(self._owners, 0)] * brightness[:, :, None], 0)
        colours = (colours.astype(numpy.int32) // COLOUR_STEP) * COLOUR_STEP
        return self._cells.coloured_cells(characters=self._characters, colours=colours)
