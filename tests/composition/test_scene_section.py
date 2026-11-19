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

"""Tests of the kind of section a scene says it is: kept, written, read back, refused and changing nothing a scene plays."""

import unittest

from llamatron.composition import file_format
from llamatron.composition.file_format import SceneSetting, Section, SectionKind
from llamatron.composition.song_file_error import SongFileError
from llamatron.macro_composer.wizard_choices import WizardChoices
from llamatron.strings import errors
from llamatron.support import version
from tests.support.rendering import render_song, song_from_data
from tests.support import song_testing
from tests.support.song_testing import clip, lead_data, pitches
from tests.support.ui_testing import fixed_text

NOT_A_SECTION = 'middle bit'
# One note a quarter long.
A_STEP = [1, 0.25]
SONG_NAME = 'a_song'
FIRST_SCENE = 1
A_SEED = 11


def a_song():
    return song_from_data(lead_data(A_STEP))


def heard(song):
    """The pitches the song's one clip plays."""
    return pitches(clip(song=render_song(song, seed=A_SEED), scene=FIRST_SCENE, track=song_testing.LEAD))


class TestSceneSection(unittest.TestCase):

    def test_a_scene_says_no_section_until_one_is_set_and_writes_none(self):
        scene = a_song().get_scenes()[0]
        self.assertIsNone(scene.get_section())
        self.assertNotIn(SceneSetting.SECTION, scene.to_data())

    def test_every_kind_can_be_set_written_and_cleared(self):
        scene = a_song().get_scenes()[0]
        for kind in file_format.SECTION_KINDS:
            scene.set_section(kind)
            self.assertEqual(scene.get_section(), kind)
            self.assertEqual(scene.to_data()[SceneSetting.SECTION], kind)
        scene.set_section(None)
        self.assertIsNone(scene.get_section())
        self.assertNotIn(SceneSetting.SECTION, scene.to_data())

    def test_a_kind_no_scene_may_be_is_refused_by_the_setter_and_by_a_file_in_the_same_words(self):
        scene = a_song().get_scenes()[0]
        with self.assertRaises(ValueError) as refused:
            scene.set_section(NOT_A_SECTION)
        self.assertIn(fixed_text(errors.ERR_BAD_SECTION), str(refused.exception))
        self.assertIsNone(scene.get_section())
        data = lead_data(A_STEP)
        data[Section.SCENES][0][SceneSetting.SECTION] = NOT_A_SECTION
        with self.assertRaises(SongFileError) as unread:
            song_from_data(data)
        self.assertIn(fixed_text(errors.ERR_BAD_SECTION), str(unread.exception))

    def test_a_section_is_read_back_from_a_file_and_changes_nothing_the_scene_plays(self):
        data = lead_data(A_STEP)
        plain = heard(song_from_data(data))
        data[Section.SCENES][0][SceneSetting.SECTION] = SectionKind.CHORUS
        read = song_from_data(data)
        self.assertEqual(read.get_scenes()[0].get_section(), SectionKind.CHORUS)
        self.assertEqual(heard(read), plain)

    def test_a_scene_of_the_song_wizard_says_its_kind_of_section(self):
        choices = WizardChoices()
        choices.set_genre('rock')
        choices.set_subgenre('hard rock')
        choices.set_seed(A_SEED)
        scenes = choices.made_setlist(name=SONG_NAME, version=version.VERSION).get_song(SONG_NAME).get_scenes()
        sections = [scene.get_section() for scene in scenes]
        self.assertIn(SectionKind.VERSE, sections)
        self.assertIn(SectionKind.CHORUS, sections)
        for scene in scenes:
            self.assertTrue(scene.get_name().startswith(scene.get_section()))


if __name__ == '__main__':
    unittest.main()
