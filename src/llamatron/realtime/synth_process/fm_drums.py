# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The FM drum machines, five on one frequency-modulation core (.claude/notes/synthesis/FM_DRUMS.md): FM Kick, FM Snare,
FM Tom, FM Metal and FM Bell. On every one Pitch is the carrier's pitch, Decay its length, Color the index, how bright and
clangorous the hit is, Sweep its movement over time, and Shape the machine's character: feedback, the ratio, or the balance of
tone and noise.

A modulator's sine moves the carrier's phase by the index, which falls over the hit; feedback feeds the modulator its own last
sample, worked out by three passes over the whole hit, which matches a true one-sample loop for gentle feedback. Velocity
deepens the index and the sweep. A hit bright enough to alias, FM Metal's and any whose sidebands pass about 12 kHz, is
rendered at four times the rate and brought down. drums.py finishes each hit as it does its own.
"""

import math
import numpy
from scipy import signal

from llamatron.model.schema.file_format import DrumMachine

T60 = 6.91
LONGEST_HIT_SECONDS = 4.0
# The ratios Shape snaps between on FM Tom and FM Bell, each held over most of its stretch with a short ramp to the next.
GOOD_RATIOS = (1.0, 1.41, 2.0, 2.76, 3.5, 4.24, 5.4, 7.13)
TOM_RATIOS = (1.0, 1.5, 2.76)
RAMP_SHARE = 0.2
# How many passes work out the feedback, and the band above which a hit renders at four times the rate.
FEEDBACK_PASSES = 3
ALIASING_HZ = 12000.0
OVERSAMPLING = 4


def fm_kick(*, x, tuning, hardness, rate, noise):
    """A sine kick whose index falls fast, Color the index and above two thirds its fall slowing, Shape feedback and, near
    the top, the modulator an octave down, Sweep a pitch drop."""
    pitch_x, decay_x, color_x, shape_x, sweep_x = x
    f0 = 30 * (200 / 30) ** pitch_x * tuning
    decay = 0.06 * 50 ** decay_x
    t = _times(decay, rate=rate)
    falls = 0.004 + 0.036 * max(0.0, (color_x - 0.66) / 0.34)
    index = 8 * color_x * (0.5 + 0.8 * hardness) * numpy.exp(-t / falls)
    drop = 15 * sweep_x * (0.8 + 0.4 * hardness)
    frequency = f0 * (1 + drop * numpy.exp(-t / (0.004 + 0.056 * sweep_x ** 2)))
    ratio = 1.0 - 0.5 * max(0.0, (shape_x - 0.79) / 0.21)
    return _fm(frequency=frequency, ratio=ratio, index=index, feedback=1.2 * shape_x, rate=rate) * numpy.exp(-T60 * t / decay)


def fm_snare(*, x, tuning, hardness, rate, noise):
    """A tone of ratio 1.41 against high-passed noise, Shape the balance and the noise's lowest pitch, Sweep a short bump in
    pitch."""
    pitch_x, decay_x, color_x, shape_x, sweep_x = x
    f = 120 * 4 ** pitch_x * tuning
    decay = 0.06 * 15 ** decay_x
    t = _times(decay, rate=rate)
    index = 8 * color_x * (0.5 + 0.8 * hardness) * numpy.exp(-t / (decay / 3))
    frequency = f * (1 + 2 * sweep_x * (0.8 + 0.4 * hardness) * numpy.exp(-t / 0.01))
    tone = _fm(frequency=frequency, ratio=1.41, index=index, feedback=0.0, rate=rate)
    hiss = signal.sosfilt(_high_pass(rate=rate, cutoff=150 * 13.3 ** shape_x), noise.standard_normal(len(t)))
    return (tone * (1 - shape_x) + hiss * shape_x * 0.7) * numpy.exp(-T60 * t / decay)


def fm_tom(*, x, tuning, hardness, rate, noise):
    """A tom from skin to wood as Shape snaps its ratio through 1, 1.5 and 2.76, Color a short slap of index, Sweep a bend down
    into the pitch."""
    pitch_x, decay_x, color_x, shape_x, sweep_x = x
    f = 60 * 10 ** pitch_x * tuning
    decay = 0.1 * 25 ** decay_x
    t = _times(decay, rate=rate)
    index = 4 * color_x * (0.5 + 0.8 * hardness) * numpy.exp(-t / 0.012)
    frequency = f * (1 + 1.5 * sweep_x * (0.8 + 0.4 * hardness) * numpy.exp(-t / (0.02 + 0.08 * sweep_x)))
    tone = _fm(frequency=frequency, ratio=plateau(share=shape_x, ratios=TOM_RATIOS), index=index, feedback=0.0, rate=rate)
    return tone * numpy.exp(-T60 * t / decay)


def fm_metal(*, x, tuning, hardness, rate, noise):
    """Every hat and cymbal: a high carrier under a modulator at the chain's spread, Color the index, Shape feedback, Sweep the
    spread and, near the top, a tremolo; rendered at four times the rate, since metal is mostly sidebands."""
    pitch_x, decay_x, color_x, shape_x, sweep_x = x
    f = 200 * 40 ** pitch_x * tuning
    decay = 0.015 * 267 ** decay_x
    high = rate * OVERSAMPLING
    t = _times(decay, rate=high)
    index = (2 + 10 * color_x) * (0.5 + 0.8 * hardness) * numpy.exp(-t / decay)
    spread = 1.4 + 2.8 * sweep_x
    body = _fm(frequency=numpy.full(len(t), min(f, high * 0.2)), ratio=spread, index=index, feedback=2.0 * shape_x * (0.8 + 0.4 * hardness), rate=high)
    body *= numpy.exp(-T60 * t / decay)
    if sweep_x > 0.85:
        body *= 1 - 0.5 * (0.5 + 0.5 * numpy.sin(2 * math.pi * (10 + 50 * (sweep_x - 0.85) / 0.15) * t))
    return signal.resample_poly(body, 1, OVERSAMPLING)


def fm_bell(*, x, tuning, hardness, rate, noise):
    """Claves, woodblock, cowbell and bell: Shape snaps the ratio through the good ones, Color the index, Sweep how closely the
    index follows the level, falling fast for wood and alike for a bell."""
    pitch_x, decay_x, color_x, shape_x, sweep_x = x
    f = 200 * 15 ** pitch_x * tuning
    decay = 0.02 * 400 ** decay_x
    ratio = plateau(share=shape_x, ratios=GOOD_RATIOS)
    index_top = 10 * color_x * (0.5 + 0.8 * hardness)
    oversampled = f * ratio * (index_top + 1) > ALIASING_HZ
    high = rate * OVERSAMPLING if oversampled else rate
    t = _times(decay, rate=high)
    level = numpy.exp(-T60 * t / decay)
    body = _fm(frequency=numpy.full(len(t), f), ratio=ratio, index=index_top * level ** (3 - 2 * sweep_x), feedback=0.0, rate=high) * level
    if oversampled:
        return signal.resample_poly(body, 1, OVERSAMPLING)
    return body


RECIPES = {DrumMachine.FM_KICK: fm_kick, DrumMachine.FM_SNARE: fm_snare, DrumMachine.FM_TOM: fm_tom, DrumMachine.FM_METAL: fm_metal,
           DrumMachine.FM_BELL: fm_bell}


def _fm(*, frequency, ratio, index, feedback, rate):
    """Return a carrier's sine at a frequency that may move, its phase moved by a modulator at ratio times it, by an index that
    may move, the modulator fed its own last sample by feedback."""
    carrier = 2 * math.pi * numpy.cumsum(frequency) / rate
    moving = carrier * ratio
    modulator = numpy.sin(moving)
    for _ in range(FEEDBACK_PASSES if feedback else 0):
        last = numpy.concatenate(([0.0], modulator[:-1]))
        modulator = numpy.sin(moving + feedback * last)
    return numpy.sin(carrier + index * modulator)


def plateau(*, share, ratios):
    """Return the ratio a knob's share gives: each of the ratios held over most of its stretch, ramping to the next at its end."""
    place = share * (len(ratios) - 1)
    first = min(int(place), len(ratios) - 2)
    along = min(max((place - first - (1 - RAMP_SHARE)) / RAMP_SHARE, 0.0), 1.0)
    return ratios[first] + (ratios[first + 1] - ratios[first]) * along


def _times(seconds, *, rate):
    return numpy.arange(int(min(seconds * 1.2 + 0.01, LONGEST_HIT_SECONDS) * rate)) / rate


def _high_pass(*, rate, cutoff):
    return signal.butter(2, min(cutoff, rate * 0.45), btype='highpass', fs=rate, output='sos')
