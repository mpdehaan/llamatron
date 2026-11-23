# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A tune written by hand fitted to chords that changed under it: long notes that clash move to the nearest chord note, short notes stay."""

from fractions import Fraction
import unittest

from llamatron.model.schema.file_format import PatternSetting, Row
from llamatron.music_theory.harmony import tune_fit
from llamatron.music_theory.harmony.tune_fit import chord_at, fitted, move_to_chord, steps_held

AN_EIGHTH = '1/8'
A_BAR = Fraction(1)
STEPS_IN_BAR = 8
AN_OCTAVE = 4
# The home chord and the chord on the second note of the scale, whose notes are 1, 3, 5 and 2, 4, 6.
HOME = 1
SECOND = 2


def tune(*, degrees, ties, octaves=None):
    return {PatternSetting.STEPS: len(degrees), PatternSetting.STEP_SIZE: AN_EIGHTH, Row.DEGREE: degrees, Row.TIE: ties,
            Row.OCTAVE: octaves or [None if degree is None else AN_OCTAVE for degree in degrees]}


class TestTuneFit(unittest.TestCase):

    def test_a_note_of_the_chord_stays_and_any_other_moves_to_the_nearest_note_of_the_chord_down_where_two_are_as_near(self):
        self.assertEqual([move_to_chord(degree=degree, root=HOME) for degree in (1, 2, 3, 4, 5, 6, 7)], [0, -1, 0, -1, 0, -1, 1])

    def test_a_note_lasts_through_the_steps_tied_to_it_and_no_further(self):
        self.assertEqual(steps_held(ties=[False, True, True, False], degrees=[5, None, None, None], place=0), 3)
        self.assertEqual(steps_held(ties=[False, True, False, True], degrees=[5, 6, None, None], place=0), 1)

    def test_a_bar_hears_its_chord_the_chords_going_round_and_the_first_of_two_that_share_a_bar(self):
        chords = [{tune_fit.DEGREE: HOME}, [{tune_fit.DEGREE: SECOND}, {tune_fit.DEGREE: HOME}], SECOND]
        self.assertEqual([chord_at(chords=chords, bar=bar) for bar in range(4)], [HOME, SECOND, SECOND, HOME])

    def test_long_notes_that_clash_move_and_short_notes_and_rests_stay(self):
        self.assertEqual(tune_fit.LONG_NOTE, Fraction(1, 4))
        written = tune(degrees=[2, None, 2, 4, None, None, 3, None], ties=[False, True, False, False, False, False, False, True])
        moved = fitted(pattern=written, chords=[{tune_fit.DEGREE: HOME}], bar=A_BAR)
        # The long 2 moves to 1, the short 2 and the short 4 pass, and the long 3 is a note of the chord.
        self.assertEqual(moved[Row.DEGREE], [1, None, 2, 4, None, None, 3, None])
        self.assertEqual(moved[Row.TIE], written[Row.TIE])
        self.assertEqual(written[Row.DEGREE][0], 2)

    def test_each_bar_is_fitted_to_its_own_chord_and_a_note_moved_past_the_top_of_the_scale_goes_up_an_octave(self):
        long_note = [False, True, True, True, True, True, True, True]
        written = tune(degrees=[3, *[None] * 7, 3, *[None] * 7, 7, *[None] * 7], ties=long_note * 3)
        moved = fitted(pattern=written, chords=[{tune_fit.DEGREE: HOME}, {tune_fit.DEGREE: SECOND}, {tune_fit.DEGREE: HOME}], bar=A_BAR)
        self.assertEqual([moved[Row.DEGREE][bar * STEPS_IN_BAR] for bar in range(3)], [3, 2, 1])
        self.assertEqual([moved[Row.OCTAVE][bar * STEPS_IN_BAR] for bar in range(3)], [AN_OCTAVE, AN_OCTAVE, AN_OCTAVE + 1])

    def test_a_pattern_with_no_notes_and_a_tune_with_no_chords_come_back_as_they_were(self):
        blank = {PatternSetting.STEPS: STEPS_IN_BAR, PatternSetting.STEP_SIZE: AN_EIGHTH}
        self.assertEqual(fitted(pattern=blank, chords=[{tune_fit.DEGREE: HOME}], bar=A_BAR), blank)
        written = tune(degrees=[2, None], ties=[False, True])
        self.assertEqual(fitted(pattern=written, chords=[], bar=A_BAR), written)
