# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every check that holds of each example set alone, an example to a class, so that a class reads and renders its example once
(tests/support/example_renders.py) and every check shares that, and the classes run side by side.

Each check lives in the module of what it checks, as a function of the test and the example's path; this module only gathers
them, so that a new check of every example is added there and listed here.
"""

import os
import re
import unittest

from llamatron.support.example_sets import example_sets
from tests.app.test_examples import check_clips_fit, check_exports, check_homage_folder, check_length, check_sounds
from tests.composition.test_kept_data import check_kept_data
from tests.composition.test_renames import check_renames
from tests.composition.test_song_writer import check_written
from tests.composition.test_taking_in import check_walk
from tests.grid.test_clip_lengths import check_lengths_agree
from tests.grid.test_clip_sounds import BothWays, check_both_ways
from tests.importers.test_midi_import import check_round_trip
from tests.realtime.test_realtime import check_player_follows, check_timeline
from tests.tui.test_tui_document import check_saves_and_loads

# Every check of one example, by what its test is called.
CHECKS = {
    'homage_folder': check_homage_folder, 'length': check_length, 'clips_fit': check_clips_fit, 'exports': check_exports,
    'sounds': check_sounds, 'kept_data': check_kept_data, 'renames': check_renames, 'written': check_written, 'walk': check_walk,
    'lengths_agree': check_lengths_agree, 'both_ways': check_both_ways, 'round_trip': check_round_trip, 'timeline': check_timeline,
    'player_follows': check_player_follows, 'saves_and_loads': check_saves_and_loads,
}
# The checks only a demo has.
TEST_NAME = 'test_{}'
CLASS_NAME = 'TestExample{}'
# What a file's name keeps in its class's name.
NAME_PARTS = re.compile(r'[A-Za-z0-9]+')


def test_of(*, check, path):
    def test(self):
        check(test=self, path=path)
    return test


def class_name(path):
    """Return the class of an example's name, like TestExample01HelloWorld, from its file's name."""
    stem = os.path.splitext(os.path.basename(path))[0]
    return CLASS_NAME.format(''.join(part.capitalize() for part in NAME_PARTS.findall(stem)))


def class_for(path):
    """Return the class of one example: a test for each check, every one of them reading the one render the class shares."""
    tests = {TEST_NAME.format(name): test_of(check=check, path=path) for name, check in CHECKS.items()}
    return type(class_name(path), (BothWays,), {'__slots__': (), **tests})


for an_example in example_sets():
    a_class = class_for(an_example)
    globals()[a_class.__name__] = a_class
del an_example, a_class


class TestEveryExampleHasItsClass(unittest.TestCase):

    def test_every_example_has_a_class_of_its_own_name(self):
        names = [class_name(path) for path in example_sets()]
        self.assertEqual(len(set(names)), len(names))
        for name in names:
            self.assertIn(name, globals())


if __name__ == '__main__':
    unittest.main()
