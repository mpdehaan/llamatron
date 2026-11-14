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
"""internal_tools/show_keys.py prints the key bindings of tui/keybindings.py: every class's, one class's, or every binding that has one key."""

import contextlib
import importlib.util
import io
import pathlib
import unittest

from llamatron.strings.legends import KeyName, What
from llamatron.tui import keybindings
from llamatron.tui.key_table import first_key

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / 'internal_tools' / 'show_keys.py'
MODULE_NAME = 'show_keys'
A_CLASS = keybindings.PianoRoll.__name__
ANOTHER_CLASS = keybindings.ArrangePage.__name__
NOT_A_CLASS = 'NoSuchPage'
SUCCESS = 0
FAILURE = 1


def load_script():
    """Load the tool as a module, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestShowKeys(unittest.TestCase):

    def setUp(self):
        self.tool = load_script()

    def shown(self, arguments, *, expected=SUCCESS):
        """Run the tool and return the lines it printed, checking what it exits with."""
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(self.tool.main(arguments), expected)
        return output.getvalue().splitlines()

    def line_of(self, *, lines, constant):
        return next(line for line in lines if line.split()[:1] == [constant])

    def test_every_class_is_shown_with_every_binding_it_lists(self):
        lines = self.shown([])
        for name, kind in self.tool.binding_classes().items():
            with self.subTest(kind=name):
                self.assertTrue(any(line.split()[:1] == [name] for line in lines))
        listed = sum(len(self.tool.bindings_of(kind)) for kind in self.tool.binding_classes().values())
        self.assertEqual(len([line for line in lines if line.startswith(' ')]), listed)

    def test_one_class_is_shown_alone_with_its_keys_names_and_what_they_do(self):
        lines = self.shown([A_CLASS])
        self.assertEqual(lines[0].split()[0], A_CLASS)
        self.assertFalse(any(line.split()[:1] == [ANOTHER_CLASS] for line in lines))
        _, shown, what = keybindings.PianoRoll.ERASE
        line = self.line_of(lines=lines, constant=self.tool.name_of(kind=keybindings.PianoRoll, binding=keybindings.PianoRoll.ERASE))
        for part in (first_key(keybindings.PianoRoll.ERASE), shown, what):
            self.assertIn(part, line)

    def test_a_binding_the_legend_leaves_out_is_marked_and_one_it_shows_is_not(self):
        lines = self.shown([A_CLASS])
        kind = keybindings.PianoRoll
        self.assertTrue(self.line_of(lines=lines, constant=self.tool.name_of(kind=kind, binding=kind.KNIFE)).endswith(self.tool.F1_ONLY))
        self.assertFalse(self.line_of(lines=lines, constant=self.tool.name_of(kind=kind, binding=kind.PLACE)).endswith(self.tool.F1_ONLY))

    def test_a_page_lists_the_keys_that_work_everywhere_first(self):
        lines = self.shown([ANOTHER_CLASS])
        everywhere = [self.tool.name_of(kind=keybindings.ArrangePage, binding=binding) for binding in keybindings.Page.EVERYWHERE]
        self.assertEqual([line.split()[0] for line in lines[1:len(everywhere) + 1]], everywhere)
        self.assertTrue(all(line.endswith(self.tool.EVERYWHERE) for line in lines[1:len(everywhere) + 1]))

    def test_a_class_that_binds_two_meanings_to_the_same_keys_shows_both(self):
        lines = self.shown([ANOTHER_CLASS])
        kind = keybindings.ArrangePage
        self.assertEqual(kind.MOVE, kind.INSET_MOVE)
        names = [line.split()[0] for line in lines if line.startswith(' ')]
        self.assertIn(self.tool.name_of(kind=kind, binding=kind.MOVE), names)
        self.assertIn(self.tool.name_of(kind=kind, binding=kind.INSET_MOVE), names)
        self.assertNotEqual(self.tool.name_of(kind=kind, binding=kind.MOVE), self.tool.name_of(kind=kind, binding=kind.INSET_MOVE))

    def test_a_key_lists_every_binding_that_has_it_once_under_the_class_that_defines_it(self):
        key = first_key(keybindings.ListPage.SORT)
        lines = self.shown([self.tool.KEY_FLAG, key.upper()])
        owners = [line.split()[0] for line in lines]
        self.assertIn(self.tool.OWNER.format(kind=keybindings.ListPage.__name__, constant=self.tool.name_of(kind=keybindings.ListPage, binding=keybindings.ListPage.SORT)), owners)
        self.assertFalse(any(owner.startswith(keybindings.PatternsPage.__name__) for owner in owners))
        self.assertEqual(len(owners), len(set(owners)))
        self.assertTrue(any(KeyName.S in line and What.SORT in line for line in lines))

    def test_a_key_nothing_has_says_so(self):
        self.assertEqual(self.shown([self.tool.KEY_FLAG, NOT_A_CLASS]), [self.tool.MSG_NOTHING_HAS_KEY.format(key=NOT_A_CLASS.lower())])

    def test_an_unknown_class_fails_and_names_the_classes(self):
        lines = self.shown([NOT_A_CLASS], expected=FAILURE)
        self.assertEqual(len(lines), 1)
        self.assertIn(NOT_A_CLASS, lines[0])
        self.assertIn(A_CLASS, lines[0])


if __name__ == '__main__':
    unittest.main()
