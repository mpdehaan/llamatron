# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Where random numbers come from: a generator reseeded from a seed, or the program's own stream when there's none."""

import random


def random_source(seed):
    """Return what draws random numbers for a seed.

    With a seed it's a generator seeded from that alone, so the same seed always draws the same
    numbers and a render can be repeated. With none it's Python's own random module, which the
    system seeds once when the program starts, so every render is a new take.
    """
    return random if seed is None else random.Random(seed)


class SeededOnFirstDraw:
    """Draws random numbers from a seed as random.Random(seed) does, seeding the generator only when the first number is drawn: a
    clip prepares a stream for each of its random choices and almost never draws from them, about 24 draws in 25,900 streams across
    the examples, and seeding one costs about 7 microseconds."""

    __slots__ = ('_seed', '_generator')

    def __init__(self, seed):
        self._seed = seed
        self._generator = None

    def random(self):
        return self._drawing().random()

    def randrange(self, stop):
        return self._drawing().randrange(stop)

    def shuffle(self, items):
        self._drawing().shuffle(items)

    def _drawing(self):
        if self._generator is None:
            self._generator = random.Random(self._seed)
        return self._generator


def drawn_from_when_asked(seed):
    """Return what draws random numbers for a seed, as random_source does, seeding the generator only on the first draw."""
    return random if seed is None else SeededOnFirstDraw(seed)
