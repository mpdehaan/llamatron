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

"""Tests of same_in_order, which counts the order of a set's items where == on dictionaries doesn't."""

import unittest

from llamatron.support.ordered_data import same_in_order


class TestSameInOrder(unittest.TestCase):

    def test_moved_items_differ_though_the_dictionaries_are_equal(self):
        first = {'patterns': {'a': {'steps': 4}, 'b': {'steps': 8}}}
        moved = {'patterns': {'b': {'steps': 8}, 'a': {'steps': 4}}}
        self.assertEqual(first, moved)
        self.assertFalse(same_in_order(first=first, second=moved))
        self.assertTrue(same_in_order(first=first, second={'patterns': {'a': {'steps': 4}, 'b': {'steps': 8}}}))

    def test_lists_and_plain_values_compare_as_ever(self):
        self.assertTrue(same_in_order(first=[1, {'x': 2}], second=[1, {'x': 2}]))
        self.assertFalse(same_in_order(first=[1, 2], second=[2, 1]))
        self.assertFalse(same_in_order(first=[1], second=[1, 2]))
        self.assertFalse(same_in_order(first={'x': 1}, second=[1]))
        shared = {'deep': [1, 2, 3]}
        self.assertTrue(same_in_order(first=shared, second=shared))
