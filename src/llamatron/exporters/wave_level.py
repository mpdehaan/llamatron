# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""A WAV file's level: the whole file raised or lowered until its loudest moment is 1 dB below the most a WAV can hold.

It is peak normalization, the usual best practice when music is prepared for streaming or Apple Music: the
whole file moves by one amount, so its quiet and loud parts keep their difference, and a peak 1 dB below
full scale (-1 dBFS, about 89%) leaves the headroom a conversion to AAC or MP3 needs. Nothing is compressed or
limited. The WAV export (exporters/wave_fluidsynth.py) and internal_tools/normalize_wave.py, which the demos'
WAV files go through, both use it. It reads and writes 16-bit PCM WAV, which FluidSynth writes, and refuses
anything else; a file is written beside itself and then put in its place, so it is never left half written.
"""

import os
import wave

import numpy

from llamatron.strings.errors import ERR_NOT_16_BIT_WAVE

# The loudest moment's level after normalizing, in decibels below full scale.
PEAK_DECIBELS = -1.0
DECIBELS_A_TENFOLD = 20
SAMPLE_BYTES = 2
BITS_A_BYTE = 8
LOWEST_SAMPLE = -32768
HIGHEST_SAMPLE = 32767
SAMPLE_TYPE = numpy.int16
PARTIAL_SUFFIX = '.part'
READ = 'rb'
WRITE = 'wb'


def peak_sample(*, peak_decibels=PEAK_DECIBELS):
    """Return the largest sample a normalized file holds, peak_decibels below full scale."""
    return HIGHEST_SAMPLE * 10 ** (peak_decibels / DECIBELS_A_TENFOLD)


def normalized_samples(samples, *, peak_decibels=PEAK_DECIBELS):
    """Return the samples scaled so that the largest is peak_decibels below full scale, and the factor, or the samples and None when they are all silent."""
    loudest = int(numpy.max(numpy.abs(samples.astype(numpy.int32)))) if samples.size else 0
    if loudest == 0:
        return samples, None
    factor = peak_sample(peak_decibels=peak_decibels) / loudest
    scaled = numpy.clip(numpy.round(samples.astype(numpy.float64) * factor), LOWEST_SAMPLE, HIGHEST_SAMPLE)
    return scaled.astype(SAMPLE_TYPE), factor


def normalize_wave(path, *, peak_decibels=PEAK_DECIBELS):
    """Normalize the WAV file in place, and return how many decibels it moved, or None when it is silent and was left as it is."""
    with wave.open(path, READ) as file:
        parameters = file.getparams()
        frames = file.readframes(parameters.nframes)
    if parameters.sampwidth != SAMPLE_BYTES:
        raise ValueError(ERR_NOT_16_BIT_WAVE.format(path=path, bits=parameters.sampwidth * BITS_A_BYTE))
    samples, factor = normalized_samples(numpy.frombuffer(frames, dtype=SAMPLE_TYPE), peak_decibels=peak_decibels)
    if factor is None:
        return None
    partial = path + PARTIAL_SUFFIX
    with wave.open(partial, WRITE) as file:
        file.setparams(parameters)
        file.writeframes(samples.tobytes())
    os.replace(partial, path)
    return DECIBELS_A_TENFOLD * float(numpy.log10(factor))
