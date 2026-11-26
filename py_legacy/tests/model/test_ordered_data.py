# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of same_in_order, which counts the order of a set's items where == on dictionaries doesn't."""

import unittest

from llamatron.model.file.ordered_data import same_in_order


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
