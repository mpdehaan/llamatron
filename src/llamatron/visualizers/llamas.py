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
"""The llamas, a visualizer mode: an ASCII llama for each track that plays, strolling, bobbing and hopping, slowly changing colour, dimming and growing, the user's design of 2026-11-10.

Mildly in the feel of Winnie the Pooh's "Heffalumps and Woozles": a dreamy parade. Each llama
strolls across the area at its own pace, turning at the edges, bobbing as if dancing, and hops when
its track's notes start. Its colour drifts slowly around the colour wheel from its track's own
place on it; it dims while its track rests and brightens gently as it plays, never quickly, so that
nothing flashes; and it grows from small to medium to large with how much its track plays, never
changing size more often than SIZE_HOLD_SECONDS, so that it never flickers. It draws at the
characters' full resolution, not derezzed: the drawings are lines of text, mirrored to stroll the
other way, later tracks' llamas over earlier ones. The amounts are named constants here, for the
user to tune by eye.
"""

import colorsys
import math

from rich.color import Color
from rich.style import Style
from rich.text import Text

from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.visualizer import Visualizer
from llamatron.strings.visualizers import MSG_LLAMA_LARGE, MSG_LLAMA_MEDIUM, MSG_LLAMA_SMALL, MSG_LLAMAS

# The drawings, smallest first, each facing left, its head at the left, and mirrored to face right.
SIZES = (MSG_LLAMA_SMALL, MSG_LLAMA_MEDIUM, MSG_LLAMA_LARGE)
MIRRORED = str.maketrans('()/\\<>{}[]', ')(\\/><}{][')
# How a llama moves: its stroll in columns a second at 120 a minute, varying by track, its bob in rows and how many bobs a beat, and its hop in rows after a note starts and how fast the hop settles.
STROLL_SPEEDS = (3.0, 4.2, 2.4, 5.1, 3.6, 2.9, 4.6)
BOB_ROWS = 0.6
BOBS_PER_BEAT = 0.5
HOP_ROWS = 1.5
HOP_KEPT_PER_SECOND = 0.02
# How a llama lights: its brightness at rest and at full energy, from 0 to 1, how fast its energy may rise toward its target and how much of the target is kept a second, and how much a note at full velocity raises the target.
RESTING_BRIGHTNESS = 0.32
PLAYING_BRIGHTNESS = 0.9
ENERGY_RISE_PER_SECOND = 1.5
ENERGY_KEPT_PER_SECOND = 0.4
ENERGY_PER_NOTE = 0.35
FULL_VELOCITY = 127
# Its colour: how saturated, how far around the wheel its track starts, and how fast it drifts, in turns a second.
SATURATION = 0.7
TRACK_HUE_STEP = 0.13
HUE_DRIFT_PER_SECOND = 0.02
# Its size: the energy above which it grows a size and below which it shrinks one, and the least time between two changes.
GROW_ABOVE = 0.55
SHRINK_BELOW = 0.2
SIZE_HOLD_SECONDS = 2.0
# Colours are rounded to steps of this, out of 255, so that styles are reused.
COLOUR_STEP = 8
LONGEST_FRAME_SECONDS = 0.2
SPACE = ' '
WHOLE = 255


def mirrored(drawing):
    """Return a drawing facing the other way: each line padded to the drawing's width, reversed, its brackets and slashes turned."""
    width = max(len(line) for line in drawing)
    return tuple(line.ljust(width)[::-1].translate(MIRRORED) for line in drawing)


class Llama:
    """One track's llama: where it is, which way it strolls, its energy, hop and size, and when its size last changed."""

    __slots__ = ('column', 'facing', 'row', 'energy', 'target', 'hop', 'size', 'since_resize')

    def __init__(self, *, column, row):
        self.column = column
        self.row = row
        self.facing = 1
        self.energy = 0.0
        self.target = 0.0
        self.hop = 0.0
        self.size = 0
        self.since_resize = SIZE_HOLD_SECONDS


class Llamas(Visualizer):
    """A parade of ASCII llamas, one for each track that plays."""

    __slots__ = ('_llamas', '_last', '_motion', '_styles', '_drawings')

    NAME = MSG_LLAMAS
    OPTION = 'llamas'

    def __init__(self):
        super().__init__()
        self._llamas = {}
        self._last = None
        self._motion = 0.0
        self._styles = {}
        self._drawings = {(size, facing): (mirrored(drawing) if facing > 0 else drawing) for size, drawing in enumerate(SIZES) for facing in (1, -1)}

    def llama_count(self):
        """Return how many llamas there are: one for each track that has played."""
        return len(self._llamas)

    def llama_of(self, track):
        """Return a track's llama, or None before the track has played."""
        return self._llamas.get(track)

    def frame(self, *, width, height, now, heard=SILENCE):
        if not width or not height:
            return []
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        tempo = heard.tempo_factor()
        self._motion += seconds * tempo
        self.hear(heard=heard, width=width, height=height)
        self.move(seconds=seconds, tempo=tempo, width=width)
        return self.drawn(width=width, height=height, now=now, beats=heard.beats)

    def hear(self, *, heard, width, height):
        """Bring each track that plays its llama, and let each note that starts raise its energy and make it hop."""
        for note in heard.notes:
            llama = self._llamas.get(note.track)
            if llama is None:
                llama = Llama(column=(note.track * 17) % max(width, 1), row=(note.track * 5) % max(height, 1))
                self._llamas[note.track] = llama
            if note.started:
                llama.target = min(llama.target + ENERGY_PER_NOTE * note.velocity / FULL_VELOCITY, 1.0)
                llama.hop = HOP_ROWS

    def move(self, *, seconds, tempo, width):
        """Stroll each llama on, turning it at the edges, let its hop settle, move its energy toward its target no faster than it may rise while the target fades, and grow or shrink it when its energy says and its size has held long enough."""
        kept = ENERGY_KEPT_PER_SECOND ** seconds
        rise = ENERGY_RISE_PER_SECOND * seconds
        settled = HOP_KEPT_PER_SECOND ** seconds
        for track, llama in self._llamas.items():
            drawing_width = max(len(line) for line in SIZES[llama.size])
            llama.column += llama.facing * STROLL_SPEEDS[track % len(STROLL_SPEEDS)] * tempo * seconds
            if llama.column < 0 or llama.column + drawing_width > width:
                llama.facing = -llama.facing
                llama.column = min(max(llama.column, 0), max(width - drawing_width, 0))
            llama.hop *= settled
            llama.energy += max(-rise, min(rise, llama.target - llama.energy))
            llama.target *= kept
            llama.since_resize += seconds
            if llama.since_resize >= SIZE_HOLD_SECONDS:
                wanted = llama.size + (llama.energy > GROW_ABOVE) - (llama.energy < SHRINK_BELOW)
                wanted = min(max(wanted, 0), len(SIZES) - 1)
                if wanted != llama.size:
                    llama.size = wanted
                    llama.since_resize = 0.0

    def colour_of(self, *, track, llama, now):
        """Return a llama's style: its colour drifting around the wheel from its track's place, as bright as its energy allows, rounded so that styles are reused."""
        hue = (track * TRACK_HUE_STEP + now * HUE_DRIFT_PER_SECOND) % 1.0
        brightness = RESTING_BRIGHTNESS + (PLAYING_BRIGHTNESS - RESTING_BRIGHTNESS) * min(llama.energy, 1.0)
        red, green, blue = (int(channel * WHOLE) // COLOUR_STEP * COLOUR_STEP for channel in colorsys.hsv_to_rgb(hue, SATURATION, brightness))
        key = (red, green, blue)
        if key not in self._styles:
            self._styles[key] = Style(color=Color.from_rgb(red, green, blue))
        return self._styles[key]

    def drawn(self, *, width, height, now, beats):
        """Return the area as lines of text, each llama's drawing laid over the ones before it, at its place, bob and hop."""
        cells = [[SPACE] * width for _ in range(height)]
        styles = [[None] * width for _ in range(height)]
        for track, llama in self._llamas.items():
            drawing = self._drawings[(llama.size, llama.facing)]
            style = self.colour_of(track=track, llama=llama, now=now)
            bob = BOB_ROWS * math.sin(math.tau * BOBS_PER_BEAT * beats + track)
            top = int(round(min(llama.row, max(height - len(drawing), 0)) + bob - llama.hop))
            left = int(llama.column)
            for down, line in enumerate(drawing):
                row = top + down
                if not 0 <= row < height:
                    continue
                for across, character in enumerate(line):
                    column = left + across
                    if character != SPACE and 0 <= column < width:
                        cells[row][column] = character
                        styles[row][column] = style
        return [self.line_of(characters=cells[row], styles=styles[row]) for row in range(height)]

    @staticmethod
    def line_of(*, characters, styles):
        """Return one line of characters as text, each run of one style one piece."""
        text = Text(no_wrap=True)
        start = 0
        for place in range(1, len(characters) + 1):
            if place == len(characters) or styles[place] is not styles[start]:
                text.append(''.join(characters[start:place]), style=styles[start])
                start = place
        return text
