# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""What moves a built-in instrument's Synth Controls while it plays: its LFOs, each worked out sample by sample a chunk at a
time, so that one at tens of hertz, a chip's vibrato, trill or wobbling pulse, moves smoothly and never in steps of a chunk.

Each chunk, before its voices play, the engine asks every instrument's modulation to advance: it sums its LFOs into an array
for each control they move, in that control's own unit: semitones for pitch, a share of the cycle for pulse width, octaves
for the first filter's cutoff, and a share of the oscillators' detune for detune spread. A voice reads the arrays as it
sounds. An LFO that retriggers starts its cycle again at each note. Speed rules this module, as it does the engine (the
user's yes).
"""

import math
import numpy

PITCH = 'pitch'
PULSE_WIDTH = 'pulse_width'
FILTER_CUTOFF = 'filter_cutoff'
DETUNE_SPREAD = 'detune_spread'
SINE = 'sine'
TRIANGLE = 'triangle'
SAW_UP = 'saw_up'
SAW_DOWN = 'saw_down'
SQUARE = 'square'
SAMPLE_AND_HOLD = 'sample_and_hold'
# How far each control moves at full depth, either way: an octave of pitch, two fifths of a pulse's cycle, four octaves of
# cutoff, and the oscillators' detune doubled or gone.
RANGES = {PITCH: 12.0, PULSE_WIDTH: 0.4, FILTER_CUTOFF: 4.0, DETUNE_SPREAD: 1.0}
# Sample and hold reads a table of random values, a new one each cycle, the same for every playing of the set.
HELD_VALUES = 4096
HELD_SEED = 224


class Lfo:
    """An LFO: the control it moves, its shape, its rate in hertz, its depth from -1 to 1 times the control's range, whether a
    note starts it again, and where it is in its cycle, counted in cycles."""

    __slots__ = ('target', 'shape', 'step', 'amount', 'retrigger', 'cycles', 'held')

    def __init__(self, *, spec, rate, held):
        self.target = spec['target']
        self.shape = spec['shape']
        self.step = spec['rate'] / rate
        self.amount = spec['depth'] * RANGES[self.target]
        self.retrigger = spec['retrigger']
        self.cycles = 0.0
        self.held = held

    def values(self, places):
        """Return the LFO over a chunk, places being 0 to the chunk's length, its depth applied, its cycle moving on past it."""
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
        return wave * self.amount


class LfoBank:
    """An instrument's LFOs, and what they gave the chunk now playing: an array for each control they move, now."""

    __slots__ = ('lfos', 'now')

    def __init__(self, *, lfos=(), rate=44100):
        held = numpy.random.default_rng(HELD_SEED).uniform(-1.0, 1.0, HELD_VALUES)
        self.lfos = [Lfo(spec=spec, rate=rate, held=held) for spec in lfos]
        self.now = {}

    def advance(self, places):
        """Work out what the LFOs give the chunk ahead, places being 0 to its length."""
        now = {}
        for lfo in self.lfos:
            values = lfo.values(places)
            if lfo.target in now:
                now[lfo.target] = now[lfo.target] + values
            else:
                now[lfo.target] = values
        self.now = now

    def note_on(self):
        """Start again every LFO that retriggers, as a note begins."""
        for lfo in self.lfos:
            if lfo.retrigger:
                lfo.cycles = 0.0


# What a patch that moves nothing holds.
NO_MODULATION = LfoBank()


def phases(*, phase, speeds):
    """Return the read positions of a chunk whose read speed changes each sample, from a phase, and the phase after it."""
    run = numpy.cumsum(speeds)
    return phase + run - speeds, phase + run[-1]
