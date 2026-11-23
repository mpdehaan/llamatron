# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Revisions: every stored object's revision moves with every change, and no two revisions are the same.

The rule here is about the code's shape: in every class of model/ that carries a revision,
a method that changes the object is written under @notes_change, and the constructor calls
note_change(). A method changes the object when it assigns to one of the object's members, or to
a place inside one, or calls a method that changes a list, dictionary or set in place on one. A
method that changes the object only by calling its other methods needs no mark, since those
carry theirs. The one member left out is the data an object keeps of itself (LlamaData's kept_data),
which is worked out from the object and is no part of what the object stores: filling it or
dropping it changes nothing, and moving the revision for it would drop it again. The tracker's
tests are the second guard: every memory checks its answers while
they run (caching/memory.py), which finds a change this rule can't see.
"""

import ast
import importlib
import inspect
import pkgutil
import textwrap
import unittest

from llamatron.caching.revised import ChangeMark, latest_revision, notes_change, Revised
import llamatron.model
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.groove import Groove
from llamatron.model.objects.named_scale import NamedScale, scale_type_name
from llamatron.model.objects.pattern import Pattern
from llamatron.model.schema.file_format import Row
from llamatron.model.values.note import NoteName
from llamatron.model.values.scale import ScaleType

CONSTRUCTOR = '__init__'
DECORATOR = notes_change.__name__
NOTE_CHANGE_CALL = 'self.note_change()'
SELF = 'self'
# The members that are no part of an object: the data it keeps of itself, worked out from it, and the record of how the pages
# show a set, which its file holds and nothing undoes or remembers an answer from (interface/tracker/page_memory.py).
NOT_PART_OF_IT = ('_cached', '_page_record')
# The methods that change a list, a dictionary or a set in place.
IN_PLACE_METHODS = frozenset({'append', 'insert', 'pop', 'remove', 'clear', 'update', 'sort', 'reverse', 'extend', 'setdefault', 'popitem', 'add', 'discard'})
MSG_UNMARKED = '{kind}.{method} changes the object and is not written under @notes_change'
MSG_SILENT_CONSTRUCTOR = "{kind}'s constructor does not call note_change()"
STEPS = 4
NOT_A_ROOT = 'H'

SAMPLE = '''
class Sample:
    def assigns(self, value):
        self._value = value
    def assigns_inside(self, value):
        self._rows[0][1] = value
    def adds_to(self, value):
        self._count += value
    def deletes(self):
        del self._rows[0]
    def appends(self, value):
        self._rows.append(value)
    def sorts_inside(self):
        self._settings[0].sort()
    def reads(self):
        return self._value
    def changes_a_copy(self):
        rows = list(self._rows)
        rows.append(1)
        return rows
    def calls_another(self, value):
        self.assigns(value)
    def keeps_its_data(self):
        self._cached = self.reads()
'''
SAMPLE_CHANGERS = ['assigns', 'assigns_inside', 'adds_to', 'deletes', 'appends', 'sorts_inside']
SAMPLE_NOT_CHANGERS = ['reads', 'changes_a_copy', 'calls_another', 'keeps_its_data']


def is_on_self(node):
    """Return whether an attribute or a subscript is a member of self that the object stores, or a place inside one."""
    member = None
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        member = node.attr if isinstance(node, ast.Attribute) else member
        node = node.value
    return isinstance(node, ast.Name) and node.id == SELF and member not in NOT_PART_OF_IT


def assigned_targets(node):
    """Return what a statement assigns to or deletes, each name of a tuple on its own."""
    if isinstance(node, (ast.Assign, ast.Delete)):
        targets = node.targets
    elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
        targets = [node.target]
    else:
        targets = []
    return [part for target in targets for part in (target.elts if isinstance(target, ast.Tuple) else [target])]


def changes_in_place(node):
    """Return whether a node is a call that changes one of self's lists, dictionaries or sets in place."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in IN_PLACE_METHODS):
        return False
    return isinstance(node.func.value, (ast.Attribute, ast.Subscript)) and is_on_self(node.func.value)


def changes_the_object(function):
    """Return whether a method changes the object it's called on, as far as its own lines show."""
    for node in ast.walk(function):
        if any(isinstance(target, (ast.Attribute, ast.Subscript)) and is_on_self(target) for target in assigned_targets(node)):
            return True
        if changes_in_place(node):
            return True
    return False


def methods_of(source):
    """Return the methods defined in a class's source."""
    tree = ast.parse(textwrap.dedent(source))
    return [node for node in tree.body[0].body if isinstance(node, ast.FunctionDef)]


def is_marked(function):
    """Return whether a method is written under @notes_change."""
    return any(isinstance(decorator, ast.Name) and decorator.id == DECORATOR for decorator in function.decorator_list)


def notes_its_making(function):
    """Return whether a constructor calls note_change() itself."""
    return any(isinstance(node, ast.Expr) and ast.unparse(node) == NOTE_CHANGE_CALL for node in ast.walk(function))


def revised_classes():
    """Return every class of the Model that carries a revision."""
    found = []
    for module_info in pkgutil.walk_packages(llamatron.model.__path__, llamatron.model.__name__ + '.'):
        module = importlib.import_module(module_info.name)
        for _, kind in inspect.getmembers(module, inspect.isclass):
            if issubclass(kind, Revised) and kind.__module__ == module.__name__:
                found.append(kind)
    return found


class TestRevisions(unittest.TestCase):

    def test_no_two_things_share_a_revision_and_a_change_takes_a_new_one(self):
        first = ChangeMark()
        second = ChangeMark()
        self.assertNotEqual(first.get_revision(), second.get_revision())
        before = first.get_revision()
        first.note_change()
        self.assertGreater(first.get_revision(), before)
        self.assertNotEqual(first.get_revision(), second.get_revision())
        self.assertEqual(latest_revision(), first.get_revision())

    def test_a_copy_has_a_revision_of_its_own(self):
        pattern = Pattern(steps=STEPS, rows={})
        self.assertNotEqual(pattern.copy().get_revision(), pattern.get_revision())

    def test_a_setter_moves_its_objects_revision_and_no_other(self):
        pattern = Pattern(steps=STEPS, rows={})
        other = Pattern(steps=STEPS, rows={})
        before = pattern.get_revision()
        untouched = other.get_revision()
        pattern.set_value(row=Row.DEGREE, step=0, value=1)
        self.assertGreater(pattern.get_revision(), before)
        self.assertEqual(other.get_revision(), untouched)

    def test_reading_moves_nothing(self):
        pattern = Pattern(steps=STEPS, rows={})
        before = pattern.get_revision()
        pattern.get_steps()
        pattern.to_data()
        pattern.get_value(row=Row.DEGREE, step=0)
        self.assertEqual(pattern.get_revision(), before)

    def test_a_setter_that_refuses_its_value_still_raises(self):
        scale = NamedScale(root=NoteName.C, kind=scale_type_name(ScaleType.MAJOR))
        with self.assertRaises(InvalidValue):
            scale.set_root(NOT_A_ROOT)
        self.assertEqual(scale.get_root(), NoteName.C)

    def test_a_marked_method_keeps_its_name_its_words_and_what_it_returns(self):
        self.assertEqual(Groove.set_cell.__name__, 'set_cell')
        self.assertEqual(Pattern.set_value.__doc__, Pattern.set_value.__wrapped__.__doc__)
        pattern = Pattern(steps=STEPS, rows={Row.DEGREE: [1, 2, 3, 4]})
        # pivot_around returns where the cursor's step went, through the marked method that rearranges the steps.
        self.assertEqual(pattern.pivot_around(0), STEPS - 1)


class TestWhatCountsAsAChange(unittest.TestCase):
    """The rule's own detector, on a class written out here: both what it must find and what it must leave alone."""

    def test_assigning_deleting_and_changing_in_place_are_changes(self):
        found = [method.name for method in methods_of(SAMPLE) if changes_the_object(method)]
        self.assertEqual(found, SAMPLE_CHANGERS)

    def test_reading_copying_calling_another_method_and_keeping_the_objects_own_data_are_not(self):
        left_alone = [method.name for method in methods_of(SAMPLE) if not changes_the_object(method)]
        self.assertEqual(left_alone, SAMPLE_NOT_CHANGERS)


class TestEveryChangeIsMarked(unittest.TestCase):

    def test_there_are_classes_to_check(self):
        names = {kind.__name__ for kind in revised_classes()}
        self.assertTrue({'Pattern', 'Scene', 'Song', 'Setlist', 'NamedItems', 'ClipSlot', 'Track', 'Chain', 'Groove', 'NamedScale', 'Draw'} <= names, names)

    def test_every_method_that_changes_a_stored_object_is_marked_and_every_constructor_notes_its_making(self):
        for kind in revised_classes():
            for method in methods_of(inspect.getsource(kind)):
                with self.subTest(kind=kind.__name__, method=method.name):
                    if method.name == CONSTRUCTOR:
                        self.assertTrue(notes_its_making(method), MSG_SILENT_CONSTRUCTOR.format(kind=kind.__name__))
                    elif changes_the_object(method):
                        self.assertTrue(is_marked(method), MSG_UNMARKED.format(kind=kind.__name__, method=method.name))


if __name__ == '__main__':
    unittest.main()
