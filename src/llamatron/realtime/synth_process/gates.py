# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The low-pass gate a built-in voice's Filter slot can hold: a filter and an amp moved together by one light, so that the
sound darkens as it fades, like a struck object (.claude/notes/synthesis/ENVELOPES.md, "The Vactrol Sound", and
FILTER_TOPOLOGIES.md, "The Ping").

The gate is lit by Env1: a Vactrol envelope is the classic gate, its cell's hyperbolic fall the sound; any other envelope
lights the gate directly. The light becomes the photoresistor's resistance by the cell's power law, and that one resistance
sets both the loudness and the cutoff, never two envelopes:

- VCA: loudness alone.
- Lowpass: the cutoff alone, through a two-pole with resonance, so that a falling cutoff rings a pitch that drops as the gate
  closes, a tuned hand drum when struck.
- Both: loudness and a one-pole's cutoff together, the classic pluck.

The Input decides what the gate is fed: the oscillator, a ping alone (a short strike each note, rung through the gate, the
oscillator unused), or both. Key track moves the gate's open cutoff with the note, so that a pinged gate plays in tune.
The gate is always a note's own, since it is the note's amp. Speed rules this module, as it does the engine (the user's yes).
"""

import math
import numpy
from scipy import signal

VCA = 'vca'
LOWPASS = 'lowpass'
BOTH = 'both'
OSCILLATOR = 'oscillator'
PING = 'ping'
PING_AND_OSCILLATOR = 'both'
# The cell's law: conductance g lights the photoresistor to 1/R = g^1.4 / R_lit + 1/R_dark.
CELL_POWER = 1.4
LIT_OHMS = 5000.0
DARK_OHMS = 1.0e7
# The VCA's divider R5 / (R5 + 2R), heard normalized at full light.
DIVIDER_OHMS = 10000.0
FULL_GAIN = DIVIDER_OHMS / (DIVIDER_OHMS + 2.0 * LIT_OHMS)
# The cutoff at full light, and how far it falls: about 70 Hz at 1 MΩ.
LOWEST_CUTOFF = 20.0
HIGHEST_SHARE = 0.45
# The gate works in parts of this many samples, its cutoff read at each.
PART = 16
# Lowpass's resonance: Q from its least to just short of oscillation.
LEAST_Q = 0.5
MOST_Q = 25.0
MIDDLE_C = 60
SEMITONES = 12.0
# A ping's strike at full velocity: a full strike rung at middle C with resonance peaks near 0.7 of full scale.
PING_LEVEL = 0.45


class LowPassGate:
    """A low-pass gate: its mode, resonance from 0 to 1, open cutoff in hertz, key tracking from 0 to 1, what it is fed and a
    ping's width in seconds, the sample rate, and the state of its filter, a note's own."""

    __slots__ = ('mode', 'resonance', 'open', 'key_track', 'input', 'width', 'rate', 'state')
    # The gate is the note's amp: Env1 lights it, and the voice applies no amp of its own.
    is_gate = True

    def __init__(self, *, spec, rate):
        self.mode = spec['mode']
        self.resonance = spec['resonance']
        self.open = spec['open']
        self.key_track = spec['key_track']
        self.input = spec['input']
        self.width = spec['ping_width']
        self.rate = rate
        self.state = None

    def fresh(self):
        other = LowPassGate.__new__(LowPassGate)
        for name in LowPassGate.__slots__:
            setattr(other, name, getattr(self, name))
        other.state = None
        return other

    def uses_oscillator(self):
        """Return whether the gate is fed the oscillator, so that a ping alone skips it."""
        return self.input != PING

    def gated(self, buffer, *, light, voice, first, octaves=None):
        """Return a chunk through the gate: buffer the oscillator's chunk or None, light Env1 from 0 to about 1 a sample, the
        cutoff moved by octaves a sample or None."""
        count = len(light)
        source = numpy.zeros(count) if buffer is None else buffer.astype(numpy.float64)
        if self.input != OSCILLATOR:
            source = source + self._ping(voice=voice, first=first, count=count)
        conductance = numpy.maximum(light, 0.0) ** CELL_POWER / LIT_OHMS + 1.0 / DARK_OHMS
        if self.mode == VCA:
            return (source * self._gain(conductance)).astype(numpy.float32)
        filtered = self._filtered(source, conductance=conductance, voice=voice, octaves=octaves)
        if self.mode == BOTH:
            filtered = filtered * self._gain(conductance)
        return filtered.astype(numpy.float32)

    @staticmethod
    def _gain(conductance):
        """Return the VCA's gain from the photoresistor, its divider normalized so that full light is full."""
        return DIVIDER_OHMS / (DIVIDER_OHMS + 2.0 / conductance) / FULL_GAIN

    def _filtered(self, source, *, conductance, voice, octaves):
        """Return the source through the gate's filter, a one-pole in Both and a resonant two-pole in Lowpass, its cutoff the
        open cutoff scaled by the resistance, read every PART samples."""
        rate = self.rate
        opened = self.open * 2.0 ** (self.key_track * (voice.pitch - MIDDLE_C) / SEMITONES)
        out = numpy.empty(len(source))
        for start in range(0, len(source), PART):
            cutoff = opened * float(conductance[start]) * LIT_OHMS
            if octaves is not None:
                cutoff *= 2.0 ** float(octaves[start])
            cutoff = min(max(cutoff, LOWEST_CUTOFF), HIGHEST_SHARE * rate)
            numerator, denominator = self._coefficients(cutoff)
            if self.state is None or len(self.state) != len(denominator) - 1:
                self.state = numpy.zeros(len(denominator) - 1)
            out[start:start + PART], self.state = signal.lfilter(numerator, denominator, source[start:start + PART], zi=self.state)
        return out

    def _coefficients(self, cutoff):
        rate = self.rate
        if self.mode == BOTH:
            pole = math.exp(-2.0 * math.pi * cutoff / rate)
            return numpy.array([1.0 - pole]), numpy.array([1.0, -pole])
        quality = LEAST_Q + self.resonance * (MOST_Q - LEAST_Q)
        w = 2.0 * math.pi * cutoff / rate
        cosine = math.cos(w)
        alpha = math.sin(w) / (2.0 * quality)
        numerator = numpy.array([(1 - cosine) / 2, 1 - cosine, (1 - cosine) / 2])
        denominator = numpy.array([1 + alpha, -2.0 * cosine, 1 - alpha])
        return numerator / denominator[0], denominator / denominator[0]

    def _ping(self, *, voice, first, count):
        """Return the chunk's part of the note's strike: a pulse of the ping's width at the note's start, as high as the
        note is hard."""
        places = numpy.arange(first, first + count) - voice.start
        return numpy.where((places >= 0) & (places < self.width * self.rate), PING_LEVEL * voice.level, 0.0)
