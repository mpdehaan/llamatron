# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests of a pattern's scale length, how many notes the scale has that the pattern was written for: kept, written, read back, refused, and cleared by a drum pattern."""

import unittest

from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.objects.pattern import Pattern
from llamatron.model.vocabulary import limits
from llamatron.model.vocabulary.file_format import PatternSetting, Section
from llamatron.user_strings import errors
from tests.support.rendering import song_from_data
from tests.support.song_testing import lead_data
from tests.support.ui_testing import fixed_text

A_STEP = [1, 0.25]
STEPS = 4
PENTATONIC = 5
# The pattern of the test data that the lead plays.
A_PATTERN = 'a'


def a_pattern(**settings):
    return Pattern(steps=STEPS, rows={}, **settings)


class TestScaleLength(unittest.TestCase):

    def test_a_pattern_is_written_for_any_scale_until_told_and_writes_nothing(self):
        pattern = a_pattern()
        self.assertIsNone(pattern.get_scale_length())
        self.assertNotIn(PatternSetting.SCALE_LENGTH, pattern.to_data())
        self.assertTrue(pattern.suits_scale_of(PENTATONIC))

    def test_every_length_can_be_set_written_and_cleared(self):
        pattern = a_pattern()
        for length in range(limits.MIN_SCALE_LENGTH, limits.MAX_SCALE_LENGTH + 1):
            pattern.set_scale_length(length)
            self.assertEqual(pattern.get_scale_length(), length)
            self.assertEqual(pattern.to_data()[PatternSetting.SCALE_LENGTH], length)
        pattern.set_scale_length(None)
        self.assertNotIn(PatternSetting.SCALE_LENGTH, pattern.to_data())

    def test_it_suits_only_a_scale_of_its_length(self):
        pattern = a_pattern(scale_length=limits.NEW_PATTERN_SCALE_LENGTH)
        self.assertTrue(pattern.suits_scale_of(limits.NEW_PATTERN_SCALE_LENGTH))
        self.assertFalse(pattern.suits_scale_of(PENTATONIC))

    def test_a_length_out_of_range_is_refused_by_the_setter_and_by_a_file_in_the_same_words(self):
        pattern = a_pattern()
        for bad in (limits.MIN_SCALE_LENGTH - 1, limits.MAX_SCALE_LENGTH + 1, str(limits.NEW_PATTERN_SCALE_LENGTH)):
            with self.assertRaises(ValueError) as refused:
                pattern.set_scale_length(bad)
            self.assertIn(fixed_text(errors.ERR_BAD_SCALE_LENGTH), str(refused.exception))
            data = lead_data(A_STEP)
            data[Section.PATTERNS][A_PATTERN][PatternSetting.SCALE_LENGTH] = bad
            with self.assertRaises(SongFileError) as unread:
                song_from_data(data)
            self.assertIn(fixed_text(errors.ERR_BAD_SCALE_LENGTH), str(unread.exception))
        self.assertIsNone(pattern.get_scale_length())

    def test_it_is_read_back_from_a_file_and_kept_by_a_copy(self):
        data = lead_data(A_STEP)
        data[Section.PATTERNS][A_PATTERN][PatternSetting.SCALE_LENGTH] = PENTATONIC
        pattern = song_from_data(data).get_pattern(A_PATTERN)
        self.assertEqual(pattern.get_scale_length(), PENTATONIC)
        self.assertEqual(pattern.copy().get_scale_length(), PENTATONIC)

    def test_a_drum_pattern_has_none(self):
        pattern = a_pattern(scale_length=PENTATONIC)
        pattern.set_drum(True)
        self.assertIsNone(pattern.get_scale_length())
