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

from llamatron.composition import file_format

# A whole note in seconds at a tempo of one beat a minute, a beat being a quarter note.
SECONDS_OF_A_WHOLE_AT_ONE_BPM = 240
# After every place at one moment, so that a step sees a set made at its own moment.
AFTER_EVERY_PLACE = float('inf')


class SceneClock:
    """One written scene's place in the song's time: where it starts in whole notes, and the seconds played at each of its tempo
    changes, so that any moment in it is turned into seconds with one search."""

    __slots__ = ('_start', '_times', '_seconds', '_tempos')

    def __init__(self, *, start, seconds_at_start, tempos):
        self._start = start
        self._times = [float(time) for time, _ in tempos]
        self._tempos = [float(tempo) for _, tempo in tempos]
        self._seconds = [seconds_at_start]
        for number in range(1, len(self._times)):
            self._seconds.append(self._seconds[-1] + (self._times[number] - self._times[number - 1]) * SECONDS_OF_A_WHOLE_AT_ONE_BPM / self._tempos[number - 1])

    def get_start(self):
        return self._start

    def seconds_at(self, time):
        """Return the seconds the song has played by a time in the scene, in whole notes from its start."""
        found = max(bisect_right(self._times, time) - 1, 0)
        return self._seconds[found] + (time - self._times[found]) * SECONDS_OF_A_WHOLE_AT_ONE_BPM / self._tempos[found]


class ModulatorClock:
    """Every modulator's value at a moment of the song, for one render.

    renderer answers where each written scene starts and how long it lasts, the tempos each plays at, and what its clips set the
    modulators to. Only the modulators the song changed from their defaults are worked out, a modulator of one value being a
    constant, and every scene's clock is made once, as far as the song is asked about, so that a step's values cost a few searches.
    """

    __slots__ = ('_renderer', '_seed', '_moving', '_constant', '_bar', '_sets', '_clocks', '_starts')

    def __init__(self, *, renderer, song, seed):
        self._renderer = renderer
        self._seed = seed
        changed = {name: song.get_modulator(name) for name in file_format.MODULATOR_NAMES if not song.get_modulator(name).is_default()}
        # A modulator whose minimum and maximum are one value never moves, whatever sets it, so it is a constant and no wave is worked out.
        self._constant = {name: modulator.get_minimum() for name, modulator in changed.items() if modulator.get_minimum() == modulator.get_maximum()}
        self._moving = {name: modulator for name, modulator in changed.items() if name not in self._constant}
        self._bar = float(song.get_time_signature().bar_length())
        # Each modulator's sets, as (time from the song's top, place, value), sorted, gathered scene by scene as far as asked.
        self._sets = {name: [] for name in self._moving}
        # Each written scene's clock by its number, and the starts of the scenes clocked so far, in order, to find a moment's scene.
        self._clocks = {}
        self._starts = []

    def is_moving(self):
        """Return whether any modulator of the song holds anything but 0, so that steps need its values at all."""
        return bool(self._moving or self._constant)

    def values_at(self, *, scene, time, place):
        """Return each modulator's value as a track at a place sees it at a time in a written scene, after its own set then."""
        if not self._moving:
            return self._constant
        clock = self._clock_of(scene)
        when = clock.get_start() + float(time)
        values = dict(self._constant)
        for name, modulator in self._moving.items():
            sets = self._sets[name]
            found = bisect_right(sets, (when, place, AFTER_EVERY_PLACE))
            origin, start = (sets[found - 1][0], sets[found - 1][2]) if found else (0.0, None)
            if modulator.counts_bars():
                cycles = (when - origin) / (self._bar * float(modulator.cycle_length()))
            else:
                cycles = (clock.seconds_at(when - clock.get_start()) - self._seconds_at(origin)) / float(modulator.cycle_length())
            values[name] = modulator.value_at(cycles=cycles, start=start, seed=self._seed, name=name, origin=origin)
        return values

    def _clock_of(self, scene):
        """Return a written scene's clock, making it and every earlier scene's first, which takes in what their clips set."""
        number = scene.get_number()
        if number not in self._clocks:
            scenes = self._renderer.get_scenes()
            for written in scenes[:scenes.index(scene) + 1]:
                if written.get_number() not in self._clocks:
                    self._add_clock(written)
        return self._clocks[number]

    def _add_clock(self, scene):
        start = float(self._renderer.scene_start(scene))
        seconds = 0.0
        if self._starts:
            before = self._clocks[self._starts[-1][1]]
            seconds = before.seconds_at(start - before.get_start())
        self._clocks[scene.get_number()] = SceneClock(start=start, seconds_at_start=seconds, tempos=self._renderer.tempos_in(scene))
        self._starts.append((start, scene.get_number()))
        for time, place, sets in self._renderer.modulator_sets_of(scene):
            for name, value in sets.items():
                if name in self._sets:
                    self._sets[name].append((start + float(time), place, value))
        for name in self._sets:
            self._sets[name].sort()

    def _seconds_at(self, when):
        """Return the seconds the song has played by a moment of a scene already clocked."""
        found = max(bisect_right(self._starts, (when, AFTER_EVERY_PLACE)) - 1, 0)
        clock = self._clocks[self._starts[found][1]]
        return clock.seconds_at(when - clock.get_start())
