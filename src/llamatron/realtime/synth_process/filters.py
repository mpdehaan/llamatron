# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The filter effect of a built-in instrument's effect blocks, a chunk at a time on the instrument's mix
(.claude/notes/synthesis/LADDER.md and FILTERS_AND_ACID.md).

Two cores serve five circuits. The multimode and the Sallen-Key are a two-pole biquad, low, band, high or notch for the
multimode, low or high for the Sallen-Key, whose resonance screams through a soft clip after it. The ladder, the diode and the
OTA are the exact linear four-pole ladder, H = G^4 / (1 + k G^4), G a prewarped bilinear one-pole, one lfilter call: the
ladder self-oscillates at full resonance and thins its bass as resonance rises; the diode stops short of oscillating and keeps
its bass, as the acid bass machine's does, driven before and after; the OTA is creamier, a softer drive before it.

Each chunk is worked in SUB_BLOCKS parts, the cutoff worked out at each from its base, its envelope and key tracking, so that a
sweep moves smoothly; the filter's state runs on from part to part and chunk to chunk. Each note the instrument starts fires
the envelope: a linear attack, then an exponential fall. Speed rules this module, as it does the engine (the user's yes).
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
# The envelope's amount at full is four octaves; its fall is an exponential that is 60 dB down at its decay time.
ENVELOPE_OCTAVES = 4.0
FALL = 6.91
MIDDLE_C = 60
# How resonant each circuit goes: the ladder's feedback to self-oscillation, the diode's short of it, and the biquads' Q.
LADDER_FEEDBACK = 3.95
DIODE_FEEDBACK = 3.3
OTA_FEEDBACK = 3.8
LOWEST_Q = 0.5
MOST_Q = 20.0
SCREAM_Q = 30.0
# How hard drive pushes into the filter at full, and the gentler push the diode and OTA always have.
MOST_DRIVE = 10.0
DIODE_PUSH = 1.5
OTA_PUSH = 1.2
SCREAM_PUSH = 1.5
# The four-pole ladder's numerator, the binomial of (1 + z^-1)^4.
FOUR_POLE = numpy.array([1.0, 4.0, 6.0, 4.0, 1.0])
LADDERS = (LADDER, DIODE, OTA)


class Filter:
    """A filter effect: its type and mode, its cutoff in hertz and resonance from 0 to 1, its envelope's amount from -1 to 1 of
    four octaves, attack and decay in seconds, key tracking and drive from 0 to 1, the sample rate, and what it keeps from chunk
    to chunk: the state of its lfilter, the sample its envelope last fired at and the pitch it fired for."""

    __slots__ = ('kind', 'mode', 'cutoff', 'resonance', 'amount', 'attack', 'decay', 'key_track', 'drive', 'rate', 'state', 'fired_at', 'pitch', 'mix',
                 'octaves')
    # The first filter of an instrument is the one its LFOs' Filter cutoff moves.
    moves_cutoff = True

    def __init__(self, *, spec, rate):
        self.kind = spec['filter_type']
        self.mode = spec['filter_mode']
        self.cutoff = spec['cutoff']
        self.resonance = spec['resonance']
        self.amount = spec['envelope_amount']
        self.attack = spec['envelope_attack']
        self.decay = spec['envelope_decay']
        self.key_track = spec['key_track']
        self.drive = spec['filter_drive']
        self.mix = spec['mix']
        self.rate = rate
        self.state = None
        self.fired_at = None
        self.pitch = MIDDLE_C
        # How far LFOs move the cutoff over the chunk, in octaves a sample, or None (engine.py).
        self.octaves = None

    def note_on(self, *, sample, pitch):
        """Fire the envelope at a note's first sample, and track the note's pitch."""
        self.fired_at = sample
        self.pitch = pitch

    def apply(self, buffer, *, start):
        """Return a chunk of the instrument's mix filtered, the chunk's first sample being start."""
        buffer = self._driven(buffer)
        size = len(buffer)
        part = -(-size // SUB_BLOCKS)
        out = numpy.empty(size, dtype=numpy.float64)
        for first in range(0, size, part):
            cutoff = self._cutoff_at(start + first)
            if self.octaves is not None:
                cutoff = min(max(cutoff * 2.0 ** float(self.octaves[first]), LOWEST_CUTOFF), HIGHEST_SHARE * self.rate)
            numerator, denominator = self._coefficients(cutoff)
            if self.state is None or len(self.state) != len(denominator) - 1:
                self.state = numpy.zeros(len(denominator) - 1)
            out[first:first + part], self.state = signal.lfilter(numerator, denominator, buffer[first:first + part], zi=self.state)
        return self._finished(out).astype(numpy.float32)

    def _cutoff_at(self, sample):
        """Return the cutoff at a sample: its base, moved by the envelope and by the note's distance from middle C."""
        octaves = self.key_track * (self.pitch - MIDDLE_C) / 12.0 + self.amount * ENVELOPE_OCTAVES * self._envelope_at(sample)
        cutoff = self.cutoff * 2.0 ** octaves
        return min(max(cutoff, LOWEST_CUTOFF), HIGHEST_SHARE * self.rate)

    def _envelope_at(self, sample):
        """Return the envelope from 0 to 1 at a sample: nothing before a note, a linear rise over the attack, then a fall."""
        if self.fired_at is None:
            return 0.0
        age = (sample - self.fired_at) / self.rate
        if age < 0.0:
            # The part of a chunk before the note it fires for.
            return 0.0
        if age < self.attack:
            return age / self.attack
        return math.exp(-FALL * (age - self.attack) / max(self.decay, 1e-3))

    def _coefficients(self, cutoff):
        if self.kind in LADDERS:
            return self._ladder(cutoff)
        return self._biquad(cutoff)

    def _ladder(self, cutoff):
        """Return the four-pole ladder's numerator and denominator at a cutoff: G^4 over (1 + k G^4), each G the one-pole
        g (1 + z^-1) / ((1 + g) + (g - 1) z^-1), its feedback k by the circuit."""
        g = math.tan(math.pi * cutoff / self.rate)
        pole = numpy.array([1.0 + g, g - 1.0])
        squared = numpy.convolve(pole, pole)
        denominator = numpy.convolve(squared, squared)
        numerator = FOUR_POLE * g ** 4
        feedback = {LADDER: LADDER_FEEDBACK, DIODE: DIODE_FEEDBACK, OTA: OTA_FEEDBACK}[self.kind] * self.resonance
        denominator = denominator + feedback * numerator
        return numerator / denominator[0], denominator / denominator[0]

    def _biquad(self, cutoff):
        """Return a two-pole filter's numerator and denominator at a cutoff, by the mode, its Q from the resonance."""
        most = SCREAM_Q if self.kind == SALLEN_KEY else MOST_Q
        quality = LOWEST_Q + self.resonance * most
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
