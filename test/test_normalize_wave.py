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

"""internal_tools/normalize_wave.py moves a WAV file's loudest moment to 1 dB below full scale, keeping everything else about the file."""

import contextlib
import importlib.util
import io
import os
import pathlib
import tempfile
import unittest
import wave

import numpy

from llamatron.exporters.wave_level import HIGHEST_SAMPLE, PARTIAL_SUFFIX, peak_sample

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / 'internal_tools' / 'normalize_wave.py'
MODULE_NAME = 'normalize_wave'
FRAME_RATE = 8000
STEREO = 2
QUIET_PEAK = 3000
LOUD_PEAK = 32767
# A wave's samples, quiet and loud places in it, so that their difference can be checked.
QUIET_PART = 500
SECONDS = 1
EIGHT_BIT = 1
NAME = 'demo.wav'
# How far a sample may be from what the arithmetic says, after rounding to a whole sample.
ROUNDING = 1


def load_script():
    """Load the tool as a module, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_wave(*, path, samples, channels=STEREO, sample_bytes=2):
    """Write the samples, interleaved, as a WAV file."""
    with wave.open(path, 'wb') as file:
        file.setnchannels(channels)
        file.setsampwidth(sample_bytes)
        file.setframerate(FRAME_RATE)
        file.writeframes(samples.tobytes())


def read_wave(path):
    """Return a WAV file's parameters and its samples."""
    with wave.open(path, 'rb') as file:
        parameters = file.getparams()
        return parameters, numpy.frombuffer(file.readframes(parameters.nframes), dtype=numpy.int16)


def samples_with(*, peak, quiet):
    """Return a second of stereo samples whose loudest is peak, with a stretch at quiet, both signs."""
    count = FRAME_RATE * SECONDS * STEREO
    samples = numpy.full(count, quiet, dtype=numpy.int16)
    samples[::2] = -quiet
    samples[count // 2] = -peak
    return samples


class TestNormalizeWave(unittest.TestCase):

    def setUp(self):
        self.tool = load_script()
        self.scratch = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.scratch.name, NAME)

    def tearDown(self):
        self.scratch.cleanup()

    def normalized(self, samples):
        """Write the samples, normalize the file, and return its parameters before and after and its samples after."""
        write_wave(path=self.path, samples=samples)
        before, _ = read_wave(self.path)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.tool.main(argv=[self.path]), 0)
        after, normalized = read_wave(self.path)
        return before, after, normalized

    def test_a_quiet_file_is_raised_until_its_peak_is_one_decibel_below_full_scale(self):
        _, _, samples = self.normalized(samples_with(peak=QUIET_PEAK, quiet=QUIET_PART))
        target = peak_sample()
        self.assertAlmostEqual(int(numpy.max(numpy.abs(samples.astype(numpy.int32)))), target, delta=ROUNDING)
        self.assertLess(target, HIGHEST_SAMPLE)

    def test_the_quiet_and_loud_parts_keep_their_difference(self):
        _, _, samples = self.normalized(samples_with(peak=QUIET_PEAK, quiet=QUIET_PART))
        factor = peak_sample() / QUIET_PEAK
        self.assertAlmostEqual(int(samples[1]), QUIET_PART * factor, delta=ROUNDING)
        self.assertAlmostEqual(int(samples[0]), -QUIET_PART * factor, delta=ROUNDING)

    def test_a_file_at_full_scale_is_lowered_to_the_same_peak(self):
        _, _, samples = self.normalized(samples_with(peak=LOUD_PEAK, quiet=QUIET_PART))
        self.assertAlmostEqual(int(numpy.max(numpy.abs(samples.astype(numpy.int32)))), peak_sample(), delta=ROUNDING)

    def test_the_file_keeps_its_channels_rate_and_length(self):
        before, after, _ = self.normalized(samples_with(peak=QUIET_PEAK, quiet=QUIET_PART))
        self.assertEqual((after.nchannels, after.sampwidth, after.framerate, after.nframes), (before.nchannels, before.sampwidth, before.framerate, before.nframes))
        self.assertFalse(os.path.exists(self.path + PARTIAL_SUFFIX))

    def test_a_silent_file_is_left_as_it_is(self):
        silent = numpy.zeros(FRAME_RATE * STEREO, dtype=numpy.int16)
        write_wave(path=self.path, samples=silent)
        self.assertEqual(self.tool.normalize(self.path), self.tool.SILENT.format(path=self.path))
        _, samples = read_wave(self.path)
        self.assertTrue(numpy.array_equal(samples, silent))

    def test_a_file_that_is_not_16_bit_is_refused_and_left_alone(self):
        write_wave(path=self.path, samples=numpy.zeros(FRAME_RATE, dtype=numpy.uint8), channels=1, sample_bytes=EIGHT_BIT)
        written = pathlib.Path(self.path).read_bytes()
        with contextlib.redirect_stderr(io.StringIO()) as printed:
            self.assertEqual(self.tool.main(argv=[self.path]), 1)
        self.assertIn(self.tool.NOT_16_BIT.format(path=self.path, bits=EIGHT_BIT * 8), printed.getvalue())
        self.assertEqual(pathlib.Path(self.path).read_bytes(), written)


if __name__ == '__main__':
    unittest.main()
