# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""LlamaData, the base class of everything a song file stores, and its rule that subclasses
define both to_data() and from_data()."""

import importlib
import pkgutil
import unittest

import llamatron.model
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.generator_settings import MusicianSettings
from llamatron.model.objects.llama_data import HoldsSettings, LlamaData
from llamatron.model.objects.setlist import Setlist
from llamatron.model.objects.song import Song
from llamatron.model.objects.track import Track
from llamatron.model.vocabulary import defaults, limits
from llamatron.model.vocabulary.file_format import Section, TrackSetting
from llamatron.user_strings import errors


def every_subclass():
    """Return every LlamaData subclass in the Model, importing all of it first."""
    for module in pkgutil.walk_packages(llamatron.model.__path__, llamatron.model.__name__ + '.'):
        importlib.import_module(module.name)
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

# A track's name made up for a test.
A_TRACK = 'lead'

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


class TestASettingLeftOutNamesNothing(unittest.TestCase):
    """A setting that names an item and that a file leaves out names nothing: a musician that follows no track's chords, asked what
    it names as a render keeps clips after an edit, once failed for want of the setting."""

    def test_a_musician_with_no_track_to_follow_names_nothing(self):
        musician = MusicianSettings({})
        self.assertEqual(musician.named_items(), set())
        self.assertFalse(musician.names_item(section=Section.TRACKS, name=A_TRACK))
