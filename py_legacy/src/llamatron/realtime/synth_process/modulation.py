# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A built-in instrument's LFOs, each worked out sample by sample a chunk at a time, so that one at tens of hertz, a chip's
vibrato, trill or wobbling pulse, moves smoothly and never in steps of a chunk.

Each chunk, before its voices play, the engine asks every instrument's LFOs to advance: each gives an array from -1 to 1 over
the chunk, which the instrument's mod matrix routes to what it moves at the slot's amount (matrix.py). An LFO that is off
gives None. An LFO that retriggers starts its cycle again at each note, and one that restarts each scene at each scene. Speed
rules this module, as it does the engine (the user's yes).
"""

import math
import numpy

SINE = 'sine'
TRIANGLE = 'triangle'
SAW_UP = 'saw_up'
SAW_DOWN = 'saw_down'
SQUARE = 'square'
SAMPLE_AND_HOLD = 'sample_and_hold'
# Sample and hold reads a table of random values, a new one each cycle, the same for every playing of the set.
HELD_VALUES = 4096
HELD_SEED = 224


class Lfo:
    """An LFO: its shape, its rate in hertz, whether a note starts it again and whether each scene does, and where it is in
    its cycle, counted in cycles."""

    __slots__ = ('shape', 'step', 'retrigger', 'each_scene', 'cycles', 'held')

    def __init__(self, *, spec, rate, held):
        self.shape = spec['shape']
        self.step = spec['rate'] / rate
        self.retrigger = spec['retrigger']
        self.each_scene = spec.get('each_scene', False)
        self.cycles = 0.0
        self.held = held

    def values(self, places):
        """Return the LFO over a chunk from -1 to 1, places being 0 to the chunk's length, its cycle moving on past it."""
        cycles = self.cycles + self.step * places
        self.cycles = (self.cycles + self.step * len(places)) % len(self.held)
        if self.shape == SAMPLE_AND_HOLD:
            wave = self.held[cycles.astype(numpy.int64) % len(self.held)]
        else:
            place = cycles % 1.0
            if self.shape == SINE:
                wave = numpy.sin(2.0 * math.pi * place)
            elif self.shape == TRIANGLE:
                wave = 1.0 - 4.0 * numpy.abs(place - 0.5)
            elif self.shape == SAW_UP:
                wave = 2.0 * place - 1.0
            elif self.shape == SAW_DOWN:
                wave = 1.0 - 2.0 * place
            else:
                wave = numpy.where(place < 0.5, 1.0, -1.0)
        return wave


class LfoBank:
    """An instrument's four LFOs, None for one that is off, and what they gave the chunk now playing: an array each, or None,
    now."""

    __slots__ = ('lfos', 'now')

    def __init__(self, *, lfos=(), rate=44100):
        held = numpy.random.default_rng(HELD_SEED).uniform(-1.0, 1.0, HELD_VALUES)
        self.lfos = []
        for spec in lfos:
            lfo = None
            if spec is not None:
                lfo = Lfo(spec=spec, rate=rate, held=held)
            self.lfos.append(lfo)
        self.now = [None] * len(self.lfos)

    def is_on(self):
        """Return whether any LFO is on, so that an instrument with none skips the work."""
        return any(lfo is not None for lfo in self.lfos)

    def advance(self, places):
        """Work out what the LFOs give the chunk ahead, places being 0 to its length."""
        self.now = [None if lfo is None else lfo.values(places) for lfo in self.lfos]

    def note_on(self):
        """Start again every LFO that retriggers, as a note begins."""
        for lfo in self.lfos:
            if lfo is not None and lfo.retrigger:
                lfo.cycles = 0.0

    def scene_started(self):
        """Start again every LFO that restarts each scene, as the instrument's clip starts with its scene."""
        for lfo in self.lfos:
            if lfo is not None and lfo.each_scene:
                lfo.cycles = 0.0


# What a patch that moves nothing holds.
NO_MODULATION = LfoBank()


def phases(*, phase, speeds):
    """Return the read positions of a chunk whose read speed changes each sample, from a phase, and the phase after it."""
    run = numpy.cumsum(speeds)
    return phase + run - speeds, phase + run[-1]
