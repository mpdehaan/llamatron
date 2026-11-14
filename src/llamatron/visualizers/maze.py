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
"""Maze, a visualizer mode in homage to the Windows 3D Maze, seen from above: a maze in box characters, with a walker for each track threading its corridors as its notes play, the user's choice of 2026-11-10.

The maze is made afresh for the area by a random depth-first carving, its walls drawn dim in the
light box characters that join properly at every corner and tee. Each track that has played is a
walker in its track's colour that wanders the corridors, going on into new ones where it can and
turning back at dead ends, a few steps for each note it starts, at a pace set by the tempo, leaving
a trail that fades. When the walkers have trodden most of the maze, it fades over FADE_SECONDS and a
new one is made. It draws at the characters' own resolution. The amounts are named constants here.
"""

import random

import numpy

from llamatron.visualizers.cells import SPACE, CellPainter
from llamatron.visualizers.colour import track_colour, vivid
from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.visualizer import Visualizer
from llamatron.strings.visualizers import MSG_MAZE

SEED = 1
LONGEST_FRAME_SECONDS = 0.2
FULL_VELOCITY = 127
# How a note moves a walker: the steps it adds for the softest and the loudest note, and how many steps a walker takes a second at 120 a minute.
FEWEST_STEPS = 1
MOST_STEPS = 4
STEPS_PER_SECOND = 14.0
# The trail: how bright a fresh step is, how much it dims a second and down to what, and the walker's own brightness and mark.
TRAIL_BRIGHTNESS = 0.95
TRAIL_DIM_PER_SECOND = 0.05
TRAIL_DIMMEST = 0.5
WALKER_BRIGHTNESS = 1.0
WALKER = '●'
TRAIL = '•'
# The walls' colour, dim, and how much of the maze may be trodden before it fades and a new one is made, and how long the fade takes.
WALL_COLOUR = (72, 68, 108)
TRODDEN_SHARE = 0.7
FADE_SECONDS = 3.0
COLOUR_STEP = 16
# The light box characters for a wall cell, by which of its four sides join other walls: up, down, left, right.
WALL_JOINS = {
    (0, 0, 0, 0): '·', (1, 0, 0, 0): '│', (0, 1, 0, 0): '│', (1, 1, 0, 0): '│', (0, 0, 1, 0): '─', (0, 0, 0, 1): '─', (0, 0, 1, 1): '─',
    (0, 1, 0, 1): '┌', (0, 1, 1, 0): '┐', (1, 0, 0, 1): '└', (1, 0, 1, 0): '┘', (1, 1, 0, 1): '├', (1, 1, 1, 0): '┤', (0, 1, 1, 1): '┬',
    (1, 0, 1, 1): '┴', (1, 1, 1, 1): '┼',
}
STEPS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def carved(*, rows, columns, chooser):
    """Return a maze for an area of this many rows and columns of characters, as a grid of booleans true for a wall, carved by a random depth-first walk between the odd places.

    Carving needs an odd number of rows and columns, so an even area's last row or column is left
    out of the maze, neither wall nor corridor (inside() says which places are the maze).
    """
    walls = numpy.zeros((rows, columns), dtype=bool)
    walls[:odd_size(rows), :odd_size(columns)] = True
    rows = odd_size(rows)
    columns = odd_size(columns)
    if rows < 3 or columns < 3:
        return walls
    start = (1, 1)
    walls[start] = False
    stack = [start]
    while stack:
        row, column = stack[-1]
        choices = [(row + 2 * down, column + 2 * across, down, across) for down, across in STEPS
                   if 0 < row + 2 * down < rows - 1 and 0 < column + 2 * across < columns - 1 and walls[row + 2 * down, column + 2 * across]]
        if not choices:
            stack.pop()
            continue
        next_row, next_column, down, across = chooser.choice(choices)
        walls[row + down, column + across] = False
        walls[next_row, next_column] = False
        stack.append((next_row, next_column))
    return walls


def odd_size(size):
    """Return the largest odd size no larger than a size, which a maze can fill."""
    return size if size % 2 else size - 1


def inside(*, rows, columns):
    """Return which places of an area are the maze, all but an even area's last row or column."""
    places = numpy.zeros((rows, columns), dtype=bool)
    places[:odd_size(rows), :odd_size(columns)] = True
    return places


class Walker:
    """One track's walker: where it is, the way it came, the steps it still has to take, and how far along the next its pace has brought it."""

    __slots__ = ('place', 'path', 'owed', 'progress')

    def __init__(self, place):
        self.place = place
        self.path = [place]
        self.owed = 0.0
        self.progress = 0.0


class Maze(Visualizer):
    """A maze in box characters, threaded by a walker for each track."""

    __slots__ = ('_rows', '_columns', '_walls', '_corridors', '_wall_characters', '_trodden', '_ages', '_owners', '_walkers', '_last', '_chooser', '_fading', '_cells')

    NAME = MSG_MAZE
    OPTION = 'maze'

    def __init__(self):
        super().__init__()
        self._chooser = random.Random(SEED)
        self._last = None
        self._cells = CellPainter()
        self._rows = 0
        self._columns = 0

    def made(self, *, rows, columns):
        """Make a new maze for an area of this size, with no walkers and nothing trodden."""
        self._rows = rows
        self._columns = columns
        self._walls = carved(rows=rows, columns=columns, chooser=self._chooser)
        self._corridors = inside(rows=rows, columns=columns) & ~self._walls
        self._wall_characters = self.wall_characters()
        self._trodden = numpy.zeros((rows, columns), dtype=bool)
        self._ages = numpy.zeros((rows, columns))
        self._owners = numpy.zeros((rows, columns), dtype=numpy.int32)
        self._walkers = {}
        self._fading = None

    def wall_characters(self):
        """Return each wall cell's box character, joining the walls beside it, and blanks for the corridors."""
        padded = numpy.pad(self._walls, 1, constant_values=False)
        characters = []
        for row in range(self._rows):
            line = []
            for column in range(self._columns):
                if not self._walls[row, column]:
                    line.append(SPACE)
                    continue
                sides = (padded[row, column + 1], padded[row + 2, column + 1], padded[row + 1, column], padded[row + 1, column + 2])
                line.append(WALL_JOINS[tuple(int(side) for side in sides)])
            characters.append(line)
        return characters

    def walker_count(self):
        """Return how many walkers there are: one for each track that has played."""
        return len(self._walkers)

    def frame(self, *, width, height, now, heard=SILENCE):
        if not width or not height:
            return []
        if (height, width) != (self._rows, self._columns):
            self.made(rows=height, columns=width)
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        self._ages += seconds
        if self._fading is not None:
            self._fading += seconds
            if self._fading >= FADE_SECONDS:
                self.made(rows=height, columns=width)
        else:
            self.hear(heard)
            self.walk(seconds * heard.tempo_factor())
            corridors = numpy.count_nonzero(self._corridors)
            if corridors and numpy.count_nonzero(self._trodden) > TRODDEN_SHARE * corridors:
                self._fading = 0.0
        return self.drawn()

    def hear(self, heard):
        """Give each track that plays a walker in a corridor, and let each note that starts owe its walker steps, more for a louder note."""
        for note in heard.notes:
            if note.track not in self._walkers:
                corridors = numpy.argwhere(self._corridors)
                if not len(corridors):
                    continue
                row, column = corridors[self._chooser.randrange(len(corridors))]
                self._walkers[note.track] = Walker((int(row), int(column)))
            if note.started:
                self._walkers[note.track].owed += FEWEST_STEPS + (MOST_STEPS - FEWEST_STEPS) * note.velocity / FULL_VELOCITY

    def walk(self, seconds):
        """Let each walker take the steps it owes, as many as its pace allows: into an untrodden corridor where it can, and back the way it came otherwise."""
        for track, walker in self._walkers.items():
            if walker.owed < 1:
                walker.progress = 0.0
                continue
            walker.progress += STEPS_PER_SECOND * seconds
            steps = int(min(walker.progress, walker.owed))
            for _ in range(steps):
                self.step(track=track, walker=walker)
            walker.progress -= steps
            walker.owed -= steps

    def step(self, *, track, walker):
        row, column = walker.place
        open_ways = [(row + down, column + across) for down, across in STEPS
                     if 0 <= row + down < self._rows and 0 <= column + across < self._columns and self._corridors[row + down, column + across]]
        fresh = [place for place in open_ways if not self._trodden[place]]
        if fresh:
            walker.place = self._chooser.choice(fresh)
            walker.path.append(walker.place)
        elif len(walker.path) > 1:
            walker.path.pop()
            walker.place = walker.path[-1]
        elif open_ways:
            walker.place = self._chooser.choice(open_ways)
        self._trodden[walker.place] = True
        self._ages[walker.place] = 0.0
        self._owners[walker.place] = track

    def drawn(self):
        """Return the area as lines: the walls dim, the trails in their tracks' colours dimming with age, and the walkers bright, everything fading when a new maze is coming."""
        characters = [list(line) for line in self._wall_characters]
        colours = numpy.zeros((self._rows, self._columns, 3))
        colours[self._walls] = WALL_COLOUR
        trail = numpy.maximum(TRAIL_BRIGHTNESS - TRAIL_DIM_PER_SECOND * self._ages, TRAIL_DIMMEST)
        palette = numpy.array([vivid(track_colour(track)) for track in range(max(int(self._owners.max()) + 1, 1))])
        colours = numpy.where(self._trodden[:, :, None], palette[self._owners] * trail[:, :, None], colours)
        for row, column in numpy.argwhere(self._trodden):
            characters[row][column] = TRAIL
        for track, walker in self._walkers.items():
            characters[walker.place[0]][walker.place[1]] = WALKER
            colours[walker.place] = vivid(track_colour(track)) * WALKER_BRIGHTNESS
        if self._fading is not None:
            colours = colours * (1.0 - self._fading / FADE_SECONDS)
        colours = (colours.astype(numpy.int32) // COLOUR_STEP) * COLOUR_STEP
        return self._cells.coloured_cells(characters=characters, colours=colours)
