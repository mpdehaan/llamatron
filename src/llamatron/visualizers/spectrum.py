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
"""The spectrum analyser, a visualizer mode in the spirit of WinAmp's own: bars across the clip area rising with the notes heard and falling after, with peak caps that hang and drop.

It hears notes rather than sound, so a bar is a band of pitches, low at the left and high at the
right, and a note lifts its band by its velocity as it starts, holds it up a little while it is
held, and lets it fall at a steady rate when it ends. Each bar is drawn at the characters' own
resolution, its top an eighth block (`▁` to `█`), so that it rises smoothly in eight steps a row,
coloured up its height from green through yellow to red as WinAmp's were, held under a ceiling so
that it never glares. A cap above each bar marks its highest recent level, hangs a moment and
drops slowly. The amounts are named constants here, for the user to tune by eye.
"""

import numpy
from rich.color import Color
from rich.style import Style
from rich.text import Text

from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.visualizer import Visualizer
from llamatron.strings.visualizers import MSG_SPECTRUM

# The bars: each this many columns wide with a gap of this many after it, and the pitches they span, low to high.
BAR_COLUMNS = 2
GAP_COLUMNS = 1
LOWEST_PITCH = 28
HIGHEST_PITCH = 100
# How a note moves its band: how high a note at full velocity lifts it, as a share of the area's height, how high a held note keeps it, and how fast a band rises toward its level and falls, as shares of the height a second.
LIFT_AT_FULL_VELOCITY = 0.9
HELD_SHARE = 0.55
RISE_PER_SECOND = 9.0
FALL_PER_SECOND = 0.9
FULL_VELOCITY = 127
# A note also lifts the bands either side of its own a little, as a sound spreads across a spectrum, by this share for each band away, so many bands either side.
SPREAD_SHARE = 0.45
SPREAD_BANDS = 2
# The caps: how long one hangs at a band's highest level before it drops, and how fast it drops, as a share of the height a second.
CAP_HANG_SECONDS = 0.5
CAP_FALL_PER_SECOND = 0.35
CAP_CHARACTER = '▀'
CAP_COLOUR = (200, 200, 210)
# The colours up a bar's height, from the bottom, as WinAmp's were, kept under the ceiling so they never glare.
GRADIENT = ((40, 190, 80), (230, 205, 50), (225, 70, 45))
# The longest a frame may count as, so that a stall doesn't drop every bar at once.
LONGEST_FRAME_SECONDS = 0.2
# A bar's top, by how many eighths of its top row it fills.
EIGHTHS = ' ▁▂▃▄▅▆▇█'
FULL_ROW = 8
SPACE = ' '


def bands_across(width):
    """Return how many bars fit across a width of columns, each with its gap, at least one."""
    return max(width // (BAR_COLUMNS + GAP_COLUMNS), 1)


def gradient_colour(height):
    """Return the colour at a height up a bar, from 0 at the bottom to 1 at the top, through the gradient's colours."""
    place = min(max(height, 0.0), 1.0) * (len(GRADIENT) - 1)
    lower = min(int(place), len(GRADIENT) - 2)
    share = place - lower
    return tuple(int(low + (high - low) * share) for low, high in zip(GRADIENT[lower], GRADIENT[lower + 1]))


class Spectrum(Visualizer):
    """Bars of bands of pitches, rising with the notes heard and falling after, with caps that hang and drop."""

    __slots__ = ('_levels', '_targets', '_caps', '_cap_ages', '_last', '_row_styles', '_cap_style')

    NAME = MSG_SPECTRUM
    OPTION = 'spectrum'

    def __init__(self):
        super().__init__()
        self._last = None
        self._row_styles = {}
        self._cap_style = Style(color=Color.from_rgb(*CAP_COLOUR))
        self.resized(columns=0, rows=0)

    def resized(self, *, columns, rows):
        self.reset(bands=bands_across(columns * BAR_COLUMNS))

    def reset(self, *, bands):
        """Start every band, and its cap, at nothing, for an area this many bands across."""
        self._levels = numpy.zeros(bands)
        self._targets = numpy.zeros(bands)
        self._caps = numpy.zeros(bands)
        self._cap_ages = numpy.zeros(bands)

    def band_of(self, pitch):
        """Return the band a pitch falls in, low pitches at the left."""
        share = (min(max(pitch, LOWEST_PITCH), HIGHEST_PITCH) - LOWEST_PITCH) / (HIGHEST_PITCH - LOWEST_PITCH)
        return min(int(share * len(self._levels)), len(self._levels) - 1)

    def frame(self, *, width, height, now, heard=SILENCE):
        if bands_across(width) != len(self._levels):
            self.reset(bands=bands_across(width))
        if not width or not height:
            return []
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        self.hear(heard)
        self.settle(seconds)
        return self.drawn(width=width, height=height)

    def hear(self, heard):
        """Lift each band a note falls in, and those either side a little: by its velocity as it starts, and to the held level while it sounds."""
        for note in heard.notes:
            lift = LIFT_AT_FULL_VELOCITY * note.velocity / FULL_VELOCITY if note.started else HELD_SHARE * note.velocity / FULL_VELOCITY
            band = self.band_of(note.pitch)
            for away in range(-SPREAD_BANDS, SPREAD_BANDS + 1):
                if 0 <= band + away < len(self._targets):
                    self._targets[band + away] = max(self._targets[band + away], lift * SPREAD_SHARE ** abs(away))

    def settle(self, seconds):
        """Move each band toward its target, rising quickly and falling steadily, and let the caps hang, then drop."""
        rising = self._targets > self._levels
        self._levels = numpy.where(rising, numpy.minimum(self._targets, self._levels + RISE_PER_SECOND * seconds), numpy.maximum(self._levels - FALL_PER_SECOND * seconds, 0.0))
        self._targets = numpy.zeros_like(self._targets)
        higher = self._levels >= self._caps
        self._caps = numpy.where(higher, self._levels, self._caps)
        self._cap_ages = numpy.where(higher, 0.0, self._cap_ages + seconds)
        dropping = self._cap_ages > CAP_HANG_SECONDS
        self._caps = numpy.where(dropping, numpy.maximum(self._caps - CAP_FALL_PER_SECOND * seconds, self._levels), self._caps)

    def row_style(self, *, row, rows):
        """Return the style of a bar's cells on a row counted from the bottom, made once for each row of each height."""
        key = (row, rows)
        if key not in self._row_styles:
            self._row_styles[key] = Style(color=Color.from_rgb(*gradient_colour(row / max(rows - 1, 1))))
        return self._row_styles[key]

    def drawn(self, *, width, height):
        """Return the bars as lines, top line first, each bar's top an eighth block and its cap above it."""
        eighths = (numpy.minimum(self._levels, 1.0) * height * FULL_ROW).astype(int)
        caps = numpy.minimum((self._caps * height).astype(int), height - 1)
        lines = []
        for line in range(height):
            row = height - 1 - line
            text = Text(no_wrap=True)
            style = self.row_style(row=row, rows=height)
            for band, filled in enumerate(eighths):
                beneath = filled - row * FULL_ROW
                if beneath > 0:
                    text.append(EIGHTHS[min(beneath, FULL_ROW)] * BAR_COLUMNS, style=style)
                elif caps[band] == row and self._caps[band] > 0:
                    text.append(CAP_CHARACTER * BAR_COLUMNS, style=self._cap_style)
                else:
                    text.append(SPACE * BAR_COLUMNS)
                text.append(SPACE * GAP_COLUMNS)
            text.truncate(width)
            text.pad_right(max(width - text.cell_len, 0))
            lines.append(text)
        return lines
