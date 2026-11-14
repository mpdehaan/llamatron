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
"""The lava lamp, the visualizer's first mode: colour blobs drifting and rippling over the clip area, the user's design of 2026-11-10.

In the user's words: big blocky pixels, like a rotozoomer drawn small and blown back up; mostly
primary-coloured blobs drifting around, one for each track, each sending ripples out as its notes
fire, thicker for longer notes, coloured by the pitch; the view turning and zooming gently with
the beat; the waves from different sources splashing and bouncing off each other like ripples in
water; vaguely a lava lamp, in the spirit of the early WinAmp visualizers, never muddy, never
overwhelming the music, and never flashing.

How it is made, from the shared pieces (fields.py, warp.py, colour.py), on a simulation SUPERSAMPLE
times finer than the big pixels each way:

- Each track that has played is a blob drifting on a slow path of its own, faster for a faster song.
- A note starting drops a splash into the water at its blob, as strong as its velocity, and a note
  still held keeps pushing a little every frame, so a long note sends a thicker train of waves
  without knowing in advance how long it is: the visualizer hears only notes that have started.
  A drum's splash is smaller and pale.
- Each blob glows its colour into a colour field, brighter as its track plays, which fades and
  bleeds into its neighbours every frame, so colours meet and mix.
- The picture is the colour field seen through the water: each cell takes its colour from a little
  way along the water's slope, and a soft highlight follows the slope, so the waves show as ripples
  in the colour.
- The view turns a little back and forth and zooms with a gentle pulse on each beat; then it is
  averaged down to the big pixels and held under the limiter, so nothing ever flashes.

The amounts are named constants here, grouped by what they shape, for the user to tune by eye.
"""

import math

import numpy

from llamatron.visualizers.colour import Limiter, note_colour
from llamatron.visualizers.fields import Discs, blurred, ripple_step
from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.visualizer import Visualizer
from llamatron.visualizers.warp import Rotozoom
from llamatron.strings.visualizers import MSG_LAVA_LAMP

# The derez: how much finer the simulation is than the big pixels, each way, and the colour steps the big pixels are rounded to.
SUPERSAMPLE = 2
COLOUR_STEP_SHIFT = 3
# Time: the longest a frame may count as, so that a stall doesn't jump everything, and the frame the per-frame amounts are reckoned at.
LONGEST_FRAME_SECONDS = 0.2
REFERENCE_FRAME_SECONDS = 0.05
# The water: how many steps it takes a frame, and how quickly its waves die away (a larger shift, slower).
WAVE_STEPS = 2
DAMPING_SHIFT = 5
# A note's splash: as a share of the field's height, its radius, and how deep it is for each point of velocity; a drum's is smaller and shallower.
SPLASH_RADIUS_SHARE = 0.09
SPLASH_PER_VELOCITY = 10
DRUM_RADIUS_SHARE = 0.05
DRUM_SPLASH_PER_VELOCITY = 6
# A held note keeps pushing every frame: its radius as a share of the field's height, and how hard for each point of velocity.
HELD_RADIUS_SHARE = 0.05
HELD_PUSH_PER_VELOCITY = 1
# How notes light their blob: how much a note at full velocity raises its energy, and how quickly the energy may rise and falls, per second, so that nothing jumps.
ENERGY_PER_NOTE = 0.45
ENERGY_RISE_PER_SECOND = 3.0
ENERGY_KEPT_PER_SECOND = 0.25
FULL_VELOCITY = 127
# The blobs' glow: its radius as a share of the field's height, how bright it is while its track rests and how much brighter at full energy, and the colour field's scale.
GLOW_RADIUS_SHARE = 0.16
GLOW_RESTING = 0.06
GLOW_PLAYING = 0.32
COLOUR_SCALE = 16
# How much of the colour field each frame keeps, out of 256, so that old colour fades.
COLOUR_KEPT = 246
COLOUR_KEPT_SHIFT = 8
# The drift: how far a blob wanders from the middle as a share of the field, how fast at 120 a minute, and how its path's speeds and phases vary by track.
DRIFT_REACH = 0.36
DRIFT_SPEED = 0.18
DRIFT_SPEEDS = (0.83, 1.0, 1.21, 0.71, 1.37, 0.93, 1.13)
DRIFT_PHASE = 2.39996
# Seeing through the water: how far the slope moves the colour (a larger shift, less), at most how many cells, and the highlight along the slope.
REFRACT_SHIFT = 6
REFRACT_MOST = 3
HIGHLIGHT_SHIFT = 5
HIGHLIGHT_MOST = 22
# The dark ground under everything.
GROUND = (6, 5, 14)
# The rotozoom: how far the view turns either way, in radians, and how long a swing takes in drift time; the zoom at rest, its pulse on each beat and how sharp the pulse is, and how much the playing swells it.
SWING = 0.10
SWING_PERIOD = 9.0
REST_ZOOM = 1.16
BEAT_PULSE = 0.025
PULSE_SHARPNESS = 6
ENERGY_SWELL = 0.03
# The limiter: the mean brightness held under, the ceiling no channel passes, how fast the mean may rise and fall, out of 255 a second, and the most it may lift a dim picture.
MEAN_LEVEL = 70.0
CEILING = 225
MEAN_RISE_PER_SECOND = 50.0
MEAN_FALL_PER_SECOND = 40.0
MOST_GAIN = 1.5
TURN = 2 * math.pi
HALF = 0.5


class Blob:
    """One track's blob: its energy, rising as its notes play and fading after, what that energy is moving toward, and the colour its last note painted."""

    __slots__ = ('energy', 'target', 'colour')

    def __init__(self, colour):
        self.energy = 0.0
        self.target = 0.0
        self.colour = colour


class LavaLamp(Visualizer):
    """Drifting blobs of colour, one for each track that plays, rippling the water they float in."""

    __slots__ = ('_rows', '_columns', '_water', '_water_before', '_colour', '_blobs', '_motion', '_last', '_discs', '_rotozoom', '_limiter', '_places')

    NAME = MSG_LAVA_LAMP
    OPTION = 'lava_lamp'

    def __init__(self):
        super().__init__()
        self._discs = Discs()
        self._rotozoom = Rotozoom()
        self._limiter = Limiter(
            mean_level=MEAN_LEVEL, ceiling=CEILING, rise_per_second=MEAN_RISE_PER_SECOND, fall_per_second=MEAN_FALL_PER_SECOND, most_gain=MOST_GAIN,
        )
        self._blobs = {}
        self._motion = 0.0
        self._last = None
        self.resized(columns=0, rows=0)

    def resized(self, *, columns, rows):
        """Start the water and the colour afresh for an area of this many big pixels."""
        self._rows = rows * SUPERSAMPLE
        self._columns = columns * SUPERSAMPLE
        shape = (self._rows, self._columns)
        self._water = numpy.zeros(shape, dtype=numpy.int32)
        self._water_before = numpy.zeros(shape, dtype=numpy.int32)
        self._colour = numpy.zeros((*shape, 3), dtype=numpy.int32)
        self._places = numpy.mgrid[0:self._rows, 0:self._columns]

    def radius(self, share):
        """Return a radius in simulation cells, a share of the field's height, at least one."""
        return max(int(self._rows * share), 1)

    def blob_place(self, track):
        """Return where a track's blob is now, as a row and a column of the simulation, on its slow path."""
        speeds = DRIFT_SPEEDS
        across = HALF + DRIFT_REACH * math.sin(self._motion * speeds[track % len(speeds)] + track * DRIFT_PHASE)
        down = HALF + DRIFT_REACH * math.sin(self._motion * speeds[(track + 3) % len(speeds)] * 0.8 + track * DRIFT_PHASE * 1.7)
        return int(down * (self._rows - 1)), int(across * (self._columns - 1))

    def pixels(self, *, now, heard=SILENCE):
        seconds = 0.0 if self._last is None else min(max(now - self._last, 0.0), LONGEST_FRAME_SECONDS)
        self._last = now
        self._motion += seconds * heard.tempo_factor() * DRIFT_SPEED
        self.hear(heard)
        self.settle(seconds)
        for _ in range(WAVE_STEPS):
            self._water, self._water_before = ripple_step(current=self._water, previous=self._water_before, damping_shift=DAMPING_SHIFT), self._water
        self.glow(seconds)
        picture = self.seen_through_water()
        energy = max((blob.energy for blob in self._blobs.values()), default=0.0)
        pulse = (HALF + HALF * math.cos(TURN * (heard.beats % 1.0))) ** PULSE_SHARPNESS
        angle = SWING * math.sin(TURN * self._motion / SWING_PERIOD)
        zoom = REST_ZOOM + BEAT_PULSE * pulse + ENERGY_SWELL * energy
        turned = self._rotozoom.sampled(picture=picture, angle=angle, zoom=zoom)
        small = derezzed(fine=turned, factor=SUPERSAMPLE)
        held = self._limiter.limited(picture=small, seconds=seconds)
        return (held >> COLOUR_STEP_SHIFT) << COLOUR_STEP_SHIFT

    def hear(self, heard):
        """Let each note heard splash or push at its track's blob, and raise the blob's energy for a note that started."""
        for note in heard.notes:
            colour = note_colour(track=note.track, pitch=note.pitch, drum=note.drum)
            blob = self._blobs.setdefault(note.track, Blob(colour))
            blob.colour = colour
            row, column = self.blob_place(note.track)
            if note.started:
                blob.target = min(blob.target + ENERGY_PER_NOTE * note.velocity / FULL_VELOCITY, 1.0)
                share, depth = (DRUM_RADIUS_SHARE, DRUM_SPLASH_PER_VELOCITY) if note.drum else (SPLASH_RADIUS_SHARE, SPLASH_PER_VELOCITY)
                self._discs.add(field=self._water, row=row, column=column, radius=self.radius(share), amount=depth * note.velocity)
            else:
                self._discs.add(field=self._water, row=row, column=column, radius=self.radius(HELD_RADIUS_SHARE), amount=HELD_PUSH_PER_VELOCITY * note.velocity)

    def settle(self, seconds):
        """Move each blob's energy toward its target no faster than it may rise, and let the target fall away."""
        kept = ENERGY_KEPT_PER_SECOND ** seconds
        rise = ENERGY_RISE_PER_SECOND * seconds
        for blob in self._blobs.values():
            blob.energy += max(-rise, min(rise, blob.target - blob.energy))
            blob.target *= kept

    def glow(self, seconds):
        """Fade the colour field and bleed it into its neighbours, then let each blob glow its colour into it, brighter as its track plays."""
        self._colour = blurred((self._colour * COLOUR_KEPT) >> COLOUR_KEPT_SHIFT)
        share = seconds / REFERENCE_FRAME_SECONDS
        radius = self.radius(GLOW_RADIUS_SHARE)
        for track, blob in self._blobs.items():
            row, column = self.blob_place(track)
            strength = (GLOW_RESTING + GLOW_PLAYING * blob.energy) * share
            self._discs.add(field=self._colour, row=row, column=column, radius=radius, amount=(blob.colour * COLOUR_SCALE * strength).astype(numpy.int32))

    def seen_through_water(self):
        """Return the colour field as seen through the water: each cell's colour taken a little way along the water's slope, with a soft highlight on the slope, over the dark ground."""
        padded = numpy.pad(self._water, 1, mode='edge')
        across = padded[1:-1, 2:] - padded[1:-1, :-2]
        down = padded[2:, 1:-1] - padded[:-2, 1:-1]
        rows, columns = self._places
        source_rows = numpy.clip(rows + numpy.clip(down >> REFRACT_SHIFT, -REFRACT_MOST, REFRACT_MOST), 0, self._rows - 1)
        source_columns = numpy.clip(columns + numpy.clip(across >> REFRACT_SHIFT, -REFRACT_MOST, REFRACT_MOST), 0, self._columns - 1)
        picture = self._colour[source_rows, source_columns] // COLOUR_SCALE
        highlight = numpy.clip(-down >> HIGHLIGHT_SHIFT, -HIGHLIGHT_MOST, HIGHLIGHT_MOST)
        return picture + highlight[:, :, None] + numpy.array(GROUND, dtype=numpy.int32)


def derezzed(*, fine, factor):
    """Return a fine picture averaged down by a factor in each direction, every big pixel the mean of the fine ones it covers."""
    rows = fine.shape[0] // factor * factor
    columns = fine.shape[1] // factor * factor
    blocks = fine[:rows, :columns].reshape(rows // factor, factor, columns // factor, factor, 3)
    return (blocks.sum(axis=(1, 3)) // (factor * factor)).astype(numpy.int32)
