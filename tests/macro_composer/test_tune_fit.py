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

"""A tune written by hand fitted to chords that changed under it: long notes that clash move to the nearest chord note, short notes stay."""

from fractions import Fraction
import unittest

from llamatron.composition.file_format import PatternSetting, Row
from llamatron.macro_composer import arranger, tune_fit
from llamatron.macro_composer.tune_fit import chord_at, fitted, move_to_chord, steps_held
from llamatron.macro_composer.wizard_choices import WizardChoices

A_GENRE = 'rock'
A_SUBGENRE = 'folk rock'
A_KIND = 'verse'
A_SEED = 7
AN_EIGHTH = '1/8'
A_BAR = Fraction(1)
STEPS_IN_BAR = 8
AN_OCTAVE = 4
# The home chord and the chord on the second note of the scale, whose notes are 1, 3, 5 and 2, 4, 6.
HOME = 1
SECOND = 2
OTHER_CHORDS = [2, 5]


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


class TestWizardFitsTune(unittest.TestCase):

    def chosen(self):
        choices = WizardChoices()
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        choices.set_seed(A_SEED)
        return choices

    def test_only_a_tune_written_by_hand_has_chords_to_watch(self):
        choices = self.chosen()
        self.assertEqual(choices.get_tunes().own_tune_chords(), {})
        choices.get_tunes().set_tune_pattern(kind=A_KIND, pattern=choices.get_tunes().tune_pattern(A_KIND))
        self.assertEqual(list(choices.get_tunes().own_tune_chords()), [A_KIND])
        with self.assertRaises(ValueError):
            self.chosen().get_tunes().fit_tune(A_KIND)

    def test_a_tune_is_fitted_to_the_chords_its_section_now_hears_and_stays_the_persons_own(self):
        choices = self.chosen()
        written = choices.get_tunes().tune_pattern(A_KIND)
        choices.get_tunes().set_tune_pattern(kind=A_KIND, pattern=written)
        before = choices.get_tunes().own_tune_chords()
        choices.section(choices.get_tunes().tune_place(A_KIND)).set_own(field=arranger.CHORDS, value=OTHER_CHORDS)
        self.assertNotEqual(choices.get_tunes().own_tune_chords(), before)
        self.assertEqual(choices.get_tunes().tune_pattern(A_KIND), written)
        choices.get_tunes().fit_tune(A_KIND)
        fit = choices.get_tunes().tune_pattern(A_KIND)
        self.assertTrue(choices.get_tunes().tune_is_own(A_KIND))
        self.assertNotEqual(fit[Row.DEGREE], written[Row.DEGREE])
        self.assertEqual([degree is None for degree in fit[Row.DEGREE]], [degree is None for degree in written[Row.DEGREE]])
        self.assertEqual(fit[Row.TIE], written[Row.TIE])
        choices.get_tunes().fit_tune(A_KIND)
        self.assertEqual(choices.get_tunes().tune_pattern(A_KIND), fit)
