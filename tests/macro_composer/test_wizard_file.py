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

"""A song file: the wizard's choices written down and made into a song, its written form, its plan and what it lays over the song."""

import os
import unittest

from llamatron.composition.file_format import Section
from llamatron.macro_composer import wizard_file
from llamatron.macro_composer.song_plan import BY_PLACE, ENERGY, PLAN_OF_SONG
from llamatron.macro_composer.wizard_choices import EXTRAS_KEPT, FORM, WizardChoices
from llamatron.strings.errors import ERR_SONG_FILE_FORM, ERR_SONG_FILE_FORM_ENTRY, ERR_SONG_FILE_NOT_A_MAPPING, ERR_SONG_FILE_NOT_READY, ERR_WIZARD_EXTRAS
from llamatron.support.version import VERSION

SONG_FILES = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'data', 'wizard_songs')
EVERYTHING = os.path.join(SONG_FILES, 'rock_everything.yml')
SONG_NAME = 'rock everything'
A_PATH = 'a_song.yml'
FILE_NAME = 'a_song'
GENRE = 'genre'
SUBGENRE = 'subgenre'
SEED = 'seed'
ROCK = 'rock'
ARENA = 'arena rock'
A_SEED = 5
OTHER_SEED = 6
VERSE = 'verse'
CHORUS = 'chorus'
ENDING = 'ending'
DRUM_SOLO = 'drum solo'
KIND = 'kind'
BARS = 'bars'
NO_SUCH = 'polka'
AN_ENERGY = 3
BASIC = {GENRE: ROCK, SUBGENRE: ARENA, SEED: A_SEED}
TEMPO = 'tempo'
A_TEMPO = 100


def choices(data, *, seed=None):
    return wizard_file.choices_of(data=data, path=A_PATH, seed=seed)


class TestSongFile(unittest.TestCase):

    def test_the_trial_song_is_made_with_every_scene_of_its_form(self):
        made = wizard_file.made_of_file(path=EVERYTHING, version=VERSION)
        song = made.get_item(section=Section.SONGS, name=SONG_NAME)
        names = [scene.get_name() for scene in song.get_scenes()]
        self.assertIn(DRUM_SOLO, names)
        self.assertEqual(len(names), len(set(names)))
        self.assertIn(PLAN_OF_SONG, song.get_wizard_choices()[EXTRAS_KEPT])

    def test_the_same_file_makes_the_same_song_and_a_seed_given_makes_another(self):
        one = wizard_file.made_of_file(path=EVERYTHING, version=VERSION).to_data()
        self.assertEqual(one, wizard_file.made_of_file(path=EVERYTHING, version=VERSION).to_data())
        self.assertNotEqual(one, wizard_file.made_of_file(path=EVERYTHING, version=VERSION, seed=OTHER_SEED).to_data())

    def test_a_song_is_named_by_the_file_where_it_gives_no_name(self):
        self.assertEqual(wizard_file.song_name(data=BASIC, path=A_PATH), FILE_NAME)
        self.assertEqual(wizard_file.song_name(data={**BASIC, wizard_file.NAME: SONG_NAME}, path=A_PATH), SONG_NAME)

    def test_a_song_is_planned_unless_the_file_says_otherwise(self):
        self.assertIn(PLAN_OF_SONG, choices(BASIC).get_song_extras())
        self.assertEqual(choices({**BASIC, PLAN_OF_SONG: False}).get_song_extras(), {})
        self.assertNotEqual(choices(BASIC).made_setlist(name=FILE_NAME, version=VERSION).to_data(), choices({**BASIC, PLAN_OF_SONG: False}).made_setlist(name=FILE_NAME, version=VERSION).to_data())

    def test_a_written_form_is_the_songs_own_and_what_a_place_is_given_goes_to_the_plan(self):
        form = [VERSE, {KIND: CHORUS, ENERGY: AN_ENERGY}, ENDING]
        made = choices({**BASIC, FORM: form})
        self.assertTrue(made.has_own_form())
        self.assertEqual([made.section_kind(place) for place in range(len(form))], [VERSE, CHORUS, ENDING])
        self.assertEqual(made.get_song_extras()[PLAN_OF_SONG][BY_PLACE], [{}, {ENERGY: AN_ENERGY}, {}])

    def test_what_the_file_lays_over_the_song_reaches_the_song(self):
        made = choices({**BASIC, EXTRAS_KEPT: {TEMPO: A_TEMPO}})
        self.assertEqual(made.song_picks(FILE_NAME)[TEMPO], A_TEMPO)
        kept = WizardChoices.from_data(made.to_data())
        self.assertEqual(kept.get_song_extras(), made.get_song_extras())

    def test_a_file_that_cannot_make_a_song_is_refused(self):
        refused = [(ERR_SONG_FILE_NOT_A_MAPPING.format(path=A_PATH), [VERSE]),
                   (ERR_SONG_FILE_NOT_READY.format(path=A_PATH), {GENRE: ROCK}),
                   (ERR_SONG_FILE_NOT_READY.format(path=A_PATH), {GENRE: NO_SUCH, SUBGENRE: ARENA}),
                   (ERR_SONG_FILE_FORM_ENTRY.format(path=A_PATH, place=2, value={BARS: 8}), {**BASIC, FORM: [VERSE, {BARS: 8}]}),
                   (ERR_SONG_FILE_FORM.format(path=A_PATH), {**BASIC, FORM: [VERSE, NO_SUCH]})]
        for message, data in refused:
            with self.subTest(message=message):
                with self.assertRaises(ValueError) as raised:
                    choices(data)
                self.assertEqual(str(raised.exception), message)

    def test_the_picks_laid_over_must_be_a_mapping(self):
        with self.assertRaises(ValueError) as raised:
            WizardChoices().set_song_extras([VERSE])
        self.assertEqual(str(raised.exception), ERR_WIZARD_EXTRAS.format(value=[VERSE]))
