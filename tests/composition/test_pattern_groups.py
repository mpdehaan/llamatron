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

"""Pattern groups: the group a pattern says it is in, the groups a set shows closed, a group renamed, emptied and copied, and patterns grouped by the track that plays them."""

import os
import tempfile
import unittest

from llamatron.composition.file_format import CLOSED_PATTERN_GROUPS, ClipSlotSetting, PatternSetting, SceneSetting, Section
from llamatron.composition.limits import MAX_NAME_LENGTH
from llamatron.composition.naming import name_in_copied_group
from llamatron.composition.setlist import Setlist, new_setlist
from llamatron.composition.song_file_error import SongFileError
from llamatron.strings.errors import ERR_GROUP_COPY_NAME_TOO_LONG, ERR_NOT_TEXT
from llamatron.strings.names import MSG_DEFAULT_SONG_NAME

# The tests' own names.
BASS = 'bass'
DRUMS = 'drums'
LEAD = 'lead'
BASS_VERSE = 'bass_verse'
BASS_CHORUS = 'bass_chorus'
KICK = 'kick'
LOOSE = 'loose'
UNPLAYED = 'unplayed'
SOLO = 'solo'
BASS_COPY = 'bass-2'
A_NUMBER = 7
NO_SUCH_GROUP = 'gone'
SAVED_FILE = 'groups.yml'
STEPS = 4
# A group's name that leaves a copied pattern's name one character too long.
LONG_GROUP = 'g' * (MAX_NAME_LENGTH - len(LOOSE))


def a_set():
    """Return a set of two bass patterns and a kick in their groups, a pattern in none that the lead plays, and one nothing plays."""
    data = new_setlist()
    data[Section.PATTERNS] = {
        BASS_VERSE: {PatternSetting.GROUP: BASS, PatternSetting.STEPS: STEPS}, BASS_CHORUS: {PatternSetting.GROUP: BASS, PatternSetting.STEPS: STEPS},
        KICK: {PatternSetting.GROUP: DRUMS, PatternSetting.STEPS: STEPS}, LOOSE: {PatternSetting.STEPS: STEPS}, UNPLAYED: {PatternSetting.STEPS: STEPS},
    }
    song = data[Section.SONGS][MSG_DEFAULT_SONG_NAME]
    song[Section.TRACKS] = {BASS: {}, LEAD: {}}
    song[Section.SCENES] = [{SceneSetting.TRACKS: {BASS: {ClipSlotSetting.PATTERN: BASS_VERSE}, LEAD: {ClipSlotSetting.PATTERN: LOOSE}}}, {SceneSetting.TRACKS: {BASS: {ClipSlotSetting.PATTERN: LOOSE}}}]
    return data


class TestAPatternsGroup(unittest.TestCase):

    def setUp(self):
        self.setlist = Setlist.from_data(data=a_set())

    def test_a_file_says_each_patterns_group_and_a_pattern_may_be_in_none(self):
        self.assertEqual(self.setlist.get_pattern(KICK).get_group(), DRUMS)
        self.assertIsNone(self.setlist.get_pattern(LOOSE).get_group())
        written = self.setlist.to_data()[Section.PATTERNS]
        self.assertEqual(written[KICK][PatternSetting.GROUP], DRUMS)
        self.assertNotIn(PatternSetting.GROUP, written[LOOSE])

    def test_a_group_that_is_not_text_is_refused_by_a_file_and_by_the_setter_in_the_same_words(self):
        data = a_set()
        data[Section.PATTERNS][KICK][PatternSetting.GROUP] = A_NUMBER
        refusal = ERR_NOT_TEXT.format(name=PatternSetting.GROUP, value=A_NUMBER)
        with self.assertRaises(SongFileError) as refused:
            Setlist.from_data(data=data)
        self.assertIn(refusal, str(refused.exception))
        with self.assertRaises(ValueError) as refused:
            self.setlist.get_pattern(KICK).set_group(A_NUMBER)
        self.assertIn(refusal, str(refused.exception))

    def test_the_groups_and_each_groups_patterns_are_sorted_and_no_group_has_its_own(self):
        self.assertEqual(self.setlist.get_pattern_groups(), [BASS, DRUMS])
        self.assertEqual(self.setlist.patterns_in_group(BASS), [BASS_CHORUS, BASS_VERSE])
        self.assertEqual(self.setlist.patterns_in_group(None), [LOOSE, UNPLAYED])

    def test_a_new_sets_starter_pattern_is_in_the_group_named_after_its_track(self):
        setlist = Setlist.from_data(data=new_setlist())
        [pattern] = setlist.get_pattern_names()
        [track] = setlist.get_song(MSG_DEFAULT_SONG_NAME).get_track_names()
        self.assertEqual(setlist.get_pattern(pattern).get_group(), track)

    def test_renaming_a_group_renames_it_for_every_pattern_in_it(self):
        self.setlist.rename_pattern_group(old=BASS, new=SOLO)
        self.assertEqual(self.setlist.patterns_in_group(SOLO), [BASS_CHORUS, BASS_VERSE])
        self.assertEqual(self.setlist.get_pattern_groups(), [DRUMS, SOLO])

    def test_ungrouping_takes_every_pattern_out_and_deletes_none(self):
        names = self.setlist.get_pattern_names()
        self.setlist.ungroup_patterns(BASS)
        self.assertEqual(self.setlist.get_pattern_names(), names)
        self.assertEqual(self.setlist.get_pattern_groups(), [DRUMS])
        self.assertIsNone(self.setlist.get_pattern(BASS_VERSE).get_group())

    def test_a_copy_of_a_pattern_stays_in_its_group(self):
        copy = self.setlist.copy_item(section=Section.PATTERNS, name=KICK, new=SOLO)
        self.assertEqual(copy.get_group(), DRUMS)


class TestClosedGroups(unittest.TestCase):
    """Which groups the Patterns page shows closed is saved with the set and is no part of the set's data."""

    def setUp(self):
        self.setlist = Setlist.from_data(data=a_set())

    def saved_and_read(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, SAVED_FILE)
            self.setlist.write_file(path)
            return Setlist.read_file(path)

    def test_a_closed_group_is_written_to_the_file_and_read_back_and_is_not_in_the_sets_data(self):
        before = self.setlist.to_data()
        self.setlist.show_pattern_group(group=DRUMS, closed=True)
        self.assertTrue(self.setlist.is_pattern_group_closed(DRUMS))
        self.assertEqual(self.setlist.to_data(), before)
        self.assertEqual(self.saved_and_read().get_closed_pattern_groups(), [DRUMS])
        self.setlist.show_pattern_group(group=DRUMS, closed=False)
        self.assertEqual(self.saved_and_read().get_closed_pattern_groups(), [])

    def test_the_patterns_in_no_group_can_be_shown_closed_for_the_session(self):
        self.setlist.show_pattern_group(group=None, closed=True)
        self.assertTrue(self.setlist.is_pattern_group_closed(None))

    def test_a_file_naming_a_group_no_pattern_is_in_opens_and_forgets_it(self):
        data = a_set()
        data[CLOSED_PATTERN_GROUPS] = [NO_SUCH_GROUP, DRUMS]
        self.assertEqual(Setlist.from_data(data=data).get_closed_pattern_groups(), [DRUMS])

    def test_a_file_holding_anything_else_there_still_opens(self):
        for held in (A_NUMBER, [A_NUMBER, DRUMS], {DRUMS: True}):
            data = a_set()
            data[CLOSED_PATTERN_GROUPS] = held
            self.assertIn(Setlist.from_data(data=data).get_closed_pattern_groups(), ([], [DRUMS]))

    def test_a_renamed_group_stays_closed_and_an_emptied_one_is_forgotten(self):
        self.setlist.show_pattern_group(group=BASS, closed=True)
        self.setlist.rename_pattern_group(old=BASS, new=SOLO)
        self.assertEqual(self.setlist.get_closed_pattern_groups(), [SOLO])
        self.setlist.ungroup_patterns(SOLO)
        self.assertEqual(self.setlist.get_closed_pattern_groups(), [])


class TestCopyingAGroup(unittest.TestCase):

    def setUp(self):
        self.setlist = Setlist.from_data(data=a_set())

    def test_a_name_starting_with_the_groups_takes_the_new_groups_in_its_place_whatever_the_capitals(self):
        self.assertEqual(name_in_copied_group(name=BASS_VERSE, old=BASS, new=BASS_COPY), BASS_COPY + BASS_VERSE[len(BASS):])
        self.assertEqual(name_in_copied_group(name=BASS_VERSE.upper(), old=BASS, new=SOLO), SOLO + BASS_VERSE.upper()[len(BASS):])

    def test_any_other_name_gets_the_new_groups_at_the_front_joined_with_an_underscore(self):
        self.assertEqual(name_in_copied_group(name=KICK, old=DRUMS, new=SOLO), SOLO + '_' + KICK)

    def test_every_pattern_is_copied_into_the_new_group_and_the_old_group_is_left_alone(self):
        copies = self.setlist.copy_pattern_group(group=BASS, new=BASS_COPY)
        self.assertEqual(sorted(copies), self.setlist.patterns_in_group(BASS_COPY))
        self.assertEqual(self.setlist.patterns_in_group(BASS_COPY), [BASS_COPY + BASS_CHORUS[len(BASS):], BASS_COPY + BASS_VERSE[len(BASS):]])
        self.assertEqual(self.setlist.patterns_in_group(BASS), [BASS_CHORUS, BASS_VERSE])
        for name, copied in self.setlist.names_in_copied_group(group=BASS, new=SOLO).items():
            self.assertEqual(self.setlist.get_pattern(name).get_steps(), STEPS, copied)

    def test_a_name_that_is_taken_counts_up(self):
        taken = name_in_copied_group(name=KICK, old=DRUMS, new=SOLO)
        self.setlist.copy_item(section=Section.PATTERNS, name=KICK, new=taken)
        copied = self.setlist.names_in_copied_group(group=DRUMS, new=SOLO)[KICK]
        self.assertNotEqual(copied, taken)
        self.assertTrue(copied.startswith(taken))

    def test_a_copy_with_a_name_too_long_is_refused_whole(self):
        self.setlist.get_pattern(LOOSE).set_group(DRUMS)
        names = self.setlist.get_pattern_names()
        with self.assertRaises(ValueError) as refused:
            self.setlist.copy_pattern_group(group=DRUMS, new=LONG_GROUP)
        too_long = name_in_copied_group(name=LOOSE, old=DRUMS, new=LONG_GROUP)
        self.assertEqual(len(too_long), MAX_NAME_LENGTH + 1)
        self.assertEqual(str(refused.exception), ERR_GROUP_COPY_NAME_TOO_LONG.format(name=too_long, most=MAX_NAME_LENGTH))
        self.assertEqual(self.setlist.get_pattern_names(), names)


class TestGroupingByTrack(unittest.TestCase):
    """A pattern made anywhere but the Patterns page goes in the group named after the track that plays it."""

    def setUp(self):
        self.setlist = Setlist.from_data(data=a_set())

    def test_the_first_track_playing_a_pattern_is_found_scene_by_scene_and_nothing_for_one_unplayed(self):
        self.assertEqual(self.setlist.first_track_playing(BASS_VERSE), BASS)
        self.assertEqual(self.setlist.first_track_playing(LOOSE), LEAD)
        self.assertIsNone(self.setlist.first_track_playing(UNPLAYED))

    def test_patterns_in_no_group_take_their_tracks_and_a_group_already_given_is_kept(self):
        self.setlist.get_pattern(BASS_VERSE).set_group(SOLO)
        self.setlist.group_patterns_by_track(self.setlist.get_song(MSG_DEFAULT_SONG_NAME))
        self.assertEqual(self.setlist.get_pattern(LOOSE).get_group(), LEAD)
        self.assertEqual(self.setlist.get_pattern(BASS_VERSE).get_group(), SOLO)
        self.assertIsNone(self.setlist.get_pattern(UNPLAYED).get_group())


if __name__ == '__main__':
    unittest.main()
