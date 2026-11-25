# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The oscillator modules of a built-in voice, each a part its Oscillators slot can hold: what makes the raw sound before the
filter and the amp.

- Basic: up to three band-limited table oscillators, each a waveform, a detune in cents and a level.
- SID: one voice of the classic home computer's chip as players use it: a triangle, saw, pulse whose width can sweep, or
  noise clocked by the pitch, ring modulated or synced by a second oscillator an interval away, and an arpeggio stepped at the
  chip's frame rate of 50 a second.
- Pocket: one voice of the handheld's chip: a pulse of one of four duties, the drawn wave of 32 steps of four bits, or a shift
  register's noise, and its pitch sweep, which moves the chip's period register 128 times a second at a pace.
- Acid: the acid bass's band-limited saw, or the square a transistor shapes from it, and its tuning.

Each is compiled once for its instrument; begin() readies a voice and wave() gives a chunk of it, its pitch moved sample by
sample by semitones the voice works out (glide, Env3's pitch envelope, the matrix), or None where nothing moves it, and its
pulse width and detune spread by the matrix's moves, which it is handed whole (matrix.py). Speed rules this module, as it does the engine (the user's yes): whole-array numpy
reads, plain attributes, never a loop over samples.
"""

import math
import numpy

from llamatron.realtime.synth_process import modulation, tables

BASIC = 'basic'
SID = 'sid'
POCKET = 'pocket'
ACID = 'acid'
DRUM = 'drum'
SAW = 'saw'
TRIANGLE = 'triangle'
PULSE = 'pulse'
NOISE = 'noise'
WAVE = 'wave'
SHORT = 'short'
RING = 'ring'
SYNC = 'sync'
OFF = 'off'
# The matrix's destinations an oscillator reads from its moves (matrix.py).
PULSE_WIDTH = 'pulse_width'
DETUNE = 'detune'
MIDDLE_A = 69
A_FREQUENCY = 440.0
SEMITONES = 12.0
CENTS = 1200.0
# How narrow and how wide a pulse's width goes, between which pulse-width modulation bounces.
NARROWEST = 0.1
WIDEST = 0.9
# The SID-style chip steps its arpeggio at the frame rate of the computers it was in.
FRAMES_PER_SECOND = 50.0
# How fast noise is clocked against the pitch: the handheld's a step each sixteenth of a cycle; the SID-style voice's four
# times as fast as the real chip's, so that middle C gives a bright noise and lower notes darken it, the real chip's rate
# sounding sample-held below the high notes players give its noise.
NOISE_STEPS_PER_CYCLE = 16
SID_NOISE_STEPS_PER_CYCLE = 64
# The handheld chip's clocks: its sweep steps 128 times a second, and its period register is eleven bits of a 131072 Hz
# clock, a pulse's frequency 131072 / (2048 - period).
SWEEP_TICKS = 128.0
CHIP_CLOCK = 131072.0
LONGEST_PERIOD = 2047
PERIODS = 2048
# The acid square is the saw's pulse shaped by a transistor: a soft clip of this push.
SQUARE_PUSH = 1.8


def frequency_of(pitch):
    """Return a MIDI number's frequency in hertz, equal tempered from A 440, a fraction of a number bending between."""
    return A_FREQUENCY * 2.0 ** ((pitch - MIDDLE_A) / SEMITONES)


class BasicOscillators:
    """Up to three table oscillators, each (tables by octave band, detune in cents, level)."""

    __slots__ = ('oscillators', 'rate')

    def __init__(self, *, spec, rate):
        self.rate = rate
        self.oscillators = []
        for waveform, cents, level in spec['oscillators']:
            self.oscillators.append((tables.waveform_tables(waveform=waveform, rate=rate), cents, level))

    def begin(self, *, voice, rate):
        voice.oscillators = []
        for oscillator_tables, cents, level in self.oscillators:
            frequency = frequency_of(voice.pitch) * 2.0 ** (cents / CENTS)
            speed = frequency * tables.TABLE_SIZE / rate
            voice.oscillators.append((oscillator_tables[tables.band_of(frequency)], speed, 0.0, level, cents))

    def wave(self, *, voice, first, count, pitch, moved):
        spread = moved.get(DETUNE)
        out = numpy.zeros(count, dtype=numpy.float32)
        steps = None
        if pitch is None and spread is None:
            steps = numpy.arange(count, dtype=numpy.float64)
        read = []
        for table, speed, phase, level, cents in voice.oscillators:
            if steps is not None:
                positions = phase + speed * steps
                after = phase + speed * count
            else:
                positions, after = modulation.phases(phase=phase, speeds=speed * moved_speed(pitch=pitch, spread=spread, cents=cents))
            out += table[positions.astype(numpy.int64) & tables.TABLE_MASK] * level
            read.append((table, speed, after % tables.TABLE_SIZE, level, cents))
        voice.oscillators = read
        return out


class SidOscillator:
    """The SID-style voice: its wave and the tables it reads, its pulse width and sweep a second, its modulation, ring or sync,
    the interval of the oscillator that does it, and its arpeggio in semitones."""

    __slots__ = ('wave_kind', 'saw', 'triangle', 'noise', 'pulse_width', 'pulse_sweep', 'interaction', 'interval', 'arpeggio', 'rate')

    def __init__(self, *, spec, rate):
        self.rate = rate
        self.wave_kind = spec['wave']
        self.saw = tables.waveform_tables(waveform=SAW, rate=rate)
        self.triangle = tables.waveform_tables(waveform=TRIANGLE, rate=rate)
        self.noise = tables.sid_noise()
        self.pulse_width = spec['pulse_width']
        self.pulse_sweep = spec['pulse_sweep']
        self.interaction = spec['modulation']
        self.interval = spec['interval']
        self.arpeggio = tuple(spec['arpeggio'])

    def begin(self, *, voice, rate):
        voice.phase = 0.0
        voice.second_phase = 0.0

    def wave(self, *, voice, first, count, pitch, moved):
        rate = self.rate
        seconds = (first - voice.start) / rate
        base = voice.pitch
        if self.arpeggio:
            base += self.arpeggio[int(seconds * FRAMES_PER_SECOND) % len(self.arpeggio)]
        bent = pitch
        if bent is not None and self.interaction != OFF:
            # Ring and sync follow the pitch's movement a chunk at a time.
            base += float(bent.mean())
            bent = None
        frequency = frequency_of(base)
        steps = numpy.arange(count, dtype=numpy.float64)
        if self.interaction == SYNC:
            second = frequency_of(base + self.interval)
            return self._synced(voice=voice, ratio=frequency / second, second_step=second / rate, steps=steps, width=self._width(seconds))
        positions = read_positions(voice=voice, speed=frequency * tables.TABLE_SIZE / rate, count=count, moved=bent)
        voice.phase %= tables.TABLE_SIZE
        out = self._wave(frequency=frequency, positions=positions, seconds=seconds, wobble=moved.get(PULSE_WIDTH))
        if self.interaction == RING:
            out *= self._ring(voice=voice, pitch=base, steps=steps, rate=rate)
        return out

    def _wave(self, *, frequency, positions, seconds, wobble):
        """Return the wave read at a chunk's positions, band-limited but for noise, as the chip's own noise is."""
        band = tables.band_of(frequency)
        indexes = positions.astype(numpy.int64)
        if self.wave_kind == SAW:
            return self.saw[band][indexes & tables.TABLE_MASK].copy()
        if self.wave_kind == TRIANGLE:
            return self.triangle[band][indexes & tables.TABLE_MASK].copy()
        if self.wave_kind == NOISE:
            return self.noise[(positions * SID_NOISE_STEPS_PER_CYCLE / tables.TABLE_SIZE).astype(numpy.int64) % len(self.noise)]
        # A band-limited pulse is one saw less another shifted by its width, which also leaves it with no offset.
        width = self._width(seconds)
        if wobble is None:
            shifted = (indexes + int(width * tables.TABLE_SIZE)) & tables.TABLE_MASK
        else:
            widths = numpy.clip(width + wobble, NARROWEST, WIDEST)
            shifted = (indexes + (widths * tables.TABLE_SIZE).astype(numpy.int64)) & tables.TABLE_MASK
        saw = self.saw[band]
        return (saw[indexes & tables.TABLE_MASK] - saw[shifted]) * numpy.float32(0.5)

    def _ring(self, *, voice, pitch, steps, rate):
        """Return the second oscillator's square, an interval away, which the wave is multiplied by: ring modulation."""
        cycles = voice.second_phase + frequency_of(pitch + self.interval) / rate * steps
        voice.second_phase = (voice.second_phase + frequency_of(pitch + self.interval) / rate * len(steps)) % 1.0
        return numpy.where(cycles % 1.0 < 0.5, numpy.float32(1.0), numpy.float32(-1.0))

    def _width(self, seconds):
        """Return the pulse's width a time into the note: pulse-width modulation, the width moving from where it starts at the
        sweep's rate and bouncing back at NARROWEST and WIDEST, as players sweep the chip's width up and down."""
        if not self.pulse_sweep:
            return min(WIDEST, max(NARROWEST, self.pulse_width))
        span = WIDEST - NARROWEST
        moved = (self.pulse_width - NARROWEST + self.pulse_sweep * seconds) % (2 * span)
        if moved > span:
            moved = 2 * span - moved
        return NARROWEST + moved

    def _synced(self, *, voice, ratio, second_step, steps, width):
        """Return the wave restarted at each cycle of the second oscillator, ratio times slower than the wave and stepping
        second_step cycles a sample: hard sync, unfiltered as the chip's is, its tearing edge the sound."""
        cycles = voice.second_phase + second_step * steps
        voice.second_phase = (voice.second_phase + second_step * len(steps)) % 1.0
        places = ((cycles % 1.0) * ratio) % 1.0
        if self.wave_kind == TRIANGLE:
            out = 1.0 - 4.0 * numpy.abs(places - 0.5)
        elif self.wave_kind == PULSE:
            out = numpy.where(places < width, 1.0, -1.0)
        else:
            out = 2.0 * places - 1.0
        return out.astype(numpy.float32)


class PocketOscillator:
    """The handheld chip's voice: pulse, wave or noise, the tables or noise it reads, and its sweep's pace, 0 for none,
    direction and step."""

    __slots__ = ('chip_voice', 'tables', 'noise', 'sweep_pace', 'sweep_up', 'sweep_step', 'rate')

    def __init__(self, *, spec, rate):
        self.rate = rate
        self.chip_voice = spec['chip_voice']
        self.tables = None
        self.noise = None
        if self.chip_voice == PULSE:
            self.tables = tables.duty_tables(duty=spec['duty'], rate=rate)
        elif self.chip_voice == WAVE:
            self.tables = tables.shape_tables(shape=spec['wave_shape'], rate=rate)
        else:
            self.noise = tables.shift_register_noise(short=spec['noise'] == SHORT)
        self.sweep_pace = spec['sweep_pace']
        self.sweep_up = spec['sweep_up']
        self.sweep_step = spec['sweep_step']

    def begin(self, *, voice, rate):
        voice.phase = 0.0
        voice.period = min(LONGEST_PERIOD, max(0, int(round(PERIODS - CHIP_CLOCK / frequency_of(voice.pitch)))))
        voice.ticks = 0

    def wave(self, *, voice, first, count, pitch, moved):
        rate = self.rate
        if self.sweep_pace:
            self._sweep(voice=voice, seconds=(first - voice.start) / rate)
        frequency = CHIP_CLOCK / (PERIODS - voice.period)
        if self.noise is not None:
            # Noise is clocked by the pitch, a step of the register each sixteenth of the note's cycle.
            positions = read_positions(voice=voice, speed=frequency * NOISE_STEPS_PER_CYCLE / rate, count=count, moved=pitch)
            out = self.noise[positions.astype(numpy.int64) % len(self.noise)]
            voice.phase %= len(self.noise)
            return out
        table = self.tables[tables.band_of(frequency)]
        positions = read_positions(voice=voice, speed=frequency * tables.TABLE_SIZE / rate, count=count, moved=pitch)
        voice.phase %= tables.TABLE_SIZE
        return table[positions.astype(numpy.int64) & tables.TABLE_MASK].copy()

    def _sweep(self, *, voice, seconds):
        """Move the period register as many sweep ticks as have come, each by itself shifted right by the step, up or down;
        past the register's top the chip goes silent, as the real one does."""
        due = int(seconds * SWEEP_TICKS / self.sweep_pace)
        while voice.ticks < due:
            change = voice.period >> self.sweep_step
            period = voice.period + change if self.sweep_up else voice.period - change
            voice.ticks += 1
            if period > LONGEST_PERIOD:
                voice.silent = True
                return
            voice.period = max(0, period)


class AcidOscillator:
    """The acid bass's oscillator: the saw's tables, whether it is the transistor's square, and its tuning in semitones."""

    __slots__ = ('saw', 'square', 'tuning', 'rate')

    def __init__(self, *, spec, rate):
        self.rate = rate
        self.saw = tables.waveform_tables(waveform=SAW, rate=rate)
        self.square = spec['acid_wave'] != SAW
        self.tuning = spec['tuning']

    def begin(self, *, voice, rate):
        voice.phase = 0.0

    def wave(self, *, voice, first, count, pitch, moved):
        rate = self.rate
        shift = self.tuning
        if pitch is not None:
            shift = pitch + self.tuning
        speeds = numpy.exp2((voice.pitch + shift - MIDDLE_A) / SEMITONES) * (A_FREQUENCY * tables.TABLE_SIZE / rate)
        if numpy.ndim(speeds) == 0:
            speeds = numpy.full(count, float(speeds))
        positions, after = modulation.phases(phase=voice.phase, speeds=speeds)
        voice.phase = after % tables.TABLE_SIZE
        saw = self.saw[tables.band_of(frequency_of(voice.pitch))]
        indexes = positions.astype(numpy.int64)
        out = saw[indexes & tables.TABLE_MASK]
        if self.square:
            pulse = (out - saw[(indexes + tables.TABLE_SIZE // 2) & tables.TABLE_MASK]) * 0.5
            out = numpy.tanh(pulse * SQUARE_PUSH) / math.tanh(SQUARE_PUSH)
        return out.astype(numpy.float32)


def compiled_oscillators(*, spec, rate):
    """Return an oscillator module from its settings."""
    kind = spec['type']
    if kind == SID:
        return SidOscillator(spec=spec, rate=rate)
    if kind == POCKET:
        return PocketOscillator(spec=spec, rate=rate)
    if kind == ACID:
        return AcidOscillator(spec=spec, rate=rate)
    return BasicOscillators(spec=spec, rate=rate)


def read_positions(*, voice, speed, count, moved):
    """Return a chunk's read positions from the voice's phase, moving the phase on, the pitch moved sample by sample where moved
    holds semitones."""
    if moved is None:
        positions = voice.phase + speed * numpy.arange(count, dtype=numpy.float64)
        voice.phase += speed * count
        return positions
    positions, voice.phase = modulation.phases(phase=voice.phase, speeds=speed * numpy.exp2(moved / SEMITONES))
    return positions


def moved_speed(*, pitch, spread, cents):
    """Return how much faster an oscillator reads each sample of a chunk, its pitch moved in semitones and its detune spread by
    a share of itself."""
    octaves = 0.0
    if pitch is not None:
        octaves = pitch / SEMITONES
    if spread is not None and cents:
        octaves = octaves + spread * (cents / CENTS)
    return numpy.exp2(octaves)
