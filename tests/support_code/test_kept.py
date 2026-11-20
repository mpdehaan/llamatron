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
from llamatron.support.kept import kept_while

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

    def test_answers_are_kept_on_their_own_object_by_the_methods_name(self):
        one = Counting()
        other = Counting()
        one.answer()
        other.answer()
        self.assertEqual((one.worked_out, other.worked_out), (1, 1))
        self.assertEqual(list(getattr(one, kept.KEPT)), [Counting.answer.__name__])


if __name__ == '__main__':
    unittest.main()
