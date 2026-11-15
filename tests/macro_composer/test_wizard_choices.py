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
"""The song wizard's choices: what a subgenre fills in, what each setter refuses, the choices kept and read back, and the song made."""

import random
import unittest

from llamatron.composition.file_format import Section
from llamatron.composition.limits import MAX_TEMPO, MIN_TEMPO
from llamatron.macro_composer.wizard_choices import FIRST_SEED, LAST_SEED, MAJOR, MINOR, SCALE_TYPES, SUBGENRE, USUAL_ROOTS, WizardChoices, genre_names, genre_title
from llamatron.macro_composer.arranger import GENRE, TYPE, style_names
from llamatron.music.note import NoteName
from llamatron.support.version import VERSION

A_NAME = 'made'
NOT_A_CHOICE = 'polka of the spheres'
A_SEED = 11
ANOTHER_SEED = 12
NOT_A_NUMBER = 'fast'
# A genre whose songs have tunes sketched from the seed, so that another seed is heard.
A_GENRE_WITH_TUNES = 'rock'


def chosen(*, genre=0, subgenre=0):
    choices = WizardChoices()
    choices.set_genre(genre_names()[genre])
    choices.set_subgenre(choices.subgenres()[subgenre])
    return choices


class TestWizardChoices(unittest.TestCase):

    def test_the_genres_are_every_style_template_in_the_order_of_their_titles(self):
        self.assertEqual(sorted(genre_names()), style_names())
        titles = [genre_title(genre) for genre in genre_names()]
        self.assertEqual(titles, sorted(titles))

    def test_nothing_is_chosen_at_first_and_no_song_can_be_made(self):
        choices = WizardChoices()
        self.assertIsNone(choices.get_genre())
        self.assertEqual(choices.subgenres(), [])
        self.assertEqual(choices.forms(), [])
        self.assertIsNone(choices.get_form())
        self.assertFalse(choices.is_ready())
        self.assertEqual(choices.to_data(), {})
        with self.assertRaises(ValueError):
            choices.made_setlist(name=A_NAME, version=VERSION)

    def test_a_genre_alone_is_not_enough_and_its_subgenres_are_sorted(self):
        choices = WizardChoices()
        choices.set_genre(genre_names()[0])
        self.assertFalse(choices.is_ready())
        self.assertTrue(choices.subgenres())
        self.assertEqual(choices.subgenres(), sorted(choices.subgenres()))

    def test_every_subgenre_of_every_genre_fills_in_the_rest_and_makes_a_song_that_keeps_the_choices(self):
        for place, genre in enumerate(genre_names()):
            for subgenre in range(len(chosen(genre=place).subgenres())):
                choices = chosen(genre=place, subgenre=subgenre)
                with self.subTest(genre=genre, subgenre=choices.get_subgenre()):
                    self.assertTrue(choices.is_ready())
                    self.assertIn(choices.get_scale_type(), SCALE_TYPES)
                    self.assertEqual(choices.get_root(), USUAL_ROOTS[choices.get_scale_type()])
                    self.assertEqual(choices.get_tempo(), choices.usual_tempo())
                    lowest, highest = choices.tempo_range()
                    self.assertLessEqual(lowest, highest)
                    self.assertEqual(choices.get_form(), choices.forms()[0])
                    self.assertTrue(choices.form_sections())
                    for section in choices.form_sections():
                        bars, _ = choices.section_facts(section)
                        self.assertGreater(bars, 0)
                    setlist = choices.made_setlist(name=A_NAME, version=VERSION)
                    self.assertEqual(setlist.get_song_names(), [A_NAME])
                    song = setlist.get_song(A_NAME)
                    self.assertTrue(song.get_scenes())
                    self.assertEqual(int(song.get_tempo()), choices.get_tempo())
                    self.assertEqual(song.get_wizard_choices(), choices.to_data())
                    self.assertIsNotNone(choices.get_seed())

    def test_another_genre_leaves_the_subgenre_to_be_chosen_again_and_the_same_genre_keeps_it(self):
        choices = chosen()
        subgenre = choices.get_subgenre()
        choices.set_genre(genre_names()[0])
        self.assertEqual(choices.get_subgenre(), subgenre)
        choices.set_genre(genre_names()[1])
        self.assertIsNone(choices.get_subgenre())
        self.assertFalse(choices.is_ready())

    def test_choosing_the_same_subgenre_again_keeps_what_was_changed(self):
        choices = chosen()
        choices.set_tempo(choices.get_tempo() + 1)
        tempo = choices.get_tempo()
        choices.set_subgenre(choices.get_subgenre())
        self.assertEqual(choices.get_tempo(), tempo)

    def test_each_setter_refuses_what_it_cannot_hold(self):
        choices = chosen()
        for setter, value in [
            (choices.set_genre, NOT_A_CHOICE), (choices.set_subgenre, NOT_A_CHOICE), (choices.set_root, NOT_A_CHOICE), (choices.set_scale_type, NOT_A_CHOICE),
            (choices.set_form, NOT_A_CHOICE), (choices.set_tempo, MIN_TEMPO - 1), (choices.set_tempo, MAX_TEMPO + 1), (choices.set_tempo, NOT_A_NUMBER), (choices.set_tempo, True),
            (choices.set_seed, NOT_A_NUMBER),
        ]:
            with self.subTest(setter=setter.__name__, value=value):
                before = choices.to_data()
                with self.assertRaises(ValueError):
                    setter(value)
                self.assertEqual(choices.to_data(), before)

    def test_any_tempo_the_tracker_plays_is_allowed_outside_the_usual_range_too(self):
        choices = chosen()
        _, highest = choices.tempo_range()
        choices.set_tempo(MAX_TEMPO)
        self.assertGreater(choices.get_tempo(), highest)

    def test_the_choices_are_kept_as_data_and_read_back_the_same(self):
        choices = chosen(genre=1, subgenre=1)
        choices.set_root(NoteName.F_SHARP)
        choices.set_scale_type(MINOR)
        choices.set_tempo(choices.get_tempo() + 3)
        choices.set_form(choices.forms()[-1])
        choices.set_seed(A_SEED)
        data = choices.to_data()
        self.assertEqual(WizardChoices.from_data(data).to_data(), data)

    def test_reading_leaves_out_what_no_longer_fits_and_keeps_the_rest(self):
        data = chosen().to_data()
        gone = WizardChoices.from_data({**data, SUBGENRE: NOT_A_CHOICE})
        self.assertEqual(gone.get_genre(), data[GENRE])
        self.assertIsNone(gone.get_subgenre())
        self.assertEqual(WizardChoices.from_data(None).to_data(), {})
        self.assertEqual(WizardChoices.from_data({GENRE: NOT_A_CHOICE}).to_data(), {})

    def test_the_same_choices_and_seed_make_the_same_song_and_another_seed_another(self):
        def data_of(seed):
            choices = chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))
            choices.set_seed(seed)
            return choices.made_setlist(name=A_NAME, version=VERSION).to_data()
        self.assertEqual(data_of(A_SEED), data_of(A_SEED))
        other = data_of(ANOTHER_SEED)
        self.assertNotEqual({**data_of(A_SEED), Section.SONGS: None}[Section.PATTERNS], other[Section.PATTERNS])

    def test_a_seed_is_drawn_once_when_none_is_given_and_kept(self):
        choices = chosen()
        choices.draw_seed(dice=random.Random(A_SEED))
        seed = choices.get_seed()
        self.assertTrue(FIRST_SEED <= seed <= LAST_SEED)
        choices.made_setlist(name=A_NAME, version=VERSION)
        self.assertEqual(choices.get_seed(), seed)

    def test_a_scale_type_changes_the_songs_scale(self):
        choices = chosen()
        for kind in (MAJOR, MINOR):
            choices.set_scale_type(kind)
            setlist = choices.made_setlist(name=A_NAME, version=VERSION)
            scale = setlist.get_named_scale(setlist.get_song(A_NAME).get_scale_name())
            self.assertEqual(scale.to_data()[TYPE], kind)
