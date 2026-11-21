# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Swing by subgenre: the groove a kind of music is played with, in the song made and as a choice of the wizard's."""

import unittest

from llamatron.composition.groove import FactoryGroove
from llamatron.macro_composer import arranger, wizard_limits
from llamatron.macro_composer.wizard_choices import WizardChoices
from llamatron.support import version
from llamatron.user_strings import errors
from tests.support.ui_testing import fixed_text

SONG_NAME = 'a_song'
A_SEED = 11
ROCK = 'rock'
ROCK_AND_ROLL = 'rock and roll'
PUNK = 'punk'
SIX_EIGHT = 'six-eight ballad'
BLUES = 'blues'
SHUFFLE = 'shuffle'
SOUL_FUNK = 'soul_funk'
FUNK = 'funk'
NOT_A_SWING = 'swing 99'
# The swing each kind that swings is written with.
SWUNG_KINDS = {(ROCK, ROCK_AND_ROLL): FactoryGroove.EIGHTH_SWING_58, ('sixties_pop', 'sunshine'): FactoryGroove.EIGHTH_SWING_58, ('sixties_pop', 'bubblegum'): FactoryGroove.EIGHTH_SWING_58,
               (SOUL_FUNK, 'new orleans'): FactoryGroove.SWING_58, (SOUL_FUNK, FUNK): FactoryGroove.SWING_54}


def chosen(*, genre=ROCK, subgenre=ROCK_AND_ROLL):
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.set_seed(A_SEED)
    return choices


def groove_of(choices):
    """The groove of the song the choices make, or None for a song with none."""
    return choices.made_setlist(name=SONG_NAME, version=version.VERSION).get_song(SONG_NAME).to_data().get(arranger.GROOVE)


class TestSwing(unittest.TestCase):

    def test_a_kind_that_swings_is_made_with_its_groove_and_a_straight_kind_with_none(self):
        for (genre, subgenre), swing in SWUNG_KINDS.items():
            with self.subTest(subgenre=subgenre):
                choices = chosen(genre=genre, subgenre=subgenre)
                self.assertEqual((choices.swing_of_genre(), choices.get_swing(), groove_of(choices)), (swing, swing, swing))
        straight = chosen(subgenre=PUNK)
        self.assertEqual((straight.get_swing(), groove_of(straight)), (arranger.NO_GROOVE, None))

    def test_every_groove_a_template_names_is_one_every_set_has(self):
        for name in arranger.style_names():
            style = arranger.style_named(name)
            for template in style[arranger.TEMPLATES]:
                swing = arranger.style_in(style=style, template=template).get(arranger.GROOVE, arranger.NO_GROOVE)
                self.assertIn(swing, wizard_limits.SWINGS)

    def test_a_song_s_own_swing_is_played_kept_and_given_back_to_the_kind(self):
        choices = chosen(subgenre=PUNK)
        choices.set_swing(FactoryGroove.SWING_62)
        self.assertEqual(groove_of(choices), FactoryGroove.SWING_62)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.get_swing(), FactoryGroove.SWING_62)
        choices.set_swing(arranger.NO_GROOVE)
        self.assertEqual(choices.to_data(), chosen(subgenre=PUNK).to_data())

    def test_a_kind_that_swings_can_be_played_straight(self):
        choices = chosen()
        choices.set_swing(arranger.NO_GROOVE)
        self.assertEqual((choices.get_swing(), groove_of(choices)), (arranger.NO_GROOVE, None))
        self.assertEqual(WizardChoices.from_data(choices.to_data()).get_swing(), arranger.NO_GROOVE)
        choices.set_swing(choices.swing_of_genre())
        self.assertEqual(choices.to_data(), chosen().to_data())

    def test_another_genre_takes_its_own_swing(self):
        choices = chosen(subgenre=PUNK)
        choices.set_swing(FactoryGroove.SWING_62)
        choices.set_genre(SOUL_FUNK)
        choices.set_subgenre(FUNK)
        self.assertEqual(choices.get_swing(), SWUNG_KINDS[(SOUL_FUNK, FUNK)])

    def test_a_kind_written_in_triplets_or_not_in_four_takes_no_swing(self):
        for genre, subgenre in ((BLUES, SHUFFLE), (ROCK, SIX_EIGHT)):
            choices = chosen(genre=genre, subgenre=subgenre)
            self.assertFalse(choices.has_swing())
            self.assertEqual(choices.get_swing(), arranger.NO_GROOVE)
            with self.assertRaisesRegex(ValueError, fixed_text(errors.ERR_WIZARD_SWING)):
                choices.set_swing(FactoryGroove.SWING_54)

    def test_what_is_no_swing_is_refused(self):
        choices = chosen()
        with self.assertRaisesRegex(ValueError, fixed_text(errors.ERR_WIZARD_SWING)):
            choices.set_swing(NOT_A_SWING)
        self.assertEqual(choices.swings(), list(wizard_limits.SWINGS))


if __name__ == '__main__':
    unittest.main()
