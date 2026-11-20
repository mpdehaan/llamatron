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
"""A set taking in another set's songs with all they use, which the song wizard does with the set it made, and a song keeping the wizard's choices."""

import os
import pathlib
import tempfile
import unittest

from llamatron.composition import setlist as setlist_values
from llamatron.composition.file_format import Section
from llamatron.composition.setlist import Setlist
from llamatron.macro_composer.wizard_choices import genre_names, WizardChoices
from llamatron.strings import names
from llamatron.support import version
from tests.support.rendering import render_song

# Names the tests give songs, a seed for each, and a file's name.
FIRST = 'first'
SECOND = 'second'
A_SEED = 7
ANOTHER_SEED = 8
A_FILE = 'taken.yml'
# What a song is given to keep, and a change made to the data handed over.
KEY = 'key'
ROOT = 'root'
SOME_CHOICES = {'genre': 'rock', KEY: {ROOT: 'E'}}
A_ROOT = 'A'
SECOND_COPY = '{}-2'
EXAMPLES = pathlib.Path(__file__).resolve().parent.parent.parent / 'examples'
SET_FILES = '*.yml'


def made(*, name, genre=0, subgenre=0, seed=A_SEED):
    """Return a set of one song the wizard's choices make, by the places of a genre and one of its subgenres."""
    choices = WizardChoices()
    choices.set_genre(genre_names()[genre])
    choices.set_subgenre(choices.subgenres()[subgenre])
    choices.set_seed(seed)
    return choices.made_setlist(name=name, version=version.VERSION)


def a_new_set():
    setlist = Setlist.new()
    setlist.fill_in_defaults()
    return setlist


class TestTakingIn(unittest.TestCase):

    def test_a_song_is_taken_in_with_everything_it_uses_and_plays_as_it_did(self):
        other = made(name=FIRST)
        alone = render_song(other.get_song(FIRST), seed=A_SEED)
        setlist = a_new_set()
        before = setlist.to_data()
        self.assertEqual(setlist.take_in(made(name=FIRST)), [FIRST])
        self.assertEqual(setlist.get_song_names(), [names.MSG_DEFAULT_SONG_NAME, FIRST])
        for section in setlist_values.SECTIONS_TAKEN_IN:
            for name, item in (before.get(section) or {}).items():
                self.assertEqual(setlist.get_item(section=section, name=name).to_data(), item)
        together = render_song(setlist.get_song(FIRST), seed=A_SEED)
        self.assertEqual([column.get_name() for column in together.get_columns()], [column.get_name() for column in alone.get_columns()])
        self.assertEqual(len(together.get_rows()), len(alone.get_rows()))

    def test_a_made_set_holds_only_what_its_song_uses(self):
        for place in range(len(genre_names())):
            other = made(name=FIRST, genre=place)
            before = other.to_data()
            other.remove_unused()
            self.assertEqual(other.to_data(), before)

    def test_a_song_whose_name_is_in_use_gets_a_name_of_its_own(self):
        setlist = a_new_set()
        setlist.take_in(made(name=FIRST))
        self.assertEqual(setlist.take_in(made(name=FIRST, seed=ANOTHER_SEED)), [SECOND_COPY.format(FIRST)])

    def test_what_is_the_same_in_both_is_shared_and_what_differs_is_renamed_and_still_named_by_the_song(self):
        setlist = a_new_set()
        setlist.take_in(made(name=FIRST))
        first = setlist.get_item(section=Section.SONGS, name=FIRST).to_data()
        patterns = setlist.get_pattern_names()
        instruments = setlist.get_instrument_names()
        setlist.take_in(made(name=SECOND, seed=ANOTHER_SEED))
        # The same band's instruments are the same things, so none is added twice, while the tunes differ and are added under names of their own.
        self.assertEqual(setlist.get_instrument_names(), instruments)
        self.assertGreater(len(setlist.get_pattern_names()), len(patterns))
        self.assertEqual(setlist.get_pattern_names()[:len(patterns)], patterns)
        self.assertEqual(setlist.get_item(section=Section.SONGS, name=FIRST).to_data(), first)
        second = setlist.get_song(SECOND)
        for scene in second.get_scenes():
            for track in second.get_track_names():
                slot = scene.get_clip_slot(track)
                if slot is not None:
                    self.assertTrue(setlist.has_pattern(slot.get_pattern_name()))

    def test_songs_of_different_genres_live_together_and_the_set_saves_and_loads(self):
        setlist = a_new_set()
        for place, genre in enumerate(genre_names()):
            setlist.take_in(made(name=FIRST, genre=place))
        self.assertEqual(len(setlist.get_song_names()), len(genre_names()) + 1)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, A_FILE)
            setlist.write_file(path)
            again = Setlist.read_file(path)
        # A set that is read fills in what its file left out, as the tracker does on opening one.
        again.fill_in_defaults()
        self.assertEqual(again.to_data(), setlist.to_data())
        for name in again.get_song_names():
            render_song(again.get_song(name), seed=A_SEED)


class TestReplacingASong(unittest.TestCase):
    """A song replaced entirely, in its place, as the song wizard replaces one."""

    def a_set_of_two(self):
        setlist = a_new_set()
        setlist.take_in(made(name=FIRST))
        setlist.take_in(made(name=SECOND, genre=1))
        return setlist

    def unused_patterns(self, setlist):
        return [name for name in setlist.get_pattern_names() if not setlist.clip_slots_naming(section=Section.PATTERNS, name=name)]

    def test_the_new_song_takes_the_name_and_the_place_and_what_only_the_old_song_used_goes(self):
        setlist = a_new_set()
        setlist.take_in(made(name=FIRST))
        setlist.take_in(made(name=SECOND, seed=ANOTHER_SEED))
        unused = self.unused_patterns(setlist)
        patterns = len(setlist.get_pattern_names())
        second = setlist.get_item(section=Section.SONGS, name=SECOND).to_data()
        setlist.replace_song(name=FIRST, other=made(name=A_FILE, genre=1))
        self.assertEqual(setlist.get_song_names(), [names.MSG_DEFAULT_SONG_NAME, FIRST, SECOND])
        self.assertEqual(setlist.get_item(section=Section.SONGS, name=SECOND).to_data(), second)
        # Nothing the old song alone used is left: every pattern unused now was unused before.
        self.assertEqual(self.unused_patterns(setlist), unused)
        self.assertNotEqual(len(setlist.get_pattern_names()), patterns)
        render_song(setlist.get_song(FIRST), seed=A_SEED)
        render_song(setlist.get_song(SECOND), seed=A_SEED)

    def test_replacing_a_song_with_the_same_song_changes_nothing(self):
        setlist = self.a_set_of_two()
        before = setlist.to_data()
        setlist.replace_song(name=FIRST, other=made(name=FIRST))
        self.assertEqual(setlist.to_data(), before)

    def test_what_nothing_used_before_is_left_alone(self):
        setlist = self.a_set_of_two()
        unused = self.unused_patterns(setlist)
        setlist.replace_song(name=SECOND, other=made(name=SECOND, seed=ANOTHER_SEED))
        for name in unused:
            self.assertTrue(setlist.has_pattern(name))


class TestUntouchedSongs(unittest.TestCase):
    """Whether a song is as it started, which the song wizard fills in place."""

    def test_a_new_sets_song_is_untouched_until_the_song_or_its_starter_pattern_changes(self):
        setlist = a_new_set()
        self.assertTrue(setlist.song_is_untouched(names.MSG_DEFAULT_SONG_NAME))
        song = setlist.get_song(names.MSG_DEFAULT_SONG_NAME)
        song.set_tempo(song.get_tempo() + 1)
        self.assertFalse(setlist.song_is_untouched(names.MSG_DEFAULT_SONG_NAME))
        other = a_new_set()
        other.remove_item(section=Section.PATTERNS, name=other.get_pattern_names()[0])
        self.assertFalse(other.song_is_untouched(names.MSG_DEFAULT_SONG_NAME))

    def test_a_song_just_added_is_untouched_and_a_made_song_is_not(self):
        setlist = a_new_set()
        setlist.add_new_song(SECOND)
        setlist.get_song(SECOND).fill_in_defaults()
        self.assertTrue(setlist.song_is_untouched(SECOND))
        setlist.take_in(made(name=FIRST))
        self.assertFalse(setlist.song_is_untouched(FIRST))

    def test_a_song_is_replaced_under_a_new_name_when_one_is_given(self):
        setlist = a_new_set()
        self.assertEqual(setlist.replace_song(name=names.MSG_DEFAULT_SONG_NAME, other=made(name=FIRST), new=SECOND), SECOND)
        self.assertEqual(setlist.get_song_names(), [SECOND])


class TestWizardChoicesKept(unittest.TestCase):
    """A song keeps what the song wizard was told, as data of its own."""

    def test_a_song_the_wizard_did_not_make_keeps_none(self):
        self.assertIsNone(a_new_set().get_song(names.MSG_DEFAULT_SONG_NAME).get_wizard_choices())

    def test_the_choices_are_kept_written_and_read_and_share_nothing_with_what_was_given(self):
        setlist = a_new_set()
        song = setlist.get_song(names.MSG_DEFAULT_SONG_NAME)
        given = {key: (dict(value) if isinstance(value, dict) else value) for key, value in SOME_CHOICES.items()}
        song.set_wizard_choices(given)
        given[KEY][ROOT] = A_ROOT
        self.assertEqual(song.get_wizard_choices(), SOME_CHOICES)
        song.get_wizard_choices()[KEY][ROOT] = A_ROOT
        self.assertEqual(song.get_wizard_choices(), SOME_CHOICES)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, A_FILE)
            setlist.write_file(path)
            self.assertEqual(Setlist.read_file(path).get_song(names.MSG_DEFAULT_SONG_NAME).get_wizard_choices(), SOME_CHOICES)
        song.set_wizard_choices(None)
        self.assertIsNone(song.get_wizard_choices())

    def test_a_songs_preview_instrument_is_written_to_the_file(self):
        # The writer once left the preview instrument out, so a saved set forgot it.
        setlist = a_new_set()
        setlist.take_in(made(name=FIRST))
        instrument = setlist.get_instrument_names()[0]
        setlist.get_song(FIRST).set_preview_instrument_name(instrument)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, A_FILE)
            setlist.write_file(path)
            self.assertEqual(Setlist.read_file(path).get_song(FIRST).get_preview_instrument_name(), instrument)


class TestEverythingNamed(unittest.TestCase):
    """What a set names, found in one walk, is what asking about each item one at a time finds."""

    def assert_the_walk_agrees(self, setlist):
        named = setlist.everything_named()
        items = [(section, name) for section in setlist_values.SECTIONS_TAKEN_IN for name in setlist.get_item_names(section)]
        self.assertTrue(items)
        for section, name in items:
            if section == Section.SONGS:
                continue
            with self.subTest(section=section, name=name):
                self.assertEqual((section, name) in named, setlist.is_named(section=section, name=name))

    def test_they_agree_on_a_made_set_before_and_after_what_nothing_names_is_removed(self):
        setlist = made(name=FIRST)
        self.assert_the_walk_agrees(setlist)
        chain = setlist.get_chain_names()[0]
        generators = setlist.get_chain(chain).named_items()
        self.assertTrue(generators)
        song = setlist.get_song(FIRST)
        for _, number, _, track in setlist.clip_slots_naming(section=Section.CHAINS, name=chain):
            song.get_scenes()[number - 1].remove_clip_slot(track)
        self.assert_the_walk_agrees(setlist)
        setlist.remove_unused()
        self.assert_the_walk_agrees(setlist)
        for section, name in setlist.named_by_songs():
            self.assertTrue(setlist.is_named(section=section, name=name), (section, name))


def check_walk(*, test, path):
    """The walk of everything named and the question of one name agree on every item of an example."""
    TestEverythingNamed.assert_the_walk_agrees(test, Setlist.read_file(path))

