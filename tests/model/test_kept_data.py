# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The data each stored object keeps of itself, which the undo history shares, and a set going back to data it kept.

kept_data() returns what to_data() does, built once and kept until the object changes, and the
set's is put together from its items', so two of the set's snapshots share every piece that no
edit between them touched. That is only safe while nothing can change a piece once it's kept, so
the rule checked here for every example is that data and objects share no list or dictionary:
neither what an object writes with the object, nor an object with the data it was read from.

Setlist.restore() reads data the set kept earlier and keeps every item whose data is unchanged.
Both paths are tested: a set restored to another set's data is what reading that data afresh
makes, and the items whose data is the same are the very objects they were.
"""

import copy
import unittest

from llamatron.engine.generators import arp as arp_plugin, auto_ratchet as auto_ratchet_plugin
from llamatron.engine.generators.arp.model import ArpSetting
from llamatron.model.file.example_sets import example_sets
from llamatron.model.file.setlist_reader import set_file_data
from llamatron.model.objects.llama_data import LlamaData, own_copy
from llamatron.model.objects.named_items import NamedItems
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import PatternSetting, Row, SceneSetting, Section, SetlistSetting, TrackSetting
from tests.support import ui_testing
from tests.support.ui_testing import a_song

EXAMPLES = example_sets()
# The members that aren't part of what an object stores: a song's way back to its set, and the data an object keeps of itself.
NOT_STORED = ('_setlist', '_kept')
SLOTS = '__slots__'
FILE_ENCODING = 'utf-8'
A_VELOCITY = 90
ANOTHER_VELOCITY = 91
A_CC_NUMBER = 74
FIRST_LANE = 0
FIRST_SCENE = 0
SOME_OFFSETS = [0, 2]
AN_OFFSET = 5
A_TITLE = 'a title'
NO_SUCH_ITEM = 'no such item'
MSG_SHARED = '{path}: {count} lists or dictionaries are shared, the first at {where}'


def example_data(path):
    """Return what an example's file holds, as plain data, as the objects read it."""
    return set_file_data(path)[0]


def example_set(path):
    """Return an example as the tracker holds it: read, with every default filled in."""
    setlist = Setlist.from_data(data=example_data(path))
    setlist.fill_in_defaults()
    return setlist


def containers_in_data(*, data, found, where):
    """Note every list and dictionary in plain data, by its identity, with where it is."""
    if isinstance(data, dict):
        found[id(data)] = where
        for key, value in data.items():
            containers_in_data(data=value, found=found, where=(*where, key))
    elif isinstance(data, list):
        found[id(data)] = where
        for place, value in enumerate(data):
            containers_in_data(data=value, found=found, where=(*where, place))


def members_of(thing):
    """Return the values an object stores, by member, through every class it inherits."""
    members = {}
    for kind in type(thing).__mro__:
        for name in getattr(kind, SLOTS, ()):
            if name not in NOT_STORED and hasattr(thing, name):
                members[name] = getattr(thing, name)
    return members


def containers_in_object(*, thing, found, where):
    """Note every list, dictionary and set that an object and the objects inside it store, by its identity, with where it is."""
    if isinstance(thing, (LlamaData, NamedItems)):
        for name, value in members_of(thing).items():
            containers_in_object(thing=value, found=found, where=(*where, type(thing).__name__, name))
    elif isinstance(thing, dict):
        found[id(thing)] = where
        for key, value in thing.items():
            containers_in_object(thing=value, found=found, where=(*where, key))
    elif isinstance(thing, (list, set, tuple)):
        if not isinstance(thing, tuple):
            found[id(thing)] = where
        for value in thing:
            containers_in_object(thing=value, found=found, where=where)


def shared(*, setlist, data):
    """Return where each list or dictionary of some data is also one the set's objects store."""
    in_object = {}
    containers_in_object(thing=setlist, found=in_object, where=())
    in_data = {}
    containers_in_data(data=data, found=in_data, where=())
    return [in_object[identity] for identity in in_object.keys() & in_data.keys()]


class TestDataAndObjectsShareNothing(unittest.TestCase):

    def check_nothing_shared(self, *, path, setlist, data):
        found = shared(setlist=setlist, data=data)
        self.assertEqual(found, [], MSG_SHARED.format(path=path, count=len(found), where=found[:1]))

    def test_the_search_finds_a_list_that_is_shared_and_only_then(self):
        # The detector's two paths, on a set made to share one list with its data and then on one that doesn't.
        document = a_song()
        setlist = document.get_setlist()
        self.assertEqual(shared(setlist=setlist, data=setlist.to_data()), [])
        stored = members_of(setlist.get_pattern(ui_testing.TUNE))
        row = next(value for value in stored.values() if isinstance(value, dict) and Row.DEGREE in value)[Row.DEGREE]
        self.assertEqual(len(shared(setlist=setlist, data={Row.DEGREE: row})), 1)

    def test_a_copy_of_plain_data_is_equal_and_shares_no_list_or_dictionary(self):
        data = {Row.DEGREE: [1, [2, 3]], SetlistSetting.TITLE: {A_TITLE: [None]}}
        copied = own_copy(data)
        self.assertEqual(copied, data)
        found = {}
        containers_in_data(data=data, found=found, where=())
        of_the_copy = {}
        containers_in_data(data=copied, found=of_the_copy, where=())
        self.assertEqual(found.keys() & of_the_copy.keys(), set())
        self.assertIs(own_copy(A_TITLE), A_TITLE)


class TestKeptData(unittest.TestCase):

    def setUp(self):
        self.document = a_song()
        self.setlist = self.document.get_setlist()

    def test_an_object_keeps_one_piece_of_data_until_it_changes(self):
        pattern = self.setlist.get_pattern(ui_testing.TUNE)
        kept = pattern.kept_data()
        self.assertEqual(kept, pattern.to_data())
        self.assertIs(pattern.kept_data(), kept)
        # to_data is the caller's own each time, and changing it reaches nothing kept.
        own = pattern.to_data()
        self.assertIsNot(own, kept)
        own[Row.DEGREE][0] = None
        self.assertEqual(pattern.kept_data(), pattern.to_data())
        pattern.set_value(row=Row.VELOCITY, step=0, value=A_VELOCITY)
        self.assertIsNot(pattern.kept_data(), kept)
        self.assertEqual(pattern.kept_data()[Row.VELOCITY][0], A_VELOCITY)
        # What was kept before the change still says what the pattern was.
        self.assertNotIn(Row.VELOCITY, kept)

    def test_the_sets_data_is_put_together_from_the_pieces_its_items_keep(self):
        before = self.setlist.kept_data()
        self.assertEqual(before, self.setlist.to_data())
        self.document.change_pattern(self.document.pattern(ui_testing.TUNE).set_value, row=Row.VELOCITY, step=0, value=A_VELOCITY)
        after = self.setlist.kept_data()
        self.assertEqual(after, self.setlist.to_data())
        self.assertIsNot(after[Section.PATTERNS][ui_testing.TUNE], before[Section.PATTERNS][ui_testing.TUNE])
        self.assertIs(after[Section.PATTERNS][ui_testing.OTHER], before[Section.PATTERNS][ui_testing.OTHER])
        self.assertIs(after[auto_ratchet_plugin.SECTION][ui_testing.ROLLS], before[auto_ratchet_plugin.SECTION][ui_testing.ROLLS])
        name = self.document.get_current_song_name()
        scenes_before = before[Section.SONGS][name][Section.SCENES]
        scenes_after = after[Section.SONGS][name][Section.SCENES]
        self.assertIs(scenes_after[FIRST_SCENE][SceneSetting.TRACKS][ui_testing.LEAD], scenes_before[FIRST_SCENE][SceneSetting.TRACKS][ui_testing.LEAD])
        self.assertIs(after[Section.SONGS][name][Section.TRACKS][ui_testing.LEAD], before[Section.SONGS][name][Section.TRACKS][ui_testing.LEAD])

    def test_a_part_that_changes_without_its_holder_changing_is_still_seen(self):
        # A clip is changed through the clip, not its scene or its song, whose own revisions stay: the holders' data is put together each time.
        name = self.document.get_current_song_name()
        before = self.setlist.kept_data()
        self.document.set_clip_slot_repeat(index=FIRST_SCENE, track=ui_testing.LEAD, repeat=3)
        self.document.change_set(self.document.song().get_track(ui_testing.LEAD).set_cc_number, lane=FIRST_LANE, number=A_CC_NUMBER)
        after = self.setlist.kept_data()
        self.assertEqual(after, self.setlist.to_data())
        self.assertNotEqual(after[Section.SONGS][name], before[Section.SONGS][name])
        self.assertEqual(after[Section.SONGS][name][Section.TRACKS][ui_testing.LEAD][TrackSetting.CC][FIRST_LANE], A_CC_NUMBER)

    def test_no_later_edit_changes_data_kept_earlier(self):
        # Every kind of object is edited in turn, and what the set kept before each edit is compared with a copy made then.
        edits = [
            lambda: self.document.change_pattern(self.document.pattern(ui_testing.TUNE).set_value, row=Row.VELOCITY, step=0, value=A_VELOCITY),
            lambda: self.document.change_pattern(self.document.pattern(ui_testing.TUNE).set_value, row=Row.VELOCITY, step=0, value=ANOTHER_VELOCITY),
            lambda: self.document.change_pattern(self.document.pattern(ui_testing.TUNE).insert_step, 0),
            lambda: self.document.change_set(self.document.song().get_track(ui_testing.LEAD).set_cc_number, lane=FIRST_LANE, number=A_CC_NUMBER),
            lambda: self.document.change_set(self.document.song().get_track(ui_testing.LEAD).set_cc_number, lane=FIRST_LANE + 1, number=A_CC_NUMBER),
            lambda: self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_reset, register=file_format.REGISTER_NAMES[0], on=True),
            lambda: self.document.change_set(self.document.song().get_scene(FIRST_SCENE).set_reset, register=file_format.REGISTER_NAMES[1], on=True),
            lambda: self.document.change_set(self.document.generator(section=arp_plugin.SECTION, name=ui_testing.UP_ARP).set_setting, name=ArpSetting.OFFSETS, value=list(SOME_OFFSETS)),
            lambda: self.document.set_arp_offset(name=ui_testing.UP_ARP, step=0, offset=AN_OFFSET),
            lambda: self.document.insert_arp_offset(name=ui_testing.UP_ARP, step=0),
            lambda: self.document.set_clip_slot_repeat(index=FIRST_SCENE, track=ui_testing.LEAD, repeat=3),
            lambda: self.document.change_set(self.document.get_setlist().set_title, A_TITLE),
            lambda: self.document.rename_named(section=Section.PATTERNS, old=ui_testing.OTHER, new=NO_SUCH_ITEM),
        ]
        kept = []
        for edit in edits:
            data = self.setlist.kept_data()
            kept.append((data, copy.deepcopy(data)))
            edit()
        self.assertEqual(self.setlist.kept_data(), self.setlist.to_data())
        for place, (data, copied) in enumerate(kept):
            with self.subTest(before_edit=place):
                self.assertEqual(data, copied)


class TestASetGoingBackToDataItKept(unittest.TestCase):

    def test_an_item_whose_data_is_the_same_is_kept_and_one_that_differs_is_read_again(self):
        document = a_song()
        setlist = document.get_setlist()
        earlier = setlist.kept_data()
        tune = setlist.get_pattern(ui_testing.TUNE)
        other = setlist.get_pattern(ui_testing.OTHER)
        song = document.song()
        document.change_pattern(document.pattern(ui_testing.TUNE).set_value, row=Row.VELOCITY, step=0, value=A_VELOCITY)
        later = setlist.kept_data()
        setlist.restore(earlier)
        self.assertEqual(setlist.to_data(), earlier)
        self.assertIs(setlist.get_pattern(ui_testing.OTHER), other)
        self.assertIsNot(setlist.get_pattern(ui_testing.TUNE), tune)
        self.assertIs(setlist.get_song(document.get_current_song_name()), song)
        # And forward again: the pattern is read once more, and the song, which never changed, stays.
        setlist.restore(later)
        self.assertEqual(setlist.to_data(), later)
        self.assertEqual(setlist.get_pattern(ui_testing.TUNE).get_value(row=Row.VELOCITY, step=0), A_VELOCITY)
        self.assertIs(setlist.get_song(document.get_current_song_name()), song)

    def test_a_song_that_changed_is_read_again_whole_and_the_patterns_stay(self):
        document = a_song()
        setlist = document.get_setlist()
        earlier = setlist.kept_data()
        tune = setlist.get_pattern(ui_testing.TUNE)
        song = document.song()
        document.set_clip_slot_repeat(index=FIRST_SCENE, track=ui_testing.LEAD, repeat=3)
        setlist.restore(earlier)
        self.assertEqual(setlist.to_data(), earlier)
        self.assertIsNot(setlist.get_song(document.get_current_song_name()), song)
        self.assertIs(setlist.get_song(document.get_current_song_name()).get_setlist(), setlist)
        self.assertIs(setlist.get_pattern(ui_testing.TUNE), tune)

    def test_added_removed_renamed_and_reordered_items_and_the_sets_settings_go_back(self):
        document = a_song()
        setlist = document.get_setlist()
        earlier = setlist.kept_data()
        document.rename_named(section=Section.PATTERNS, old=ui_testing.OTHER, new=NO_SUCH_ITEM)
        document.add_pattern(name=ui_testing.ONE)
        document.delete_named(section=Section.PATTERNS, name=ui_testing.ONE)
        document.add_pattern(name=ui_testing.LEAD)
        document.move_named(section=Section.PATTERNS, place=len(setlist.get_pattern_names()) - 1, offset=-1)
        document.change_set(document.get_setlist().set_title, A_TITLE)
        document.add_track(NO_SUCH_ITEM)
        changed = setlist.kept_data()
        setlist.restore(earlier)
        self.assertEqual(setlist.to_data(), earlier)
        self.assertEqual(list(setlist.to_data()[Section.PATTERNS]), list(earlier[Section.PATTERNS]))
        setlist.restore(changed)
        self.assertEqual(setlist.to_data(), changed)
        self.assertEqual(list(setlist.to_data()[Section.PATTERNS]), list(changed[Section.PATTERNS]))

    def test_a_section_the_data_leaves_out_is_left_out_again(self):
        setlist = Setlist.from_data(data={})
        unwritten = setlist.kept_data()
        self.assertNotIn(Section.PATTERNS, unwritten)
        filled = example_set(EXAMPLES[0])
        filled.restore(unwritten)
        self.assertEqual(filled.to_data(), unwritten)
        self.assertNotIn(Section.PATTERNS, filled.to_data())
        self.assertEqual(filled.get_pattern_names(), [])

    def test_any_example_restored_to_any_other_is_what_reading_the_other_makes(self):
        # The widest test of both paths: a set going back reads only what differs, and the result is what reading everything gives.
        sets = [example_set(path) for path in EXAMPLES]
        kept = [setlist.kept_data() for setlist in sets]
        written = [setlist.to_data() for setlist in sets]
        for place, path in enumerate(EXAMPLES):
            target = (place + 1) % len(EXAMPLES)
            with self.subTest(path=path, to=EXAMPLES[target]):
                setlist = example_set(path)
                setlist.restore(kept[target])
                setlist.fill_in_defaults()
                self.assertEqual(setlist.to_data(), written[target])
                self.assertEqual(setlist.kept_data(), written[target])
                # And nothing the other set keeps was changed by being read.
                self.assertEqual(kept[target], written[target])

    def test_a_pattern_setting_changed_through_the_pattern_is_kept_right(self):
        document = a_song()
        setlist = document.get_setlist()
        earlier = setlist.kept_data()
        document.change_pattern(document.pattern(ui_testing.TUNE).set_step_size, earlier[Section.PATTERNS][ui_testing.OTHER][PatternSetting.STEP_SIZE])
        self.assertEqual(setlist.kept_data(), setlist.to_data())
        self.assertNotEqual(setlist.kept_data(), earlier)



def check_kept_data(*, test, path):
    """What an example writes and keeps shares nothing with its objects, and an example read from data shares nothing with the data."""
    setlist = example_set(path)
    TestDataAndObjectsShareNothing.check_nothing_shared(test, path=path, setlist=setlist, data=setlist.to_data())
    TestDataAndObjectsShareNothing.check_nothing_shared(test, path=path, setlist=setlist, data=setlist.kept_data())
    data = example_data(path)
    TestDataAndObjectsShareNothing.check_nothing_shared(test, path=path, setlist=Setlist.from_data(data=data), data=data)


if __name__ == '__main__':
    unittest.main()
