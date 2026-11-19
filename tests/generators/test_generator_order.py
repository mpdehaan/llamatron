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

"""Tests of the order the Generators page lists every generator in, kept in the set as generator_order."""

import os
import tempfile
import unittest

from llamatron.composition import file_format
from llamatron.composition.file_format import GeneratorKind, Section, SetlistSetting
from llamatron.composition.setlist import Setlist
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
    data = as_setlist({Section.ARPS: {ARP: {}, OTHER_ARP: {}}, Section.AUTO_RATCHETS: {RATCHET: {'counts': [2]}}})
    if order is not None:
        data[SetlistSetting.GENERATOR_ORDER] = order
    return Setlist.from_data(data=data)


class TestGeneratorOrder(unittest.TestCase):

    def test_with_no_order_each_kind_comes_in_its_own_order(self):
        self.assertEqual(a_set().ordered_generators(), [(GeneratorKind.ARP, ARP), (GeneratorKind.ARP, OTHER_ARP), (GeneratorKind.AUTO_RATCHET, RATCHET)])

    def test_a_kept_order_comes_first_and_anything_it_leaves_out_follows_and_nonsense_is_dropped(self):
        setlist = a_set(order=[{GeneratorKind.AUTO_RATCHET: RATCHET}, {GeneratorKind.ARP: UNKNOWN}, 'nonsense', {'nokind': ARP}])
        self.assertEqual(setlist.ordered_generators(), [(GeneratorKind.AUTO_RATCHET, RATCHET), (GeneratorKind.ARP, ARP), (GeneratorKind.ARP, OTHER_ARP)])

    def test_moving_keeps_the_order_through_saving_and_stops_at_the_ends(self):
        setlist = a_set()
        self.assertTrue(setlist.move_generator(place=2, offset=-2))
        self.assertFalse(setlist.move_generator(place=0, offset=-1))
        again = Setlist.from_data(data=setlist.to_data())
        self.assertEqual(again.ordered_generators()[0], (GeneratorKind.AUTO_RATCHET, RATCHET))

    def test_a_rename_keeps_its_place_and_a_copy_comes_straight_after_what_it_copies(self):
        setlist = a_set()
        setlist.move_generator(place=2, offset=-2)
        setlist.rename_item(section=Section.ARPS, old=ARP, new=RENAMED)
        self.assertEqual(setlist.ordered_generators()[1], (GeneratorKind.ARP, RENAMED))
        setlist.copy_item(section=Section.AUTO_RATCHETS, name=RATCHET, new=COPIED)
        self.assertEqual(setlist.ordered_generators()[1], (GeneratorKind.AUTO_RATCHET, COPIED))


class TestOpenGeneratorTypes(unittest.TestCase):
    """The types of generator the Generators page shows open, which the set keeps and its file holds."""

    def test_every_type_is_closed_until_opened_and_closes_again(self):
        setlist = a_set()
        self.assertEqual(setlist.get_open_generator_types(), [])
        setlist.show_generator_type(kind=GeneratorKind.AUTO_RATCHET, opened=True)
        setlist.show_generator_type(kind=GeneratorKind.ARP, opened=True)
        self.assertEqual(setlist.get_open_generator_types(), [GeneratorKind.ARP, GeneratorKind.AUTO_RATCHET])
        setlist.show_generator_type(kind=GeneratorKind.ARP, opened=False)
        self.assertFalse(setlist.is_generator_type_open(GeneratorKind.ARP))
        self.assertTrue(setlist.is_generator_type_open(GeneratorKind.AUTO_RATCHET))

    def test_the_open_types_are_no_part_of_the_sets_data(self):
        setlist = a_set()
        before = setlist.to_data()
        setlist.show_generator_type(kind=GeneratorKind.ARP, opened=True)
        self.assertEqual(setlist.to_data(), before)
        self.assertNotIn(file_format.OPEN_GENERATOR_TYPES, setlist.to_data())

    def test_a_file_keeps_the_open_types_and_forgets_a_type_with_no_generator(self):
        data = a_set().to_data()
        data[file_format.OPEN_GENERATOR_TYPES] = [GeneratorKind.ARP, GeneratorKind.DRIFT, UNKNOWN]
        self.assertEqual(Setlist.from_data(data=data).get_open_generator_types(), [GeneratorKind.ARP])

    def test_a_file_holding_anything_else_there_still_opens(self):
        for held in (A_NUMBER, [A_NUMBER, GeneratorKind.ARP], {GeneratorKind.ARP: True}):
            data = a_set().to_data()
            data[file_format.OPEN_GENERATOR_TYPES] = held
            self.assertIn(Setlist.from_data(data=data).get_open_generator_types(), ([], [GeneratorKind.ARP]))

    def test_an_open_type_is_written_to_the_file_and_read_back(self):
        setlist = a_set()
        setlist.show_generator_type(kind=GeneratorKind.AUTO_RATCHET, opened=True)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, SAVED_FILE)
            setlist.write_file(path)
            self.assertEqual(Setlist.read_file(path).get_open_generator_types(), [GeneratorKind.AUTO_RATCHET])
