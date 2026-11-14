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
"""The UI tests press keys by the bindings of tui/keybindings.py, which say what a key does, never as letters written into the test.

A test that presses 'n' says nothing about whether it means rename, new or no, and breaks
silently when the program's key changes. Pressing keybindings.PatternsPage.RENAME says what it
means and follows the program, as the user asked on 2026-11-07. The same goes for naming the
letter as a key: Key.N is still only the letter. A key that types nothing, like Enter, Esc or an
arrow, is pressed by its name in Key, and a digit is the value being typed, so it stays a
literal. A key that isn't a binding's first is pressed with key_of(binding=..., key=Key.PLUS),
which names both, and any other letter a test needs, like one that must do nothing, is a named
constant at the top of the test file.
"""

import ast
import os
import unittest

from llamatron.tui.keys import Key

TEST_FOLDER = os.path.dirname(os.path.abspath(__file__))
PYTHON_SUFFIX = '.py'
FILE_ENCODING = 'utf-8'
# The methods that press keys in the UI tests, on a test or on Textual's pilot.
PRESSES = ('press', 'press_at_once')
# The class of keys in tui/keys.py, and the helper that names one key of a binding, inside which a key's own name is what's wanted.
KEY_CLASS = 'Key'
KEY_OF = 'key_of'
MSG_CHARACTER_KEY = '{file}:{line}: press(Key.{key}) names a character, not what the key does: press the binding from tui/keybindings.py, such as keybindings.ListPage.ADD'
MSG_LITERAL_KEY = '{file}:{line}: press({key!r}) should press a binding from tui/keybindings.py, or a named constant for a letter that is not a key'
# Code of the test's own, to check that the rule finds what it should and leaves the rest.
PRESSES_A_CHARACTER_KEY = 'self.press(Key.ENTER, Key.N, *[Key.PLUS] * 2)'
PRESSES_ONE_KEY_OF_A_BINDING = 'self.press(key_of(binding=keybindings.GateRow.ADJUST, key=Key.PLUS), Key.DOWN)'
PRESSES_A_LETTER = "self.press('n', '5', OLD_ADD_KEY)"
LETTER_PRESSED = 'n'


def test_files():
    return sorted(os.path.join(TEST_FOLDER, name) for name in os.listdir(TEST_FOLDER) if name.endswith(PYTHON_SUFFIX))


def parsed(path):
    with open(path, encoding=FILE_ENCODING) as source:
        return ast.parse(source.read(), filename=path)


def is_press(node):
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in PRESSES


def literal_keys(tree):
    """Return (line, key) for every string written straight into a press() call that isn't a digit."""
    found = []
    for node in ast.walk(tree):
        if is_press(node):
            for argument in node.args:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str) and not argument.value.isdigit():
                    found.append((node.lineno, argument.value))
    return found


def types_a_character(name):
    """Return whether a name of Key is a letter or a mark, a key that types its own character, which says nothing of what the key does."""
    value = getattr(Key, name, None)
    return isinstance(value, str) and len(value) == 1 and not value.isdigit()


def is_key_of(node):
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == KEY_OF


def keys_named_in(node):
    """Return the names of Key that a piece of code names, leaving out what is inside key_of(), which names one key of a binding."""
    if is_key_of(node):
        return []
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == KEY_CLASS:
        return [node.attr]
    return [name for child in ast.iter_child_nodes(node) for name in keys_named_in(child)]


def character_keys(tree):
    """Return (line, name) for every letter or mark of Key named in what a press() call presses."""
    found = []
    for node in ast.walk(tree):
        if is_press(node):
            for argument in node.args:
                found += [(node.lineno, name) for name in keys_named_in(argument) if types_a_character(name)]
    return found


class TestPressedKeys(unittest.TestCase):

    def test_no_test_presses_a_key_by_its_character(self):
        """A test that pressed the plus character to add broke when add became A, and said nothing about what it meant: about 35 lines did on 2026-11-09."""
        for path in test_files():
            for line, key in character_keys(parsed(path)):
                with self.subTest(file=os.path.basename(path), line=line):
                    self.fail(MSG_CHARACTER_KEY.format(file=os.path.basename(path), line=line, key=key))

    def test_no_test_presses_a_key_written_as_a_letter(self):
        for path in test_files():
            for line, key in literal_keys(parsed(path)):
                with self.subTest(file=os.path.basename(path), line=line):
                    self.fail(MSG_LITERAL_KEY.format(file=os.path.basename(path), line=line, key=key))

    def test_the_rule_finds_a_letter_and_a_mark_of_key_and_leaves_the_keys_that_type_nothing(self):
        found = [name for _, name in character_keys(ast.parse(PRESSES_A_CHARACTER_KEY))]
        self.assertEqual([getattr(Key, name) for name in found], [Key.N, Key.PLUS])

    def test_the_rule_leaves_one_key_of_a_binding(self):
        self.assertEqual(character_keys(ast.parse(PRESSES_ONE_KEY_OF_A_BINDING)), [])

    def test_the_rule_finds_a_letter_written_out_and_leaves_a_digit_and_a_named_constant(self):
        self.assertEqual([key for _, key in literal_keys(ast.parse(PRESSES_A_LETTER))], [LETTER_PRESSED])


if __name__ == '__main__':
    unittest.main()
