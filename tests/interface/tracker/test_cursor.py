# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of the cursor and the search a page or a dialog holds, which need no screen."""

import unittest

from llamatron.interface.tracker import cursor as cursor_values
from llamatron.interface.tracker.cursor import Cursor, Search, shown_around
from llamatron.interface.tracker.keys import Key

ROWS = 5
LAST_ROW = ROWS - 1
NAMES = ['bass', 'Bass drum', 'lead', 'pad']
TYPED = 'ba'
PLACES_WITH_BA = [0, 1]
ROOM = 3
HELD_DOWN = ROWS * 2


class TestCursor(unittest.TestCase):

    def test_an_arrow_moves_it_one_place_and_it_stops_at_either_end(self):
        cursor = Cursor()
        cursor.move(name=Key.UP, count=ROWS)
        self.assertTrue(cursor.is_on(cursor_values.FIRST_PLACE))
        for _ in range(HELD_DOWN):
            cursor.move(name=Key.DOWN, count=ROWS)
        self.assertEqual(cursor.get_place(), LAST_ROW)
        cursor.move(name=Key.LEFT, count=ROWS)
        self.assertEqual(cursor.get_place(), LAST_ROW - 1)

    def test_it_comes_back_inside_a_list_that_got_shorter_and_shifts_with_what_it_carries(self):
        cursor = Cursor(place=LAST_ROW)
        cursor.keep_within(ROOM)
        self.assertEqual(cursor.get_place(), ROOM - 1)
        cursor.shift(1)
        self.assertEqual(cursor.get_place(), ROOM)
        cursor.keep_within(0)
        self.assertEqual(cursor.get_place(), cursor_values.FIRST_PLACE)

    def test_among_the_rows_a_search_keeps_it_steps_from_one_to_the_next_and_goes_to_the_first_when_on_none(self):
        cursor = Cursor(place=LAST_ROW)
        kept = [1, 3]
        cursor.move_among(name=Key.DOWN, places=kept)
        self.assertEqual(cursor.get_place(), kept[0])
        cursor.move_among(name=Key.DOWN, places=kept)
        cursor.move_among(name=Key.DOWN, places=kept)
        self.assertEqual(cursor.get_place(), kept[-1])
        cursor.keep_among(kept)
        self.assertEqual(cursor.get_place(), kept[-1])
        cursor.keep_among([0])
        self.assertEqual(cursor.get_place(), 0)
        cursor.move_among(name=Key.DOWN, places=[])
        cursor.keep_among([])
        self.assertEqual(cursor.get_place(), 0)


class TestSearch(unittest.TestCase):

    def typed(self, text):
        search = Search()
        for character in text:
            search.type_key(character)
        return search

    def test_nothing_typed_keeps_every_option_and_typing_keeps_those_that_contain_it_whatever_the_case(self):
        self.assertEqual(Search().places_matching(NAMES), list(range(len(NAMES))))
        self.assertEqual(self.typed(TYPED).places_matching(NAMES), PLACES_WITH_BA)

    def test_space_types_a_space_erasing_takes_the_last_character_and_clearing_takes_all(self):
        search = self.typed(TYPED)
        search.type_key(Key.SPACE)
        self.assertEqual(search.get_typed(), TYPED + ' ')
        search.erase()
        self.assertEqual(search.get_typed(), TYPED)
        search.clear()
        self.assertEqual(search.get_typed(), cursor_values.NOTHING_TYPED)

    def test_completing_grows_what_was_typed_as_far_as_every_match_agrees_from_its_start(self):
        search = self.typed(TYPED)
        search.complete(NAMES)
        self.assertEqual(search.get_typed(), NAMES[0])
        inside = self.typed('as')
        inside.complete(NAMES)
        self.assertEqual(inside.get_typed(), 'as')


class TestShownAround(unittest.TestCase):

    def test_a_list_shows_the_rows_around_the_cursor_and_stays_full_at_either_end(self):
        places = list(range(ROWS))
        self.assertEqual(shown_around(places=places, at=0, room=ROOM), [0, 1, 2])
        self.assertEqual(shown_around(places=places, at=2, room=ROOM), [1, 2, 3])
        self.assertEqual(shown_around(places=places, at=LAST_ROW, room=ROOM), [2, 3, 4])
        self.assertEqual(shown_around(places=places, at=0, room=ROWS * 2), places)


if __name__ == '__main__':
    unittest.main()
