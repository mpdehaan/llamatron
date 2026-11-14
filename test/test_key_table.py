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

"""How a page binds the keys its class in tui/keybindings.py lists: a plain key, a key that passes its own name, keys that step one way or the other, and the order and the legend the class's lists give."""

import unittest

from llamatron.strings.legends import KeyName, What
from llamatron.tui import keybindings
from llamatron.tui.key_table import STEP_BACK, STEP_FORWARD, BindsKeys, bound, cursor_moved, every_key, first_key, key_event, keys_of, place_of, pressed_key
from llamatron.tui.keys import ARROWS_LEFT_RIGHT, Key, LESS_KEYS, MORE_KEYS, Steps

# How many places a cursor moves among in these tests, the first and last of them, and one in the middle with the places either side of it.
PLACES = 4
FIRST_PLACE = 0
LAST_PLACE = PLACES - 1
MIDDLE_PLACE = 1
PLACE_BEFORE_MIDDLE = 0
PLACE_AFTER_MIDDLE = 2
# What a page says in place of a binding's own name and words, and the keys it binds in place of the binding's own.
OTHER_NAME = '1-5'
OTHER_WHAT = What.CHOOSE
OTHER_KEYS = (Key.DIGIT_1, Key.DIGIT_2)


class Bindings:
    """A class of bindings like those of tui/keybindings.py: two bindings that hold the same keys and words, one binding the legend leaves out, and a part's bindings in an order of their own."""

    RENAME = (Key.N, KeyName.N, What.RENAME)
    MOVE = (ARROWS_LEFT_RIGHT, KeyName.LEFT_RIGHT, What.MOVE)
    ADJUST = (Steps(back=LESS_KEYS, forward=MORE_KEYS), KeyName.BRACKETS, What.MORE)
    ENDS = (Steps(back=(Key.HOME,), forward=(Key.END,)), KeyName.HOME_END, What.ENDS)
    ADJUST_AGAIN = (Steps(back=LESS_KEYS, forward=MORE_KEYS), KeyName.BRACKETS, What.MORE)
    IN_HELP = [MOVE, ADJUST, ENDS, RENAME, ADJUST_AGAIN]
    IN_LEGEND = [MOVE, ADJUST, RENAME, ADJUST_AGAIN]


class PartBindings:
    """The bindings of a part of a page, which the page lists among its own."""

    COPY = (Key.C, KeyName.C, What.COPY)
    SORT = (Key.S, KeyName.S, What.SORT)
    IN_HELP = [COPY, SORT]
    IN_LEGEND = IN_HELP


class Recorder(BindsKeys):
    """Something that binds the keys of Bindings, and remembers what a binding's action was called with."""

    __slots__ = ('calls',)

    KEYS = Bindings

    def __init__(self):
        self.calls = []

    def called(self, *arguments):
        self.calls.append(arguments)


class Part(BindsKeys):
    """A part of a page, which binds the keys of PartBindings."""

    __slots__ = ()

    KEYS = PartBindings

    def nothing(self):
        pass


class TestKeyTable(unittest.TestCase):

    def setUp(self):
        self.recorder = Recorder()

    def bind(self, binding, **named):
        return self.recorder.bind(binding, action=self.recorder.called, **named)

    def test_a_plain_key_calls_its_action_with_nothing(self):
        binding = self.bind(Bindings.RENAME)
        binding.press(first_key(Bindings.RENAME))
        self.assertEqual(self.recorder.calls, [()])
        self.assertEqual((binding.keys, binding.label, binding.what), ((Key.N,), KeyName.N, What.RENAME))

    def test_a_key_that_wants_its_name_is_passed_it(self):
        binding = self.bind(Bindings.MOVE, wants_key=True)
        binding.press(Key.RIGHT)
        self.assertEqual(self.recorder.calls, [(Key.RIGHT,)])

    def test_one_key_or_several_are_a_tuple_of_names(self):
        self.assertEqual(keys_of(Key.TAB), (Key.TAB,))
        self.assertEqual(keys_of([Key.HOME, Key.END]), (Key.HOME, Key.END))
        self.assertEqual(keys_of(Steps(back=LESS_KEYS, forward=MORE_KEYS)), (*LESS_KEYS, *MORE_KEYS))

    def test_a_binding_says_every_key_it_has_and_its_first(self):
        self.assertEqual(every_key(Bindings.RENAME), (Key.N,))
        self.assertEqual(every_key(Bindings.MOVE), ARROWS_LEFT_RIGHT)
        self.assertEqual(every_key(Bindings.ENDS), (Key.HOME, Key.END))
        self.assertEqual(first_key(Bindings.MOVE), ARROWS_LEFT_RIGHT[0])

    def test_stepping_keys_pass_their_direction_and_never_the_key(self):
        binding = self.bind(Bindings.ADJUST)
        self.assertEqual(binding.keys, (*LESS_KEYS, *MORE_KEYS))
        for name in (*LESS_KEYS, *MORE_KEYS):
            binding.press(name)
        self.assertEqual(self.recorder.calls, [(STEP_BACK,)] * len(LESS_KEYS) + [(STEP_FORWARD,)] * len(MORE_KEYS))

    def test_stepping_keys_take_one_key_each_way_too(self):
        binding = self.bind(Bindings.ENDS)
        self.assertEqual(binding.keys, (Key.HOME, Key.END))
        binding.press(Key.END)
        binding.press(Key.HOME)
        self.assertEqual(self.recorder.calls, [(STEP_FORWARD,), (STEP_BACK,)])

    def test_a_binding_shows_the_name_its_class_gives_it(self):
        self.assertEqual(self.bind(Bindings.ADJUST).shown_label(), KeyName.BRACKETS)

    def test_the_legend_shows_a_binding_only_when_the_class_lists_it(self):
        self.assertTrue(self.bind(Bindings.MOVE).shown)
        self.assertFalse(self.bind(Bindings.ENDS).shown)

    def test_a_page_can_say_its_own_keys_name_and_words(self):
        binding = self.bind(Bindings.RENAME, keys=OTHER_KEYS, name=OTHER_NAME, what=OTHER_WHAT)
        self.assertEqual((binding.keys, binding.label, binding.what), (OTHER_KEYS, OTHER_NAME, OTHER_WHAT))
        self.assertIs(binding.binding, Bindings.RENAME)

    def test_bindings_come_in_the_order_the_class_lists_them(self):
        bindings = [self.bind(Bindings.RENAME), self.bind(Bindings.ENDS), self.bind(Bindings.MOVE)]
        self.assertEqual([item.binding for item in self.recorder.in_order(bindings)], [Bindings.MOVE, Bindings.ENDS, Bindings.RENAME])

    def test_two_bindings_that_hold_the_same_keep_their_own_places(self):
        self.assertEqual(Bindings.ADJUST, Bindings.ADJUST_AGAIN)
        self.assertEqual(place_of(binding=Bindings.ADJUST, bindings=Bindings.IN_HELP), Bindings.IN_HELP.index(Bindings.ADJUST))
        self.assertEqual(place_of(binding=Bindings.ADJUST_AGAIN, bindings=Bindings.IN_HELP), len(Bindings.IN_HELP) - 1)
        bindings = [self.bind(Bindings.ADJUST_AGAIN), self.bind(Bindings.RENAME), self.bind(Bindings.ADJUST)]
        ordered = self.recorder.in_order(bindings)
        self.assertIs(ordered[0].binding, Bindings.ADJUST)
        self.assertIs(ordered[-1].binding, Bindings.ADJUST_AGAIN)

    def test_a_binding_a_list_leaves_out_has_no_place_in_it(self):
        self.assertIsNone(place_of(binding=Bindings.ENDS, bindings=Bindings.IN_LEGEND))

    def test_a_parts_bindings_stay_where_the_page_put_them(self):
        part = Part()
        sort = bound(of=PartBindings, binding=PartBindings.SORT, action=part.nothing)
        copy = bound(of=PartBindings, binding=PartBindings.COPY, action=part.nothing)
        bindings = [self.bind(Bindings.RENAME), self.bind(Bindings.MOVE), sort, copy, self.bind(Bindings.ENDS), self.bind(Bindings.ADJUST)]
        ordered = [item.binding for item in self.recorder.in_order(bindings)]
        self.assertEqual(ordered, [Bindings.MOVE, Bindings.RENAME, PartBindings.SORT, PartBindings.COPY, Bindings.ADJUST, Bindings.ENDS])

    def test_a_cursor_moves_back_and_forward_and_stops_at_both_ends(self):
        for name in (Key.UP, Key.LEFT):
            self.assertEqual(cursor_moved(place=MIDDLE_PLACE, name=name, count=PLACES), PLACE_BEFORE_MIDDLE)
            self.assertEqual(cursor_moved(place=FIRST_PLACE, name=name, count=PLACES), FIRST_PLACE)
        for name in (Key.DOWN, Key.RIGHT):
            self.assertEqual(cursor_moved(place=MIDDLE_PLACE, name=name, count=PLACES), PLACE_AFTER_MIDDLE)
            self.assertEqual(cursor_moved(place=LAST_PLACE, name=name, count=PLACES), LAST_PLACE)

    def test_every_key_that_works_everywhere_is_read_as_itself_when_a_terminal_sends_it(self):
        # A control key arrives with its control code as its character, which is not printable, so it is read by its name or not at all: Ctrl+T was once read as nothing.
        for binding in keybindings.Page.EVERYWHERE:
            for key in every_key(binding):
                self.assertEqual(pressed_key(key_event(key)), key)
