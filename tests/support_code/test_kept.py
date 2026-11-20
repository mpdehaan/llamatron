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
"""Tests of kept_while: an answer worked out once and kept while its key stays the same."""

import unittest

from llamatron.support import kept
from llamatron.support.kept import forget_kept, kept_for_life, kept_while
from llamatron.support.memory import Memory, StaleAnswer

A_KEY = 'first'
ANOTHER_KEY = 'second'


class Counting:
    """An object whose answer counts how many times it was worked out, kept while its key is the same."""

    __slots__ = ('_kept', 'key', 'worked_out')

    def __init__(self):
        self._kept = {}
        self.key = A_KEY
        self.worked_out = 0

    @kept_while(lambda counting: counting.key)
    def answer(self):
        """Return the key and how many times the answer has been worked out."""
        self.worked_out += 1
        return (self.key, self.worked_out)

    @kept_while(lambda counting: counting.key)
    def doubled(self, *, number):
        """Return a number doubled, counting how many times it was worked out."""
        self.worked_out += 1
        return number * 2


class Checked:
    """An object whose kept answer leaves out what it depends on, which the tests' check finds: its key never changes."""

    __slots__ = ('_kept', 'value')

    def __init__(self):
        self._kept = {}
        self.value = 1

    @kept_while(lambda checked: A_KEY, said=list)
    def values(self):
        """Return a list of the value, kept by a key that leaves the value out."""
        return [self.value]

    @kept_for_life
    def tripled(self, *, number):
        """Return a number tripled."""
        return number * 3


class TestKeptWhile(unittest.TestCase):

    def test_an_answer_is_worked_out_once_while_its_key_stays_the_same(self):
        counting = Counting()
        first = counting.answer()
        self.assertIs(counting.answer(), first)
        self.assertEqual(counting.worked_out, 1)

    def test_a_new_key_works_the_answer_out_again_and_a_key_of_none_keeps_nothing(self):
        counting = Counting()
        counting.answer()
        counting.key = ANOTHER_KEY
        self.assertEqual(counting.answer(), (ANOTHER_KEY, 2))
        counting.key = None
        counting.answer()
        counting.answer()
        self.assertEqual(counting.worked_out, 4)

    def test_each_set_of_arguments_keeps_an_answer_of_its_own_until_the_key_changes(self):
        counting = Counting()
        self.assertEqual([counting.doubled(number=2), counting.doubled(number=3), counting.doubled(number=2)], [4, 6, 4])
        self.assertEqual(counting.worked_out, 2)
        counting.key = ANOTHER_KEY
        counting.doubled(number=2)
        self.assertEqual(counting.worked_out, 3)

    def test_answers_are_kept_on_their_own_object_by_the_methods_name(self):
        one = Counting()
        other = Counting()
        one.answer()
        other.answer()
        self.assertEqual((one.worked_out, other.worked_out), (1, 1))
        self.assertEqual(list(getattr(one, kept.KEPT)), [Counting.answer.__name__])


    def test_forget_kept_drops_every_answer(self):
        counting = Counting()
        counting.answer()
        forget_kept(counting)
        counting.answer()
        self.assertEqual(counting.worked_out, 2)


class TestKeptChecked(unittest.TestCase):
    """A method given said is worked out again on every call while the tests check every remembered answer, as a Memory is."""

    def setUp(self):
        self.checked_before = Memory.checks_by_default()
        Memory.check_every_answer()

    def tearDown(self):
        Memory.check_every_answer(checks=self.checked_before)

    def test_a_key_that_leaves_out_what_the_answer_depends_on_is_found_while_answers_are_checked(self):
        checked = Checked()
        checked.values()
        checked.value = 2
        with self.assertRaises(StaleAnswer):
            checked.values()

    def test_without_the_checks_the_kept_answer_is_returned(self):
        Memory.check_every_answer(checks=False)
        checked = Checked()
        first = checked.values()
        checked.value = 2
        self.assertIs(checked.values(), first)

    def test_an_answer_kept_for_life_is_kept_by_its_arguments_alone(self):
        checked = Checked()
        self.assertEqual([checked.tripled(number=2), checked.tripled(number=3)], [6, 9])
        self.assertEqual(len(getattr(checked, kept.KEPT)[Checked.tripled.__name__][1]), 2)


if __name__ == '__main__':
    unittest.main()
