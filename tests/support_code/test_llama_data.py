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

"""LlamaData, the base class of everything a song file stores, and its rule that subclasses
define both to_data() and from_data()."""

import importlib
import pkgutil
import unittest

import llamatron.composition
from llamatron.composition import defaults, limits
from llamatron.composition.file_format import TrackSetting
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.llama_data import HoldsSettings, LlamaData
from llamatron.composition.setlist import Setlist
from llamatron.composition.song import Song
from llamatron.composition.track import Track
from llamatron.strings import errors


def every_subclass():
    """Return every LlamaData subclass in the composition package, importing all of it first."""
    for module in pkgutil.iter_modules(llamatron.composition.__path__):
        importlib.import_module(f'llamatron.composition.{module.name}')
    found = []
    waiting = list(LlamaData.__subclasses__())
    while waiting:
        subclass = waiting.pop()
        found.append(subclass)
        waiting += subclass.__subclasses__()
    return found

# The classes that exist to be subclassed, which no file holds and which read nothing themselves.
SUPERCLASSES = (HoldsSettings,)
# What holds everything else and is never copied whole by copy(): the set, and a song, which the set copies through its data.
NEVER_COPIED = (Setlist, Song)


class TestLlamaData(unittest.TestCase):

    def test_the_base_class_says_what_is_missing(self):
        with self.assertRaisesRegex(NotImplementedError, 'LlamaData needs a to_data'):
            LlamaData().to_data()
        with self.assertRaisesRegex(NotImplementedError, 'LlamaData needs a from_data'):
            LlamaData.from_data(data={}, where='the file')

    def test_a_subclass_without_its_own_methods_is_caught(self):
        class Incomplete(LlamaData):
            pass
        with self.assertRaisesRegex(NotImplementedError, 'Incomplete needs a to_data'):
            Incomplete().to_data()

    def test_every_kind_of_object_in_a_song_file_is_one(self):
        names = {subclass.__name__ for subclass in every_subclass()}
        for name in ['Setlist', 'Song', 'Scene', 'ClipSlot', 'Track', 'Pattern', 'NamedScale', 'Chain', 'ArpSettings', 'AutoRatchetSettings']:
            with self.subTest(name=name):
                self.assertIn(name, names)

    def test_every_subclass_defines_both_methods(self):
        for subclass in every_subclass():
            if subclass.__module__ == __name__ or subclass in SUPERCLASSES:
                continue
            with self.subTest(subclass=subclass.__name__):
                self.assertIsNot(subclass.to_data, LlamaData.to_data)
                self.assertIsNot(subclass.from_data.__func__, LlamaData.from_data.__func__)


    def test_everything_that_is_copied_says_how(self):
        for subclass in every_subclass():
            if subclass.__module__ == __name__ or subclass in SUPERCLASSES or subclass in NEVER_COPIED:
                continue
            with self.subTest(subclass=subclass.__name__):
                self.assertIsNot(subclass.copy, LlamaData.copy)

    def test_the_base_class_says_a_copy_is_missing(self):
        with self.assertRaises(NotImplementedError) as refused:
            LlamaData().copy()
        self.assertEqual(str(refused.exception), errors.ERR_NEEDS_COPY.format(kind=LlamaData.__name__))

    def test_a_holder_of_settings_checks_a_value_by_its_description_and_leaves_none_and_the_default_out(self):
        track = Track()
        track.set_written(name=TrackSetting.ACCENT, value=limits.MAX_STEP_ACCENT)
        self.assertEqual(track.get_written(TrackSetting.ACCENT), limits.MAX_STEP_ACCENT)
        self.assertEqual(track.to_data(), {TrackSetting.ACCENT: limits.MAX_STEP_ACCENT})
        with self.assertRaises(InvalidValue):
            track.set_written(name=TrackSetting.ACCENT, value=limits.MAX_STEP_ACCENT + 1)
        before = track.get_revision()
        track.set_written(name=TrackSetting.ACCENT, value=None)
        self.assertEqual(track.to_data(), {})
        self.assertNotEqual(track.get_revision(), before)
        track.set_written_unless_default(name=TrackSetting.ACCENT, value=defaults.DEFAULT_TRACK_ACCENT, default=defaults.DEFAULT_TRACK_ACCENT)
        self.assertIsNone(track.get_written(TrackSetting.ACCENT))


if __name__ == '__main__':
    unittest.main()
