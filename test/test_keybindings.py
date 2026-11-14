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
"""The rules of tui/keybindings.py: every page, dialog and component that binds keys has a class of bindings named after it, and nothing in it is left over.

The classes of tui/keybindings.py are where a key is changed, so they have to be the whole truth:
a class for every part of the tracker that binds keys, every binding listed for the F1 dialog,
and no binding, key or key name that nothing uses. test_tui_help_keys.py checks the rest by
touring the tracker: that each bound key comes from its own class and that no key does two things
in one place.
"""

import importlib
import inspect
import pathlib
import pkgutil
import re
import unittest

import llamatron.tui
from llamatron.strings.legends import KeyName
from llamatron.tui import keybindings
from llamatron.tui.key_table import BindsKeys, every_key, place_of
from llamatron.tui.keys import Key, SHIFT_LEFT_RIGHT, SHIFT_UP_DOWN, Steps

SOURCE = pathlib.Path(llamatron.tui.__file__).parent
PYTHON_FILES = '*.py'
FILE_ENCODING = 'utf-8'
# A __main__ module starts the program when it's imported, so it's left out. It defines no classes.
STARTS_THE_PROGRAM = '__main__'
# The module of bindings itself, which names every binding where it's defined.
BINDINGS_FILE = 'keybindings.py'
# The lists every class of bindings has, and the list of the keys that work everywhere, which only Page has.
IN_HELP = 'IN_HELP'
IN_LEGEND = 'IN_LEGEND'
EVERYWHERE = 'EVERYWHERE'
# How many things a binding holds: its keys, its name on screen and what it does.
BINDING_PARTS = 3
# How a page names one of its bindings where it binds it, and how anything else does.
BOUND_THROUGH_KEYS = r'\bKEYS\.{name}\b'
BOUND_BY_CLASS = r'\bkeybindings\.\w+\.{name}\b'
# How the bindings module names a key's name.
NAMED = r'\bKeyName\.{name}\b'
# The keys no binding has, and why: Delete is read as Backspace, Shift with an arrow is never bound, which tests check, and F5 is a key that does nothing, which a test presses.
NEVER_BOUND = (Key.DELETE, *SHIFT_UP_DOWN, *SHIFT_LEFT_RIGHT, Key.F5)


def every_module():
    """Import and return every module of the tracker."""
    found = pkgutil.walk_packages(llamatron.tui.__path__, prefix=f'{llamatron.tui.__name__}.')
    return [importlib.import_module(module.name) for module in found if not module.name.endswith(STARTS_THE_PROGRAM)]


def classes_that_bind_keys():
    """Return every class of the tracker that binds keys, by its name."""
    found = {}
    for module in every_module():
        for _, kind in inspect.getmembers(module, inspect.isclass):
            if issubclass(kind, BindsKeys) and kind is not BindsKeys and kind.__module__ == module.__name__:
                found[kind.__name__] = kind
    return found


def binding_classes():
    """Return every class of tui/keybindings.py, by its name."""
    return {name: kind for name, kind in inspect.getmembers(keybindings, inspect.isclass) if kind.__module__ == keybindings.__name__}


def is_binding(value):
    return isinstance(value, tuple) and not isinstance(value, Steps) and len(value) == BINDING_PARTS


def own_bindings(kind):
    """Return the bindings a class of tui/keybindings.py defines itself, by name."""
    return {name: value for name, value in vars(kind).items() if name.isupper() and is_binding(value)}


def all_bindings(kind):
    """Return every binding of a class of tui/keybindings.py, its own and the ones it inherits."""
    return [value for name, value in inspect.getmembers(kind) if name.isupper() and is_binding(value)]


def is_one_of(*, binding, bindings):
    return place_of(binding=binding, bindings=bindings) is not None


def tracker_source():
    """Return the text of every module of the tracker but the bindings module."""
    return '\n'.join(path.read_text(encoding=FILE_ENCODING) for path in sorted(SOURCE.rglob(PYTHON_FILES)) if path.name != BINDINGS_FILE)


def constants_of(kind):
    return {name: value for name, value in vars(kind).items() if name.isupper()}


class TestKeybindings(unittest.TestCase):

    def test_every_class_that_binds_keys_has_the_bindings_class_of_its_name(self):
        bindings = binding_classes()
        for name, kind in classes_that_bind_keys().items():
            with self.subTest(kind=name):
                self.assertIn(name, bindings)
                self.assertIs(kind.KEYS, bindings[name])

    def test_every_bindings_class_is_named_after_a_class_that_binds_keys(self):
        self.assertEqual(sorted(set(binding_classes()) - set(classes_that_bind_keys())), [])

    def test_a_bindings_class_inherits_as_its_class_does(self):
        binders = classes_that_bind_keys()
        for name, kind in binding_classes().items():
            expected = [base.__name__ for base in binders[name].__mro__[1:] if base.__name__ in binders]
            with self.subTest(kind=name):
                self.assertEqual([base.__name__ for base in kind.__mro__[1:] if base is not object], expected)

    def test_every_binding_is_keys_a_name_and_what_it_does(self):
        for name, kind in binding_classes().items():
            for constant, (keys, shown, what) in own_bindings(kind).items():
                with self.subTest(kind=name, binding=constant):
                    self.assertTrue(every_key(getattr(kind, constant)))
                    self.assertTrue(all(isinstance(key, str) and key for key in every_key(getattr(kind, constant))))
                    self.assertTrue(isinstance(shown, str) and shown)
                    self.assertTrue(isinstance(what, str) and what)

    def test_every_binding_a_class_defines_is_listed_for_help_or_for_the_legend(self):
        for name, kind in binding_classes().items():
            listed = [*kind.IN_HELP, *kind.IN_LEGEND, *getattr(kind, EVERYWHERE, [])]
            for constant, binding in own_bindings(kind).items():
                with self.subTest(kind=name, binding=constant):
                    self.assertTrue(is_one_of(binding=binding, bindings=listed))

    def test_every_listed_binding_is_one_of_the_class(self):
        for name, kind in binding_classes().items():
            for which in (IN_HELP, IN_LEGEND):
                for binding in getattr(kind, which):
                    with self.subTest(kind=name, which=which, binding=binding):
                        self.assertTrue(is_one_of(binding=binding, bindings=all_bindings(kind)))

    def test_no_list_names_a_binding_twice(self):
        for name, kind in binding_classes().items():
            for which in (IN_HELP, IN_LEGEND):
                listed = getattr(kind, which)
                with self.subTest(kind=name, which=which):
                    self.assertEqual(len({id(binding) for binding in listed}), len(listed))

    def test_every_binding_is_bound_somewhere(self):
        source = tracker_source()
        for name, kind in binding_classes().items():
            for constant in own_bindings(kind):
                with self.subTest(kind=name, binding=constant):
                    patterns = (BOUND_THROUGH_KEYS.format(name=constant), BOUND_BY_CLASS.format(name=constant))
                    self.assertTrue(any(re.search(pattern, source) for pattern in patterns))

    def test_every_key_is_bound_or_known_never_to_be(self):
        bound = {key for kind in binding_classes().values() for binding in all_bindings(kind) for key in every_key(binding)}
        for name, key in constants_of(Key).items():
            with self.subTest(key=name):
                self.assertNotEqual(key in bound, key in NEVER_BOUND)

    def test_every_key_name_names_a_binding(self):
        source = (SOURCE / BINDINGS_FILE).read_text(encoding=FILE_ENCODING)
        for name in constants_of(KeyName):
            with self.subTest(name=name):
                self.assertRegex(source, NAMED.format(name=name))


if __name__ == '__main__':
    unittest.main()
