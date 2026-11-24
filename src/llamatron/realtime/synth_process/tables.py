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
