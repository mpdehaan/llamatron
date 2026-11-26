# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard fitting a tune written by hand to the chords its section now hears (music_theory/harmony/tune_fit.py)."""

import unittest

from llamatron.model.schema.file_format import Row
from llamatron.wizards.create_song import wizard_names
from llamatron.wizards.create_song.wizard_choices import WizardChoices

A_GENRE = 'rock'
A_SUBGENRE = 'folk rock'
A_KIND = 'verse'
A_SEED = 7
OTHER_CHORDS = [2, 5]


class TestWizardFitsTune(unittest.TestCase):

    def chosen(self):
        choices = WizardChoices()
        choices.set_genre(A_GENRE)
        choices.set_subgenre(A_SUBGENRE)
        choices.set_seed(A_SEED)
        return choices

    def test_only_a_tune_written_by_hand_has_chords_to_watch(self):
        choices = self.chosen()
        tune_choices = choices.get_tunes()
        tunes = tune_choices
        self.assertEqual(tunes.own_tune_chords(), {})
        tunes.set_tune_pattern(kind=A_KIND, pattern=tunes.tune_pattern(A_KIND))
        self.assertEqual(list(tunes.own_tune_chords()), [A_KIND])
        with self.assertRaises(ValueError):
            self.chosen().get_tunes().fit_tune(A_KIND)

    def test_a_tune_is_fitted_to_the_chords_its_section_now_hears_and_stays_the_persons_own(self):
        choices = self.chosen()
        tune_choices = choices.get_tunes()
        tunes = tune_choices
        written = tunes.tune_pattern(A_KIND)
        tunes.set_tune_pattern(kind=A_KIND, pattern=written)
        before = tunes.own_tune_chords()
        choices.section(tunes.tune_place(A_KIND)).set_own(field=wizard_names.ARRANGER_CHORDS, value=OTHER_CHORDS)
        self.assertNotEqual(tunes.own_tune_chords(), before)
        self.assertEqual(tunes.tune_pattern(A_KIND), written)
        tunes.fit_tune(A_KIND)
        fit = tunes.tune_pattern(A_KIND)
        self.assertTrue(tunes.tune_is_own(A_KIND))
        self.assertNotEqual(fit[Row.DEGREE], written[Row.DEGREE])
        self.assertEqual([degree is None for degree in fit[Row.DEGREE]], [degree is None for degree in written[Row.DEGREE]])
        self.assertEqual(fit[Row.TIE], written[Row.TIE])
        tunes.fit_tune(A_KIND)
        self.assertEqual(tunes.tune_pattern(A_KIND), fit)
