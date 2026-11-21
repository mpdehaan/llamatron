# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A song file: the wizard's choices written down and made into a song, its written form, its plan and what it lays over the song."""

import os
import unittest

from llamatron.model.file import version
from llamatron.model.schema.file_format import Section
from llamatron.song_wizard import arranger, song_plan, wizard_file, wizard_limits
from llamatron.song_wizard.wizard_choices import WizardChoices
from llamatron.user_strings import errors

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
        made = wizard_file.made_of_file(path=EVERYTHING, version=version.VERSION)
        song = made.get_item(section=Section.SONGS, name=SONG_NAME)
        names = [scene.get_name() for scene in song.get_scenes()]
        self.assertIn(DRUM_SOLO, names)
        self.assertEqual(len(names), len(set(names)))
        self.assertIn(song_plan.PLAN_OF_SONG, song.get_wizard_choices()[wizard_limits.EXTRAS_KEPT])

    def test_the_same_file_makes_the_same_song_and_a_seed_given_makes_another(self):
        one = wizard_file.made_of_file(path=EVERYTHING, version=version.VERSION).to_data()
        self.assertEqual(one, wizard_file.made_of_file(path=EVERYTHING, version=version.VERSION).to_data())
        self.assertNotEqual(one, wizard_file.made_of_file(path=EVERYTHING, version=version.VERSION, seed=OTHER_SEED).to_data())

    def test_a_song_is_named_by_the_file_where_it_gives_no_name(self):
        self.assertEqual(wizard_file.song_name(data=BASIC, path=A_PATH), FILE_NAME)
        self.assertEqual(wizard_file.song_name(data={**BASIC, wizard_file.NAME: SONG_NAME}, path=A_PATH), SONG_NAME)

    def test_a_song_is_planned_unless_the_file_says_otherwise(self):
        self.assertIn(song_plan.PLAN_OF_SONG, choices(BASIC).get_song_extras())
        self.assertEqual(choices({**BASIC, song_plan.PLAN_OF_SONG: False}).get_song_extras(), {})
        self.assertNotEqual(choices(BASIC).made_setlist(name=FILE_NAME, version=version.VERSION).to_data(), choices({**BASIC, song_plan.PLAN_OF_SONG: False}).made_setlist(name=FILE_NAME, version=version.VERSION).to_data())

    def test_a_written_form_is_the_songs_own_and_what_a_place_is_given_goes_to_the_plan(self):
        form = [VERSE, {KIND: CHORUS, song_plan.ENERGY: AN_ENERGY}, ENDING]
        made = choices({**BASIC, arranger.FORM: form})
        self.assertTrue(made.get_song_form().has_own_form())
        self.assertEqual([made.section(place).kind() for place in range(len(form))], [VERSE, CHORUS, ENDING])
        self.assertEqual(made.get_song_extras()[song_plan.PLAN_OF_SONG][song_plan.BY_PLACE], [{}, {song_plan.ENERGY: AN_ENERGY}, {}])

    def test_what_the_file_lays_over_the_song_reaches_the_song(self):
        made = choices({**BASIC, wizard_limits.EXTRAS_KEPT: {TEMPO: A_TEMPO}})
        self.assertEqual(made.song_picks(FILE_NAME)[TEMPO], A_TEMPO)
        kept = WizardChoices.from_data(made.to_data())
        self.assertEqual(kept.get_song_extras(), made.get_song_extras())

    def test_a_file_that_cannot_make_a_song_is_refused(self):
        refused = [(errors.ERR_SONG_FILE_NOT_A_MAPPING.format(path=A_PATH), [VERSE]),
                   (errors.ERR_SONG_FILE_NOT_READY.format(path=A_PATH), {GENRE: ROCK}),
                   (errors.ERR_SONG_FILE_NOT_READY.format(path=A_PATH), {GENRE: NO_SUCH, SUBGENRE: ARENA}),
                   (errors.ERR_SONG_FILE_FORM_ENTRY.format(path=A_PATH, place=2, value={BARS: 8}), {**BASIC, arranger.FORM: [VERSE, {BARS: 8}]}),
                   (errors.ERR_SONG_FILE_FORM.format(path=A_PATH), {**BASIC, arranger.FORM: [VERSE, NO_SUCH]})]
        for message, data in refused:
            with self.subTest(message=message):
                with self.assertRaises(ValueError) as raised:
                    choices(data)
                self.assertEqual(str(raised.exception), message)

    def test_the_picks_laid_over_must_be_a_mapping(self):
        with self.assertRaises(ValueError) as raised:
            WizardChoices().set_song_extras([VERSE])
        self.assertEqual(str(raised.exception), errors.ERR_WIZARD_EXTRAS.format(value=[VERSE]))
