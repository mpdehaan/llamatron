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
"""Drifts as the song plays: one process for each drift, for the whole song, which every clip naming it in its chain hears.

The user's design of 2026-11-11. A drift's clock runs from the top of the song, the scenes laid
end to end, and triggers every so often (its every, or a bar of the song's time signature). At
each trigger it picks new amounts and holds them until the next. Its position between its
versions A and B moves one step a trigger, over steps_to_b triggers, in its direction, always
starting at A: number values are blended between A's and B's by the position, and a choice, a
scale or a root, is B's with a chance equal to the position. What a trigger picks is worked out
once and kept, so every clip and both plays of a render hear the same drift.

The render reads it two ways: what the drifts a clip names add to the registers at their
triggers, which join the register timeline, and what they do to each step the clip plays, its
velocity, probability, degree and scale (DriftEffects).
"""

import math
import random
from typing import NamedTuple

from llamatron.composition.checks import in_whole_notes
from llamatron.composition.file_format import DriftDirection, GeneratorKind
from llamatron.composition.file_format import DriftValue, DriftVersion
from llamatron.composition.generator_settings import DRIFT_ADDS
from llamatron.support.random_source import random_source

# How a drift's own random numbers are seeded from the render's seed and its name, so that each drift draws its own.
DRIFT_SEED = '{seed}/drift/{name}'
NOTHING_ADDED = 0
FULL_CHANCE = 100
A_PLACE = 0


class DriftEffects(NamedTuple):
    """What the drifts a clip names do to one step: added to its velocity, its probability and its degree, and the scale and root that override the clip's, or None."""

    velocity: int
    probability: int
    degree: int
    scale: object
    root: object


NO_EFFECTS = DriftEffects(NOTHING_ADDED, NOTHING_ADDED, NOTHING_ADDED, None, None)


class Trigger(NamedTuple):
    """What one drift picked at one trigger: its blended numbers by value, its degree's random part, and its scale and root overrides, or None."""

    numbers: dict
    random_degree: int
    scale: object
    root: object


class DriftPlay:
    """Every drift of a song as it plays, worked out a trigger at a time and remembered."""

    __slots__ = ('_song', '_seed', '_bar', '_triggers', '_walks', '_choosers')

    def __init__(self, *, song, seed):
        self._song = song
        self._seed = seed
        self._bar = song.get_time_signature().bar_length()
        self._triggers = {}
        self._walks = {}
        self._choosers = {}

    def settings(self, name):
        return self._song.get_generator_settings(kind=GeneratorKind.DRIFT, name=name)

    def every(self, name):
        """Return how long one of a drift's triggers lasts, in whole notes."""
        written = self.settings(name).get_every()
        return self._bar if written is None else in_whole_notes(time=written, bar=self._bar)

    def trigger_at(self, *, name, time):
        """Return which trigger of a drift is current at a time from the song's top, counted from 0."""
        return math.floor(time / self.every(name))

    def trigger_times(self, *, name, start, end, origin=0):
        """Return the song times of a drift's triggers from start to before end, its clock starting at origin, a time from the song's top."""
        every = self.every(name)
        first = math.ceil((start - origin) / every)
        times = []
        place = first
        while origin + every * place < end:
            times.append(origin + every * place)
            place += 1
        return times

    def picked(self, *, name, trigger):
        """Return what a drift picked at a trigger, working it out the first time it's asked."""
        key = (name, trigger)
        if key not in self._triggers:
            self._triggers[key] = self._pick(name=name, trigger=trigger)
        return self._triggers[key]

    def adds_at(self, *, name, trigger):
        """Return what a drift adds to each register at a trigger, by register name, leaving out nothing added."""
        numbers = self.picked(name=name, trigger=trigger).numbers
        return {register: numbers[value] for register, value in DRIFT_ADDS.items() if numbers[value]}

    def effects(self, *, names, time, origins=None):
        """Return what the drifts named do to a step at a song time, their numbers added together and the last one's overrides winning.

        origins gives where each drift's clock starts, from the song's top, as its Restart says;
        a drift missing from it runs from the top.
        """
        if not names:
            return NO_EFFECTS
        velocity = probability = degree = NOTHING_ADDED
        scale = root = None
        for name in names:
            picked = self.picked(name=name, trigger=self.trigger_at(name=name, time=time - (origins or {}).get(name, 0)))
            velocity += picked.numbers[DriftValue.VELOCITY]
            probability += picked.numbers[DriftValue.PROBABILITY]
            degree += picked.numbers[DriftValue.DEGREE] + picked.random_degree
            scale = picked.scale or scale
            root = picked.root or root
        return DriftEffects(velocity, probability, degree, scale, root)

    def _chooser(self, name):
        """Return what draws a drift's random numbers: from its own seed, or else the render's with its name, or Python's own when neither has one."""
        if name not in self._choosers:
            own = self.settings(name).get_seed()
            if own is not None:
                self._choosers[name] = random.Random(own)
            else:
                self._choosers[name] = random_source(None if self._seed is None else DRIFT_SEED.format(seed=self._seed, name=name))
        return self._choosers[name]

    def position(self, *, name, trigger):
        """Return how far a drift is from A (0) toward B (1) at a trigger, by its direction."""
        settings = self.settings(name)
        steps = settings.get_steps_to_b()
        direction = settings.get_direction()
        if direction == DriftDirection.FORWARD:
            place = min(trigger, steps)
        elif direction == DriftDirection.LOOP:
            place = trigger % (steps + 1)
        elif direction == DriftDirection.PENDULUM:
            place = trigger % (2 * steps)
            place = place if place <= steps else 2 * steps - place
        else:
            place = self._walk(name=name, trigger=trigger, steps=steps)
        return place / steps

    def _walk(self, *, name, trigger, steps):
        """Return a brownian drift's place at a trigger: a step up or down from the one before, held between A and B."""
        walk = self._walks.setdefault(name, [A_PLACE])
        chooser = self._chooser(name)
        while len(walk) <= trigger:
            walk.append(min(max(walk[-1] + chooser.choice((-1, 1)), A_PLACE), steps))
        return walk[trigger]

    def _pick(self, *, name, trigger):
        settings = self.settings(name)
        position = self.position(name=name, trigger=trigger)
        chooser = self._chooser(name)
        numbers = {}
        for value in (*DRIFT_ADDS.values(), DriftValue.VELOCITY, DriftValue.PROBABILITY, DriftValue.DEGREE, DriftValue.DEGREE_RANDOM,
                      DriftValue.SCALE_PROBABILITY, DriftValue.ROOT_PROBABILITY):
            first = settings.get_value(version=DriftVersion.A, value=value) or NOTHING_ADDED
            second = settings.get_value(version=DriftVersion.B, value=value) or NOTHING_ADDED
            numbers[value] = round(first + (second - first) * position)
        spread = numbers[DriftValue.DEGREE_RANDOM]
        random_degree = chooser.randint(-spread, spread) if spread else NOTHING_ADDED
        scale = self._override(settings=settings, value=DriftValue.SCALE, chance=numbers[DriftValue.SCALE_PROBABILITY], position=position, chooser=chooser)
        root = self._override(settings=settings, value=DriftValue.ROOT, chance=numbers[DriftValue.ROOT_PROBABILITY], position=position, chooser=chooser)
        return Trigger(numbers, random_degree, scale, root)

    def _override(self, *, settings, value, chance, position, chooser):
        """Return the scale or root a trigger overrides with, or None: B's with a chance of the position, else A's, and only with the override's chance."""
        first = settings.get_value(version=DriftVersion.A, value=value)
        second = settings.get_value(version=DriftVersion.B, value=value)
        if first is None and second is None:
            return None
        choice = second if chooser.random() < position else first
        if choice is None or chooser.random() * FULL_CHANCE >= chance:
            return None
        return choice


def drifts_named(*, song, chain_names):
    """Return the names of the drifts the chains name, in order, from their steps."""
    names = []
    for chain in chain_names:
        for step in song.get_chain(chain).get_steps():
            if step.kind == GeneratorKind.DRIFT:
                names.append(step.name)
    return names
