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

"""The song's modulators as it plays: each one's whole value at any moment, the same for every track.

A modulator's wave starts at the song's top from its Start, and starts again from the value a step sets it to, at the step's
moment in the song. Its rate counts bars, which follow the time signature, or hertz, which count seconds through every tempo the
scenes play at, ramps included. What a step sees is worked out where the step is played, never ahead of time for the song.
"""

from bisect import bisect_right
from fractions import Fraction

from llamatron.composition import file_format

# A whole note in seconds at a tempo of one beat a minute, a beat being a quarter note.
SECONDS_OF_A_WHOLE_AT_ONE_BPM = 240


def exact(time):
    """Return a render's time, a Rational or a number, as a Fraction."""
    return Fraction(time.numerator, time.denominator) if hasattr(time, 'denominator') else Fraction(time)


class ModulatorClock:
    """Every modulator's value at a moment of the song, for one render.

    renderer answers where each written scene starts and how long it lasts, the tempos each plays at, and what its clips set the
    modulators to. Only the modulators the song changed from their defaults are worked out, since a default one stays at 0.
    """

    __slots__ = ('_renderer', '_song', '_seed', '_moving', '_constant', '_bar', '_sets', '_gathered', '_seconds_at_starts')

    def __init__(self, *, renderer, song, seed):
        self._renderer = renderer
        self._song = song
        self._seed = seed
        changed = {name: song.get_modulator(name) for name in file_format.MODULATOR_NAMES if not song.get_modulator(name).is_default()}
        # A modulator whose minimum and maximum are one value never moves, whatever sets it, so it is a constant and no wave is worked out.
        self._constant = {name: modulator.get_minimum() for name, modulator in changed.items() if modulator.get_minimum() == modulator.get_maximum()}
        self._moving = {name: modulator for name, modulator in changed.items() if name not in self._constant}
        self._bar = exact(song.get_time_signature().bar_length())
        # Each modulator's sets, as (time from the song's top, place, value), sorted, gathered scene by scene as far as asked.
        self._sets = {name: [] for name in self._moving}
        self._gathered = set()
        # How many seconds the song has played as each written scene starts, by its number, worked out once each.
        self._seconds_at_starts = {}

    def is_moving(self):
        """Return whether any modulator of the song holds anything but 0, so that steps need its values at all."""
        return bool(self._moving or self._constant)

    def values_at(self, *, scene, time, place):
        """Return each moving modulator's value as a track at a place sees it at a time in a written scene, after its own set then."""
        if not self._moving:
            return self._constant
        when = exact(self._renderer.scene_start(scene)) + exact(time)
        self._gather_through(scene)
        values = dict(self._constant)
        for name, modulator in self._moving.items():
            sets = self._sets[name]
            found = bisect_right(sets, (when, place, float('inf')))
            origin, start = (sets[found - 1][0], sets[found - 1][2]) if found else (Fraction(0), None)
            values[name] = modulator.value_at(cycles=self._cycles(modulator=modulator, origin=origin, when=when), start=start, seed=self._seed, name=name, origin=origin)
        return values

    def _cycles(self, *, modulator, origin, when):
        if modulator.counts_bars():
            return (when - origin) / (self._bar * modulator.cycle_length())
        return (self._seconds_at(when) - self._seconds_at(origin)) / modulator.cycle_length()

    def _gather_through(self, scene):
        """Take in what the clips of every written scene up to this one set the modulators to, once each."""
        for written in self._renderer.get_scenes()[:self._renderer.get_scenes().index(scene) + 1]:
            if written.get_number() in self._gathered:
                continue
            start = exact(self._renderer.scene_start(written))
            for time, place, sets in self._renderer.modulator_sets_of(written):
                for name, value in sets.items():
                    if name in self._sets:
                        self._sets[name].append((start + exact(time), place, value))
            for name in self._sets:
                self._sets[name].sort()
            self._gathered.add(written.get_number())

    def _seconds_at(self, when):
        """Return how many seconds the song has played by a moment, through every scene's tempos, ramps included."""
        scenes = self._renderer.get_scenes()
        for written in reversed(scenes):
            start = exact(self._renderer.scene_start(written))
            if start <= when:
                return self._seconds_at_start(written) + self._seconds_within(scene=written, upto=when - start)
        return Fraction(0)

    def _seconds_at_start(self, scene):
        number = scene.get_number()
        if number not in self._seconds_at_starts:
            scenes = self._renderer.get_scenes()
            place = scenes.index(scene)
            before = scenes[place - 1] if place else None
            self._seconds_at_starts[number] = Fraction(0) if before is None else self._seconds_at_start(before) + self._seconds_within(scene=before, upto=exact(self._renderer.get_scene_length(before)))
        return self._seconds_at_starts[number]

    def _seconds_within(self, *, scene, upto):
        """Return the seconds a written scene plays from its start to a time in it, at its tempos."""
        changes = [(exact(time), tempo) for time, tempo in self._renderer.tempos_in(scene)]
        seconds = Fraction(0)
        for number, (time, tempo) in enumerate(changes):
            end = changes[number + 1][0] if number + 1 < len(changes) else upto
            span = min(end, upto) - time
            if span > 0:
                seconds += span * SECONDS_OF_A_WHOLE_AT_ONE_BPM / Fraction(tempo)
        return seconds
