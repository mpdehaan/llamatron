# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""internal_tools/normalize_wave.py, one quick check of its main path: a quiet file is raised until its peak is one decibel below full scale. A tool fails loudly when it is run, so one check is enough (.claude/rules/TESTING.md)."""

import contextlib
import importlib.util
import io
import numpy
import os
import pathlib
import tempfile
import unittest
import wave

from llamatron.exporters import wave_level
from llamatron.exporters.wave_level import peak_sample

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'normalize_wave.py'
MODULE_NAME = 'normalize_wave'
FRAME_RATE = 8000
STEREO = 2
QUIET_PEAK = 3000
# A wave's samples, quiet and loud places in it, so that their difference can be checked.
QUIET_PART = 500
SECONDS = 1
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
        self.assertLess(target, wave_level.HIGHEST_SAMPLE)

if __name__ == '__main__':
    unittest.main()
