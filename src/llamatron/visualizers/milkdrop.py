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
"""MilkDrop, a visualizer mode in the spirit of Ryan Geiss's plugin: a feedback picture that trails and swirls, with the notes drawn new on top.

Each frame the last picture is warped, zoomed in a little and turned about the middle with a swirl
that turns the middle faster than the edges, blurred a touch and faded, and then each note heard
is drawn into it in its track's colour: a soft splash where a note starts, as strong as its
velocity, and a dot that keeps glowing while a note is held, the tracks spread around a slowly turning circle by
their places and the notes along it by pitch. So everything a track plays streams outward and
twists into trails. The warp's zoom and turn breathe slowly with the beat. It is worked out at
SUPERSAMPLE times the big pixels each way and averaged down, and held under the limiter so that it
never flashes. The amounts are named constants here, for the user to tune by eye.
"""

import math

import numpy

from llamatron.visualizers.colour import Limiter, note_colour
from llamatron.visualizers.fields import Discs, blurred
from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.lava_lamp import derezzed
from llamatron.visualizers.visualizer import Visualizer
from llamatron.strings.visualizers import MSG_MILKDROP

# The derez: how much finer the picture is than the big pixels, each way, and the colour steps the big pixels are rounded to.
SUPERSAMPLE = 2
COLOUR_STEP_SHIFT = 3
LONGEST_FRAME_SECONDS = 0.2
REFERENCE_FRAME_SECONDS = 0.05
# The feedback: how much of the picture each frame keeps, out of 256, the zoom each frame, and the turn and the swirl's extra turn at the middle, in radians a frame at 120 a minute.
KEPT = 238
KEPT_SHIFT = 8
WHOLE_KEPT = 256
ZOOM = 1.035
TURN = 0.012
SWIRL = 0.05
# How the warp breathes with the beat: its zoom grows by this share at each beat's top, as sharp as this.
BEAT_BREATH = 0.012
BREATH_SHARPNESS = 4
# Where the notes are drawn: on a circle this share of the area's height from the middle, which turns this many radians a second at 120 a minute, the tracks spread around it and each track's notes along an arc of this many radians by pitch.
CIRCLE_SHARE = 0.32
CIRCLE_TURN_PER_SECOND = 0.35
PITCH_ARC = 1.2
LOWEST_PITCH = 24
HIGHEST_PITCH = 108
# A note starting: a splash of this radius as a share of the height, as bright as its velocity times this; a held note: a dot of this radius, this bright.
RING_RADIUS_SHARE = 0.08
RING_BRIGHTNESS = 2.2
DOT_RADIUS_SHARE = 0.05
DOT_BRIGHTNESS = 1.1
FULL_VELOCITY = 127
# The picture's colour scale, so that fades keep whole numbers.
COLOUR_SCALE = 16
# The limiter: the mean brightness held under, the ceiling, how fast the mean may rise and fall, out of 255 a second, and the most it may lift a dim picture.
MEAN_LEVEL = 60.0
CEILING = 225
MEAN_RISE_PER_SECOND = 45.0
MEAN_FALL_PER_SECOND = 40.0
MOST_GAIN = 1.3
FULL_TURN = 2 * math.pi
HALF = 0.5


class Milkdrop(Visualizer):
    """A picture fed back into itself, zoomed, turned and swirled, faded and blurred, with each note drawn new on top."""

    __slots__ = ('_rows', '_columns', '_picture', '_discs', '_limiter', '_last', '_motion', '_warp_key', '_warp_rows', '_warp_columns', '_tracks_seen')

    NAME = MSG_MILKDROP
    OPTION = 'milkdrop'

    def __init__(self):
        super().__init__()
        self._discs = Discs()
        self._limiter = Limiter(
            mean_level=MEAN_LEVEL, ceiling=CEILING, rise_per_second=MEAN_RISE_PER_SECOND, fall_per_second=MEAN_FALL_PER_SECOND, most_gain=MOST_GAIN,
        )
        self._last = None
        self._motion = 0.0
        self._tracks_seen = 1
        self.resized(columns=0, rows=0)

    def resized(self, *, columns, rows):
        self._rows = rows * SUPERSAMPLE
        self._columns = columns * SUPERSAMPLE
        self._picture = numpy.zeros((self._rows, self._columns, 3), dtype=numpy.int32)
        self._warp_key = None

    def warp(self, zoom):
        """Return where each cell of the next picture comes from in the last, as row and column indexes: zoomed in by zoom and turned, the middle more than the edges, worked out again only when the zoom moves."""
        key = round(zoom, 3)
        if key != self._warp_key:
            self._warp_key = key
            rows, columns = numpy.mgrid[0:self._rows, 0:self._columns].astype(numpy.float32)
            middle_row = (self._rows - 1) / 2
            middle_column = (self._columns - 1) / 2
            down = rows - middle_row
            across = columns - middle_column
            reach = numpy.hypot(down, across) / max(middle_row, middle_column, 1.0)
            angle = TURN + SWIRL * numpy.clip(1.0 - reach, 0.0, 1.0)
            cosine = numpy.cos(angle) / zoom
            sine = numpy.sin(angle) / zoom
            self._warp_rows = numpy.clip(numpy.rint(down * cosine - across * sine + middle_row), 0, self._rows - 1).astype(numpy.intp)
            self._warp_columns = numpy.clip(numpy.rint(down * sine + across * cosine + middle_column), 0, self._columns - 1).astype(numpy.intp)
        return self._warp_rows, self._warp_columns

    def pixels(self, *, now, heard=SILENCE):
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        self._motion += seconds * heard.tempo_factor()
        breath = (HALF + HALF * math.cos(FULL_TURN * (heard.beats % 1.0))) ** BREATH_SHARPNESS
        rows, columns = self.warp(ZOOM + BEAT_BREATH * breath)
        # What a frame keeps, reckoned for the time it really took, so that the trails last as long whatever the frame rate.
        kept = int(WHOLE_KEPT * (KEPT / WHOLE_KEPT) ** (seconds / REFERENCE_FRAME_SECONDS)) if seconds else KEPT
        self._picture = blurred((self._picture[rows, columns] * kept) >> KEPT_SHIFT)
        self.draw_notes(heard)
        small = derezzed(fine=self._picture // COLOUR_SCALE, factor=SUPERSAMPLE)
        held = self._limiter.limited(picture=small, seconds=seconds)
        return (held >> COLOUR_STEP_SHIFT) << COLOUR_STEP_SHIFT

    def draw_notes(self, heard):
        """Draw each note heard into the picture: a splash where it starts and a dot while it is held, on the turning circle at its track's place and its pitch's."""
        if not heard.notes:
            return
        self._tracks_seen = max(self._tracks_seen, max(note.track for note in heard.notes) + 1)
        radius = CIRCLE_SHARE * self._rows
        for note in heard.notes:
            pitch_share = (min(max(note.pitch, LOWEST_PITCH), HIGHEST_PITCH) - LOWEST_PITCH) / (HIGHEST_PITCH - LOWEST_PITCH)
            angle = CIRCLE_TURN_PER_SECOND * self._motion + FULL_TURN * note.track / self._tracks_seen + PITCH_ARC * (pitch_share - HALF)
            row = int((self._rows - 1) / 2 + radius * math.sin(angle))
            column = int((self._columns - 1) / 2 + radius * 2 * math.cos(angle))
            colour = note_colour(track=note.track, pitch=note.pitch, drum=note.drum) * COLOUR_SCALE
            loudness = note.velocity / FULL_VELOCITY
            if note.started:
                self._discs.add(field=self._picture, row=row, column=column, radius=max(int(self._rows * RING_RADIUS_SHARE), 1),
                                amount=(colour * RING_BRIGHTNESS * loudness).astype(numpy.int32))
            else:
                self._discs.add(field=self._picture, row=row, column=column, radius=max(int(self._rows * DOT_RADIUS_SHARE), 1),
                                amount=(colour * DOT_BRIGHTNESS * loudness).astype(numpy.int32))
