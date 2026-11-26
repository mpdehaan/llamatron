# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The names the tracker makes up itself: one rule for the whole tracker (.claude/rules/UX.md, "Names the tracker makes")."""

import unittest

from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.naming import copy_name, default_scale_name, is_default_scale_name, is_taken, name_order, new_name, same_name, split_trailing_number, suggested_word, unique_name
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import names

# Names of the tests' own.
FOO = 'foo'
FOO_2 = 'foo-2'
FOO_3 = 'foo-3'
BASS = 'bass'
BASS_CAPITAL = 'Bass'
BASS_2 = 'bass-2'
BASS_3 = 'bass-3'
NAME_1 = 'name1'
NAME_2 = 'name2'
NAME_3 = 'name3'
DASHED_1 = 'name-1'
DASHED_2 = 'name-2'
SPACED_2 = 'bass 2'
SPACED_3 = 'bass 3'
UNDERSCORED_1 = 'verse_1'
UNDERSCORED_2 = 'verse_2'
# A name whose words end in a number themselves, and what a new thing and a duplicate of it are called.
TREBLE_1 = 'treble 1'
TREBLE_1_FIRST = 'treble 1-1'
TREBLE_1_SECOND = 'treble 1-2'
TREBLE_2 = 'treble 2'
ONLY_A_NUMBER = '2'
PATTERN_1 = 'pattern-1'
PATTERN_2 = 'pattern-2'
PATTERN_5 = 'pattern-5'
PATTERN_6 = 'pattern-6'
# A name of the same word written another way, which still counts toward the highest number.
PATTERN_SPACED_7 = 'Pattern 7'
PATTERN_8 = 'pattern-8'
OTHER = 'other'
ROOT_C = 'C'
ROOT_F_SHARP = 'F#'
ROOT_B_FLAT = 'Bb'
MAJOR = 'major'
HARMONIC_MINOR = 'harmonic_minor'
C_MAJOR = 'C_major'
C_MAJOR_LOWER = 'c_major'
C_MAJOR_2 = 'C_major-2'
C_MAJOR_AS_OLDER_FILES_WROTE = 'C Major'
F_SHARP_HARMONIC_MINOR = 'F#_harmonic_minor'
B_FLAT_MAJOR = 'Bb_major'
LABEL = 'Voice Leading'
LABEL_AS_A_NAME = 'voice_leading'
# Names as a sort by letters alone leaves them, and as the tracker orders them.
OUT_OF_ORDER = ['verse-10', 'verse-2', 'verse', 'chorus2', 'chorus10', 'verse_b', 'bass 3']
IN_ORDER = ['bass 3', 'chorus2', 'chorus10', 'verse', 'verse-2', 'verse-10', 'verse_b']
CAPITALS_OUT_OF_ORDER = ['beta', 'Alpha-2', 'alpha-1', 'Gamma']
CAPITALS_IN_ORDER = ['alpha-1', 'Alpha-2', 'beta', 'Gamma']


class TestDuplicateNames(unittest.TestCase):
    """A duplicate counts: a copy, a conflict or an import whose name is taken."""

    def test_a_name_with_no_number_gets_a_dash_and_two_since_the_name_picked_is_the_first(self):
        self.assertEqual(copy_name(name=FOO, taken=[FOO]), FOO_2)

    def test_the_number_goes_on_until_the_name_is_free(self):
        self.assertEqual(copy_name(name=FOO, taken=[FOO, FOO_2]), FOO_3)

    def test_a_name_that_counts_already_counts_up_and_keeps_its_joint(self):
        self.assertEqual(copy_name(name=BASS_2, taken=[BASS_2]), BASS_3)
        self.assertEqual(copy_name(name=NAME_1, taken=[NAME_1]), NAME_2)
        self.assertEqual(copy_name(name=NAME_1, taken=[NAME_1, NAME_2]), NAME_3)
        self.assertEqual(copy_name(name=DASHED_1, taken=[DASHED_1]), DASHED_2)
        self.assertEqual(copy_name(name=SPACED_2, taken=[SPACED_2]), SPACED_3)
        self.assertEqual(copy_name(name=UNDERSCORED_1, taken=[UNDERSCORED_1]), UNDERSCORED_2)

    def test_no_number_is_added_after_a_number(self):
        self.assertEqual(copy_name(name=TREBLE_1, taken=[TREBLE_1]), TREBLE_2)

    def test_a_name_wanted_is_kept_while_it_is_free(self):
        self.assertEqual(unique_name(base=FOO, taken=[OTHER]), FOO)
        self.assertEqual(unique_name(base=FOO, taken=[FOO]), FOO_2)

    def test_capitals_make_no_difference_to_what_is_taken_and_the_name_keeps_its_own(self):
        self.assertEqual(unique_name(base=BASS_CAPITAL, taken=[BASS]), 'Bass-2')
        self.assertEqual(copy_name(name=BASS, taken=[BASS, 'BASS-2']), BASS_3)


class TestNewNames(unittest.TestCase):
    """A new thing is its kind's word, a dash and one more than the highest number in use."""

    def test_the_first_is_one(self):
        self.assertEqual(new_name(word=names.MSG_NEW_PATTERN_WORD, taken=[OTHER]), PATTERN_1)

    def test_a_new_thing_never_takes_the_number_of_one_deleted(self):
        self.assertEqual(new_name(word=names.MSG_NEW_PATTERN_WORD, taken=[PATTERN_1, PATTERN_2, PATTERN_5]), PATTERN_6)

    def test_every_way_of_writing_the_word_and_its_number_counts(self):
        self.assertEqual(new_name(word=names.MSG_NEW_PATTERN_WORD, taken=[PATTERN_1, PATTERN_SPACED_7]), PATTERN_8)

    def test_a_word_that_ends_in_a_number_is_still_counted_by_the_number_after_the_dash(self):
        self.assertEqual(new_name(word=TREBLE_1, taken=[]), TREBLE_1_FIRST)
        self.assertEqual(new_name(word=TREBLE_1, taken=[TREBLE_1_FIRST]), TREBLE_1_SECOND)

    def test_a_label_becomes_lowercase_with_underscores(self):
        self.assertEqual(suggested_word(LABEL), LABEL_AS_A_NAME)


class TestTrailingNumbers(unittest.TestCase):

    def test_a_name_is_split_into_its_words_its_joint_and_its_number(self):
        self.assertEqual(split_trailing_number(BASS_2), (BASS, '-', 2))
        self.assertEqual(split_trailing_number(NAME_1), ('name', '', 1))
        self.assertEqual(split_trailing_number(TREBLE_1_FIRST), (TREBLE_1, '-', 1))

    def test_a_name_with_no_number_or_nothing_but_one_has_none(self):
        self.assertEqual(split_trailing_number(BASS), (BASS, None, None))
        self.assertEqual(split_trailing_number(ONLY_A_NUMBER), (ONLY_A_NUMBER, None, None))


class TestTheOrderOfNames(unittest.TestCase):
    """Names are sorted by their words, ignoring capitals, and then by the number they end in, read as a number."""

    def test_a_number_at_the_end_counts_as_a_number_and_a_name_without_one_comes_first(self):
        self.assertEqual(sorted(OUT_OF_ORDER, key=name_order), IN_ORDER)

    def test_capitals_make_no_difference(self):
        self.assertEqual(sorted(CAPITALS_OUT_OF_ORDER, key=name_order), CAPITALS_IN_ORDER)


class TestScaleNames(unittest.TestCase):
    """A scale is named after its root and kind in lowercase with underscores, the note's name keeping its capital and its mark."""

    def test_the_note_keeps_its_capital_and_its_mark(self):
        self.assertEqual(default_scale_name(root=ROOT_C, kind=MAJOR), C_MAJOR)
        self.assertEqual(default_scale_name(root=ROOT_F_SHARP, kind=HARMONIC_MINOR), F_SHARP_HARMONIC_MINOR)
        self.assertEqual(default_scale_name(root=ROOT_B_FLAT, kind=MAJOR), B_FLAT_MAJOR)

    def test_a_second_scale_of_the_same_notes_is_a_duplicate(self):
        self.assertEqual(unique_name(base=C_MAJOR, taken=[C_MAJOR]), C_MAJOR_2)

    def test_a_new_set_starts_with_a_scale_named_by_its_number(self):
        # A name after the notes was wrong once the notes changed, so a new scale is numbered as every new thing.
        self.assertEqual(Setlist.new().get_item_names(Section.SCALES), [new_name(word=names.MSG_NEW_SCALE_WORD, taken=[])])

    def test_an_older_files_name_still_says_what_the_scale_is(self):
        self.assertTrue(is_default_scale_name(name=C_MAJOR, root=ROOT_C, kind=MAJOR))
        self.assertTrue(is_default_scale_name(name=C_MAJOR_AS_OLDER_FILES_WROTE, root=ROOT_C, kind=MAJOR))
        self.assertFalse(is_default_scale_name(name=OTHER, root=ROOT_C, kind=MAJOR))


class TestNamesWithoutRegardToCapitals(unittest.TestCase):
    """Names are compared without regard to capitals and kept as typed."""

    def setUp(self):
        self.setlist = Setlist.new()
        self.first = self.setlist.get_item_names(Section.PATTERNS)[0]
        self.setlist.copy_item(section=Section.PATTERNS, name=self.first, new=BASS)

    def test_two_names_that_differ_in_capitals_are_one_name(self):
        self.assertTrue(same_name(one=BASS, other=BASS_CAPITAL))
        self.assertTrue(is_taken(name=BASS_CAPITAL, taken=[BASS]))
        self.assertFalse(is_taken(name=FOO, taken=[BASS]))

    def test_a_rename_to_another_things_name_in_other_capitals_is_refused(self):
        with self.assertRaises(InvalidValue):
            self.setlist.rename_item(section=Section.PATTERNS, old=self.first, new=BASS_CAPITAL)

    def test_a_copy_under_another_things_name_in_other_capitals_is_refused(self):
        with self.assertRaises(InvalidValue):
            self.setlist.copy_item(section=Section.PATTERNS, name=self.first, new=BASS_CAPITAL)

    def test_a_thing_can_change_the_capitals_of_its_own_name(self):
        self.setlist.rename_item(section=Section.PATTERNS, old=BASS, new=BASS_CAPITAL)
        self.assertIn(BASS_CAPITAL, self.setlist.get_item_names(Section.PATTERNS))
        self.assertNotIn(BASS, self.setlist.get_item_names(Section.PATTERNS))

    def test_a_file_that_holds_both_still_loads(self):
        data = self.setlist.to_data()
        patterns = data[Section.PATTERNS]
        patterns[BASS_CAPITAL] = dict(patterns[BASS])
        loaded = Setlist.from_data(data=data)
        self.assertIn(BASS, loaded.get_item_names(Section.PATTERNS))
        self.assertIn(BASS_CAPITAL, loaded.get_item_names(Section.PATTERNS))


if __name__ == '__main__':
    unittest.main()
