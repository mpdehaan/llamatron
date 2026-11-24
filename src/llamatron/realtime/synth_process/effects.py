# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The effects an instrument's four blocks hold, each applied to the instrument's mix a chunk at a time, keeping what it
needs from one chunk to the next, so that nothing restarts at a chunk's edge.

The bitcrusher holds each sample for as long as its rate gives, by a phase that runs on across chunks, then rounds to its
bits. Drive shapes the mix by a curve: soft and warm saturate, warm leaning to one side for even harmonics, hard clips,
fold folds back past full scale and wrap wraps round, the last two the harsh digital sounds of cheap grooveboxes. Speed rules
this module, as it does the engine (the user's yes).
"""

import math
import numpy

BITCRUSH = 'bitcrush'
DRIVE = 'drive'
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


class Bitcrush:
    """The bitcrusher: its bits, 16 for none, and the rate it holds samples at, 0 for none, with the phase of its hold and
    the sample it holds, carried from chunk to chunk."""

    __slots__ = ('levels', 'step', 'phase', 'held')

    def __init__(self, *, bits, hold_rate, rate):
        self.levels = 0
        if bits < 16:
            self.levels = 2 ** (bits - 1)
        self.step = 0.0
        if 0 < hold_rate < rate:
            self.step = hold_rate / rate
        self.phase = 0.0
        self.held = 0.0

    def apply(self, buffer):
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


class Drive:
    """Drive: its curve and its gain from its amount."""

    __slots__ = ('curve', 'gain', 'scale', 'offset')

    def __init__(self, *, curve, amount):
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

    def apply(self, buffer):
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
    """Return an instrument's effects in order, compiled from (kind, settings...) as the set gives them."""
    compiled = []
    for effect in effects:
        if effect[0] == BITCRUSH:
            compiled.append(Bitcrush(bits=effect[1], hold_rate=effect[2], rate=rate))
        elif effect[0] == DRIVE:
            compiled.append(Drive(curve=effect[1], amount=effect[2]))
    return compiled


def through_effects(*, buffer, effects):
    """Return an instrument's mix through its effects in order, as float32."""
    for effect in effects:
        buffer = effect.apply(buffer)
    return buffer.astype(numpy.float32, copy=False)
