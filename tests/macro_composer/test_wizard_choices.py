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
from fractions import Fraction

from llamatron.composition.file_format import Section
from llamatron.composition.limits import MAX_TEMPO, MIN_TEMPO
from llamatron.macro_composer.wizard_choices import LEAST_BUSY, MOST_BUSY, USUAL_BUSY, QUARTERS_IN_WHOLE, SECONDS_IN_MINUTE, FIRST_SEED, LAST_SEED, MAJOR, MINOR, SCALE_TYPES, SUBGENRE, USUAL_ROOTS, WizardChoices, genre_names, genre_title
from llamatron.macro_composer.arranger import DRUMS, GENRE, PLAYERS, TYPE, WITHOUT, style_names
from llamatron.music.note import NoteName
from llamatron.playback.song_renderer import SongRenderer
from llamatron.support.version import VERSION

A_NAME = 'made'
NOT_A_CHOICE = 'polka of the spheres'
A_SEED = 11
ANOTHER_SEED = 12
NOT_A_NUMBER = 'fast'
# How near the length said must be to the length made.
A_SECOND = 1
# A genre whose songs have tunes sketched from the seed, so that another seed is heard.
A_GENRE_WITH_TUNES = 'rock'
# A player that genre always has.
A_BASS = 'bass'


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

    def test_a_forms_length_is_its_bars_at_the_tempo_and_the_meter(self):
        choices = chosen()
        bars = sum(choices.section_facts(name)[0] for name in choices.form_sections())
        seconds = choices.form_seconds()
        self.assertAlmostEqual(seconds, bars * float(Fraction(choices.meter())) * QUARTERS_IN_WHOLE * SECONDS_IN_MINUTE / choices.get_tempo())
        choices.set_tempo(choices.get_tempo() * 2)
        self.assertAlmostEqual(choices.form_seconds(), seconds / 2)

    def test_every_subgenre_has_a_meter_and_its_forms_from_the_shortest_to_the_longest(self):
        for place in range(len(genre_names())):
            for subgenre in range(len(chosen(genre=place).subgenres())):
                choices = chosen(genre=place, subgenre=subgenre)
                self.assertGreater(Fraction(choices.meter()), 0)
                lengths = [choices.form_seconds(form=form) for form in choices.forms_by_length()]
                self.assertEqual(lengths, sorted(lengths))
                self.assertEqual(sorted(choices.forms_by_length()), sorted(choices.forms()))

    def test_stepping_the_length_chooses_the_next_longer_or_shorter_form_and_stops_at_both_ends(self):
        choices = chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))
        forms = choices.forms_by_length()
        self.assertGreater(len(forms), 2)
        for _ in forms:
            choices.step_length(-1)
        self.assertEqual(choices.get_form(), forms[0])
        choices.step_length(1)
        self.assertEqual(choices.get_form(), forms[1])
        for _ in forms:
            choices.step_length(1)
        self.assertEqual(choices.get_form(), forms[-1])

    def test_the_length_said_is_the_length_of_the_song_made_for_every_form_of_every_subgenre(self):
        for place in range(len(genre_names())):
            for subgenre in range(len(chosen(genre=place).subgenres())):
                choices = chosen(genre=place, subgenre=subgenre)
                choices.set_seed(A_SEED)
                for form in choices.forms():
                    choices.set_form(form)
                    song = choices.made_setlist(name=A_NAME, version=VERSION).get_song(A_NAME)
                    made = sum(float(scene.seconds) for scene in SongRenderer(song).estimate())
                    self.assertAlmostEqual(choices.form_seconds(), made, delta=A_SECOND, msg=(choices.get_subgenre(), form))


class TestWizardBand(unittest.TestCase):
    """The band of the wizard's choices: who is in, how each plays and how busy each is."""

    def rock(self):
        choices = chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))
        choices.set_seed(A_SEED)
        return choices

    def tracks_of(self, choices):
        setlist = choices.made_setlist(name=A_NAME, version=VERSION)
        return setlist.get_song(A_NAME).get_track_names()

    def test_no_band_is_known_before_a_subgenre_is_chosen(self):
        choices = WizardChoices()
        self.assertEqual(choices.roles(), [])
        with self.assertRaises(ValueError):
            choices.set_role_in(role=NOT_A_CHOICE, on=True)

    def test_every_player_of_every_subgenre_can_be_put_in_or_left_out_played_each_way_and_made_busier(self):
        for place in range(len(genre_names())):
            for subgenre in range(len(chosen(genre=place).subgenres())):
                choices = chosen(genre=place, subgenre=subgenre)
                choices.set_seed(A_SEED)
                for role in choices.roles():
                    with self.subTest(subgenre=choices.get_subgenre(), role=role):
                        self.try_a_player(choices=choices, role=role)

    def try_a_player(self, *, choices, role):
        was_in = choices.role_is_in(role)
        try:
            choices.set_role_in(role=role, on=True)
        except ValueError:
            # No way of playing is written for the player in this subgenre.
            self.assertFalse(was_in)
            return
        for trait in choices.role_traits(role):
            usual = choices.get_way(trait)
            self.assertIn(usual, choices.ways(role=role, trait=trait))
            for way in choices.ways(role=role, trait=trait):
                choices.set_way(trait=trait, value=way)
                choices.made_setlist(name=A_NAME, version=VERSION)
            choices.set_way(trait=trait, value=usual)
        if choices.has_busy(role):
            for level in (LEAST_BUSY, MOST_BUSY, USUAL_BUSY):
                choices.set_busy(role=role, level=level)
                choices.made_setlist(name=A_NAME, version=VERSION)
        if len(choices.roles_in()) > 1:
            choices.set_role_in(role=role, on=False)
            self.assertFalse(choices.role_is_in(role))
            choices.made_setlist(name=A_NAME, version=VERSION)
        choices.set_role_in(role=role, on=was_in or len(choices.roles_in()) < 1)

    def test_a_player_left_out_has_no_track_and_the_drums_left_out_leave_no_drum_track(self):
        choices = self.rock()
        whole = self.tracks_of(choices)
        choices.set_role_in(role=A_BASS, on=False)
        self.assertEqual(self.tracks_of(choices), [track for track in whole if track != A_BASS])
        choices.set_role_in(role=A_BASS, on=True)
        self.assertEqual(self.tracks_of(choices), whole)
        choices.set_role_in(role=DRUMS, on=False)
        left = self.tracks_of(choices)
        self.assertEqual(left, [track for track in whole if track in choices.roles()])

    def test_the_last_player_cannot_be_left_out(self):
        choices = self.rock()
        last = choices.roles_in()[-1]
        for role in choices.roles_in()[:-1]:
            choices.set_role_in(role=role, on=False)
        with self.assertRaises(ValueError):
            choices.set_role_in(role=last, on=False)
        self.assertEqual(choices.roles_in(), [last])

    def test_a_player_who_usually_sits_out_comes_in_playing_a_way_that_sounds(self):
        rock = genre_names().index(A_GENRE_WITH_TUNES)
        every = [chosen(genre=rock, subgenre=place) for place in range(len(chosen(genre=rock).subgenres()))]
        choices = next(choices for choices in every if len(choices.roles_in()) < len(choices.roles()))
        choices.set_seed(A_SEED)
        out = [role for role in choices.roles() if not choices.role_is_in(role)]
        choices.set_role_in(role=out[0], on=True)
        self.assertTrue(choices.role_is_in(out[0]))
        self.assertIn(out[0], self.tracks_of(choices))

    def test_each_player_starts_a_little_busy_and_busier_players_change_the_song(self):
        choices = self.rock()
        self.assertEqual(choices.get_busy(DRUMS), USUAL_BUSY)
        usual = choices.made_setlist(name=A_NAME, version=VERSION).to_data()[Section.PATTERNS]
        choices.set_busy(role=DRUMS, level=MOST_BUSY)
        self.assertNotEqual(choices.made_setlist(name=A_NAME, version=VERSION).to_data()[Section.PATTERNS], usual)
        for level in (LEAST_BUSY - 1, MOST_BUSY + 1, NOT_A_NUMBER, True):
            with self.assertRaises(ValueError):
                choices.set_busy(role=DRUMS, level=level)
        self.assertEqual(choices.get_busy(DRUMS), MOST_BUSY)

    def test_a_way_of_playing_that_is_not_the_traits_is_refused(self):
        choices = self.rock()
        trait = choices.role_traits(A_BASS)[0]
        before = choices.to_data()
        with self.assertRaises(ValueError):
            choices.set_way(trait=trait, value=NOT_A_CHOICE)
        self.assertEqual(choices.to_data(), before)

    def test_the_band_is_kept_with_the_choices_and_another_subgenre_starts_a_band_afresh(self):
        choices = self.rock()
        trait = choices.role_traits(A_BASS)[0]
        choices.set_way(trait=trait, value=choices.ways(role=A_BASS, trait=trait)[-1])
        choices.set_busy(role=A_BASS, level=MOST_BUSY)
        choices.set_role_in(role=choices.roles_in()[0], on=False)
        data = choices.to_data()
        again = WizardChoices.from_data(data)
        self.assertEqual(again.to_data(), data)
        self.assertEqual(again.made_setlist(name=A_NAME, version=VERSION).to_data(), choices.made_setlist(name=A_NAME, version=VERSION).to_data())
        choices.set_subgenre(choices.subgenres()[-1])
        self.assertEqual(choices.get_busy(A_BASS), USUAL_BUSY)
        self.assertNotIn(WITHOUT, choices.to_data())

    def test_choices_kept_before_the_band_could_be_chosen_name_no_levels_and_make_the_same_song(self):
        choices = self.rock()
        old = {field: value for field, value in choices.to_data().items() if field != PLAYERS}
        again = WizardChoices.from_data(old)
        self.assertIsNone(again.get_busy(DRUMS))
        self.assertEqual(again.to_data(), old)
