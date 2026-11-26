# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The wavetables the built-in instruments read: one cycle of each waveform, band-limited for each octave, so that a note
never holds a harmonic above half the sample rate, the aliasing that makes naive waves harsh at high notes.

A table is TABLE_SIZE samples, a power of two, so that a read position wraps with a mask. Each waveform has a table for
each octave band, built by adding its harmonics up to the highest that stays under half the sample rate at the top note of
the band; a note reads the table of its octave. Built once, when an instrument is compiled, and never while playing.
"""

import functools
import math
import numpy

from llamatron.model.schema.file_format import Waveform

TABLE_SIZE = 2048
TABLE_MASK = TABLE_SIZE - 1
# How many steps of the SID-style chip's noise are kept.
SID_NOISE_STEPS = 32768
# The lowest note a table band serves, as a frequency, and how many octave bands there are above it.
LOWEST_FREQUENCY = 8.0
OCTAVE_BANDS = 12




def harmonic_amplitudes(*, waveform, count):
    """Return the amplitude of each harmonic from the first, as a numpy array of count, of a waveform's Fourier series; a
    pulse's are the saw's, since a pulse is read as one saw less another shifted by its width."""
    numbers = numpy.arange(1, count + 1, dtype=numpy.float64)
    if waveform == Waveform.SINE:
        amplitudes = numpy.zeros(count)
        amplitudes[0] = 1.0
        return amplitudes
    if waveform in (Waveform.SAW, Waveform.PULSE):
        return 2.0 / math.pi * ((-1.0) ** (numbers + 1)) / numbers
    if waveform == Waveform.SQUARE:
        return numpy.where(numbers % 2 == 1, 4.0 / (math.pi * numbers), 0.0)
    # The triangle: odd harmonics falling as the square of their number, alternating in sign.
    signs = numpy.where(((numbers - 1) // 2) % 2 == 0, 1.0, -1.0)
    return numpy.where(numbers % 2 == 1, 8.0 / (math.pi ** 2) * signs / numbers ** 2, 0.0)


def band_limited_table(*, waveform, highest_harmonic):
    """Return one cycle of a waveform holding its harmonics up to the highest given, no more than a table can hold, as
    float32, made in one inverse Fourier transform."""
    count = max(1, min(highest_harmonic, TABLE_SIZE // 2 - 1))
    spectrum = numpy.zeros(TABLE_SIZE // 2 + 1, dtype=numpy.complex128)
    # A sine of amplitude a at harmonic n is the bin -i * a * N / 2.
    spectrum[1:count + 1] = -1j * harmonic_amplitudes(waveform=waveform, count=count) * TABLE_SIZE / 2
    table = numpy.fft.irfft(spectrum, n=TABLE_SIZE)
    # Each table peaks at 1, so that every waveform plays at one level.
    return (table / numpy.abs(table).max()).astype(numpy.float32)


@functools.cache
def waveform_tables(*, waveform, rate):
    """Return a waveform's tables, one for each octave band, lowest first, at a sample rate."""
    tables = []
    for band in range(OCTAVE_BANDS):
        top = LOWEST_FREQUENCY * 2 ** (band + 1)
        tables.append(band_limited_table(waveform=waveform, highest_harmonic=int(rate / 2 / top)))
    return tuple(tables)


def band_of(frequency):
    """Return the octave band a frequency reads its table from."""
    if frequency <= LOWEST_FREQUENCY:
        return 0
    return min(OCTAVE_BANDS - 1, int(math.log2(frequency / LOWEST_FREQUENCY)))


def cycle_tables(*, cycle, rate):
    """Return the tables of any one cycle, such as a chip's duty pulse or its 32 steps of drawn wave, one for each octave
    band, lowest first: its harmonics measured by one Fourier transform, then each band keeping those under half the rate,
    so that a stepped chip wave keeps its steps up to where they would alias, and no further."""
    spectrum = numpy.fft.rfft(numpy.repeat(numpy.asarray(cycle, dtype=numpy.float64), TABLE_SIZE // len(cycle)))
    spectrum[0] = 0.0
    tables = []
    for band in range(OCTAVE_BANDS):
        top = LOWEST_FREQUENCY * 2 ** (band + 1)
        kept = numpy.zeros_like(spectrum)
        highest = max(1, min(int(rate / 2 / top), TABLE_SIZE // 2 - 1))
        kept[1:highest + 1] = spectrum[1:highest + 1]
        table = numpy.fft.irfft(kept, n=TABLE_SIZE)
        tables.append((table / max(numpy.abs(table).max(), 1e-9)).astype(numpy.float32))
    return tuple(tables)


@functools.cache
def duty_tables(*, duty, rate):
    """Return the tables of a chip's pulse of a duty, the share of its eight steps it is high."""
    high = int(round(duty * 8))
    return cycle_tables(cycle=[1.0] * high + [-1.0] * (8 - high), rate=rate)


@functools.cache
def shape_tables(*, shape, rate):
    """Return the tables of a drawn wave of 32 steps of four bits, by its shape's name."""
    return cycle_tables(cycle=[step / 7.5 - 1.0 for step in WAVE_SHAPE_STEPS[shape]], rate=rate)


@functools.cache
def shift_register_noise(*, short):
    """Return a chip's noise as the values a shift register gives in turn, -1 or 1: 32767 of the long hiss from 15 bits, or
    127 of the short metallic buzz from 7, the register's two lowest bits made one by exclusive or and fed back at the top."""
    width = 7 if short else 15
    register = (1 << width) - 1
    values = []
    for _ in range((1 << width) - 1):
        bit = (register ^ (register >> 1)) & 1
        register = (register >> 1) | (bit << (width - 1))
        values.append(1.0 if register & 1 else -1.0)
    return numpy.array(values, dtype=numpy.float32)


@functools.cache
def sid_noise():
    """Return the SID-style chip's noise: the values its 23-bit shift register gives in turn, each step read as an eight-bit
    word of its bits, -1 to 1, as the chip outputs it, so that its noise has 256 levels, smoother than the one-bit noise of
    the handheld's chip. 32768 steps, the register's own sequence being far longer than any note's need."""
    register = 0x7FFFF8
    values = []
    for _ in range(SID_NOISE_STEPS):
        bit = ((register >> 22) ^ (register >> 17)) & 1
        register = ((register << 1) | bit) & 0x7FFFFF
        word = (((register >> 20) & 1) << 7 | ((register >> 18) & 1) << 6 | ((register >> 14) & 1) << 5 | ((register >> 11) & 1) << 4
                | ((register >> 9) & 1) << 3 | ((register >> 5) & 1) << 2 | ((register >> 2) & 1) << 1 | (register & 1))
        values.append(word / 127.5 - 1.0)
    return numpy.array(values, dtype=numpy.float32)


def _drawn(function):
    """Return 32 steps of four bits, 0 to 15, drawing a function of the cycle's place from 0 to 1 that answers -1 to 1."""
    return tuple(int(round((function(place / 32.0) + 1.0) * 7.5)) for place in range(32))


# The drawn waves a Pocket sound's wave voice offers, each 32 steps of 0 to 15, as the chip's wave memory holds them.
WAVE_SHAPE_STEPS = {
    'triangle': _drawn(lambda x: 1.0 - 4.0 * abs(x - 0.5)),
    'saw': _drawn(lambda x: 2.0 * x - 1.0),
    'square': _drawn(lambda x: 1.0 if x < 0.5 else -1.0),
    'sine': _drawn(lambda x: math.sin(2.0 * math.pi * x)),
    'organ': _drawn(lambda x: (math.sin(2.0 * math.pi * x) + 0.5 * math.sin(4.0 * math.pi * x) + 0.33 * math.sin(6.0 * math.pi * x)) / 1.5),
}
