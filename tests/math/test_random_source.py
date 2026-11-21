# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later



"""Where random numbers come from (math/random_source.py): a stream seeded on its first draw draws what random.Random draws from
the same seed, whichever draw comes first, and seeds nothing until it is drawn from; with no seed, the program's own stream."""

import random
import unittest
from unittest import mock

from llamatron.math import random_source
from llamatron.math.random_source import drawn_from_when_asked

SEED = '7 scene 2 track lead probability'
DRAWS = 5
COUNT = 16
ITEMS = list(range(COUNT))


def draws_of(source):
    """Return a few of each kind of draw a clip makes, in one order."""
    numbers = [source.random() for _ in range(DRAWS)]
    places = [source.randrange(COUNT) for _ in range(DRAWS)]
    shuffled = list(ITEMS)
    source.shuffle(shuffled)
    return numbers, places, shuffled


class TestSeededOnFirstDraw(unittest.TestCase):

    def test_it_draws_what_a_generator_seeded_at_once_draws(self):
        self.assertEqual(draws_of(drawn_from_when_asked(SEED)), draws_of(random.Random(SEED)))

    def test_a_first_draw_of_any_kind_seeds_it_the_same_way(self):
        late = drawn_from_when_asked(SEED)
        at_once = random.Random(SEED)
        self.assertEqual(late.randrange(COUNT), at_once.randrange(COUNT))
        self.assertEqual(late.random(), at_once.random())

    def test_nothing_is_seeded_until_it_is_drawn_from(self):
        with mock.patch.object(random_source.random, random.Random.__name__) as made:
            source = drawn_from_when_asked(SEED)
            made.assert_not_called()
            source.random()
            made.assert_called_once_with(SEED)

    def test_with_no_seed_it_is_the_programs_own_stream(self):
        self.assertIs(drawn_from_when_asked(None), random)


if __name__ == '__main__':
    unittest.main()
