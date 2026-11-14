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

"""Digital rain: green streams of ones and zeros falling down the screen, the user's design after the film The Matrix.

Each column of characters holds a one or a zero, and a few change every frame, as the code in the
film does; only the glyphs change, never the brightness. A note starting sends a stream down from
the top in the column of its pitch, low at the left, its head pale green and as bright as the note is
loud, its tail fading behind it; the streams fall STREAM_ROWS_PER_BEAT rows a beat, each a little
faster or slower, so that the rain keeps to the tempo. The whole green brightens as more plays and
settles back, gently, and a sparse dim rain keeps falling in silence. It draws only in green, the
heads never white. The amounts are named constants here, for the user to tune.
"""

import random

import numpy

from llamatron.visualizers.cells import CellPainter
from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.visualizer import Visualizer
from llamatron.strings.visualizers import MSG_DIGITAL_RAIN, MSG_RAIN_DIGITS

SEED = 1
LONGEST_FRAME_SECONDS = 0.2
FULL_VELOCITY = 127
LOWEST_PITCH = 24
HIGHEST_PITCH = 96
# The streams: how many rows a beat they fall, how much faster or slower one may be, how long a tail is, as a share of the height, how far either way a note's column varies, and the most at once.
STREAM_ROWS_PER_BEAT = 3.0
SPEED_SPREAD = 0.35
SHORTEST_TAIL = 0.2
LONGEST_TAIL = 0.6
COLUMN_SPREAD = 2
MOST_STREAMS = 500
# How bright a note's stream is for the softest and the loudest note, and a stream of the rain that falls by itself.
SOFTEST_STREAM = 0.55
QUIET_STREAM = 0.3
# How many streams fall by themselves a second, for each column, and how much of the glyphs change a second.
QUIET_STREAMS_PER_COLUMN = 0.06
GLYPH_CHANGES_PER_SECOND = 0.5
# How the tail fades from the head: a power over one makes it fade sooner.
TAIL_FADE_POWER = 1.6
# The colours: the head pale green, the tail green, both never past the ceiling.
HEAD_COLOUR = (150, 255, 150)
TAIL_COLOUR = (20, 255, 60)
CEILING = 230
COLOUR_STEP = 8
# How the playing brightens the green: at rest, playing, what a note at full velocity adds, and how fast it rises and falls back.
RESTING_BRIGHTNESS = 0.7
PLAYING_BRIGHTNESS = 1.0
ENERGY_PER_NOTE = 0.2
ENERGY_RISE_PER_SECOND = 1.5
ENERGY_KEPT_PER_SECOND = 0.4
BEATS_PER_SECOND_AT_120 = 2.0


class DigitalRain(Visualizer):
    """Green ones and zeros falling, a stream for each note."""

    __slots__ = ('_cells', '_chooser', '_rows', '_columns', '_glyphs', '_streams', '_last', '_energy', '_target', '_owed')

    NAME = MSG_DIGITAL_RAIN
    OPTION = 'digital_rain'
    DARK_IN_SILENCE = False

    def __init__(self):
        super().__init__()
        self._cells = CellPainter()
        self._chooser = random.Random(SEED)
        self._rows = 0
        self._columns = 0
        self._glyphs = []
        # Each stream is a row of: its column, its head's row, its speed in rows a beat, its tail's length in rows and its brightness.
        self._streams = numpy.zeros((0, 5))
        self._last = None
        self._energy = 0.0
        self._target = 0.0
        self._owed = 0.0

    def cleared(self, *, rows, columns):
        """Start again at a size: every cell a one or a zero, and no streams."""
        self._rows = rows
        self._columns = columns
        self._glyphs = [[self._chooser.choice(MSG_RAIN_DIGITS) for _ in range(columns)] for _ in range(rows)]
        self._streams = numpy.zeros((0, 5))

    def stream_count(self):
        """Return how many streams are falling, for the tests."""
        return len(self._streams)

    def frame(self, *, width, height, now, heard=SILENCE):
        if not width or not height:
            return []
        if (height, width) != (self._rows, self._columns):
            self.cleared(rows=height, columns=width)
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        self.hear(heard)
        self.fall_quietly(seconds)
        rise = ENERGY_RISE_PER_SECOND * seconds
        self._energy += max(-rise, min(rise, self._target - self._energy))
        self._target *= ENERGY_KEPT_PER_SECOND ** seconds
        beats = seconds * BEATS_PER_SECOND_AT_120 * heard.tempo_factor()
        if len(self._streams):
            self._streams[:, 1] += self._streams[:, 2] * beats
            self._streams = self._streams[self._streams[:, 1] - self._streams[:, 3] < self._rows]
        self.change_glyphs(seconds)
        return self._cells.coloured_cells(characters=self._glyphs, colours=self.colours())

    def hear(self, heard):
        """Send a stream down for each note that starts, in the column of its pitch, and let it brighten the green."""
        for note in heard.notes:
            if note.started:
                loudness = note.velocity / FULL_VELOCITY
                height = min(max((note.pitch - LOWEST_PITCH) / (HIGHEST_PITCH - LOWEST_PITCH), 0.0), 1.0)
                column = round(height * (self._columns - 1)) + self._chooser.randint(-COLUMN_SPREAD, COLUMN_SPREAD)
                self.send(column=min(max(column, 0), self._columns - 1), brightness=SOFTEST_STREAM + (1.0 - SOFTEST_STREAM) * loudness)
                self._target = min(self._target + ENERGY_PER_NOTE * loudness, 1.0)

    def fall_quietly(self, seconds):
        """Send down the streams of the rain that falls by itself, dim, in columns chosen at random."""
        self._owed += QUIET_STREAMS_PER_COLUMN * self._columns * seconds
        while self._owed >= 1.0:
            self._owed -= 1.0
            self.send(column=self._chooser.randrange(self._columns), brightness=QUIET_STREAM)

    def send(self, *, column, brightness):
        """Start a stream at the top of a column, a little faster or slower than the rest, with a tail of its own length."""
        speed = STREAM_ROWS_PER_BEAT * (1.0 + self._chooser.uniform(-SPEED_SPREAD, SPEED_SPREAD))
        tail = max(self._rows * self._chooser.uniform(SHORTEST_TAIL, LONGEST_TAIL), 2.0)
        stream = numpy.array([[column, 0.0, speed, tail, brightness]])
        self._streams = numpy.concatenate([self._streams, stream])[-MOST_STREAMS:]

    def change_glyphs(self, seconds):
        """Turn a few cells' ones to zeros and zeros to ones."""
        for _ in range(int(GLYPH_CHANGES_PER_SECOND * self._rows * self._columns * seconds)):
            row = self._chooser.randrange(self._rows)
            column = self._chooser.randrange(self._columns)
            self._glyphs[row][column] = self._chooser.choice(MSG_RAIN_DIGITS)

    def colours(self):
        """Return each cell's colour: black, a tail's green fading from its head, or a head's pale green, brighter as more plays."""
        levels = numpy.zeros((self._rows, self._columns))
        heads = numpy.zeros((self._rows, self._columns))
        rows = numpy.arange(self._rows)
        for column, head, _, tail, brightness in self._streams:
            behind = head - rows
            inside = (behind >= 0) & (behind < tail)
            level = numpy.where(inside, brightness * numpy.clip(1.0 - behind / tail, 0.0, 1.0) ** TAIL_FADE_POWER, 0.0)
            levels[:, int(column)] = numpy.maximum(levels[:, int(column)], level)
            head_row = int(head)
            if 0 <= head_row < self._rows:
                heads[head_row, int(column)] = max(heads[head_row, int(column)], brightness)
        brightness = RESTING_BRIGHTNESS + (PLAYING_BRIGHTNESS - RESTING_BRIGHTNESS) * self._energy
        colours = levels[:, :, None] * numpy.array(TAIL_COLOUR) * brightness
        colours = numpy.where((heads > 0)[:, :, None], heads[:, :, None] * numpy.array(HEAD_COLOUR) * brightness, colours)
        return (numpy.clip(colours, 0, CEILING).astype(numpy.int32) // COLOUR_STEP) * COLOUR_STEP


