# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of the order the Generators page lists every generator in, kept in the set as generator_order."""

import os
import tempfile
import unittest

from llamatron.engine.generators import arp as arp_plugin, drift as drift_plugin, timing as timing_plugin
from llamatron.interface.tracker.page_memory import PageMemory
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import SetlistSetting
from tests.support.rendering import as_setlist

ARP = 'up'
OTHER_ARP = 'down'
RATCHET = 'rolls'
RENAMED = 'climb'
COPIED = 'up 2'
UNKNOWN = 'nothing'
A_NUMBER = 7
SAVED_FILE = 'saved.yml'


def a_set(*, order=None):
    data = as_setlist({arp_plugin.SECTION: {ARP: {}, OTHER_ARP: {}}, timing_plugin.SECTION: {RATCHET: {}}})
    if order is not None:
        data[SetlistSetting.GENERATOR_ORDER] = order
    return Setlist.from_data(data=data)


class TestGeneratorOrder(unittest.TestCase):

    def test_with_no_order_each_kind_comes_in_its_own_order(self):
        self.assertEqual(a_set().ordered_generators(), [(arp_plugin.NAME, ARP), (arp_plugin.NAME, OTHER_ARP), (timing_plugin.NAME, RATCHET)])

    def test_a_kept_order_comes_first_and_anything_it_leaves_out_follows_and_nonsense_is_dropped(self):
        setlist = a_set(order=[{timing_plugin.NAME: RATCHET}, {arp_plugin.NAME: UNKNOWN}, 'nonsense', {'nokind': ARP}])
        self.assertEqual(setlist.ordered_generators(), [(timing_plugin.NAME, RATCHET), (arp_plugin.NAME, ARP), (arp_plugin.NAME, OTHER_ARP)])

    def test_moving_keeps_the_order_through_saving_and_stops_at_the_ends(self):
        setlist = a_set()
        self.assertTrue(setlist.move_generator(place=2, offset=-2))
        self.assertFalse(setlist.move_generator(place=0, offset=-1))
        again = Setlist.from_data(data=setlist.to_data())
        self.assertEqual(again.ordered_generators()[0], (timing_plugin.NAME, RATCHET))

    def test_a_rename_keeps_its_place_and_a_copy_comes_straight_after_what_it_copies(self):
        setlist = a_set()
        setlist.move_generator(place=2, offset=-2)
        setlist.rename_item(section=arp_plugin.SECTION, old=ARP, new=RENAMED)
        self.assertEqual(setlist.ordered_generators()[1], (arp_plugin.NAME, RENAMED))
        setlist.copy_item(section=timing_plugin.SECTION, name=RATCHET, new=COPIED)
        self.assertEqual(setlist.ordered_generators()[1], (timing_plugin.NAME, COPIED))


class TestOpenGeneratorTypes(unittest.TestCase):
    """The types of generator the Generators page shows open, which the set keeps and its file holds."""

    def test_every_type_is_closed_until_opened_and_closes_again(self):
        setlist = a_set()
        memory = PageMemory(setlist.get_page_record())
        self.assertEqual(memory.open_generator_types(setlist), [])
        memory.show_generator_type(kind=timing_plugin.NAME, opened=True)
        memory.show_generator_type(kind=arp_plugin.NAME, opened=True)
        self.assertEqual(memory.open_generator_types(setlist), [arp_plugin.NAME, timing_plugin.NAME])
        memory.show_generator_type(kind=arp_plugin.NAME, opened=False)
        self.assertFalse(memory.is_generator_type_open(arp_plugin.NAME))
        self.assertTrue(memory.is_generator_type_open(timing_plugin.NAME))

    def test_the_open_types_are_no_part_of_the_sets_data(self):
        setlist = a_set()
        before = setlist.to_data()
        memory = PageMemory(setlist.get_page_record())
        memory.show_generator_type(kind=arp_plugin.NAME, opened=True)
        setlist.set_page_record(memory.record(setlist))
        self.assertEqual(setlist.to_data(), before)
        self.assertNotIn(file_format.OPEN_GENERATOR_TYPES, setlist.to_data())

    def open_on_opening(self, data):
        setlist = Setlist.from_data(data=data)
        return PageMemory(setlist.get_page_record()).open_generator_types(setlist)

    def test_a_file_keeps_the_open_types_and_forgets_a_type_with_no_generator(self):
        data = a_set().to_data()
        data[file_format.OPEN_GENERATOR_TYPES] = [arp_plugin.NAME, drift_plugin.NAME, UNKNOWN]
        self.assertEqual(self.open_on_opening(data), [arp_plugin.NAME])

    def test_a_file_holding_anything_else_there_still_opens(self):
        for held in (A_NUMBER, [A_NUMBER, arp_plugin.NAME], {arp_plugin.NAME: True}):
            data = a_set().to_data()
            data[file_format.OPEN_GENERATOR_TYPES] = held
            self.assertIn(self.open_on_opening(data), ([], [arp_plugin.NAME]))

    def test_an_open_type_is_written_to_the_file_and_read_back(self):
        setlist = a_set()
        memory = PageMemory(setlist.get_page_record())
        memory.show_generator_type(kind=timing_plugin.NAME, opened=True)
        setlist.set_page_record(memory.record(setlist))
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, SAVED_FILE)
            setlist.write_file(path)
            read = Setlist.read_file(path)
        self.assertEqual(PageMemory(read.get_page_record()).open_generator_types(read), [timing_plugin.NAME])
