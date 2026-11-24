# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The built-in drum machines: each renders one whole hit, as float32, from its five knobs, Pitch, Decay, Color, Shape and
Sweep, each 0 to 127, a note's pitch tuning it in half steps from middle C and its velocity brightening it a little.

The recipes are the professor's (.claude/synthesis_techniques/DRUMS.md), honoring the classic drum machines' circuits:
a sine resonator swept down in pitch for the kicks, detuned tones and snapped noise for the snare, noise bursts for the
clap, six clashing squares for the hats, two squares through a band-pass for the cowbell, and a struck membrane's modes for
the acoustic tom, and Karplus and Strong's plucked drum. A hit is rendered once, when its note first arrives, in a few milliseconds, and kept; every hit starts at
phase zero and its noise is seeded by what it is, so that replays and WAV exports match to the sample. Every machine ends
alike: a DC-blocking high-pass, a fade where it falls silent, and a gain so that its loudest default hit peaks near -3 dB.
"""

import functools
import math
import numpy
from scipy import signal

KNOB_TOP = 127.0
MIDDLE_C = 60
# What a hit's end and start do: the level it fades out below, the length of that fade, the DC-blocking cutoff, its peak.
SILENT_DB = -80.0
END_FADE_SECONDS = 0.005
DC_BLOCK_HZ = 20.0
PEAK = 10 ** (-3 / 20)
T60 = 6.91
# A hit lasts no longer than this, whatever its decay.
LONGEST_HIT_SECONDS = 4.0
# The analog cymbal circuit's six clashing pitches, the hats' metal.
HAT_PITCHES = (205.3, 304.4, 369.6, 522.7, 540.0, 800.0)
# A circular membrane's mode ratios, and those a center strike rings most.
MEMBRANE_RATIOS = (1.000, 1.594, 2.136, 2.296, 2.653, 2.918, 3.156, 3.501, 3.600, 4.060)
CENTER_MODES = (1.000, 2.296, 3.600)


class Machine:
    """A drum machine's name, as an instrument stores it."""

    KICK = 'kick'
    HARD_KICK = 'hard_kick'
    SYNTH_KICK = 'synth_kick'
    SNARE = 'snare'
    CLAP = 'clap'
    RIM = 'rim'
    HATS = 'hats'
    COWBELL = 'cowbell'
    ACOUSTIC_TOM = 'acoustic_tom'
    KARPLUS_DRUM = 'karplus_drum'


MACHINES = (Machine.KICK, Machine.HARD_KICK, Machine.SYNTH_KICK, Machine.SNARE, Machine.CLAP, Machine.RIM, Machine.HATS,
            Machine.COWBELL, Machine.ACOUSTIC_TOM, Machine.KARPLUS_DRUM)


def render_hit(*, machine, knobs, pitch, velocity, rate):
    """Return one hit of a machine, its knobs (Pitch, Decay, Color, Shape, Sweep, each 0 to 127), at a note's pitch and
    velocity and a sample rate, as float32."""
    pitch_x, decay_x, color_x, shape_x, sweep_x = (knob / KNOB_TOP for knob in knobs)
    tuning = 2.0 ** ((pitch - MIDDLE_C) / 12.0)
    hardness = velocity / 127.0
    seed = hash((machine, knobs, pitch, velocity)) & 0xFFFFFFFF
    made = RECIPES[machine](x=(pitch_x, decay_x, color_x, shape_x, sweep_x), tuning=tuning, hardness=hardness, rate=rate,
                            noise=numpy.random.default_rng(seed))
    return finished(made, rate=rate)


def finished(hit, *, rate):
    """Return a hit high-passed against DC, faded out where it falls silent, at its peak gain, as float32."""
    hit = signal.sosfilt(_high_pass(rate=rate, cutoff=DC_BLOCK_HZ), hit)
    level = numpy.abs(hit)
    loud = numpy.nonzero(level > 10 ** (SILENT_DB / 20) * max(level.max(), 1e-12))[0]
    end = (loud[-1] + 1) if len(loud) else len(hit)
    fade = min(int(END_FADE_SECONDS * rate), end)
    hit = hit[:end].copy()
    if fade:
        hit[-fade:] *= numpy.linspace(1.0, 0.0, fade)
    peak = numpy.abs(hit).max()
    if peak > 0:
        hit *= PEAK / peak
    return hit.astype(numpy.float32)


def kick(*, x, tuning, hardness, rate, noise):
    """A sine resonator swept down in pitch, with click, noise and harmonics by Color, and clipped by Shape."""
    pitch_x, decay_x, color_x, shape_x, sweep_x = x
    f0 = 30 * 2 ** (3 * pitch_x) * tuning
    decay = 0.06 * 50 ** decay_x
    t = _times(decay, rate=rate)
    drop = 15 * sweep_x ** 1.5
    tau = 0.004 + 0.056 * sweep_x ** 2
    phase = _phase(f0 * (1 + drop * numpy.exp(-t / tau)), rate=rate)
    harmonics = max(0.0, (color_x - 0.66) / 0.34)
    body = (numpy.sin(phase) + harmonics / 2 * numpy.sin(2 * phase) + harmonics / 4 * numpy.sin(3 * phase)) * numpy.exp(-T60 * t / decay)
    body += _click(t, rate=rate, level=min(1.0, color_x / 0.33) * (0.5 + 0.5 * hardness))
    body += _noise_burst(t, sound=(rate, noise), level=min(1.0, max(0.0, (color_x - 0.33) / 0.33)) * 0.3, decay=0.004, centre=3000)
    return _clip(body, gain=1 + 19 * shape_x ** 2)


def hard_kick(*, x, tuning, hardness, rate, noise):
    """The techno kick: a hold at full level before the decay, a tick and a little noise."""
    pitch_x, decay_x, color_x, shape_x, sweep_x = x
    f0 = 35 * (200 / 35) ** pitch_x * tuning
    decay = 0.06 * 30 ** decay_x
    hold = 0.15 * shape_x ** 2
    t = _times(decay + hold, rate=rate)
    phase = _phase(f0 * (1 + 12 * sweep_x ** 1.5 * numpy.exp(-t / (0.004 + 0.04 * sweep_x ** 2))), rate=rate)
    level = numpy.where(t < hold, 1.0, numpy.exp(-T60 * (t - hold) / decay))
    body = numpy.sin(phase) * level
    tick = int(0.0003 * rate)
    body[:tick] += color_x * (0.5 + 0.5 * hardness)
    body += _noise_burst(t, sound=(rate, noise), level=0.06 + 0.2 * color_x, decay=0.01, centre=3000)
    return _clip(body, gain=2.0)


def synth_kick(*, x, tuning, hardness, rate, noise):
    """The groovebox synth kick: a sine morphing to a triangle and a square by Color, its phase reset each hit, its level
    falling with no attack and its pitch dropping octaves exponentially, low-passed and driven."""
    pitch_x, decay_x, color_x, shape_x, sweep_x = x
    f0 = 30 * (200 / 30) ** pitch_x * tuning
    decay = 0.04 * 50 ** decay_x
    t = _times(decay, rate=rate)
    octaves = 5 * sweep_x
    tau = 0.005 + 0.075 * sweep_x ** 2
    frequency = f0 * 2 ** (octaves * numpy.exp(-t / tau))
    phase = _phase(frequency, rate=rate)
    wave = _morphed(phase=phase, frequency=frequency, color=color_x, rate=rate)
    curve = 1.0 - 0.6 * min(1.0, shape_x / 0.5)
    body = wave * numpy.exp(-T60 * t / decay) ** curve
    body = _gliding_low_pass(body, sweep=(4000.0, max(4 * f0, 300.0), tau), t=t, rate=rate)
    drive = 1 + 9 * max(0.0, (shape_x - 0.5) / 0.5)
    return _clip(body * (0.8 + 0.2 * hardness), gain=drive)


def snare(*, x, tuning, hardness, rate, noise):
    """Two detuned triangle tones with a bump, and snapped, filtered noise, balanced by Shape and clipped."""
    pitch_x, decay_x, color_x, shape_x, sweep_x = x
    f1 = 120 * 4 ** pitch_x * tuning
    decay = 0.06 * 15 ** decay_x
    t = _times(decay, rate=rate)
    bump = 1 + sweep_x * numpy.exp(-t / 0.008)
    tones = numpy.zeros_like(t)
    for frequency in (f1, f1 * 1.47 * (1 + 0.04 * color_x)):
        phase = _phase(frequency * bump, rate=rate)
        tones += _triangle(phase) * numpy.exp(-T60 * t / (0.35 * decay))
    snap = numpy.where(t < 0.003, 2.0, 1.0) * numpy.exp(-T60 * t / decay)
    rattle = signal.sosfilt(_high_pass(rate=rate, cutoff=600 + 3400 * color_x), noise.standard_normal(len(t))) * snap * (0.6 + 0.4 * hardness)
    balance = shape_x
    return _clip(tones * (1 - balance) * 0.6 + rattle * balance, gain=3.0)


def clap(*, x, tuning, hardness, rate, noise):
    """Three to six noise bursts and a room tail, through a band-pass falling a little at the start."""
    pitch_x, decay_x, color_x, shape_x, sweep_x = x
    centre = min(700 * 4 ** pitch_x * tuning, rate * 0.45)
    decay = 0.08 * 15 ** decay_x
    bursts = 3 + int(round(3 * color_x))
    spacing = 0.014 - 0.007 * color_x
    t = _times(bursts * spacing + decay, rate=rate)
    raw = noise.standard_normal(len(t))
    shape = numpy.zeros_like(t)
    for burst in range(bursts):
        start = burst * spacing + noise.uniform(0, 0.001)
        since = t - start
        shape += numpy.where(since >= 0, numpy.minimum(since / 0.0015, 1.0) * numpy.exp(-numpy.maximum(since, 0) / (0.006 - 0.004 * hardness)), 0.0)
    last = (bursts - 1) * spacing
    tail = numpy.where(t >= last, numpy.exp(-T60 * numpy.maximum(t - last, 0) / decay), 0.0) * 10 ** ((-30 + 30 * shape_x) / 20)
    return signal.sosfilt(_band_pass(rate=rate, centre=centre * (1 + 0.6 * sweep_x * 0.5), quality=2.0), raw * (shape + tail))


def rim(*, x, tuning, hardness, rate, noise):
    """Two short resonators a little over an octave and a half apart, a click, and drive."""
    pitch_x, decay_x, color_x, shape_x, sweep_x = x
    frequency = 250 * (900 / 250) ** pitch_x * tuning
    factor = 0.4 * 10 ** decay_x
    t = _times(0.025 * factor * 2, rate=rate)
    drop = 1 - 0.15 * sweep_x * (1 - numpy.exp(-t / 0.005))
    low = numpy.sin(_phase(frequency * drop, rate=rate)) * numpy.exp(-T60 * t / (0.025 * factor))
    high = numpy.sin(_phase(frequency * 3.66 * drop, rate=rate)) * numpy.exp(-T60 * t / (0.012 * factor))
    body = low * (1 - color_x * 0.5) + high * (0.3 + 0.7 * color_x)
    body += _click(t, rate=rate, level=0.4 + 0.4 * hardness)
    return _clip(body, gain=1 + 11 * shape_x)


def hats(*, x, tuning, hardness, rate, noise):
    """Six clashing squares blended with noise by Color, band-passed and high-passed, closed or open by Decay."""
    pitch_x, decay_x, color_x, shape_x, sweep_x = x
    scale = 0.5 * 4 ** pitch_x * tuning
    decay = 0.015 * 100 ** decay_x
    t = _times(decay, rate=rate)
    metal = _metal(scale=round(scale, 3), rate=rate)[:len(t)]
    source = metal * color_x + noise.standard_normal(len(t)) * 0.4 * (1 - color_x)
    band = signal.sosfilt(_band_pass(rate=rate, centre=min(8000.0 * (1 - 0.3 * sweep_x), rate * 0.45), quality=1.5 + 2.5 * shape_x), source)
    bright = signal.sosfilt(_high_pass(rate=rate, cutoff=min(6000.0, rate * 0.4)), band)
    gap = 1.0 - (0.75 * shape_x) * ((t > 0.002) & (t < 0.006))
    envelope = numpy.minimum(t / 0.0005, 1.0) * numpy.exp(-T60 * t / decay) * gap
    return bright * envelope * (0.7 + 0.3 * hardness)


def cowbell(*, x, tuning, hardness, rate, noise):
    """Two squares about a fifth apart through a band-pass, a fast fall to a level set by Shape, then the tail."""
    pitch_x, decay_x, color_x, shape_x, sweep_x = x
    frequency = 300 * (1100 / 300) ** pitch_x * tuning
    decay = 0.1 * 12 ** decay_x
    t = _times(decay, rate=rate)
    bump = 1 + 0.3 * sweep_x * numpy.exp(-t / 0.006)
    squares = numpy.sign(numpy.sin(_phase(frequency * bump, rate=rate))) + numpy.sign(numpy.sin(_phase(frequency * 1.48 * bump, rate=rate)))
    shaped = signal.sosfilt(_band_pass(rate=rate, centre=min(2.6 * frequency, rate * 0.45), quality=3.0), squares)
    floor = 0.2 + 0.6 * shape_x
    envelope = (1 - floor) * numpy.exp(-T60 * t / 0.03) + floor * numpy.exp(-T60 * t / decay)
    body = signal.sosfilt(_low_pass(rate=rate, cutoff=4000 - 2500 * color_x), shaped * envelope)
    return _clip(body * (0.7 + 0.3 * hardness), gain=1 + 2 * color_x)


def acoustic_tom(*, x, tuning, hardness, rate, noise):
    """A struck membrane's modes, rung by strike position and mallet hardness, its tension gliding down after a hard hit."""
    pitch_x, decay_x, color_x, shape_x, sweep_x = x
    f0 = 60 * (400 / 60) ** pitch_x * tuning
    decay = 0.1 * 25 ** decay_x
    t = _times(decay, rate=rate)
    width = 0.004 - 0.0037 * min(1.0, color_x + 0.2 * hardness)
    glide = 1 + 0.08 * sweep_x * hardness * numpy.exp(-t / 0.04)
    body = numpy.zeros_like(t)
    for ratio in MEMBRANE_RATIOS:
        frequency = f0 * ratio
        if frequency >= rate * 0.45:
            continue
        centre = 1.0 if ratio in CENTER_MODES else 0.15
        amplitude = centre * (1 - shape_x) + shape_x
        amplitude /= 1 + (frequency * width * 2) ** 2
        mode_decay = decay / (1 + 0.6 * (ratio - 1))
        body += amplitude * numpy.sin(_phase(frequency * glide, rate=rate)) * numpy.exp(-T60 * t / mode_decay)
    shell = signal.sosfilt(_band_pass(rate=rate, centre=min(5 * f0, rate * 0.45), quality=1.0), noise.standard_normal(len(t))) * numpy.exp(-T60 * t / 0.2) * 0.03
    return body + shell


def karplus_drum(*, x, tuning, hardness, rate, noise):
    """Karplus and Strong's drum: a burst of noise circulating in a delay line a period long, each pass averaged with its
    neighbor, which dulls and fades it, and each sample's sign flipped at random by Shape, the blend, which turns a plucked
    string into a drum; Color brightens the burst and the averaging, Sweep drops the pitch at the start."""
    pitch_x, decay_x, color_x, shape_x, sweep_x = x
    frequency = 50 * 16 ** pitch_x * tuning
    decay = 0.05 * 40 ** decay_x
    t = _times(decay, rate=rate)
    total = len(t)
    period = max(2, int(round(rate / frequency)))
    burst = noise.standard_normal(period)
    if color_x < 1:
        burst = signal.sosfilt(_low_pass(rate=rate, cutoff=min(500 + 15000 * color_x * (0.6 + 0.4 * hardness), rate * 0.45)), burst)
    out = numpy.empty(total)
    loss = 10 ** (-3 * period / (decay * rate))
    blend = 1.0 - shape_x * 0.5
    bright = 0.5 + 0.45 * color_x
    line = burst
    place = 0
    while place < total:
        since = place / rate
        length = max(2, int(round(period / (1 + sweep_x * numpy.exp(-since / 0.03)))))
        if length != len(line):
            line = numpy.interp(numpy.linspace(0, len(line) - 1, length), numpy.arange(len(line)), line)
        averaged = bright * line + (1 - bright) * numpy.roll(line, 1)
        signs = numpy.where(noise.random(length) < blend, 1.0, -1.0)
        line = averaged * signs * loss
        take = min(length, total - place)
        out[place:place + take] = line[:take]
        place += take
    return out


RECIPES = {
    Machine.KICK: kick, Machine.HARD_KICK: hard_kick, Machine.SYNTH_KICK: synth_kick, Machine.SNARE: snare, Machine.CLAP: clap,
    Machine.RIM: rim, Machine.HATS: hats, Machine.COWBELL: cowbell, Machine.ACOUSTIC_TOM: acoustic_tom, Machine.KARPLUS_DRUM: karplus_drum,
}


def _times(seconds, *, rate):
    return numpy.arange(int(min(seconds * 1.2 + 0.01, LONGEST_HIT_SECONDS) * rate)) / rate


def _phase(frequency, *, rate):
    """Return the phase of a frequency that may move, as the running sum of its frequency, starting at zero."""
    frequency = numpy.broadcast_to(frequency, frequency.shape if hasattr(frequency, 'shape') else ())
    return 2 * math.pi * numpy.cumsum(frequency) / rate


def _triangle(phase):
    return 2 / math.pi * numpy.arcsin(numpy.sin(phase))


def _morphed(*, phase, frequency, color, rate):
    """Return a wave morphing from a sine at Color 0 through a triangle to a square at full Color, from odd harmonics kept
    under 8 kHz."""
    wave = numpy.sin(phase)
    if color <= 0:
        return wave
    for number in (3, 5, 7, 9, 11, 13):
        keep = frequency * number < min(8000.0, rate * 0.45)
        triangle = ((-1) ** ((number - 1) // 2)) / number ** 2
        square = 1.0 / number
        weight = triangle * min(1.0, color * 2) + (square - triangle) * max(0.0, color * 2 - 1)
        wave = wave + numpy.where(keep, weight * numpy.sin(number * phase), 0.0)
    return wave


def _click(t, *, rate, level):
    width = max(1, int(0.001 * rate))
    click = numpy.zeros_like(t)
    click[:width] = level * 0.5 * (1 + numpy.cos(numpy.linspace(0, math.pi, width)))
    return signal.sosfilt(_high_pass(rate=rate, cutoff=1000.0), click)


def _noise_burst(t, *, sound, level, decay, centre):
    rate, noise = sound
    if level <= 0:
        return numpy.zeros_like(t)
    burst = noise.standard_normal(len(t)) * numpy.exp(-t / decay) * level
    return signal.sosfilt(_band_pass(rate=rate, centre=min(centre, rate * 0.45), quality=0.7), burst)


def _clip(body, *, gain):
    clipped = numpy.tanh(gain * body) / math.tanh(gain)
    if gain > 8:
        clipped = numpy.clip(clipped * 1.1, -1.0, 1.0)
    return clipped


def _gliding_low_pass(body, *, sweep, t, rate):
    """Low-pass a hit in blocks, the cutoff falling with the pitch envelope, sweep being (start, end, tau)."""
    start, end, tau = sweep
    out = numpy.empty_like(body)
    block = max(64, int(0.002 * rate))
    state = None
    for first in range(0, len(body), block):
        cutoff = end + (start - end) * math.exp(-t[first] / tau)
        sos = _low_pass(rate=rate, cutoff=min(cutoff, rate * 0.45))
        if state is None:
            state = numpy.zeros((sos.shape[0], 2))
        out[first:first + block], state = signal.sosfilt(sos, body[first:first + block], zi=state)
    return out


@functools.cache
def _metal(*, scale, rate):
    """Return two seconds of the six clashing squares at a scale, naive and so a little aliased, as the digital edge has it."""
    t = numpy.arange(int(2.0 * rate)) / rate
    metal = numpy.zeros_like(t)
    for frequency in HAT_PITCHES:
        metal += numpy.sign(numpy.sin(2 * math.pi * frequency * scale * t))
    return metal / len(HAT_PITCHES)


@functools.cache
def _high_pass(*, rate, cutoff):
    return signal.butter(2, cutoff, btype='highpass', fs=rate, output='sos')


@functools.cache
def _low_pass(*, rate, cutoff):
    return signal.butter(2, max(cutoff, 20.0), btype='lowpass', fs=rate, output='sos')


@functools.cache
def _band_pass(*, rate, centre, quality):
    width = centre / quality
    low = max(20.0, centre - width / 2)
    high = min(rate * 0.49, centre + width / 2)
    return signal.butter(2, (low, high), btype='bandpass', fs=rate, output='sos')
