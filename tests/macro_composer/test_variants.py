# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of the kinds of song a subgenre holds: each kind drawn whole, kept with the song and refused when unknown."""

import unittest

from llamatron.macro_composer import arranger
from llamatron.macro_composer.arranger import style_in, style_named, style_names
from llamatron.macro_composer.wizard_choices import WizardChoices
from llamatron.model.file import version
from llamatron.user_strings import errors
from tests.support.ui_testing import fixed_text

SONG_NAME = 'a_song'
A_SEED = 11
ROCK = 'rock'
HARD_ROCK = 'hard rock'
# A subgenre that is one kind of song.
PUNK = 'punk'
NOT_A_VARIANT = 'polka'
ALL_SHARES = 100


def chosen(*, subgenre=HARD_ROCK, variant=None):
    choices = WizardChoices()
    choices.set_genre(ROCK)
    choices.set_subgenre(subgenre)
    choices.take_variant(variant)
    choices.set_seed(A_SEED)
    return choices


def made(choices):
    return choices.made_setlist(name=SONG_NAME, version=version.VERSION).to_data()


class TestVariants(unittest.TestCase):

    def test_a_subgenre_starts_on_its_commonest_kind_and_says_what_the_kind_is(self):
        choices = chosen()
        kinds = style_named(ROCK)[arranger.VARIANTS][HARD_ROCK]
        commonest = max(kinds, key=lambda kind: kind[arranger.SHARE])
        self.assertEqual(choices.variants()[0], commonest[arranger.NAME])
        self.assertEqual(choices.get_variant(), commonest[arranger.NAME])
        self.assertEqual(choices.variant_says(), commonest[arranger.VARIANT_SAYS])
        self.assertEqual(sorted(choices.variants()), sorted(kind[arranger.NAME] for kind in kinds))

    def test_a_subgenre_of_one_kind_has_no_variants(self):
        choices = chosen(subgenre=PUNK)
        self.assertEqual(choices.variants(), [])
        self.assertIsNone(choices.get_variant())
        self.assertIsNone(choices.variant_says())
        self.assertNotIn(arranger.VARIANT, choices.to_data())

    def test_every_kind_makes_a_song_unlike_every_other_kind_s(self):
        songs = [made(chosen(variant=variant)) for variant in chosen().variants()]
        for place, song in enumerate(songs):
            for other in songs[place + 1:]:
                self.assertNotEqual(song, other)

    def test_a_kind_takes_its_own_tempo_and_riff(self):
        tempos = set()
        riffs = set()
        for variant in chosen().variants():
            choices = chosen(variant=variant)
            tempos.add(choices.get_tempo())
            riffs.add(bool(choices.get_riffs().riff_names()))
        self.assertGreater(len(tempos), 1)
        self.assertEqual(riffs, {True, False})

    def test_choosing_a_kind_leaves_behind_what_was_chosen_for_another(self):
        choices = chosen()
        first, other = choices.variants()[:2]
        choices.set_tempo(choices.get_tempo() + 1)
        choices.set_variant(other)
        self.assertEqual(choices.get_tempo(), chosen(variant=other).get_tempo())
        # Choosing the kind already chosen changes nothing.
        choices.set_tempo(choices.get_tempo() + 1)
        tempo = choices.get_tempo()
        choices.set_variant(other)
        self.assertEqual(choices.get_tempo(), tempo)
        self.assertNotEqual(first, other)

    def test_a_kind_is_kept_with_the_song_and_read_back(self):
        last = chosen().variants()[-1]
        choices = chosen(variant=last)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.get_variant(), last)
        self.assertEqual(made(again), made(choices))

    def test_a_kind_the_subgenre_has_not_is_refused_and_a_kept_one_is_left_out(self):
        choices = chosen()
        with self.assertRaises(ValueError) as refused:
            choices.set_variant(NOT_A_VARIANT)
        self.assertIn(fixed_text(errors.ERR_WIZARD_NO_SUCH_VARIANT), str(refused.exception))
        again = WizardChoices.from_data({**choices.to_data(), arranger.VARIANT: NOT_A_VARIANT})
        self.assertEqual(again.get_variant(), choices.get_variant())

    def test_the_shares_of_a_subgenre_s_kinds_add_to_all(self):
        for name in style_names():
            for subgenre, kinds in style_named(name).get(arranger.VARIANTS, {}).items():
                self.assertEqual(sum(kind[arranger.SHARE] for kind in kinds), ALL_SHARES, (name, subgenre))
                self.assertIn(subgenre, style_named(name)[arranger.TEMPLATES])

    def test_a_kind_s_words_are_laid_over_the_subgenre_s_and_a_kind_unknown_changes_nothing(self):
        style = style_named(ROCK)
        usual = style_in(style=style, template=HARD_ROCK)
        self.assertIs(style_in(style=style, template=HARD_ROCK, variant=NOT_A_VARIANT), usual)
        for kind in style[arranger.VARIANTS][HARD_ROCK]:
            laid = style_in(style=style, template=HARD_ROCK, variant=kind[arranger.NAME])
            for field, value in kind[arranger.STYLE].items():
                if not isinstance(value, dict):
                    self.assertEqual(laid[field], value)
