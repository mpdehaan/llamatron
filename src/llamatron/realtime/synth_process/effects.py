# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The effects an instrument's four blocks hold, each applied to the instrument's mix a chunk at a time, keeping what it
needs from one chunk to the next, so that nothing restarts at a chunk's edge, and each blended into what came before it by its
Mix. A filter is in filters.py.

The bitcrusher holds each sample for as long as its rate gives, by a phase that runs on across chunks, then rounds to its
bits. Drive shapes the mix by a curve: soft and warm saturate, warm leaning to one side for even harmonics, hard clips,
fold folds back past full scale and wrap wraps round, the last two the harsh digital sounds of cheap grooveboxes. Speed rules
this module, as it does the engine (the user's yes).
"""

import math
import numpy

from llamatron.realtime.synth_process.filters import Filter

BITCRUSH = 'bitcrush'
DRIVE = 'drive'
FILTER = 'filter'
SOFT = 'soft'
WARM = 'warm'
HARD = 'hard'
FOLD = 'fold'
WRAP = 'wrap'
# How much gain drive's amount reaches at full: twenty times for the saturating curves, four for fold and wrap, which
# turn harsh fast.
MOST_GAIN = 20.0
MOST_FOLDING_GAIN = 4.0
# How far warm drive leans to one side before it saturates, which gives it its even harmonics.
WARM_LEAN = 0.3


class SoundEffect:
    """What every effect but the filter (filters.py, which does the same itself) does beside shaping a chunk: note when a note starts, which only a filter's envelope needs, and how
    much of it is mixed in, from 0 to 1."""

    __slots__ = ('mix',)

    def __init__(self, *, mix=1.0):
        self.mix = mix

    def note_on(self, *, sample, pitch):
        """Do nothing: only a filter's envelope fires on a note."""


class Bitcrush(SoundEffect):
    """The bitcrusher: its bits, 16 for none, and the rate it holds samples at, 0 for none, with the phase of its hold and
    the sample it holds, carried from chunk to chunk."""

    __slots__ = ('levels', 'step', 'phase', 'held')

    def __init__(self, *, bits, hold_rate, rate, mix=1.0):
        super().__init__(mix=mix)
        self.levels = 0
        if bits < 16:
            self.levels = 2 ** (bits - 1)
        self.step = 0.0
        if 0 < hold_rate < rate:
            self.step = hold_rate / rate
        self.phase = 0.0
        self.held = 0.0

    def apply(self, buffer, *, start=0):
        if self.step:
            buffer = self._held(buffer)
        if self.levels:
            buffer = numpy.round(buffer * self.levels) / self.levels
        return buffer

    def _held(self, buffer):
        """Return the buffer with each sample held until the hold's phase passes its next whole number, the phase and the
        held sample running on into the next chunk."""
        count = len(buffer)
        phases = self.phase + self.step * numpy.arange(1, count + 1)
        ticks = numpy.floor(phases)
        taken = numpy.empty(count, dtype=bool)
        taken[0] = ticks[0] > math.floor(self.phase)
        taken[1:] = ticks[1:] > ticks[:-1]
        places = numpy.where(taken, numpy.arange(count), -1)
        numpy.maximum.accumulate(places, out=places)
        out = numpy.where(places >= 0, buffer[numpy.maximum(places, 0)], numpy.float32(self.held))
        self.phase = phases[-1] - math.floor(phases[-1])
        self.held = float(out[-1])
        return out.astype(numpy.float32)


class Drive(SoundEffect):
    """Drive: its curve and its gain from its amount."""

    __slots__ = ('curve', 'gain', 'scale', 'offset')

    def __init__(self, *, curve, amount, mix=1.0):
        super().__init__(mix=mix)
        self.curve = curve
        most = MOST_FOLDING_GAIN if curve in (FOLD, WRAP) else MOST_GAIN
        self.gain = 1.0 + amount * most
        self.offset = 0.0
        self.scale = 1.0 / math.tanh(self.gain)
        if curve == WARM:
            # Leaning before the curve and taking the lean's own level away again leaves silence silent; the scale is the
            # larger of the two extremes, so that the curve reaches full scale on one side and stays under it on the other.
            self.offset = math.tanh(WARM_LEAN)
            self.scale = 1.0 / max(math.tanh(self.gain + WARM_LEAN) - self.offset, self.offset - math.tanh(WARM_LEAN - self.gain))

    def apply(self, buffer, *, start=0):
        driven = buffer * self.gain
        if self.curve == SOFT:
            return numpy.tanh(driven) * self.scale
        if self.curve == WARM:
            return (numpy.tanh(driven + WARM_LEAN) - self.offset) * self.scale
        if self.curve == HARD:
            return numpy.clip(driven, -1.0, 1.0)
        if self.curve == FOLD:
            return numpy.sin(driven * (math.pi / 2.0))
        return (driven + 1.0) % 2.0 - 1.0


def compiled_effects(*, effects, rate):
    """Return an instrument's effects in order, compiled from their settings as llamatron gives them (model/objects/built_in_sound.py)."""
    compiled = []
    for effect in effects:
        kind = effect['effect']
        if kind == BITCRUSH:
            compiled.append(Bitcrush(bits=effect['bits'], hold_rate=effect['rate'], rate=rate, mix=effect['mix']))
        elif kind == DRIVE:
            compiled.append(Drive(curve=effect['curve'], amount=effect['amount'], mix=effect['mix']))
        elif kind == FILTER:
            compiled.append(Filter(spec=effect, rate=rate))
    return compiled


def through_effects(*, buffer, effects, start):
    """Return an instrument's mix through its effects in order, each blended into what came before by its Mix, as float32; the
    chunk's first sample is start."""
    for effect in effects:
        shaped = effect.apply(buffer, start=start)
        if effect.mix < 1.0:
            shaped = buffer + (shaped - buffer) * effect.mix
        buffer = shaped
    return buffer.astype(numpy.float32, copy=False)
