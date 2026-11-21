# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The genre measures of internal_tools/analysis_and_generation/, one quick check of its main path: a song keeps every measure within its units bounds. A research tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

from measuring.hearing.performance import performance_of
from measuring.hearing.profile import profile_of_performance
from measuring.measures.registry import MEASURES
import os
import unittest

from llamatron.composition.setlist import Setlist

DEMO = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, 'examples', 'by_genre', 'rock', 'green_men.yml')
SEED = 1


def demo_performance():
    setlist = Setlist.read_file(DEMO)
    return performance_of(setlist.get_song(setlist.get_song_names()[0]), seed=SEED)


def out_of_bounds(*, subject):
    """Return the names of the measures whose value in a subject lies outside its unit's bounds."""
    found = []
    for each in MEASURES:
        value = each.of(subject)
        bounds = each.bounds()
        if bounds is None or value is None:
            continue
        values = value if isinstance(value, tuple) else (value,)
        if any(not bounds[0] <= one <= bounds[1] for one in values):
            found.append(each.name())
    return found


class TestReadingMeasures(unittest.TestCase):

    def test_a_song_keeps_every_measure_within_its_units_bounds(self):
        profile = profile_of_performance(performance=demo_performance(), name='demo')
        self.assertEqual(out_of_bounds(subject=profile), [])


if __name__ == '__main__':
    unittest.main()
