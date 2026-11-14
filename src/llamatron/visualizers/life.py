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
"""Life, a visualizer mode: Conway's Game of Life over a drifting gradient that follows the music, the user's design of 2026-11-10.

The background is a diffuse gradient that drifts and turns, going between the colours of the tracks
heard, kept around the middle of bright so that it never glares, and brightening gently as the
tracks play. Each Life cell is two characters wide and one row tall, so that it is square: a live
cell is filled with the inverse of the gradient's colour beneath it, which differs from it by hue
more than by brightness, so that cells being born and dying never flash, and it is outlined in
Braille dots, a ring around the cell, which brighten gently with each beat. The grid follows the
classic rules, born with three neighbours and surviving with two or three, wrapping at the edges,
and steps on each beat, at most MOST_STEPS_PER_SECOND; each note starting seeds a few cells near
the column its pitch sets, and an empty grid is seeded afresh. The amounts are named constants here.
"""

import math
import random

import numpy

from llamatron.visualizers.cells import BRAILLE_BITS, BRAILLE_BLANK, SPACE, CellPainter, packed
from llamatron.visualizers.colour import TRACK_COLOURS, note_colour
from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.visualizer import Visualizer
from llamatron.strings.visualizers import MSG_LIFE

SEED = 1
LONGEST_FRAME_SECONDS = 0.2
FULL_VELOCITY = 127
LOWEST_PITCH = 28
HIGHEST_PITCH = 100
# A cell is this many characters wide and tall, so that it is square.
CELL_COLUMNS = 2
CELL_ROWS = 1
# Stepping: once a beat, and never more often than this.
MOST_STEPS_PER_SECOND = 3.0
# Seeding: how many cells a note at full velocity brings to life near its column, how far from it they fall, and the share of the grid a fresh seeding fills.
SEEDS_PER_NOTE = 5
SEED_REACH = 2
FRESH_SHARE = 0.18
# The gradient: how fast it drifts and turns, in turns a second at 120 a minute, its brightness around the middle of bright at rest and playing, and how strongly its colours come through.
DRIFT_PER_SECOND = 0.05
TURN_PER_SECOND = 0.02
RESTING_LEVEL = 0.45
PLAYING_LEVEL = 0.62
QUIET_COLOURS = (TRACK_COLOURS[1], TRACK_COLOURS[4])
WHOLE = 255
# The outline: its brightness beside the fill, and how much brighter on the beat, as sharp as this.
OUTLINE_LIFT = 1.25
BEAT_LIFT = 0.25
BEAT_SHARPNESS = 4
# The energy of the playing: how much a note raises it, how fast it may rise and how much is kept a second.
ENERGY_PER_NOTE = 0.25
ENERGY_RISE_PER_SECOND = 1.2
ENERGY_KEPT_PER_SECOND = 0.4
COLOUR_STEP = 16
CEILING = 225
# The Braille dots that outline a cell's left and right characters: the outer column of each and its top and bottom rows.
LEFT_RING = numpy.array([[1, 1], [1, 0], [1, 0], [1, 1]])
RIGHT_RING = numpy.array([[1, 1], [0, 1], [0, 1], [1, 1]])
NEIGHBOURS = [(down, across) for down in (-1, 0, 1) for across in (-1, 0, 1) if (down, across) != (0, 0)]


def stepped(alive):
    """Return the next generation of a grid of live cells by Conway's rules, the edges wrapping: born with three neighbours, surviving with two or three."""
    count = sum(numpy.roll(numpy.roll(alive, down, axis=0), across, axis=1) for down, across in NEIGHBOURS)
    return (count == 3) | (alive & (count == 2))


class Life(Visualizer):
    """Conway's Game of Life, its live cells the inverse of a drifting gradient, outlined with the beat."""

    __slots__ = ('_alive', '_colours', '_energy', '_target', '_drift', '_since_step', '_last', '_last_beat', '_chooser', '_cells', '_shape', '_left_bits', '_right_bits')

    NAME = MSG_LIFE
    OPTION = 'life'
    DARK_IN_SILENCE = False

    def __init__(self):
        super().__init__()
        self._chooser = random.Random(SEED)
        self._cells = CellPainter()
        self._colours = {}
        self._energy = 0.0
        self._target = 0.0
        self._drift = 0.0
        self._since_step = 0.0
        self._last = None
        self._last_beat = None
        self._shape = None
        self._left_bits = int((LEFT_RING * BRAILLE_BITS).sum())
        self._right_bits = int((RIGHT_RING * BRAILLE_BITS).sum())

    def alive(self):
        """Return the grid of live cells, for the tests."""
        return self._alive.copy()

    def seeded(self, *, rows, columns):
        """Return a fresh grid with FRESH_SHARE of its cells alive, at random."""
        return numpy.array([[self._chooser.random() < FRESH_SHARE for _ in range(columns)] for _ in range(rows)], dtype=bool)

    def frame(self, *, width, height, now, heard=SILENCE):
        rows = height // CELL_ROWS
        columns = width // CELL_COLUMNS
        if not rows or not columns:
            return []
        if self._shape != (rows, columns):
            self._shape = (rows, columns)
            self._alive = self.seeded(rows=rows, columns=columns)
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        tempo = heard.tempo_factor()
        self._drift += seconds * tempo
        self.hear(heard)
        rise = ENERGY_RISE_PER_SECOND * seconds
        self._energy += max(-rise, min(rise, self._target - self._energy))
        self._target *= ENERGY_KEPT_PER_SECOND ** seconds
        self._since_step += seconds
        beat = math.floor(heard.beats)
        if beat != self._last_beat and self._since_step >= 1.0 / MOST_STEPS_PER_SECOND:
            self._last_beat = beat
            self._since_step = 0.0
            self._alive = stepped(self._alive)
            if not self._alive.any():
                self._alive = self.seeded(rows=rows, columns=columns)
        return self.drawn(width=width, height=height, beats=heard.beats)

    def hear(self, heard):
        """Let each note heard bring its track's colour into the gradient, and each that starts seed a few cells near the column its pitch sets and raise the energy."""
        rows, columns = self._shape
        for note in heard.notes:
            self._colours[note.track] = note_colour(track=note.track, pitch=note.pitch, drum=note.drum)
            if not note.started:
                continue
            self._target = min(self._target + ENERGY_PER_NOTE * note.velocity / FULL_VELOCITY, 1.0)
            share = (min(max(note.pitch, LOWEST_PITCH), HIGHEST_PITCH) - LOWEST_PITCH) / (HIGHEST_PITCH - LOWEST_PITCH)
            column = int(share * (columns - 1))
            row = (note.track * 7) % rows
            for _ in range(max(int(SEEDS_PER_NOTE * note.velocity / FULL_VELOCITY), 1)):
                self._alive[(row + self._chooser.randint(-SEED_REACH, SEED_REACH)) % rows, (column + self._chooser.randint(-SEED_REACH, SEED_REACH)) % columns] = True

    def gradient(self, *, height, width):
        """Return the background as a colour for each character: a gradient between two of the tracks' colours, drifting and turning, around the middle of bright."""
        colours = [self._colours[track] for track in sorted(self._colours)] or list(QUIET_COLOURS)
        if len(colours) == 1:
            colours.append(QUIET_COLOURS[0])
        drift = self._drift * DRIFT_PER_SECOND
        first = numpy.array(colours[int(drift) % len(colours)], dtype=float)
        second = numpy.array(colours[(int(drift) + 1) % len(colours)], dtype=float)
        angle = math.tau * self._drift * TURN_PER_SECOND
        down, across = numpy.mgrid[0:height, 0:width].astype(float)
        along = ((across / max(width - 1, 1) - 0.5) * math.cos(angle) + (down / max(height - 1, 1) - 0.5) * math.sin(angle)) + 0.5
        share = numpy.clip(along + (drift % 1.0) - 0.5, 0.0, 1.0)[:, :, None]
        mixed = first * (1 - share) + second * share
        level = RESTING_LEVEL + (PLAYING_LEVEL - RESTING_LEVEL) * self._energy
        brightest = numpy.maximum(mixed.max(axis=2, keepdims=True), 1.0)
        return mixed / brightest * WHOLE * level

    def drawn(self, *, width, height, beats):
        """Return the lines: each character's background the gradient, or its inverse inside a live cell, with the cell's ring of dots in a brighter shade, brighter still on the beat."""
        background = self.gradient(height=height, width=width)
        rows, columns = self._shape
        live = numpy.zeros((height, width), dtype=bool)
        live[:rows * CELL_ROWS, :columns * CELL_COLUMNS] = numpy.repeat(numpy.repeat(self._alive, CELL_ROWS, axis=0), CELL_COLUMNS, axis=1)
        inverse = WHOLE * (RESTING_LEVEL + PLAYING_LEVEL) - background
        fills = numpy.where(live[:, :, None], inverse, background)
        pulse = (0.5 + 0.5 * math.cos(math.tau * (beats % 1.0))) ** BEAT_SHARPNESS
        outlines = inverse * (OUTLINE_LIFT + BEAT_LIFT * pulse)
        fills = numpy.clip(fills, 0, CEILING).astype(numpy.int32) // COLOUR_STEP * COLOUR_STEP
        outlines = numpy.clip(outlines, 0, CEILING).astype(numpy.int32) // COLOUR_STEP * COLOUR_STEP
        fill_rows = packed(fills).tolist()
        outline_rows = packed(outlines).tolist()
        lines = []
        for row in range(height):
            characters = []
            styles = []
            for column in range(width):
                fill = fill_rows[row][column]
                if live[row, column]:
                    bits = self._left_bits if column % CELL_COLUMNS == 0 else self._right_bits
                    characters.append(chr(BRAILLE_BLANK + bits))
                    styles.append(self._cells.packed_style(number=outline_rows[row][column], background=fill))
                else:
                    characters.append(SPACE)
                    styles.append(self._cells.packed_style(number=fill, background=fill))
            lines.append(self._cells.line(characters=characters, styles=styles))
        return lines
