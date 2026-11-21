# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of a song's genre, subgenre and variant: the lists agreeing with the style templates, what a song keeps, what a
file's text is read as, and what a set calls a mashup."""

import unittest

from llamatron.composition import genres
from llamatron.composition.file_format import Section, SongSetting
from llamatron.composition.genres import sensible_style, style_name, subgenres_of, variants_of
from llamatron.macro_composer import arranger
from llamatron.macro_composer.arranger import variants_of as variants_of_template
from llamatron.macro_composer.wizard_choices import genre_names, style_of, WizardChoices
from llamatron.support import version
from tests.support.rendering import as_setlist, setlist_from_data, song_from_data
from tests.support.song_testing import lead_data

A_NOTE = [1, 0.25]
ROCK = 'Rock'
HARD_ROCK = 'hard rock'
HEAVY = 'heavy'
FOLK = 'Folk'
BLUES = 'Blues'
A_SHUFFLE = 'shuffle'
NOT_A_GENRE = 'Skronk'
OLD_ROCK_MASHUP = 'Rock Mashup'
SHOUTED_ROCK = 'ROCK'
SONG_NAME = 'a_song'
A_SEED = 5
WIZARD_ROCK = 'rock'


def set_data(**settings):
    """The data of a set of one song, with the song's settings as given."""
    data = as_setlist(lead_data(A_NOTE))
    next(iter(data[Section.SONGS].values())).update(settings)
    return data


def a_song(**settings):
    return song_from_data(set_data(**settings))


def style_kept(song):
    return song.get_genre(), song.get_subgenre(), song.get_variant()


class TestGenreLists(unittest.TestCase):

    def test_every_genre_and_subgenre_of_the_song_wizard_is_one_a_song_can_say(self):
        for genre in genre_names():
            style = style_of(genre)
            with self.subTest(genre=genre):
                self.assertIn(style[arranger.GENRE], genres.GENRES)
                self.assertEqual(sorted(subgenres_of(style[arranger.GENRE])), sorted(style[arranger.TEMPLATES]))
                for subgenre in style[arranger.TEMPLATES]:
                    names = [variant[arranger.NAME] for variant in variants_of_template(style=style, template=subgenre)]
                    self.assertEqual(variants_of(genre=style[arranger.GENRE], subgenre=subgenre), names)

    def test_every_list_is_of_a_genre_there_is_and_the_genres_are_in_order(self):
        self.assertEqual(genres.GENRES, sorted(genres.GENRES, key=str.lower))
        self.assertLessEqual(set(genres.SUBGENRES), set(genres.GENRES))
        for genre, subgenres in genres.VARIANTS.items():
            self.assertLessEqual(set(subgenres), set(subgenres_of(genre)))

    def test_a_genre_with_no_subgenres_has_none_and_no_genre_has_none(self):
        self.assertEqual(subgenres_of(FOLK), [])
        self.assertEqual(subgenres_of(None), [])
        self.assertEqual(variants_of(genre=BLUES, subgenre=A_SHUFFLE), [])


class TestSensibleStyle(unittest.TestCase):

    def test_what_is_known_is_kept_as_the_program_writes_it_whatever_its_capitals(self):
        self.assertEqual(sensible_style(genre=SHOUTED_ROCK, subgenre=HARD_ROCK.upper(), variant=HEAVY.title()), (ROCK, HARD_ROCK, HEAVY))

    def test_what_is_not_known_is_nothing_and_takes_what_is_under_it_along(self):
        self.assertEqual(sensible_style(genre=NOT_A_GENRE, subgenre=HARD_ROCK, variant=HEAVY), (None, None, None))
        self.assertEqual(sensible_style(genre=ROCK, subgenre=A_SHUFFLE, variant=HEAVY), (ROCK, None, None))
        self.assertEqual(sensible_style(genre=ROCK, subgenre=HARD_ROCK, variant=A_SHUFFLE), (ROCK, HARD_ROCK, None))
        self.assertEqual(sensible_style(genre=A_SEED, subgenre=[HARD_ROCK], variant=None), (None, None, None))

    def test_a_mashup_written_the_older_way_is_the_mashup_of_its_genre(self):
        self.assertEqual(sensible_style(genre=OLD_ROCK_MASHUP, subgenre=None, variant=None), (genres.MASHUP, ROCK, None))
        self.assertEqual(sensible_style(genre=genres.MASHUP_NAMED.format(subgenre=NOT_A_GENRE), subgenre=None, variant=None), (genres.MASHUP, None, None))

    def test_a_mashup_is_named_with_its_subgenre_and_any_other_genre_by_itself(self):
        self.assertEqual(style_name(genre=genres.MASHUP, subgenre=ROCK), OLD_ROCK_MASHUP)
        self.assertEqual(style_name(genre=genres.MASHUP, subgenre=None), genres.MASHUP)
        self.assertEqual(style_name(genre=ROCK, subgenre=HARD_ROCK), ROCK)
        self.assertIsNone(style_name(genre=None, subgenre=None))


class TestSongStyle(unittest.TestCase):

    def test_a_song_says_none_until_told_and_writes_none(self):
        song = a_song()
        self.assertEqual(style_kept(song), (None, None, None))
        for setting in (SongSetting.GENRE, SongSetting.SUBGENRE, SongSetting.VARIANT):
            self.assertNotIn(setting, song.to_data())

    def test_a_song_keeps_a_genre_then_its_subgenre_then_its_variant_and_writes_them(self):
        song = a_song()
        song.set_genre(ROCK)
        song.set_subgenre(HARD_ROCK)
        song.set_variant(HEAVY)
        self.assertEqual(style_kept(song), (ROCK, HARD_ROCK, HEAVY))
        written = song.to_data()
        self.assertEqual((written[SongSetting.GENRE], written[SongSetting.SUBGENRE], written[SongSetting.VARIANT]), (ROCK, HARD_ROCK, HEAVY))

    def test_a_subgenre_or_a_variant_with_nothing_over_it_is_not_kept(self):
        song = a_song()
        song.set_subgenre(HARD_ROCK)
        song.set_variant(HEAVY)
        self.assertEqual(style_kept(song), (None, None, None))

    def test_another_genre_takes_the_subgenre_and_the_variant_away_and_another_subgenre_the_variant(self):
        song = a_song()
        song.set_genre(ROCK)
        song.set_subgenre(HARD_ROCK)
        song.set_variant(HEAVY)
        song.set_subgenre(subgenres_of(ROCK)[0])
        self.assertEqual(style_kept(song), (ROCK, subgenres_of(ROCK)[0], None))
        song.set_genre(BLUES)
        self.assertEqual(style_kept(song), (BLUES, None, None))
        song.set_genre(None)
        self.assertEqual(style_kept(song), (None, None, None))

    def test_a_genre_the_program_does_not_know_is_none_whether_set_or_read_and_the_set_still_opens(self):
        song = a_song()
        song.set_genre(ROCK)
        song.set_genre(NOT_A_GENRE)
        self.assertIsNone(song.get_genre())
        self.assertEqual(style_kept(a_song(genre=NOT_A_GENRE, subgenre=HARD_ROCK)), (None, None, None))

    def test_a_file_written_the_older_way_reads_as_a_mashup_and_the_set_names_it_as_before(self):
        setlist = setlist_from_data(set_data(genre=OLD_ROCK_MASHUP))
        song = setlist.get_song(setlist.get_song_names()[0])
        self.assertEqual(style_kept(song), (genres.MASHUP, ROCK, None))
        self.assertEqual(song.get_style_name(), OLD_ROCK_MASHUP)
        self.assertEqual(setlist.get_genres(), [OLD_ROCK_MASHUP])
        written = setlist.to_data()[Section.SONGS][setlist.get_song_names()[0]]
        self.assertEqual((written[SongSetting.GENRE], written[SongSetting.SUBGENRE]), (genres.MASHUP, ROCK))

    def test_a_song_of_the_song_wizard_says_its_genre_subgenre_and_variant(self):
        choices = WizardChoices()
        choices.set_genre(WIZARD_ROCK)
        choices.set_subgenre(HARD_ROCK)
        choices.set_variant(HEAVY)
        choices.set_seed(A_SEED)
        song = choices.made_setlist(name=SONG_NAME, version=version.VERSION).get_song(SONG_NAME)
        self.assertEqual(style_kept(song), (ROCK, HARD_ROCK, HEAVY))


if __name__ == '__main__':
    unittest.main()
