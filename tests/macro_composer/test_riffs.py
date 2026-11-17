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

"""Tests of a riff, a song's second hook: its notes as drawn, and the riff in the song wizard's choices, who plays it, where, its notes by hand and another take."""

import unittest

from llamatron.composition.file_format import Section
from llamatron.macro_composer import line_edits
from llamatron.macro_composer.notation import DEGREE, OCTAVE, REST
from llamatron.macro_composer.riffs import FIRST_TAKE, HOME, RIFF_BARS, riff_line
from llamatron.macro_composer.wizard_choices import RIFF_EVERYWHERE, RIFF_INTRO_AND_VERSES, RIFF_UNDER_CHORUSES, WizardChoices
from llamatron.strings.macro_composer import MSG_PART_OF_SECTION
from llamatron.support.version import VERSION

A_NAME = 'made'
A_SEED = 11
ANOTHER_SEED = 12
EIGHTHS = 8
A_GENRE = 'rock'
A_SUBGENRE = 'hard rock'
A_GENRE_OF_NO_FIGURES = 'experimental'
THE_GUITAR = 'guitar'
THE_BASS = 'bass'
THE_SINGER = 'lead'
THE_RIFF = 'riff'
NOT_A_WAY = 'sideways'
MANY_SEEDS = 40


def chosen(*, genre=A_GENRE, subgenre=A_SUBGENRE):
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre if genre == A_GENRE else choices.subgenres()[0])
    choices.set_seed(A_SEED)
    return choices


def made(choices):
    return choices.made_setlist(name=A_NAME, version=VERSION)


def patterns(choices):
    return made(choices).to_data()[Section.PATTERNS]


class TestRiffLine(unittest.TestCase):
    """A riff's notes as drawn."""

    __slots__ = ()

    def test_a_riff_is_two_bars_that_start_on_the_root_the_second_answering_the_first(self):
        for seed in range(MANY_SEEDS):
            line = riff_line(seed=seed, take=FIRST_TAKE, eighths=EIGHTHS)
            self.assertEqual(line_edits.steps_of(line), RIFF_BARS * EIGHTHS)
            self.assertEqual((line[0][DEGREE], line[0].get(OCTAVE, 0)), HOME)
            first, second = self.bars(line)
            self.assertEqual([line_edits.length_of(note) for note in first], [line_edits.length_of(note) for note in second])
            self.assertEqual([REST in note for note in first], [REST in note for note in second])
            self.assertEqual(first[0], second[0])

    def bars(self, line):
        half = len(line) // RIFF_BARS
        return line[:half], line[half:]

    def test_a_seed_and_a_take_make_one_riff_and_another_take_another(self):
        self.assertEqual(riff_line(seed=A_SEED, take=FIRST_TAKE, eighths=EIGHTHS), riff_line(seed=A_SEED, take=FIRST_TAKE, eighths=EIGHTHS))
        self.assertNotEqual(riff_line(seed=A_SEED, take=FIRST_TAKE, eighths=EIGHTHS), riff_line(seed=A_SEED, take=FIRST_TAKE + 1, eighths=EIGHTHS))
        self.assertNotEqual(riff_line(seed=A_SEED, take=FIRST_TAKE, eighths=EIGHTHS), riff_line(seed=ANOTHER_SEED, take=FIRST_TAKE, eighths=EIGHTHS))


class TestWizardRiff(unittest.TestCase):
    """The riff in the wizard's choices."""

    __slots__ = ()

    def test_a_song_has_no_riff_until_a_player_of_a_figure_is_given_one(self):
        choices = chosen()
        self.assertFalse(choices.has_riff())
        self.assertIsNone(choices.riff_line())
        self.assertIsNone(choices.riff_notes())
        offered = choices.riff_players_offered()
        self.assertIn([THE_GUITAR], offered)
        self.assertIn([THE_GUITAR, THE_BASS], offered)
        self.assertNotIn([THE_SINGER], offered)
        self.assertEqual(chosen(genre=A_GENRE_OF_NO_FIGURES).riff_players_offered(), [])
        self.assertEqual(WizardChoices().riff_players_offered(), [])

    def test_the_riff_takes_the_place_of_its_players_figures_in_the_sections_it_is_played_in(self):
        choices = chosen()
        usual = patterns(choices)
        choices.set_riff(players=[THE_GUITAR, THE_BASS])
        self.assertEqual(choices.get_riff_players(), [THE_GUITAR, THE_BASS])
        self.assertEqual(choices.get_riff_said(), RIFF_INTRO_AND_VERSES)
        with_riff = patterns(choices)
        self.assertNotEqual(with_riff, usual)
        for role in (THE_GUITAR, THE_BASS):
            self.assertIn(MSG_PART_OF_SECTION.format(role, THE_RIFF), with_riff)
        song = made(choices).get_song(A_NAME)
        riff_scenes = [scene.get_name() for scene in song.get_scenes() if MSG_PART_OF_SECTION.format(THE_GUITAR, THE_RIFF) in str(scene.to_data())]
        self.assertTrue(riff_scenes)
        self.assertTrue(all(name.startswith(('intro', 'verse')) for name in riff_scenes))
        choices.set_riff(players=[THE_GUITAR, THE_BASS], said=RIFF_UNDER_CHORUSES)
        self.assertEqual(choices.get_riff_said(), RIFF_UNDER_CHORUSES)
        self.assertNotEqual(patterns(choices), with_riff)
        choices.set_riff(players=[])
        self.assertFalse(choices.has_riff())
        self.assertEqual(patterns(choices), usual)

    def test_another_take_is_another_riff_and_notes_by_hand_are_the_riff(self):
        choices = chosen()
        choices.set_riff(players=[THE_BASS], said=RIFF_EVERYWHERE)
        first = choices.riff_line()
        choices.new_riff()
        second = choices.riff_line()
        self.assertNotEqual(first, second)
        written = line_edits.moved(line=second, step=0, by=2)
        choices.set_riff_line(written)
        self.assertTrue(choices.riff_is_own())
        self.assertEqual(line_edits.place_of(choices.riff_line()[0]), line_edits.place_of(second[0]) + 2)
        steps, in_bar, notes = choices.riff_notes()
        self.assertEqual((steps, in_bar), (RIFF_BARS * EIGHTHS, EIGHTHS))
        self.assertEqual(len(notes), len([note for note in written if REST not in note]))
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.riff_line(), choices.riff_line())
        self.assertEqual(patterns(again), patterns(choices))
        choices.set_riff_line(None)
        self.assertEqual(choices.riff_line(), second)

    def test_what_is_no_riff_is_refused_and_a_change_of_genre_leaves_the_riff_behind(self):
        choices = chosen()
        for refused in (dict(players=[THE_SINGER]), dict(players=[THE_BASS], said=NOT_A_WAY)):
            with self.assertRaises(ValueError):
                choices.set_riff(**refused)
        for without in (choices.new_riff, lambda: choices.set_riff_line([])):
            with self.assertRaises(ValueError):
                without()
        choices.set_riff(players=[THE_BASS])
        with self.assertRaises(ValueError):
            choices.set_riff_line(choices.riff_line()[:1])
        choices.set_genre(A_GENRE_OF_NO_FIGURES)
        choices.set_subgenre(choices.subgenres()[0])
        self.assertFalse(choices.has_riff())

    def test_every_genre_s_riff_makes_a_song_wherever_it_is_played(self):
        for genre in ('rock', 'sixties_pop', 'soul_funk', 'blues', 'electronic'):
            choices = chosen(genre=genre)
            for players in (choices.riff_players_offered()[0], choices.riff_players_offered()[-1]):
                for said in choices.riff_said_offered():
                    with self.subTest(genre=genre, players=players, said=said):
                        choices.set_riff(players=players, said=said)
                        made(choices)
