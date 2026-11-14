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
"""The Document's edits of anything with a name: renaming, copying, deleting, moving and sorting take the section (tui/document_parts/named_edits.py).

Every section is edited through the same five methods, so each is tested on every section, and
then the little that differs by kind: the current song, a factory groove's copy and a track's.
"""

import unittest

from ui_testing import DRUMS, LEAD, NAMED, ONE, TUNE, a_song
from llamatron.composition.file_format import Section
from llamatron.composition.groove import FactoryGroove
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.sections import SONG_SECTIONS
from llamatron.strings.errors import ERR_LAST_SONG
from llamatron.strings.names import MSG_DEFAULT_SONG_NAME
from llamatron.composition.naming import copy_name

# The sections whose items have names, which are every section these edits take.
NAMED_SECTIONS = [
    Section.PATTERNS, Section.SCALES, Section.ARPS, Section.AUTO_RATCHETS, Section.CHAINS, Section.GROOVES, Section.SONGS, Section.TRACKS,
]
A_GROOVE = 'shuffle'
RENAMED = 'renamed'
SECOND_SONG = 'second'
THIRD_SONG = 'third'
FIRST_PLACE = 0
UP_ONE = -1
DOWN_ONE = 1
FIRST_SCENE = 0


def a_document():
    """Return a document whose every named section has at least one item of the set's own."""
    document = a_song()
    document.add_groove(A_GROOVE)
    return document


def names_of(*, document, section):
    """Return the names of a section's own items, in the section's order: the song's for its tracks, the set's otherwise."""
    if section == Section.GROOVES:
        return document.setlist().get_own_groove_names()
    owner = document.song() if section in SONG_SECTIONS else document.setlist()
    return owner.get_item_names(section)


class TestEveryNamedSectionIsEditedTheSameWay(unittest.TestCase):

    def test_every_section_has_an_item_to_edit(self):
        for section in NAMED_SECTIONS:
            self.assertTrue(names_of(document=a_document(), section=section), section)

    def test_a_copy_is_named_after_the_item_and_returned(self):
        for section in NAMED_SECTIONS:
            with self.subTest(section=section):
                document = a_document()
                before = names_of(document=document, section=section)
                new = document.copy_named(section=section, name=before[FIRST_PLACE])
                self.assertNotIn(new, before)
                self.assertEqual(sorted(names_of(document=document, section=section)), sorted([*before, new]))
                self.assertTrue(document.is_dirty())

    def test_a_rename_changes_the_name_in_place(self):
        for section in NAMED_SECTIONS:
            with self.subTest(section=section):
                document = a_document()
                before = names_of(document=document, section=section)
                document.rename_named(section=section, old=before[FIRST_PLACE], new=RENAMED)
                self.assertEqual(names_of(document=document, section=section), [RENAMED, *before[1:]])

    def test_a_rename_to_a_name_in_use_is_refused(self):
        for section in NAMED_SECTIONS:
            with self.subTest(section=section):
                document = a_document()
                new = document.copy_named(section=section, name=names_of(document=document, section=section)[FIRST_PLACE])
                with self.assertRaises(InvalidValue):
                    document.rename_named(section=section, old=new, new=names_of(document=document, section=section)[FIRST_PLACE])

    def test_a_delete_takes_the_item_away(self):
        for section in NAMED_SECTIONS:
            with self.subTest(section=section):
                document = a_document()
                before = names_of(document=document, section=section)
                new = document.copy_named(section=section, name=before[FIRST_PLACE])
                document.delete_named(section=section, name=new)
                self.assertEqual(names_of(document=document, section=section), before)

    def test_a_move_changes_the_order_and_says_whether_anything_moved(self):
        for section in NAMED_SECTIONS:
            with self.subTest(section=section):
                document = a_document()
                document.copy_named(section=section, name=names_of(document=document, section=section)[FIRST_PLACE])
                before = names_of(document=document, section=section)
                self.assertFalse(document.move_named(section=section, place=FIRST_PLACE, offset=UP_ONE))
                self.assertEqual(names_of(document=document, section=section), before)
                self.assertTrue(document.move_named(section=section, place=FIRST_PLACE, offset=DOWN_ONE))
                self.assertEqual(names_of(document=document, section=section), [before[1], before[0], *before[2:]])

    def test_a_sort_puts_the_names_in_order(self):
        for section in NAMED_SECTIONS:
            with self.subTest(section=section):
                document = a_document()
                document.copy_named(section=section, name=names_of(document=document, section=section)[FIRST_PLACE])
                document.move_named(section=section, place=FIRST_PLACE, offset=DOWN_ONE)
                document.sort_named(section)
                names = names_of(document=document, section=section)
                self.assertEqual(names, sorted(names, key=str.casefold))

    def test_each_edit_is_one_step_to_undo(self):
        for section in NAMED_SECTIONS:
            with self.subTest(section=section):
                document = a_document()
                document.record_edit()
                before = names_of(document=document, section=section)
                document.copy_named(section=section, name=before[FIRST_PLACE])
                document.record_edit()
                document.undo()
                self.assertEqual(names_of(document=document, section=section), before)


class TestWhatDiffersByKind(unittest.TestCase):

    def test_a_renamed_pattern_is_still_what_its_clips_play(self):
        document = a_document()
        document.rename_named(section=Section.PATTERNS, old=TUNE, new=RENAMED)
        self.assertEqual(document.song().get_scene(FIRST_SCENE).get_clip_slot(LEAD).get_pattern_name(), RENAMED)

    def test_the_current_song_stays_current_when_it_is_renamed(self):
        document = a_document()
        document.rename_named(section=Section.SONGS, old=MSG_DEFAULT_SONG_NAME, new=RENAMED)
        self.assertEqual(document.current_song_name(), RENAMED)
        self.assertEqual(document.song().get_track_names(), [LEAD, DRUMS])

    def test_renaming_another_song_leaves_the_current_one_current(self):
        document = a_document()
        document.add_song(SECOND_SONG)
        document.rename_named(section=Section.SONGS, old=MSG_DEFAULT_SONG_NAME, new=RENAMED)
        self.assertEqual(document.current_song_name(), SECOND_SONG)

    def test_the_last_song_cannot_be_deleted(self):
        document = a_document()
        with self.assertRaises(InvalidValue) as refused:
            document.delete_named(section=Section.SONGS, name=MSG_DEFAULT_SONG_NAME)
        self.assertEqual(str(refused.exception), ERR_LAST_SONG)
        self.assertEqual(document.song_names(), [MSG_DEFAULT_SONG_NAME])

    def test_deleting_the_current_song_makes_the_one_before_it_current(self):
        document = a_document()
        document.add_song(SECOND_SONG)
        document.add_song(THIRD_SONG)
        document.delete_named(section=Section.SONGS, name=THIRD_SONG)
        self.assertEqual(document.current_song_name(), SECOND_SONG)

    def test_deleting_the_first_song_while_current_makes_the_next_one_current(self):
        document = a_document()
        document.add_song(SECOND_SONG)
        document.select_song(MSG_DEFAULT_SONG_NAME)
        document.delete_named(section=Section.SONGS, name=MSG_DEFAULT_SONG_NAME)
        self.assertEqual(document.current_song_name(), SECOND_SONG)

    def test_deleting_another_song_leaves_the_current_one_current(self):
        document = a_document()
        document.add_song(SECOND_SONG)
        document.delete_named(section=Section.SONGS, name=MSG_DEFAULT_SONG_NAME)
        self.assertEqual(document.current_song_name(), SECOND_SONG)

    def test_a_factory_groove_is_copied_into_the_sets_own_grooves(self):
        document = a_document()
        taken = document.setlist().get_groove_names()
        new = document.copy_named(section=Section.GROOVES, name=FactoryGroove.SWING_58)
        self.assertEqual(new, copy_name(name=FactoryGroove.SWING_58, taken=taken))
        self.assertEqual(document.setlist().get_own_groove_names(), [A_GROOVE, new])
        self.assertEqual(document.setlist().get_groove(new).to_data(), document.setlist().get_groove(FactoryGroove.SWING_58).to_data())

    def test_a_copied_track_stands_right_after_the_track_with_its_clips(self):
        document = a_document()
        new = document.copy_named(section=Section.TRACKS, name=LEAD)
        self.assertEqual(document.song().get_track_names(), [LEAD, new, DRUMS])
        scene = document.song().get_scene(FIRST_SCENE)
        self.assertEqual(scene.get_clip_slot(new).get_pattern_name(), scene.get_clip_slot(LEAD).get_pattern_name())

    def test_a_deleted_track_takes_its_clips_with_it(self):
        document = a_document()
        document.delete_named(section=Section.TRACKS, name=LEAD)
        self.assertEqual(document.song().get_track_names(), [DRUMS])
        self.assertIsNone(document.song().get_scene(FIRST_SCENE).get_clip_slot(LEAD))

    def test_a_copy_of_a_chain_or_a_scene_name_does_not_touch_the_other_sections(self):
        document = a_document()
        patterns = document.setlist().get_pattern_names()
        document.copy_named(section=Section.CHAINS, name=NAMED)
        self.assertEqual(document.setlist().get_pattern_names(), patterns)
        self.assertEqual(document.song().get_scene(FIRST_SCENE).get_name(), ONE)


if __name__ == '__main__':
    unittest.main()
