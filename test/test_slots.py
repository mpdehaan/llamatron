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

"""Every class declares its data members with __slots__, so none can be added by mistake.

With __slots__, a class lists exactly what its objects hold, and assigning anything else, like a
misspelled name, raises an error. Each class in a hierarchy needs its own, even if empty, or its
objects quietly get a dictionary again.

The exceptions are classes that only hold constants, which are never made into objects, and
subclasses of classes from outside llamatron, such as Textual's screens, enums and exceptions,
whose bases already give every object a dictionary. A base from outside that declares its own
empty slots, like abc.ABC, doesn't excuse a class.
"""

import importlib
import inspect
import pkgutil
import unittest

import llamatron

PACKAGE = 'llamatron'
# A __main__ module starts the program when it's imported, so it's left out. It defines no classes.
STARTS_THE_PROGRAM = '__main__'


def every_module():
    """Import and return every module in llamatron."""
    modules = [llamatron]
    for found in pkgutil.walk_packages(llamatron.__path__, prefix=f'{PACKAGE}.'):
        if not found.name.endswith(STARTS_THE_PROGRAM):
            modules.append(importlib.import_module(found.name))
    return modules


def classes_defined_in(module):
    return [kind for _, kind in inspect.getmembers(module, inspect.isclass) if kind.__module__ == module.__name__]


def extends_an_outside_class(kind):
    """Return whether a class builds on a class from outside llamatron that gives its objects a dictionary anyway.

    A base like abc.ABC declares empty slots itself, so classes built on it still need theirs.
    """
    return any(
        base is not object and not base.__module__.startswith(PACKAGE) and '__slots__' not in vars(base)
        for base in kind.__mro__[1:]
    )


def only_holds_constants(kind):
    """Return whether a class is just a group of named constants, like Row, which nothing makes objects of.

    A class with nothing of its own that builds only on such classes is one too, like the key
    bindings of a page that has its base page's keys and no more.
    """
    own = [name for name in vars(kind) if not name.startswith('__')]
    if own:
        return all(name.isupper() for name in own)
    bases = [base for base in kind.__bases__ if base is not object]
    return bool(bases) and all(only_holds_constants(base) for base in bases)


def needs_slots(kind):
    return not extends_an_outside_class(kind) and not only_holds_constants(kind)


class Constants:
    """A group of named constants."""

    FIRST = 1


class MoreConstants(Constants):
    """A group of constants built on another."""

    SECOND = 2


class SameConstants(MoreConstants):
    """A class with nothing of its own, built on a group of constants."""


class Empty:
    """A class with nothing in it, which objects could be made of."""

    __slots__ = ()


class ConstantsWithMethod:
    """A class with a constant and a method, which objects are made of."""

    __slots__ = ()

    FIRST = 1

    def first(self):
        return self.FIRST


class EmptyOnMethod(ConstantsWithMethod):
    """A class with nothing of its own, built on a class that objects are made of."""

    __slots__ = ()


class TestSlots(unittest.TestCase):

    def test_every_class_declares_its_slots(self):
        for module in every_module():
            for kind in classes_defined_in(module):
                if needs_slots(kind):
                    with self.subTest(module=module.__name__, kind=kind.__name__):
                        self.assertIn('__slots__', vars(kind))

    def test_a_class_of_constants_and_an_empty_class_built_on_one_need_no_slots(self):
        self.assertFalse(needs_slots(Constants))
        self.assertFalse(needs_slots(MoreConstants))
        self.assertFalse(needs_slots(SameConstants))

    def test_an_empty_class_and_a_class_with_a_method_need_slots(self):
        self.assertTrue(needs_slots(Empty))
        self.assertTrue(needs_slots(ConstantsWithMethod))
        self.assertTrue(needs_slots(EmptyOnMethod))

    def test_an_object_cannot_be_given_a_new_member(self):
        from llamatron.composition.track import Track
        track = Track()
        with self.assertRaises(AttributeError):
            track._drumm = True


if __name__ == '__main__':
    unittest.main()
