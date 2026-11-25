# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The ladder family of filters a built-in voice's Filter slot can hold, a chunk at a time, on one note or on the instrument's
mix (.claude/notes/synthesis/LADDER.md, FILTERS_AND_ACID.md and FILTER_TOPOLOGIES.md).

Two cores serve five circuits. The multimode and the Sallen-Key are a two-pole biquad, low, band, high or notch for the
multimode, low or high for the Sallen-Key, whose resonance screams through a soft clip after it. The ladder, the diode and the
OTA are the exact linear four-pole ladder, H = G^4 / (1 + k G^4), G a prewarped bilinear one-pole, one lfilter call: the
ladder self-oscillates at full resonance and thins its bass as resonance rises; the diode stops short of oscillating and keeps
its bass, as the acid bass machine's does, driven before and after, its floor lowered a little by its Env amount as that
machine's circuit lowers it; the OTA is creamier, a softer drive before it.

The voice moves the cutoff, in octaves a sample: Env2 times the Env amount, key tracking, and the mod matrix (modular.py).
Each chunk is worked in SUB_BLOCKS parts, each part's cutoff the average over it, so that a sweep moves smoothly and a fast one
never jumps the coefficients; the filter's state runs on
from part to part and chunk to chunk. Speed rules this module, as it does the engine (the user's yes).
"""

import math
import numpy
from scipy import signal

LADDER = 'ladder'
MULTIMODE = 'multimode'
SALLEN_KEY = 'sallen_key'
DIODE = 'diode'
OTA = 'ota'
LOW = 'low'
BAND = 'band'
HIGH = 'high'
NOTCH = 'notch'
# How many parts a chunk is filtered in, each with its own cutoff.
SUB_BLOCKS = 4
# How far a cutoff may go: never above this share of the sample rate, where the bilinear filter warps, nor below this.
HIGHEST_SHARE = 0.45
LOWEST_CUTOFF = 20.0
# Env2 at full Env amount moves the cutoff four octaves.
ENVELOPE_OCTAVES = 4.0
# The diode's floor falls this many octaves at full Env amount (the acid bass machine's).
ENV_MOD_DIP = 0.5
# How resonant each circuit goes: the ladder's feedback to self-oscillation, the diode's short of it, and the biquads' Q.
LADDER_FEEDBACK = 3.95
DIODE_FEEDBACK = 3.3
OTA_FEEDBACK = 3.8
LOWEST_Q = 0.5
MOST_Q = 20.0
SCREAM_Q = 30.0
# Above this share of the sample rate, a two-pole's Q is held at most to HIGH_Q.
HIGH_SHARE = 0.3
HIGH_Q = 10.0
# How hard drive pushes into the filter at full, and the gentler push the diode and OTA always have.
MOST_DRIVE = 10.0
DIODE_PUSH = 1.5
OTA_PUSH = 1.2
SCREAM_PUSH = 1.5
# The four-pole ladder's numerator, the binomial of (1 + z^-1)^4.
FOUR_POLE = numpy.array([1.0, 4.0, 6.0, 4.0, 1.0])
ONE_ZERO = numpy.array([1.0, 1.0])
FOUR = 4
LADDERS = (LADDER, DIODE, OTA)


class Filter:
    """A filter of the ladder family: its type and mode, its cutoff in hertz, resonance from 0 to 1, Env amount from -1 to 1
    of four octaves, key tracking and drive from 0 to 1, the sample rate, and the state of its lfilter, which runs on from
    chunk to chunk."""

    __slots__ = ('kind', 'mode', 'cutoff', 'resonance', 'amount', 'key_track', 'drive', 'rate', 'state', 'poles')
    # Only the low-pass gate is a note's amp (gates.py).
    is_gate = False

    def __init__(self, *, spec, rate):
        self.kind = spec['type']
        self.mode = spec['mode']
        self.cutoff = spec['cutoff']
        if self.kind == DIODE:
            self.cutoff = self.cutoff * 2.0 ** (-ENV_MOD_DIP * abs(spec['env_amount']))
        self.resonance = spec['resonance']
        self.amount = spec['env_amount']
        self.key_track = spec['key_track']
        self.drive = spec['drive']
        # The ladder's slope, the poles it is tapped after: 1 to 4, 6 to 24 dB an octave, its resonance still the whole loop's.
        self.poles = spec.get('poles', FOUR)
        self.rate = rate
        self.state = None

    def fresh(self):
        """Return the same filter with a state of its own, for a note that has its own filter."""
        other = Filter.__new__(Filter)
        for name in Filter.__slots__:
            setattr(other, name, getattr(self, name))
        other.state = None
        return other

    def filtered(self, buffer, *, octaves=None, resonance=None):
        """Return a chunk filtered, the cutoff moved by octaves a sample and the resonance by a share a sample, each None for
        none, each part's the average of its samples."""
        buffer = self._driven(buffer)
        size = len(buffer)
        part = -(-size // SUB_BLOCKS)
        out = numpy.empty(size, dtype=numpy.float64)
        highest = HIGHEST_SHARE * self.rate
        base = self.resonance
        for first in range(0, size, part):
            # Each part's cutoff and resonance are its average, never its first sample: a filter envelope opening in a few
            # samples would otherwise jump the coefficients from one part to the next and spike the filter's output.
            cutoff = self.cutoff
            if octaves is not None:
                cutoff = cutoff * 2.0 ** float(numpy.mean(octaves[first:first + part]))
            if resonance is not None:
                self.resonance = min(max(base + float(numpy.mean(resonance[first:first + part])), 0.0), 1.0)
            numerator, denominator = self._coefficients(min(max(cutoff, LOWEST_CUTOFF), highest))
            if self.state is None or len(self.state) != len(denominator) - 1:
                self.state = numpy.zeros(len(denominator) - 1)
            out[first:first + part], self.state = signal.lfilter(numerator, denominator, buffer[first:first + part], zi=self.state)
        out = self._finished(out).astype(numpy.float32)
        self.resonance = base
        return out

    def _coefficients(self, cutoff):
        if self.kind in LADDERS:
            return self._ladder(cutoff)
        return self._biquad(cutoff)

    def _ladder(self, cutoff):
        """Return the ladder's numerator and denominator at a cutoff, tapped after its poles: G^n over (1 + k G^4), each G the
        one-pole g (1 + z^-1) / ((1 + g) + (g - 1) z^-1), its feedback k by the circuit; tapped early, the poles after the tap
        still in the loop, so that resonance peaks as on the hardware's slope switch."""
        g = math.tan(math.pi * cutoff / self.rate)
        pole = numpy.array([1.0 + g, g - 1.0])
        squared = numpy.convolve(pole, pole)
        loop = numpy.convolve(squared, squared)
        four = FOUR_POLE * g ** 4
        feedback = {LADDER: LADDER_FEEDBACK, DIODE: DIODE_FEEDBACK, OTA: OTA_FEEDBACK}[self.kind] * self.resonance
        denominator = loop + feedback * four
        numerator = four
        if self.poles < FOUR:
            numerator = numpy.array([g ** self.poles])
            for _ in range(self.poles):
                numerator = numpy.convolve(numerator, ONE_ZERO)
            for _ in range(FOUR - self.poles):
                numerator = numpy.convolve(numerator, pole)
        return numerator / denominator[0], denominator / denominator[0]

    def _biquad(self, cutoff):
        """Return a two-pole filter's numerator and denominator at a cutoff, by the mode, its Q from the resonance."""
        most = SCREAM_Q if self.kind == SALLEN_KEY else MOST_Q
        quality = LOWEST_Q + self.resonance * most
        if cutoff > HIGH_SHARE * self.rate:
            # A two-pole moved fast near the top can peak dozens of times over (.claude/notes/synthesis/SYNTH_SAFETY.md), so
            # its resonance is held back up there.
            quality = min(quality, HIGH_Q)
        w = 2.0 * math.pi * cutoff / self.rate
        cosine = math.cos(w)
        alpha = math.sin(w) / (2.0 * quality)
        if self.mode == HIGH:
            numerator = [(1 + cosine) / 2, -(1 + cosine), (1 + cosine) / 2]
        elif self.mode == BAND and self.kind == MULTIMODE:
            numerator = [alpha, 0.0, -alpha]
        elif self.mode == NOTCH and self.kind == MULTIMODE:
            numerator = [1.0, -2.0 * cosine, 1.0]
        else:
            numerator = [(1 - cosine) / 2, 1 - cosine, (1 - cosine) / 2]
        denominator = [1 + alpha, -2.0 * cosine, 1 - alpha]
        return numpy.array(numerator) / denominator[0], numpy.array(denominator) / denominator[0]

    def _driven(self, buffer):
        """Return the mix pushed into the filter: drive's soft clip, and the push the diode and the OTA always have."""
        push = 1.0 + self.drive * MOST_DRIVE
        if self.kind == DIODE:
            push *= DIODE_PUSH
        elif self.kind == OTA:
            push *= OTA_PUSH
        if push == 1.0:
            return buffer.astype(numpy.float64)
        return numpy.tanh(buffer * push) / math.tanh(push)

    def _finished(self, out):
        """Return the filter's output finished as its circuit does: the ladder's bass partly made up, the diode's wholly and
        clipped softly, the Sallen-Key's scream clipped."""
        if self.kind == LADDER:
            return out * (1.0 + 0.5 * LADDER_FEEDBACK * self.resonance)
        if self.kind == DIODE:
            return numpy.tanh(out * (1.0 + DIODE_FEEDBACK * self.resonance))
        if self.kind == SALLEN_KEY:
            return numpy.tanh(out * SCREAM_PUSH) / math.tanh(SCREAM_PUSH)
        return out
