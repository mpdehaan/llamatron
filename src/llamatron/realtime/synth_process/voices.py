# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tonal engines of the Synthesis Process, each a compiled patch that starts a voice and sounds it a chunk at a time.

A Basic patch reads band-limited tables through an attack, decay, sustain and release. A SID patch is one voice of the
classic home computer's chip as players use it: a triangle, saw, pulse whose width can sweep, or noise clocked by the pitch,
ring modulated or synced by a second oscillator an interval away, an arpeggio stepped at the chip's frame rate of 50 a
second, glide, and the same envelope. A Pocket patch is one voice of the handheld's chip: a pulse of one of four duties, the
drawn wave of 32 steps of four bits, or a shift register's noise, through the chip's envelope of sixteen levels stepped 64
times a second at a pace, and its pitch sweep, which moves the chip's period register 128 times a second at a pace.

Speed rules this module, as it does the engine (the user's yes to break the style rules here): each patch's sound() makes a
chunk in whole-array numpy reads, its values held in plain attributes, never a loop over samples.
"""

import math
import numpy

from llamatron.realtime.synth_process import modulation as modulation_values, tables

MIDDLE_A = 69
A_FREQUENCY = 440.0
# A voice whose envelope has fallen below this is silent and is dropped.
SILENT = 1e-4
# How long a note takes to reach full level from silence at the least, so that no start clicks.
SHORTEST_ATTACK_SECONDS = 0.001
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
# The handheld chip's clocks: its envelope steps 64 times a second, its sweep 128, and its period register is eleven bits
# of a 131072 Hz clock, a pulse's frequency 131072 / (2048 - period).
ENVELOPE_TICKS = 64.0
SWEEP_TICKS = 128.0
CHIP_CLOCK = 131072.0
LONGEST_PERIOD = 2047
PERIODS = 2048
CHIP_LEVELS = 15.0
# A chip note has no release of its own: a note off fades it out over this long, so that it never clicks.
CHIP_FADE_SECONDS = 0.005


def frequency_of(pitch):
    """Return a MIDI number's frequency in hertz, equal tempered from A 440, a fraction of a number bending between."""
    return A_FREQUENCY * 2.0 ** ((pitch - MIDDLE_A) / 12.0)


class BasicPatch:
    """A compiled Basic instrument: its oscillators, each (tables by octave band, detune in cents, level), its envelope in
    seconds and its sustain level, how many notes it plays at once, its volume, and its effects in order."""

    __slots__ = ('oscillators', 'attack', 'decay', 'sustain', 'release', 'voices', 'volume', 'effects', 'modulation')
    # Only Fishline slides from a held note to the next (acid.py).
    slides = False

    def __init__(self, *, oscillators, envelope, voices=4, volume=0.5, effects=()):
        self.oscillators = oscillators
        self.attack, self.decay, self.sustain, self.release = envelope
        self.voices = voices
        self.volume = volume
        self.effects = list(effects)
        self.modulation = modulation_values.NO_MODULATION

    def begin(self, *, voice, rate):
        for oscillator_tables, cents, oscillator_level in self.oscillators:
            frequency = frequency_of(voice.pitch) * 2.0 ** (cents / 1200.0)
            speed = frequency * tables.TABLE_SIZE / rate
            voice.oscillators.append((oscillator_tables[tables.band_of(frequency)], speed, 0.0, oscillator_level, cents))

    def sound(self, *, voice, first, count, rate):
        out = numpy.zeros(count, dtype=numpy.float32)
        now = self.modulation.now
        pitch = now.get(modulation_values.PITCH)
        spread = now.get(modulation_values.DETUNE_SPREAD)
        steps = None
        if pitch is None and spread is None:
            steps = numpy.arange(count, dtype=numpy.float64)
        read = []
        for table, speed, phase, oscillator_level, cents in voice.oscillators:
            if steps is not None:
                positions = phase + speed * steps
                after = phase + speed * count
            else:
                positions, after = modulation_values.phases(phase=phase, speeds=speed * moved_speed(pitch=pitch, spread=spread, cents=cents))
            out += table[positions.astype(numpy.int64) & tables.TABLE_MASK] * oscillator_level
            read.append((table, speed, after % tables.TABLE_SIZE, oscillator_level, cents))
        voice.oscillators = read
        out *= envelope(patch=self, voice=voice, first=first, count=count, rate=rate)
        return out


class SidPatch:
    """A compiled SID-style instrument: its wave and the tables it reads, its pulse width and sweep a second, its
    modulation, ring or sync, and the interval of the oscillator that does it, its arpeggio in semitones, its glide in
    seconds, its envelope as Basic's, voices, volume and effects, and the pitch it last played, which a glide starts from."""

    __slots__ = ('wave', 'saw', 'triangle', 'noise', 'pulse_width', 'pulse_sweep', 'interaction', 'interval', 'arpeggio', 'glide', 'attack',
                 'decay', 'sustain', 'release', 'voices', 'volume', 'effects', 'last_pitch', 'modulation')
    # Only Fishline slides from a held note to the next (acid.py).
    slides = False

    def __init__(self, *, spec, rate, effects):
        """spec is the sound as llamatron gives it (model/objects/built_in_sound.py), effects its effects compiled."""
        self.wave = spec['wave']
        self.saw = tables.waveform_tables(waveform='saw', rate=rate)
        self.triangle = tables.waveform_tables(waveform='triangle', rate=rate)
        self.noise = tables.sid_noise()
        self.pulse_width = spec['pulse_width']
        self.pulse_sweep = spec['pulse_sweep']
        self.interaction = spec['modulation']
        self.interval = spec['interval']
        self.arpeggio = tuple(spec['arpeggio'])
        self.glide = spec['glide']
        self.attack, self.decay, self.sustain, self.release = spec['envelope']
        self.voices = spec['voices']
        self.volume = spec['volume']
        self.effects = list(effects)
        self.last_pitch = None
        self.modulation = modulation_values.NO_MODULATION

    def begin(self, *, voice, rate):
        voice.glide_from = voice.pitch
        if self.glide > 0 and self.last_pitch is not None:
            voice.glide_from = self.last_pitch
        self.last_pitch = voice.pitch
        voice.phase = 0.0
        voice.second_phase = 0.0

    def sound(self, *, voice, first, count, rate):
        seconds = (first - voice.start) / rate
        pitch = voice.pitch
        if self.glide > 0:
            pitch += (voice.glide_from - voice.pitch) * math.exp(-seconds / self.glide)
        if self.arpeggio:
            pitch += self.arpeggio[int(seconds * FRAMES_PER_SECOND) % len(self.arpeggio)]
        now = self.modulation.now
        moved = now.get(modulation_values.PITCH)
        if moved is not None and self.interaction != 'off':
            # Ring and sync follow the pitch's movement a chunk at a time.
            pitch += float(moved.mean())
            moved = None
        frequency = frequency_of(pitch)
        steps = numpy.arange(count, dtype=numpy.float64)
        if self.interaction == 'sync':
            second = frequency_of(pitch + self.interval)
            out = self._synced(voice=voice, ratio=frequency / second, second_step=second / rate, steps=steps, width=self._width(seconds))
        else:
            positions = read_positions(voice=voice, speed=frequency * tables.TABLE_SIZE / rate, count=count, moved=moved)
            voice.phase %= tables.TABLE_SIZE
            out = self._wave(frequency=frequency, positions=positions, seconds=seconds)
            if self.interaction == 'ring':
                out *= self._ring(voice=voice, pitch=pitch, steps=steps, rate=rate)
        out *= envelope(patch=self, voice=voice, first=first, count=count, rate=rate)
        return out

    def _wave(self, *, frequency, positions, seconds):
        """Return the wave read at a chunk's positions, band-limited but for noise, as the chip's own noise is."""
        band = tables.band_of(frequency)
        indexes = positions.astype(numpy.int64)
        if self.wave == 'saw':
            return self.saw[band][indexes & tables.TABLE_MASK].copy()
        if self.wave == 'triangle':
            return self.triangle[band][indexes & tables.TABLE_MASK].copy()
        if self.wave == 'noise':
            return self.noise[(positions * SID_NOISE_STEPS_PER_CYCLE / tables.TABLE_SIZE).astype(numpy.int64) % len(self.noise)]
        # A band-limited pulse is one saw less another shifted by its width, which also leaves it with no offset.
        width = self._width(seconds)
        wobble = self.modulation.now.get(modulation_values.PULSE_WIDTH)
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
        if self.wave == 'triangle':
            out = 1.0 - 4.0 * numpy.abs(places - 0.5)
        elif self.wave == 'pulse':
            out = numpy.where(places < width, 1.0, -1.0)
        else:
            out = 2.0 * places - 1.0
        return out.astype(numpy.float32)


class PocketPatch:
    """A compiled Pocket instrument: its voice, pulse, wave or noise, the tables or noise it reads, its envelope's start
    level of fifteen, its pace in ticks, 0 holding, and whether it steps up, its sweep's pace, 0 for none, direction and
    step, its voices, volume and effects."""

    __slots__ = ('chip_voice', 'tables', 'noise', 'start_level', 'level_pace', 'level_up', 'sweep_pace', 'sweep_up', 'sweep_step', 'voices',
                 'volume', 'effects', 'modulation')
    # Only Fishline slides from a held note to the next (acid.py).
    slides = False

    def __init__(self, *, spec, rate, effects):
        """spec is the sound as llamatron gives it (model/objects/built_in_sound.py), effects its effects compiled."""
        self.chip_voice = spec['chip_voice']
        self.tables = None
        self.noise = None
        if self.chip_voice == 'pulse':
            self.tables = tables.duty_tables(duty=spec['duty'], rate=rate)
        elif self.chip_voice == 'wave':
            self.tables = tables.shape_tables(shape=spec['wave_shape'], rate=rate)
        else:
            self.noise = tables.shift_register_noise(short=spec['noise'] == 'short')
        self.start_level = spec['start_level']
        self.level_pace = spec['level_pace']
        self.level_up = spec['level_up']
        self.sweep_pace = spec['sweep_pace']
        self.sweep_up = spec['sweep_up']
        self.sweep_step = spec['sweep_step']
        self.voices = spec['voices']
        self.volume = spec['volume']
        self.effects = list(effects)
        self.modulation = modulation_values.NO_MODULATION

    def begin(self, *, voice, rate):
        voice.phase = 0.0
        voice.period = min(LONGEST_PERIOD, max(0, int(round(PERIODS - CHIP_CLOCK / frequency_of(voice.pitch)))))
        voice.ticks = 0

    def sound(self, *, voice, first, count, rate):
        seconds = (first - voice.start) / rate
        if self.sweep_pace:
            self._sweep(voice=voice, seconds=seconds)
        frequency = CHIP_CLOCK / (PERIODS - voice.period)
        moved = self.modulation.now.get(modulation_values.PITCH)
        if self.noise is not None:
            # Noise is clocked by the pitch, a step of the register each sixteenth of the note's cycle.
            positions = read_positions(voice=voice, speed=frequency * NOISE_STEPS_PER_CYCLE / rate, count=count, moved=moved)
            out = self.noise[positions.astype(numpy.int64) % len(self.noise)]
            voice.phase %= len(self.noise)
        else:
            table = self.tables[tables.band_of(frequency)]
            positions = read_positions(voice=voice, speed=frequency * tables.TABLE_SIZE / rate, count=count, moved=moved)
            out = table[positions.astype(numpy.int64) & tables.TABLE_MASK].copy()
            voice.phase %= tables.TABLE_SIZE
        out *= numpy.float32(self._level(voice=voice, seconds=seconds) * voice.level)
        if voice.release_at is not None:
            out *= self._fade(voice=voice, first=first, count=count, rate=rate)
        return out

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

    def _level(self, *, voice, seconds):
        """Return the envelope's level from 0 to 1, stepped from its start a level each pace's ticks, up or down, the voice
        silent once it steps to nothing."""
        level = self.start_level
        if self.level_pace:
            moved = int(seconds * ENVELOPE_TICKS / self.level_pace)
            level = min(CHIP_LEVELS, level + moved) if self.level_up else max(0, level - moved)
        if level == 0 and (self.level_pace or self.start_level == 0) and not self.level_up:
            voice.silent = True
        return level / CHIP_LEVELS

    def _fade(self, *, voice, first, count, rate):
        """Return the short fade a note off brings, the voice silent once it is over."""
        since = numpy.arange(first, first + count, dtype=numpy.float64) - voice.release_at
        fade = numpy.clip(1.0 - since / (CHIP_FADE_SECONDS * rate), 0.0, 1.0)
        if since[-1] >= CHIP_FADE_SECONDS * rate:
            voice.silent = True
        return fade.astype(numpy.float32)


def read_positions(*, voice, speed, count, moved):
    """Return a chunk's read positions from the voice's phase, moving the phase on, the pitch moved sample by sample by an LFO
    where moved holds semitones."""
    if moved is None:
        positions = voice.phase + speed * numpy.arange(count, dtype=numpy.float64)
        voice.phase += speed * count
        return positions
    positions, voice.phase = modulation_values.phases(phase=voice.phase, speeds=speed * numpy.exp2(moved / 12.0))
    return positions


def moved_speed(*, pitch, spread, cents):
    """Return how much faster an oscillator reads each sample of a chunk, its pitch moved by an LFO in semitones and its detune
    spread by a share of itself."""
    octaves = 0.0
    if pitch is not None:
        octaves = pitch / 12.0
    if spread is not None and cents:
        octaves = octaves + spread * (cents / 1200.0)
    return numpy.exp2(octaves)


def envelope(*, patch, voice, first, count, rate):
    """Return a voice's envelope over a stretch of samples: a linear attack, an exponential fall to its sustain, and after
    its release an exponential fall to silence, the voice marked silent once below SILENT."""
    ages = (numpy.arange(count, dtype=numpy.float64) + (first - voice.start))
    attack = max(patch.attack, SHORTEST_ATTACK_SECONDS) * rate
    decay = max(patch.decay, SHORTEST_ATTACK_SECONDS) * rate
    level = numpy.where(ages < attack, ages / attack, patch.sustain + (1.0 - patch.sustain) * numpy.exp(-(ages - attack) / decay))
    if voice.release_at is not None:
        release = max(patch.release, SHORTEST_ATTACK_SECONDS) * rate
        since = numpy.arange(first, first + count, dtype=numpy.float64) - voice.release_at
        at_release_age = voice.release_at - voice.start
        if at_release_age < attack:
            released_from = at_release_age / attack
        else:
            released_from = patch.sustain + (1.0 - patch.sustain) * math.exp(-(at_release_age - attack) / decay)
        falling = released_from * numpy.exp(-numpy.maximum(since, 0.0) / release)
        level = numpy.where(since >= 0, falling, level)
        if since[-1] >= 0 and falling[-1] < SILENT:
            voice.silent = True
    return (level * voice.level).astype(numpy.float32)
